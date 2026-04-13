import streamlit as st
import pandas as pd
import pdfplumber
import re
from datetime import datetime

st.set_page_config(page_title="STM Matcher Pro", layout="wide")

st.title("📊 ระบบเทียบยอดบัญชี STM vs หลังบ้าน")

# --- Sidebar: การตั้งค่าที่แม่นยำ ---
st.sidebar.header("⚙️ ตั้งค่าการอ่านไฟล์")
bank_type = st.sidebar.selectbox("เลือกธนาคารของไฟล์ PDF", ["KBANK (กสิกร)", "KTB (กรุงไทย)", "SCB (ไทยพาณิชย์)"])
selected_date = st.sidebar.date_input("เลือกวันที่ตรวจสอบ", datetime.now())

# เตรียมตัวแปรวันที่
d = selected_date.strftime("%d")
m = selected_date.strftime("%m")
y_en = selected_date.strftime("%y") # 26
y_th = str(int(y_en) + 43)          # 69

# --- ฟังก์ชันดึงข้อมูลแยกตามธนาคาร ---
def extract_stm(file, bank):
    data = []
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text: continue
            for line in text.split('\n'):
                # ตรวจสอบวันที่ตาม Format ธนาคาร
                is_date = False
                if bank == "KBANK (กสิกร)" and f"{d}-{m}-{y_en}" in line: is_date = True
                elif bank == "KTB (กรุงไทย)" and f"{d}/{m}/{y_th}" in line: is_date = True
                elif bank == "SCB (ไทยพาณิชย์)" and f"{d}/{m}/{y_en}" in line: is_date = True
                
                if is_date:
                    # ดึงเวลา
                    time_m = re.search(r'(\d{2}:\d{2})', line)
                    t = time_m.group(1) if time_m else "--:--"
                    
                    # ดึงยอดเงิน (Regex เฉพาะตัวเลขที่มีทศนิยม)
                    amts = re.findall(r'[\d,]+\.\d{2}', line)
                    if amts:
                        # ลอจิกเลือกยอดเงิน (หลบยอดคงเหลือ)
                        if bank == "KBANK (กสิกร)":
                            # กสิกร ยอดเงินธุรกรรมมักจะอยู่ 'ก่อน' ยอดคงเหลือ
                            val = amts[0] 
                        elif bank == "KTB (กรุงไทย)":
                            # กรุงไทย ยอดเงินมักอยู่ตัวแรก (รายการฝาก/ถอน)
                            val = amts[0]
                        else:
                            val = amts[0]
                        
                        data.append({"Time": t, "Amount": "{:.2f}".format(abs(float(val.replace(',', ''))))})
    return pd.DataFrame(data)

# --- ฟังก์ชันดึงข้อมูลหลังบ้าน (เน้นเฉพาะบรรทัดที่มีราคา) ---
def extract_web(raw_text):
    data = []
    # กรองเฉพาะบรรทัดที่มียอดเงิน และวันที่ตรงกัน (เช่น 12-04-2026)
    target_date = selected_date.strftime("%d-%m-%Y")
    lines = raw_text.split('\n')
    for line in lines:
        if target_date in line:
            amts = re.findall(r'(-?[\d,]+\.\d{2})', line)
            if amts:
                time_m = re.search(r'(\d{2}:\d{2})', line)
                t = time_m.group(1) if time_m else "--:--"
                data.append({"Time": t, "Amount": "{:.2f}".format(abs(float(amts[0].replace(',', ''))))})
    return pd.DataFrame(data)

# --- ส่วนแสดงผล ---
col1, col2 = st.columns(2)
with col1:
    pdf_file = st.file_uploader("1. อัปโหลด PDF", type=['pdf'])
with col2:
    web_input = st.text_area("2. วางข้อมูลหลังบ้าน:", height=150)

if pdf_file and web_input:
    df_stm = extract_stm(pdf_file, bank_type)
    df_web = extract_web(web_input)
    
    st.divider()
    if df_stm.empty: st.warning(f"⚠️ ไม่พบรายการใน PDF (เช็กว่าเลือกธนาคารและวันที่ตรงกับในไฟล์ไหม)")
    
    # Matching Logic
    stm_list = df_stm['Amount'].tolist()
    web_list = df_web['Amount'].tolist()
    
    diff_web = [] # ในเว็บมี แต่ STM ไม่มี
    temp_stm = stm_list.copy()
    for _, row in df_web.iterrows():
        if row['Amount'] in temp_stm: temp_stm.remove(row['Amount'])
        else: diff_web.append(row)
            
    diff_stm = [] # ใน STM มี แต่เว็บไม่มี
    temp_web = web_list.copy()
    for _, row in df_stm.iterrows():
        if row['Amount'] in temp_web: temp_web.remove(row['Amount'])
        else: diff_stm.append(row)

    c1, c2 = st.columns(2)
    with c1:
        st.error(f"❌ หลังบ้านมี แต่ STM ไม่มี ({len(diff_web)})")
        st.table(pd.DataFrame(diff_web) if diff_web else pd.DataFrame(columns=['Time', 'Amount']))
    with c2:
        st.warning(f"⚠️ STM มี แต่หลังบ้านไม่มี ({len(diff_stm)})")
        st.table(pd.DataFrame(diff_stm) if diff_stm else pd.DataFrame(columns=['Time', 'Amount']))
