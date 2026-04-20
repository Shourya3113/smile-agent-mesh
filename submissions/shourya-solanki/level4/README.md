# Level 4 Submission — SMILE Agent Mesh
**Author**: Shourya Solanki | Track A: Agent Builders

## What I Built
A secure two-agent mesh where:
- Agent A (SMILE Strategist) — orchestrates, queries LPI for methodology
- Agent B (Industry Analyst) — FastAPI server, queries LPI for case studies and insights

Agents discover each other via A2A Agent Cards, exchange structured JSON, and together produce recommendations neither could generate alone.

## How to Run

Requirements: Python 3.10+, Node.js 18+ with lpi-developer-kit built, Ollama running with qwen2.5:1.5b

Setup:
    python3 -m venv venv
    source venv/bin/activate
    pip install fastapi uvicorn requests

Run Agent B (terminal 1):
    uvicorn agents.agent_b:app --port 8001

Run Agent A (terminal 2):
    python3 agents/agent_a.py "How should I build a personal health digital twin?"

## Architecture
User Question → Agent A (SMILE Strategist)
    Agent A queries LPI: smile_overview, smile_phase_detail
    Agent A discovers Agent B via GET /.well-known/agent.json
    Agent A queries Agent B via POST /query
        Agent B queries LPI: get_case_studies, get_insights, query_knowledge
    Agent A sends all 5 tool outputs to Ollama (qwen2.5:1.5b)
    Combined Intelligence Report + Provenance

## Security Features
- Prompt injection detection (13 patterns) on both agents independently
- 500 character input limit
- Zero trust — Agent B sanitizes inputs even from Agent A
- LPI subprocess terminated after every request
- Graceful failure on Agent B unavailability
- No system prompt leakage

## Files
- agent_a.py — SMILE Strategist (orchestrator)
- agent_b.py — Industry Analyst (FastAPI server)
- agent_a.json — A2A Agent Card for Agent A
- agent_b.json — A2A Agent Card for Agent B
- THREAT_MODEL.md — attack surface analysis
- SECURITY_AUDIT.md — self-audit with test results and fixes
- DEMO.md — full demo transcript