# Medico AI Companion — Master Product & Technical Reference

**Version:** 2.0 | **Last Updated:** April 2026 | **Status:** Pivot to Research-Centric Platform Complete

---

## Table of Contents

1. [Product Vision & Mission](#1-product-vision--mission)
2. [Target Users & Market](#2-target-users--market)
3. [Defensive Moats & Differentiation](#3-defensive-moats--differentiation)
4. [Feature Set](#4-feature-set)
5. [Architecture Overview](#5-architecture-overview)
6. [Tech Stack](#6-tech-stack)
7. [Backend Deep Dive](#7-backend-deep-dive)
8. [Frontend Deep Dive](#8-frontend-deep-dive)
9. [Security & Compliance](#9-security--compliance)
10. [Commercial Model](#10-commercial-model)
11. [Data Flywheel](#11-data-flywheel)
12. [Deliberately Deferred/Removed Features](#12-deliberately-deferred-features)
13. [Known Blockers & Next Steps](#13-known-blockers--next-steps)

---

## 1. Product Vision & Mission

**Medico AI Companion** is a zero-hallucination, research-centric clinical intelligence platform designed for **practicing Indian doctors, residents, and NEET-PG students**. Over time, to avoid catastrophic medical legal liability, the platform systematically stripped away diagnostic features (like DDx generation) and pivoted exclusively to evidence retrieval, clinical guidelines tracking, and educational Q&A.

> "A living academic extension of a doctor's mind. We don't diagnose your patient; we autonomously fetch, summarize, and cite the exact research and regional guidelines you need to make the diagnosis yourself."

### Mission
Equip every Indian physician with an intelligent assistant that synthesizes global peer-reviewed data (PubMed/OpenAlex) and regional statutory guidelines (DHR/ICMR/WHO), grounded safely with zero AI hallucination.

---

## 2. Target Users & Market

| Segment | Description | Key Need |
|---|---|---|
| **Attending Physicians** | Community and hospital doctors | Quick statutory guideline lookup, tracking new global papers |
| **Residents (PGY 1–3)** | Doctors in post-grad training | Quick clinical reference, literature review assistance |
| **NEET-PG Students** | Medical exam aspirants | High-yield MCQs, core textbook fact retrieval |

- **Primary geographic focus:** India (Stanley Medical College, AIIMS, CMC Vellore ecosystem)
- **Initial Curriculum Corpus:** Pediatric-first (Nelson's 22nd Ed + Piyush Gupta trilogy — 15,000+ pages)

---

## 3. Defensive Moats & Differentiation

The product is architected around **4 compounding defensive moats**:

### Moat 1: Clean Data Moat (Hierarchical RAG)
While every competitor has access to generic PubMed, we index the **exact editions of textbooks used in Indian medical curricula** with structural hierarchy (`Chapter → Section → Paragraph → Page`).

### Moat 2: Zero-Hallucination Policy
Every synthesized answer is passed through a strict **Confidence Threshold Gate** (0.85). If Gemini's structured output confidence falls below 0.85, the engine refuses the prompt. 

### Moat 3: Proprietary Feed Orchestration
Generic chatbots require active prompting. Medico automatically constructs a unified 2-column feed pulling from complex, hidden regional JSON APIs (MoHFW/DHR India) and merges them with global open-access academic literature (OpenAlex/PubMed) behind a single elegant glass pane UI. Gemini is injected mid-stream to auto-generate 2-sentence clinical summaries before the data reaches the user.

### Moat 4: Evidence Traceability (Data Trust)
The **Split-Pane Source Preview UI** ensures doctors can click on any AI synthesis and trace it directly to the exact highlighted text snippet from the textbook or the DOI link of the research paper.

---

## 4. Feature Set (The New 3-Section Strategy)

| Section | Feature | Status | Route | Notes |
|---|---|---|---|---|
| **Section 1** | **Live Evidence Dashboard** | ✅ Live | `/` | 2-column feed. Left: PubMed+OpenAlex. Right: DHR+WHO Guidelines. Gemini AI summaries on all cards. |
| **Section 2** | **Unified MediChat AI** | ✅ Live | `/chat` | Perplexity-style chat injected with live guidelines & textbook RAG indexing. |
| **Section 3** | **Medical Quizzes** | ✅ Live | `/quizzes` | Animated topic cards + neon MCQ for NEET-PG. |
| **Extension** | **WhatsApp Bot** | ✅ Live | `+14155238886` | Twilio Sandbox, querying RAG backend via Whatsapp with session memory. |

*(Note: Diagnostic tools were completely purged to achieve 100% legal compliance).*

---

## 5. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     Medico AI Companion Platform                │
│                                                                 │
│  ┌──────────────┐   HTTPS/REST   ┌──────────────────────────┐  │
│  │   React 19   │ ◄────────────► │    FastAPI Backend        │  │
│  │   Vite 7     │                │    (Python 3.12)          │  │
│  │   Vanilla CSS│                └────────────┬─────────────┘  │
│  └──────────────┘                             │                 │
│                                               ▼                 │
│                              ┌────────────────────────────┐    │
│                              │    Synthesis Engine         │    │
│                              │    (Google Gemini 1.5 Pro)  │    │
│                              │    Temp=0.0 (Zero Halluc.)  │    │
│                              └────────┬───────────────────┘    │
│                                       │                         │
│                       ┌───────────────┼────────────────┐        │
│                       ▼               ▼                ▼        │
│              ┌──────────────┐  ┌──────────┐  ┌──────────────┐  │
│              │   Pinecone   │  │ Supabase │  │   Live API   │  │
│              │ Vector DB    │  │ Auth/DB  │  │   Pipeline   │  │
│              │ (Hier. RAG)  │  │ (RLS)    │  │(PubMed/WHO)  │  │
│              └──────────────┘  └──────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 6. Tech Stack

### Frontend
| Layer | Technology | Purpose |
|---|---|---|
| Framework | **React 19 + Vite 7** | Fast SPA with HMR |
| Styling | **Vanilla CSS** | Deep-space Glassmorphism |
| Icons | **Lucide React** | Consistent icon library |
| Auth Client | **@supabase/supabase-js** | JWT session management |

### Backend
| Layer | Technology | Purpose |
|---|---|---|
| Framework | **FastAPI** | High-performance async API |
| LLM Provider | **Google Gemini 1.5 Pro/Flash** | Structured JSON synthesis & abstract summarization |
| Vector DB | **Pinecone** | Offline textbook retrieval |
| Live Academic | **PubMed (Entrez) + OpenAlex** | Fused academic streams |
| Live statutory | **requests** (Custom Extractors) | DHR XML, WHO SEARO JSON scraping |

---

## 7. Backend Deep Dive

### 7.1 File Structure

```
backend/
├── app/
│   ├── main.py                  
│   ├── api/routes/
│   │   ├── chat.py              # POST /api/chat — RAG Chatbot
│   │   ├── research.py          # GET /api/research/scholarly & /guidelines with Paginated Gemini Sub-summaries
│   │   └── whatsapp.py          # POST /api/whatsapp/webhook
│   └── services/
│       ├── rag.py               # HybridRAGEngine
│       ├── live_sources.py      # Combines PubMed, OpenAlex
│       └── rss_fetcher.py       # Exclusively pulls from DHR India & WHO SEARO
├── scripts/
├── data/documents/              
├── requirements.txt             
└── .env                         # Uses ENTREZ_EMAIL=vgrahul7@gmail.com
```

### 7.2 Key API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/chat` | Unified Hybrid RAG medical chat |
| `GET` | `/api/research/scholarly` | Latest academic papers + AI summaries |
| `GET` | `/api/research/guidelines` | Live DHR/WHO guidelines + AI summaries |
| `POST` | `/api/whatsapp/webhook` | WhatsApp inbound handler via Twilio |

---

## 8. Frontend Deep Dive

### 8.1 File Structure

```
src/
├── components/
│   ├── Layout.jsx               
│   └── Sidebar.jsx              
├── pages/
│   ├── Dashboard.jsx            # 2-Column Live Feed (Research Left, Guidelines Right) + Pagination
│   ├── AIChat.jsx               # Centered Unified Chat UI
│   └── Quizzes.jsx              # Neon MOQ Engine
├── index.css                    # Master design system
```

### 8.2 Dashboard UI Mechanics
- **Scholarly Feed (Left):** Interleaves PubMed & OpenAlex papers. Triggers backend Gemini 1.5 prompt to generate a 2-sentence clinical breakdown. UI supports expanding dropdown to read full native abstracts without leaving the app. Paginates via `Load Next 5`.
- **Statutory Guidelines (Right):** Tracks the DHR (ICMR) hidden JSON endpoint and WHO SEARO API constraint. Also features Gemini AI Summary blocks and fully matches the aesthetic of the academic feed. Paginates via `Load Next 5 Guideline`.

---

## 9. Security & Compliance

### 9.1 Absolute Liability Avoidance (The DDx Purge)
To legally protect the company in Indian and Global jurisdictions, all components related to DDx (Differential Diagnosis) generation, lab report analysis, and standalone "clinical verdicts" have been purged from the codebase. The app now acts strictly as an **intelligent Search & Synthesis platform**, avoiding classification as a "Software as a Medical Device" (SaMD).

### 9.2 API Security
- Entrez & OpenAlex adhere strictly to rate limiting and API polite-pool registration using the system email (`vgrahul7@gmail.com`). 
- Raw HTML blocks returned by PubMed are strictly systematically stripped via Regex (`re.sub`) prior to LLM summarization.

---

## 10. Commercial Model

### Freemium Tiers
| Feature | Free | Pro |
|---|---|---|
| MediChat AI queries | 20 / day | Unlimited |
| Live Feed Access | ✅ | ✅ |
| Quizzes | ✅ | Advanced/Custom |
| **Price** | **₹0** | **₹499/month (est.)** |

---

## 11. Data Flywheel

The **Data Flywheel** relies on user engagement with our Live Feeds and Chat.
Every time a doctor expands an AI summary or rates a chat response, telemetry events are logged anonymously. The high interaction rates with the new 2-Column Dashboard ensure continuous data collection to fine-tune future LLM summarization models for medical nuance.

---

## 12. Deliberately Deferred/Removed Features

| Feature | Reason Deferred |
|---|---|
| **DDx Assistant** | 🛑 **REMOVED:** Extreme legal liability; misdiagnosis risk. |
| **Daily Briefing / Report Analyzer** | 🛑 **REMOVED:** Redundant or too legally complex for MVP. |
| **Custom Telemetry Dashboard** | PostHog free tier covers this. |
| **Mobile App (iOS/Android)** | Responsive PWA first; native app post-funding. |

---

## 13. Known Blockers & Next Steps

### Immediate Next Steps
1. **Frontend Final Validation** — Validate that the newly built Section 2 (unified Chatbot) dynamically incorporates the RSS Guideline states successfully based on user query inputs.
2. **Supabase Integration** — Attach the real authentication layer to secure the routes.
3. **Database Ingestion** — Push the full 15k pages of textbook assets (Piyush Gupta, Nelson) into the Pinecone Vector Cloud to complete the hybrid system.
