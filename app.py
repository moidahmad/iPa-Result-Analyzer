import streamlit as st
import re
import csv
import io
from collections import defaultdict

# ================== PAGE CONFIG ==================
st.set_page_config(page_title="iPa-Doc Analyzer", layout="wide")

st.markdown("<h1 style='text-align: center; color: #1E293B;'>📊 iPa-Doc Analyzer v1.0</h1>", unsafe_allow_html=True)
st.markdown("---")

uploaded_file = st.file_uploader("Upload Document (CSV or XLSX only)", type=['csv', 'xlsx'])

# ================== PURE PYTHON PARSER (NO PANDAS, NO NUMPY!) ==================
def analyze_marks(headers, rows):
    """Sirf Python lists aur loops se SGPA nikaalo"""
    try:
        # Columns dhoondho
        sem_idx = None
        marks_idx = None
        
        for i, h in enumerate(headers):
            h_lower = str(h).lower()
            if 'sem' in h_lower or 'year' in h_lower:
                sem_idx = i
            if 'mark' in h_lower or 'grade' in h_lower or 'score' in h_lower or 'gpa' in h_lower:
                marks_idx = i
        
        if sem_idx is None or marks_idx is None:
            return None, None, "⚠️ Columns nahi mile. Headers mein 'Semester' aur 'Marks' hona chahiye."
        
        sem_marks = defaultdict(list)
        
        # Har row mein ghoomo
        for row in rows:
            if len(row) <= max(sem_idx, marks_idx):
                continue  # Chhoti row skip karo
                
            sem_val = str(row[sem_idx]).strip()
            mark_val = str(row[marks_idx]).strip()
            
            # Regex se numbers nikaalo
            match = re.search(r'(\d+\.?\d*)', mark_val)
            if match:
                try:
                    num = float(match.group(1))
                    if 0 <= num <= 100:  # Valid marks range
                        sem_marks[sem_val].append(num)
                except ValueError:
                    pass
        
        if not sem_marks:
            return None, None, "❌ Koi valid marks nahi mile. Check karo data format."
        
        # SGPA nikaalo
        sgpa_list = []
        for sem, marks in sem_marks.items():
            avg = sum(marks) / len(marks)
            sgpa = round(avg / 10.0, 2)
            sgpa_list.append([sem, sgpa, len(marks)])  # Semester, SGPA, Subject count
        
        # CGPA
        total_sgpa = sum([item[1] for item in sgpa_list])
        cgpa = round(total_sgpa / len(sgpa_list), 2) if sgpa_list else 0
        
        return sgpa_list, cgpa, "✅ Analysis Complete! (Zero Pandas/NumPy used)"
        
    except Exception as e:
        return None, None, f"🔥 Python error: {e}"

# ================== MAIN LOGIC ==================
if uploaded_file is not None:
    file_name = uploaded_file.name.lower()
    headers = []
    rows = []
    msg = ""
    
    st.info(f"🔍 iPa ne file dekhi: '{uploaded_file.name}'")
    
    with st.spinner("🔄 iPa pure Python engine chal raha hai..."):
        try:
            # ---------- CSV READ (Pure Python) ----------
            if file_name.endswith('.csv'):
                # bytes ko string mein decode karo
                content = uploaded_file.read().decode('utf-8')
                reader = csv.reader(io.StringIO(content))
                headers = next(reader)  # Pehli row header
                rows = list(reader)
                msg = "✅ CSV loaded (Pure Python)"
            
            # ---------- XLSX READ (openpyxl - Pure Python) ----------
            elif file_name.endswith('.xlsx'):
                try:
                    import openpyxl
                    # Bytes ko load karo
                    wb = openpyxl.load_workbook(uploaded_file, data_only=True)
                    sheet = wb.active
                    
                    # Header row (row 1)
                    headers = [cell.value for cell in sheet[1]]
                    
                    # Data rows (row 2 se end tak)
                    rows = []
                    for row in sheet.iter_rows(min_row=2, values_only=True):
                        rows.append(list(row))
                    msg = "✅ Excel loaded (openpyxl)"
                except ImportError:
                    st.error("❌ openpyxl install nahi hai. Install karne ke liye: pip install openpyxl")
                    st.stop()
                except Exception as e:
                    st.error(f"❌ Excel reading error: {e}")
                    st.stop()
            
            else:
                st.error("❌ Sirf CSV aur XLSX allow hai.")
                st.stop()

            # ---------- DISPLAY RAW DATA PREVIEW ----------
            st.subheader("📋 Raw Data Preview")
            if headers:
                st.table([headers] + rows[:5])  # Sirf 5 rows dikhao
            
            # ---------- RUN ANALYSIS ----------
            sgpa_data, cgpa, result_msg = analyze_marks(headers, rows)
            
            if sgpa_data:
                st.success(result_msg)
                col1, col2 = st.columns(2)
                col1.metric("📈 Overall CGPA", f"{cgpa} / 10.0")
                col2.metric("🏆 Semesters Count", f"{len(sgpa_data)}")
                
                st.subheader("📊 Semester-wise SGPA")
                # Table dikhao (100% safe)
                st.table({
                    "Semester": [s[0] for s in sgpa_data],
                    "SGPA": [s[1] for s in sgpa_data],
                    "Subjects": [s[2] for s in sgpa_data]
                })
                
                # Chart try karo (agar fail ho toh chup raho)
                try:
                    chart_data = {s[0]: s[1] for s in sgpa_data}
                    st.bar_chart(chart_data)
                except:
                    st.info("💡 Bar chart render nahi hui (Haider ki limited capacity), lekin table mein numbers hain!")
            else:
                st.warning(result_msg)
                st.info("💡 Tip: Ensure your file has headers like 'Semester', 'Marks'.")
                
        except Exception as e:
            st.error(f"🔥 Haider ruk gaya: {e}")
            st.info("💡 Agar error aaye toh file ko Notepad mein khol kar 'Save As' -> 'UTF-8' karke try karo.")

else:
    st.info("👆 File upload karo, iPa analysis karega!")

st.markdown("---")
st.markdown("<p style='text-align: center; color: grey;'>Built with ❤️ by iPa v4.6 for Moid | Zero Pandas Mode</p>", unsafe_allow_html=True)