# Image2Prompt

**Reverse prompt engineering as a SaaS.** Upload an image and AI models deduce how it
was created — camera settings, artistic style, composition, storytelling — and return a
text-to-image prompt that could recreate it.

This repo productizes that capability (originally a single Streamlit + AWS Bedrock lab)
into a microservices backend with two Angular portals: signup/signin → upload image →
generate a prompt via a pluggable AI provider → browse/search generated prompts, plus an
admin portal to manage providers and customers.

It also ships a commercial **Project Knowledge Bank** capability — customers build
per-project knowledge bases from their generated prompts on a pluggable vector store
(8 tech stacks), gated and priced by **admin-defined subscription plans**, with
Stripe-backed **billing** (per-stack metering, idempotent invoicing, optional scheduled
monthly sweep). See [Project Knowledge Bank & Subscriptions](#project-knowledge-bank--subscriptions).

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
                                      │ 15 providers   │  feature-toggled controllers
                                      │ all real:      │  bedrock·anthropic·openai·google·
                                      │ mock works     │  microsoft·mistral·cohere·ollama·
                                      │ offline        │  langgraph·crewai·llamaindex·strands·
                                      └────────────────┘  mock + routers openrouter·litellm
```

**Provider selection cascade** (most specific wins): per-request override → customer
default preferences → all admin-enabled providers. Only globally-enabled providers are
ever dispatched. Each request is logged in `proc_req_log`; each provider's response in
`proc_req_log_providers` (both JSON-heavy). Uploads go through a pluggable storage
backend (`local` now; S3/Azure/GCP stubbed) and are referenced everywhere by `file_refs.id`.

The **mock** provider is enabled by default so the entire flow works with **zero cloud
credentials**. Enable **bedrock** and provide AWS credentials to use real Claude on Bedrock.

## Project Knowledge Bank & Subscriptions

A separate **`kb-service`** (:8005, schema `img2pmpt_kb`, gateway prefix `/api/kb`) turns
a customer's generated prompts into searchable, per-project knowledge bases.

**Hierarchy:** Customer → Project → **KB Group** → **Project KB** (one per tech stack).
A customer picks which generated prompts to ingest; the KB embeds *instruction + prompt +
metadata* and supports semantic search. Ingestion can run **synchronously** or as a
**background job** (`POST /kbs/{id}/ingest-async` → poll `…/ingest-jobs/{job_id}`) so
large batches don't block.

**Pluggable vector stores (8 tech stacks).** Each is lazily wired to its SDK, gated by
config, and **degrades to an in-process index** when unconfigured (so the flow always
works) — `backend_ready` flags whether the real backend is live:

| Stack | Backend |
|---|---|
| `pgvector` | PostgreSQL (real, the local/test workhorse) |
| `chroma` | Chroma (real when `chromadb` installed) |
| `bedrock` | Amazon Bedrock Knowledge Bases (managed RAG over S3) |
| `opensearch` | AWS OpenSearch k-NN |
| `mongodb` | MongoDB Atlas Vector Search |
| `neo4j` | neo4j vector index |
| `pinecone` | Pinecone serverless |
| `weaviate` | Weaviate Cloud |

Embeddings use **Amazon Titan** on Bedrock, degrading to a deterministic local embedder
when boto3/creds are absent. Deleting a KB (or group) purges the external store so a
provisioned backend never leaks data or keeps counting toward billing.

**Subscriptions (admin-defined).** The **admin portal → Subscriptions** menu creates
plans that both *gate* which tech stacks a customer may use and *price* each
(`stacks: [{stack, monthly_cost}]`), plus per-plan **quotas** (`max_kbs`,
`max_docs_per_kb`; blank = unlimited). A fresh deploy seeds **Starter / Professional /
Enterprise**. Admins assign a plan to a customer; `kb-service` enforces the stack gate
*and* the quotas (KB creation 403s over `max_kbs`; ingest stops at `max_docs_per_kb`)
via `admin-service /internal/subscriptions/customer/{id}`. The customer's KB picker is
scoped to the plan's allowed stacks (`kb-service GET /my-subscription`). The admin
Subscriptions page also shows a **contracted-MRR rollup** (active subscribers × plan
list price) at `GET /admin/subscriptions/revenue`.

**Billing (Stripe).** `kb-service` exposes per-stack usage at
`/internal/usage/customer/{id}`; `customer-service` computes the monthly charge as
**plan price × the stacks a customer actually provisions** (surfaced on the portal's
Billing page) and creates a Stripe invoice on demand or via an opt-in **scheduled
monthly sweep** (`BILLING_SWEEP_ENABLED`). Billing is **idempotent per
(customer, calendar month)** — a `billing_runs` record prevents double-charging no
matter how often the action/sweep runs. Without a Stripe key it degrades to a priced
preview. The gateway refuses to proxy any upstream `/internal/*` path, so these
service-to-service endpoints aren't reachable from the edge.

## Service architecture (Python)

Every Python business service follows a strict **layered, shared-nothing**
structure (see any service's `app/`):

```
api (FastAPI controllers)  ->  facade (interface + impl)  ->  service  ->  dao
```

- Controllers depend on facade **interfaces** (ABCs), resolved by a small DI
  container (`app/di.py`). Flow is always facade → service → dao.
- Every layer method takes exactly one `*Req` and returns one `*Resp` — no loose
  positional args. The DB `Session` travels inside the `*Req`.
- Components are **singletons** holding no per-request state (shared-nothing), so
  one instance serves all concurrent requests safely.
- Controllers translate a failed `*Resp` to HTTP via `ensure_ok`; layers never
  raise HTTP errors.

**Database:** one Postgres server, one database, **a schema per service**
(`img2pmpt_admin`, `img2pmpt_customer`, `img2pmpt_image`). Schema + tables are
created by **Alembic** on startup (SQLite tests skip schemas and use create_all).

**Observability:** structured logging + **OpenTelemetry** traces and metrics
(`@observe`, `Metrics`, span attributes) with FastAPI/httpx/SQLAlchemy
auto-instrumentation and W3C trace propagation, so traces stitch across
gateway → service → ai-adapters. All **feature-toggled** and **fail-safe** —
disabled, SDK missing, or collector down all degrade to no-op. Locally,
`npm run local:containers:start-all` brings up an **OTel Collector + Jaeger +
Prometheus + Grafana** stack (each reused if already running); in AWS each ECS
task runs an **ADOT collector sidecar** exporting to X-Ray + CloudWatch.
Jaeger UI :16686 · Grafana :3000 · Prometheus :9090.

## Configuration & secrets

One config contract (env var names in `ServiceSettings`), two sources depending
on environment — services never change:

- **Local:** a single **repo-root `.env`** (`.env.example` to copy). The
  `DevOps/Local` scripts source it and export it to every service.
- **Cloud (AWS/Azure/GCP):** don't ship `.env`. Set `CAF_SECRET_PROVIDER` to
  `aws` / `azure` / `gcp` and the values are read from the secret store via the
  **`img2pmpt-caf-secret`** library (`libs/img2pmpt-caf-secret`).

`img2pmpt-caf-secret` (CAF = Common Application Framework) exposes a single
`ISecretClient` (`get_secret_by_key` / `get_secrets_by_keys`); the underlying
provider (`EnvFileProvider`, AWS Secrets Manager, Azure Key Vault, GCP Secret
Manager) is chosen by feature toggle (`CAF_SECRET_PROVIDER` + per-provider
`CAF_SECRET_*_ENABLED`). Cloud SDKs are imported lazily; a disabled toggle,
missing SDK, or lookup error degrades gracefully (returns a failed result with
any default, never raises). The shared settings layer plugs this in as a pydantic
source, so a field resolves from the local `.env` or a cloud secret with **zero
per-service code changes** (priority: explicit env > `.env` > CAF secret store).

For AWS, the secret named by `CAF_SECRET_AWS_SECRET_NAME` is a JSON object whose
keys are the uppercase env names (`JWT_SECRET`, `DATABASE_URL`, …); Azure/GCP use
one secret per key.

**AI provider keys** follow the same path. Locally, set `OPENAI_API_KEY`,
`ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`, and `AZURE_OPENAI_*` in the root `.env`
(see `.env.example`). In AWS they're entered as **inputs to `AWS_002_Setup_Secrets`**
(or `AWS_1000_All_Setup`) and **patched into the secret via the CLI** (jq merge,
non-empty only) — they are *never* passed as CloudFormation parameters, so they
don't appear in stack/parameter history. A blank key just leaves that provider
returning an error envelope if invoked (bedrock + the framework providers use AWS
creds; `mock` needs nothing).

## Quick start (local dev)

Everything is orchestrated from the repo root via `npm run local:*` scripts
(thin wrappers over `DevOps/Local/*.sh`).

```bash
cp .env.example .env                               # repo-root .env: single source of truth

# 1) Postgres — starts our container ONLY if nothing is already on :5432
#    (an existing Postgres on the laptop is reused; services just create schemas).
npm run local:containers:start-all

# 2) Python venv (one-time): install shared lib + CAF secrets lib + service deps
python -m venv .venv && . .venv/bin/activate
pip install ./services/shared ./libs/img2pmpt-caf-secret ./libs/img2pmpt-caf-routers boto3 email-validator
# (gateway/customer/admin/ai-adapters/image all import the shared lib)

# 3) Bring up services + portals together (portals need `npm install` first)
npm run local:services-ui:start-all

# status / shutdown
npm run local:services-ui:status-all
npm run local:shutdown:all          # portals + services + containers
```

Granular controls also exist: `local:containers:*`, `local:services:*`,
`local:portals:*`, each with `start-all` / `stop-all` / `status-all`.

| Service                    | URL                      |
|----------------------------|--------------------------|
| gateway (portals call this)| http://localhost:8000    |
| admin-service              | http://localhost:8001    |
| customer-service           | http://localhost:8002    |
| ai-adapters                | http://localhost:8003    |
| image-processing-service   | http://localhost:8004    |
| kb-service                 | http://localhost:8005    |
| customer-portal            | http://localhost:4200    |
| admin-portal               | http://localhost:4300    |

Seed admin (from `DevOps/Local/.env`): `admin@image2prompt.io` / `admin12345`.
Both portals talk to the gateway at `http://localhost:8000` (see each portal's
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
  shared/                    image2prompt_shared: settings, schema-scoped Base,
                             dtos (BaseReq/Resp), singleton, layer bases + interfaces,
                             security/JWT, auth deps, storage, http client,
                             logging, observability (OTEL), Alembic/seed bootstrap
  gateway/                   FastAPI edge: JWT validation + reverse proxy (+ logging/OTEL)
  customer-service/          api/facades/services/dao + dtos; img2pmpt_customer schema
  admin-service/             api/facades/services/dao + dtos; img2pmpt_admin schema
  ai-adapters/               api/facade/service + provider controllers (req/resp)
  image-processing-service/  api/facade(orchestrator)/services/dao; img2pmpt_image schema
  kb-service/                Project KB: api/facade/services/dao; pluggable vector
                             stores (8 stacks) + Titan embedder; img2pmpt_kb schema
  <each service>/alembic/    Alembic env + initial migration
libs/
  img2pmpt-caf-secret/       CAF secrets lib: client (ISecretClient) + provider_impls
                             (env / AWS / Azure / GCP), feature-toggled
  img2pmpt-caf-routers/      CAF LLM-routers lib: client (IRouterClient) + provider_impls
                             (OpenRouter / LiteLLM), feature-toggled; ai-adapters delegates
portals/
  customer-portal/           Angular — Dashboard (per-request provider pick + project),
                             Connections (cloud drives, mock OAuth), Projects, Prompts,
                             Knowledge Bank (Project KB), Preferences, Payment Settings
                             (Stripe), Billing & Receipts (subscription charges + invoice)
  admin-portal/              Angular — Dashboard (live analytics), Customer Search/Listing,
                             Customer Endpoints (per-customer connections), Providers,
                             Subscriptions (plans + per-stack pricing + assignment + reports)
DevOps/Local/                postgres docker-compose + start/stop/status scripts
.env.example                 root: single local config source of truth
package.json                 root: local:* orchestration scripts (no app code)
```

## Testing

Each Python service has pytest smoke tests (SQLite-backed, no Postgres needed):

```bash
python -m venv .venv && source .venv/bin/activate
pip install ./services/shared boto3 pytest httpx email-validator
cd services/customer-service          && python -m pytest   # signup/login/me, internal search
cd services/admin-service             && python -m pytest   # seed admin login, provider toggle
cd services/ai-adapters               && python -m pytest   # all providers real, graceful w/o SDK
cd services/image-processing-service  && python -m pytest   # orchestration (stubbed remotes)
cd services/kb-service                && python -m pytest   # KB CRUD/ingest/query, usage, delete
cd services/gateway                   && python -m pytest   # rate limit, /internal block, headers
```

`admin-service` tests also cover subscription plan CRUD + seeding; `customer-service`
covers billing computation, invoice idempotency, and the monthly sweep.

## AWS deployment (CloudFormation + ECS Fargate)

Deployed via **manual** GitHub Actions (Actions tab → Run workflow) that drive
**CloudFormation** stacks. Nothing triggers automatically.

**One-time:** add repo secrets `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`.
Each workflow takes an `aws_region` input (default `us-east-1`).

**All-in-one:** run **`AWS_1000_All_Setup_Image2Prompt`** to deploy everything in
order; **`AWS_1001_All_Destroy_Image2Prompt`** to tear it all down (reverse order).

**Per-module** (numbered, each a Setup/Destroy pair):

| Module | Stack | What |
|---|---|---|
| `AWS_001_Setup_Network`  | img2pmpt-network  | VPC + subnets + SGs. Reuses an **existing VPC** if you pass `existing_vpc_id` (+ subnet IDs), else creates one. |
| `AWS_002_Setup_Secrets`  | img2pmpt-secrets  | Secrets Manager bundle (`img2pmpt/app`) — the CAF `aws` provider reads it. |
| `AWS_003_Setup_Database` | img2pmpt-database | RDS PostgreSQL; then patches `DATABASE_URL` into the secret. |
| `AWS_004_Setup_Registry` | img2pmpt-registry | ECR repos. |
| `AWS_005_Setup_Compute`  | img2pmpt-compute  | Builds/pushes 6 service images, then ECS cluster + ALB + Cloud Map + services. |
| `AWS_006_Setup_Portals`  | img2pmpt-portals  | Builds/pushes the portals image, then the portals Fargate service. |

**Runtime shape:** one ALB — `/api/*` → **gateway**, everything else → **portals**
(one task serving both Angular apps). Internal services talk over **Cloud Map**
DNS (`*.img2pmpt.local`). Desired counts: gateway 2, customer 1, admin 1,
**ai-adapters 2**, **image-processing 2**, **kb-service 1**, portals 1 (all CFN parameters).
Services read JWT/DB/admin secrets at runtime through the CAF `aws` provider (the
task role can read the secret) — no secrets baked into images. After
`AWS_005`/`All_Setup`, the workflow log prints the ALB URL.

> CloudFormation/workflows are structurally validated but not deploy-tested here
> (no AWS account in this environment). The per-service Dockerfiles are built in
> CI and pushed to ECR — they're never run locally.

## Scope

**Built now:** customer auth + image→prompt generation (10 AI providers; mock offline) +
prompt listing/search; admin auth + provider management + customer listing/search;
**Project Knowledge Bank** (8 vector stores, embed + semantic search, delete/cleanup);
**Subscriptions** (admin plans, per-stack pricing, gating) and **billing** (metering,
idempotent invoicing, optional monthly sweep).

**Stubbed / wired for later:** real Google Drive/OneDrive/S3/Azure/GCP connections &
storage; production auth hardening. Connections use mock OAuth (real OAuth swaps
into connection_provider_service later). All 10 AI providers, the 6 managed vector
stores (pgvector + chroma run locally), and Stripe billing/invoicing are implemented
with lazy SDKs; they need their respective creds to run live and have **not** been
exercised against the real vendor APIs here. Initial Alembic migrations create tables
from model metadata — future schema changes should be explicit, autogenerated migrations.
