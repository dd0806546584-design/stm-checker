import streamlit as st
import pandas as pd
import pdfplumber
import re
from datetime import datetime

st.set_page_config(page_title="STM Matcher Pro", layout="wide")

st.title("📊 ระบบเทียบยอดบัญชี (เวอร์ชันปรับปรุงความแม่นยำ)")

# --- แถบตั้งค่าด้านข้าง ---
st.sidebar.header("📅 การตั้งค่า")
bank = st.sidebar.selectbox("เลือกธนาคาร", ["KBANK (กสิกร)", "KTB (กรุงไทย)", "SCB (ไทยพาณิชย์)"])
selected_date = st.sidebar.date_input("วันที่ตรวจสอบ", datetime.now())

# เตรียม Format วันที่สำหรับค้นหา
d, m = selected_date.strftime("%d"), selected_date.strftime("%m")
y_en, y_th = selected_date.strftime("%y"), str(int(selected_date.strftime("%y")) + 43)
target_web = selected_date.strftime("%d-%m-%Y") # 14-04-2026

# --- ฟังก์ชันอ่าน PDF (เน้นเฉพาะยอดธุรกรรม) ---
def get_stm_data(file, bank_name):
    extracted = []
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text: continue
            for line in text.split('\n'):
                # เช็กวันที่ตามประเภทธนาคาร
                valid = False
                if bank_name == "KBANK (กสิกร)" and f"{d}-{m}-{y_en}" in line: valid = True
                elif bank_name == "KTB (กรุงไทย)" and f"{d}/{m}/{y_th}" in line: valid = True
                elif bank_name == "SCB (ไทยพาณิชย์)" and f"{d}/{m}/{y_en}" in line: valid = True
                
                if valid:
                    # ดึงเวลา
                    t_match = re.search(r'(\d{2}:\d{2})', line)
                    time_str = t_match.group(1) if t_match else "--:--"
                    # ดึงยอดเงิน (เอาตัวเลขที่มี .22)
                    amts = re.findall(r'[\d,]+\.\d{2}', line)
                    if amts:
                        # กสิกร/กรุงไทย ยอดธุรกรรมมักเป็นตัวแรก (ไม่ใช่ยอดคงเหลือตัวสุดท้าย)
                        val = amts[0].replace(',', '')
                        extracted.append({"Time": time_str, "Amount": "{:.2f}".format(abs(float(val)))})
    return pd.DataFrame(extracted)

# --- ฟังก์ชันอ่านหลังบ้าน (ดึงเฉพาะบรรทัดที่มียอดเงินจริงๆ) ---
def get_web_data(raw_text):
    extracted = []
    for line in raw_text.split('\n'):
        # ต้องมีวันที่ที่เราเลือกอยู่ในบรรทัดนั้น ถึงจะดึงยอดมา (กันดึงเลขมั่ว)
        if target_web in line:
            amt_match = re.findall(r'(-?[\d,]+\.\d{2})', line)
            if amt_match:
                t_match = re.search(r'(\d{2}:\d{2})', line)
                time_str = t_match.group(1) if t_match else "--:--"
                extracted.append({"Time": time_str, "Amount": "{:.2f}".format(abs(float(amt_match[0].replace(',', ''))))})
    return pd.DataFrame(extracted)

# --- ส่วนการทำงานหลัก ---
c1, c2 = st.columns(2)
with c1:
    pdf_file = st.file_uploader("1. อัปโหลดไฟล์ PDF", type=['pdf'])
with c2:
    web_input = st.text_area("2. วางข้อมูลหลังบ้าน:", height=150, placeholder="วางข้อมูลที่มีวันที่และยอดเงิน...")

if pdf_file and web_input:
    df_stm = get_stm_data(pdf_file, bank)
    df_web = get_web_data(web_input)
    
    # ป้องกันแอปค้างถ้าหาข้อมูลไม่เจอ
    if df_stm.empty: st.warning("⚠️ ไม่พบรายการใน PDF (ลองเช็กวันที่และธนาคารที่เลือก)")
    if df_web.empty: st.warning("⚠️ ไม่พบรายการจากหลังบ้าน (ต้องมีวันที่ 14-04-2026 ในข้อความที่วาง)")

    if not df_stm.empty and not df_web.empty:
        # Matching Logic (ยอดต่อยอด)
        stm_list = df_stm['Amount'].tolist()
        web_list = df_web['Amount'].tolist()
        
        # เปรียบเทียบ
        diff_web = [] # เว็บมี แต่ STM ไม่มี
        temp_stm = stm_list.copy()
        for _, row in df_web.iterrows():
            if row['Amount'] in temp_stm: temp_stm.remove(row['Amount'])
            else: diff_web.append(row)
                
        diff_stm = [] # STM มี แต่เว็บไม่มี
        temp_web = web_list.copy()
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
