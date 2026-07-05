import streamlit as st
import re
import csv
import io
import pandas as pd
from collections import defaultdict
from PIL import Image

# ================== ULTRA PROFESSIONAL UI ==================
st.set_page_config(page_title="iPa Result Analyzer", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    .main { background-color: #f8fafc; }
    .stApp { background-color: #f8fafc; }
    .css-1d391kg { background-color: #0f172a; }
    .st-bb { background-color: #ffffff; border-radius: 12px; padding: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    h1 { color: #0f172a !important; font-weight: 700 !important; }
    .gold-text { color: #f59e0b; }
    div[data-testid="stMetricValue"] { font-size: 2rem !important; font-weight: 700 !important; color: #0f172a !important; }
</style>
""", unsafe_allow_html=True)

st.sidebar.markdown("## 🧠 iPa Analyzer v5.0 (Final)")
st.sidebar.markdown("---")
st.sidebar.markdown("**CSV | Excel | PDF | Image (PNG/JPG)**")

uploaded_file = st.file_uploader(
    "Upload Document (CSV, XLSX, PDF, or Image of Marksheet)",
    type=['csv', 'xlsx', 'pdf', 'png', 'jpg', 'jpeg']
)

# ================== UNIVERSAL SMART PARSER ==================
def smart_parse(headers, rows):
    """Auto-detect: Semester, MBA Result, or MBA Transcript (SPI/CPI)"""
    try:
        headers_lower = [str(h).lower().strip() for h in headers]
        
        # ---- MBA Transcript (SPI/CPI) ----
        if any('spi' in h for h in headers_lower) or any('cpi' in h for h in headers_lower):
            st.info("📄 **MBA Transcript** detected! Computing SPI/CPI.")
            rank_idx = name_idx = spi_idx = cpi_idx = result_idx = None
            for i, h in enumerate(headers_lower):
                if 'rank' in h: rank_idx = i
                if 'student' in h or 'name' in h: name_idx = i
                if 'spi' in h: spi_idx = i
                if 'cpi' in h: cpi_idx = i
                if 'result' in h: result_idx = i
            
            names, spis, cpis, results = [], [], [], []
            for row in rows:
                if name_idx is not None and len(row) > name_idx: names.append(str(row[name_idx]).strip())
                if spi_idx is not None and len(row) > spi_idx:
                    match = re.search(r'(\d+\.?\d*)', str(row[spi_idx]))
                    if match:
                        try: spis.append(float(match.group(1)))
                        except: pass
                if cpi_idx is not None and len(row) > cpi_idx:
                    match = re.search(r'(\d+\.?\d*)', str(row[cpi_idx]))
                    if match:
                        try: cpis.append(float(match.group(1)))
                        except: pass
                if result_idx is not None and len(row) > result_idx:
                    results.append(str(row[result_idx]).strip().upper())
            
            avg_spi = sum(spis)/len(spis) if spis else 0
            avg_cpi = sum(cpis)/len(cpis) if cpis else 0
            pass_count = sum(1 for r in results if 'PASS' in r) if results else 0
            fail_count = len(results) - pass_count if results else 0
            toppers = names[:3] if names else []
            
            return {"type": "mba_transcript", "total_students": len(spis), "avg_spi": round(avg_spi, 2), "avg_cpi": round(avg_cpi, 2), "pass_count": pass_count, "fail_count": fail_count, "toppers": toppers}
        
        # ---- MBA Final Result (SGPA) ----
        elif any('rank' in h for h in headers_lower) and any('grand total' in h for h in headers_lower):
            st.info("📊 **MBA Final Result** detected!")
            sgpa_list, total_marks, names = [], [], []
            name_idx = sgpa_idx = total_idx = None
            for i, h in enumerate(headers_lower):
                if 'student' in h or 'name' in h: name_idx = i
                if 'sgpa' in h: sgpa_idx = i
                if 'grand total' in h or 'total' in h: total_idx = i
            
            for row in rows:
                if name_idx is not None and len(row) > name_idx: names.append(str(row[name_idx]).strip())
                if sgpa_idx is not None and len(row) > sgpa_idx:
                    match = re.search(r'(\d+\.?\d*)', str(row[sgpa_idx]))
                    if match:
                        try: sgpa_list.append(float(match.group(1)))
                        except: pass
                if total_idx is not None and len(row) > total_idx:
                    match = re.search(r'(\d+\.?\d*)', str(row[total_idx]))
                    if match:
                        try: total_marks.append(float(match.group(1)))
                        except: pass
            
            avg_sgpa = sum(sgpa_list)/len(sgpa_list) if sgpa_list else 0
            avg_total = sum(total_marks)/len(total_marks) if total_marks else 0
            toppers = names[:3] if names else []
            return {"type": "mba_result", "cgpa": round(avg_sgpa, 2), "total_students": len(sgpa_list), "avg_total": round(avg_total, 2), "toppers": toppers}
        
        # ---- Semester Marksheet (Semester, Subject, Marks) ----
        elif any('sem' in h for h in headers_lower) and any('mark' in h or 'subject' in h for h in headers_lower):
            st.info("📊 **Semester Marksheet** detected!")
            sem_idx = marks_idx = None
            for i, h in enumerate(headers_lower):
                if 'sem' in h: sem_idx = i
                if 'mark' in h or 'score' in h: marks_idx = i
            
            sem_marks = defaultdict(list)
            for row in rows:
                if len(row) <= max(sem_idx, marks_idx): continue
                sem_val = str(row[sem_idx]).strip()
                match = re.search(r'(\d+\.?\d*)', str(row[marks_idx]))
                if match:
                    try:
                        num = float(match.group(1))
                        if 0 <= num <= 100: sem_marks[sem_val].append(num)
                    except: pass
            
            sgpa_data = []
            for sem, marks in sem_marks.items():
                avg = sum(marks) / len(marks)
                sgpa = round(avg / 10.0, 2)
                sgpa_data.append([sem, sgpa, len(marks)])
            if not sgpa_data: return {"type": "unknown"}
            total_sgpa = sum([s[1] for s in sgpa_data])
            cgpa = round(total_sgpa / len(sgpa_data), 2)
            return {"type": "semester", "cgpa": cgpa, "sgpa_data": sgpa_data}
        else:
            return {"type": "unknown"}
    except Exception as e:
        return {"type": "error", "msg": str(e)}

# ================== MAIN ENGINE ==================
if uploaded_file is not None:
    file_name = uploaded_file.name.lower()
    headers = []
    rows = []
    
    with st.spinner("🔄 iPa is processing..."):
        try:
            # ---- 1. CSV ----
            if file_name.endswith('.csv'):
                content = uploaded_file.read().decode('utf-8')
                reader = csv.reader(io.StringIO(content))
                headers = next(reader)
                rows = list(reader)
                st.success("✅ CSV Loaded!")
            
            # ---- 2. EXCEL ----
            elif file_name.endswith('.xlsx'):
                import openpyxl
                wb = openpyxl.load_workbook(uploaded_file, data_only=True)
                sheet = wb.active
                headers = [cell.value for cell in sheet[1]]
                for row in sheet.iter_rows(min_row=2, values_only=True):
                    rows.append(list(row))
                st.success("✅ Excel Loaded!")
            
            # ---- 3. PDF ----
            elif file_name.endswith('.pdf'):
                try:
                    import pdfplumber
                    with pdfplumber.open(uploaded_file) as pdf:
                        for page in pdf.pages:
                            table = page.extract_table()
                            if table and len(table) > 1:
                                headers = table[0]; rows = table[1:]; break
                        if not rows:
                            all_text = ""
                            for page in pdf.pages: all_text += page.extract_text() or ""
                            lines = [line.split() for line in all_text.split('\n') if line.strip()]
                            # Auto-find header row
                            header_keywords = ['rank', 'roll', 'name', 'spi', 'cpi', 'result']
                            header_idx = -1
                            for i, line in enumerate(lines):
                                line_lower = ' '.join(line).lower()
                                if any(k in line_lower for k in header_keywords) and len(line) > 5:
                                    header_idx = i; break
                            if header_idx != -1:
                                headers = lines[header_idx]; rows = lines[header_idx+1:]
                            else:
                                headers = ['Raw_Text']; rows = [line for line in all_text.split('\n') if line.strip()]
                    st.success("✅ PDF Loaded!")
                except ImportError:
                    st.error("❌ pdfplumber missing. Please check requirements.")
                    st.stop()
            
            # ---- 4. IMAGE (PNG/JPG) - FINALLY ADDED! ----
            elif file_name.endswith(('png', 'jpg', 'jpeg')):
                try:
                    import pytesseract
                    image = Image.open(uploaded_file)
                    # Preprocess: grayscale for better OCR
                    gray = image.convert('L')
                    # Extract text
                    text = pytesseract.image_to_string(gray)
                    lines = [line.split() for line in text.split('\n') if line.strip()]
                    
                    if lines:
                        # Find header row
                        header_keywords = ['rank', 'roll', 'name', 'spi', 'cpi', 'result', 'sem', 'mark']
                        header_idx = -1
                        for i, line in enumerate(lines):
                            line_lower = ' '.join(line).lower()
                            if any(k in line_lower for k in header_keywords) and len(line) > 3:
                                header_idx = i; break
                        if header_idx != -1:
                            headers = lines[header_idx]
                            rows = lines[header_idx+1:]
                            st.success("✅ Image OCR successful! Text extracted.")
                        else:
                            # Fallback: treat first line as header
                            headers = ['Extracted_Text']
                            rows = [line for line in lines]
                            st.warning("⚠️ OCR done, but could not auto-detect columns. Displaying raw text.")
                    else:
                        st.error("❌ No text found in image. Please upload a clearer image.")
                        st.stop()
                except ImportError:
                    st.error("❌ pytesseract missing. Please install pytesseract and ensure tesseract-ocr is installed (via packages.txt).")
                    st.stop()
                except Exception as e:
                    st.error(f"❌ OCR Error: {e}")
                    st.stop()
            
            else:
                st.error("❌ Unsupported format")
                st.stop()

            # ---- RAW DATA PREVIEW (ALL ROWS) ----
            st.subheader("📋 Raw Data Preview")
            if headers and rows:
                df_display = pd.DataFrame(rows, columns=headers)
                st.dataframe(df_display, use_container_width=True, height=350)
            
            # ---- RUN ANALYSIS ----
            result = smart_parse(headers, rows)
            
            if result and result.get("type") == "mba_transcript":
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("📈 Avg SPI", result['avg_spi']); c2.metric("📊 Avg CPI", result['avg_cpi'])
                c3.metric("✅ Pass", result['pass_count']); c4.metric("❌ Fail", result['fail_count'])
                st.success(f"🏆 Top 3: {', '.join(result['toppers'])}")
                
            elif result and result.get("type") == "mba_result":
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("📈 CGPA", f"{result['cgpa']}/10"); c2.metric("👨‍🎓 Total", result['total_students'])
                c3.metric("📊 Avg Total", result['avg_total']); c4.metric("🥇 Toppers", ", ".join(result['toppers']) if result['toppers'] else "N/A")
                
            elif result and result.get("type") == "semester":
                c1, c2 = st.columns(2)
                c1.metric("📈 CGPA", f"{result['cgpa']}/10"); c2.metric("📚 Semesters", len(result['sgpa_data']))
                st.subheader("📊 Semester SGPA")
                sgpa = result['sgpa_data']
                st.table({"Semester": [s[0] for s in sgpa], "SGPA": [s[1] for s in sgpa], "Subjects": [s[2] for s in sgpa]})
                try: st.bar_chart({s[0]: s[1] for s in sgpa})
                except: pass
                
            elif result and result.get("type") == "unknown":
                st.warning("⚠️ iPa read data but couldn't find standard columns.")
            elif result and result.get("type") == "error":
                st.error(f"🔥 Error: {result.get('msg')}")

        except Exception as e:
            st.error(f"🔥 Engine Error: {e}")

else:
    st.info("👆 Upload MBA PDF, Image, or CSV to start!")

st.markdown("---")
st.markdown("<p style='text-align: center; color: #64748b;'>Built with ❤️ by iPa v5.0 | Final Production Version</p>", unsafe_allow_html=True)
