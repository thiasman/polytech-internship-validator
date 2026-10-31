# Polytech Orléans — Simple IT Handoff & Production Integration Guide

> **For:** Polytech Orléans 2-Person IT Team (DSI) & Data Protection Officer (DPO)  
> **Realistic University IT Effort:** **~4 Days Total** (3 simple integration steps — no new infrastructure or databases to maintain)

---

## 1. What We Hand Off (Built) vs. What Polytech IT Wires (~4 Days)

To go from this prototype to university production, Polytech IT does **not** need to build any AI logic or host a vector database. Your team only wires **3 standard university hooks**:

| Step | What Polytech IT Wires | Why It's Needed | Effort |
| :--- | :--- | :--- | :--- |
| **1. Deploy Container & OpenAI Service Account** | Run `docker compose up -d` on an internal university VM and set the **OpenAI Project Service Account Key** (`eu.api.openai.com` with Zero Data Retention). | Runs the stateless Python service inside the campus network with scoped EU API access. | **0.5 Days** |
| **2. Connect `check_school_db` to Intranet DB** | Replace the 10-line mock dictionary in `openai_engine.py` with a **read-only SQL query** to your existing `Esup-Stage` database (`SELECT status, notes FROM stages WHERE siret = %s`). | Lets Tool 1 check real historical internship outcomes at that company SIRET. | **1.5 Days** |
| **3. Intranet Webhook + Faculty SSO Check** | Point the existing intranet's PDF upload button to `POST /api/analyze-pdf` (restricted to logged-in faculty via your existing **CAS SSO** session, with a 15s timeout fallback to manual entry). | Auto-fills the 17 intranet fields for professors while ensuring students cannot call the API directly. | **2.0 Days** |

---

## 2. Authentication Trade-Offs (Two Layers of Auth)

A common question from university IT & security teams is: **"How do we authenticate users vs. how does the server authenticate to OpenAI?"**

### Layer A: Intranet-to-OpenAI Authentication (API Key vs. Service Account vs. OAuth)

| Auth Method | How It Works | Pros | Cons / Trade-Off | Our Recommendation |
| :--- | :--- | :--- | :--- | :--- |
| **1. Personal API Key** *(Used in PoC)* | Tied to one developer's OpenAI user account (`sk-...`). | Instant setup (1 minute) for local prototyping. | **Bad for production:** If that developer leaves the university, the integration breaks; no project-level spend cap. | **PoC Only** |
| **2. OpenAI Project Service Account Key + mTLS / IP Allowlist** *(Recommended)* | Scoped to a dedicated `polytech-orleans-prod` OpenAI Project (`sk-svcacct-...`) with a **€50/mo hard budget cap** and **restricted to `models.response` + `vector_stores` scopes**. | Stateless, zero token-refresh code for the 2-person IT team, survives staff turnover, and enforces a hard spend limit. | Static secret must be stored in the university's secret manager / `.env` and rotated annually. | **✅ Best for Phase 1–3** (Simple for a 2-person IT team) |
| **3. Short-Lived OAuth / Cloud KMS Federation (API Gateway)** | Central API gateway exchanges short-lived OIDC tokens before calling the LLM. | Zero long-lived static keys on disk; per-department billing tags. | Requires running an enterprise API Gateway (Kong/Vault)—overkill for a 2-person university IT team. | **Phase 4 Only** (When centralizing across all 16 Polytech schools) |

### Layer B: Professor-to-Intranet Authentication
- **Why Professors Don't Need OpenAI Logins:** Because this is a **backend B2B workflow**, professors never log into OpenAI or hold API keys. They log into the Polytech Intranet using their existing **University CAS / Shibboleth SSO**, and the intranet backend calls our Docker service over the internal campus VLAN.

---

## 3. Quickstart Commands (3 Steps)

```bash
# 1. Configure your OpenAI EU Service Account key & read-only DB host
cp .env.example .env

# 2. Start the stateless microservice
docker compose up -d --build

# 3. Run the evaluation suite (gpt-6-luna Worker + gpt-6-sol Judge) before any syllabus update
docker compose exec internship-ai python eval_pipeline.py
```
