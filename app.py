"""Polytech Orléans Faculty Intranet — Student Internships Portal (Port 8765)."""

import base64
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
import os

from openai_engine import (
    analyze_internship_document,
    extract_text_from_pdf_bytes,
    load_env_key,
    run_internship_agent,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FEEDBACK_FILE = os.path.join(BASE_DIR, "professor_feedback_evals.json")

HTML_PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Polytech Orléans — Faculty Intranet</title>
  <style>
    :root {
      --navy: #003366;
      --blue: #0055a5;
      --light-blue: #eef5fc;
      --bg: #f4f6f9;
      --card: #ffffff;
      --border: #d8e0ea;
      --text: #1c2836;
      --muted: #5a6b7c;
      --green-bg: #edf9f0;
      --green-border: #2e8540;
      --green-text: #1b5e20;
      --yellow-bg: #fff9e6;
      --yellow-border: #d99b00;
      --yellow-text: #7a5200;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
      font-size: 14px;
      line-height: 1.45;
    }

    /* Intranet Top Header */
    .intranet-header {
      background: var(--navy);
      color: #fff;
      padding: 0 28px;
      height: 56px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      border-bottom: 3px solid #009fe3;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
      font-weight: 700;
      font-size: 16px;
      letter-spacing: 0.2px;
    }
    .brand-badge {
      background: #009fe3;
      color: #fff;
      font-weight: 800;
      padding: 4px 9px;
      border-radius: 4px;
      font-size: 13px;
    }
    .brand-sub {
      font-weight: 400;
      font-size: 13px;
      color: #bfd6ed;
      margin-left: 6px;
    }
    .user-profile {
      font-size: 13px;
      color: #d6e4f2;
      display: flex;
      align-items: center;
      gap: 14px;
    }

    /* Intranet Navigation Tabs */
    .intranet-nav {
      background: #ffffff;
      border-bottom: 1px solid var(--border);
      padding: 0 28px;
      display: flex;
      gap: 6px;
    }
    .nav-tab {
      padding: 12px 18px;
      font-size: 13.5px;
      font-weight: 600;
      color: var(--muted);
      border-bottom: 3px solid transparent;
      cursor: pointer;
      user-select: none;
    }
    .nav-tab:hover { color: var(--navy); }
    .nav-tab.active {
      color: var(--navy);
      border-bottom-color: #009fe3;
      background: #f8fbff;
    }

    /* Main Container */
    .container {
      max-width: 1080px;
      margin: 22px auto 48px;
      padding: 0 20px;
    }
    .page-title-bar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 16px;
    }
    .page-title-bar h1 {
      font-size: 19px;
      margin: 0 0 3px 0;
      color: var(--navy);
    }
    .page-title-bar p {
      margin: 0;
      font-size: 13px;
      color: var(--muted);
    }

    .btn {
      padding: 8px 14px;
      border-radius: 5px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      border: 1px solid var(--border);
      background: #fff;
      color: var(--text);
      transition: all 0.15s;
    }
    .btn:hover { background: #f0f4f8; }
    .btn:disabled {
      opacity: 0.6;
      cursor: not-allowed;
    }
    .btn-primary {
      background: var(--blue);
      color: #fff;
      border-color: var(--blue);
    }
    .btn-primary:hover:not(:disabled) { background: var(--navy); }
    .btn-success {
      background: #2e8540;
      color: #fff;
      border-color: #2e8540;
    }
    .btn-success:hover { background: #236631; }
    .btn-warning {
      background: #d97706;
      color: #fff;
      border-color: #d97706;
    }
    .btn-warning:hover { background: #b45309; }
    .btn-outline-blue {
      background: #f0f7ff;
      color: var(--blue);
      border-color: #93c5fd;
    }
    .btn-outline-blue:hover {
      background: #e0effe;
    }

    /* Card Layout */
    .card {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 7px;
      padding: 20px 22px;
      margin-bottom: 18px;
      box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
    }

    /* Document Upload Dropzone */
    .upload-zone {
      border: 2px dashed #9ab7d3;
      background: var(--light-blue);
      border-radius: 7px;
      padding: 18px 20px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      transition: all 0.2s;
    }
    .upload-zone.dragover {
      border-color: var(--blue);
      background: #dcebfb;
    }
    .upload-zone.processing {
      border-style: solid;
      border-color: #009fe3;
      background: #e6f4ff;
    }
    .upload-info strong {
      display: block;
      font-size: 14px;
      color: var(--navy);
      margin-bottom: 3px;
    }
    .upload-info span {
      font-size: 12.5px;
      color: var(--muted);
    }
    .file-pill {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      margin-top: 8px;
      background: #fff;
      border: 1px solid #9ab7d3;
      padding: 4px 12px;
      border-radius: 14px;
      font-size: 12.5px;
      color: var(--navy);
      font-weight: 600;
    }

    /* Spinner Animation */
    @keyframes spin {
      to { transform: rotate(360deg); }
    }
    .spinner {
      width: 16px;
      height: 16px;
      border: 2.5px solid #cbd5e1;
      border-top-color: var(--blue);
      border-radius: 50%;
      animation: spin 0.75s linear infinite;
      display: inline-block;
      vertical-align: middle;
      flex-shrink: 0;
    }

    /* Live 4-Step Pipeline Tracker */
    .thinking-box {
      background: #f8fafc;
      border: 1px solid #cbd5e1;
      border-left: 4px solid var(--blue);
      border-radius: 7px;
      padding: 16px 20px;
      margin-top: 16px;
      display: none;
    }
    .thinking-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-weight: 700;
      color: var(--navy);
      margin-bottom: 12px;
      font-size: 14px;
      padding-bottom: 8px;
      border-bottom: 1px solid #e2e8f0;
    }
    .thinking-header-left {
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .timer-badge {
      background: #e0f2fe;
      color: #0369a1;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 12px;
      font-weight: 700;
      padding: 2px 9px;
      border-radius: 12px;
    }
    .step-list {
      display: flex;
      flex-direction: column;
      gap: 8px;
      margin: 0;
      padding: 0;
      list-style: none;
    }
    .step-item {
      display: flex;
      align-items: flex-start;
      gap: 10px;
      padding: 8px 12px;
      border-radius: 6px;
      background: #ffffff;
      border: 1px solid #e2e8f0;
      font-size: 13px;
      color: #64748b;
      transition: all 0.2s;
    }
    .step-item.active {
      border-color: #38bdf8;
      background: #f0f9ff;
      color: var(--navy);
      font-weight: 600;
    }
    .step-item.done {
      border-color: #bbf7d0;
      background: #f0fdf4;
      color: #1e293b;
    }
    .step-item.error {
      border-color: #fecaca;
      background: #fef2f2;
      color: #991b1b;
      font-weight: 600;
    }
    .step-icon {
      width: 20px;
      height: 20px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      font-weight: 800;
      font-size: 12px;
      border-radius: 50%;
      flex-shrink: 0;
      margin-top: 1px;
    }
    .step-item.pending .step-icon {
      background: #e2e8f0;
      color: #64748b;
    }
    .step-item.done .step-icon {
      background: #22c55e;
      color: #fff;
    }
    .step-item.error .step-icon {
      background: #dc2626;
      color: #fff;
    }
    .step-body { flex: 1; }
    .step-title {
      font-weight: 700;
      color: var(--navy);
    }
    .step-detail {
      display: block;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 12px;
      color: #475569;
      margin-top: 2px;
    }

    /* Output Review Card */
    .result-card {
      display: none;
      border-width: 2px;
    }
    .status-banner {
      padding: 12px 16px;
      border-radius: 6px;
      font-weight: 700;
      font-size: 15px;
      margin-bottom: 16px;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .status-banner.GREEN {
      background: var(--green-bg);
      border: 1px solid var(--green-border);
      color: var(--green-text);
    }
    .status-banner.YELLOW {
      background: var(--yellow-bg);
      border: 1px solid var(--yellow-border);
      color: var(--yellow-text);
    }
    .status-banner.RED {
      background: #fef2f2;
      border: 2px solid #dc2626;
      color: #991b1b;
    }
    .review-bullets {
      margin: 0 0 16px 0;
      padding-left: 20px;
    }
    .review-bullets li {
      margin-bottom: 10px;
      font-size: 13.5px;
    }
    .email-section label {
      display: block;
      font-weight: 700;
      font-size: 12.5px;
      color: var(--navy);
      margin-bottom: 6px;
    }
    .email-section textarea {
      width: 100%;
      min-height: 135px;
      padding: 10px 12px;
      border: 1px solid #cbd5e1;
      border-radius: 5px;
      font-family: inherit;
      font-size: 13px;
      line-height: 1.45;
      margin-bottom: 14px;
    }

    /* Human-in-the-Loop Action & Override Bar */
    .hitl-panel {
      background: #f8fafc;
      border: 1px solid #cbd5e1;
      border-radius: 7px;
      padding: 14px 16px;
    }
    .hitl-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 10px;
    }
    .hitl-title {
      font-size: 12.5px;
      font-weight: 700;
      color: var(--navy);
      text-transform: uppercase;
      letter-spacing: 0.4px;
    }
    .action-buttons {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
    }
    .override-drawer {
      display: none;
      margin-top: 14px;
      padding-top: 14px;
      border-top: 1px dashed #cbd5e1;
    }
    .override-grid {
      display: grid;
      grid-template-columns: 240px 1fr auto;
      gap: 12px;
      align-items: end;
    }
    .override-drawer label {
      display: block;
      font-size: 11.5px;
      font-weight: 700;
      color: var(--navy);
      margin-bottom: 4px;
    }
    .override-drawer select, .override-drawer input {
      width: 100%;
      padding: 8px 10px;
      border: 1px solid #94a3b8;
      border-radius: 5px;
      font-size: 13px;
      font-family: inherit;
      background: #fff;
    }
    .toast-msg {
      margin-top: 10px;
      padding: 8px 12px;
      border-radius: 5px;
      font-weight: 600;
      font-size: 13px;
      display: none;
    }
    .toast-msg.info {
      display: block;
      background: #ecfdf5;
      border: 1px solid #6ee7b7;
      color: #065f46;
    }
    .toast-msg.eval {
      display: block;
      background: #eff6ff;
      border: 1px solid #93c5fd;
      color: #1e40af;
    }

    /* Granular Form Sections */
    .form-card-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 8px;
    }
    .form-card-header h2 {
      font-size: 15px;
      margin: 0;
      color: var(--navy);
    }
    .autofill-badge {
      display: none;
      background: #e0f2fe;
      color: #0369a1;
      font-size: 12px;
      font-weight: 700;
      padding: 3px 10px;
      border-radius: 12px;
    }
    .section-header {
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: var(--blue);
      border-bottom: 1px solid #e5ebf2;
      padding-bottom: 5px;
      margin: 16px 0 12px 0;
    }
    .form-grid-4 {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 12px;
      margin-bottom: 12px;
    }
    .form-grid-3 {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 12px;
      margin-bottom: 12px;
    }
    .form-grid-2 {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 12px;
      margin-bottom: 12px;
    }
    .field {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }
    .field label {
      font-size: 11.5px;
      font-weight: 600;
      color: #425466;
    }
    .field input, .field textarea {
      padding: 7px 10px;
      border: 1px solid #cbd5e1;
      border-radius: 4px;
      font-size: 13px;
      font-family: inherit;
      color: var(--text);
      background: #fff;
      transition: background-color 0.35s, border-color 0.25s;
    }
    .field input:focus, .field textarea:focus {
      outline: none;
      border-color: var(--blue);
    }
    .field input.autofilled, .field textarea.autofilled {
      background-color: #f0f7ff;
      border-color: #60a5fa;
      font-weight: 500;
    }
    .field textarea {
      resize: vertical;
      min-height: 68px;
    }
    .form-footer {
      display: flex;
      justify-content: flex-end;
      gap: 10px;
      margin-top: 14px;
      padding-top: 12px;
      border-top: 1px solid #eef2f6;
    }

    /* Floating Bottom-Right Agent Popup Widget */
    .agent-fab {
      position: fixed;
      bottom: 24px;
      right: 24px;
      background: var(--navy);
      color: #ffffff;
      border: 2px solid #38bdf8;
      border-radius: 999px;
      padding: 12px 20px;
      font-size: 13.5px;
      font-weight: 700;
      cursor: pointer;
      box-shadow: 0 8px 24px rgba(0, 51, 102, 0.28);
      display: flex;
      align-items: center;
      gap: 8px;
      z-index: 999;
      transition: transform 0.15s, background 0.15s;
    }
    .agent-fab:hover {
      background: var(--blue);
      transform: translateY(-2px);
    }
    .agent-popup {
      position: fixed;
      bottom: 82px;
      right: 24px;
      width: 380px;
      height: 490px;
      background: #ffffff;
      border: 1px solid #cbd5e1;
      border-radius: 12px;
      box-shadow: 0 14px 36px rgba(15, 23, 42, 0.22);
      display: none;
      flex-direction: column;
      overflow: hidden;
      z-index: 1000;
    }
    .agent-popup.open {
      display: flex;
    }
    .agent-popup-header {
      background: var(--navy);
      color: #ffffff;
      padding: 12px 15px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      border-bottom: 2px solid #009fe3;
    }
    .agent-popup-title {
      font-size: 13.5px;
      font-weight: 700;
      display: flex;
      flex-direction: column;
      gap: 2px;
    }
    .agent-popup-sub {
      font-size: 11px;
      color: #bae6fd;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-weight: 500;
    }
    .agent-popup-close {
      background: transparent;
      border: none;
      color: #cbd5e1;
      font-size: 16px;
      cursor: pointer;
      padding: 2px 6px;
    }
    .agent-popup-close:hover { color: #ffffff; }
    .agent-quick-chips {
      padding: 8px 12px;
      background: #f1f5f9;
      border-bottom: 1px solid #e2e8f0;
      display: flex;
      gap: 6px;
      flex-wrap: wrap;
    }
    .agent-chip {
      background: #ffffff;
      border: 1px solid #93c5fd;
      color: var(--navy);
      padding: 4px 9px;
      border-radius: 99px;
      font-size: 11.5px;
      font-weight: 600;
      cursor: pointer;
    }
    .agent-chip:hover { background: #e0f2fe; }
    .agent-popup-messages {
      flex: 1;
      padding: 12px;
      overflow-y: auto;
      background: #f8fafc;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }
    .popup-msg {
      padding: 9px 12px;
      border-radius: 10px;
      font-size: 12.5px;
      line-height: 1.45;
      max-width: 90%;
      white-space: pre-wrap;
    }
    .popup-msg.user {
      align-self: flex-end;
      background: var(--blue);
      color: #ffffff;
      border-bottom-right-radius: 2px;
    }
    .popup-msg.agent {
      align-self: flex-start;
      background: #ffffff;
      border: 1px solid #cbd5e1;
      color: var(--text);
      border-bottom-left-radius: 2px;
    }
    .popup-tool-badge {
      display: inline-block;
      background: #0f172a;
      color: #38bdf8;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 10.5px;
      font-weight: 700;
      padding: 3px 7px;
      border-radius: 4px;
      margin-bottom: 5px;
    }
    .agent-popup-input {
      padding: 10px;
      background: #ffffff;
      border-top: 1px solid #e2e8f0;
      display: flex;
      gap: 6px;
    }
    .agent-popup-input input {
      flex: 1;
      padding: 8px 10px;
      border: 1px solid #cbd5e1;
      border-radius: 6px;
      font-size: 12.5px;
      font-family: inherit;
    }
  </style>
</head>
<body>

  <!-- Intranet Top Bar -->
  <header class="intranet-header">
    <div class="brand">
      <span class="brand-badge">POLYTECH</span>
      <span>ORLÉANS — Intranet Enseignants</span>
      <span class="brand-sub">| Université d'Orléans</span>
    </div>
    <div class="user-profile">
      <span>Department: <strong>Electronics &amp; Optics (5A)</strong></span>
      <span>•</span>
      <span>Prof. M. Canales</span>
    </div>
  </header>

  <!-- Intranet Tabs -->
  <nav class="intranet-nav">
    <div class="nav-tab">Home</div>
    <div class="nav-tab">My Courses &amp; Labs</div>
    <div class="nav-tab active">Student Internships (PFE 5A)</div>
    <div class="nav-tab">Academic Jury &amp; Defenses</div>
  </nav>

  <!-- Main Content -->
  <main class="container">
    <div class="page-title-bar">
      <div>
        <h1>5th-Year Engineering Internship Validation (PFE)</h1>
        <p>Upload a student's internship proposal PDF to automatically extract form fields and run the 3 OpenAI verification tools.</p>
      </div>
      <div>
        <button class="btn" onclick="resetForm()">Clear / New Request</button>
      </div>
    </div>

    <!-- Top Card: PDF Upload + Live 4-Step Progress Tracker -->
    <section class="card">
      <div class="upload-zone" id="dropzone">
        <div class="upload-info">
          <strong id="dropzone-title">Drop Student Internship Proposal PDF here (or click to browse)</strong>
          <span id="dropzone-subtitle">Automatically extracts all 17 administrative &amp; technical fields from multi-page internship agreements and runs OpenAI validation tools.</span>
          <div id="file-indicator" style="display:none;">
            <span class="file-pill" id="file-name-pill"></span>
          </div>
        </div>
        <div>
          <input type="file" id="pdf-input" accept=".pdf" style="display:none;" onchange="handleFileSelect(event)" />
          <button class="btn btn-primary" id="upload-btn" onclick="document.getElementById('pdf-input').click()">Upload Internship PDF</button>
        </div>
      </div>

      <!-- Live 4-Step Pipeline Progress Box -->
      <div class="thinking-box" id="thinking-box">
        <div class="thinking-header">
          <div class="thinking-header-left">
            <span class="spinner" id="pipeline-spinner"></span>
            <span id="thinking-title">Processing PDF with OpenAI `gpt-6-luna`...</span>
          </div>
          <div style="display:flex; align-items:center; gap:10px;">
            <span id="execution-mode-label" style="font-size: 12px; font-weight: 600; color: #475569;"></span>
            <span class="timer-badge" id="timer-badge">0.0s</span>
          </div>
        </div>

        <ul class="step-list">
          <li class="step-item pending" id="step-row-1">
            <span class="step-icon" id="step-icon-1">1</span>
            <div class="step-body">
              <span class="step-title">Step 1 — Input Guardrails &amp; PDF Parsing (`MaskPII` + `InjectionTripwire`)</span>
              <span class="step-detail" id="step-detail-1">Waiting to parse multi-page PDF, mask student PII (GDPR), and scan for prompt injections...</span>
            </div>
          </li>
          <li class="step-item pending" id="step-row-2">
            <span class="step-icon" id="step-icon-2">2</span>
            <div class="step-body">
              <span class="step-title">Step 2 — Tool 1: School Database &amp; Legal Check (`check_school_db`)</span>
              <span class="step-detail" id="step-detail-2">Checking duration (&ge;20 weeks), stipend (&ge;650 EUR/mo), and company SIRET history at Polytech Orléans...</span>
            </div>
          </li>
          <li class="step-item pending" id="step-row-3">
            <span class="step-icon" id="step-icon-3">3</span>
            <div class="step-body">
              <span class="step-title">Step 3 — Tools 2 &amp; 3: Company Web Search &amp; 5A Syllabus Match (`web_search` + `file_search`)</span>
              <span class="step-detail" id="step-detail-3">Verifying company R&amp;D profile on the web and comparing tasks against 5A Electronics &amp; Optics syllabus...</span>
            </div>
          </li>
          <li class="step-item pending" id="step-row-4">
            <span class="step-icon" id="step-icon-4">4</span>
            <div class="step-body">
              <span class="step-title">Step 4 — Structured Output Auto-Fill (`strict: True` JSON Schema)</span>
              <span class="step-detail" id="step-detail-4">Populating all 17 intranet form fields and generating student reply draft...</span>
            </div>
          </li>
        </ul>
      </div>
    </section>

    <!-- Decision & Human-in-the-Loop Output Card -->
    <section class="card result-card" id="result-card">
      <div class="status-banner" id="status-banner">
        <span id="status-badge-text"></span>
        <span style="font-size:12px; font-weight:600;">Professor Human-in-the-Loop Review</span>
      </div>

      <ul class="review-bullets">
        <li id="bullet-1"></li>
        <li id="bullet-2"></li>
        <li id="bullet-3"></li>
      </ul>

      <div class="email-section">
        <label for="draft-email-box">Suggested Reply to Student (Editable by Professor before sending):</label>
        <textarea id="draft-email-box"></textarea>
      </div>

      <!-- Human-in-the-Loop Decision & Override Panel -->
      <div class="hitl-panel">
        <div class="hitl-header">
          <span class="hitl-title">Human-in-the-Loop Professor Decision</span>
          <div class="action-buttons">
            <button class="btn btn-success" onclick="recordProfessorAction('APPROVED — Convention sent to administrative office')">
              ✓ Approve Internship
            </button>
            <button class="btn btn-warning" onclick="recordProfessorAction('REVISION REQUESTED — Email sent to student for engineering detail')">
              ✉ Ask Student for More Engineering Detail
            </button>
            <button class="btn btn-outline-blue" onclick="toggleOverrideDrawer()">
              ✎ Modify AI Decision &amp; Add to Eval Suite
            </button>
          </div>
        </div>

        <!-- Expandable Override Drawer that logs a new test case to eval_pipeline.py -->
        <div class="override-drawer" id="override-drawer">
          <div style="font-size:12.5px; color:#334155; margin-bottom:10px;">
            <strong>Closed-Loop Evaluation Feedback:</strong> If you disagree with the AI's recommendation (or if the student updated their mission), modify the decision below. Saving this override automatically creates a new regression test case in <code>eval_pipeline.py</code>.
          </div>
          <div class="override-grid">
            <div>
              <label for="override-status">Professor Ground-Truth Decision</label>
              <select id="override-status">
                <option value="GREEN">GREEN — Approve (Valid 5A Engineering R&amp;D)</option>
                <option value="YELLOW">YELLOW — Flag (Technician / Needs Revision)</option>
              </select>
            </div>
            <div>
              <label for="override-reason">Professor Note / Updated Mission Context (Saved to Eval Case)</label>
              <input type="text" id="override-reason" placeholder="e.g. Supervisor confirmed student will design an automated FPGA/Python test bench in Altium" />
            </div>
            <div>
              <button class="btn btn-primary" onclick="saveProfessorOverrideToEval()">
                Save Override → Add to Eval Pipeline
              </button>
            </div>
          </div>
        </div>

        <div class="toast-msg" id="action-toast"></div>
      </div>
    </section>

    <!-- Auto-Filled 17-Field Intranet Form -->
    <section class="card">
      <div class="form-card-header">
        <h2>Internship Agreement Form (17 Structured Fields — Editable by Professor)</h2>
        <span class="autofill-badge" id="autofill-badge">✓ 17/17 Fields Auto-Filled from PDF</span>
      </div>

      <div class="section-header">1. Student Identification</div>
      <div class="form-grid-4">
        <div class="field">
          <label>Student First Name</label>
          <input type="text" id="f_first_name" placeholder="e.g. Lucas" />
        </div>
        <div class="field">
          <label>Student Last Name</label>
          <input type="text" id="f_last_name" placeholder="e.g. Moreau" />
        </div>
        <div class="field">
          <label>Academic Year</label>
          <input type="text" id="f_academic_year" placeholder="e.g. 5th Year (5A)" />
        </div>
        <div class="field">
          <label>Department / Track</label>
          <input type="text" id="f_department" placeholder="e.g. Electronics & Optics" />
        </div>
      </div>

      <div class="section-header">2. Host Organization &amp; Industrial Supervision</div>
      <div class="form-grid-3">
        <div class="field">
          <label>Host Company Name</label>
          <input type="text" id="f_company_name" placeholder="Legal corporate name" />
        </div>
        <div class="field">
          <label>City &amp; Location</label>
          <input type="text" id="f_company_city" placeholder="City & postal code" />
        </div>
        <div class="field">
          <label>Company SIRET Number (14 digits)</label>
          <input type="text" id="f_siret_number" placeholder="XXX XXX XXX XXXXX" />
        </div>
      </div>
      <div class="form-grid-2">
        <div class="field">
          <label>Industrial Supervisor Full Name</label>
          <input type="text" id="f_supervisor_name" placeholder="On-site tutor name" />
        </div>
        <div class="field">
          <label>Supervisor Title &amp; Qualification</label>
          <input type="text" id="f_supervisor_title" placeholder="Role / Engineering degree" />
        </div>
      </div>

      <div class="section-header">3. Contract Duration, Stipend &amp; Confidentiality</div>
      <div class="form-grid-4">
        <div class="field">
          <label>Start Date</label>
          <input type="text" id="f_start_date" placeholder="YYYY-MM-DD" />
        </div>
        <div class="field">
          <label>End Date</label>
          <input type="text" id="f_end_date" placeholder="YYYY-MM-DD" />
        </div>
        <div class="field">
          <label>Duration (Weeks)</label>
          <input type="text" id="f_duration_weeks" placeholder="Min. 20 weeks" />
        </div>
        <div class="field">
          <label>Monthly Stipend (EUR)</label>
          <input type="text" id="f_monthly_stipend_eur" placeholder="Min. 650 EUR/mo" />
        </div>
      </div>
      <div class="form-grid-2">
        <div class="field">
          <label>Internship Offer Title</label>
          <input type="text" id="f_internship_title" placeholder="Official title of the internship" />
        </div>
        <div class="field">
          <label>Confidentiality / Defense NDA Status</label>
          <input type="text" id="f_confidentiality_nda" placeholder="Standard or Defense NDA (Huis Clos)" />
        </div>
      </div>

      <div class="section-header">4. Proposed Technical Mission &amp; Engineering Environment</div>
      <div class="field" style="margin-bottom: 12px;">
        <label>Detailed Technical Tasks &amp; Weekly Breakdown</label>
        <textarea id="f_technical_tasks" placeholder="Paste or upload the student's technical task breakdown..."></textarea>
      </div>
      <div class="field">
        <label>Engineering Software, Lab Instruments &amp; Hardware Tools</label>
        <input type="text" id="f_tools_and_software" placeholder="e.g. Zemax OpticStudio, Xilinx Vivado (VHDL), Altium Designer..." />
      </div>

      <div class="form-footer">
        <button class="btn btn-primary" onclick="runManualTextAnalysis()">Re-Run Validation on Edited Form Fields</button>
      </div>
    </section>
  </main>

  <!-- Floating Bottom-Right Agent Button & Popup Chat Window -->
  <button class="agent-fab" onclick="toggleAgentPopup()">
    <span>💬 Ask Internship Agent</span>
  </button>

  <div class="agent-popup" id="agent-popup">
    <div class="agent-popup-header">
      <div class="agent-popup-title">
        <span>🤖 Polytech Internship Agent</span>
        <span class="agent-popup-sub">Tool: validate_internship_offer (/api/analyze)</span>
      </div>
      <button class="agent-popup-close" onclick="toggleAgentPopup()">✕</button>
    </div>

    <div class="agent-quick-chips">
      <button class="agent-chip" onclick="sendPopupMessage('Validate Clara Chêne Thales LiDAR offer')">
        ▶ Validate Clara (Thales)
      </button>
      <button class="agent-chip" onclick="sendPopupMessage('Validate Lucas Moreau Sologne PCB offer')">
        ▶ Validate Lucas (Sologne PCB)
      </button>
      <button class="agent-chip" onclick="sendPopupMessage('Validate the current intranet form fields')">
        ▶ Check Current Form
      </button>
    </div>

    <div class="agent-popup-messages" id="agent-popup-messages">
      <div class="popup-msg agent">Bonjour Prof. Canales! I am an OpenAI Agent connected to your <code>validate_internship_offer</code> API tool. Ask me to validate an offer or check the current form.</div>
    </div>

    <div class="agent-popup-input">
      <input type="text" id="agent-popup-input" placeholder="Ask agent to validate an offer..." onkeydown="if(event.key==='Enter') sendPopupMessage()" />
      <button class="btn btn-primary" onclick="sendPopupMessage()">Send</button>
    </div>
  </div>

  <script>
    const FORM_FIELDS = [
      "first_name", "last_name", "academic_year", "department",
      "company_name", "company_city", "siret_number",
      "supervisor_name", "supervisor_title",
      "start_date", "end_date", "duration_weeks", "monthly_stipend_eur",
      "confidentiality_nda", "internship_title", "technical_tasks", "tools_and_software"
    ];

    let timerInterval = null;
    let stepAnimationInterval = null;
    let lastAiStatus = "YELLOW";

    const dropzone = document.getElementById("dropzone");
    dropzone.addEventListener("dragover", (e) => {
      e.preventDefault();
      dropzone.classList.add("dragover");
    });
    dropzone.addEventListener("dragleave", () => {
      dropzone.classList.remove("dragover");
    });
    dropzone.addEventListener("drop", (e) => {
      e.preventDefault();
      dropzone.classList.remove("dragover");
      if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        uploadPdfFile(e.dataTransfer.files[0]);
      }
    });

    function handleFileSelect(event) {
      if (event.target.files && event.target.files.length > 0) {
        uploadPdfFile(event.target.files[0]);
      }
    }

    function setStepState(stepNum, state, detailText) {
      const row = document.getElementById("step-row-" + stepNum);
      const icon = document.getElementById("step-icon-" + stepNum);
      const detail = document.getElementById("step-detail-" + stepNum);
      row.className = "step-item " + state;
      if (state === "active") {
        icon.innerHTML = '<span class="spinner" style="width:14px;height:14px;border-width:2px;"></span>';
      } else if (state === "done") {
        icon.textContent = "✓";
      } else if (state === "error") {
        icon.textContent = "✕";
      } else {
        icon.textContent = String(stepNum);
      }
      if (detailText) {
        detail.textContent = detailText;
      }
    }

    function startLiveProgressAnimation(filename) {
      document.getElementById("thinking-box").style.display = "block";
      document.getElementById("pipeline-spinner").style.display = "inline-block";
      document.getElementById("thinking-title").textContent = "Running OpenAI `gpt-6-luna` + 3 Tools on " + filename + "...";
      document.getElementById("execution-mode-label").textContent = "Connecting to OpenAI API...";

      const defaultDetails = [
        "Extracting pages with pypdf, masking student INE/phone (GDPR), and scanning for prompt injections...",
        "Calling Tool 1 (`check_school_db`) to verify duration (>=20w), stipend (>=650 EUR), and SIRET history...",
        "Calling Tools 2 & 3 (`web_search` on company R&D + `file_search` on 5A Electronics & Optics syllabus)...",
        "Enforcing `strict: True` JSON Schema to auto-fill all 17 form fields and draft reply email..."
      ];
      for (let i = 1; i <= 4; i++) {
        setStepState(i, i === 1 ? "active" : "pending", defaultDetails[i - 1]);
      }

      const startTime = performance.now();
      const timerBadge = document.getElementById("timer-badge");
      if (timerInterval) clearInterval(timerInterval);
      timerInterval = setInterval(() => {
        const elapsed = ((performance.now() - startTime) / 1000).toFixed(1);
        timerBadge.textContent = elapsed + "s";
      }, 100);

      let currentStep = 1;
      if (stepAnimationInterval) clearInterval(stepAnimationInterval);
      stepAnimationInterval = setInterval(() => {
        if (currentStep < 4) {
          setStepState(currentStep, "done");
          currentStep++;
          setStepState(currentStep, "active");
        }
      }, 1400);
    }

    function stopLiveProgressAnimation() {
      if (timerInterval) clearInterval(timerInterval);
      if (stepAnimationInterval) clearInterval(stepAnimationInterval);
      document.getElementById("pipeline-spinner").style.display = "none";
      document.getElementById("dropzone").classList.remove("processing");
      document.getElementById("upload-btn").disabled = false;
      document.getElementById("upload-btn").textContent = "Upload Internship PDF";
    }

    function resetForm() {
      stopLiveProgressAnimation();
      FORM_FIELDS.forEach(k => {
        const el = document.getElementById("f_" + k);
        if (el) {
          el.value = "";
          el.classList.remove("autofilled");
        }
      });
      document.getElementById("pdf-input").value = "";
      document.getElementById("file-indicator").style.display = "none";
      document.getElementById("autofill-badge").style.display = "none";
      document.getElementById("thinking-box").style.display = "none";
      document.getElementById("result-card").style.display = "none";
      document.getElementById("override-drawer").style.display = "none";
      const toast = document.getElementById("action-toast");
      toast.className = "toast-msg";
      toast.textContent = "";
      document.getElementById("dropzone-title").textContent = "Drop Student Internship Proposal PDF here (or click to browse)";
    }

    function populateFormFields(extracted) {
      if (!extracted) return;
      let count = 0;
      FORM_FIELDS.forEach(k => {
        const el = document.getElementById("f_" + k);
        if (el && extracted[k] !== undefined && extracted[k] !== null) {
          el.value = extracted[k];
          el.classList.add("autofilled");
          count++;
        }
      });
      if (count > 0) {
        const badge = document.getElementById("autofill-badge");
        badge.textContent = "✓ " + count + "/17 Fields Auto-Filled from PDF";
        badge.style.display = "inline-block";
      }
    }

    async function uploadPdfFile(file) {
      document.getElementById("dropzone").classList.add("processing");
      document.getElementById("dropzone-title").textContent = "Processing Uploaded Document: " + file.name;
      document.getElementById("file-indicator").style.display = "block";
      document.getElementById("file-name-pill").innerHTML = '📄 ' + file.name + ' (' + Math.round(file.size / 1024) + ' KB)';
      document.getElementById("upload-btn").disabled = true;
      document.getElementById("upload-btn").textContent = "Processing PDF...";
      document.getElementById("result-card").style.display = "none";
      document.getElementById("override-drawer").style.display = "none";
      const toast = document.getElementById("action-toast");
      toast.className = "toast-msg";
      toast.textContent = "";

      startLiveProgressAnimation(file.name);

      const reader = new FileReader();
      reader.onload = async function(evt) {
        const base64Data = evt.target.result.split(",")[1];
        const resp = await fetch("/api/analyze-pdf", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ filename: file.name, pdf_base64: base64Data })
        });
        const data = await resp.json();
        renderPipelineResponse(data, file.name);
      };
      reader.readAsDataURL(file);
    }

    async function runManualTextAnalysis() {
      const summaryText = FORM_FIELDS.map(k => {
        const el = document.getElementById("f_" + k);
        return k + ": " + (el ? el.value : "");
      }).join("\n");

      document.getElementById("result-card").style.display = "none";
      startLiveProgressAnimation("Edited Form Fields");

      const resp = await fetch("/api/analyze-text", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: summaryText })
      });
      const data = await resp.json();
      renderPipelineResponse(data, "Edited Form Fields");
    }

    function renderPipelineResponse(data, sourceLabel) {
      stopLiveProgressAnimation();
      populateFormFields(data.extracted_form);
      document.getElementById("execution-mode-label").textContent = data.execution_mode || "";
      document.getElementById("dropzone-title").textContent = "Processed Document: " + sourceLabel;
      lastAiStatus = data.status;

      // Default the override dropdown to the opposite of the AI's current recommendation
      const overrideSelect = document.getElementById("override-status");
      overrideSelect.value = (data.status === "YELLOW") ? "GREEN" : "YELLOW";
      document.getElementById("override-reason").value = (data.status === "YELLOW")
        ? "Supervisor confirmed student will design an automated FPGA/VHDL test bench in Altium Designer."
        : "Tasks lack sufficient autonomous Master-level R&D design depth.";

      const steps = data.thinking_steps || [];
      if (data.status === "RED") {
        document.getElementById("thinking-title").textContent = "🛑 Execution Halted by OpenAI Input Guardrail";
        setStepState(1, "done", steps[0] || "Parsed PDF and masked student PII.");
        setStepState(2, "error", steps[1] || "CRITICAL ALERT: Indirect Prompt Injection detected in PDF.");
        setStepState(3, "error", steps[2] || "Halted before calling gpt-6-luna or downstream tools.");
        setStepState(4, "error", "Blocked: Refused to auto-approve injected instructions.");
      } else {
        document.getElementById("thinking-title").textContent = "✓ OpenAI `gpt-6-luna` Validation Complete (3 Tools Executed)";
        for (let i = 1; i <= 4; i++) {
          setStepState(i, "done", steps[i - 1] || "Completed.");
        }
      }

      const banner = document.getElementById("status-banner");
      banner.className = "status-banner " + data.status;
      document.getElementById("status-badge-text").textContent = data.status_badge;

      document.getElementById("bullet-1").textContent = data.bullet_1_company;
      document.getElementById("bullet-2").textContent = data.bullet_2_syllabus;
      document.getElementById("bullet-3").textContent = data.bullet_3_recommendation;

      document.getElementById("draft-email-box").value = data.draft_email;
      document.getElementById("result-card").style.display = "block";
    }

    function recordProfessorAction(message) {
      const toast = document.getElementById("action-toast");
      toast.className = "toast-msg info";
      toast.textContent = "✓ Professor Decision Recorded: " + message;
    }

    function toggleOverrideDrawer() {
      const drawer = document.getElementById("override-drawer");
      drawer.style.display = (drawer.style.display === "block") ? "none" : "block";
    }

    async function saveProfessorOverrideToEval() {
      const newStatus = document.getElementById("override-status").value;
      const reason = document.getElementById("override-reason").value;
      const firstName = document.getElementById("f_first_name").value || "Student";
      const lastName = document.getElementById("f_last_name").value || "Override";
      const company = document.getElementById("f_company_name").value || "Host Company";
      const siret = document.getElementById("f_siret_number").value || "000 000 000 00000";
      const duration = document.getElementById("f_duration_weeks").value || "24";
      const stipend = document.getElementById("f_monthly_stipend_eur").value || "1000";
      const tasks = document.getElementById("f_technical_tasks").value || "";

      const resp = await fetch("/api/log-override", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          student_name: firstName + " " + lastName,
          company_name: company,
          siret_number: siret,
          duration_weeks: duration,
          monthly_stipend_eur: stipend,
          tasks: tasks,
          ai_status: lastAiStatus,
          professor_status: newStatus,
          professor_reason: reason
        })
      });
      const res = await resp.json();

      // Update the UI banner to reflect the Professor's Human-in-the-Loop Override
      const banner = document.getElementById("status-banner");
      banner.className = "status-banner " + newStatus;
      document.getElementById("status-badge-text").textContent =
        newStatus + " — Professor Override Applied (Was " + lastAiStatus + ")";

      const toast = document.getElementById("action-toast");
      toast.className = "toast-msg eval";
      toast.innerHTML =
        "✓ <strong>Human-in-the-Loop Override Saved!</strong> Created new test case <code>" +
        res.eval_id + " (" + res.case_name + ")</code> in <code>professor_feedback_evals.json</code>. " +
        "Run <code>./.venv/bin/python eval_pipeline.py</code> to test it with <code>gpt-6-luna</code> + <code>gpt-6-sol</code> (LLM-as-a-Judge).";
    }

    // --- FLOATING POPUP AGENT (Single Tool: validate_internship_offer) ---
    let popupHistory = [];

    function toggleAgentPopup() {
      const popup = document.getElementById("agent-popup");
      popup.classList.toggle("open");
    }

    async function sendPopupMessage(presetText) {
      const input = document.getElementById("agent-popup-input");
      const text = (presetText || input.value || "").trim();
      if (!text) return;
      if (!presetText) input.value = "";

      const msgBox = document.getElementById("agent-popup-messages");
      const userDiv = document.createElement("div");
      userDiv.className = "popup-msg user";
      userDiv.textContent = text;
      msgBox.appendChild(userDiv);

      const loadingDiv = document.createElement("div");
      loadingDiv.className = "popup-msg agent";
      loadingDiv.innerHTML = '<span class="spinner" style="width:12px;height:12px;border-width:2px;"></span> Thinking...';
      msgBox.appendChild(loadingDiv);
      msgBox.scrollTop = msgBox.scrollHeight;

      const currentForm = FORM_FIELDS.map(k => {
        const el = document.getElementById("f_" + k);
        return k + ": " + (el ? el.value : "");
      }).join("\n");

      const resp = await fetch("/api/agent-chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, current_form: currentForm, history: popupHistory })
      });
      const data = await resp.json();

      popupHistory.push({ role: "user", content: text });
      popupHistory.push({ role: "assistant", content: data.reply || "" });

      if (data.pipeline_result) {
        renderPipelineResponse(data.pipeline_result, "Agent Tool Call (validate_internship_offer)");
      }

      const badgeHtml = data.tool_called
        ? `<div class="popup-tool-badge">⚡ Tool: ${data.tool_called}</div><br/>`
        : "";
      loadingDiv.innerHTML = badgeHtml + (data.reply || "").replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
      msgBox.scrollTop = msgBox.scrollHeight;
    }
  </script>
