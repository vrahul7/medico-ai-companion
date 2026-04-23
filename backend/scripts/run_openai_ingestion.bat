@echo off
REM ============================================================
REM  Medico AI — Full OpenAI Ingestion Pipeline (Windows)
REM  Run from: backend\ directory
REM  Steps:
REM   1. Recreate Pinecone index at 3072 dims
REM   2. Ingest all 5 textbooks with OpenAI text-embedding-3-large
REM ============================================================

echo.
echo  ╔═══════════════════════════════════════════════════════╗
echo  ║    Medico AI — OpenAI Re-ingestion Pipeline           ║
echo  ║    text-embedding-3-large (3072 dims)                 ║
echo  ╚═══════════════════════════════════════════════════════╝
echo.
echo  [STEP 1/2] Recreating Pinecone index...
echo  (You will be prompted to confirm deletion of old vectors)
echo.

venv\Scripts\python scripts\recreate_index_openai.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  [ERROR] Index recreation failed. Check output above.
    pause
    exit /b 1
)

echo.
echo  [STEP 2/2] Starting ingestion of all 5 books...
echo  (Safe to Ctrl+C and re-run — checkpoints will resume)
echo.

venv\Scripts\python scripts\ingest_openai.py --all
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  [WARNING] Some books may have failed. Re-run this script to resume.
    pause
    exit /b 1
)

echo.
echo  ╔═══════════════════════════════════════════════════════╗
echo  ║  ✅ All done! RAG engine is ready with OpenAI embeds  ║
echo  ╚═══════════════════════════════════════════════════════╝
echo.
pause
