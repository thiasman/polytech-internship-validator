# Polytech Orléans — 5th-Year Internship Validation Prototype

A lightweight Python microservice that helps engineering professors validate 5th-year student internship proposals (PDFs) in seconds.

---

## 1. How It Works

```mermaid
flowchart LR
    A["📄 Student PDF Upload"] --> B["🔒 Step 1: Local Check\nExtracts text (pypdf),\nmasks student ID/phone/email,\nblocks prompt injections"]
    B -- "Blocked if malicious" --> C["🛑 Red Security Alert"]
    B -- "Clean text" --> D["🧠 Step 2: OpenAI API\n(gpt-6-luna)"]
    D <--> T1["🗄️ Tool 1: check_school_db\nChecks duration (>=20w),\nstipend (>=650€) & company history"]
    D <--> T2["🌐 Tool 2: web_search\nChecks company R&D activity"]
    D <--> T3["📚 Tool 3: file_search\nReads 5A Syllabus file\n(syllabus_electronics_optics.md)"]
    D --> E["✅ Step 3: Intranet Output\nAuto-fills 17 form fields,\nGreen/Yellow status & draft email"]
```

---

## 2. What Is in This Repository

* **`app.py`** — Local web demo (`http://localhost:8765`) with:
  * **Tab 1:** The Faculty Intranet PDF validator (auto-fills 17 form fields, shows Green/Yellow/Red status, and lets professors override decisions).
  * **Tab 2:** A preview of a future Professor Admin Agent combining internship validation with two mock tools (defense jury scheduling and Month-1 student check-in).
* **`openai_engine.py`** — Core logic: PDF text extraction (`pypdf`), regex masking of student personal data, prompt-injection check, OpenAI tool calls, and 17-field JSON extraction.
* **`syllabus_electronics_optics.md`** — The 5th-year Electronics & Optics syllabus rules used by OpenAI `file_search` to distinguish Master-level R&D from technician work.
* **`eval_pipeline.py`** — Automated test suite that grades field accuracy, decision accuracy, and uses `gpt-6-sol` to score syllabus alignment and email tone (1–5) on `sample_pdfs/` and `professor_feedback_evals.json`.
* **`tradeoff_benchmark/`** — Benchmark script comparing local `pypdf` text extraction (`~5.8s`) vs. sending the raw PDF file directly to `gpt-6-luna` multimodal input (`~11.4s`).
* **`Dockerfile` & `docker-compose.yml`** — Container setup to run the service on a university server.

---

## 3. Quickstart (Run Locally)

```bash
# 1. Add your OpenAI API key
cp .env.example .env

# 2. Start the web app on http://localhost:8765
./.venv/bin/python app.py

# 3. Run the automated evaluation suite
./.venv/bin/python eval_pipeline.py
```

---

## 4. 3-Step Integration Guide for University IT (~4 Days)

What is mocked in this prototype vs. what University IT connects for production:

1. **Deploy the Docker Container (0.5 Days):**
   Run `docker compose up -d --build` on an internal university server using a scoped OpenAI Project Service Account Key configured for the EU endpoint (`https://eu.api.openai.com/v1`) with data storage disabled (`store=False`).
2. **Connect `check_school_db` to the School Database (1.5 Days):**
   In `openai_engine.py` (`def check_school_db`), replace the 10-line mock `SCHOOL_DB` dictionary with a read-only SQL `SELECT` query to your existing internship database to look up past internships by company SIRET number.
3. **Connect the Intranet Form (2.0 Days):**
   Point your existing faculty intranet upload button to `POST /api/analyze-pdf` (accessible only to logged-in professors) and map the 17 returned JSON fields to your HTML form inputs.
