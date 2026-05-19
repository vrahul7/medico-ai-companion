import os
import time
import pandas as pd
import google.generativeai as genai
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
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

class ClinicalDataHandler(FileSystemEventHandler):
    def on_created(self, event):
        self._handle_event(event)

    def on_modified(self, event):
        self._handle_event(event)

    def on_moved(self, event):
        self._handle_event(event)

    def _handle_event(self, event):
        dest_path = getattr(event, 'dest_path', event.src_path)
        if not event.is_directory and dest_path.endswith(('.xlsx', '.xls', '.csv')):
            print(f"File event detected: {dest_path}")
            # Prevent duplicate processing by checking if it's already being handled
            # (Simple debouncing)
            if hasattr(self, '_last_processed') and self._last_processed == dest_path:
                return
            self._last_processed = dest_path
            self.process_file(dest_path)

    def process_file(self, file_path):
        try:
            # 1. Deterministic Extraction
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path)
            
            filename = os.path.basename(file_path)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_path = os.path.join(OUTPUT_DIR, f"Report_{filename}_{timestamp}.md")

            # 2. Stats Calculation
            stats = df.describe(include='all').to_string()
            cols = list(df.columns)
            
            # 3. AI Synthesis
            ai_insight = "AI Key not found."
            if GEMINI_API_KEY:
                prompt = f"""
                You are a Clinical Data Analyst. Analyze this dataset summary and provide a professional clinical breakdown.
                Format as:
                ### 📌 Dataset Summary
                ### 📈 Key Clinical Trends
                ### ⚠️ Anomalies/Outliers
                
                Data:
                Filename: {filename}
                Columns: {cols}
                Stats Summary:
                {stats}
                """
                response = model.generate_content(prompt)
                ai_insight = response.text

            # 4. Generate Markdown Report
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(f"# 🩺 Clinical Analysis Report: {filename}\n")
                f.write(f"**Processed At:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write(f"## 📊 Raw Stats (Deterministic)\n")
                f.write(f"```\n{stats}\n```\n\n")
                f.write(f"## ✨ AI Clinical Insight\n")
                f.write(f"{ai_insight}\n")

            print(f"Analysis complete. Report saved: {report_path}")

        except Exception as e:
            print(f"Error processing {file_path}: {e}")

if __name__ == "__main__":
    if not os.path.exists(INPUT_DIR): os.makedirs(INPUT_DIR)
    if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)

    event_handler = ClinicalDataHandler()
    observer = Observer()
    observer.schedule(event_handler, INPUT_DIR, recursive=False)
    
    print("SheetVitals Watcher started.")
    print(f"Input Folder: {os.path.abspath(INPUT_DIR)}")
    print(f"Output Folder: {os.path.abspath(OUTPUT_DIR)}")
    
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
