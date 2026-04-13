import streamlit as st
import pandas as pd
import pdfplumber
import re
from datetime import datetime

st.set_page_config(page_title="STM Matcher Pro", layout="wide")

st.title("📊 ระบบเทียบยอดบัญชี STM vs หลังบ้าน (Version: แก้ไขยอดติดลบ)")

# --- Sidebar ---
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
                        # เก็บเฉพาะตัวเลขเพียวๆ ไม่มีเครื่องหมาย
                        clean_amt = "{:.2f}".format(abs(float(amt.replace(',', ''))))
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
                # ใช้ abs() เพื่อลบเครื่องหมายลบออกก่อนเก็บค่า
                clean_amt = "{:.2f}".format(abs(float(amounts[0].replace(',', ''))))
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
        # --- ลอจิกการ Matching (ลบเครื่องหมายออกทั้งสองฝั่ง) ---
        stm_list = df_stm.to_dict('records')
        web_list = df_web.to_dict('records')

        matched_web_indices = []
        matched_stm_indices = []

        for w_idx, w_item in enumerate(web_list):
            for s_idx, s_item in enumerate(stm_list):
                if s_idx not in matched_stm_indices:
                    # เทียบเฉพาะตัวเลข String ที่จัด format แล้ว
                    if w_item['Amount'] == s_item['Amount']:
                        matched_web_indices.append(w_idx)
                        matched_stm_indices.append(s_idx)
                        break

        not_in_stm = [item for idx, item in enumerate(web_list) if idx not in matched_web_indices]
        not_in_web = [item for idx, item in enumerate(stm_list) if idx not in matched_stm_indices]

        st.divider()
        c1, c2 = st.columns(2)
        
        with c1:
            st.error(f"❌ หลังบ้านมี แต่ STM ไม่มี ({len(not_in_stm)})")
            if not_in_stm:
                st.table(pd.DataFrame(not_in_stm))

        with c2:
            st.warning(f"⚠️ STM มี แต่หลังบ้านไม่มี ({len(not_in_web)})")
            if not_in_web:
                st.table(pd.DataFrame(not_in_web))
        
        if not not_in_stm and not not_in_web:
            st.success("🎉 ยอดเงินทุกรายการตรงกันสมบูรณ์!")
