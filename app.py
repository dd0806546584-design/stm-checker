import streamlit as st
import pandas as pd
import pdfplumber
import re
from datetime import datetime

st.set_page_config(page_title="Universal STM Matcher", layout="wide")

st.title("📊 ระบบเทียบยอดบัญชี (All-in-One Support)")
st.caption("รองรับ KTB, KBANK, SCB และธนาคารหลักอื่นๆ")

# --- ส่วนของการเลือกวันที่ ---
st.sidebar.header("📅 ตัวเลือกการกรอง")
selected_date = st.sidebar.date_input("เลือกวันที่ตรวจสอบ", datetime.now())

# สร้างชุดตัวแปรวันที่หลายรูปแบบเพื่อเอาไปค้นหาใน PDF
d_day = selected_date.strftime("%d")
d_month = selected_date.strftime("%m")
d_year_short_th = str(int(selected_date.strftime("%y")) + 43) # 69
d_year_short_en = selected_date.strftime("%y")               # 26
d_year_full_en = selected_date.strftime("%Y")               # 2026

# รูปแบบวันที่ที่พบบ่อยใน STM: 14/04/69, 14/04/26, 14-04-26, 14/04/2026
date_patterns = [
    f"{d_day}/{d_month}/{d_year_short_th}",
    f"{d_day}/{d_month}/{d_year_short_en}",
    f"{d_day}-{d_month}-{d_year_short_en}",
    f"{d_day}/{d_month}/{d_year_full_en}"
]

# --- ฟังก์ชัน Universal Scanner ---
def universal_pdf_scanner(file):
    extracted_data = []
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text: continue
            
            lines = text.split('\n')
            for line in lines:
                # 1. เช็กว่าบรรทัดนี้มีวันที่ที่เราต้องการไหม (เช็กทุก Pattern)
                if any(pat in line for pat in date_patterns):
                    # 2. ดึงเวลา (HH:MM)
                    time_match = re.search(r'(\d{2}:\d{2})', line)
                    t_val = time_match.group(1) if time_match else "--:--"
                    
                    # 3. ดึงยอดเงิน (เน้นตัวเลขที่มีทศนิยม 2 ตำแหน่ง)
                    # กวาดตัวเลขทั้งหมด เช่น 5,000.00 หรือ 500.00
                    amounts = re.findall(r'[\d,]+\.\d{2}', line)
                    
                    if amounts:
                        # กรณี KTB/KBANK อาจมียอดคงเหลือต่อท้าย เราจะเช็กตำแหน่งยอดเงิน
                        # โดยปกติยอดธุรกรรมจะมาก่อนยอดคงเหลือ
                        for amt in amounts:
                            clean_amt = amt.replace(',', '')
                            # กรองยอดที่อาจเป็นเลขสาขาหรืออื่นๆ (เช่น .00 เฉยๆ)
                            if float(clean_amt) > 0:
                                extracted_data.append({
                                    "Time": t_val,
                                    "Amount": "{:.2f}".format(abs(float(clean_amt)))
                                })
                                # ถ้าได้ยอดแล้วให้หยุดหาในบรรทัดนั้น (เพื่อไม่ให้ไปดึงยอดคงเหลือ)
                                break 
    return pd.DataFrame(extracted_data)

# --- ส่วน UI และลอจิกการเทียบยอด ---
col1, col2 = st.columns(2)
with col1:
    pdf_file = st.file_uploader("1. อัปโหลดไฟล์ STM (PDF)", type=['pdf'])
with col2:
    raw_input = st.text_area("2. วางข้อมูลหลังบ้านเว็บ:", height=150, placeholder="วางรายการจากหน้าเว็บ...")

if pdf_file and raw_input:
    df_stm = universal_pdf_scanner(pdf_file)
    
    # ดึงข้อมูลจากหลังบ้าน (เน้นดึงตัวเลขจากบรรทัด)
    web_data = []
    web_lines = raw_input.split('\n')
    for wl in web_lines:
        amt_web = re.findall(r'(-?[\d,]+\.\d{2})', wl)
        if amt_web:
            # ดึงเวลาถ้ามี
            time_web = re.search(r'(\d{2}:\d{2})', wl)
            tw = time_web.group(1) if time_web else "--:--"
            web_data.append({"Time": tw, "Amount": "{:.2f}".format(abs(float(amt_web[0].replace(',', ''))))})
    df_web = pd.DataFrame(web_data)

    if not df_stm.empty or not df_web.empty:
        # ลอจิกการ Matching แบบแม่นยำ (ป้องกันยอดซ้ำ)
        stm_list = df_stm['Amount'].tolist()
        web_list = df_web['Amount'].tolist()
        
        diff_in_web = [] # เว็บมี แต่ STM ไม่มี
        temp_stm = stm_list.copy()
        for _, row in df_web.iterrows():
            if row['Amount'] in temp_stm:
                temp_stm.remove(row['Amount'])
            else:
                diff_in_web.append(row)

        diff_in_stm = [] # STM มี แต่เว็บไม่มี
        temp_web = web_list.copy()
        for _, row in df_stm.iterrows():
            if row['Amount'] in temp_web:
                temp_web.remove(row['Amount'])
            else:
                diff_in_stm.append(row)

        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            st.error(f"❌ หลังบ้านมี แต่ STM ไม่มี ({len(diff_in_web)})")
            st.table(pd.DataFrame(diff_in_web) if diff_in_web else pd.DataFrame(columns=['Time', 'Amount']))
        with c2:
            st.warning(f"⚠️ STM มี แต่หลังบ้านไม่มี ({len(diff_in_stm)})")
            st.table(pd.DataFrame(diff_in_stm) if diff_in_stm else pd.DataFrame(columns=['Time', 'Amount']))
