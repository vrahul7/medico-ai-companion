@echo off
echo ===============================================================================
echo  Medico AI Companion - Hierarchical Textbook Ingestion Batch
echo  Target Pinecone Index: medico-ai-companion
echo  This process will vectorize ~15,000 pages into the Gold Standard library.
echo  Safe to leave running overnight. DO NOT close this window.
echo  NOTE: If interrupted, re-running this script will RESUME from the exact
echo  checkpoint where it left off.
echo ===============================================================================

REM Navigate to the backend root so all relative paths resolve correctly
cd /d "%~dp0.."

echo.
echo Verifying environment variables...
python scripts\check_env.py
if %errorlevel% neq 0 (
    echo [FATAL] Environment check failed. Please verify your .env file.
    pause
    exit /b 1
)

echo.
echo -----------------------------------------------------------------------
echo [1/5] Nelson Pediatrics Vol 1 (22nd Ed, ~80MB)
echo -----------------------------------------------------------------------
python -u scripts\ingest_hierarchical.py --file "data\documents\Nelson Textbook of Pediatrics  Volume 1   22ed  2024.pdf" --book Nelson_Vol1
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Nelson Vol 1 ingestion stopped. 
    echo Please fix any limits or network issues, then run this bat file again to RESUME.
    pause
    exit /b %errorlevel%
)

echo.
echo -----------------------------------------------------------------------
echo [2/5] Nelson Pediatrics Vol 2 (22nd Ed, ~91MB)
echo -----------------------------------------------------------------------
python -u scripts\ingest_hierarchical.py --file "data\documents\Nelson Textbook of Pediatrics  Volume 2 22ed  2024.pdf" --book Nelson_Vol2
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Nelson Vol 2 ingestion stopped.
    echo Please fix any limits or network issues, then run this bat file again to RESUME.
    pause
    exit /b %errorlevel%
)

echo.
echo -----------------------------------------------------------------------
echo [3/5] Piyush Gupta Vol 1 (~93MB)
echo -----------------------------------------------------------------------
python -u scripts\ingest_hierarchical.py --file "data\documents\Piyush Gupta PG textbook of Pediatrics Vol1.pdf" --book PiyushGupta_Vol1
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Piyush Gupta Vol 1 ingestion stopped.
    echo Please fix any limits or network issues, then run this bat file again to RESUME.
    pause
    exit /b %errorlevel%
)

echo.
echo -----------------------------------------------------------------------
echo [4/5] Piyush Gupta Vol 2 (~37MB)
echo -----------------------------------------------------------------------
python -u scripts\ingest_hierarchical.py --file "data\documents\Piyush Gupta PG Textbook of Pediatrics Vol 2_compressed.pdf" --book PiyushGupta_Vol2
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Piyush Gupta Vol 2 ingestion stopped.
    echo Please fix any limits or network issues, then run this bat file again to RESUME.
    pause
    exit /b %errorlevel%
)

echo.
echo -----------------------------------------------------------------------
echo [5/5] Piyush Gupta Vol 3 (~55MB)
echo -----------------------------------------------------------------------
python -u scripts\ingest_hierarchical.py --file "data\documents\Piyush Gupta PG Textbook of Pediatrics Vol 3_compressed.pdf" --book PiyushGupta_Vol3
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Piyush Gupta Vol 3 ingestion stopped.
    echo Please fix any limits or network issues, then run this bat file again to RESUME.
    pause
    exit /b %errorlevel%
)

echo.
echo ===============================================================================
echo  BATCH INGESTION COMPLETE!
echo  Your Gold Standard Pinecone index 'medico-ai-companion' is now fully hydrated.
echo  All 5 textbooks vectorized with Chapter > Section > Paragraph metadata.
echo ===============================================================================
pause
