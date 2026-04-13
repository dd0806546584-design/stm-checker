import streamlit as st
import pandas as pd
import pdfplumber
import re
from datetime import datetime

st.set_page_config(page_title="STM Matcher Pro", layout="wide")

st.title("📊 ระบบเทียบยอดบัญชี STM vs หลังบ้าน")

# --- ส่วนของการเลือกวันที่ (ใหม่!) ---
st.sidebar.header("📅 ตัวเลือกการกรอง")
selected_date = st.sidebar.date_input("เลือกวันที่ต้องการตรวจสอบ", datetime.now())
formatted_date = selected_date.strftime("%d/%m/%y") # แปลงเป็น 14/04/26 เพื่อเทียบกับ STM

st.info(f"ระบบกำลังแสดงข้อมูลของวันที่: **{selected_date.strftime('%d/%m/%Y')}**")

# --- ฟังก์ชันอ่าน PDF STM ---
def extract_data_from_pdf(file):
    temp_data = []
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                matches = re.findall(r'(\d{2}/\d{2}/\d{2,4}).*?([\d,]+\.\d{2})', text)
                for m in matches:
                    # กรองเอาเฉพาะวันที่ที่เลือก
                    date_val = m[0]
                    if len(date_val) > 8: # ถ้าเป็น 2026 ให้เหลือ 26
                        date_val = date_val[:6] + date_val[-2:]
                    
                    if date_val == formatted_date:
                        temp_data.append({
                            "Date": date_val, 
                            "Amount": float(m[1].replace(',', ''))
                        })
    return pd.DataFrame(temp_data)

# --- ฟังก์ชันอ่านข้อมูลหลังบ้าน ---
def parse_backend_text(raw_text):
    extracted_data = []
    items = re.split(r'(\d{2}-\d{2}-\d{4})', raw_text)
    
    for i in range(1, len(items), 2):
        date_str = items[i]
        content = items[i+1]
        
        # กรองข้อมูลหลังบ้านตามวันที่เลือก
        # แปลง 14-04-2026 เป็น 14/04/26
        clean_date = date_str.replace('-', '/')
        short_date = clean_date[:6] + clean_date[-2:]
        
        if short_date == formatted_date:
            amounts = re.findall(r'(-?[\d,]+\.\d{2})', content)
            if amounts:
                val = float(amounts[0].replace(',', ''))
                extracted_data.append({
                    "Date": short_date,
                    "Amount": val
                })
    return pd.DataFrame(extracted_data)

# --- ส่วน UI ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("1. ฝั่งธนาคาร (PDF)")
    pdf_file = st.file_uploader("อัปโหลดไฟล์ PDF", type=['pdf'])

with col2:
    st.subheader("2. ฝั่งหลังบ้านเว็บ")
    raw_input = st.text_area("วางข้อมูลหลังบ้านที่นี่:", height=250)

# --- ส่วนการคำนวณ ---
if pdf_file and raw_input:
    df_stm = extract_data_from_pdf(pdf_file)
    df_web = parse_backend_text(raw_input)
    
    if df_stm.empty and df_web.empty:
        st.warning(f"📭 ไม่พบรายการของวันที่ {selected_date.strftime('%d/%m/%Y')} ในไฟล์หรือข้อความที่ระบุ")
    else:
        # สร้าง Key สำหรับเทียบ
        if not df_stm.empty:
            df_stm['key'] = df_stm['Date'] + "_" + df_stm['Amount'].map('{:.2f}'.format)
        if not df_web.empty:
            df_web['key'] = df_web['Date'] + "_" + df_web['Amount'].map('{:.2f}'.format)
            
        st.divider()
        m1, m2 = st.columns(2)
        m1.metric(f"STM ({selected_date.strftime('%d/%m/%y')})", f"{len(df_stm)} รายการ")
        m2.metric(f"หลังบ้าน ({selected_date.strftime('%d/%m/%y')})", f"{len(df_web)} รายการ")

        # ตรวจสอบจุดที่ไม่ตรง (Handle กรณี Empty DataFrame)
        not_in_stm = df_web[~df_web['key'].isin(df_stm['key'])] if not df_web.empty else pd.DataFrame()
        not_in_web = df_stm[~df_stm['key'].isin(df_web['key'])] if not df_stm.empty else pd.DataFrame()

        res1, res2 = st.columns(2)
        with res1:
            st.error(f"❌ หลังบ้านมี แต่ STM ไม่มี ({len(not_in_stm)})")
            st.dataframe(not_in_stm[['Date', 'Amount']] if not not_in_stm.empty else pd.DataFrame(columns=['Date', 'Amount']), use_container_width=True)
        with res2:
            st.warning(f"⚠️ STM มี แต่หลังบ้านไม่มี ({len(not_in_web)})")
            st.dataframe(not_in_web[['Date', 'Amount']] if not not_in_web.empty else pd.DataFrame(columns=['Date', 'Amount']), use_container_width=True)
