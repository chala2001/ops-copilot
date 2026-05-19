# MCP (Model Context Protocol) — A Beginner's Guide

> A complete, plain-English guide to understanding what MCP is, why your mentor asked for it, and how to convert your SRE Ops Copilot into an MCP server — step by step, from zero knowledge.

---

## Table of Contents

1. [What is MCP? (Explain Like I'm 5)](#1-what-is-mcp-explain-like-im-5)
2. [The Real-World Problem MCP Solves](#2-the-real-world-problem-mcp-solves)
3. [Why Your Mentor Wants This](#3-why-your-mentor-wants-this)
4. [How MCP Actually Works](#4-how-mcp-actually-works)
5. [MCP vs REST API — What's the Difference?](#5-mcp-vs-rest-api--whats-the-difference)
6. [The Three Things an MCP Server Can Expose](#6-the-three-things-an-mcp-server-can-expose)
7. [What Your Current App Looks Like](#7-what-your-current-app-looks-like)
8. [What Your App Will Look Like After MCP](#8-what-your-app-will-look-like-after-mcp)
9. [Step-by-Step: Converting Ops Copilot to MCP](#9-step-by-step-converting-ops-copilot-to-mcp)
10. [Testing Your MCP Server](#10-testing-your-mcp-server)
11. [Common Mistakes and How to Avoid Them](#11-common-mistakes-and-how-to-avoid-them)
12. [Glossary](#12-glossary)
13. [Useful Links](#13-useful-links)

---

## 1. What is MCP? (Explain Like I'm 5)

**MCP** stands for **Model Context Protocol**.

Forget the fancy name for a second. Here's the simple version:

> **MCP is a standard way for AI assistants (like Claude, ChatGPT, Copilot) to talk to your tools, databases, and applications.**

Think of MCP like a **USB port** for AI.

- Before USB: every device had its own weird cable. Printers had one cable, mice had another, keyboards a third. Chaos.
- After USB: one standard plug, everything works together.

Before MCP, every AI assistant had its own custom way of connecting to tools. Each tool needed to be re-built for each AI. With MCP, you build your tool **once**, and **any** AI assistant that speaks MCP can use it.

### A simple analogy

Imagine you built a vending machine (your SRE Ops Copilot). Today, only people who know your **specific** vending machine buttons can use it. If a new customer comes from another country, they don't know your buttons.

MCP is like agreeing on a **universal vending machine button layout**. Now anyone, from any country, can walk up and use your machine because they understand the buttons.

In our case:
- Your **vending machine** = SRE Ops Copilot (your RAG system)
- Your **buttons** = the questions people ask it
- The **customers** = other AI systems, Claude Desktop, internal tools, automation scripts
- **MCP** = the agreed-upon button layout

---

## 2. The Real-World Problem MCP Solves

Right now, your SRE Ops Copilot is a **Streamlit web app**. To use it, a human has to:

1. Open a browser
2. Go to `https://localhost:8501`
3. Log in
4. Type a question
5. Read the answer

That's great for humans. But what if:

- An **on-call alerting system** wants to automatically ask "What is the runbook for CustomerX P1 alert?" when an alert fires?
- A **Slack bot** wants to query your knowledge base when someone posts a question in `#sre-help`?
- **Claude Desktop** (the AI assistant) wants to use your runbooks as context when an engineer is asking it questions?
- Another **internal tool** (say, a deployment dashboard) wants to pull configuration info from your RAG system?

None of those are browsers. None of them can "click" or "type into a textbox". They need a **programmatic way** to talk to your system.

You could build:
- A REST API for the Slack bot
- A different integration for Claude Desktop
- A webhook for the alerting system
- Another endpoint for the dashboard

**Or** — you build ONE MCP server, and all of those tools can use it because they all speak MCP.

That's the value.

---

## 3. Why Your Mentor Wants This

Your mentor said:

> "This system needs to interact with their existing systems, so they need this application in MCP manner."

Translated:

> "We have other systems at WSO2 that need to query the SRE knowledge base. Instead of every system writing its own custom integration, expose the Copilot as an MCP server. Then any MCP-compatible client — Claude Desktop, automation agents, AI workflows — can use it out of the box."

### Concrete examples of "their existing systems"

These are guesses based on your project context (internal WSO2 tooling), but likely candidates:

| Existing system | How it would use your MCP server |
|---|---|
| Claude Desktop / Claude Code (used by engineers) | Pulls runbook context automatically when an engineer is debugging |
| Internal AI agent / chatbot | Calls your `ask_runbook` tool when a question is about customer deployments |
| Slack bot | When `@bot` is mentioned, queries your MCP server for an answer |
| Incident response automation | When a P1 fires, pulls the runbook automatically |
| Onboarding assistant | New engineers ask questions and the assistant uses your KB as a source |

The point: **your RAG system stops being a standalone app, and becomes a building block that other AI systems can plug into.**

---

## 4. How MCP Actually Works

MCP has two sides:

### 4.1 MCP Server (what YOU build)

The MCP **server** exposes capabilities (tools, data, prompts).

Your **SRE Ops Copilot** becomes the MCP server. It says:

> "Hi, I'm a server. I can do these things:
> - Tool: `ask_sre_knowledge_base(question, customer_scope)` — ask me a question and I'll search my docs
> - Tool: `list_customers()` — get the list of customers I have docs for
> - Resource: `runbook://CustomerX/P1` — direct access to specific runbooks"

### 4.2 MCP Client (what someone else uses)

The MCP **client** is whatever wants to use your server. Examples:

- **Claude Desktop** has an MCP client built in
- **Claude Code** (the CLI you're using right now) has an MCP client built in
- A **Python script** can be an MCP client if it imports the MCP SDK
- A **custom AI agent** can be an MCP client

When the client wants to use your server, it:

1. **Connects** to your MCP server (over stdio, HTTP, or websocket)
2. **Discovers** what tools/resources/prompts you offer (you advertise this automatically)
3. **Calls** your tools when needed
4. **Gets** the results back as structured data

### 4.3 The Three Transports

MCP can run over three "transports" (ways the client and server talk):

| Transport | When to use it | How it works |
|---|---|---|
| **stdio** | Server runs as a subprocess of the client. Local dev, Claude Desktop integration. | Client launches your Python script, talks to it via stdin/stdout. |
| **HTTP (Streamable)** | Server runs as a remote service. Multiple clients, network access, production. | Client makes HTTP requests. Supports streaming responses (SSE). |
| **SSE (legacy)** | Older HTTP-based transport. Still supported. | Server-Sent Events. Largely replaced by Streamable HTTP. |

**For your project** (internal WSO2 deployment, 30-40 concurrent users, Azure VM), you almost certainly want **HTTP transport** — because your server runs in Azure and clients connect over the network. Stdio is mostly for local dev / Claude Desktop.

---

## 5. MCP vs REST API — What's the Difference?

You might be thinking: "Wait, this sounds like a REST API. Why don't I just build a `/ask` endpoint?"

Great question. Here's the difference:

| Feature | REST API | MCP |
|---|---|---|
| Who designed it for? | Humans/programmers reading docs | AI assistants discovering capabilities automatically |
| How does the client know what's available? | Read the docs, hardcode the endpoints | The server tells the client at connection time (introspection) |
| Schema for inputs/outputs? | Optional (OpenAPI if you bother) | Mandatory, built-in (JSON Schema) |
| Streaming results? | Custom (SSE, WebSocket, etc.) | First-class support |
| Authorization? | Custom per API | Standardized (OAuth 2.1 recommended) |
| Works with Claude Desktop out of the box? | No, needs a custom integration | Yes |
| Works with N other AI tools? | Each needs its own integration | All of them, for free |

**Short version:** REST is for humans-writing-code. MCP is for AI-discovering-tools. You can build both, but MCP is what makes your tool **AI-native**.

---

## 6. The Three Things an MCP Server Can Expose

An MCP server can offer three kinds of "things":

### 6.1 Tools (most important for you)

A **tool** is a function the AI can call. Like a Python function, but described in a schema so any AI can understand it.

For your project, you'd expose:

```
Tool: ask_sre_knowledge_base
Description: Ask a question and get an answer grounded in WSO2 SRE runbooks.
Inputs:
  - question (string, required): The question to ask
  - customer_scope (array of strings, optional): Limit search to these customers
Output:
  - answer (string): The generated answer
  - sources (array): List of source documents with citations
```

The AI sees this and knows: "Oh, when someone asks me about WSO2 SRE stuff, I can call `ask_sre_knowledge_base`."

### 6.2 Resources

A **resource** is a piece of data the AI can read (like a file or a record).

Example for your project:

```
Resource: runbook://CustomerX/incident-playbook
Description: The P1 incident response playbook for CustomerX
Content: <markdown content>
```

Resources are good for documents the AI should "see" rather than "search through".

### 6.3 Prompts

A **prompt** is a pre-built prompt template that can be triggered by name.

Example:

```
Prompt: investigate_alert
Description: Walk through investigating an alert step by step
Arguments: alert_name, customer
```

For your first version, **focus on Tools**. That's where 90% of the value is. You can add resources and prompts later.

---

## 7. What Your Current App Looks Like

Right now, your app is structured roughly like this:

```
┌───────────────────────────────────────────┐
│        Browser (Streamlit UI)             │
│        https://localhost:8501             │
└──────────────────┬────────────────────────┘
                   │
                   ▼
┌───────────────────────────────────────────┐
│           app.py (Streamlit)              │
│  - Login                                  │
│  - Chat UI                                │
│  - Calls core/rag.py::ask()               │
└──────────────────┬────────────────────────┘
                   │
                   ▼
┌───────────────────────────────────────────┐
│            core/rag.py                    │
│  - Embeds question                        │
│  - Searches ChromaDB                      │
│  - Reranks                                │
│  - Calls Gemini                           │
│  - Returns answer + sources               │
└───────────────────────────────────────────┘
```

The **business logic** lives in [core/rag.py](core/rag.py). The Streamlit UI is just a wrapper around it.

**This is great news**: because your logic is already in a clean function (`ask(question, customer_scope)`), wrapping it as an MCP tool is mostly plumbing.

---

## 8. What Your App Will Look Like After MCP

After conversion, you'll have **two ways** to use the same RAG engine:

```
┌────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│  Streamlit UI      │    │   MCP Client #1     │    │   MCP Client #2     │
│  (human users)     │    │   (Claude Desktop)  │    │  (Slack bot, etc)   │
└─────────┬──────────┘    └──────────┬──────────┘    └──────────┬──────────┘
          │                          │                          │
          │                          │ MCP protocol (HTTP)      │
          │                          ▼                          │
          │              ┌────────────────────────┐             │
          │              │   mcp_server.py (NEW)  │◀────────────┘
          │              │   - Exposes tools      │
          │              │   - Talks MCP protocol │
          │              └───────────┬────────────┘
          │                          │
          ▼                          ▼
       ┌─────────────────────────────────────────┐
       │       core/rag.py (unchanged)            │
       │       ask(question, customer_scope)      │
       └──────────────────────────────────────────┘
```

**You do NOT throw away Streamlit.** You add MCP **alongside** it. Same RAG engine, two interfaces.

---

## 9. Step-by-Step: Converting Ops Copilot to MCP

Here's the actual conversion plan. We'll go from zero to a working MCP server.

### Step 1 — Install the MCP SDK

The official Python SDK for MCP is called `mcp`. Anthropic and the MCP community maintain it.

```bash
pip install "mcp[cli]"
```

Add to [requirements.txt](requirements.txt):

```
mcp[cli]>=1.2.0
```

### Step 2 — Create the MCP Server File

Create a new file: `mcp_server.py` at the project root. Don't touch `app.py` yet.

```python
# mcp_server.py
# ── MCP Server for SRE Ops Copilot ────────────────────────
# Exposes the RAG engine as MCP tools so other AI systems
# (Claude Desktop, agents, automation) can use it.

from mcp.server.fastmcp import FastMCP
from core.rag import ask, get_authorized_customers

# Create the MCP server. The name is what clients will see.
mcp = FastMCP("sre-ops-copilot")


@mcp.tool()
def ask_sre_knowledge_base(
    question: str,
    customer_scope: list[str] | None = None,
) -> dict:
    """
    Ask a question about WSO2 customer deployments, runbooks, or SRE procedures.
    Returns an answer grounded in internal documentation with source citations.

    Args:
        question: A natural-language question (max 2000 chars).
        customer_scope: Optional list of customer names to restrict the search.
                        If None, searches across 'General' only.

    Returns:
        A dict with 'answer' (string) and 'sources' (list of dicts).
    """
    scope = customer_scope or ["General"]
    answer, sources = ask(question, scope)
    return {
        "answer": answer,
        "sources": sources,
    }


@mcp.tool()
def list_customers_for_user(username: str) -> list[str]:
    """
    Return the list of customer scopes a given user is authorized to query.

    Args:
        username: The username (e.g. 'alice', 'bob').

    Returns:
        A list of authorized customer scope names.
    """
    return get_authorized_customers(username)


if __name__ == "__main__":
    # Default transport is stdio (good for local dev / Claude Desktop).
    # For production deployment, switch to streamable-http (see Step 5).
    mcp.run()
```

That's it. **About 40 lines of code.** The `@mcp.tool()` decorator does all the heavy lifting — it reads your function's type hints and docstring to build the schema automatically.

### Step 3 — Test It Locally with the MCP Inspector

The MCP team provides an "Inspector" — a debugging UI for testing your server.

```bash
mcp dev mcp_server.py
```

This launches a browser-based UI where you can:
- See the tools your server exposes
- Call them manually with test inputs
- See the responses

This is the easiest way to verify your server works **before** hooking it up to a real client.

### Step 4 — Test It with Claude Desktop (Optional but Cool)

If you want to try it with Claude Desktop:

1. Open Claude Desktop config (location varies by OS — `~/Library/Application Support/Claude/claude_desktop_config.json` on Mac, `%APPDATA%\Claude\claude_desktop_config.json` on Windows).
2. Add your server:

```json
{
  "mcpServers": {
    "sre-ops-copilot": {
      "command": "python",
      "args": ["/absolute/path/to/ops-copilot/mcp_server.py"]
    }
  }
}
```

3. Restart Claude Desktop.
4. Ask Claude something like: "Use the SRE knowledge base to find the P1 runbook for CustomerX."

Claude will discover your tool and call it. Magic.

### Step 5 — Switch to HTTP Transport for Production

For your real Azure deployment, you want HTTP transport so multiple clients can connect over the network. Change the bottom of `mcp_server.py`:

```python
if __name__ == "__main__":
    # Streamable HTTP transport — for networked/multi-client deployment
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8765)
```

Now the server listens on port 8765 and any MCP client on the network can connect to `http://your-azure-vm:8765`.

### Step 6 — Add Authentication

**Critical for WSO2 internal deployment.** Don't expose an unauthenticated MCP server on the network.

MCP officially supports OAuth 2.1. For a first version, you can do something simpler — an API key check using a middleware. The MCP Python SDK supports adding ASGI middleware.

Minimal API-key example:

```python
import os
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

EXPECTED_KEY = os.environ["MCP_API_KEY"]

class ApiKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if request.headers.get("x-api-key") != EXPECTED_KEY:
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        return await call_next(request)

# Attach middleware to the FastMCP app
app = mcp.streamable_http_app()
app.add_middleware(ApiKeyMiddleware)
```

For production, plan to migrate to **OAuth 2.1** (the MCP spec strongly recommends it), but API keys are fine for an MVP behind your VPN.

### Step 7 — Update Docker / docker-compose

You already have a [Dockerfile](Dockerfile) and [docker-compose.yml](docker-compose.yml). Add a second service for the MCP server:

```yaml
services:
  streamlit:
    # ... your existing service ...

  mcp:
    build: .
    command: python mcp_server.py
    ports:
      - "8765:8765"
    environment:
      - MCP_API_KEY=${MCP_API_KEY}
      - GOOGLE_API_KEY=${GOOGLE_API_KEY}
    volumes:
      - ./chroma_db:/app/chroma_db  # share the vector DB
```

Both services share the same `chroma_db` and the same code. **Two interfaces, one brain.**

### Step 8 — Document the Tool Catalogue

Create a short doc (e.g. `docs/mcp_tools.md`) listing every tool, its inputs, and example usage. Other teams at WSO2 will need this to integrate.

---

## 10. Testing Your MCP Server

There are three layers of testing:

### 10.1 Unit tests for the underlying RAG

You already have these in [tests/](tests/). Don't change them. The `ask()` function still works the same.

### 10.2 MCP-level tests with the Inspector

```bash
mcp dev mcp_server.py
```

Call each tool with sample inputs. Verify schemas look right.

### 10.3 End-to-end with a real client

Either Claude Desktop (manual) or write a tiny Python script that uses `mcp.client` to connect and call your tools (automated).

Example automated test:

```python
# tests/test_mcp_server.py
import asyncio
from mcp.client.streamable_http import streamablehttp_client
from mcp import ClientSession

async def test_ask_tool():
    async with streamablehttp_client("http://localhost:8765/mcp") as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "ask_sre_knowledge_base",
                {"question": "What is CustomerX running?", "customer_scope": ["General"]},
            )
            assert "answer" in result.structuredContent

asyncio.run(test_ask_tool())
```

---

## 11. Common Mistakes and How to Avoid Them

| Mistake | Why it's bad | What to do instead |
|---|---|---|
| Throwing away Streamlit | You lose your human-facing UI | Keep both — they share the same `core/rag.py` |
| Putting business logic inside `@mcp.tool()` functions | Hard to test, hard to reuse | Tools should be **thin wrappers** that call your existing functions |
| Exposing the MCP server without auth | Anyone on the network can query your KB | Always require an API key or OAuth |
| Hardcoding usernames in MCP tools | The calling system has no concept of "alice" or "bob" | Accept username as a tool argument, or use auth claims |
| Ignoring the customer_scope param | Information leakage across customers | Always pass scope through; never default to "everything" |
| Returning huge unstructured blobs | AI clients can't parse them well | Return structured dicts with clear fields |
| Logging sensitive answers in plaintext | Audit/compliance risk | Log questions and metadata, not the full answers |

---

## 12. Glossary

- **MCP (Model Context Protocol)** — Open standard for connecting AI assistants to tools and data sources. Created by Anthropic, now community-maintained.
- **MCP Server** — A program that exposes capabilities (tools/resources/prompts) over MCP. **You are building this.**
- **MCP Client** — A program that consumes those capabilities. Claude Desktop, Claude Code, custom AI agents.
- **Tool** — A callable function exposed by an MCP server. Has a name, description, input schema, and output.
- **Resource** — A readable piece of data (like a file). Identified by a URI.
- **Prompt** — A pre-built prompt template, callable by name.
- **Transport** — How the client and server talk: `stdio`, `streamable-http`, or `sse`.
- **FastMCP** — A high-level Python helper in the `mcp` SDK that lets you build servers with decorators (similar to FastAPI's style).
- **Inspector** — A web UI shipped with the MCP CLI for testing your server interactively. Run with `mcp dev`.
- **JSON Schema** — The format MCP uses to describe tool inputs and outputs. Generated automatically from your Python type hints.
- **OAuth 2.1** — The auth standard MCP recommends for production deployments.

---

## 13. Useful Links

- **Official MCP site:** https://modelcontextprotocol.io
- **MCP specification:** https://spec.modelcontextprotocol.io
- **Python SDK on GitHub:** https://github.com/modelcontextprotocol/python-sdk
- **Example MCP servers:** https://github.com/modelcontextprotocol/servers
- **Anthropic's announcement post:** https://www.anthropic.com/news/model-context-protocol

---

## TL;DR for Your Mentor

> "I read up on MCP. It's a standard protocol that lets AI assistants and other systems call our RAG engine programmatically — same way they'd call any other MCP-compatible tool. I'll add an `mcp_server.py` that exposes our existing `ask()` function as an MCP tool, run it alongside the Streamlit app over HTTP on a separate port, and put it behind an API key (with OAuth as a follow-up). Streamlit stays for human users; MCP becomes the entry point for every other system that needs to query the knowledge base."

That sentence summarises this entire document. You're not rewriting the app — you're **adding a second front door** that AI tools know how to walk through.
