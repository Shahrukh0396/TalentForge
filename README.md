# TalentForge Resume Processing API

FastAPI backend that accepts resume uploads (PDF/DOCX/TXT), parses and formats them with Azure OpenAI, and returns Syntax Talent–styled DOCX and PDF files. Designed for Power Apps and Azure deployment.

## What it does

1. Upload one or many resumes
2. Parse raw text and remove contact info
3. Structure content with Azure OpenAI (summary, competencies, experience, education, skills, certifications)
4. Render formatted DOCX using the Syntax Talent letterhead template
5. Generate PDF (via LibreOffice)
6. Persist all artifacts in Azure Blob Storage

---

## Prerequisites

| Requirement | Notes |
|---|---|
| **Python 3.12+** | Recommended (matches Docker image) |
| **Azure Storage Account** | Blob container for files and job metadata |
| **Azure OpenAI** | Chat deployment with JSON output support |
| **LibreOffice** | Required for PDF generation (`soffice` command) |

### Install LibreOffice

**macOS:**
```bash
brew install --cask libreoffice
```

**Ubuntu/Debian:**
```bash
sudo apt-get update && sudo apt-get install -y libreoffice libreoffice-writer
```

**Windows:** Install from [libreoffice.org](https://www.libreoffice.org/) and ensure `soffice` is on your PATH.

> PDF generation fails if LibreOffice is not installed. DOCX generation still works without it.

---

## Project structure

```
TalentForge/
├── app/
│   ├── api/v1/resumes.py      # API endpoints
│   ├── main.py                  # FastAPI app + CORS
│   ├── models/resume_job.py     # Job model
│   ├── parsing/                 # PDF/DOCX/TXT text extraction
│   ├── services/
│   │   ├── resume_service.py    # Processing pipeline
│   │   ├── openai_service.py    # Azure OpenAI structuring
│   │   ├── docx_renderer.py     # Letterhead DOCX output
│   │   └── pdf_service.py       # DOCX → PDF conversion
│   ├── storage/
│   │   ├── blob_stub.py         # Azure Blob client
│   │   └── job_store.py         # Job metadata persistence
│   └── templates/
│       └── syntax_talent_letterhead.docx
├── requirements.txt
├── Dockerfile
├── .env.example
└── README.md
```

---

## 1. Clone and set up Python environment

```bash
cd TalentForge

# Create virtual environment
python3 -m venv .venv

# Activate (macOS/Linux)
source .venv/bin/activate

# Activate (Windows PowerShell)
# .venv\Scripts\Activate.ps1
```

---

## 2. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 3. Configure environment variables

Copy the example file and fill in your values:

```bash
cp .env.example .env
```

Edit `.env`:

```env
APP_NAME=TalentForge Resume Processing API
API_VERSION=v1

# Azure Blob Storage
AZURE_BLOB_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=...
AZURE_BLOB_CONTAINER=resumes

# Azure OpenAI
AZURE_OPENAI_API_KEY=your-key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-08-01-preview
AZURE_OPENAI_DEPLOYMENT=your-deployment-name
```

> Never commit `.env` to git. It is already listed in `.gitignore`.

---

## 4. Set up Azure Blob Storage

### Portal steps

1. Create a **Storage account** (General-purpose v2).
2. Create a container (e.g. `resumes`).
3. Go to **Access keys** → copy **Connection string**.
4. Set in `.env`:
   - `AZURE_BLOB_CONNECTION_STRING`
   - `AZURE_BLOB_CONTAINER`

### Azure CLI (optional)

```bash
az login

az group create --name rg-talentforge --location eastus

az storage account create \
  --name talentforgestore$RANDOM \
  --resource-group rg-talentforge \
  --location eastus \
  --sku Standard_LRS \
  --kind StorageV2

# Replace with your account name
ACCOUNT_NAME=your-storage-account-name

az storage container create \
  --name resumes \
  --account-name "$ACCOUNT_NAME" \
  --auth-mode login

az storage account show-connection-string \
  --name "$ACCOUNT_NAME" \
  --resource-group rg-talentforge \
  --query connectionString -o tsv
```

### Blob layout after processing

```
resumes/                          # your container
├── raw/{resume_id}/{filename}              # uploaded resume
├── processed/{resume_id}/resume.json       # structured AI output
├── generated/{resume_id}/{name}.docx       # formatted DOCX
├── generated/{resume_id}/{name}.pdf        # formatted PDF
└── jobs/{resume_id}/job.json               # job status & blob paths
```

---

## 5. Set up Azure OpenAI

1. Create an **Azure OpenAI** resource in Azure Portal.
2. Deploy a chat model (e.g. `gpt-4o` or `gpt-4o-mini`).
3. Copy from the resource:
   - API key → `AZURE_OPENAI_API_KEY`
   - Endpoint → `AZURE_OPENAI_ENDPOINT`
   - Deployment name → `AZURE_OPENAI_DEPLOYMENT`
4. Set `AZURE_OPENAI_API_VERSION` (e.g. `2024-08-01-preview`).

---

## 6. Run the API locally

```bash
source .venv/bin/activate   # if not already active

uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Open:

| URL | Purpose |
|---|---|
| [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) | Swagger UI (API testing) |
| [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc) | ReDoc |
| [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health) | Health check |

---

## 7. Test the API (Swagger / Postman)

### Single resume flow

1. **Upload** — `POST /api/v1/resumes`
   - Body: `form-data` → `file` = your resume (`.pdf`, `.docx`, or `.txt`)
   - Copy `resume_id` from the response

2. **Process** — `POST /api/v1/resumes/{resume_id}/process`

3. **Check status** — `GET /api/v1/resumes/{resume_id}`
   - Poll until `status` is `COMPLETED` or `FAILED`

4. **Download DOCX** — `GET /api/v1/resumes/{resume_id}/docx`
   - In Postman: use **Send and Download** (not plain Send)
   - Save as `.docx` and open in Word

5. **Download PDF** — `GET /api/v1/resumes/{resume_id}/pdf`

6. **View parsed JSON** — `GET /api/v1/resumes/{resume_id}/parsed`

### Batch flow (Power App style)

1. `POST /api/v1/resumes/batch` — upload multiple files
2. `POST /api/v1/resumes/batch/process` — body:
   ```json
   {
     "resume_ids": ["id-1", "id-2", "id-3"]
   }
   ```
3. Poll each `GET /api/v1/resumes/{resume_id}`
4. Download each completed job

### cURL example

```bash
# Upload
curl -X POST "http://127.0.0.1:8000/api/v1/resumes" \
  -F "file=@/path/to/resume.docx"

# Process (replace RESUME_ID)
curl -X POST "http://127.0.0.1:8000/api/v1/resumes/RESUME_ID/process"

# Status
curl "http://127.0.0.1:8000/api/v1/resumes/RESUME_ID"

# Download DOCX
curl -o output.docx "http://127.0.0.1:8000/api/v1/resumes/RESUME_ID/docx"
```

---

## 8. API endpoints reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/resumes` | Upload single resume |
| `POST` | `/api/v1/resumes/batch` | Upload multiple resumes |
| `POST` | `/api/v1/resumes/{id}/process` | Start processing |
| `POST` | `/api/v1/resumes/batch/process` | Process multiple jobs |
| `GET` | `/api/v1/resumes/{id}` | Job status |
| `GET` | `/api/v1/resumes/{id}/parsed` | Structured JSON output |
| `GET` | `/api/v1/resumes/{id}/docx` | Download stored DOCX |
| `GET` | `/api/v1/resumes/{id}/pdf` | Download stored PDF |
| `GET` | `/health` | Health check |

---

## 9. Run with Docker (local)

```bash
docker build -t talentforge-api .
docker run --env-file .env -p 8000:8000 talentforge-api
```

---

## 10. Deployment pipeline (GitHub Actions → Azure)

This repo includes automated CI/CD:

| Workflow | Trigger | Purpose |
|---|---|---|
| `.github/workflows/ci.yml` | PR + push to `main`/`stable` | Install deps, compile Python, build Docker image |
| `.github/workflows/azure-deploy.yml` | Push to `stable` + manual | Build image, push to ACR, deploy Azure Web App |

### One-time Azure setup

#### 1) Create Azure Container Registry (ACR)

```bash
az login
az group create --name rg-talentforge --location eastus
az acr create --resource-group rg-talentforge --name talentforgeacr --sku Basic
az acr show --name talentforgeacr --query loginServer -o tsv
```

#### 2) Create Azure Web App for Containers

```bash
ACR_LOGIN_SERVER=$(az acr show --name talentforgeacr --query loginServer -o tsv)
APP_NAME=talentforge-api-$RANDOM

az appservice plan create \
  --name plan-talentforge \
  --resource-group rg-talentforge \
  --sku B1 \
  --is-linux

az webapp create \
  --resource-group rg-talentforge \
  --plan plan-talentforge \
  --name "$APP_NAME" \
  --deployment-container-image-name "$ACR_LOGIN_SERVER/talentforge-api:latest"

az webapp config appsettings set \
  --resource-group rg-talentforge \
  --name "$APP_NAME" \
  --settings WEBSITES_PORT=8000
```

#### 3) Enable ACR pull for Web App

```bash
ACR_ID=$(az acr show --name talentforgeacr --query id -o tsv)
az webapp identity assign --resource-group rg-talentforge --name "$APP_NAME"
PRINCIPAL_ID=$(az webapp identity show --resource-group rg-talentforge --name "$APP_NAME" --query principalId -o tsv)
az role assignment create --assignee "$PRINCIPAL_ID" --scope "$ACR_ID" --role AcrPull
```

#### 4) Add app settings in Azure Portal

In **Web App → Configuration → Application settings**, add:

- `AZURE_BLOB_CONNECTION_STRING`
- `AZURE_BLOB_CONTAINER`
- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_API_VERSION`
- `AZURE_OPENAI_DEPLOYMENT`
- `WEBSITES_PORT=8000`

#### 5) Create GitHub secrets

In GitHub repo **Settings → Secrets and variables → Actions**, add:

| Secret | Value |
|---|---|
| `AZURE_CREDENTIALS` | Service principal JSON (see below) |
| `ACR_LOGIN_SERVER` | e.g. `talentforgeacr.azurecr.io` |
| `ACR_USERNAME` | ACR admin username (or SP) |
| `ACR_PASSWORD` | ACR admin password (or SP secret) |
| `AZURE_WEBAPP_NAME` | Your web app name |

Create service principal:

```bash
az ad sp create-for-rbac \
  --name "talentforge-github-deploy" \
  --role contributor \
  --scopes /subscriptions/<SUBSCRIPTION_ID>/resourceGroups/rg-talentforge \
  --sdk-auth
```

Copy the full JSON output into `AZURE_CREDENTIALS`.

#### 6) Create GitHub environment (recommended)

Create environment: `production`  
(Optional) Add required reviewers for safer deploys.

### Deploy flow

1. Merge/push to `stable`
2. GitHub Actions runs `azure-deploy.yml`
3. Docker image is built and pushed to ACR
4. Azure Web App is updated to the new image tag (`github.sha`)
5. Verify:
   - `https://<your-app>.azurewebsites.net/health`
   - `https://<your-app>.azurewebsites.net/docs`

### Manual deploy trigger

GitHub → **Actions** → **Deploy to Azure** → **Run workflow**

### Local Docker deploy test (before pipeline)

```bash
docker build -t talentforge-api .
docker run --env-file .env -p 8000:8000 talentforge-api
```

The Docker image includes LibreOffice, so PDF generation works out of the box.

---

## Troubleshooting

| Problem | Likely cause | Fix |
|---|---|---|
| `AZURE_BLOB_CONNECTION_STRING is not set` | Missing `.env` or vars not loaded | Copy `.env.example` → `.env` and restart server |
| `Azure OpenAI environment variables are not fully set` | Missing OpenAI config | Fill all `AZURE_OPENAI_*` vars |
| `Resume not found` after restart | Old in-memory-only jobs | Re-upload and process; new jobs persist to `jobs/{id}/job.json` in blob |
| Postman shows `PK...` garbage on download | Binary DOCX shown as text | Use **Send and Download**, save as `.docx` |
| PDF processing fails locally | LibreOffice not installed | Install LibreOffice (`soffice` on PATH) |
| `status: FAILED` with LibreOffice error | Same as above | Install LibreOffice or use Docker |
| CORS errors from Power Apps | Origin blocked | API includes dynamic CORS middleware; verify App Service URL |

---

## Processing pipeline

```
Upload → Azure Blob (raw/)
    ↓
Parse text (PDF/DOCX/TXT)
    ↓
Azure OpenAI → structured JSON
    ↓
DOCX renderer (letterhead template)
    ↓
LibreOffice → PDF
    ↓
Save to Azure Blob (processed/, generated/, jobs/)
    ↓
Download via API
```

---

## License

Internal use — Syntax Talent / TalentForge.
