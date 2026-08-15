# Architecting Agent Memory: Session State, Vector Search, and Managed Cloud Memory

> *"Ask an agent for dinner ideas on Monday, come back Wednesday, and most agents greet you like a stranger."*

Across eight graded rungs (**L0 → L7**), this guide explores the journey from a stateless goldfish to an enterprise-grade agent with vector memory, durable cross-session states, file artifacts, working-memory management, and zero-rewrite cloud scaling on Google Cloud Vertex AI.

[![ADK](https://img.shields.io/badge/ADK-2.6+-blue)](https://adk.dev)
[![Python](https://img.shields.io/badge/Python-3.11+-green)](https://python.org)
[![Model](https://img.shields.io/badge/Model-Gemini%202.5%20Flash-orange)](https://deepmind.google/technologies/gemini/)

---

## 🪜 The 8 Memory Rungs (L0 → L7)

```mermaid
flowchart TD
    L0["🐟 L0: Stateless Goldfish\n(Every invocation starts from zero)"] --> L1["📝 L1: Within-Chat Scratchpad\n(session.state / output_key)"]
    L1 --> L2["💾 L2: Durable User State\n(DatabaseSessionService + user: scope)"]
    L2 --> L3["🔍 L3: Searchable Long-Term Memory\n(add_session_to_memory / preload_memory_tool)"]
    L3 --> L4["📁 L4: File Artifacts\n(FileArtifactService / load_artifacts_tool)"]
    L4 --> L5["🧹 L5: Working-Memory Management\n(Compaction & Conversation Rewind)"]
    L5 --> L6["⏸️ L6: Durability & Human-in-the-Loop\n(Pause / Checkpoint / Resume with state_delta)"]
    L6 --> L7["☁️ L7: Managed Cloud Memory\n(VertexAiSessionService, Vertex Memory Bank, GCS)"]

    style L0 fill:#fee2e2,stroke:#ef4444,stroke-width:2px
    style L1 fill:#fef3c7,stroke:#f59e0b,stroke-width:2px
    style L2 fill:#fef3c7,stroke:#f59e0b,stroke-width:2px
    style L3 fill:#dcfce7,stroke:#10b981,stroke-width:2px
    style L4 fill:#dcfce7,stroke:#10b981,stroke-width:2px
    style L5 fill:#e0e7ff,stroke:#6366f1,stroke-width:2px
    style L6 fill:#e0e7ff,stroke:#6366f1,stroke-width:2px
    style L7 fill:#f3e8ff,stroke:#a855f7,stroke-width:3px
```

---

## 🚀 Example Index & Code Map

Every rung is tested against live Gemini models on Google Cloud Vertex AI:

| Level | File | Concept | ADK 2 API Primitives |
|---|---|---|---|
| **L0** | [`00_l0_stateless.py`](examples/00_l0_stateless.py) | **Stateless Goldfish** | `Agent`, `Runner`, `InMemorySessionService` |
| **L1** | [`01_l1_session_state.py`](examples/01_l1_session_state.py) | **Within-Chat Scratchpad** | `output_key`, `ctx.session.state` |
| **L2** | [`02_l2_durable_user_state.py`](examples/02_l2_durable_user_state.py) | **Durable Cross-Session State** | `DatabaseSessionService`, `user:*` prefix |
| **L3** | [`03_l3_searchable_memory.py`](examples/03_l3_searchable_memory.py) | **Searchable Vector Memory** | `add_session_to_memory`, `preload_memory_tool` |
| **L4** | [`04_l4_file_artifacts.py`](examples/04_l4_file_artifacts.py) | **External File Artifacts** | `FileArtifactService`, `load_artifacts_tool` |
| **L5** | [`05_l5_working_memory_compaction.py`](examples/05_l5_working_memory_compaction.py) | **Working-Memory Management** | `EventsCompactionConfig`, `rewind_before_invocation_id` |
| **L6** | [`06_l6_durability_pause_resume.py`](examples/06_l6_durability_pause_resume.py) | **Durability & Checkpoints** | `EventActions(state_delta=...)`, pause/resume |
| **L7** | [`07_l7_managed_cloud_memory.py`](examples/07_l7_managed_cloud_memory.py) | **Managed Cloud Memory** | `VertexAiSessionService`, `VertexAiMemoryBankService` |

---

## 🛠️ Google Cloud Database Setup & Running

```bash
# 1. Activate virtual environment
source .venv/bin/activate

# 2. Install dependencies (including Google Cloud & Async Database support)
pip install "google-adk[gcp]" "google-adk[db]" asyncpg sqlalchemy google-cloud-aiplatform google-cloud-storage

# 3. Configure Google Cloud Project & Location
export GOOGLE_CLOUD_PROJECT="your-project-id"
export GOOGLE_CLOUD_LOCATION="us-central1"
export GOOGLE_GENAI_USE_VERTEXAI="True"

# 4. Provision & Configure Google Cloud Database (Option A: Cloud SQL PostgreSQL)
# gcloud sql instances create adk-chef-db --database-version=POSTGRES_15 --cpu=2 --memory=7680MiB --region=us-central1
# gcloud sql users set-password postgres --instance=adk-chef-db --password="YOUR_PASSWORD"
# gcloud sql databases create chef_memory --instance=adk-chef-db
export CLOUDSQL_DATABASE_URL="postgresql+asyncpg://postgres:YOUR_PASSWORD@127.0.0.1:5432/chef_memory"

# 5. Run any memory rung
python memory-guide/examples/02_l2_durable_user_state.py
```

---

## 🧠 Architectural Insights: "Persistence is NOT Memory"

One of the most important conceptual epiphanies in building production AI agents is understanding that **Session Persistence** and **Memory** solve two completely different problems:

```
┌──────────────────────────────────────────────┐  ┌──────────────────────────────────────────────┐
│       SESSION PERSISTENCE (L1 / L2)          │  │       SEARCHABLE MEMORY (L3 / L7)            │
│                                              │  │                                              │
│ • "What did the user say 2 minutes ago?"     │  │ • "What does the user like in general?"      │
│ • Exact chronological event log              │  │ • Semantic vector search over all past days  │
│ • Hard token limit: blowing up context window│  │ • Token efficient: retrieves top-K snippets  │
│ • Stored in DatabaseSessionService           │  │ • Stored in MemoryService / Memory Bank       │
└──────────────────────────────────────────────┘  └──────────────────────────────────────────────┘
```

---

## 🎯 Conclusion: The 5 Golden Rules of Agent Memory

1. **Persistence is NOT Memory**: Use `DatabaseSessionService` to preserve chronological turn events for the active session, but use `MemoryService` (vector search) for cross-session long-term recall to protect context limits.
2. **Use Scoped State**: Prefix permanent user flags with `user:*` (e.g. `user:dietary_preferences`) so they automatically hydrate across new sessions for the same user ID.
3. **Keep Heavy Documents in Artifacts**: Offload multi-page PDFs, menus, and reports to `FileArtifactService` or `GcsArtifactService`, and query them via `load_artifacts_tool`.
4. **Manage Working Memory**: Implement `EventsCompactionConfig` for long multi-turn conversations and emit `rewind_before_invocation_id` to prune hallucinations.
5. **Zero-Rewrite Cloud Scaling**: Keep agent definitions clean and standard. Swap local SQLite and RAM services for Vertex AI Cloud Memory with zero code changes.

---

*Part of [ADK Workflow Patterns](../README.md)*
