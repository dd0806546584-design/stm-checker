import streamlit as st
import pandas as pd
import pdfplumber
import re

st.set_page_config(page_title="STM Matcher", layout="wide")

st.title("📊 ระบบเทียบยอดบัญชี STM vs หลังบ้าน")
st.info("คำแนะนำ: อัปโหลดไฟล์ PDF จากธนาคาร และเลือกวิธีใส่ข้อมูลจากหลังบ้านเว็บ")

# --- ฟังก์ชันอ่าน PDF ---
def extract_data_from_pdf(file):
    temp_data = []
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                # Regex นี้ค้นหาวันที่ (DD/MM/YY) และยอดเงิน (0.00) 
                # อาจต้องปรับตาม Format ของแต่ละธนาคาร
                matches = re.findall(r'(\d{2}/\d{2}/\d{2}).*?([\d,]+\.\d{2})', text)
                for m in matches:
                    temp_data.append({"Date": m[0], "Amount": float(m[1].replace(',', ''))})
    return pd.DataFrame(temp_data)

# --- ส่วน UI ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("1. ฝั่งธนาคาร (PDF)")
    pdf_file = st.file_uploader("ลากไฟล์ PDF STM วางที่นี่", type=['pdf'])

with col2:
    st.subheader("2. ฝั่งหลังบ้านเว็บ")
    method = st.radio("วิธีนำเข้าข้อมูล:", ["วางข้อความ (Copy-Paste)", "อัปโหลด Excel"])
    
    df_web = pd.DataFrame()
    if method == "วางข้อความ (Copy-Paste)":
        raw_text = st.text_area("ก๊อปปี้ตารางจากหน้าเว็บมาวาง (วันที่ และ ยอดเงิน):", height=150)
        if raw_text:
            lines = [l.split() for l in raw_text.strip().split('\n')]
            df_web = pd.DataFrame(lines, columns=['Date', 'Amount'])
            df_web['Amount'] = pd.to_numeric(df_web['Amount'].str.replace(',', ''))
    else:
        web_file = st.file_uploader("อัปโหลดไฟล์หลังบ้าน", type=['xlsx', 'csv'])
        if web_file:
            df_web = pd.read_excel(web_file)

# --- ส่วนการคำนวณ ---
if pdf_file and not df_web.empty:
    df_stm = extract_data_from_pdf(pdf_file)
    
    # สร้าง Key สำหรับเทียบ (Date_Amount)
    df_stm['key'] = df_stm['Date'].astype(str) + "_" + df_stm['Amount'].astype(str)
    df_web['key'] = df_web['Date'].astype(str) + "_" + df_web['Amount'].astype(str)
    
    st.divider()
    
    # สรุปยอด
    m1, m2 = st.columns(2)
    m1.metric("รายการใน STM", f"{len(df_stm)} รายการ")
    m2.metric("รายการหลังบ้าน", f"{len(df_web)} รายการ")

    # ตรวจสอบจุดที่ไม่ตรง
    not_in_stm = df_web[~df_web['key'].isin(df_stm['key'])]
    not_in_web = df_stm[~df_stm['key'].isin(df_web['key'])]

    res1, res2 = st.columns(2)
    with res1:
        st.error("❌ มีในเว็บ แต่หาไม่เจอใน STM")
        st.dataframe(not_in_stm[['Date', 'Amount']], use_container_width=True)
    with res2:
        st.warning("⚠️ มีใน STM แต่หาไม่เจอในเว็บ")
        st.dataframe(not_in_web[['Date', 'Amount']], use_container_width=True)