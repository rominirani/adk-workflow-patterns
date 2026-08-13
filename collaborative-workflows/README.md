# Collaborative Workflows — ADK 2 by Example

> *"You define the team. The LLM decides who plays."*

Collaborative workflows are for when you know the specialists available but the user's request determines which ones get involved and in what order. The LLM reads each agent's `description` and routes accordingly.

---

## When to Use Collaborative Workflows

| Scenario | Example |
|---|---|
| Intent-based routing | "Refund" → billing, "crash" → tech support |
| Multi-turn conversations | Appointment booking agent that asks follow-ups |
| Quality review loops | Draft → Evaluate → Revise until approved |
| Mixed specialist teams | Coordinator delegates to the right expert |
| Conditional complexity | P1 tickets get parallel enrichment; P4 get quick answers |

## Examples

Each example is self-contained and tested against ADK 2.6.3 + Vertex AI.

### Setup

```bash
# From the repo root
python3 -m venv .venv && source .venv/bin/activate
pip install google-adk

export GOOGLE_CLOUD_PROJECT="your-project-id"
export GOOGLE_CLOUD_LOCATION="us-central1"
export GOOGLE_GENAI_USE_VERTEXAI="True"
```

### Run

```bash
python collaborative-workflows/examples/01_sequential_pipeline.py
```

### Example Index

| # | File | Pattern | Core Concept |
|---|---|---|---|
| 01 | [01_sequential_pipeline.py](examples/01_sequential_pipeline.py) | Sequential Pipeline | `SequentialAgent(sub_agents=[...])` with `output_key` |
| 02 | [02_parallel_delegators.py](examples/02_parallel_delegators.py) | Parallel Delegators | `ParallelAgent` runs 3 analyses concurrently |
| 03 | [03_evaluator_optimizer.py](examples/03_evaluator_optimizer.py) | Evaluator-Optimizer | `LoopAgent(max_iterations=3)` with writer + critic |
| 04 | [04_coordinator.py](examples/04_coordinator.py) | Coordinator-Dispatcher | LLM routes via `sub_agents` + `description` |
| 05 | [05_custom_workflow.py](examples/05_custom_workflow.py) | Custom BaseAgent | `_run_async_impl` with conditional branching |
| 06 | [06_transfer_modes.py](examples/06_transfer_modes.py) | Transfer Modes | `single_turn`, `task`, `chat` modes |
| 07 | [07_complete_system.py](examples/07_complete_system.py) | Complete System | All patterns under one coordinator |

## Key API Patterns

### Coordinator-Dispatcher (The Star Pattern)

```python
coordinator = LlmAgent(
    name="concierge",
    model=MODEL,
    instruction="Route to the right specialist.",
    sub_agents=[billing, tech, shipping],  # LLM reads descriptions
)
```

### Sequential Pipeline

```python
pipeline = SequentialAgent(
    name="support_pipeline",
    sub_agents=[triage, enrich, respond],  # Runs in order
)
```

### Data Passing with `output_key`

```python
triage = LlmAgent(
    name="triage",
    model=MODEL,
    instruction="Classify priority...",
    output_key="triage_result",  # Saved to session state
)

# Next agent reads from conversation context automatically
```

### Transfer Modes

```python
# Runs once, returns immediately — no user interaction
lookup = LlmAgent(name="lookup", mode="single_turn", ...)

# Can ask user questions, auto-returns when done
booker = LlmAgent(name="booker", mode="task", ...)

# Full multi-turn conversation (default)
advisor = LlmAgent(name="advisor", mode="chat", ...)
```

### Custom BaseAgent

```python
class SmartRouter(BaseAgent):
    async def _run_async_impl(self, ctx):
        async for event in triage.run_async(ctx):
            yield event
        priority = ctx.session.state.get("priority", "P3")
        if priority == "P1":
            async for event in urgent_handler.run_async(ctx):
                yield event
```

## ⚠️ Deprecation Notice

`SequentialAgent`, `ParallelAgent`, and `LoopAgent` are **deprecated** in ADK 2.6+ in favor of `Workflow`. They still work but will be removed. We use them here because `Workflow` cannot yet be used as an `LlmAgent` sub-agent. See the [Graph Workflows Guide](../graph-workflows/) for the `Workflow`-based approach.

---

*Part of [ADK Workflow Patterns](../README.md)*
