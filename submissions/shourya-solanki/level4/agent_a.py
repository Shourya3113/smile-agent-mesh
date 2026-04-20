#!/usr/bin/env python3
"""
Agent A — SMILE Strategist
Orchestrates: queries Agent B for industry context,
queries LPI for methodology, synthesizes via Ollama.
"""

import json
import subprocess
import os
import re
import urllib.request
import urllib.error
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "lpi-developer-kit"))
LPI_SERVER_CMD = ["node", os.path.join(REPO_ROOT, "dist", "src", "index.js")]
AGENT_B_URL = "http://localhost:8001"
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen2.5:1.5b"

MAX_INPUT_LENGTH = 500
BLOCKED_PATTERNS = [
    r"ignore previous", r"ignore all", r"system prompt",
    r"reveal.*prompt", r"forget.*instruction", r"you are now",
    r"pretend you", r"act as", r"jailbreak", r"override.*instruction",
    r"repeat.*above",
    r"repeat.*everything",
    r"what.*instructions",
]

def sanitize_input(text: str) -> str:
    if len(text) > MAX_INPUT_LENGTH:
        print("[SECURITY] Input rejected — too long")
        sys.exit(1)
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            print(f"[SECURITY] Input rejected — prompt injection detected: {pattern}")
            sys.exit(1)
    return text.strip()

def call_mcp_tool(process, tool_name: str, arguments: dict) -> str:
    request = {
        "jsonrpc": "2.0", "id": 1,
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments}
    }
    process.stdin.write(json.dumps(request) + "\n")
    process.stdin.flush()
    line = process.stdout.readline()
    if not line:
        return "[ERROR] No response"
    response = json.loads(line)
    if "result" in response and "content" in response["result"]:
        return response["result"]["content"][0].get("text", "")
    return "[ERROR] Unexpected response"

def start_lpi():
    proc = subprocess.Popen(
        LPI_SERVER_CMD, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True, cwd=REPO_ROOT
    )
    init_req = {
        "jsonrpc": "2.0", "id": 0, "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "smile-strategist-agent", "version": "1.0"}
        }
    }
    proc.stdin.write(json.dumps(init_req) + "\n")
    proc.stdin.flush()
    proc.stdout.readline()
    notif = {"jsonrpc": "2.0", "method": "notifications/initialized"}
    proc.stdin.write(json.dumps(notif) + "\n")
    proc.stdin.flush()
    return proc

def discover_agent_b() -> dict:
    req = urllib.request.Request(f"{AGENT_B_URL}/.well-known/agent.json")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"[A2A] Failed to discover Agent B: {e}")
        sys.exit(1)

def query_agent_b(query: str, request_id: str) -> dict:
    payload = json.dumps({"query": query, "request_id": request_id}).encode()
    req = urllib.request.Request(
        f"{AGENT_B_URL}/query", data=payload,
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        return {"error": str(e)}

def call_ollama(prompt: str) -> str:
    payload = json.dumps({
        "model": OLLAMA_MODEL, "prompt": prompt, "stream": False
    }).encode()
    req = urllib.request.Request(
        OLLAMA_URL, data=payload,
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read())["response"]
    except Exception as e:
        return f"[ERROR] Ollama unavailable: {e}"

def run(question: str):
    question = sanitize_input(question)

    print("\n🔍 [A2A] Discovering Agent B...")
    agent_b_card = discover_agent_b()
    print(f"✅ Found: {agent_b_card['name']} — {agent_b_card['description']}")

    print("\n📡 [A2A] Querying Agent B for industry context...")
    b_response = query_agent_b(question, request_id="req-001")

    print("\n🧠 [LPI] Querying SMILE methodology...")
    proc = start_lpi()
    try:
        smile = call_mcp_tool(proc, "smile_overview", {})
        phases = call_mcp_tool(proc, "smile_phase_detail", {"phase": "reality-emulation"})
    finally:
        proc.terminate()

    b_results = b_response.get("results", {})
    prompt = f"""You are a SMILE methodology strategist with access to industry intelligence.

User question: "{question}"

--- [Agent A: SMILE Methodology — smile_overview] ---
{smile[:1000]}

--- [Agent A: Phase Detail — smile_phase_detail(reality-emulation)] ---
{phases[:600]}

--- [Agent B: Industry Case Studies — get_case_studies] ---
{b_results.get('case_studies', '')[:800]}

--- [Agent B: Scenario Insights — get_insights] ---
{b_results.get('insights', '')[:800]}

--- [Agent B: Knowledge Base — query_knowledge] ---
{b_results.get('knowledge', '')[:600]}

Using ALL five sources above, provide:
1. A direct answer grounded in SMILE methodology
2. A real-world industry example that supports the recommendation
3. Which SMILE phases are most relevant
4. One insight that only emerges from combining methodology + industry data

Cite which agent and tool provided each key insight."""

    print("\n🤖 Synthesizing across both agents via Ollama...\n")
    answer = call_ollama(prompt)

    print("=" * 70)
    print("🌐 SMILE AGENT MESH — COMBINED INTELLIGENCE REPORT")
    print("=" * 70)
    print(f"\nQuestion: {question}\n")
    print(answer)
    print("\n" + "=" * 70)
    print("✅ PROVENANCE")
    print("=" * 70)
    print("[Agent A] smile_overview({}) — SMILE methodology foundation")
    print("[Agent A] smile_phase_detail({phase: reality-emulation})")
    print(f"[Agent B] get_case_studies({{query: '{question}'}})")
    print("[Agent B] get_insights({scenario: personal health digital twin})")
    print(f"[Agent B] query_knowledge({{query: '{question}'}})")
    print("=" * 70)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Usage: python3 agent_a.py "Your question here"')
        sys.exit(1)
    run(sys.argv[1])
