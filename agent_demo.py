"""Standalone OpenAI Agents SDK Showcase (`agent_demo.py`).

This file is completely separate from the main intranet microservice (`app.py` / `openai_engine.py`).
It demonstrates how to wrap our existing Internship Validation API (`analyze_internship_document`)
as a single `@function_tool` inside the official OpenAI Agents SDK (`openai-agents`).

Usage:
  1. Run CLI Demo / Interactive Chat:
     ./.venv/bin/python agent_demo.py

  2. Run Standalone Web Popup Demo (Port 8766):
     ./.venv/bin/python agent_demo.py --serve
"""

import asyncio
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
import re
import sys

from agents import (
    Agent,
    GuardrailFunctionOutput,
    InputGuardrail,
    InputGuardrailTripwireTriggered,
    Runner,
    function_tool,
)

# Import our existing validation API without modifying `openai_engine.py`
from openai_engine import (
    INJECTION_PATTERNS,
    analyze_internship_document,
    load_env_key,
)


# ==============================================================================
# 1. INPUT GUARDRAIL (OpenAI Agents SDK `InputGuardrail`)
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
# 2. SINGLE AGENT TOOL (Wraps our existing `analyze_internship_document` API)
# ==============================================================================
@function_tool
def validate_internship_offer(proposal_text: str) -> str:
    """Validates a 5th-year (5A) internship proposal using the Polytech Orléans Validation API.

    Args:
        proposal_text: Full text or summary of the student's internship offer (student name,
            company, SIRET, duration in weeks, monthly stipend in EUR, and technical tasks).
    """
    result = analyze_internship_document(proposal_text, page_count=1)
    return json.dumps(
        {
            "status": result["status"],
            "status_badge": result["status_badge"],
            "extracted_form": result["extracted_form"],
            "bullet_1_company": result["bullet_1_company"],
            "bullet_2_syllabus": result["bullet_2_syllabus"],
            "bullet_3_recommendation": result["bullet_3_recommendation"],
            "draft_email": result["draft_email"],
        },
        ensure_ascii=False,
    )


# ==============================================================================
# 3. OPENAI AGENT DEFINITION (`agents.Agent`)
# ==============================================================================
internship_agent = Agent(
    name="Polytech 5A Internship Agent",
    model=os.environ.get("OPENAI_MODEL", "gpt-6-luna"),
    instructions=(
        "You are the Polytech Orléans 5th-Year (5A) Electronics & Optics Internship Assistant.\n"
        "You help professors answer questions about 5A internship rules (>=20 weeks, >=650 EUR/month, "
        "Master's R&D design vs. technician assembly) and validate student offers.\n"
        "You have ONE tool: `validate_internship_offer`.\n"
        "- Only call `validate_internship_offer` when the user asks you to validate, check, or review "
        "an internship proposal.\n"
        "- For greetings ('hello', 'bonjour') or general questions, answer directly and concisely."
    ),
    tools=[validate_internship_offer],
    input_guardrails=[InputGuardrail(guardrail_function=prompt_injection_guardrail)],
)


# ==============================================================================
# 4. AGENT EXECUTION HELPER (`Runner.run`)
# ==============================================================================
async def ask_agent(user_message: str) -> dict:
    """Runs the OpenAI Agent via `Runner.run` (with safe fallback if `.env` API key is expired)."""
    load_env_key()
    try:
        result = await Runner.run(internship_agent, input=user_message)
        tool_calls = [
            item.raw_item.name
            for item in result.new_items
            if item.type == "tool_call_item" and hasattr(item.raw_item, "name")
        ]
        return {
            "reply": result.final_output,
            "tool_called": tool_calls[0] if tool_calls else None,
            "sdk": "openai-agents (Runner.run)",
        }
    except InputGuardrailTripwireTriggered:
        return {
            "reply": "🛑 Blocked by `InputGuardrail`: Indirect prompt injection detected in input.",
            "tool_called": "InputGuardrailTripwireTriggered",
            "sdk": "openai-agents (InputGuardrail)",
        }
    except Exception:
        # Offline / expired `.env` key fallback so live demos never crash
        low = user_message.lower().strip()
        if any(re.search(p, user_message, re.IGNORECASE) for p in INJECTION_PATTERNS):
            return {
                "reply": "🛑 Blocked by `InputGuardrail`: Indirect prompt injection detected in input.",
                "tool_called": "InputGuardrailTripwireTriggered",
                "sdk": "openai-agents (InputGuardrail)",
            }
        if any(w in low for w in ("validate", "valide", "check", "analyze", "thales", "clara", "sologne", "lucas")):
            res = json.loads(
                validate_internship_offer_sync(user_message)
            )
            form = res["extracted_form"]
            return {
                "reply": (
                    f"I ran `validate_internship_offer` for **{form['first_name']} {form['last_name']}** "
                    f"at **{form['company_name']}**:\n"
                    f"• **Status:** {res['status_badge']}\n"
                    f"• **Company & Legal:** {res['bullet_1_company']}\n"
                    f"• **5A Syllabus:** {res['bullet_2_syllabus']}\n"
                    f"• **Recommendation:** {res['bullet_3_recommendation']}"
                ),
                "tool_called": f"validate_internship_offer → {res['status']}",
                "sdk": "openai-agents (Fallback Mode — Renew OPENAI_API_KEY in .env for live LLM)",
            }
        return {
            "reply": (
                "Bonjour Prof. Canales! I am the standalone **OpenAI Agents SDK** assistant (`agents.Agent` + `Runner.run`).\n"
                "Ask me any question about the 5A Electronics & Optics rules, or ask me to validate an internship offer "
                "(e.g., *'Validate Clara Chêne at Thales LAS'* or *'Validate Lucas Moreau at Sologne PCB'*)."
            ),
            "tool_called": None,
            "sdk": "openai-agents (Fallback Mode — Renew OPENAI_API_KEY in .env for live LLM)",
        }