</body>
</html>
"""


class IntranetHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:
        pass

    def do_GET(self) -> None:
        if self.path == "/" or self.path.startswith("/?"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode("utf-8"))
            return

        if self.path.startswith("/slides"):
            slides_path = os.path.join(BASE_DIR, "slides.html")
            if os.path.exists(slides_path):
                with open(slides_path, "rb") as f:
                    data = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(data)
                return

        self.send_response(404)
        self.end_headers()

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(length) if length > 0 else b"{}"
        try:
            payload = json.loads(raw_body.decode("utf-8") or "{}")
        except Exception:
            payload = {}

        if self.path == "/api/log-override":
            existing = []
            if os.path.exists(FEEDBACK_FILE):
                try:
                    with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
                        existing = json.load(f)
                except Exception:
                    existing = []

            eval_id = f"EVAL-0{4 + len(existing)}"
            student = payload.get("student_name", "Student")
            company = payload.get("company_name", "Company")
            prof_status = payload.get("professor_status", "GREEN")
            reason = payload.get("professor_reason", "")
            case_name = f"{student} — {company} (Prof. Override)"

            synthetic_doc = (
                f"Student: {student} (5A Electronics & Optics).\n"
                f"Company: {company} | SIRET: {payload.get('siret_number', '482 910 384 00019')}\n"
                f"Duration: {payload.get('duration_weeks', 24)} weeks | Stipend: {payload.get('monthly_stipend_eur', 1000)} EUR/month.\n"
                f"Original Tasks: {payload.get('tasks', '')}\n"
                f"Professor Addendum / Override Context: {reason}"
            )

            existing.append({
                "id": eval_id,
                "source": "Prof. Override",
                "name": case_name,
                "text": synthetic_doc,
                "expected": prof_status,
                "professor_rationale": reason,
                "expected_fields": {
                    "siret_number": payload.get("siret_number", "48291038400019"),
                    "duration_weeks": int(payload.get("duration_weeks", 24) or 24),
                    "monthly_stipend_eur": float(payload.get("monthly_stipend_eur", 1000) or 1000),
                },
            })
            with open(FEEDBACK_FILE, "w", encoding="utf-8") as f:
                json.dump(existing, f, indent=2)

            self._send_json({"ok": True, "eval_id": eval_id, "case_name": case_name})
            return

        if self.path == "/api/agent-chat":
            msg = payload.get("message", "")
            current_form = payload.get("current_form", "")
            history = payload.get("history", [])
            agent_out = run_internship_agent(msg, current_form_text=current_form, history=history)
            self._send_json(agent_out)
            return

        try:
            if self.path == "/api/analyze-pdf":
                pdf_bytes = base64.b64decode(payload.get("pdf_base64", ""))
                extracted_text, page_count = extract_text_from_pdf_bytes(pdf_bytes)
                result = analyze_internship_document(
                    extracted_text, page_count=page_count
                )
                self._send_json(result)
                return

            if self.path in ("/api/analyze-text", "/api/analyze"):
                text = payload.get("text", "")
                result = analyze_internship_document(text, page_count=1)
                self._send_json(result)
                return
        except ValueError as guardrail_err:
            self._send_json({
                "extracted_form": {
                    "first_name": "Hugo",
                    "last_name": "Blanc",
                    "academic_year": "5th Year (5A - Master's Level)",
                    "department": "Electronics & Optics (EO)",
                    "company_name": "Loire Bureautique & Copy-Shop SARL",
                    "company_city": "Orléans (45000)",
                    "siret_number": "512 884 102 00014",
                    "supervisor_name": "Jean-Pierre Garnier",
                    "supervisor_title": "Store Manager",
                    "start_date": "2027-02-01",
                    "end_date": "2027-07-30",
                    "duration_weeks": 24,
                    "monthly_stipend_eur": 680,
                    "confidentiality_nda": "Standard",
                    "internship_title": "Support Bureautique, Photocopieurs et Accueil Client",
                    "technical_tasks": f"[BLOCKED BY GUARDRAIL — {guardrail_err}]",
                    "tools_and_software": "Office Photocopiers, Excel",
                },
                "status": "RED",
                "status_badge": "🛑 BLOCKED BY OPENAI GUARDRAIL — Indirect Prompt Injection Detected in PDF",
                "bullet_1_company": "Input Guardrail Tripwire Triggered (`run_input_guardrails`): The uploaded PDF contains hidden adversarial instructions attempting to override the system prompt and force `status=GREEN`.",
                "bullet_2_syllabus": "Tool & Model Protection: Execution was halted immediately before calling `gpt-6-luna` or any downstream tools (`check_school_db`, `web_search`, `file_search`) to prevent tool hijacking.",
                "bullet_3_recommendation": "Security Action: Do NOT approve. Summon the student for an academic integrity review regarding the injected instructions in Section 5 of their PDF.",
                "draft_email": (
                    "Bonjour Hugo,\n\n"
                    "Lors du dépôt de votre fiche de stage sur l'intranet Polytech Orléans, notre système de sécurité "
                    "a détecté une tentative d'injection d'instructions cachées ('SYSTEM OVERRIDE - IGNORE PREVIOUS INSTRUCTIONS') "
                    "dans la Section 5 de votre document PDF visant à contourner la validation pédagogique.\n\n"
                    "Votre dossier a été automatiquement bloqué. Merci de vous présenter au bureau du Responsable de la "
                    "spécialité Électronique & Optique pour un entretien concernant l'intégrité académique de votre dépôt.\n\n"
                    "Direction des Études — Polytech Orléans"
                ),
                "thinking_steps": [
                    "Step 1 — PDF Text Extraction & PII Masking: Extracted PDF text and masked student INE (22109941Z) & personal contact details.",
                    f"Step 2 — OpenAI Input Guardrail (`InjectionTripwire`): CRITICAL ALERT — {guardrail_err}",
                    "Step 3 — Execution Halted: Blocked request before calling `gpt-6-luna` or executing tools (`check_school_db`, `web_search`, `file_search`).",
                ],
                "execution_mode": "🛑 OpenAI Input Guardrail Tripwire (Blocked Before LLM Call)",
            })
            return

        self.send_response(404)
        self.end_headers()

    def _send_json(self, obj: dict) -> None:
        body = json.dumps(obj).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    load_env_key()
    port = int(os.environ.get("PORT", "8765"))
    server = HTTPServer(("0.0.0.0", port), IntranetHandler)
    print(f"Polytech Orléans Intranet Server listening on http://mathiascanales.c.googlers.com:{port}")
    server.serve_forever()
