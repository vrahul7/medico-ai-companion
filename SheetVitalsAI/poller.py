import os
import time
import pandas as pd
import google.generativeai as genai
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# Configuration
INPUT_DIR = "analysis_input"
OUTPUT_DIR = "analysis_output"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-1.5-flash")

def process_file(file_path):
    try:
        print(f"Processing: {file_path}")
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)
        
        filename = os.path.basename(file_path)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = os.path.join(OUTPUT_DIR, f"Report_{filename}_{timestamp}.md")

        stats = df.describe(include='all').to_string()
        cols = list(df.columns)
        
        ai_insight = "AI Analysis skipped or failed (check API Key)."
        if GEMINI_API_KEY:
            try:
                # Try multiple model names as fallbacks
                models_to_try = ["gemini-1.5-flash", "gemini-pro"]
                response = None
                for model_name in models_to_try:
                    try:
                        temp_model = genai.GenerativeModel(model_name)
                        prompt = f"""
                        You are a Clinical Data Analyst. Analyze this dataset summary and provide a professional clinical breakdown.
                        Format as:
                        ### Dataset Summary
                        ### Key Clinical Trends
                        ### Anomalies/Outliers
                        
                        Data:
                        Filename: {filename}
                        Columns: {cols}
                        Stats Summary:
                        {stats}
                        """
                        response = temp_model.generate_content(prompt)
                        if response:
                            ai_insight = response.text
                            break
                    except Exception as e:
                        print(f"Model {model_name} failed: {e}")
            except Exception as e:
                ai_insight = f"AI Synthesis failed: {str(e)}"

        with open(report_path, "w", encoding="utf-8") as f:
            f.write(f"# Clinical Analysis Report: {filename}\n")
            f.write(f"**Processed At:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"## Raw Stats (Deterministic)\n")
            f.write(f"```\n{stats}\n```\n\n")
            f.write(f"## AI Clinical Insight\n")
            f.write(f"{ai_insight}\n")

        print(f"Analysis complete: {report_path}")
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    if not os.path.exists(INPUT_DIR): os.makedirs(INPUT_DIR)
    if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)

    print("SheetVitals Poller started. Monitoring 'analysis_input'...")
    processed_files = set()

    while True:
        files = [f for f in os.listdir(INPUT_DIR) if f.endswith(('.xlsx', '.xls', '.csv'))]
        for f in files:
            if f not in processed_files:
                process_file(os.path.join(INPUT_DIR, f))
                processed_files.add(f)
        
        time.sleep(2)
