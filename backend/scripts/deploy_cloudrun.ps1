# deploy_cloudrun.ps1 — Production Deployment script for Medico Feeds API
# Ensure you are logged into gcloud before running:
#   gcloud auth login
#   gcloud config set project <your-gcp-project-id>

$PROJECT_ID = gcloud config get-value project
if (-not $PROJECT_ID) {
    Write-Error "Google Cloud Project ID is not set. Run: gcloud config set project [PROJECT_ID]"
    exit 1
}

Write-Host "Deploying Medico Feeds Backend to Google Cloud Run..." -ForegroundColor Cyan
Write-Host "Active GCP Project: $PROJECT_ID" -ForegroundColor Yellow

# Build container image using Google Cloud Build
gcloud builds submit --tag gcr.io/$PROJECT_ID/medico-feeds-api

# Deploy image to Google Cloud Run
gcloud run deploy medico-feeds-api `
    --image gcr.io/$PROJECT_ID/medico-feeds-api `
    --platform managed `
    --region us-central1 `
    --allow-unauthenticated

Write-Host "Deployment Completed Successfully!" -ForegroundColor Green
