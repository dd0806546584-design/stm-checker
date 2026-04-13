import streamlit as st
import pandas as pd
import pdfplumber
import re
from datetime import datetime

st.set_page_config(page_title="STM Matcher Pro", layout="wide")

st.title("📊 ระบบเทียบยอดบัญชี STM vs หลังบ้าน (ฉบับปรับปรุงความแม่นยำ)")

# --- Sidebar สำหรับตั้งค่า ---
st.sidebar.header("📅 ตัวเลือกการกรอง")
selected_date = st.sidebar.date_input("เลือกวันที่ต้องการตรวจสอบ", datetime.now())
formatted_date_stm = selected_date.strftime("%d/%m/%y") 
formatted_date_web = selected_date.strftime("%d-%m-%Y")

# --- ฟังก์ชันอ่าน PDF STM ---
def extract_data_from_pdf(file):
    temp_data = []
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                matches = re.findall(r'(\d{2}/\d{2}/\d{2,4})\s+(\d{2}:\d{2})\s+.*?([\d,]+\.\d{2})', text)
                for m in matches:
                    d, t, amt = m
                    if len(d) > 8: d = d[:6] + d[-2:]
                    if d == formatted_date_stm:
                        # บังคับให้เป็น String ทศนิยม 2 ตำแหน่งทันที
                        clean_amt = "{:.2f}".format(float(amt.replace(',', '')))
                        temp_data.append({"Time": t, "Amount": clean_amt})
    return pd.DataFrame(temp_data)

# --- ฟังก์ชันอ่านข้อมูลหลังบ้าน ---
def parse_backend_text(raw_text):
    extracted_data = []
    items = re.split(r'(\d{2}-\d{2}-\d{4})', raw_text)
    for i in range(1, len(items), 2):
        date_str = items[i]
        content = items[i+1]
        if date_str == formatted_date_web:
            times = re.findall(r'(\d{2}:\d{2}:\d{2})', content)
            amounts = re.findall(r'(-?[\d,]+\.\d{2})', content)
            if times and amounts:
                # บังคับให้เป็น String ทศนิยม 2 ตำแหน่ง
                clean_amt = "{:.2f}".format(float(amounts[0].replace(',', '')))
                extracted_data.append({"Time": times[0][:5], "Amount": clean_amt})
    return pd.DataFrame(extracted_data)

# --- ส่วน UI ---
uploaded_file = st.file_uploader("1. อัปโหลดไฟล์ PDF STM", type=['pdf'])
raw_input = st.text_area("2. วางข้อมูลหลังบ้านเว็บที่นี่:", height=200)

if uploaded_file and raw_input:
    df_stm = extract_data_from_pdf(uploaded_file)
    df_web = parse_backend_text(raw_input)
    
    if df_stm.empty and df_web.empty:
        st.warning(f"ไม่พบรายการในวันที่ {selected_date.strftime('%d/%m/%Y')}")
    else:
        st.divider()
        
        # --- ลอจิกการ Matching (ใช้ยอดเงินที่จัด Format แล้วเป็น Key) ---
        # สร้าง List ของยอดเงินเพื่อใช้เช็ค
        stm_amounts = df_stm['Amount'].tolist()
        web_amounts = df_web['Amount'].tolist()

        # รายการที่เว็บมี แต่ STM ไม่มี (ยอดที่หาคู่ไม่ได้ใน STM)
        not_in_stm = []
        temp_stm = stm_amounts.copy()
        for _, row in df_web.iterrows():
            if row['Amount'] in temp_stm:
                temp_stm.remove(row['Amount']) # ถ้าเจอแล้วให้ลบออก (ป้องกันยอดซ้ำมาจับคู่ซ้อน)
            else:
                not_in_stm.append(row)

        # รายการที่ STM มี แต่เว็บไม่มี
        not_in_web = []
        temp_web = web_amounts.copy()
        for _, row in df_stm.iterrows():
            if row['Amount'] in temp_web:
                temp_web.remove(row['Amount'])
            else:
                not_in_web.append(row)

        # --- แสดงผล ---
        c1, c2 = st.columns(2)
        
        with c1:
            st.error(f"❌ หลังบ้านมี แต่ STM ไม่มี ({len(not_in_stm)} ยอด)")
            if not_in_stm:
                st.table(pd.DataFrame(not_in_stm))
            else:
                st.success("ฝั่งนี้ตรงกันหมด!")

        with c2:
            st.warning(f"⚠️ STM มี แต่หลังบ้านไม่มี ({len(not_in_web)} ยอด)")
            if not_in_web:
                st.table(pd.DataFrame(not_in_web))
            else:
                st.success("ลงข้อมูลครบถ้วน!")
