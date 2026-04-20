#!/usr/bin/env python3
"""
Agent B — Industry Analyst
Specializes in LPI case studies and insights.
Serves as an HTTP API that Agent A can query.
"""

import json
import subprocess
import os
import re
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

app = FastAPI(title="Industry Analyst Agent", version="1.0.0")

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "lpi-developer-kit"))
LPI_SERVER_CMD = ["node", os.path.join(REPO_ROOT, "dist", "src", "index.js")]

MAX_INPUT_LENGTH = 500
BLOCKED_PATTERNS = [
    r"ignore previous",
    r"ignore all",
    r"system prompt",
    r"reveal.*prompt",
    r"forget.*instruction",
    r"you are now",
    r"pretend you",
    r"act as",
    r"jailbreak",
    r"override.*instruction",
    r"repeat.*above",
    r"repeat.*everything",
    r"what.*instructions",
]

class QueryRequest(BaseModel):
    query: str
    request_id: str = "unknown"

def sanitize_input(text: str) -> str:
    if len(text) > MAX_INPUT_LENGTH:
        raise HTTPException(status_code=400, detail="Input too long — max 500 characters")
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            raise HTTPException(status_code=400, detail="Input rejected — potential prompt injection detected")
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
            "clientInfo": {"name": "industry-analyst-agent", "version": "1.0"}
        }
    }
    proc.stdin.write(json.dumps(init_req) + "\n")
    proc.stdin.flush()
    proc.stdout.readline()
    notif = {"jsonrpc": "2.0", "method": "notifications/initialized"}
    proc.stdin.write(json.dumps(notif) + "\n")
    proc.stdin.flush()
    return proc

@app.get("/.well-known/agent.json")
def agent_card():
    return {
        "name": "Industry Analyst Agent",
        "version": "1.0.0",
        "description": "Specializes in digital twin case studies and scenario insights using LPI tools",
        "capabilities": ["case_study_analysis", "industry_insights", "scenario_recommendations"],
        "tools_used": ["get_case_studies", "get_insights", "query_knowledge"],
        "endpoint": "http://localhost:8001",
        "protocol": "A2A/1.0"
    }

@app.post("/query")
def query(req: QueryRequest):
    query_text = sanitize_input(req.query)
    proc = start_lpi()
    try:
        cases = call_mcp_tool(proc, "get_case_studies", {"query": query_text})
        insights = call_mcp_tool(proc, "get_insights", {
            "scenario": "personal health digital twin", "tier": "free"
        })
        knowledge = call_mcp_tool(proc, "query_knowledge", {"query": query_text})
    finally:
        proc.terminate()

    return {
        "agent": "Industry Analyst",
        "request_id": req.request_id,
        "query": query_text,
        "tools_used": ["get_case_studies", "get_insights", "query_knowledge"],
        "results": {
            "case_studies": cases[:1000],
            "insights": insights[:1000],
            "knowledge": knowledge[:1000]
        }
    }

@app.get("/health")
def health():
    return {"status": "ok", "agent": "Industry Analyst Agent"}
