import streamlit as st
import re
import pandas as pd
from collections import defaultdict

# ===================== ULTRA PROFESSIONAL UI =====================
st.set_page_config(page_title="iPa Result Analyzer v6.4", layout="wide", initial_sidebar_state="expanded")

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

st.sidebar.markdown("## 🧠 iPa Analyzer v6.4")
st.sidebar.markdown("---")
st.sidebar.markdown("**UGC Rule + Tie-Breaker Enabled**")

uploaded_file = st.file_uploader(
    "Upload Document (CSV, XLSX, PDF, Image, or TXT containing MBA ODL Data)",
    type=['csv', 'xlsx', 'pdf', 'png', 'jpg', 'jpeg', 'txt']
)

# ======================== CORE PARSER (UGC RULE) ========================

def parse_mba_odl_text(text):
    """Parse the specific 9-subject MBA ODL format with UGC rules."""
    lines = text.split('\n')
    data = []
    
    for line in lines:
        parts = line.split()
        if len(parts) < 20:  # Minimum valid row
            continue
            
        # Find Result column (PASSED or FAILED)
        try:
            idx_res = parts.index('PASSED') if 'PASSED' in parts else parts.index('FAILED')
        except ValueError:
            continue
        
        # Basic Info
        sl = parts[0]
        rc = parts[1]
        enrl = parts[2]
        roll = parts[3]
        
        # Result & Grade
        result = parts[idx_res]
        sgpa_str = parts[idx_res + 1] if idx_res + 1 < len(parts) else '-'
        grade = parts[idx_res + 2] if idx_res + 2 < len(parts) else '-'
        
        # Name tokens (between roll number and subject 1)
        # We know exactly 25 tokens are for 9 subjects (7*3 + 2*2 = 25)
        name_tokens = parts[4 : idx_res - 25]
        name = ' '.join(name_tokens)
        
        # Extract subjects from the end (backward indexing)
        try:
            # Subject 9: P9, R9
            p9 = float(re.sub(r'[^0-9.]', '', parts[idx_res - 2])) if parts[idx_res - 2].replace('.','',1).isdigit() else 0
            r9 = parts[idx_res - 1]
            
            # Subject 8: P8, R8
            p8 = float(re.sub(r'[^0-9.]', '', parts[idx_res - 4])) if parts[idx_res - 4].replace('.','',1).isdigit() else 0
            r8 = parts[idx_res - 3]
            
            # Subject 7 to 1: A, T, R
            a7 = float(re.sub(r'[^0-9.]', '', parts[idx_res - 7])) if parts[idx_res - 7].replace('.','',1).isdigit() else 0
            t7 = float(re.sub(r'[^0-9.]', '', parts[idx_res - 6])) if parts[idx_res - 6].replace('.','',1).isdigit() else 0
            r7 = parts[idx_res - 5]
            
            a6 = float(re.sub(r'[^0-9.]', '', parts[idx_res - 10])) if parts[idx_res - 10].replace('.','',1).isdigit() else 0
            t6 = float(re.sub(r'[^0-9.]', '', parts[idx_res - 9])) if parts[idx_res - 9].replace('.','',1).isdigit() else 0
            r6 = parts[idx_res - 8]
            
            a5 = float(re.sub(r'[^0-9.]', '', parts[idx_res - 13])) if parts[idx_res - 13].replace('.','',1).isdigit() else 0
            t5 = float(re.sub(r'[^0-9.]', '', parts[idx_res - 12])) if parts[idx_res - 12].replace('.','',1).isdigit() else 0
            r5 = parts[idx_res - 11]
            
            a4 = float(re.sub(r'[^0-9.]', '', parts[idx_res - 16])) if parts[idx_res - 16].replace('.','',1).isdigit() else 0
            t4 = float(re.sub(r'[^0-9.]', '', parts[idx_res - 15])) if parts[idx_res - 15].replace('.','',1).isdigit() else 0
            r4 = parts[idx_res - 14]
            
            a3 = float(re.sub(r'[^0-9.]', '', parts[idx_res - 19])) if parts[idx_res - 19].replace('.','',1).isdigit() else 0
            t3 = float(re.sub(r'[^0-9.]', '', parts[idx_res - 18])) if parts[idx_res - 18].replace('.','',1).isdigit() else 0
            r3 = parts[idx_res - 17]
            
            a2 = float(re.sub(r'[^0-9.]', '', parts[idx_res - 22])) if parts[idx_res - 22].replace('.','',1).isdigit() else 0
            t2 = float(re.sub(r'[^0-9.]', '', parts[idx_res - 21])) if parts[idx_res - 21].replace('.','',1).isdigit() else 0
            r2 = parts[idx_res - 20]
            
            a1 = float(re.sub(r'[^0-9.]', '', parts[idx_res - 25])) if parts[idx_res - 25].replace('.','',1).isdigit() else 0
            t1 = float(re.sub(r'[^0-9.]', '', parts[idx_res - 24])) if parts[idx_res - 24].replace('.','',1).isdigit() else 0
            r1 = parts[idx_res - 23]
            
        except (ValueError, IndexError):
            continue
        
        # Calculate Total Marks
        total = a1+t1 + a2+t2 + a3+t3 + a4+t4 + a5+t5 + a6+t6 + a7+t7 + p8 + p9
        
        # Check Failures
        if 'F' in [r1, r2, r3, r4, r5, r6, r7, r8, r9] or result == 'FAILED':
            final_result = 'FAILED'
            # For failed, SGPA calculation still works for records, but we can keep passed calculation
        else:
            final_result = 'PASSED'
        
        # UGC SGPA Rule (Max Marks = 720)
        sgpa = round((total / 720) * 10, 2) if total > 0 else 0.0
        
        data.append({
            "SL": sl,
            "RC/SRC": rc,
            "Enrl No": enrl,
            "Roll No": roll,
            "Student Name": name,
            "Total": total,
            "SGPA": sgpa,
            "Result": final_result,
            "Grade": grade if grade != '-' else ('O' if sgpa >= 9.0 else 'A+' if sgpa >= 8.5 else 'A' if sgpa >= 8.0 else 'B+' if sgpa >= 7.5 else 'B' if sgpa >= 7.0 else 'C' if sgpa >= 6.0 else 'P' if sgpa >= 5.0 else 'F')
        })
    
    if not data:
        return pd.DataFrame()
    
    df = pd.DataFrame(data)
    
    # --- TIE-BREAKER RULE (UGC Standard) ---
    # 1. Sort by SGPA (Desc), then Total (Desc)
    df = df.sort_values(by=['SGPA', 'Total'], ascending=[False, False])
    
    # 2. Assign Rank
    df['Rank'] = range(1, len(df) + 1)
    
    # Re-arrange columns for display
    df = df[['Rank', 'SL', 'Student Name', 'Roll No', 'Total', 'SGPA', 'Grade', 'Result']]
    return df

