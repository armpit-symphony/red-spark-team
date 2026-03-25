# Red Spark Team

Red Spark Team is a governed internal audit workspace for authorized red-team style reviews, scanner evidence normalization, and human-approved report export.

It is designed for teams that need a clear, reviewable workflow rather than a loose collection of tools and notes.

---

## Table of Contents

1. [What this app does](#what-this-app-does)
2. [Who this is for](#who-this-is-for)
3. [Core capabilities](#core-capabilities)
4. [System overview](#system-overview)
5. [Accepted inputs](#accepted-inputs)
6. [How to use the app](#how-to-use-the-app)
7. [Environment variables](#environment-variables)
8. [Local deployment](#local-deployment)
9. [Docker deployment](#docker-deployment)
10. [VM/server deployment](#vmserver-deployment)
11. [Repository quick start](#repository-quick-start)
12. [Run tests](#run-tests)
13. [Deployment templates shipped in the repo](#deployment-templates-shipped-in-the-repo)
14. [Current vs next architecture](#current-vs-next-architecture)
15. [Remaining work](#remaining-work)
16. [API overview](#api-overview)
17. [Project structure](#project-structure)
18. [Troubleshooting](#troubleshooting)
19. [Security notes](#security-notes)

---

## What this app does

Red Spark Team gives operators and developers one place to:

- define authorized audit targets
- start governed audit runs
- import raw scanner output in **text** or **JSON**
- normalize that input into structured findings
- draft review-ready markdown reports
- require **human approval** before report export
- manage provider configuration for LLM-assisted analysis

This is an internal governance-focused workflow tool. It is intentionally designed around review, evidence quality, and clean report handoff.

---

## Who this is for

This README is written for both:

- **Operators / security reviewers** who need to use the product day to day
- **Developers / maintainers** who need to run, configure, support, or extend it

---

## Core capabilities

### 1) Governed audit runs
- Create targets and scope boundaries
- Launch exploratory or consent-gated runs
- Keep run evidence isolated by workspace

### 2) Secure provider configuration
- Save custom provider keys
- Store keys encrypted at rest
- Update or remove keys later
- Use universal-key or custom-key modes by provider

### 2b) OpenRouter model catalog
- Sync OpenRouter models on backend startup
- Refresh the catalog manually from Settings
- Browse OpenRouter model names from both Settings and Run Detail
- Fall back to a curated manual list if the remote catalog is unavailable

### 2c) Reliability-first routing
- Choose a default routing policy in Settings
- Select a routing policy per analysis run
- Try the primary route first, then one fallback route
- Show the primary and fallback error reasons if both routes fail

### 3) Scanner import and normalization
- Import scanner output as **plain text** or **JSON**
- Convert valid entries into normalized findings
- Skip invalid items instead of failing the entire import
- Append imported evidence into the run’s tool-output section

### 4) Finding review workflow
- Review normalized findings per run
- Keep source context visible
- Track finding status and remediation guidance

### 5) Human-review export approval
- Report starts in `pending_review`
- Export unlocks only after approval
- Approved report can be:
  - copied as markdown
  - downloaded as a markdown file

---

## System overview

### Frontend
- **React** application
- Dashboard-style layout with pages for:
  - Overview
  - Targets
  - Policies
  - Audit Runs
  - Findings
  - Reports
  - Settings
  - Audit Log

### Backend
- **FastAPI** API service
- Handles targets, runs, findings, reports, providers, audit logs, and scanner import normalization

### Database
- **MongoDB**
- Stores application records, findings, report drafts, provider settings, and audit events

### LLM support
- OpenAI / Anthropic through universal-key or encrypted custom-key workflows
- OpenRouter / MiniMax through custom provider settings

### Primary workflow

```text
Create target
  -> Start audit run
  -> Capture or import evidence
  -> Normalize findings
  -> Generate report draft
  -> Human review
  -> Approve export
  -> Copy or download markdown
```

---

## Accepted inputs

### A. Target inputs
When creating a target, users provide:

- target name
- target type (`repo`, `webapp`, `script`, `service`)
- locator (URL, repo path, service reference, etc.)
- scope limit / scope notes
- allowed run modes

### B. Run inputs
When starting a run, users provide:

- selected target
- mode (`exploratory` or `consent_gated`)
- audit objective
- scope notes
- consent token (required for consent-gated runs)

### C. Provider settings inputs
On the Settings page, users can provide:

- model name
- auth mode (`universal` or `custom`)
- base URL
- optional custom API key
- enabled / disabled state

### D. Scanner import inputs
Scanner import currently supports:

- **Text input**
- **JSON input**

#### Example text input

```text
Title: Weak CSP on admin shell
Severity: high
Evidence: script-src allows unsafe-inline on /admin
Remediation: Remove unsafe-inline and move to nonce-based scripts.
```

#### Example JSON input

```json
{
  "findings": [
    {
      "title": "Missing frame-ancestors directive",
      "severity": "medium",
      "description": "The /settings page can be framed.",
      "remediation": "Set frame-ancestors 'none'."
    }
  ]
}
```

#### Import rules
- valid items are normalized into findings
- items missing required structure such as title or severity are **skipped**
- one invalid item does **not** block the rest of the import

---

## How to use the app

### 1. Configure providers
Open **Settings** and review the providers available for analysis.

Recommended flow:
- leave OpenAI / Anthropic on universal mode if your environment supports it, or switch them to custom mode for user-supplied provider keys
- use custom mode for OpenRouter / MiniMax if needed
- save or remove custom keys as required

### 2. Create a target
Go to **Targets** and add a scoped target with clear boundaries.

Include:
- what is in scope
- what is out of scope
- which run modes are allowed

### 3. Start an audit run
Go to **Audit Runs** and create a new run.

Choose:
- target
- mode
- objective
- scope notes

If using consent-gated mode, enter the required consent token.

### 4. Import scanner output
Inside the run workspace:
- open the **Findings** tab
- paste text or JSON scanner output
- click **Import findings**

The app will:
- normalize valid findings
- show imported / skipped counts
- preserve the import context in the tool-output evidence section

### 5. Review findings
Still inside the run, review:
- severity
- status
- evidence
- remediation
- source tag for imported items

### 6. Draft a report
Use the run’s analysis controls to generate a markdown draft report.

### 7. Approve export
Open the **Report** tab in the run or visit **Reports**.

Review the markdown draft, then:
- click **Approve export**

Once approved, the report can be:
- copied as markdown
- downloaded as a `.md` file

---

## Environment variables

### Backend (`backend/.env`)

| Variable | Required | Description |
|---|---:|---|
| `MONGO_URL` | Yes | MongoDB connection string |
| `DB_NAME` | Yes | MongoDB database name |
| `EMERGENT_LLM_KEY` | Recommended | Universal LLM key for supported providers |

### Frontend (`frontend/.env`)

| Variable | Required | Description |
|---|---:|---|
| `REACT_APP_BACKEND_URL` | Yes | Backend API base URL. For same-origin deployments, `/api` is recommended. |

### Recommended values by environment

#### Local development
- `REACT_APP_BACKEND_URL=/api`

#### Same-domain production behind reverse proxy
- `REACT_APP_BACKEND_URL=/api`

#### Separate frontend/backend hosts
- `REACT_APP_BACKEND_URL=https://your-api-domain.example.com/api`

---

## Local deployment

This is the fastest way to run the app for development, internal review, or QA.

### Prerequisites
- Node.js 18+
- Yarn
- Python 3.11+
- MongoDB 6+

### 1. Clone the project

```bash
git clone <your-repository-url>
cd red-spark-team
```

### 2. Start MongoDB

Make sure MongoDB is running locally and reachable through your configured `MONGO_URL`.

### 3. Configure the backend

Create or update `backend/.env`:

```env
MONGO_URL=mongodb://localhost:27017
DB_NAME=red_team_audit
EMERGENT_LLM_KEY=your_key_here
```

Install dependencies and run the backend:

```bash
cd backend
pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

### 4. Configure the frontend

Create or update `frontend/.env`:

```env
REACT_APP_BACKEND_URL=/api
```

Install dependencies and run the frontend:

```bash
cd frontend
yarn install
yarn start
```

### 5. Open the app

- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8001/api`

Because the frontend ships with a local `/api` proxy, `REACT_APP_BACKEND_URL=/api` works well in development.

---

## Docker deployment

This repository does not currently depend on a specific bundled Docker workflow, but the recommended production container layout is:

- **MongoDB** container
- **Backend** container (FastAPI)
- **Frontend** container (React build served behind Nginx or similar)

### Recommended container topology

```text
browser
  -> frontend container
  -> reverse proxy routes /api
  -> backend container
  -> MongoDB container
```

### Recommended Docker approach

#### Backend image
- base image: `python:3.11-slim`
- copy `backend/`
- install `requirements.txt`
- run `uvicorn server:app --host 0.0.0.0 --port 8001`

#### Frontend image
- build with Node
- serve production build with Nginx or another static server
- proxy `/api` to the backend service

#### MongoDB image
- use official `mongo` image
- mount a persistent data volume

### Production environment variables

Backend container:

```env
MONGO_URL=mongodb://mongo:27017
DB_NAME=red_team_audit
EMERGENT_LLM_KEY=your_key_here
```

Frontend container:

```env
REACT_APP_BACKEND_URL=/api
```

### Docker deployment checklist
- use persistent storage for MongoDB
- keep frontend and backend on the same network
- terminate TLS at Nginx, Traefik, or your load balancer
- route `/api` traffic to the backend container
- do not expose MongoDB publicly

---

## VM/server deployment

This option is suitable for internal staging or production on a cloud VM or private server.

### Recommended stack
- Ubuntu 22.04+ (or equivalent Linux server)
- Nginx
- Python 3.11+
- Node.js 18+
- MongoDB
- systemd for service management

### 1. Install runtime dependencies

Install:
- Python
- pip
- Node.js
- Yarn
- MongoDB
- Nginx

### 2. Deploy the backend

#### Example backend service file

`/etc/systemd/system/red-spark-backend.service`

```ini
[Unit]
Description=Red Spark Team Backend
After=network.target

[Service]
User=www-data
WorkingDirectory=/var/www/red-spark-team/backend
Environment="MONGO_URL=mongodb://localhost:27017"
Environment="DB_NAME=red_team_audit"
Environment="EMERGENT_LLM_KEY=your_key_here"
ExecStart=/usr/bin/python3 -m uvicorn server:app --host 127.0.0.1 --port 8001
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start it:

```bash
sudo systemctl daemon-reload
sudo systemctl enable red-spark-backend
sudo systemctl start red-spark-backend
```

### 3. Build the frontend

Set frontend env:

```env
REACT_APP_BACKEND_URL=/api
```

Build the frontend:

```bash
cd /var/www/red-spark-team/frontend
yarn install
yarn build
```

### 4. Configure Nginx

Example Nginx site:

```nginx
server {
    listen 80;
    server_name your-domain.example.com;

    root /var/www/red-spark-team/frontend/build;
    index index.html;

    location / {
        try_files $uri /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8001/api/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Then enable the site and reload Nginx.

### 5. Add TLS

For production, terminate HTTPS using:
- Let’s Encrypt + Certbot
- your cloud load balancer
- internal PKI if this is an internal-only deployment

---

## Repository quick start

If you want the fastest best-effort way to clone and run the project from repo structure, use the flow below.

### Clone the repo

```bash
git clone https://github.com/armpit-symphony/red-spark-team.git
cd red-spark-team
```

### Backend

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

export MONGO_URL="mongodb://127.0.0.1:27017"
export DB_NAME="red_spark_team"
export EMERGENT_LLM_KEY="REPLACE_WITH_UNIVERSAL_KEY"

cd backend
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

Notes:
- backend crypto and provider-key storage depend on `MONGO_URL` and `DB_NAME`
- `EMERGENT_LLM_KEY` is used for supported universal-auth provider flows
- the backend assumes `server.py` exposes the FastAPI app as `app`

### Frontend

```bash
cd ../frontend
yarn install
yarn start
```

Notes:
- the frontend dev proxy points to `http://127.0.0.1:8001/api`
- keep the backend running on port `8001` unless you also update the proxy / API base config

---

## Run tests

The backend test suite includes workflow coverage for provider key handling, scanner import normalization, and report approval/export.

With the backend running on port `8001`, open another terminal and run:

```bash
cd backend
export REACT_APP_BACKEND_URL="http://127.0.0.1:8001/api"
pytest -q
```

The current tests expect `REACT_APP_BACKEND_URL` to be set.

---

## Deployment templates shipped in the repo

The repository now includes self-hosting templates you can adapt directly:

### Docker / Compose
- `docker-compose.yml`
- `backend/Dockerfile`
- `frontend/Dockerfile`
- `frontend/nginx.conf`

### Kubernetes
- `k8s/namespace.yaml`
- `k8s/secret.yaml`
- `k8s/mongo.yaml`
- `k8s/backend.yaml`
- `k8s/frontend.yaml`
- `k8s/ingress.yaml`

### Future-state config references
- `configs/providers.yaml`
- `configs/routing.yaml`
- `docs/requirements-gap-analysis.md`
- `docs/openrouter-setup.md`

Important:
- the Docker and Kubernetes files are practical deployment templates
- the `configs/providers.yaml` and `configs/routing.yaml` files are **reference templates for future-state architecture** and are **not yet wired into the live runtime**
- the docs files capture the current requirements gap analysis and OpenRouter setup direction so the roadmap stays current

---

## Current vs next architecture

### Current platform shape

```text
User
  -> Frontend (React)
  -> Backend (FastAPI)
  -> MongoDB
  -> LLM provider(s)

Core product flow:
Create target / run
  -> POST /targets, POST /runs
Paste or import scanner output
  -> POST /runs/{id}/scanner-import
Normalize findings + store evidence
Run analysis
  -> POST /runs/{id}/analysis
Approve report
  -> POST /api/reports/{report_id}/approve
Export approved markdown
  -> GET /api/reports/{report_id}/export
```

### Next-state reference architecture

```text
Workspace UI
  -> Targets / Runs / Evidence / Approvals

Core API
  -> Auth / RBAC / Policy Gates

Model Router
  -> Multi-provider routing and fallback layer

Model Catalog
  -> OpenRouter model enumeration / sync

Tool Execution Plane
  -> Sandboxed jobs (Semgrep, CodeQL, evidence ingestion)

Observability
  -> OTel collector and trace / cost backend

State and secrets
  -> Postgres + pgvector
  -> Vault Transit / dedicated secrets system
```

This split helps keep the README honest about what exists today while still documenting where the platform is intended to grow.

---

## Remaining work

The items below are still roadmap / hardening work rather than current delivered behavior:

- add tenant isolation and auth / RBAC
- replace permissive default CORS for production deployments
- add model catalog ingestion and UI for broader provider coverage
- add router-based model fallback / latency / cost policies
- add real tool execution pipelines for scanner and code analysis jobs
- adopt stronger production secrets handling such as Vault Transit or equivalent managed encryption
- add OpenTelemetry instrumentation and optional LLM trace observability backend
- consider Postgres + pgvector if semantic retrieval becomes a core feature

---

## API overview

The backend exposes routes under `/api`.

### Key endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/health` | GET | Health check |
| `/api/targets` | GET / POST | List or create targets |
| `/api/runs` | GET / POST | List or create audit runs |
| `/api/runs/{run_id}` | GET | Get run workspace details |
| `/api/runs/{run_id}/sections` | POST | Save evidence/report sections |
| `/api/runs/{run_id}/analysis` | POST | Generate LLM-assisted output |
| `/api/runs/{run_id}/scanner-import` | POST | Import text or JSON into normalized findings |
| `/api/findings` | GET | List findings |
| `/api/reports` | GET | List reports |
| `/api/reports/{report_id}/approve` | POST | Approve report export |
| `/api/reports/{report_id}/export` | GET | Export approved markdown |
| `/api/providers` | GET | List provider settings |
| `/api/providers/{provider_name}` | PUT | Update provider settings |
| `/api/providers/{provider_name}/custom-key` | DELETE | Remove stored custom key |
| `/api/audit-log` | GET | List audit events |

---

## Project structure

```text
/app
├── backend/
│   ├── server.py
│   ├── models.py
│   ├── database.py
│   ├── llm_service.py
│   ├── security_utils.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   ├── components/
│   │   ├── lib/
│   │   └── App.js
│   └── package.json
├── tests/
├── scripts/
└── README.md
```

---

## Troubleshooting

### Frontend loads but API calls fail
Check:
- backend is running
- `REACT_APP_BACKEND_URL` is correct
- reverse proxy forwards `/api` properly

### Scanner import created fewer findings than expected
That usually means some entries were skipped.

Check whether imported items include:
- a recognizable title
- a recognizable severity

### Report export button is disabled
Report export only works after approval.

Approve the report first from:
- the run’s **Report** tab, or
- the **Reports** page

### Custom provider key appears missing
If a key was removed, the provider will show:
- no stored key
- `custom-key-required` when custom mode is enabled without a key

### MongoDB connection fails
Verify:
- MongoDB service is running
- `MONGO_URL` is correct
- `DB_NAME` exists or is allowed to be created

---

## Security notes

- Custom provider keys are stored **encrypted at rest**
- Report export is gated by **human approval**
- Imported scanner data is preserved in evidence context for auditability
- MongoDB should never be exposed directly to the public internet
- Frontend and backend should be served behind HTTPS in production
- For production hardening, use a dedicated cryptographic secret management strategy for provider key encryption and rotation

---

## Summary

Red Spark Team is a practical internal audit control plane for teams who need:

- strong workflow structure
- scanner-to-finding normalization
- secure provider configuration
- human-reviewed markdown export

If you want, the next documentation upgrade can be a separate `docs/` folder for API examples, operations playbooks, and admin SOPs.
