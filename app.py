import streamlit as st
import pandas as pd
import pdfplumber
import re

st.set_page_config(page_title="STM Matcher Pro", layout="wide")

st.title("📊 ระบบเทียบยอดบัญชี STM vs หลังบ้าน")
st.info("คำแนะนำ: อัปโหลด PDF ธนาคาร และก๊อปปี้ข้อมูลหน้าเว็บทั้งหมดมาวางได้เลย")

# --- ฟังก์ชันอ่าน PDF STM ---
def extract_data_from_pdf(file):
    temp_data = []
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                # มองหาวันที่ และ ยอดเงินที่มีจุดทศนิยม
                matches = re.findall(r'(\d{2}/\d{2}/\d{2,4}).*?([\d,]+\.\d{2})', text)
                for m in matches:
                    temp_data.append({
                        "Date": m[0], 
                        "Amount": float(m[1].replace(',', ''))
                    })
    return pd.DataFrame(temp_data)

# --- ฟังก์ชันอ่านข้อมูลหลังบ้าน (เวอร์ชันอัปเกรดเพื่อรองรับข้อความแอดมิน) ---
def parse_backend_text(raw_text):
    extracted_data = []
    # แยกเป็นกลุ่มรายการ (หนึ่งรายการมักเริ่มด้วย วันที่)
    items = re.split(r'(\d{2}-\d{2}-\d{4})', raw_text)
    
    # วนลูปเช็กทีละกลุ่ม (วันที่ + ข้อมูลที่ตามมา)
    for i in range(1, len(items), 2):
        date_str = items[i]
        content = items[i+1]
        
        # ค้นหาตัวเลขยอดเงิน (มองหาตัวเลขที่มีจุดทศนิยม 2 ตำแหน่ง)
        # เราจะเอาเฉพาะตัวเลขตัวแรกที่เจอหลังจากวันที่ เพราะตัวที่สองมักจะเป็นยอดคงเหลือ (Balance)
        amounts = re.findall(r'(-?[\d,]+\.\d{2})', content)
        
        if amounts:
            val = float(amounts[0].replace(',', ''))
            # จัด format วันที่ให้เป็น DD/MM/YY เพื่อให้ตรงกับ STM
            clean_date = date_str.replace('-', '/')
            if len(clean_date) > 8: # ถ้าเป็น 2026 ให้เหลือ 26
                clean_date = clean_date[:6] + clean_date[-2:]
            
            extracted_data.append({
                "Date": clean_date,
                "Amount": val
            })
            
    return pd.DataFrame(extracted_data)

# --- ส่วน UI ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("1. ฝั่งธนาคาร (PDF)")
    pdf_file = st.file_uploader("ลากไฟล์ PDF STM วางที่นี่", type=['pdf'])

with col2:
    st.subheader("2. ฝั่งหลังบ้านเว็บ")
    raw_input = st.text_area("ก๊อปปี้ตารางหน้าเว็บมาวางทั้งหมดได้เลย:", height=250, placeholder="วางข้อมูลที่มีวันที่ ยอดเงิน และบอทจับคู่สำเร็จ...")

# --- ส่วนการคำนวณ ---
if pdf_file and raw_input:
    with st.spinner('กำลังประมวลผล...'):
        df_stm = extract_data_from_pdf(pdf_file)
        df_web = parse_backend_text(raw_input)
        
        if df_stm.empty or df_web.empty:
            st.error("❌ ไม่พบข้อมูลที่ดึงได้ โปรดตรวจสอบว่าไฟล์ PDF หรือข้อความที่วางมี 'วันที่' และ 'ยอดเงิน' หรือไม่")
        else:
            # สร้าง Key สำหรับเทียบ (Date_Amount)
            df_stm['key'] = df_stm['Date'] + "_" + df_stm['Amount'].map('{:.2f}'.format)
            df_web['key'] = df_web['Date'] + "_" + df_web['Amount'].map('{:.2f}'.format)
            
            st.divider()
            
            # สรุปภาพรวม
            m1, m2, m3 = st.columns(3)
            m1.metric("รายการใน STM", f"{len(df_stm)} รายการ")
            m2.metric("รายการหลังบ้าน", f"{len(df_web)} รายการ")
            
            diff_count = len(df_web) - len(df_stm)
            m3.metric("ส่วนต่าง", f"{diff_count} รายการ", delta_color="inverse" if diff_count != 0 else "normal")

            # ตรวจสอบจุดที่ไม่ตรง
            not_in_stm = df_web[~df_web['key'].isin(df_stm['key'])]
            not_in_web = df_stm[~df_stm['key'].isin(df_web['key'])]

            res1, res2 = st.columns(2)
            with res1:
                st.error(f"❌ มีในเว็บ แต่ไม่มีใน STM ({len(not_in_stm)} ยอด)")
                st.dataframe(not_in_stm[['Date', 'Amount']], use_container_width=True)
            with res2:
                st.warning(f"⚠️ มีใน STM แต่ไม่มีในเว็บ ({len(not_in_web)} ยอด)")
                st.dataframe(not_in_web[['Date', 'Amount']], use_container_width=True)
                
            st.success("เปรียบเทียบข้อมูลเรียบร้อยแล้ว!")