# ======================== MAIN ENGINE ========================

if uploaded_file is not None:
    file_name = uploaded_file.name.lower()
    df_result = pd.DataFrame()
    
    with st.spinner("🔄 iPa v6.4 analyzing with UGC rules..."):
        try:
            # ---- 1. TEXT / TXT / Raw Data ----
            if file_name.endswith('.txt'):
                content = uploaded_file.read().decode('utf-8')
                df_result = parse_mba_odl_text(content)
                st.success("✅ Raw Text Data Parsed Successfully!")
            
            # ---- 2. CSV / EXCEL (if user uploads structured) ----
            elif file_name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
                # Check if it's the raw wide format (like 9 subjects) or already final
                if len(df.columns) > 15:
                    # We expect our parse function to handle, but let's use the raw text logic by converting to text
                    # Simpler: Just read as is and try to map if columns match
                    # But since user provided raw text, they will likely upload .txt
                    st.warning("⚠️ CSV uploaded. If it contains raw data, please paste as .txt file. Displaying raw CSV.")
                    df_result = df
                else:
                    df_result = df
            
            elif file_name.endswith('.xlsx'):
                import openpyxl
                df = pd.read_excel(uploaded_file)
                st.warning("⚠️ Excel uploaded. If it contains raw data, please paste as .txt file. Displaying raw Excel.")
                df_result = df
            
            # ---- 3. PDF / IMAGE (OCR and then Parse) ----
            elif file_name.endswith(('pdf', 'png', 'jpg', 'jpeg')):
                try:
                    text = ""
                    if file_name.endswith('.pdf'):
                        import pdfplumber
                        with pdfplumber.open(uploaded_file) as pdf:
                            for page in pdf.pages:
                                text += page.extract_text() or ""
                    else:
                        import pytesseract
                        from PIL import Image
                        image = Image.open(uploaded_file)
                        text = pytesseract.image_to_string(image)
                    
                    df_result = parse_mba_odl_text(text)
                    if not df_result.empty:
                        st.success("✅ OCR/PDF Data Parsed Successfully!")
                    else:
                        st.error("❌ Could not extract data from PDF/Image. Please upload raw text or CSV.")
                        st.stop()
                except ImportError:
                    st.error("❌ Required libraries missing for PDF/Image parsing. Please upload raw .txt file.")
                    st.stop()
            
            else:
                st.error("❌ Unsupported format")
                st.stop()

            # ---- DISPLAY RESULTS (UGC + Tie-Breaker) ----
            if not df_result.empty:
                st.subheader("📊 Final Ranked Result (UGC Rule + Tie-Breaker)")
                
                # Metrics
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
                # FIX: Hide the ugly blue index
                display_df = df_result.copy()
                display_df.index = range(1, len(display_df) + 1)
                st.dataframe(display_df.style.hide(axis='index'), use_container_width=True, height=500)
                
            else:
                st.warning("⚠️ No data found. Please ensure the file contains valid MBA ODL result data.")

        except Exception as e:
            st.error(f"🔥 Engine Error: {e}")
            st.info("💡 Try saving the raw text data in a `.txt` file and uploading it.")

else:
    st.info("👆 Upload your MBA ODL Result data (TXT, CSV, PDF, or Image).")

st.markdown("---")
st.markdown("<p style='text-align: center; color: #64748b;'>Built with ❤️ by iPa v6.4 | UGC Rules + Tie-Breaker</p>", unsafe_allow_html=True)
