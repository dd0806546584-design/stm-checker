import streamlit as st
import pandas as pd
import pdfplumber
import re
from datetime import datetime

st.set_page_config(page_title="STM Matcher Pro", layout="wide")

st.title("📊 ระบบเทียบยอดบัญชี STM vs หลังบ้าน")

# --- Sidebar: เลือกวันที่และธนาคาร ---
st.sidebar.header("⚙️ ตั้งค่าการตรวจสอบ")
bank = st.sidebar.selectbox("1. เลือกธนาคารของ PDF", ["KBANK (กสิกร)", "KTB (กรุงไทย)", "SCB (ไทยพาณิชย์)"])
selected_date = st.sidebar.date_input("2. เลือกวันที่ต้องการตรวจสอบ", datetime.now())

# แปลงวันที่ที่เลือกเป็นรูปแบบต่างๆ เพื่อใช้ค้นหา
d = selected_date.strftime("%d")
m = selected_date.strftime("%m")
y_en_short = selected_date.strftime("%y") # เช่น 26
y_en_full = selected_date.strftime("%Y")  # เช่น 2026
y_th_short = str(int(y_en_short) + 43)    # เช่น 69

# วันที่สำหรับตรวจในหลังบ้าน (เช่น 10-04-2026)
target_date_web = selected_date.strftime("%d-%m-%Y")

st.info(f"📅 กำลังตรวจสอบข้อมูลประจำวันที่: **{selected_date.strftime('%d/%m/%Y')}**")

# --- ฟังก์ชันอ่าน PDF STM ---
def get_stm_data(file, bank_name):
    extracted = []
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text: continue
            for line in text.split('\n'):
                # เช็กวันที่ใน PDF ตาม format ธนาคาร
                is_match = False
                if bank_name == "KBANK (กสิกร)" and f"{d}-{m}-{y_en_short}" in line: is_match = True
                elif bank_name == "KTB (กรุงไทย)" and f"{d}/{m}/{y_th_short}" in line: is_match = True
                elif bank_name == "SCB (ไทยพาณิชย์)" and f"{d}/{m}/{y_en_short}" in line: is_match = True
                
                if is_match:
                    t_match = re.search(r'(\d{2}:\d{2})', line)
                    time_str = t_match.group(1) if t_match else "--:--"
                    amts = re.findall(r'[\d,]+\.\d{2}', line)
                    if amts:
                        val = amts[0].replace(',', '')
                        extracted.append({"Time": time_str, "Amount": "{:.2f}".format(abs(float(val)))})
    return pd.DataFrame(extracted)

# --- ฟังก์ชันอ่านหลังบ้าน ---
def get_web_data(raw_text):
    extracted = []
    for line in raw_text.split('\n'):
        # แก้ไข: ค้นหาเฉพาะบรรทัดที่มีวันที่ "ตามที่คุณเลือกในปฏิทิน" เท่านั้น
        if target_date_web in line:
            amt_match = re.findall(r'(-?[\d,]+\.\d{2})', line)
            if amt_match:
                t_match = re.search(r'(\d{2}:\d{2})', line)
                time_str = t_match.group(1) if t_match else "--:--"
                extracted.append({"Time": time_str, "Amount": "{:.2f}".format(abs(float(amt_match[0].replace(',', ''))))})
    return pd.DataFrame(extracted)

# --- ส่วน UI ---
c1, c2 = st.columns(2)
with c1:
    pdf_file = st.file_uploader("1. อัปโหลดไฟล์ PDF", type=['pdf'])
with c2:
    web_input = st.text_area("2. วางข้อมูลหลังบ้าน:", height=150, placeholder=f"เช่นรายการของวันที่ {target_date_web}...")

if pdf_file and web_input:
    df_stm = get_stm_data(pdf_file, bank)
    df_web = get_web_data(web_input)
    
    # แสดงคำเตือนโดยใช้ค่าวันที่จากตัวแปรปฏิทิน (ไม่ใช่ค่าคงที่ 14 อีกต่อไป)
    if df_stm.empty: 
        st.warning(f"⚠️ ไม่พบรายการใน PDF วันที่ {selected_date.strftime('%d/%m/%Y')}")
    if df_web.empty: 
        st.warning(f"⚠️ ไม่พบรายการหลังบ้านที่มีวันที่ {target_date_web}")

    if not df_stm.empty and not df_web.empty:
        # Matching Logic
        stm_list = df_stm['Amount'].tolist()
        web_list = df_web['Amount'].tolist()
        
        diff_web, temp_stm = [], stm_list.copy()
        for _, row in df_web.iterrows():
            if row['Amount'] in temp_stm: temp_stm.remove(row['Amount'])
            else: diff_web.append(row)
                
        diff_stm, temp_web = [], web_list.copy()
        for _, row in df_stm.iterrows():
            if row['Amount'] in temp_web: temp_web.remove(row['Amount'])
            else: diff_stm.append(row)

        st.divider()
        res1, res2 = st.columns(2)
        with res1:
            st.error(f"❌ หลังบ้านมี แต่ STM ไม่มี ({len(diff_web)})")
            st.table(pd.DataFrame(diff_web) if diff_web else pd.DataFrame(columns=['Time', 'Amount']))
        with res2:
            st.warning(f"⚠️ STM มี แต่หลังบ้านไม่มี ({len(diff_stm)})")
            st.table(pd.DataFrame(diff_stm) if diff_stm else pd.DataFrame(columns=['Time', 'Amount']))