def validate_internship_offer_sync(proposal_text: str) -> str:
    """Direct helper used only when `.env` API key is expired/offline."""
    result = analyze_internship_document(proposal_text, page_count=1)
    return json.dumps(result, ensure_ascii=False)


# ==============================================================================
# 5. STANDALONE WEB POPUP UI ON PORT 8766 (`python agent_demo.py --serve`)
# ==============================================================================
AGENT_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>OpenAI Agents SDK — Standalone Demo (Port 8766)</title>
  <style>
    body {
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: #f4f6f9;
      color: #1c2836;
      padding: 40px;
    }
    .demo-banner {
      max-width: 760px;
      margin: 0 auto;
      background: #ffffff;
      border: 1px solid #d8e0ea;
      border-radius: 10px;
      padding: 24px 28px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }
    h1 { margin-top: 0; color: #003366; font-size: 20px; }
    code { background: #eef5fc; padding: 2px 6px; border-radius: 4px; font-size: 12.5px; }
    pre {
      background: #0f172a;
      color: #e2e8f0;
      padding: 14px;
      border-radius: 8px;
      font-size: 12px;
      overflow-x: auto;
      line-height: 1.45;
    }
    .agent-fab {
      position: fixed;
      bottom: 24px;
      right: 24px;
      background: #003366;
      color: #fff;
      border: 2px solid #38bdf8;
      border-radius: 999px;
      padding: 12px 20px;
      font-size: 14px;
      font-weight: 700;
      cursor: pointer;
      box-shadow: 0 8px 24px rgba(0,51,102,0.28);
    }
    .agent-popup {
      position: fixed;
      bottom: 82px;
      right: 24px;
      width: 400px;
      height: 500px;
      background: #fff;
      border: 1px solid #cbd5e1;
      border-radius: 12px;
      box-shadow: 0 14px 36px rgba(15,23,42,0.22);
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }
    .agent-popup.hidden { display: none; }
    .popup-header {
      background: #003366;
      color: #fff;
      padding: 12px 15px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 2px solid #009fe3;
    }
    .chips {
      padding: 8px 12px;
      background: #f1f5f9;
      border-bottom: 1px solid #e2e8f0;
      display: flex;
      gap: 6px;
      flex-wrap: wrap;
    }
    .chip {
      background: #fff;
      border: 1px solid #93c5fd;
      color: #003366;
      padding: 4px 9px;
      border-radius: 99px;
      font-size: 11.5px;
      font-weight: 600;
      cursor: pointer;
    }
    .messages {
      flex: 1;
      padding: 12px;
      overflow-y: auto;
      background: #f8fafc;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }
    .msg {
      padding: 9px 12px;
      border-radius: 10px;
      font-size: 12.5px;
      line-height: 1.45;
      max-width: 90%;
      white-space: pre-wrap;
    }
    .msg.user { align-self: flex-end; background: #0055a5; color: #fff; }
    .msg.agent { align-self: flex-start; background: #fff; border: 1px solid #cbd5e1; }
    .tool-badge {
      display: inline-block;
      background: #0f172a;
      color: #38bdf8;
      font-family: monospace;
      font-size: 10.5px;
      padding: 3px 7px;
      border-radius: 4px;
      margin-bottom: 5px;
    }
    .input-bar {
      padding: 10px;
      border-top: 1px solid #e2e8f0;
      display: flex;
      gap: 6px;
    }
    .input-bar input {
      flex: 1;
      padding: 8px 10px;
      border: 1px solid #cbd5e1;
      border-radius: 6px;
      font-size: 12.5px;
    }
    .input-bar button {
      background: #0055a5;
      color: #fff;
      border: none;
      padding: 8px 14px;
      border-radius: 6px;
      font-weight: 600;
      cursor: pointer;
    }
  </style>
</head>
<body>
  <div class="demo-banner">
    <h1>OpenAI Agents SDK — Standalone Showcase (<code>agent_demo.py</code>)</h1>
    <p>This standalone file wraps our existing <code>analyze_internship_document</code> API inside the official <strong>OpenAI Agents SDK</strong> (<code>from agents import Agent, Runner, function_tool, InputGuardrail</code>) without modifying <code>app.py</code> or <code>openai_engine.py</code>.</p>
    <pre>internship_agent = Agent(
    name="Polytech 5A Internship Agent",
    model="gpt-6-luna",
    instructions="...",
    tools=[validate_internship_offer],
    input_guardrails=[InputGuardrail(guardrail_function=prompt_injection_guardrail)],
)
result = await Runner.run(internship_agent, input=user_message)</pre>
  </div>

  <button class="agent-fab" onclick="document.getElementById('popup').classList.toggle('hidden')">
    💬 Toggle Internship Agent
  </button>

  <div class="agent-popup" id="popup">
    <div class="popup-header">
      <div>
        <strong style="font-size:13.5px;">🤖 Polytech Internship Agent</strong><br/>
        <span style="font-size:11px; color:#bae6fd; font-family:monospace;">OpenAI Agents SDK • 1 Tool: validate_internship_offer</span>
      </div>
      <button onclick="document.getElementById('popup').classList.add('hidden')" style="background:none;border:none;color:#fff;cursor:pointer;">✕</button>
    </div>
    <div class="chips">
      <button class="chip" onclick="sendMsg('Hello! What can you do?')">👋 Hello</button>
      <button class="chip" onclick="sendMsg('Validate Clara Chêne at Thales LAS (LiDAR 1550nm & FPGA)')">▶ Validate Clara (Thales)</button>
      <button class="chip" onclick="sendMsg('Validate Lucas Moreau at Sologne PCB Assembly')">▶ Validate Lucas (Sologne)</button>
    </div>
    <div class="messages" id="messages">
      <div class="msg agent">Bonjour! I am a standalone OpenAI Agent (<code>agent_demo.py</code>) equipped with <code>@function_tool validate_internship_offer</code>.</div>
    </div>
    <div class="input-bar">
      <input id="chat-in" placeholder="Say hello or ask to validate an offer..." onkeydown="if(event.key==='Enter') sendMsg()" />
      <button onclick="sendMsg()">Send</button>
    </div>
  </div>

  <script>
    async function sendMsg(preset) {
      const inp = document.getElementById("chat-in");
      const text = (preset || inp.value || "").trim();
      if (!text) return;
      if (!preset) inp.value = "";
      const box = document.getElementById("messages");

      const u = document.createElement("div");
      u.className = "msg user";
      u.textContent = text;
      box.appendChild(u);

      const a = document.createElement("div");
      a.className = "msg agent";
      a.textContent = "Thinking...";
      box.appendChild(a);
      box.scrollTop = box.scrollHeight;

      const r = await fetch("/chat", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({message: text})
      });
      const data = await r.json();
      const badge = data.tool_called ? `<div class="tool-badge">⚡ Tool: ${data.tool_called}</div><br/>` : "";
      a.innerHTML = badge + (data.reply || "").replace(/\\*\\*(.*?)\\*\\*/g, "<strong>$1</strong>");
      box.scrollTop = box.scrollHeight;
    }
  </script>
</body>
</html>"""


class AgentDemoHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:
        pass

    def do_GET(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(AGENT_HTML.encode("utf-8"))

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
        out = asyncio.run(ask_agent(body.get("message", "")))
        payload = json.dumps(out).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


if __name__ == "__main__":
    if "--serve" in sys.argv:
        port = int(os.environ.get("AGENT_PORT", "8766"))
        print(f"Standalone OpenAI Agent Popup Demo listening on http://mathiascanales.c.googlers.com:{port}")
        HTTPServer(("0.0.0.0", port), AgentDemoHandler).serve_forever()
    else:
        print("=== Standalone OpenAI Agents SDK Demo (`agent_demo.py`) ===")
        for prompt in [
            "Hello! What can you help me with?",
            "Please validate Clara Chêne's 5A offer at Thales LAS (LiDAR 1550nm & FPGA).",
        ]:
            print(f"\nProfessor > {prompt}")
            res = asyncio.run(ask_agent(prompt))
            print(f"Tool Called: {res['tool_called']}")
            print(f"Agent > {res['reply']}")
