import streamlit as st
import pandas as pd
import re

st.title("🚀 เครื่องมือตรวจสอบยอดหลังบ้าน (Arom168)")

# ส่วนนี้คือ Magic Box ที่รับข้อมูลได้ไม่จำกัด
raw_text = st.text_area("👉 ก๊อปข้อมูลจากหลังบ้านหน้า 1, 2, 3... มาวางต่อกันที่นี่ได้เลย:", height=300)

if st.button("🔍 ตรวจสอบและดึงข้อมูลทั้งหมด"):
    if raw_text:
        # ใช้ Regex "ขั้นเทพ" เพื่อดึงข้อมูล 3 ส่วน: [วัน-เวลา] [เลขบัญชี] [ยอดเงิน]
        # ไม่ว่าข้อความจะติดอะไรมา Regex นี้จะเจาะจงเฉพาะข้อมูลที่เราต้องการเท่านั้น
        pattern = r'(\d{2}-\d{2}-\d{4}\s\d{2}:\d{2}:\d{2}).*?(\d{10}).*?(-?[\d,]+\.\d{2})'
        matches = re.findall(pattern, raw_text, re.DOTALL)
        
        if matches:
            # สร้างตารางข้อมูล
            df_web = pd.DataFrame(matches, columns=['วัน-เวลา', 'เลขบัญชี', 'ยอดเงิน'])
            
            # ล้างค่าซ้ำ (กรณีคนใช้งานเผลอก๊อปหน้าเดิมมาวางซ้ำ)
            df_web = df_web.drop_duplicates().reset_index(drop=True)
            
            st.success(f"✅ สำเร็จ! ดึงข้อมูลมาได้ทั้งหมด {len(df_web)} รายการ")
            st.dataframe(df_web, use_container_width=True)
            
            # เก็บข้อมูลลง Session ไว้ไปเทียบกับ PDF ต่อ
            st.session_state.final_web_data = df_web
        else:
            st.error("❌ ไม่พบข้อมูลธุรกรรม กรุณาก๊อปปี้จากหน้าเว็บมาใหม่ (ลอง Ctrl+A ในหน้าตาราง)")

# ส่วนอัปโหลด PDF เพื่อเทียบยอด (ใส่โค้ด Matching เดิมของคุณได้เลย)
