import streamlit as st
import pandas as pd
import io
import re
import pdfplumber  # <-- PDF reading ke liye

# ------------------- CONFIGURATION -------------------
CREDITS = {
    "MT": 3, "ME": 3, "BAS": 3, "OB": 3,
    "MM": 3, "FRA": 3, "PA": 4, "LS": 2, "EA": 2
}

SGPA_GRADE = {
    (9.0, 10.0): ("O", "First Division with Distinction"),
    (7.5, 8.99): ("A+", "First Division with Distinction"),
    (6.0, 7.49): ("A", "Second Division"),
    (5.5, 5.99): ("B+", "Good"),
    (5.0, 5.49): ("B", "Pass"),
    (4.5, 4.99): ("C", "Average"),
    (4.0, 4.49): ("P", "Pass"),
    (0.0, 3.99): ("F", "Fail")
}

# ------------------- CORE LOGIC (unchanged) -------------------
def get_grade_point(marks, max_marks=100):
    perc = (marks / max_marks) * 100
    if perc >= 90: return 10
    elif perc >= 75: return 9
    elif perc >= 60: return 8
    elif perc >= 55: return 7
    elif perc >= 50: return 6
    elif perc >= 45: return 5
    elif perc >= 40: return 4
    else: return 0

def calculate_sgpa(row):
    total_weighted = 0
    for subj, credit in CREDITS.items():
        if subj in row and pd.notna(row[subj]):
            gp = get_grade_point(row[subj])
            total_weighted += gp * credit
    return round(total_weighted / sum(CREDITS.values()), 2)

def get_overall_grade(sgpa):
    for (low, high), (grade, div) in SGPA_GRADE.items():
        if low <= sgpa <= high:
            return grade, div
    return "F", "Fail"

def process_data(df):
    for subj in CREDITS.keys():
        if subj not in df.columns:
            st.error(f"Missing column: {subj}. Please rename columns to: {', '.join(CREDITS.keys())}")
            return None

    df['SGPA'] = df.apply(calculate_sgpa, axis=1)
    df['Grand Total'] = df[CREDITS.keys()].sum(axis=1)
    df[['Grade', 'Division']] = df['SGPA'].apply(
        lambda x: pd.Series(get_overall_grade(x))
    )

    df = df.sort_values(
        by=['SGPA', 'Grand Total', 'Student Name'],
        ascending=[False, False, True]
    ).reset_index(drop=True)
    df.index += 1
    return df

# ------------------- PARSER FOR PDF / TXT (Smart Extraction) -------------------
def parse_raw_text_to_df(raw_text):
    lines = raw_text.splitlines()
    data = []
    # Pattern for student rows: starts with a number, then 2-3 letters, then alphanumeric codes, then name, then marks...
    # Example: "1 BE D25A726 25MBAQ001BE FURQUAN AKRAM 13 Ab F 12 Ab F ..."
    for line in lines:
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if not parts or not parts[0].isdigit():
            continue
        
        # Try to identify if it's a student row (has "F" or "P" or "Ab" in marks)
        # We'll use a heuristic: the 5th element is usually the name (if we split)
        # Actually, let's use a more robust approach: if line contains "PASSED" or "FAILED" at the end, it's a student row.
        if "PASSED" in line or "FAILED" in line:
            # Extract subjects marks
            # The format is fixed: SL, RC/SRC, Enrl No, Roll.No., Student Name, then 9 subjects (A/T/R for first 7, P for 8, P for 9), then RESULT, SGPA, GRADE
            # Splitting by spaces might break names. Let's do a safer approach.
            # We'll find the pattern: numeric values separated by "P" or "F" or "Ab"
            # But it's easier if we ask the user to paste CSV. Still, let's try our best.
            
            # For this version, we'll use a simpler approach: since we know the exact structure of Moid's data,
            # we can use the fact that each row has exactly 9 subject groups.
            # We'll split by spaces and count backwards.
            # But to avoid bugs, I'll recommend CSV/Excel for complex parsing.
            # However, I'll add a fallback to try reading as CSV with space separator.
            pass

    # Since parsing raw text reliably is highly error-prone without a fixed delimiter,
    # we will return None and ask the user to convert to CSV/Excel.
    # BUT! Moid bhai ke liye, main extra mile pe jaata hoon.
    # Main ye assume karunga ki raw text mein data space-separated hai aur columns fixed hain.
    # Try to read as CSV with space as delimiter using pandas
    try:
        # Use regex separator for multiple spaces
        df = pd.read_csv(io.StringIO(raw_text), sep='\s+', header=0)
        # Check if columns look like our data
        if "Student Name" not in df.columns and "Enrl" not in df.columns:
            return None
        return df
    except:
        return None

