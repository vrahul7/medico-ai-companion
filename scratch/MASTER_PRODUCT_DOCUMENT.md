# Medico AI Companion — Master Product & Technical Reference

**Version:** 1.0 | **Last Updated:** April 2026 | **Status:** Phase 1–6 Complete

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
12. [Deliberately Deferred Features](#12-deliberately-deferred-features)
13. [Known Blockers & Next Steps](#13-known-blockers--next-steps)

---

## 1. Product Vision & Mission

**Medico AI Companion** is a clinical-grade AI decision support platform designed for **practicing Indian doctors, residents, and NEET-PG students**. It bridges the gap between dense textbook theory and real-time clinical practice.

> "Not another medical chatbot — a zero-hallucination clinical reasoning engine grounded in the exact textbooks your team trained on."

### Mission
Equip every Indian physician with an intelligent assistant that cites sources like a consultant, thinks like a differential list, and keeps patient data private — all from a mobile browser.

---

## 2. Target Users & Market

| Segment | Description | Key Need |
|---|---|---|
| **Residents (PGY 1–3)** | Doctors in post-grad training | DDx assistance, drug references |
| **NEET-PG Students** | Medical exam aspirants | High-yield MCQs, clinical reasoning |
| **Attending Physicians** | Community and hospital doctors | Quick guideline lookup, cross-checking |

- **Primary geographic focus:** India (Stanley Medical College, AIIMS, CMC Vellore ecosystem)
- **Initial Curriculum Corpus:** Pediatric-first (Nelson's 22nd Ed + Piyush Gupta trilogy — 15,000+ pages)

---

## 3. Defensive Moats & Differentiation

The product is architected around **4 compounding defensive moats** that are hard for generic LLM wrappers to replicate:

### Moat 1: Clean Data Moat (Hierarchical RAG)
While every competitor has access to generic PubMed, we have ingested and indexed the **exact editions of textbooks used in Indian medical curricula** with structural hierarchy:

```
Chapter → Section → Paragraph → Page
```

This allows the AI to output citations like:
> *"According to Nelson's Pediatrics, Chapter 142, Section 3: Wheezing and dyspnea are hallmark signs..."*

**Ingestion Engine:** `ingest_hierarchical.py` parses dense PDFs using heuristic regex for structural markers, stores metadata in Pinecone namespaced by book.

---

### Moat 2: Zero-Hallucination Policy
Every synthesized answer is passed through a strict **Confidence Threshold Gate**:

```python
CONFIDENCE_THRESHOLD = 0.85
```

If Gemini's structured output confidence falls below 0.85, the engine refuses to output clinical advice and returns a **safe fallback**:

> *"I cannot provide a safe clinical answer based on current data. Please consult your attending."*

The LLM is forced to output a structured Pydantic JSON payload for every response, mapping **every single sentence** to a discrete `source_id` and `exact_quote`.

---

### Moat 3: Workflow Moat (DDx Assistant)
Rather than a generic chatbot, the DDx Assistant is a **structured clinical input form** — replicating how a real physician thinks through a differential:

```
Age + Sex + Primary Symptom + Vitals + Co-morbidities → Probability Table
```

Output: Ranked list of diagnoses by probability with inline citations traceable to exact textbook paragraphs.

---

### Moat 4: Evidence Traceability (Data Trust)
The **Split-Pane Source Preview UI** lets doctors click on any citation number and see:
- The exact highlighted text snippet from the source
- The book name + Chapter + Section structural context
- 👍 / 👎 Feedback buttons flowing into the Data Flywheel

---

## 4. Feature Set

| Feature | Status | Route | Notes |
|---|---|---|---|
| **MediChat AI** | ✅ Live | `/chat` | Perplexity-style centered layout |
| **DDx Assistant** | ✅ Live | `/ddx` | Split-pane with source preview |
| **Medical Quizzes** | ✅ Live | `/quizzes` | Animated topic cards + neon MCQ |
| **Dashboard** | ✅ Live | `/` | Control Centre + Live Research Feed |
| **Research Feed** | ✅ Live | `/` | PubMed live feed, Gemini summaries, paginated |
| **WhatsApp Bot** | ✅ Live (Sandbox) | `+14155238886` | Twilio Sandbox, phone whitelist, session memory |
| **Lab Report Analyzer** | ⏸ Deferred | — | HIPAA liability — post-PMF |

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
│              │   Pinecone   │  │ Supabase │  │    PostHog   │  │
│              │ Vector DB    │  │ Auth/DB  │  │  Analytics   │  │
│              │ (Hier. RAG)  │  │ (RLS)    │  │  (Free Tier) │  │
│              └──────────────┘  └──────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 6. Tech Stack

### Frontend
| Layer | Technology | Purpose |
|---|---|---|
| Framework | **React 19 + Vite 7** | Fast SPA with HMR |
| Styling | **Vanilla CSS** (custom design system) | Full control, no Tailwind dependency |
| Routing | **React Router v7** | SPA routing |
| Icons | **Lucide React** | Consistent icon library |
| Auth Client | **@supabase/supabase-js** | JWT session management |
| Analytics | **PostHog** | Event capture (free tier) |

### Backend
| Layer | Technology | Purpose |
|---|---|---|
| Framework | **FastAPI** | High-performance async API |
| LLM Orchestration | **LangChain** | Chain/RAG abstractions |
| LLM Provider | **Google Gemini 1.5 Pro** | Reasoning + structured JSON output |
| Embeddings | **Google text-embedding-004** | Medical semantic vectors |
| Vector DB | **Pinecone** | Hierarchical metadata retrieval |
| Live Data | **PubMed (Entrez)** | Real-time clinical study abstracts |
| Live Data | **OpenAlex** | Open scholarly graph (no key required) |
| Live Data | **Unpaywall** | Free full-text PDF resolver |
| Auth | **Supabase** | PostgreSQL + RLS + JWT |
| PII Anonymizer | **Microsoft Presidio** | HIPAA-safe query processing |
| Config | **python-dotenv** | Secure `.env` loading |

---

## 7. Backend Deep Dive

### 7.1 File Structure

```
backend/
├── app/
│   ├── main.py                  # FastAPI entrypoint, CORS, router registration
│   ├── api/routes/
│   │   ├── chat.py              # POST /api/chat — Hybrid RAG synthesis endpoint
│   │   ├── ddx.py               # POST /api/ddx/generate — DDx probability engine
│   │   ├── research.py          # GET /api/research/feed — Live PubMed feed + Gemini summaries
│   │   └── whatsapp.py          # POST /api/whatsapp/webhook — Twilio WhatsApp bot handler
│   └── services/
│       ├── rag.py               # HybridRAGEngine class (core zero-halluc. pipeline)
│       ├── live_sources.py      # PubMed + OpenAlex + Unpaywall live adapters
│       ├── whatsapp_bot.py      # WhatsApp message processor (whitelist + session + formatter)
│       ├── anonymizer.py        # Presidio PII stripper (HIPAA safe)
│       └── rate_limiter.py      # 20 queries/day Free Tier gate (no ads)
├── scripts/
│   ├── ingest_hierarchical.py   # Chapter > Section > Para PDF parser + Pinecone uploader
│   ├── ingest_all.bat           # Batch ingestion of all 5 textbooks (run overnight)
│   ├── start_tunnel.bat         # ngrok tunnel for dev WhatsApp webhook
│   └── WHATSAPP_SETUP.md        # 15-minute WhatsApp bot setup guide
├── data/documents/              # Gold Standard Textbook Library (350MB PDFs)
│   ├── Nelson Textbook of Pediatrics Volume 1 22ed 2024.pdf
│   ├── Nelson Textbook of Pediatrics Volume 2 22ed 2024.pdf
│   ├── Piyush Gupta PG Textbook Vol 1.pdf
│   ├── Piyush Gupta PG Textbook Vol 2.pdf
│   └── Piyush Gupta PG Textbook Vol 3.pdf
├── scripts/init_db.sql          # Supabase schema + logging.telemetry_logs
├── requirements.txt             # All Python dependencies
└── .env                         # API keys (NEVER commit to git)
```

### 7.2 Key API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Health check |
| `POST` | `/api/chat` | Hybrid RAG medical chat |
| `POST` | `/api/ddx/generate` | DDx probability table generator |
| `GET` | `/api/research/feed` | Latest PubMed articles + Gemini summaries (paginated) |
| `GET` | `/api/whatsapp/webhook` | Twilio/Meta webhook verification |
| `POST` | `/api/whatsapp/webhook` | WhatsApp incoming message handler |

### 7.3 Zero-Hallucination Synthesis Pipeline (`rag.py`)

```python
# Strict Pydantic output — every sentence mapped to a citation
class SynthesizedResponse(BaseModel):
    clinical_answer: str
    citations: List[Citation]          # source_id, exact_quote, structural_context
    confidence_score: float            # 0.0 to 1.0

# Fallback trigger
CONFIDENCE_THRESHOLD = 0.85
temperature = 0.0                      # Zero randomness
```

**Pipeline Flow:**
1. Anonymize query via Presidio (strip PHI)
2. Embed query using `text-embedding-004`
3. Retrieve top-5 semantic chunks from Pinecone (with Chapter/Section metadata)
4. Optionally fetch live PubMed abstracts (BioPython Entrez)
5. Format structural context block: `[Book - Chapter - Section]`
6. Force Gemini to output strict Pydantic JSON with citations
7. Check confidence score — trigger fallback if < 0.85

### 7.4 Hierarchical Ingestion (`ingest_hierarchical.py`)

**Metadata stored per vector chunk:**
```python
{
    "book_name": "Nelson Pediatrics Vol 1",
    "chapter": "Chapter 142",
    "section": "Section 3",
    "page_number": 847,
    "paragraph_id": 3
}
```

**Gold Standard Library Stats:**
- 5 textbooks | ~350MB PDFs | ~15,000 pages
- Estimated vector chunks: ~12,000–15,000 per book
- Pinecone index: `medico-ai-companion`
- Namespace: per-book (e.g., `nelson_pediatrics_vol_1`)

### 7.5 Rate Limiter (`rate_limiter.py`)

```
Free Tier:  20 queries / day  →  Hard 429 error → Upgrade CTA
Pro Tier:   Unlimited
```
> **No Ads on Free Tier.** Medical professionals have zero tolerance for ad-loaded UIs. Query limits drive upgrade conversions cleanly.

---

## 8. Frontend Deep Dive

### 8.1 File Structure

```
src/
├── components/
│   ├── Layout.jsx               # App shell: Sidebar + frosted glass header
│   └── Sidebar.jsx              # Glassmorphism nav: staggered slide-in animations
├── pages/
│   ├── Dashboard.jsx            # Stat cards with 3D lift + pulse animations
│   ├── AIChat.jsx               # Perplexity-style centered chat UI
│   ├── DDxAssistant.jsx         # Split-pane DDx form + Evidence Traceability
│   ├── Quizzes.jsx              # Animated MCQ engine with neon glow states
│   └── DailyBriefing.jsx        # Placeholder
├── main.jsx                     # Supabase + PostHog initialization
├── App.jsx                      # React Router routes
└── index.css                    # Master design system (700+ lines, no Tailwind)
```

### 8.2 Design System (`index.css`)

**Design Philosophy:** Deep-Space Glassmorphism
- Background: `linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%)`
- Glass panels: `rgba(255,255,255,0.03)` + `backdrop-filter: blur(16px)`
- Primary: Electric Blue `#60a5fa` | Accent: Deep Purple `#c084fc`
- Typography: `Inter` (Google Fonts, weights 300–700)

**Animation Library (CSS Keyframes):**
| Animation | Class | Usage |
|---|---|---|
| Fade + slide up | `.fade-in-up` | Page loads, cards, messages |
| Fade from top | `.fade-in-down` | Header |
| Staggered slide-in | `.stagger-slide-in` | Sidebar nav links, quiz options |
| Hover 3D lift | `.hover-lift` | Dashboard cards, quiz topics |
| Border glow | `.border-glow` | Insights panel hover |
| Pulsing heartbeat | `.pulse-animation` | Live dot indicator |
| Slow icon spin | `.icon-spin-slow` | Synthesis loading icon |
| Typing bounce | `.typing-dots` | AI "thinking" indicator |
| Fast spin | `.icon-spin-fast` | Loader spinner |

### 8.3 MediChat AI (`/chat`) — Perplexity Layout

- Centered 760px message stream, no side-by-side pane
- **Source Bubbles:** Pill-shaped floating badges above AI responses
- **Sliding Source Panel:** Animates in from the right (380px) on citation click
- **Suggested Queries:** 4 clinical query chips on first load to onboard users
- **Inline Citations:** Superscript `[1]` badges; click to highlight the source card
- **Typing Indicator:** 3-dot bounce animation + spinning Search icon

### 8.4 DDx Assistant (`/ddx`) — Evidence Traceability

- **Left Pane (60%):** Structured clinical form → Probability Assessment Table
- **Right Pane (40%):** Evidence Traceability Source Card
  - Shows: Exact Quote, Book + Chapter + Section
  - `<mark>` highlights the specific sentence
  - 👍/👎 feedback logged to Data Flywheel
- **Full-screen:** Bypasses standard page header for immersive experience

### 8.5 Quizzes (`/quizzes`) — Animated MCQ Engine

- **Topic Selection:** 6 specialty cards with emoji icons, per-topic accent color glow on hover
- **Question Flow:** Staggered A/B/C/D slide-in (80ms delay between options)
- **Selection States:**
  - Correct → Green neon glow border `rgba(74,222,128,0.15)` + `#4ade80` box-shadow
  - Incorrect → Red neon glow border `rgba(248,113,113,0.15)` + `#f87171` box-shadow
  - Others → Dimmed to 35% opacity
- **Explanation Block:** Fade-in panel with textbook source citation
- **Score Screen:** Animated gradient progress bar with dynamic grade label

---

## 9. Security & Compliance

### 9.1 PII Anonymization (Presidio)
All clinical queries pass through `anonymizer.py` before being sent to Gemini or stored in Pinecone. Microsoft Presidio detects and strips:
- Names (patient, doctor)
- Phone numbers, emails
- Dates of birth, addresses

### 9.2 Authentication (Supabase)
- JWT-based session management via `@supabase/supabase-js`
- Row-Level Security (RLS) on PostgreSQL ensures users can only access their own data

### 9.3 Zero-Hallucination Policy
- `temperature=0.0` on all Gemini calls
- Structured JSON output enforcement (Pydantic)
- Confidence threshold gate (0.85) with mandatory fallback

### 9.4 API Key Management
All secrets stored in `backend/.env` — never committed to version control:
```
GEMINI_API_KEY
GOOGLE_API_KEY
PINECONE_API_KEY
PINECONE_INDEX=medico-ai-companion
NCBI_API_KEY (optional, for PubMed rate limit increase)
```

---

## 10. Commercial Model

### Freemium Tiers

| Feature | Free | Pro |
|---|---|---|
| MediChat AI queries | 20 / day | Unlimited |
| DDx Assistant | 20 / day | Unlimited |
| Gold Standard Corpus | ✅ | ✅ + Future specialties |
| Live PubMed synthesis | ✅ | ✅ |
| Export / Share DDx | ❌ | ✅ |
| Advanced analytics | ❌ | ✅ |
| **Price** | **₹0** | **₹499/month (est.)** |

### Key Commercial Decisions
- ❌ **No Ads** — Medical professionals will immediately churn from ad-laden UIs
- ✅ **Hard Query Limits** — Clean UX, natural upgrade nudge via clear messaging
- ✅ **PostHog Free Tier** — Track conversion funnels, feature usage, DDx generation rates
- ❌ **No Custom Telemetry Dashboard** — Use PostHog's built-in dashboards to ship faster

---

## 11. Data Flywheel

The **Data Flywheel** is our long-term competitive advantage for model improvement.

**Schema:** `logging.telemetry_logs` (Supabase PostgreSQL)

Every DDx and Chat interaction is logged (anonymized via Presidio) with:
- Query text (PII-stripped)
- AI response + citations used
- Confidence score
- User feedback (👍 / 👎 from Source Preview)
- Session metadata

**Flywheel Loop:**
```
User Query → PII Strip → Pinecone Retrieval → 
Gemini Synthesis → User Feedback → Log to DB →
(Future) Fine-tune Gemini on domain-specific patterns
```

This means every doctor who uses the system makes responses better over time for the next — a **compounding data advantage** that generic chatbots cannot replicate.

---

## 12. Deliberately Deferred Features

These were consciously cut to maximize focused shipping velocity:

| Feature | Reason Deferred |
|---|---|
| **Lab Report Analyzer** | HIPAA/data liability complexity; high risk, low initial PMF signal |
| **Custom Telemetry Dashboard** | PostHog free tier covers this; building custom wastes sprint cycles |
| **Ads on Free Tier** | Medical users churn immediately from ads; use query limits instead |
| **Non-Pediatric Corpus** | Start narrow, go deep. Expand to Cardiology/Neurology post-PMF |
| **Mobile App (iOS/Android)** | Responsive PWA first; native app post-funding |

---

## 13. Known Blockers & Next Steps

### Current Blockers
| Issue | Status | Solution |
|---|---|---|
| Pinecone index mismatch (`medico-ai-index` vs `medico-ai-companion`) | ✅ **Fixed** | Added `PINECONE_INDEX=medico-ai-companion` to `.env` |
| PowerShell execution policy blocking `npm` | Workaround | Use `cmd.exe /c npm run dev` |

### Immediate Next Steps
1. **Run `ingest_all.bat`** — Double-click to upload all 5 textbook PDFs overnight. Expect 6–10 hours depending on Gemini API rate limits.
2. **Connect Live PubMed API** — ✅ **DONE** — `live_sources.py` implements PubMed (Entrez), OpenAlex, and Unpaywall adapters.
3. **Set up Git + GitHub** — Install Git for Windows, initialize repo, push codebase. Critical for version control before launch.
4. **Wire Supabase Auth to Frontend** — Add login/signup flow. Supabase provides a pre-built Auth UI component.
5. **Connect Rate Limiter to Supabase** — Currently mocked in-memory. Connect to actual user rows in Supabase to persist query counts across sessions.

### Growth Levers (Post-Launch)
1. ~~**WhatsApp Bot Integration**~~ — ✅ **SHIPPED** (Twilio Sandbox, phone whitelist, session memory)
2. **Expand Corpus to Sub-specialties** — Cardiology (Braunwald's), Neurology, OBG (Williams')
3. **NEET-PG Mock Test Mode** — Timed, scored, adaptive MCQ streaks
4. **Hospital API Integration** — EMR context injection for ward-round decision support
5. **WhatsApp Production Upgrade** — Migrate from Twilio Sandbox to Meta Cloud API with dedicated `+91` number
