import streamlit as st
import re
import pandas as pd
from collections import defaultdict
import io

# ===================== ULTRA PROFESSIONAL UI =====================
st.set_page_config(page_title="iPa Result Analyzer v6.6", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    .stApp { background-color: #f1f5f9; }
    section[data-testid="stSidebar"] { background-color: #0f172a !important; padding-top: 2rem; }
    section[data-testid="stSidebar"] * { color: #e2e8f0 !important; }
    section[data-testid="stSidebar"] .stMarkdown h1, section[data-testid="stSidebar"] .stMarkdown h2 { color: #f59e0b !important; }
    div[data-testid="stMetric"] { background-color: #ffffff !important; padding: 15px !important; border-radius: 16px !important; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1) !important; border-left: 6px solid #f59e0b !important; }
    div[data-testid="stMetric"] p { color: #1e293b !important; font-weight: 600 !important; }
    h1, h2, h3 { color: #0f172a !important; font-weight: 700 !important; }
    .stFileUploader { background-color: white; border: 2px dashed #cbd5e1; border-radius: 16px; padding: 20px; }
</style>
""", unsafe_allow_html=True)

st.sidebar.markdown("## 🧠 iPa Analyzer v6.6")
st.sidebar.markdown("---")
st.sidebar.markdown("**UGC Exact Rules**")
st.sidebar.markdown("- Grade mapping fixed (A+ starts at 7.5)")
st.sidebar.markdown("- Tie-breaker: Alphabetical (A-Z)")

uploaded_file = st.file_uploader(
    "Upload Document (TXT, PDF, Image, CSV)",
    type=['csv', 'xlsx', 'pdf', 'png', 'jpg', 'jpeg', 'txt']
)

# ======================== EXACT UGC PARSER ========================

def parse_mba_odl(text):
    lines = text.split('\n')
    data = []
    
    for line in lines:
        parts = line.split()
        if len(parts) < 20:
            continue
            
        # 1. FIND RESULT (PASSED / FAILED)
        try:
            res_idx = parts.index('PASSED') if 'PASSED' in parts else parts.index('FAILED')
        except ValueError:
            continue
        
        # 2. FIND SUBJECT START (First numeric token or 'Ab' after index 3)
        sub_start = -1
        for i in range(4, res_idx):
            token = parts[i]
            if token.isdigit() or token == 'Ab':
                sub_start = i
                break
        
        if sub_start == -1:
            continue
        
        # 3. EXTRACT BASIC INFO
        sl = parts[0]
        rc = parts[1]
        enrl = parts[2]
        roll = parts[3]
        
        # 4. EXTRACT STUDENT NAME
        name_tokens = parts[4:sub_start]
        name = ' '.join(name_tokens)
        
        # 5. EXTRACT SUBJECT TOKENS (Exactly 25 tokens for 9 subjects)
        subject_tokens = parts[sub_start:res_idx]
        if len(subject_tokens) < 25:
            continue
        
        total = 0
        
        # Subjects 1 to 7 (Each has A, T, R)
        for i in range(7):
            a_str = subject_tokens[i*3]
            t_str = subject_tokens[i*3 + 1]
            a = float(re.sub(r'[^0-9.]', '', a_str)) if a_str.replace('.','',1).isdigit() or a_str.isdigit() else 0
            t = float(re.sub(r'[^0-9.]', '', t_str)) if t_str.replace('.','',1).isdigit() or t_str.isdigit() else 0
            total += a + t
        
        # Subject 8 (P8, R8)
        p8_str = subject_tokens[21]
        p8 = float(re.sub(r'[^0-9.]', '', p8_str)) if p8_str.replace('.','',1).isdigit() or p8_str.isdigit() else 0
        total += p8
        
        # Subject 9 (P9, R9)
        p9_str = subject_tokens[23]
        p9 = float(re.sub(r'[^0-9.]', '', p9_str)) if p9_str.replace('.','',1).isdigit() or p9_str.isdigit() else 0
        total += p9
        
        # 6. CHECK FAILURE
        result = parts[res_idx]
        is_fail = False
        for i in range(7):
            r_token = subject_tokens[i*3 + 2]
            if 'F' in r_token or 'Ab' in r_token:
                is_fail = True
                break
        if 'F' in subject_tokens[22] or 'F' in subject_tokens[24] or 'Ab' in subject_tokens[22] or 'Ab' in subject_tokens[24]:
            is_fail = True
        
        final_result = 'PASSED' if (result == 'PASSED' and not is_fail) else 'FAILED'
        
        # 7. CALCULATE SGPA (DIVISOR = 718)
        sgpa = round((total / 718) * 10, 2) if total > 0 else 0.0
        
        # 8. 🔥 EXACT GRADE MAPPING (As per your table)
        if sgpa >= 9.0: grade = 'O'
        elif sgpa >= 7.5: grade = 'A+'   # <-- Fixed! 75% to 89.99%
        elif sgpa >= 6.0: grade = 'A'
        elif sgpa >= 5.5: grade = 'B+'
        elif sgpa >= 5.0: grade = 'B'
        elif sgpa >= 4.5: grade = 'C'
        elif sgpa >= 4.0: grade = 'P'
        else: grade = 'F'
        
        data.append({
            "SL": sl,
            "RC/SRC": rc,
            "Enrl No": enrl,
            "Roll No": roll,
            "Student Name": name,
            "Total": int(total),
            "SGPA": sgpa,
            "Grade": grade,
            "Result": final_result
        })
    
    if not data:
        return pd.DataFrame()
    
    df = pd.DataFrame(data)
    
    # 9. 🔥 TIE-BREAKER (Exact UGC Rule)
    # Sort by SGPA Desc, Total Desc, then Student Name Ascending (A-Z)
    df = df.sort_values(by=['SGPA', 'Total', 'Student Name'], ascending=[False, False, True])
    df['Rank'] = range(1, len(df) + 1)
    df = df[['Rank', 'SL', 'Student Name', 'Roll No', 'Total', 'SGPA', 'Grade', 'Result']]
    return df

# ======================== MAIN ENGINE ========================

if uploaded_file is not None:
    file_name = uploaded_file.name.lower()
    df_result = pd.DataFrame()
    
    with st.spinner("🔄 iPa v6.6 analyzing with Exact UGC rules..."):
        try:
            if file_name.endswith('.txt'):
                content = uploaded_file.read().decode('utf-8')
                df_result = parse_mba_odl(content)
                st.success("✅ Raw Text Data Parsed Successfully!")
            
            elif file_name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
                if len(df.columns) > 15:
                    txt_buffer = io.StringIO()
                    df.to_csv(txt_buffer, index=False, header=False)
                    df_result = parse_mba_odl(txt_buffer.getvalue())
                else:
                    df_result = df
            
            elif file_name.endswith('.xlsx'):
                import openpyxl
                df = pd.read_excel(uploaded_file)
                st.warning("⚠️ Excel uploaded. Please upload raw .txt file for best results.")
                df_result = df
            
            elif file_name.endswith(('pdf', 'png', 'jpg', 'jpeg')):
                text = ""
                if file_name.endswith('.pdf'):
                    try:
                        import pdfplumber
                        with pdfplumber.open(uploaded_file) as pdf:
                            for page in pdf.pages:
                                text += page.extract_text() or ""
                    except ImportError:
                        st.error("❌ pdfplumber not installed.")
                        st.stop()
                else:
                    try:
                        import pytesseract
                        from PIL import Image
                        image = Image.open(uploaded_file)
                        text = pytesseract.image_to_string(image)
                    except ImportError:
                        st.error("❌ pytesseract not installed.")
                        st.stop()
                
                if text:
                    df_result = parse_mba_odl(text)
                    st.success("✅ OCR/PDF Data Parsed Successfully!")
                else:
                    st.error("❌ No text extracted from the document.")
                    st.stop()
            else:
                st.error("❌ Unsupported format")
                st.stop()

            # ---- DISPLAY RESULTS ----
            if not df_result.empty:
                st.subheader("📊 Final Ranked Result (UGC Rules)")
                
                total_students = len(df_result)
                avg_sgpa = df_result['SGPA'].mean()
                pass_count = df_result[df_result['Result'] == 'PASSED'].shape[0]
                fail_count = total_students - pass_count
                
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("👨‍🎓 Total Students", total_students)
                col2.metric("📈 Batch Avg SGPA", f"{avg_sgpa:.2f}/10")
                col3.metric("✅ Passed", pass_count)
                col4.metric("❌ Failed", fail_count)
                
                st.markdown("---")
                
                # Top 3 Toppers (With Names & Correct Grade!)
                st.subheader("🏆 Top 3 Toppers")
                top3 = df_result.head(3)
                for idx, row in top3.iterrows():
                    st.markdown(f"**Rank {row['Rank']}:** {row['Student Name']} | SGPA: {row['SGPA']} | Total: {row['Total']} | Grade: {row['Grade']}")
                
                st.markdown("---")
                
                # Full Data Table
                st.subheader("📋 Complete Ranked List")
                display_df = df_result.copy()
                display_df.index = range(1, len(display_df) + 1)
                st.dataframe(display_df.style.hide(axis='index'), use_container_width=True, height=500)
                
            else:
                st.warning("⚠️ No valid data found. Please ensure the file contains the MBA ODL format.")

        except Exception as e:
            st.error(f"🔥 Engine Error: {e}")
            st.info("💡 If you have raw text, paste it into a .txt file and upload.")

else:
    st.info("👆 Upload your MBA ODL Result data.")

st.markdown("---")
st.markdown("<p style='text-align: center; color: #64748b;'>Built with ❤️ by iPa v6.6 | Exact UGC Grades & Tie-Breaker</p>", unsafe_allow_html=True)
