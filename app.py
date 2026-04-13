import streamlit as st
import pandas as pd
import pdfplumber
import re
from datetime import datetime

st.set_page_config(page_title="STM Matcher Pro (KTB Support)", layout="wide")

st.title("📊 ระบบเทียบยอดบัญชี STM vs หลังบ้าน (รองรับ KTB)")

# --- Sidebar ---
st.sidebar.header("📅 ตัวเลือกการกรอง")
selected_date = st.sidebar.date_input("เลือกวันที่ต้องการตรวจสอบ", datetime.now())

# เตรียม Format วันที่สำหรับเทียบ (รองรับทั้ง 2569 และ 2026)
d_short_th = selected_date.strftime("%d/%m/") + str(int(selected_date.strftime("%y")) + 43) # เช่น 12/04/69
d_dash_web = selected_date.strftime("%d-%m-%Y") # เช่น 12-04-2026

st.info(f"กำลังตรวจสอบข้อมูลของวันที่: **{selected_date.strftime('%d/%m/%Y')}** (ใน PDF จะมองหา {d_short_th})")

# --- ฟังก์ชันอ่าน PDF STM (ปรับปรุงเพื่อ KTB) ---
def extract_data_from_pdf(file):
    temp_data = []
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                lines = text.split('\n')
                for line in lines:
                    # มองหาบรรทัดที่มีวันที่แบบไทย (เช่น 01/04/69)
                    if d_short_th in line:
                        # 1. ดึงเวลา (มักอยู่บรรทัดถัดไป หรือท้ายบรรทัด)
                        time_match = re.search(r'(\d{2}:\d{2})', line)
                        time_val = time_match.group(1) if time_match else "--:--"
                        
                        # 2. ดึงยอดเงิน (KTB มักมีหลายตัวเลขในบรรทัดเดียว: ยอดถอน/ฝาก และ ยอดคงเหลือ)
                        # เราจะดึงทุกลำดับที่เป็นตัวเลขทศนิยม
                        amounts = re.findall(r'[\d,]+\.\d{2}', line)
                        
                        if len(amounts) >= 2:
                            # ตัวสุดท้ายมักจะเป็น 'ยอดเงินคงเหลือ' เราจะไม่เอา
                            # เราจะเอาตัวแรกๆ ที่ไม่ใช่ยอดคงเหลือ
                            actual_amount = amounts[0] 
                            val = float(actual_amount.replace(',', ''))
                            
                            temp_data.append({
                                "Time": time_val,
                                "Amount": "{:.2f}".format(abs(val))
                            })
    return pd.DataFrame(temp_data)

# --- ฟังก์ชันอ่านข้อมูลหลังบ้าน ---
def parse_backend_text(raw_text):
    extracted_data = []
    items = re.split(r'(\d{2}-\d{2}-\d{4})', raw_text)
    for i in range(1, len(items), 2):
        date_str = items[i]
        content = items[i+1]
        if date_str == d_dash_web:
            times = re.findall(r'(\d{2}:\d{2}:\d{2})', content)
            amounts = re.findall(r'(-?[\d,]+\.\d{2})', content)
            if times and amounts:
                clean_amt = "{:.2f}".format(abs(float(amounts[0].replace(',', ''))))
                extracted_data.append({"Time": times[0][:5], "Amount": clean_amt})
    return pd.DataFrame(extracted_data)

# --- ส่วน UI ---
uploaded_file = st.file_uploader("1. อัปโหลดไฟล์ PDF (KTB)", type=['pdf'])
raw_input = st.text_area("2. วางข้อมูลหลังบ้านเว็บที่นี่:", height=200)

if uploaded_file and raw_input:
    df_stm = extract_data_from_pdf(uploaded_file)
    df_web = parse_backend_text(raw_input)
    
    if df_stm.empty and df_web.empty:
        st.warning("ไม่พบข้อมูลในวันที่เลือก")
    else:
        # Matching Logic (จับคู่ยอดเงิน)
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
