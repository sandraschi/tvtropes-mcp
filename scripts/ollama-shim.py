#!/usr/bin/env python3
"""Ollama API compatibility shim — wraps any OpenAI-compatible backend.

Usage:
    uv run python scripts/ollama-shim.py --upstream http://localhost:1234 --port 11434

This proxies /api/generate, /api/chat, /api/tags, /api/embeddings to
the OpenAI-compatible /v1/ endpoints. Any MCP server expecting Ollama
can point at this shim instead.
"""

import argparse
import json
import logging
import re
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
import uvicorn

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("ollama-shim")

app = FastAPI(title="Ollama Shim", version="0.1.0")

_upstream: str = ""
_client: httpx.AsyncClient | None = None


def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=120)
    return _client


@app.on_event("shutdown")
async def shutdown():
    if _client:
        await _client.aclose()


@app.get("/api/tags")
async def api_tags():
    client = get_client()
    r = await client.get(f"{_upstream}/v1/models")
    if r.status_code != 200:
        raise HTTPException(502, detail=f"Upstream {r.status_code}")
    data = r.json()
    models = [{"name": m["id"]} for m in data.get("data", [])]
    return {"models": models}


@app.post("/api/generate")
async def api_generate(body: dict[str, Any]):
    client = get_client()
    prompt = body.get("prompt", "")
    model = body.get("model", "")
    stream = body.get("stream", False)
    fmt = body.get("format", "")
    opts = body.get("options", {})

    messages = [{"role": "user", "content": prompt}]
    if fmt == "json":
        payload = {
            "model": model,
            "messages": messages,
            "temperature": opts.get("temperature", 0.1),
            "max_tokens": opts.get("num_predict", 2048),
        }
        r = await client.post(f"{_upstream}/v1/chat/completions", json=payload)
        if r.status_code != 200:
            raise HTTPException(502, detail=f"Upstream {r.status_code}")
        data = r.json()
        text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return {"response": text}

    payload = {
        "model": model,
        "messages": messages,
        "temperature": opts.get("temperature", 0.7),
        "max_tokens": opts.get("num_predict", 2048),
        "stream": stream,
    }
    r = await client.post(f"{_upstream}/v1/chat/completions", json=payload)
    if r.status_code != 200:
        raise HTTPException(502, detail=f"Upstream {r.status_code}")
    data = r.json()
    text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    return {"response": text, "done": True}


@app.post("/api/chat")
async def api_chat(body: dict[str, Any]):
    client = get_client()
    model = body.get("model", "")
    messages = body.get("messages", [])
    stream = body.get("stream", False)

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.7,
        "stream": stream,
    }
    r = await client.post(f"{_upstream}/v1/chat/completions", json=payload)
    if r.status_code != 200:
        raise HTTPException(502, detail=f"Upstream {r.status_code}")
    data = r.json()
    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    return {"message": {"role": "assistant", "content": content}, "done": True}


@app.post("/api/embeddings")
async def api_embeddings(body: dict[str, Any]):
    client = get_client()
    model = body.get("model", "")
    prompt = body.get("prompt", "")

    payload = {"model": model, "input": prompt}
    r = await client.post(f"{_upstream}/v1/embeddings", json=payload)
    if r.status_code != 200:
        raise HTTPException(502, detail=f"Upstream {r.status_code}")
    data = r.json()
    embedding = data.get("data", [{}])[0].get("embedding", [])
    return {"embedding": embedding}


@app.get("/")
async def root():
    return {"service": "ollama-shim", "upstream": _upstream}


def main():
    global _upstream
    parser = argparse.ArgumentParser(description="Ollama API compatibility shim")
    parser.add_argument("--upstream", default="http://localhost:1234", help="OpenAI-compatible API URL")
    parser.add_argument("--port", type=int, default=11434, help="Port to listen on (default 11434 = Ollama default)")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address")
    args = parser.parse_args()
    _upstream = args.upstream.rstrip("/")
    log.info(f"Ollama shim: {args.host}:{args.port} -> {_upstream}")
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
