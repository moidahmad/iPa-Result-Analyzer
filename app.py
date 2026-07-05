import streamlit as st
import re
import csv
import io
import pandas as pd
from collections import defaultdict
from PIL import Image
import numpy as np

# ===================== ULTIMATE PROFESSIONAL UI (FIXED) =====================
st.set_page_config(page_title="iPa Result Analyzer v6.0", layout="wide", initial_sidebar_state="expanded")

# --- Strong Custom CSS (Navy + Gold + Shadows) ---
st.markdown("""
<style>
    /* Main Background */
    .stApp { background-color: #f1f5f9; }
    
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #0f172a !important;
        padding-top: 2rem;
    }
    section[data-testid="stSidebar"] * {
        color: #e2e8f0 !important;
    }
    section[data-testid="stSidebar"] .stMarkdown h1, 
    section[data-testid="stSidebar"] .stMarkdown h2,
    section[data-testid="stSidebar"] .stMarkdown h3 {
        color: #f59e0b !important;
    }
    
    /* Metric Cards */
    div[data-testid="stMetric"] {
        background-color: #ffffff !important;
        padding: 15px !important;
        border-radius: 16px !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06) !important;
        border-left: 6px solid #f59e0b !important;
    }
    div[data-testid="stMetric"] p {
        color: #1e293b !important;
        font-weight: 600 !important;
    }
    
    /* Dataframes */
    .stDataFrame { border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    
    /* Headers */
    h1, h2, h3 { color: #0f172a !important; font-weight: 700 !important; }
    
    /* Upload Box */
    .stFileUploader { background-color: white; border: 2px dashed #cbd5e1; border-radius: 16px; padding: 20px; }
</style>
""", unsafe_allow_html=True)

st.sidebar.markdown("## 🧠 iPa Analyzer v6.0")
st.sidebar.markdown("---")
st.sidebar.markdown("**Supports:** CSV | Excel | PDF | Images (PNG/JPG)")
st.sidebar.markdown("**Pro-Tip:** Dikhne mein mushkil, par iPa sab sambhal lega!")

uploaded_file = st.file_uploader(
    "Upload Document (CSV, XLSX, PDF, or Image of Marksheet)",
    type=['csv', 'xlsx', 'pdf', 'png', 'jpg', 'jpeg']
)

# ======================== UNIVERSAL PARSER ENGINE (v6.0) ========================

def clean_headers(headers):
    """Duplicate aur empty headers ko handle karo"""
    cleaned = []
    seen = {}
    for h in headers:
        h = str(h).strip()
        if not h or h.lower() == 'nan' or h.lower() == 'none':
            h = "Unknown_Col"
        if h in seen:
            seen[h] += 1
            cleaned.append(f"{h}_{seen[h]}")
        else:
            seen[h] = 0
            cleaned.append(h)
    return cleaned

def normalize_rows(rows, target_cols):
    """Har row mein columns count match karo"""
    norm_rows = []
    for row in rows:
        if len(row) < target_cols:
            row = list(row) + [''] * (target_cols - len(row))
        elif len(row) > target_cols:
            row = row[:target_cols]
        norm_rows.append(row)
    return norm_rows

