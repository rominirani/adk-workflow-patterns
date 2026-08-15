# ADK Workflow Patterns — Learn by Example

**Practical, tested examples for building AI agent workflows with Google's Agent Development Kit (ADK).**

[![ADK](https://img.shields.io/badge/ADK-2.6.3-blue)](https://adk.dev)
[![Python](https://img.shields.io/badge/Python-3.11+-green)](https://python.org)
[![License](https://img.shields.io/badge/License-Apache%202.0-orange)](LICENSE)

---

I created this repo because I wanted to learn the ADK Workflow system from the ground up. The official docs are great, but I learn best by writing real code, running it, breaking it, and fixing it. So I built a series of progressively complex examples — each one tested against a live Vertex AI backend — to map out how every pattern actually works in practice.

If you're the kind of developer who learns by doing, this repo is for you.

## 📚 Guides

This repo contains two comprehensive guides, each with fully tested, runnable code examples:

### 1. [Graph Workflows](graph-workflows/) — 9 Examples
> *"You draw the graph. The framework executes it."*

When you know the exact shape of your workflow ahead of time, graph workflows give you deterministic, reproducible pipelines. Think assembly lines.

| # | Pattern | What You'll Learn |
|---|---|---|
| 01 | Sequential Pipeline | Chain nodes: `START → A → B → Agent` |
| 02 | Conditional Routing | Branch based on keywords with `EventActions(route=...)` |
| 03 | Parallel Fan-out + Join | Run 3 tasks in ~1s instead of ~3s with `JoinNode` |
| 04 | Full Pipeline | Fan-out → Join → Classify → Route |
| 05 | Nested Workflows | Compose workflows inside workflows |
| 06 | Loop with Quality Gate | Draft → Critic → Loop back or break |
| 07 | Human-in-the-Loop | Pause for approval, resume with `state_delta` |
| 08 | Dynamic Nodes | `@node(rerun_on_resume=True)` + `ctx.run_node()` |
| 09 | Complete System | All patterns in one graph |

### 2. [Collaborative Workflows](collaborative-workflows/) — 5 Examples
> *"You define the team. The LLM decides who plays."*

When you know the specialists but the user's request determines who gets involved, collaborative multi-agent teams let the LLM orchestrate dynamically.

| # | Pattern | What You'll Learn |
|---|---|---|
| 01 | Coordinator-Dispatcher | Semantic routing via `Agent(sub_agents=[...])` and `description` |
| 02 | Sub-Agent Transfer Modes | `single_turn`, `task` with `output_schema`, and `chat` modes |
| 03 | Supervisor & Specialists | Drafter + Critic multi-agent peer review |
| 04 | Custom BaseAgent | Programmatic control, `ctx.session.state`, & dynamic dispatch |
| 05 | Complete Support Concierge | Full multi-agent customer support architecture |

### 3. [Agent Memory Guide](memory-guide/) — 8 Graded Rungs (L0 → L7)
> *"Ask an agent for dinner ideas on Monday, come back Wednesday, and most agents greet you like a stranger."*

Master agent memory from scratchpad session states to durable SQL databases, vector memory banks, working-memory compaction, and zero-rewrite Vertex AI cloud memory.

| Level | Rung | What You'll Learn |
|---|---|---|
| L0 | Stateless Goldfish | Baseline: Why agents forget across sessions |
| L1 | Within-Chat Scratchpad | Multi-agent variable sharing with `output_key` & `session.state` |
| L2 | Durable User State | Cross-session persistence with `DatabaseSessionService` & `user:*` |
| L3 | Searchable Vector Memory | Long-term memory search with `add_session_to_memory` |
| L4 | File Artifacts | External document retrieval with `FileArtifactService` |
| L5 | Working-Memory Management | `EventsCompactionConfig` & conversational rewind |
| L6 | Durability & Checkpoints | Pausing & resuming workflows with `state_delta` |
| L7 | Managed Cloud Memory | Zero-rewrite scale with `VertexAiSessionService` & Memory Bank |

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Google Cloud project with Vertex AI API enabled (or Gemini API key)
- `gcloud auth login` completed

### Setup

```bash
# Clone the repo
git clone https://github.com/rominirani/adk-workflow-patterns.git
cd adk-workflow-patterns

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install google-adk pydantic

# Configure Vertex AI
export GOOGLE_CLOUD_PROJECT="your-project-id"
export GOOGLE_CLOUD_LOCATION="us-central1"
export GOOGLE_GENAI_USE_VERTEXAI="True"
```

### Run Any Example

```bash
# Graph workflow example
python graph-workflows/examples/01_sequential.py

# Collaborative workflow example
python collaborative-workflows/examples/01_coordinator_routing.py
```

### Using an API Key Instead

If you prefer using the Gemini API directly instead of Vertex AI:

```bash
export GOOGLE_API_KEY="your-api-key"
# Don't set GOOGLE_GENAI_USE_VERTEXAI
```

## 🏗️ Repo Structure

```
adk-workflow-patterns/
├── README.md                              ← You are here
├── graph-workflows/
│   ├── README.md                          ← Deterministic graph workflows guide
│   └── examples/
│       ├── 01_sequential.py
│       ├── 02_routing.py
│       ├── ...
│       └── 09_complete_system.py
├── collaborative-workflows/
│   ├── README.md                          ← Autonomous multi-agent guide
│   └── examples/
│       ├── 01_coordinator_routing.py
│       ├── 02_transfer_modes.py
│       ├── 03_supervisor_collaboration.py
│       ├── 04_custom_orchestrator.py
│       └── 05_complete_support_system.py
├── requirements.txt
├── .gitignore
└── LICENSE
```

## 🔑 Key ADK 2 Concepts

| Concept | Graph Workflows | Collaborative Workflows |
|---|---|---|
| **Who decides what runs?** | The graph topology | The LLM model / Supervisor |
| **Core primitive** | `Workflow(edges=[...])` | `Agent(sub_agents=[...])` |
| **Data flow** | `node_input` parameter | Session state (`ctx.session.state`) / sub-agent returns |
| **Routing** | `EventActions(route=...)` | LLM reads semantic `description` fields |
| **Parallelism** | `JoinNode` | Concurrent tool / sub-agent dispatch |
| **Refinement / Loops** | Graph conditional back-edge | Supervisor / Critic collaboration |
| **Dynamic Custom Logic** | `@node` + `ctx.run_node()` | `BaseAgent._run_async_impl()` |

## ⚠️ ADK Version Notes

These examples are tested against **ADK 2.6+**. Notable API details:

- `SequentialAgent`, `ParallelAgent`, and `LoopAgent` are **deprecated** in favor of `Workflow`. For deterministic chains, parallel joins, and loops, use `Workflow` (see [Graph Workflows](graph-workflows/)).
- `Agent` is the modern canonical alias for `LlmAgent`.
- Function nodes receive upstream data via a `node_input` parameter (by name).
- Session state in `BaseAgent` is accessed via `ctx.session.state`, not `ctx.state`.
- Dynamic nodes in graphs use `@node(rerun_on_resume=True)`.

## 📝 License

Apache 2.0 — see [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

- [Google ADK Documentation](https://adk.dev)
- [Vertex AI](https://cloud.google.com/vertex-ai)
- Built with ☕ and curiosity
