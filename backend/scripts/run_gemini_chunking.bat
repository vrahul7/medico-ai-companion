@echo off
setlocal enabledelayedexpansion

echo ===============================================================================
echo  Medico AI Companion - Semantic Gemini Flash Ingestion
echo  Using logic-based chunking (10-page blocks)
echo ===============================================================================

REM Navigate to the backend root
cd /d "%~dp0.."

echo.
echo [1/5] Nelson Pediatrics Vol 1
python -u scripts\ingest_gemini_flash.py --file "data\documents\Nelson Textbook of Pediatrics  Volume 1   22ed  2024.pdf" --book Nelson_Vol1_Semantic
if %errorlevel% neq 0 exit /b %errorlevel%

echo.
echo [2/5] Nelson Pediatrics Vol 2
python -u scripts\ingest_gemini_flash.py --file "data\documents\Nelson Textbook of Pediatrics  Volume 2 22ed  2024.pdf" --book Nelson_Vol2_Semantic
if %errorlevel% neq 0 exit /b %errorlevel%

echo.
echo [3/5] Piyush Gupta Vol 1
python -u scripts\ingest_gemini_flash.py --file "data\documents\Piyush Gupta PG textbook of Pediatrics Vol1.pdf" --book PiyushGupta_Vol1_Semantic
if %errorlevel% neq 0 exit /b %errorlevel%

echo.
echo [4/5] Piyush Gupta Vol 2
python -u scripts\ingest_gemini_flash.py --file "data\documents\Piyush Gupta PG Textbook of Pediatrics Vol 2_compressed.pdf" --book PiyushGupta_Vol2_Semantic
if %errorlevel% neq 0 exit /b %errorlevel%

echo.
echo [5/5] Piyush Gupta Vol 3
python -u scripts\ingest_gemini_flash.py --file "data\documents\Piyush Gupta PG Textbook of Pediatrics Vol 3_compressed.pdf" --book PiyushGupta_Vol3_Semantic
if %errorlevel% neq 0 exit /b %errorlevel%

echo.
echo ===============================================================================
echo  SEMANTIC INGESTION COMPLETE!
echo ===============================================================================
pause
