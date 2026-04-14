@echo off
echo ============================================================
echo  Medico AI — WhatsApp Tunnel (ngrok)
echo  This exposes your local FastAPI to the internet so
echo  Twilio can reach your webhook.
echo ============================================================
echo.
echo [STEP] Checking if ngrok is installed...
where ngrok >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] ngrok not found. Download from: https://ngrok.com/download
    echo         Unzip ngrok.exe to this folder and re-run.
    pause
    exit /b 1
)
echo [OK] Found ngrok.
echo.
echo [START] Starting tunnel on port 8000...
echo [INFO]  Copy the HTTPS URL shown below and paste it into:
echo         Twilio Console → Messaging → Try WhatsApp → Sandbox Settings
echo         Set 'When a message comes in' URL to:
echo         https://xxxx.ngrok-free.app/api/whatsapp/webhook
echo.
ngrok http 8000