def smart_parse_v6(headers, rows):
    """Auto-detect: MBA Transcript, Final Result, Semester, B.Tech Memo, ya Unknown"""
    try:
        headers_lower = [str(h).lower().strip() for h in headers]
        all_data = " ".join([" ".join(map(str, r)) for r in rows]).lower()
        
        # --- 1. MBA TRANSCRIPT (SPI/CPI) ---
        if any('spi' in h for h in headers_lower) or any('cpi' in h for h in headers_lower):
            st.info("📄 **MBA Transcript** detected (SPI/CPI).")
            # Index mapping
            name_idx = next((i for i, h in enumerate(headers_lower) if 'student' in h or 'name' in h), None)
            spi_idx = next((i for i, h in enumerate(headers_lower) if 'spi' in h), None)
            cpi_idx = next((i for i, h in enumerate(headers_lower) if 'cpi' in h), None)
            result_idx = next((i for i, h in enumerate(headers_lower) if 'result' in h), None)
            
            spis, cpis, results, names = [], [], [], []
            for row in rows:
                if name_idx is not None and len(row) > name_idx: names.append(str(row[name_idx]).strip())
                if spi_idx is not None and len(row) > spi_idx:
                    m = re.search(r'(\d+\.?\d*)', str(row[spi_idx]))
                    if m: spis.append(float(m.group(1)))
                if cpi_idx is not None and len(row) > cpi_idx:
                    m = re.search(r'(\d+\.?\d*)', str(row[cpi_idx]))
                    if m: cpis.append(float(m.group(1)))
                if result_idx is not None and len(row) > result_idx: results.append(str(row[result_idx]).strip().upper())
            
            avg_spi = sum(spis)/len(spis) if spis else 0
            avg_cpi = sum(cpis)/len(cpis) if cpis else 0
            pass_count = sum(1 for r in results if 'PASS' in r) if results else 0
            return {"type": "transcript", "avg_spi": round(avg_spi,2), "avg_cpi": round(avg_cpi,2), 
                    "pass": pass_count, "fail": len(results)-pass_count, "toppers": names[:3]}

        # --- 2. MBA FINAL RESULT (Rank, Grand Total, SGPA) ---
        elif any('rank' in h for h in headers_lower) and any('grand total' in h for h in headers_lower):
            st.info("📊 **MBA Final Result** detected.")
            sgpa_idx = next((i for i, h in enumerate(headers_lower) if 'sgpa' in h), None)
            total_idx = next((i for i, h in enumerate(headers_lower) if 'grand total' in h or 'total' in h), None)
            name_idx = next((i for i, h in enumerate(headers_lower) if 'student' in h or 'name' in h), None)
            
            sgpas, totals, names = [], [], []
            for row in rows:
                if name_idx is not None and len(row) > name_idx: names.append(str(row[name_idx]).strip())
                if sgpa_idx is not None and len(row) > sgpa_idx:
                    m = re.search(r'(\d+\.?\d*)', str(row[sgpa_idx]))
                    if m: sgpas.append(float(m.group(1)))
                if total_idx is not None and len(row) > total_idx:
                    m = re.search(r'(\d+\.?\d*)', str(row[total_idx]))
                    if m: totals.append(float(m.group(1)))
            
            avg_sgpa = sum(sgpas)/len(sgpas) if sgpas else 0
            return {"type": "result", "cgpa": round(avg_sgpa,2), "total": len(sgpas), 
                    "avg_total": round(sum(totals)/len(totals),2) if totals else 0, "toppers": names[:3]}

        # --- 3. B.Tech Consolidated Memo (SL No, SUBJECTS, MAX, OBTAINED) ---
        elif any('sl no' in h for h in headers_lower) or any('subjects' in h for h in headers_lower) or any('maximum marks' in h for h in headers_lower):
            st.info("📘 **B.Tech Consolidated Memo** detected.")
            sem_idx = None
            marks_idx = None
            # Try to find semester column or just group by sequential rows
            # Let's extract marks
            marks_list = []
            sem_count = 0
            current_sem = 1
            for row in rows:
                row_str = ' '.join(map(str, row)).lower()
                if 'semester' in row_str or 'i – semester' in row_str or 'ii – semester' in row_str:
                    sem_count += 1
                    current_sem = sem_count
                    continue
                # Find marks: look for a number between 0-100 in the row that isn't the sl no
                nums = re.findall(r'\b(\d{1,3})\b', ' '.join(map(str, row)))
                nums = [int(n) for n in nums if 0 <= int(n) <= 100]
                if nums and len(nums) >= 1:
                    # Usually the last number is the obtained marks
                    marks_list.append(current_sem)
                    # We'll just store raw numbers to calculate avg per sem
                    
            st.warning("⚠️ B.Tech Consolidated Memo is complex! iPa will display the raw structured table below. For semester calculation, ensure 'Semester' and 'Marks' columns are explicit.")
            return {"type": "btech_raw", "data": rows}

        # --- 4. SEMESTER MARKSHEET (Semester, Subject, Marks) ---
        elif any('sem' in h for h in headers_lower) and any('mark' in h or 'subject' in h for h in headers_lower):
            st.info("📚 **Semester Marksheet** detected.")
            sem_idx = next((i for i, h in enumerate(headers_lower) if 'sem' in h), None)
            marks_idx = next((i for i, h in enumerate(headers_lower) if 'mark' in h or 'score' in h), None)
            
            sem_marks = defaultdict(list)
            for row in rows:
                if sem_idx is not None and marks_idx is not None and len(row) > max(sem_idx, marks_idx):
                    sem_val = str(row[sem_idx]).strip()
                    m = re.search(r'(\d+\.?\d*)', str(row[marks_idx]))
                    if m: sem_marks[sem_val].append(float(m.group(1)))
            
            sgpa_data = []
            for sem, marks in sem_marks.items():
                avg = sum(marks)/len(marks)
                sgpa_data.append([sem, round(avg/10.0, 2), len(marks)])
            if sgpa_data:
                cgpa = round(sum(s[1] for s in sgpa_data)/len(sgpa_data), 2)
                return {"type": "semester", "cgpa": cgpa, "sgpa_data": sgpa_data}

        # --- 5. UNKNOWN (Raw display) ---
        else:
            return {"type": "unknown", "msg": "Data read, but iPa couldn't auto-detect structure. Displaying raw table."}
    except Exception as e:
        return {"type": "error", "msg": str(e)}

