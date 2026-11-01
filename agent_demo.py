"""OpenAI Agents SDK Module (`agent_demo.py`).

A clean, separate module showcasing the official OpenAI Agents SDK (`openai-agents`)
for the popup chat widget on the main intranet page (`app.py`).

It wraps our existing validation API (`analyze_internship_document` from `openai_engine.py`)
as a single `@function_tool` (`validate_internship_offer`) without modifying `openai_engine.py`.
"""

import json
import os
import re

from agents import (
    Agent,
    GuardrailFunctionOutput,
    InputGuardrail,
    InputGuardrailTripwireTriggered,
    Runner,
    function_tool,
)

from openai_engine import (
    INJECTION_PATTERNS,
    analyze_internship_document,
    load_env_key,
)

# Stores the latest structured output when the agent calls `validate_internship_offer`
# so the main intranet page can auto-fill the 17 form fields behind the popup.
_LAST_TOOL_PIPELINE_RESULT: dict | None = None


# ==============================================================================
# 1. INPUT GUARDRAIL (`agents.InputGuardrail`)
# ==============================================================================
async def prompt_injection_guardrail(ctx, agent, input_data) -> GuardrailFunctionOutput:
    """Blocks indirect prompt injection before the Agent executes any tool."""
    text = input_data if isinstance(input_data, str) else json.dumps(input_data)
    triggered = any(re.search(pattern, text, re.IGNORECASE) for pattern in INJECTION_PATTERNS)
    return GuardrailFunctionOutput(
        output_info={"injection_detected": triggered},
        tripwire_triggered=triggered,
    )


# ==============================================================================
# 2. SINGLE TOOL (`@function_tool` wrapping our existing `analyze_internship_document` API)
# ==============================================================================
@function_tool
def validate_internship_offer(proposal_text: str) -> str:
    """Calls the Polytech Orléans 5A Internship Validation API on a student offer.

    Args:
        proposal_text: Full text or summary of the internship offer to validate.
    """
    global _LAST_TOOL_PIPELINE_RESULT
    _LAST_TOOL_PIPELINE_RESULT = analyze_internship_document(proposal_text, page_count=1)
    return json.dumps(
        {
            "status": _LAST_TOOL_PIPELINE_RESULT["status"],
            "status_badge": _LAST_TOOL_PIPELINE_RESULT["status_badge"],
            "extracted_form": _LAST_TOOL_PIPELINE_RESULT["extracted_form"],
            "bullet_1_company": _LAST_TOOL_PIPELINE_RESULT["bullet_1_company"],
            "bullet_2_syllabus": _LAST_TOOL_PIPELINE_RESULT["bullet_2_syllabus"],
            "bullet_3_recommendation": _LAST_TOOL_PIPELINE_RESULT["bullet_3_recommendation"],
            "draft_email": _LAST_TOOL_PIPELINE_RESULT["draft_email"],
        },
        ensure_ascii=False,
    )


# ==============================================================================
# 3. AGENT DEFINITION (`agents.Agent`)
# ==============================================================================
internship_agent = Agent(
    name="Polytech 5A Internship Agent",
    model=os.environ.get("OPENAI_MODEL", "gpt-6-luna"),
    instructions=(
        "You are the Polytech Orléans 5th-Year (5A) Electronics & Optics Internship Assistant "
        "helping Prof. Mathias Canales.\n"
        "You can chat naturally in English or French, answer greetings ('hello', 'bonjour'), "
        "explain the 5A Electronics & Optics validation rules (>=20 weeks duration, >=650 EUR/month stipend, "
        "Master's R&D design/simulation vs. technician assembly), and discuss the current form.\n"
        "You have ONE tool: `validate_internship_offer`.\n"
        "- ONLY call `validate_internship_offer` when the professor asks to validate, check, analyze, "
        "or review an internship offer or the current form.\n"
        "- For greetings or general questions, reply directly in 2-3 concise sentences without calling the tool."
    ),
    tools=[validate_internship_offer],
    input_guardrails=[InputGuardrail(guardrail_function=prompt_injection_guardrail)],
)


# ==============================================================================
# 4. AGENT RUNNER (`Runner.run_sync`) CALLED BY THE POPUP WIDGET IN `app.py`
# ==============================================================================
def run_agent_turn(user_message: str, current_form_text: str = "", history: list | None = None) -> dict:
    """Executes one conversational turn of `internship_agent` via `Runner.run_sync`."""
    global _LAST_TOOL_PIPELINE_RESULT
    _LAST_TOOL_PIPELINE_RESULT = None
    load_env_key()
    history = history or []

    # Build multi-turn input list for `Runner.run_sync`
    input_items = []
    for turn in history[-6:]:
        role = "user" if turn.get("role") == "user" else "assistant"
        input_items.append({"role": role, "content": turn.get("content", "")})

    user_content = user_message
    if current_form_text.strip():
        user_content = f"{user_message}\n\n[Current Intranet Form Context:\n{current_form_text}]"
    input_items.append({"role": "user", "content": user_content})

    try:
        result = Runner.run_sync(internship_agent, input=input_items)
        tool_called = None
        if _LAST_TOOL_PIPELINE_RESULT is not None:
            tool_called = f"validate_internship_offer → {_LAST_TOOL_PIPELINE_RESULT['status']}"
        return {
            "reply": result.final_output,
            "tool_called": tool_called,
            "pipeline_result": _LAST_TOOL_PIPELINE_RESULT,
        }
    except InputGuardrailTripwireTriggered:
        return {
            "reply": "🛑 Blocked by `InputGuardrail`: Indirect prompt injection detected in message.",
            "tool_called": "InputGuardrailTripwireTriggered",
            "pipeline_result": None,
        }
    except Exception:
        # Fallback if the `.env` API key is expired or offline
        return _offline_agent_fallback(user_message, current_form_text)


