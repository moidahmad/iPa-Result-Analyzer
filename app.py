import streamlit as st
import re
import pandas as pd
from collections import defaultdict
import io

# ===================== ULTRA PROFESSIONAL UI =====================
st.set_page_config(page_title="iPa Result Analyzer v6.7", layout="wide", initial_sidebar_state="expanded")

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

st.sidebar.markdown("## 🧠 iPa Analyzer v6.7")
st.sidebar.markdown("---")
st.sidebar.markdown("**Credit-Based SGPA (26 Credits)**")
st.sidebar.markdown("- Subjects 1-7: out of 100")
st.sidebar.markdown("- LS & EA: out of 50")

uploaded_file = st.file_uploader(
    "Upload Document (TXT, PDF, Image, CSV)",
    type=['csv', 'xlsx', 'pdf', 'png', 'jpg', 'jpeg', 'txt']
)

# ======================== CREDIT-BASED PARSER ========================

def parse_mba_odl(text):
    lines = text.split('\n')
    data = []
    
    # Credit structure (as per MANUU MBA ODL)
    credits = [3, 3, 3, 3, 3, 3, 4, 2, 2]
    total_credits = sum(credits)  # 26
    
    for line in lines:
        parts = line.split()
        if len(parts) < 20:
            continue
            
        # 1. FIND RESULT
        try:
            res_idx = parts.index('PASSED') if 'PASSED' in parts else parts.index('FAILED')
        except ValueError:
            continue
        
        # 2. FIND SUBJECT START
        sub_start = -1
        for i in range(4, res_idx):
            token = parts[i]
            if token.isdigit() or token == 'Ab':
                sub_start = i
                break
        
        if sub_start == -1:
            continue
        
        # 3. BASIC INFO
        sl = parts[0]
        rc = parts[1]
        enrl = parts[2]
        roll = parts[3]
        
        # 4. NAME
        name_tokens = parts[4:sub_start]
        name = ' '.join(name_tokens)
        
        # 5. SUBJECT TOKENS (Exactly 25 tokens)
        subject_tokens = parts[sub_start:res_idx]
        if len(subject_tokens) < 25:
            continue
        
        # 6. EXTRACT RAW MARKS
        # Subjects 1 to 7 (A, T, R)
        a_vals = []
        t_vals = []
        r_vals = []
        for i in range(7):
            a_str = subject_tokens[i*3]
            t_str = subject_tokens[i*3 + 1]
            r_str = subject_tokens[i*3 + 2]
            a = float(re.sub(r'[^0-9.]', '', a_str)) if a_str.replace('.','',1).isdigit() or a_str.isdigit() else 0
            t = float(re.sub(r'[^0-9.]', '', t_str)) if t_str.replace('.','',1).isdigit() or t_str.isdigit() else 0
            a_vals.append(a)
            t_vals.append(t)
            r_vals.append(r_str)
        
        # Subject 8 (P8, R8)
        p8 = float(re.sub(r'[^0-9.]', '', subject_tokens[21])) if subject_tokens[21].replace('.','',1).isdigit() or subject_tokens[21].isdigit() else 0
        r8 = subject_tokens[22]
        
        # Subject 9 (P9, R9)
        p9 = float(re.sub(r'[^0-9.]', '', subject_tokens[23])) if subject_tokens[23].replace('.','',1).isdigit() or subject_tokens[23].isdigit() else 0
        r9 = subject_tokens[24]
        
        # 7. CHECK FAILURE
        is_fail = False
        for r in r_vals:
            if 'F' in r or 'Ab' in r:
                is_fail = True
                break
        if 'F' in r8 or 'F' in r9 or 'Ab' in r8 or 'Ab' in r9:
            is_fail = True
        
        final_result = 'PASSED' if (parts[res_idx] == 'PASSED' and not is_fail) else 'FAILED'
        
        # 8. CALCULATE GRADE POINTS & WEIGHTED SUM (CREDIT BASED)
        weighted_sum = 0
        raw_total = 0
        subject_details = []
        
        # Subjects 1 to 7 (Out of 100)
        for i in range(7):
            marks = a_vals[i] + t_vals[i]
            raw_total += marks
            pct = marks  # Already out of 100
            
            # Grade Point Mapping
            if pct >= 90: gp = 10
            elif pct >= 75: gp = 9
            elif pct >= 60: gp = 8
            elif pct >= 55: gp = 7
            elif pct >= 50: gp = 6
            elif pct >= 45: gp = 5
            elif pct >= 40: gp = 4
            else: gp = 0
            
            weighted_sum += gp * credits[i]
        
        # Subject 8 (LS) (Out of 50)
        raw_total += p8
        pct_ls = (p8 / 50) * 100
        if pct_ls >= 90: gp_ls = 10
        elif pct_ls >= 75: gp_ls = 9
        elif pct_ls >= 60: gp_ls = 8
        elif pct_ls >= 55: gp_ls = 7
        elif pct_ls >= 50: gp_ls = 6
        elif pct_ls >= 45: gp_ls = 5
        elif pct_ls >= 40: gp_ls = 4
        else: gp_ls = 0
        weighted_sum += gp_ls * credits[7]
        
        # Subject 9 (EA) (Out of 50)
        raw_total += p9
        pct_ea = (p9 / 50) * 100
        if pct_ea >= 90: gp_ea = 10
        elif pct_ea >= 75: gp_ea = 9
        elif pct_ea >= 60: gp_ea = 8
        elif pct_ea >= 55: gp_ea = 7
        elif pct_ea >= 50: gp_ea = 6
        elif pct_ea >= 45: gp_ea = 5
        elif pct_ea >= 40: gp_ea = 4
        else: gp_ea = 0
        weighted_sum += gp_ea * credits[8]
        
        # SGPA = Weighted Sum / Total Credits (26)
        sgpa = round(weighted_sum / total_credits, 2)
        
        # 9. GRADE AS PER SGPA RANGE (Exact as image)
        if sgpa >= 9.0: grade = 'O'
        elif sgpa >= 7.5: grade = 'A+'
        elif sgpa >= 6.0: grade = 'A'
        elif sgpa >= 5.5: grade = 'B+'
        elif sgpa >= 5.0: grade = 'B'
        elif sgpa >= 4.5: grade = 'C'
        elif sgpa >= 4.0: grade = 'D'
        else: grade = 'F'
        
        data.append({
            "SL": sl,
            "RC/SRC": rc,
            "Enrl No": enrl,
            "Roll No": roll,
            "Student Name": name,
            "Total": int(raw_total),
            "SGPA": sgpa,
            "Grade": grade,
            "Result": final_result
        })
    
    if not data:
        return pd.DataFrame()
    
    df = pd.DataFrame(data)
    
    # --- TIE-BREAKER (Exact UGC Rule) ---
    df = df.sort_values(by=['SGPA', 'Total', 'Student Name'], ascending=[False, False, True])
    df['Rank'] = range(1, len(df) + 1)
    df = df[['Rank', 'SL', 'Student Name', 'Roll No', 'Total', 'SGPA', 'Grade', 'Result']]
    return df

# ======================== MAIN ENGINE ========================

if uploaded_file is not None:
    file_name = uploaded_file.name.lower()
    df_result = pd.DataFrame()
    
    with st.spinner("🔄 iPa v6.7 calculating credit-based SGPA..."):
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
                    st.error("❌ No text extracted.")
                    st.stop()
            else:
                st.error("❌ Unsupported format")
                st.stop()

            # ---- DISPLAY RESULTS ----
            if not df_result.empty:
                st.subheader("📊 Final Ranked Result (Credit-Based UGC Rule)")
                
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
                
                # Top 3 Toppers
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
st.markdown("<p style='text-align: center; color: #64748b;'>Built with ❤️ by iPa v6.7 | Credit-Based SGPA (26 Credits)</p>", unsafe_allow_html=True)
