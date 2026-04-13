import streamlit as st
import pandas as pd
import pdfplumber
import re

st.set_page_config(page_title="STM Matcher", layout="wide")

st.title("📊 ระบบเทียบยอดบัญชี STM vs หลังบ้าน")
st.info("วิธีใช้: อัปโหลด PDF ธนาคาร และก๊อปปี้ข้อมูลหน้าเว็บมาวางได้เลย")

# --- ฟังก์ชันอ่าน PDF ---
def extract_data_from_pdf(file):
    temp_data = []
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                # มองหาวันที่ (DD/MM/YY หรือ DD/MM/YYYY) และตัวเลขยอดเงิน
                matches = re.findall(r'(\d{2}/\d{2}/\d{2,4}).*?([\d,]+\.\d{2})', text)
                for m in matches:
                    temp_data.append({"Date": m[0], "Amount": float(m[1].replace(',', ''))})
    return pd.DataFrame(temp_data)

# --- ฟังก์ชันอ่าน Text ที่ก๊อปมาวาง (แบบยืดหยุ่น) ---
def parse_web_text(raw_text):
    data = []
    lines = raw_text.strip().split('\n')
    for line in lines:
        # ใช้ Regex ค้นหาตัวเลขที่มีจุดทศนิยม 2 ตำแหน่งในบรรทัดนั้นๆ
        amounts = re.findall(r'([\d,]+\.\d{2})', line)
        # ใช้ Regex ค้นหาวันที่
        dates = re.findall(r'(\d{2}[-/]\d{2}[-/]\d{2,4})', line)
        
        if amounts and dates:
            data.append({
                "Date": dates[0].replace('-', '/'), # ปรับ format ให้ใช้ / เหมือนกัน
                "Amount": float(amounts[0].replace(',', ''))
            })
    return pd.DataFrame(data)

# --- ส่วน UI ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("1. ฝั่งธนาคาร (PDF)")
    pdf_file = st.file_uploader("ลากไฟล์ PDF STM วางที่นี่", type=['pdf'])

with col2:
    st.subheader("2. ฝั่งหลังบ้านเว็บ")
    raw_text = st.text_area("ก๊อปปี้ตารางจากหน้าเว็บมาวาง (วางมาทั้งหน้าได้เลย):", height=150)

# --- ส่วนการคำนวณ ---
if pdf_file and raw_text:
    df_stm = extract_data_from_pdf(pdf_file)
    df_web = parse_web_text(raw_text)
    
    if df_stm.empty or df_web.empty:
        st.warning("⚠️ ตรวจสอบข้อมูล: ระบบยังดึงวันที่หรือยอดเงินออกมาไม่ได้ ลองตรวจสอบรูปแบบข้อความที่วางครับ")
    else:
        # สร้าง Key สำหรับเทียบ (Date_Amount)
        df_stm['key'] = df_stm['Date'].astype(str).str[-8:] + "_" + df_stm['Amount'].map('{:.2f}'.format)
        df_web['key'] = df_web['Date'].astype(str).str[-8:] + "_" + df_web['Amount'].map('{:.2f}'.format)
        
        st.divider()
        m1, m2 = st.columns(2)
        m1.metric("พบรายการใน STM", f"{len(df_stm)} รายการ")
        m2.metric("พบรายการหลังบ้าน", f"{len(df_web)} รายการ")

        not_in_stm = df_web[~df_web['key'].isin(df_stm['key'])]
        not_in_web = df_stm[~df_stm['key'].isin(df_web['key'])]

        res1, res2 = st.columns(2)
        with res1:
            st.error(f"❌ มีในเว็บ แต่ไม่มีใน STM ({len(not_in_stm)})")
            st.dataframe(not_in_stm[['Date', 'Amount']], use_container_width=True)
        with res2:
            st.warning(f"⚠️ มีใน STM แต่ไม่มีในเว็บ ({len(not_in_web)})")
            st.dataframe(not_in_web[['Date', 'Amount']], use_container_width=True)
