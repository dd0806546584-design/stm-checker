import streamlit as st
import pandas as pd
import pdfplumber
import re
from datetime import datetime

st.set_page_config(page_title="STM Matcher Multi-Bank", layout="wide")

st.title("📊 ระบบเทียบยอดบัญชี (รองรับหลายธนาคาร)")

# --- Sidebar ---
st.sidebar.header("📅 ตัวเลือกการกรอง")
selected_date = st.sidebar.date_input("เลือกวันที่ต้องการตรวจสอบ", datetime.now())
# สร้างรูปแบบวันที่หลายๆ แบบที่ธนาคารชอบใช้
d_long = selected_date.strftime("%d/%m/%Y")   # 14/04/2026
d_short = selected_date.strftime("%d/%m/%y")  # 14/04/26
d_dash = selected_date.strftime("%d-%m-%Y")   # 14-04-2026

# --- ฟังก์ชันอ่าน PDF STM (แบบยืดหยุ่นสูง) ---
def extract_data_from_pdf(file):
    temp_data = []
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                # แยกข้อความเป็นบรรทัด
                lines = text.split('\n')
                for line in lines:
                    # 1. เช็กก่อนว่าบรรทัดนี้มีวันที่ที่เราเลือกไหม
                    if d_long in line or d_short in line:
                        # 2. ค้นหาเวลา (HH:MM)
                        time_match = re.search(r'(\d{2}:\d{2})', line)
                        time_val = time_match.group(1) if time_match else "--:--"
                        
                        # 3. ค้นหายอดเงิน (ตัวเลขที่มีจุดทศนิยม 2 ตำแหน่ง)
                        # ดึงมาทุกลำดับในบรรทัดนั้น แล้วเลือกตัวที่ดูเหมือนยอดเงินโอนมากที่สุด
                        amounts = re.findall(r'[\d,]+\.\d{2}', line)
                        
                        if amounts:
                            # ปกติยอดเงินโอนมักจะเป็นตัวแรกๆ หรือตัวที่เปลี่ยนค่า
                            # ในที่นี้เราจะกรองตัวเลขที่ 'ไม่ใช่ยอดคงเหลือ' (ถ้าทำได้) 
                            # แต่เบื้องต้นให้ดึงมาเทียบทั้งหมดก่อน
                            for amt in amounts:
                                val = float(amt.replace(',', ''))
                                if val > 0: # สนใจเฉพาะยอดที่ไม่เป็น 0
                                    temp_data.append({
                                        "Time": time_val,
                                        "Amount": "{:.2f}".format(abs(val))
                                    })
    return pd.DataFrame(temp_data).drop_duplicates().reset_index(drop=True)

# --- ฟังก์ชันอ่านข้อมูลหลังบ้าน ---
def parse_backend_text(raw_text):
    extracted_data = []
    items = re.split(r'(\d{2}-\d{2}-\d{4})', raw_text)
    for i in range(1, len(items), 2):
        date_str = items[i]
        content = items[i+1]
        if date_str == d_dash:
            times = re.findall(r'(\d{2}:\d{2}:\d{2})', content)
            amounts = re.findall(r'(-?[\d,]+\.\d{2})', content)
            if times and amounts:
                clean_amt = "{:.2f}".format(abs(float(amounts[0].replace(',', ''))))
                extracted_data.append({"Time": times[0][:5], "Amount": clean_amt})
    return pd.DataFrame(extracted_data)

# --- ส่วน UI ---
uploaded_file = st.file_uploader("1. อัปโหลดไฟล์ PDF STM (ได้ทุกธนาคาร)", type=['pdf'])
raw_input = st.text_area("2. วางข้อมูลหลังบ้านเว็บที่นี่:", height=200)

if uploaded_file and raw_input:
    with st.spinner('กำลังประมวลผล...'):
        df_stm = extract_data_from_pdf(uploaded_file)
        df_web = parse_backend_text(raw_input)
        
        if df_stm.empty:
            st.error(f"❌ ระบบอ่านไฟล์ PDF ธนาคารนี้ไม่ได้ หรือไม่พบยอดของวันที่ {d_short}")
            st.info("ข้อแนะนำ: ลองเปิด PDF ดูว่าวันที่ในไฟล์เขียนรูปแบบไหน (เช่น 14/04/2026 หรือ 14 Apr)")
        
        if not df_stm.empty and not df_web.empty:
            # Matching Logic
            stm_list = df_stm.to_dict('records')
            web_list = df_web.to_dict('records')
            matched_web, matched_stm = [], []

            for w_idx, w_item in enumerate(web_list):
                for s_idx, s_item in enumerate(stm_list):
                    if s_idx not in matched_stm and w_item['Amount'] == s_item['Amount']:
                        matched_web.append(w_idx)
                        matched_stm.append(s_idx)
                        break

            not_in_stm = [item for idx, item in enumerate(web_list) if idx not in matched_web]
            not_in_web = [item for idx, item in enumerate(stm_list) if idx not in matched_stm]

            st.divider()
            c1, c2 = st.columns(2)
            with c1:
                st.error(f"❌ หลังบ้านมี แต่ STM ไม่มี ({len(not_in_stm)})")
                st.table(pd.DataFrame(not_in_stm) if not_in_stm else pd.DataFrame(columns=['Time', 'Amount']))
            with c2:
                st.warning(f"⚠️ STM มี แต่หลังบ้านไม่มี ({len(not_in_web)})")
                st.table(pd.DataFrame(not_in_web) if not_in_web else pd.DataFrame(columns=['Time', 'Amount']))
