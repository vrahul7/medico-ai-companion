Medico AI Companion: Product Flow & Technical Architecture

[!NOTE]This document details the end-to-end product flow, system architecture, and public data sources for theMedico AI Companion (Hybrid RAG Healthcare Platform). This platform bridges the gap between academic theory and clinical practice for medical students and practitioners.

1. Product Flow (User Journeys)

The platform is designed around four primary modules. The user journey for each module is outlined below:

1.1. AI Medical Chat (Hybrid RAG)

The core feature allowing users to ask complex clinical questions and receive evidence-based answers with inline citations.

Input: User enters a clinical query (e.g., "What are the latest guidelines for managing acute asthma exacerbation in pediatric patients?").

Intent Parsing: The system categorizes the query (e.g., diagnostic, pharmacological, procedural).

Hybrid Retrieval:

Offline Path (Local RAG): Queries the Vector Database containing pre-processed medical textbooks, university lecture notes, and local protocols.

Online Path (Live RAG): Triggers API calls to live medical databases to fetch the latest research papers and clinical guidelines.

Synthesis: The retrieved documents from both paths are reranked, filtered, and passed to the LLM.

Output: The LLM generates a comprehensive, synthesized response containing interactive inline citations that map directly to the source cards displayed in a split-pane "OpenEvidence" style UI.

1.2. Lab Report Analyzer

A premium tool for rapid analysis of patient lab results.

Input: User uploads a lab report (PDF, JPG, PNG).

Extraction: OCR engine extracts raw text and tabular data from the document.

Parsing & structuring: Extracted text is parsed into structured JSON (Test Name, Result, Units).

Analysis: Values are compared against standardized reference ranges.

Output: The UI presents a table of flagged abnormalities and an AI-generated clinical assessment detailing potential differential diagnoses or implications.

1.3. Personalized Quizzes

An educational tool for medical students.

Input: Based on the user's chat history and selected weak topics, the system schedules a quiz.

Generation: The LLM dynamically generates MCQ or short-answer clinical vignettes.

Feedback: As the user answers, real-time explanations are provided, linking back to the relevant literature or textbooks.

1.4. Daily Medical Briefing

A curated news feed keeping practitioners up-to-date.

Input: System automatically pulls daily feeds based on the user's declared specialty.

Summarization: New papers are condensed into bite-sized summaries by the LLM.

Output: User receives a daily dashboard or email briefing with links to the full texts.

2. Technical Architecture

The architecture follows a decoupled, scalable approach optimized for high-performance retrieval and secure data handling.

graph TD    A[Client User Interface] --> B[Vite + React.js]        subgraph Frontend    B --> C[Routing & State Management]    C --> D[Split-Pane UI Components]    end    D <--> E[FastAPI Backend - Python]    subgraph Backend / API Layer    E --> F[Authentication & Security]    E --> G[Orchestrator Layer / Routing]    end    subgraph Retrieval Augmented Generation    G --> H[LangChain / LlamaIndex]    H --> I[Vector Database: ChromaDB/Pinecone]    H --> J[External API Fetchers]    H --> K[Large Language Model]    end    subgraph Storage    I <--> L[(Document Corpus)]    end    J <--> M[Public Medical Data Sources]

2.1. Frontend Stack

Framework: Vite + React.js (optimized for fast client-side rendering).

Styling: Vanilla CSS, CSS Modules, and utility libraries like clsx.

UI Components: Shadcn/UI philosophy (headless components), Lucide React for consistent iconography.

Layout: High-fidelity split-pane view (Chat on left, Source Cards on right).

2.2. Backend & AI Stack

Framework: Python / FastAPI (for high-concurrency, typed endpoints).

AI Orchestration: LangChain / LlamaIndex for document chunking, ingestion, and complex retrieval pipelines.

LLM: OpenAI, Anthropic Claude, or Gemini (optimized for medical reasoning).

Vector Database: ChromaDB (for local/testing) or Pinecone (for scalable production) to store embeddings of offline medical books.

Embedding Model: Dense embedding models specialized for medical jargon (e.g., text-embedding-3-small or specialized Med-BERT models).

2.3. Security & Compliance

Data Privacy: End-to-end encryption for any uploaded patient data.

HIPAA Compliance: Stripping PII (Personally Identifiable Information) from lab reports before LLM processing.

Secure File Storage: Short-lived signed URLs for uploaded files, automatic deletion post-analysis.

3. Public Data Sources

To ensure the "Live RAG" aspect provides the most accurate and up-to-date clinical information, the system will integrate with the following public APIs and data aggregators:

3.1. Primary Research & Literature

PubMed (NCBI E-utilities / Biopython.Entrez): The primary source for biomedical literature, clinical trials, and Medline data.

OpenAlex: An open and comprehensive index of scholarly papers, authors, and institutions. Excellent for cross-referencing citations.

Unpaywall API: Used to automatically locate and fetch full-text, Open Access (OA) versions of research papers identified via PubMed or OpenAlex.

3.2. Clinical Guidelines & Protocols

WHO (World Health Organization): For global health guidelines, disease outbreaks, and international protocols.

CDC (Centers for Disease Control and Prevention): For epidemiology, vaccination schedules, and infectious disease guidelines.

ClinicalTrials.gov: To fetch data on ongoing or recently concluded clinical trials (helpful for experimental treatment queries).

3.3. Pharmacological & Anatomical Databases

RxNorm: (via NLM APIs) For standardized nomenclature for clinical drugs, used in cross-checking medications in lab reports or queries.

UMLS (Unified Medical Language System): Used to map medical terms across different classification systems (ICD-10, SNOMED CT) to ensure the LLM understands user queries accurately.

[!IMPORTANT]The reliability of a Healthcare AI relies entirely on its citations. The synthesis engine MUST explicitly verify every claim against the retrieved texts from these sources and handle "no context found" gracefully to prevent medical hallucinations.