# ======================== MAIN LOGIC ========================
if uploaded_file is not None:
    file_name = uploaded_file.name.lower()
    headers = []
    rows = []
    
    with st.spinner("🔄 iPa v6.0 analyzing... (Mujhe kuch nahi rok sakta!)"):
        try:
            # ---- 1. CSV ----
            if file_name.endswith('.csv'):
                content = uploaded_file.read().decode('utf-8')
                reader = csv.reader(io.StringIO(content))
                headers = clean_headers(next(reader))
                raw_rows = list(reader)
                rows = normalize_rows(raw_rows, len(headers))
                st.success("✅ CSV Loaded!")
            
            # ---- 2. EXCEL ----
            elif file_name.endswith('.xlsx'):
                import openpyxl
                wb = openpyxl.load_workbook(uploaded_file, data_only=True)
                sheet = wb.active
                headers = clean_headers([cell.value for cell in sheet[1]])
                raw_rows = []
                for row in sheet.iter_rows(min_row=2, values_only=True):
                    raw_rows.append(list(row))
                rows = normalize_rows(raw_rows, len(headers))
                st.success("✅ Excel Loaded!")
            
            # ---- 3. PDF (Fixed duplicate & merged cell issue) ----
            elif file_name.endswith('.pdf'):
                try:
                    import pdfplumber
                    with pdfplumber.open(uploaded_file) as pdf:
                        all_rows = []
                        for page in pdf.pages:
                            table = page.extract_table()
                            if table:
                                if not headers:
                                    headers = clean_headers(table[0])
                                    all_rows.extend(table[1:])
                                else:
                                    # If headers already set, just add rows (normalized later)
                                    all_rows.extend(table[1:])
                        # If no table found via extract_table, do a smart text split
                        if not all_rows:
                            text = ""
                            for page in pdf.pages:
                                text += page.extract_text() or ""
                            lines = [line.split() for line in text.split('\n') if line.strip()]
                            # Try to find the header line
                            header_keywords = ['rank', 'roll', 'name', 'spi', 'cpi', 'result', 'subjects']
                            header_idx = -1
                            for i, line in enumerate(lines):
                                line_lower = ' '.join(line).lower()
                                if any(k in line_lower for k in header_keywords) and len(line) > 4:
                                    header_idx = i
                                    break
                            if header_idx != -1:
                                headers = clean_headers(lines[header_idx])
                                all_rows = lines[header_idx+1:]
                            else:
                                # Extreme fallback: treat first 2 rows as header?
                                if len(lines) > 1:
                                    headers = clean_headers(lines[0])
                                    all_rows = lines[1:]
                                else:
                                    headers = ['Raw_Data']
                                    all_rows = lines
                        
                        # Normalize rows to match header count
                        rows = normalize_rows(all_rows, len(headers))
                    st.success("✅ PDF Loaded (Merged cells handled)!")
                except ImportError:
                    st.error("❌ pdfplumber missing.")
                    st.stop()
            
            # ---- 4. IMAGE (Fixed Column Mismatch) ----
            elif file_name.endswith(('png', 'jpg', 'jpeg')):
                try:
                    import pytesseract
                    image = Image.open(uploaded_file)
                    text = pytesseract.image_to_string(image)
                    lines = [line.split() for line in text.split('\n') if line.strip()]
                    
                    if lines:
                        # Find best header row
                        header_keywords = ['rank', 'roll', 'name', 'spi', 'cpi', 'result', 'sem', 'mark', 'subjects', 'sl no']
                        header_idx = -1
                        for i, line in enumerate(lines):
                            line_lower = ' '.join(line).lower()
                            if any(k in line_lower for k in header_keywords) and len(line) > 3:
                                header_idx = i
                                break
                        if header_idx != -1:
                            # Use the detected header
                            raw_headers = lines[header_idx]
                            # Remove header if it appears in rows (clean up)
                            cleaned_lines = []
                            for line in lines[header_idx+1:]:
                                if ' '.join(line) != ' '.join(raw_headers):
                                    cleaned_lines.append(line)
                            headers = clean_headers(raw_headers)
                            rows = normalize_rows(cleaned_lines, len(headers))
                            st.success("✅ Image OCR Successful!")
                        else:
                            # Fallback: treat first row as header
                            if lines:
                                headers = clean_headers(lines[0])
                                rows = normalize_rows(lines[1:], len(headers))
                                st.success("✅ OCR Done (Auto-detected header).")
                            else:
                                st.error("❌ No text extracted.")
                                st.stop()
                    else:
                        st.error("❌ No text found in image.")
                        st.stop()
                except ImportError:
                    st.error("❌ pytesseract missing. Please install.")
                    st.stop()
            
            else:
                st.error("❌ Unsupported format")
                st.stop()

            # ---- RAW DATA PREVIEW (ALL ROWS, SCROLLABLE) ----
            st.subheader("📋 Raw Data Preview")
            if headers and rows:
                df_display = pd.DataFrame(rows, columns=headers)
                st.dataframe(df_display, use_container_width=True, height=400)

            # ---- RUN SMART ANALYSIS v6.0 ----
            result = smart_parse_v6(headers, rows)
            
            if result and result.get("type") == "transcript":
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("📈 Avg SPI", result['avg_spi']); c2.metric("📊 Avg CPI", result['avg_cpi'])
                c3.metric("✅ Pass", result['pass']); c4.metric("❌ Fail", result['fail'])
                if result.get('toppers'): st.success(f"🏆 Top 3: {', '.join(result['toppers'])}")
                
            elif result and result.get("type") == "result":
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("📈 CGPA", f"{result['cgpa']}/10"); c2.metric("👨‍🎓 Total", result['total'])
                c3.metric("📊 Avg Total", result['avg_total'])
                if result.get('toppers'): c4.metric("🥇 Toppers", ", ".join(result['toppers'])[:20]+"...")
                
            elif result and result.get("type") == "semester":
                c1, c2 = st.columns(2)
                c1.metric("📈 CGPA", f"{result['cgpa']}/10"); c2.metric("📚 Semesters", len(result['sgpa_data']))
                
                st.subheader("📊 Semester-wise SGPA")
                sgpa_data = result['sgpa_data']
                # FIXED TABLE: Proper mapping
                display_df = pd.DataFrame({
                    "Semester": [s[0] for s in sgpa_data],
                    "SGPA": [s[1] for s in sgpa_data],
                    "Subjects": [s[2] for s in sgpa_data]
                })
                st.table(display_df)
                
                # FIXED CHART: Use numeric values
                try:
                    chart_df = pd.DataFrame({
                        "Semester": [s[0] for s in sgpa_data],
                        "SGPA": [s[1] for s in sgpa_data]
                    }).set_index("Semester")
                    st.bar_chart(chart_df)
                except Exception as chart_e:
                    st.info(f"💡 Chart render issue: {chart_e}, but table above shows the SGPA!")
                    
            elif result and result.get("type") == "btech_raw":
                st.info("📘 B.Tech Memo detected. Showing structured table. For automated SGPA, please ensure 'Semester' and 'Marks' columns exist.")
                st.dataframe(pd.DataFrame(rows, columns=headers), use_container_width=True)
                
            elif result and result.get("type") == "unknown":
                st.warning(f"⚠️ {result.get('msg', 'Unknown format')}")
                st.info("💡 Tip: Ensure columns like 'SPI/CPI', 'Semester/Marks', or 'Rank/Total/SGPA' exist in the first row.")
            elif result and result.get("type") == "error":
                st.error(f"🔥 Analysis Error: {result.get('msg')}")

        except Exception as e:
            st.error(f"🔥 Engine Error: {e}")
            st.info("💡 Copy this error and send to iPa. I'll debug it right away!")

else:
    st.info("👆 Upload your document or image!")

st.markdown("---")
st.markdown("<p style='text-align: center; color: #64748b;'>Built with ❤️ by iPa v6.0 | The Survivor Edition</p>", unsafe_allow_html=True)
