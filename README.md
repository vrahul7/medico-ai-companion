   # 🩺 Medico AI Companion
### Clinical Intelligence Synthesis & Physician Support Bot

Medico AI is a high-performance Hybrid RAG (Retrieval-Augmented Generation) platform designed for pediatricians. It synthesizes clinical knowledge from Gold Standard textbooks (Nelson, Piyush Gupta) and live medical research feeds.

## 🚀 Key Features
- **Hybrid RAG Engine:** Grounded synthesis using Gemini 2.5 Flash and 3072-dim vector precision.
- **Textbook Library:** Ingested 7,700+ clinical chunks from Nelson's and Piyush Gupta textbooks.
- **WhatsApp Bot:** Secure clinical support via Twilio WhatsApp Sandbox with PII anonymization.
- **OpenEvidence Interface:** Premium split-pane React UI with interactive citation mapping.
- **Security:** Integrated Supabase Auth and Physician Whitelisting.

## 📁 Project Structure
- `frontend/`: React + Vite application (OpenEvidence UI).
- `backend/`: FastAPI service with RAG and WhatsApp logic.
- `backend/scripts/`: Essential clinical data ingestion tools.

## 🛠️ Quick Start
1. **Backend Setup:**
   ```bash
   cd backend
   pip install -r requirements.txt
   uvicorn app.main:app --reload
   ```
2. **Frontend Setup:**
   ```bash
   npm install
   npm run dev
   ```

## 🔐 Deployment
- **Frontend:** Optimized for Vercel.
- **Backend:** Optimized for Docker-based deployment (Render/Railway/HuggingFace).

---
*Disclaimer: For clinical support only. Not a substitute for professional medical judgment.*
