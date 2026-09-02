# FinanzPrüfer — Agentic Due Diligence Engine

Autonomous financial intelligence platform built for the **Nebius x NVIDIA Global AI Hackathon** (Best Apps and Agents Track).

## Core Architecture
- **Reasoning Orchestrator:** NVIDIA Nemotron 3 Ultra via Nebius Token Factory.
- **Fast Interactive Copilot:** NVIDIA Nemotron Nano/Super.
- **Live Context:** Tavily Search API.
- **Auditing Tools:** SEC filings parsing (Form 4, 13F, 10-K) and quantitative risk heuristic scoring.

## Significant Updates
- Refactored research modules into autonomous tool-calling agents.
- Migrated inference pipeline to Nebius Token Factory.
- Added live financial web verification via Tavily.