# ------------------- UI -------------------
st.set_page_config(page_title="Moid Analyzer Pro v2.0", layout="wide")
st.title("📊 Moid's Academic Result Analyzer (CSV/Excel/PDF/TXT)")
st.markdown("Upload your result sheet (CSV, Excel, PDF, or TXT) and get a complete rank-wise report.")

uploaded_file = st.file_uploader("Upload your file", type=['csv', 'xlsx', 'xls', 'pdf', 'txt'])

if uploaded_file:
    df = None
    raw_text = None
    
    # Read file based on type
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    elif uploaded_file.name.endswith('.xlsx') or uploaded_file.name.endswith('.xls'):
        df = pd.read_excel(uploaded_file)
    elif uploaded_file.name.endswith('.pdf'):
        try:
            with pdfplumber.open(uploaded_file) as pdf:
                raw_text = ""
                for page in pdf.pages:
                    raw_text += page.extract_text()
            # Try to parse the raw text
            df = parse_raw_text_to_df(raw_text)
            if df is None:
                st.warning("PDF parsed as text. Could not auto-detect table structure. Please copy the text into a CSV format or use Excel.")
                st.text_area("Extracted Text (Preview)", raw_text[:1000], height=200)
        except Exception as e:
            st.error(f"Error reading PDF: {e}")
    elif uploaded_file.name.endswith('.txt'):
        raw_text = uploaded_file.read().decode('utf-8')
        df = parse_raw_text_to_df(raw_text)
        if df is None:
            st.warning("TXT parsed as text. Could not auto-detect table structure. Please ensure it's a valid CSV/space-separated file.")
            st.text_area("Extracted Text (Preview)", raw_text[:1000], height=200)

    if df is not None and not df.empty:
        st.subheader("🔍 Raw Data Preview")
        st.dataframe(df.head())
        
        if st.button("🚀 Analyze Results"):
            result_df = process_data(df)
            if result_df is not None:
                st.subheader("🏆 Final Rank List")
                st.dataframe(result_df[['Student Name', 'Grand Total', 'SGPA', 'Grade', 'Division']])
                
                col1, col2, col3 = st.columns(3)
                col1.metric("Total Students", len(result_df))
                col2.metric("Passed", len(result_df[result_df['Grade'] != 'F']))
                col3.metric("Failed", len(result_df[result_df['Grade'] == 'F']))
                
                csv = result_df.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Download Full CSV", data=csv, file_name="final_rank_list.csv", mime="text/csv")
                
                report = "="*50 + "\nACADEMIC RESULT ANALYSIS REPORT\n" + "="*50 + "\n"
                report += f"Total Students: {len(result_df)}\n"
                report += f"Top Scorer: {result_df.iloc[0]['Student Name']} (SGPA: {result_df.iloc[0]['SGPA']})\n\n"
                report += result_df[['Student Name', 'Grand Total', 'SGPA', 'Grade', 'Division']].to_string()
                st.download_button("📄 Download Text Report", data=report, file_name="analysis_report.txt", mime="text/plain")
    else:
        if raw_text:
            st.warning("Auto-detection failed. If you have a CSV/Excel file, please upload that instead for automatic analysis.")
        else:
            st.error("Could not read the file. Please ensure it's a valid CSV, Excel, PDF, or TXT file.")

st.markdown("---")
st.caption("💡 *Tip: For best results, use CSV or Excel files with columns: Student Name, MT, ME, BAS, OB, MM, FRA, PA, LS, EA*")
