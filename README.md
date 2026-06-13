# Image2Prompt

**Reverse prompt engineering as a SaaS.** Upload an image and AI models deduce how it
was created — camera settings, artistic style, composition, storytelling — and return a
text-to-image prompt that could recreate it.

This repo productizes that capability (originally a single Streamlit + AWS Bedrock lab)
into a microservices backend with two Angular portals. It is currently a **vertical
slice**: signup/signin → upload image → generate a prompt via a pluggable AI provider →
browse/search generated prompts, plus an admin portal to manage providers and customers.

## Architecture

```
                ┌─────────────────┐         ┌──────────────────┐
 customer :4200 │ customer-portal │         │   admin-portal   │ admin :4300
                └────────┬────────┘         └────────┬─────────┘
                         │   Angular (standalone)     │
                         └─────────────┬──────────────┘
                                       │ HTTP (JWT)
                              ┌────────▼─────────┐
                              │   gateway :8000  │  edge auth + reverse proxy
                              └───┬─────────┬────┬┘
            /api/customer ────────┘         │    └──────── /api/admin
                  │                /api/images                 │
        ┌─────────▼─────────┐  ┌────────────▼───────────┐  ┌───▼──────────────┐
        │ customer-service  │  │ image-processing-svc   │  │  admin-service   │
        │  :8002            │  │  :8004                 │  │  :8001           │
        │ auth, profile,    │  │ store image, build     │  │ admin auth,      │
        │ prefs, projects,  │  │ proc_req_log, fan-out, │  │ providers CRUD,  │
        │ payments (stub)   │  │ list/search prompts    │  │ customer search  │
        └─────────┬─────────┘  └───────────┬────────────┘  └──────────────────┘
                  │                         │ POST /invoke
              Postgres                ┌─────▼──────────┐
          (db per service)           │  ai-adapters   │ :8003  provider registry
                                      │ bedrock(real), │  feature-toggled controllers
                                      │ mock(real),    │  bedrock·anthropic·openai·
                                      │ + 7 stubs      │  google·microsoft·langgraph·
                                      └────────────────┘  crewai·llamaindex
```

**Provider selection cascade** (most specific wins): per-request override → customer
default preferences → all admin-enabled providers. Only globally-enabled providers are
ever dispatched. Each request is logged in `proc_req_log`; each provider's response in
`proc_req_log_providers` (both JSON-heavy). Uploads go through a pluggable storage
backend (`local` now; S3/Azure/GCP stubbed) and are referenced everywhere by `file_refs.id`.

The **mock** provider is enabled by default so the entire flow works with **zero cloud
credentials**. Enable **bedrock** and provide AWS credentials to use real Claude on Bedrock.

## Quick start

### 1. Backend + Postgres (Docker)

```bash
cd infra
cp .env.example .env          # tweak secrets / AWS creds if desired
docker compose up --build
```

This starts Postgres (with a database per service) and all five services. Tables are
auto-created and providers + a seed admin are created on startup.

| Service                    | URL                      |
|----------------------------|--------------------------|
| gateway (portals call this)| http://localhost:8000    |
| admin-service              | http://localhost:8001    |
| customer-service           | http://localhost:8002    |
| ai-adapters                | http://localhost:8003    |
| image-processing-service   | http://localhost:8004    |

Seed admin (from `.env`): `admin@image2prompt.io` / `admin12345`.

### 2. Portals (Angular)

```bash
cd portals/customer-portal && npm install && npm start   # http://localhost:4200
cd portals/admin-portal    && npm install && npm start   # http://localhost:4300
```

Both portals talk to the gateway at `http://localhost:8000` (see
`src/environments/environment.ts`).

### End-to-end walkthrough

1. Open the **customer portal** (4200) → **Sign up** → land on the **Dashboard**.
2. Upload any image → **Generate Reverse Prompt**. With no AWS creds the `mock` provider
   returns a prompt; it appears under **Prompts** (searchable).
3. Open the **admin portal** (4300) → sign in with the seed admin → **Customer Listing**
   shows the new signup; **Customer Search** finds them; **Providers** toggles which
   providers run.

## Repository layout

```
services/
  shared/                    image2prompt_shared: db, settings, security/JWT, auth deps,
                             pluggable storage, http client
  gateway/                   FastAPI edge: JWT validation + reverse proxy
  customer-service/          auth, profile, preferences, projects, payments (stub)
  image-processing-service/  upload → store → proc_req_log → fan-out → persist → list/search
  ai-adapters/               provider registry + per-provider controllers
  admin-service/             admin auth, providers CRUD/enable, customer search proxy
portals/
  customer-portal/           Angular — Dashboard, Connections (disabled), Projects,
                             Prompts, Payment Settings, Billing
  admin-portal/              Angular — Dashboard, Customer Search/Listing/Endpoints,
                             Providers
infra/                       docker-compose, postgres init, .env.example
```

## Testing

Each Python service has pytest smoke tests (SQLite-backed, no Postgres needed):

```bash
python -m venv .venv && source .venv/bin/activate
pip install ./services/shared boto3 pytest httpx email-validator
cd services/customer-service && python -m pytest      # signup/login/me, internal search
cd services/admin-service    && python -m pytest      # seed admin login, provider toggle
cd services/ai-adapters      && python -m pytest      # mock success, stub 501, unknown 404
```

## Scope

**Built now:** customer auth + image→prompt generation (Bedrock + mock) + prompt
listing/search; admin auth + provider management + customer listing/search.

**Stubbed / wired for later:** real Google Drive/OneDrive/S3/Azure/GCP connections &
storage; real Stripe billing; the 7 non-Bedrock provider controllers; dashboard
analytics; Alembic migrations; production auth hardening.
