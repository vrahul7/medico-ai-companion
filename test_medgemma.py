import urllib.request
import json
import time
import sys

def main():
    model_name = "medgemma:4b"
    url = "http://localhost:11434/api/generate"
    
    # Clinical Vignette to test reasoning and accuracy (zero hallucination evaluation)
    clinical_prompt = (
        "You are a clinical AI reasoning assistant. Answer the following medical query with extreme clinical accuracy, "
        "evidence-based recommendations, and absolute precision. If you are unsure or do not have enough data, clearly state so "
        "to prevent hallucination.\n\n"
        "Clinical Case:\n"
        "A 52-year-old male presents to the emergency department with sudden-onset, crushing chest pain radiating to his left shoulder "
        "and jaw, which began 45 minutes ago. He is diaphoretic, nauseated, and has a history of type 2 diabetes, hypertension, and a "
        "30 pack-year smoking history. His vital signs are: BP 145/90 mmHg, HR 98 bpm, RR 20 bpm, O2 Sat 94% on room air.\n\n"
        "Questions:\n"
        "1. What is the most critical and likely working diagnosis?\n"
        "2. What are the immediate diagnostic steps to perform within the first 10 minutes?\n"
        "3. What immediate pharmacological interventions should be initiated, and what are their clinical rationales?"
    )
    
    data = {
        "model": model_name,
        "prompt": clinical_prompt,
        "stream": True
    }
    
    print(f"Connecting to local Ollama service at {url}...")
    print(f"Sending prompt to {model_name} (evaluating clinical reasoning)...\n")
    print("-" * 50)
    print(f"PROMPT:\n{clinical_prompt}")
    print("-" * 50)
    print("RESPONSE:\n")
    
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    
    response_text = ""
    start_time = time.time()
    
    try:
        with urllib.request.urlopen(req) as response:
            for line in response:
                if line:
                    chunk = json.loads(line.decode("utf-8"))
                    text = chunk.get("response", "")
                    print(text, end="", flush=True)
                    response_text += text
        
        duration = time.time() - start_time
        print("\n" + "-" * 50)
        print(f"\nResponse completed in {duration:.2f} seconds.")
        
        # Save results to a markdown file for documentation
        report_path = "medgemma_test_results.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(f"# MedGemma Local Evaluation Report\n\n")
            f.write(f"- **Model**: {model_name}\n")
            f.write(f"- **Date**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"- **Generation Time**: {duration:.2f} seconds\n")
            f.write(f"- **Data Security Status**: Local execution (HIPAA Compliant, zero PHI transit)\n\n")
            f.write(f"## Test Prompt\n\n```\n{clinical_prompt}\n```\n\n")
            f.write(f"## Model Output\n\n{response_text}\n\n")
            f.write(f"## PM Evaluation Notes (Zero Hallucination & Accuracy Check)\n\n")
            f.write(f"1. **Working Diagnosis**: (Verify if Acute Coronary Syndrome / STEMI / NSTEMI is identified)\n")
            f.write(f"2. **Immediate Diagnostics**: (Verify if 12-lead ECG and cardiac troponins are ordered within 10 minutes)\n")
            f.write(f"3. **Pharmacological Interventions**: (Verify if Aspirin 162-325 mg chewed, Nitroglycerin, Heparin, or O2 if hypoxemic are suggested, and check if diabetes/hypertension contraindications are noted)\n")
            
        print(f"Results successfully saved to {report_path}")
        
    except Exception as e:
        print(f"\nError communicating with Ollama: {e}")
        print("Please ensure the model has finished pulling and the Ollama service is active.")

if __name__ == "__main__":
    main()
