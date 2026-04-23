import json
import os

log_path = r'C:\Users\NC24008_Rahul\.gemini\antigravity\brain\d093c18a-2002-4d47-8c23-a83389f3b5d6\.system_generated\logs\overview.txt'
output_path = r'd:\Antigravity\Project Directory\medico_ai_project_history.txt'

history = []

print(f"Reading logs from {log_path}...")

with open(log_path, 'r', encoding='utf-8') as f:
    for line in f:
        try:
            data = json.loads(line)
            source = data.get('source', '')
            msg_type = data.get('type', '')
            created_at = data.get('created_at', '')
            content = data.get('content', '')

            if not content:
                continue

            if msg_type == 'USER_INPUT':
                # Clean up user request tags
                clean_content = content
                if '<USER_REQUEST>' in content:
                    clean_content = content.split('<USER_REQUEST>')[1].split('</USER_REQUEST>')[0].strip()
                history.append(f"\n========================================\n[USER] {created_at}\n========================================\n{clean_content}\n")
            
            elif msg_type == 'PLANNER_RESPONSE':
                history.append(f"\n----------------------------------------\n[MEDICO AI]\n----------------------------------------\n{content}\n")
        
        except Exception as e:
            continue

print(f"Writing {len(history)} entries to {output_path}...")

with open(output_path, 'w', encoding='utf-8') as f:
    f.write("MEDICO AI COMPANION - PROJECT CONVERSATION HISTORY\n")
    f.write("="*50 + "\n")
    f.write("".join(history))

print("Export complete.")
