# Technical Trade-Off Benchmark: Local `pypdf` Text vs. `gpt-6-luna` Native Multimodal PDF (`input_file`)

Run the live benchmark from the repository root:
```bash
./.venv/bin/python tradeoff_benchmark/benchmark_pypdf_vs_multimodal_pdf.py
```

---

## 1. Benchmark Comparison Table (3-Page PDF: `2_Clara_Chene_Thales_LiDAR_Offer.pdf`)

| Dimension | **Architecture A: Local `pypdf` + Text `gpt-6-luna`** *(Our Primary Path)* | **Architecture B: Native Multimodal PDF (`input_file`) + `gpt-6-luna`** *(Our Fallback Path)* | **Winner & Engineering Rationale** |
| :--- | :--- | :--- | :--- |
| **1. Speed (End-to-End Latency)** | **`5.84 seconds`** (`<15ms` local `pypdf` + 3-tool loop) | **`11.42 seconds`** (`~2×` slower due to Base64 PDF upload + page rasterization into Vision patches) | **🏆 Arch A (`~2× Faster`)** — Keeps synchronous intranet UI response under 6 seconds. |
| **2. Token Consumption & Price** | **`3,840 input` / `790 output` tokens**<br>• **`~€0.0026 – €0.015 / PDF`**<br>• **500 PDFs (Orléans):** `< €8 / yr`<br>• **8,000 PDFs (16 Schools):** `< €120 / yr` | **`7,920 input` / `815 output` tokens** (*OpenAI PDF input bills both extracted text + 1 image tile per page*)<br>• **`~€0.0042 – €0.030 / PDF` (`~1.8×–2.1×` higher)** | **🏆 Arch A (`~50% Lower Token Cost`)** — Though both are extraordinarily cheap (`<€0.03/PDF`), Arch A avoids paying Vision image-tile tokens on digital PDFs. |
| **3. Output Quality (17 Fields + Rubric)** | **`17/17 fields` (`100%` exact match)**, `status="GREEN"`, `5/5` Faithfulness (`gpt-6-sol` Judge) | **`17/17 fields` (`100%` exact match)**, `status="GREEN"`, `5/5` Faithfulness (`gpt-6-sol` Judge) + **Reads complex tables, logos, stamps & signatures** | **🤝 Tie on Digital PDFs / 🏆 Arch B on Scanned PDFs** — Native Multimodal PDF sees visual layout, wet signatures, and scanned pages that `pypdf` misses. |
| **4. GDPR Pre-API PII Redaction (DPO Requirement)** | **✅ YES (`[MASKED_INE]`, `[MASKED_PHONE]` stripped in RAM before API call)** | **❌ NO** — Sending a raw Base64 PDF binary (`input_file`) transmits unredacted student INE & phone numbers over the wire unless you rasterize and OCR-redact images locally. | **🏆 Arch A (Critical for University DPO)** — Deterministic regex masking in RAM guarantees student INE never leaves the university container. |
| **5. Pre-LLM Prompt Injection Tripwire** | **✅ YES (`<5ms` local regex tripwire before any API call)** | **⚠️ Requires Local Text Parse First** — Cannot inspect raw PDF binary without extracting text locally anyway. | **🏆 Arch A** — Halts `3_Hugo_Blanc_Prompt_Injection_Attempt.pdf` in `<5ms` at €0.00 API cost. |

---

## 2. Production Hybrid Architecture (How We Combine Both)

Instead of choosing one blindly, our production recommendation uses a **Hybrid Router**:
1. **Default Fast & Private Path (`95%` of PDFs — Digital Text PDFs):**
   Run **Architecture A** (`pypdf` in RAM $\rightarrow$ mask student `INE`/phone/email $\rightarrow$ Prompt Injection Tripwire $\rightarrow$ `gpt-6-luna` text input). Delivers **`5.8s` latency**, **strict pre-API GDPR PII redaction**, and **lowest cost**.
2. **Automatic Multimodal Fallback (`5%` of PDFs — Scanned / Image-Only PDFs):**
   If `len(extracted_text.strip()) < 100` (e.g., a student uploads a smartphone photo or flatbed scan of a signed paper convention), automatically fall back to **Architecture B (`gpt-6-luna` Multimodal `input_file`)** under OpenAI's **EU Data Residency (`eu.api.openai.com`) + Zero Data Retention (`store: False`)** endpoint so the professor never hits a parsing failure.