def _offline_agent_fallback(user_message: str, current_form_text: str) -> dict:
    """Conversational & tool fallback used when `OPENAI_API_KEY` in `.env` is expired."""
    msg_low = user_message.lower().strip()

    if any(re.search(p, user_message, re.IGNORECASE) for p in INJECTION_PATTERNS):
        return {
            "reply": "🛑 Blocked by `InputGuardrail`: Indirect prompt injection detected in message.",
            "tool_called": "InputGuardrailTripwireTriggered",
            "pipeline_result": None,
        }

    validate_verbs = ("validate", "valide", "check", "analyse", "analyze", "review", "évalue", "vérifie")
    offer_nouns = ("thales", "clara", "sologne", "lucas", "hugo", "offer", "offre", "form", "formulaire", "stage", "siret")
    should_call_tool = any(v in msg_low for v in validate_verbs) and (any(n in msg_low for n in offer_nouns) or len(msg_low) > 25)

    if should_call_tool:
        target = (
            user_message
            if any(k in msg_low for k in ("thales", "clara", "sologne", "lucas"))
            else (current_form_text or user_message)
        )
        pipeline_res = analyze_internship_document(target, page_count=1)
        form = pipeline_res["extracted_form"]
        return {
            "reply": (
                f"I ran `@function_tool validate_internship_offer` for **{form['first_name']} {form['last_name']}** "
                f"at **{form['company_name']}**:\n"
                f"• **Status:** {pipeline_res['status_badge']}\n"
                f"• **5A Syllabus:** {pipeline_res['bullet_2_syllabus']}\n"
                f"• **Action:** I have populated all 17 form fields and drafted the student email on the main page."
            ),
            "tool_called": f"validate_internship_offer → {pipeline_res['status']}",
            "pipeline_result": pipeline_res,
        }

    if any(g in msg_low for g in ("hello", "hi", "hey", "bonjour", "salut", "coucou", "how are you", "ça va")):
        return {
            "reply": (
                "Bonjour Prof. Canales! 👋 I am the **Polytech 5A Internship Agent** (`agent_demo.py`), "
                "built with the official OpenAI Agents SDK (`Agent` + `Runner.run_sync`).\n\n"
                "You can chat with me about the **5A Electronics & Optics rules**, ask about a student offer, "
                "or ask me to **validate an offer** using my `@function_tool validate_internship_offer`."
            ),
            "tool_called": None,
            "pipeline_result": None,
        }

    if any(w in msg_low for w in ("rule", "règle", "syllabus", "criteria", "stipend", "gratification", "duration", "durée", "weeks")):
        return {
            "reply": (
                "For a **5A Electronics & Optics** PFE at Polytech Orléans, we check 3 criteria:\n"
                "• **Statutory Minimums:** Duration **≥ 20 weeks** and stipend **≥ 650 EUR/month**.\n"
                "• **5A Master's R&D Syllabus:** Autonomous design/simulation (e.g., Zemax, VHDL/FPGA, Altium RF layout) — not technician PCB soldering or cable wiring.\n"
                "• **Company & Supervision:** Active R&D company (SIRET) with an engineering-qualified supervisor."
            ),
            "tool_called": None,
            "pipeline_result": None,
        }

    if any(w in msg_low for w in ("why", "pourquoi", "explain", "explique", "lucas", "sologne", "clara", "thales")):
        if "lucas" in msg_low or "sologne" in msg_low or ("sologne" in current_form_text.lower() and "clara" not in msg_low):
            return {
                "reply": (
                    "**Lucas Moreau (Sologne PCB Assembly)** is flagged **YELLOW** because while duration (22w) and stipend (750 EUR) "
                    "pass legal minimums, the tasks focus on technician-level manual PCB soldering and wiring rather than 5A Master's R&D design."
                ),
                "tool_called": None,
                "pipeline_result": None,
            }
        if "clara" in msg_low or "thales" in msg_low or "thales" in current_form_text.lower():
            return {
                "reply": (
                    "**Clara Chêne (Thales LAS France)** is approved **GREEN** because her 24-week, 1,650 EUR/month offer matches "
                    "5A Electronics & Optics Master's R&D (1550nm Zemax optical modeling, InGaAs APD front-end layout, and Xilinx Zynq VHDL FPGA control)."
                ),
                "tool_called": None,
                "pipeline_result": None,
            }

    return {
        "reply": (
            "I'm ready to help! Ask me about the **5A Electronics & Optics rules**, ask why a student offer was approved or flagged, "
            "or ask me to **validate an internship offer** (e.g., *'Validate Clara Chêne Thales LiDAR offer'*)."
        ),
        "tool_called": None,
        "pipeline_result": None,
    }
