import streamlit as st
import pandas as pd
import pdfplumber
import re
from datetime import datetime

st.set_page_config(page_title="STM Matcher Pro", layout="wide")

st.title("📊 ระบบเทียบยอดบัญชี STM vs หลังบ้าน (ระบุเวลา)")

# --- ส่วนของการเลือกวันที่ ---
st.sidebar.header("📅 ตัวเลือกการกรอง")
selected_date = st.sidebar.date_input("เลือกวันที่ต้องการตรวจสอบ", datetime.now())
formatted_date_stm = selected_date.strftime("%d/%m/%y") 
formatted_date_web = selected_date.strftime("%d-%m-%Y")

st.info(f"กำลังตรวจสอบข้อมูลวันที่: **{selected_date.strftime('%d/%m/%Y')}**")

# --- ฟังก์ชันอ่าน PDF STM ---
def extract_data_from_pdf(file):
    temp_data = []
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                # ดึง วันที่, เวลา, และ ยอดเงิน
                matches = re.findall(r'(\d{2}/\d{2}/\d{2,4})\s+(\d{2}:\d{2})\s+.*?([\d,]+\.\d{2})', text)
                for m in matches:
                    d, t, amt = m
                    if len(d) > 8: d = d[:6] + d[-2:] # ปรับเป็น 14/04/26
                    
                    if d == formatted_date_stm:
                        temp_data.append({
                            "Date": d,
                            "Time": t,
                            "Amount": float(amt.replace(',', '')),
                            "Source": "STM"
                        })
    return pd.DataFrame(temp_data)

# --- ฟังก์ชันอ่านข้อมูลหลังบ้าน ---
def parse_backend_text(raw_text):
    extracted_data = []
    # แยกรายการตามวันที่
    items = re.split(r'(\d{2}-\d{2}-\d{4})', raw_text)
    
    for i in range(1, len(items), 2):
        date_str = items[i]
        content = items[i+1]
        
        if date_str == formatted_date_web:
            # ดึงเวลา (HH:MM:SS) และ ยอดเงิน
            times = re.findall(r'(\d{2}:\d{2}:\d{2})', content)
            amounts = re.findall(r'(-?[\d,]+\.\d{2})', content)
            
            if times and amounts:
                val = float(amounts[0].replace(',', ''))
                # เอาแค่ HH:MM เพื่อให้เทียบกับ STM ได้ง่ายขึ้น
                short_time = times[0][:5] 
                
                extracted_data.append({
                    "Date": date_str.replace('-', '/')[0:6] + date_str[-2:],
                    "Time": short_time,
                    "Amount": val,
                    "Source": "Web"
                })
    return pd.DataFrame(extracted_data)

# --- ส่วนประมวลผล ---
if pdf_file := st.file_uploader("1. อัปโหลดไฟล์ PDF STM", type=['pdf']):
    if raw_input := st.text_area("2. วางข้อมูลหลังบ้านเว็บที่นี่:", height=200):
        
        df_stm = extract_data_from_pdf(pdf_file)
        df_web = parse_backend_text(raw_input)
        
        if df_stm.empty and df_web.empty:
            st.warning("ไม่พบข้อมูลในวันที่เลือก")
        else:
            # สร้าง Key สำหรับเทียบ (วันที่_ยอดเงิน) *ไม่ใช้เวลาเทียบเพราะวินาทีอาจคลาดเคลื่อน*
            df_stm['key'] = df_stm['Amount'].map('{:.2f}'.format)
            df_web['key'] = df_web['Amount'].map('{:.2f}'.format)
            
            st.divider()
            
            # ยอดที่ "หลังบ้านมี" แต่ "STM ไม่มี"
            # ใช้เปรียบเทียบจากยอดเงินเป็นหลัก
            not_in_stm = df_web[~df_web['key'].isin(df_stm['key'])]
            
            # ยอดที่ "STM มี" แต่ "หลังบ้านไม่มี"
            not_in_web = df_stm[~df_stm['key'].isin(df_web['key'])]

            c1, c2 = st.columns(2)
            
            with c1:
                st.error(f"❌ หลังบ้านมี แต่ STM ไม่มี ({len(not_in_stm)} รายการ)")
                if not not_in_stm.empty:
                    # แสดงเวลาด้วยเพื่อให้หาตัวตนง่ายขึ้น
                    st.table(not_in_stm[['Time', 'Amount']].rename(columns={'Time': 'เวลาหลังบ้าน', 'Amount': 'ยอดเงิน'}))
                else:
                    st.success("ไม่มีรายการตกหล่น")

            with c2:
                st.warning(f"⚠️ STM มี แต่หลังบ้านไม่มี ({len(not_in_web)} รายการ)")
                if not not_in_web.empty:
                    st.table(not_in_web[['Time', 'Amount']].rename(columns={'Time': 'เวลาใน STM', 'Amount': 'ยอดเงิน'}))
                else:
                    st.success("ลงข้อมูลครบถ้วน")
