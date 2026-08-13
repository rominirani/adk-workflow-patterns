# Graph Workflows — ADK 2 by Example

> *"You draw the graph. The framework executes it."*

Graph workflows are for when you know the exact shape of your pipeline before any user input arrives. You define nodes (functions or agents), connect them with edges, and the framework handles execution order, parallelism, and data flow.

---

## When to Use Graph Workflows

| Scenario | Example |
|---|---|
| Fixed processing pipeline | Intake → Enrich → Classify → Respond |
| Deterministic routing | Keyword-based ticket routing |
| Parallel data fetching | Fetch from 3 APIs simultaneously |
| Quality control loops | Draft → Critique → Revise → Approve |
| Human-in-the-loop | Pause for manager approval on large refunds |

## Examples

Each example is a self-contained, runnable Python file tested against ADK 2.6.3 + Vertex AI.

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
python graph-workflows/examples/01_sequential.py
```

### Example Index

| # | File | Pattern | Core Concept |
|---|---|---|---|
| 01 | [01_sequential.py](examples/01_sequential.py) | Sequential Pipeline | `(START, fn1, fn2, agent)` — chain nodes in a tuple |
| 02 | [02_routing.py](examples/02_routing.py) | Conditional Routing | `EventActions(route=...)` with dict-based branching |
| 03 | [03_parallel_join.py](examples/03_parallel_join.py) | Parallel + Join | `JoinNode` collects parallel branches into one dict |
| 04 | [04_full_pipeline.py](examples/04_full_pipeline.py) | Full Pipeline | Fan-out → Join → Classify → Route to specialist |
| 05 | [05_nested.py](examples/05_nested.py) | Nested Workflows | Use a `Workflow` as a node inside another `Workflow` |
| 06 | [06_loop.py](examples/06_loop.py) | Loop + Quality Gate | Route `"fail"` loops back; `"pass"` breaks out |
| 07 | [07_hitl.py](examples/07_hitl.py) | Human-in-the-Loop | Pause workflow, resume with `state_delta` |
| 08 | [08_dynamic.py](examples/08_dynamic.py) | Dynamic Nodes | `@node(rerun_on_resume=True)` + `ctx.run_node()` |
| 09 | [09_complete_system.py](examples/09_complete_system.py) | Complete System | All patterns composed in one graph |

## Key API Patterns

### Defining a Graph

```python
from google.adk import Workflow
from google.adk.workflow import START, JoinNode

workflow = Workflow(
    name="my_workflow",
    edges=[
        (START, step_a, step_b, agent),      # Sequential
        (START, fetch1, join),                # Parallel branch 1
        (START, fetch2, join),                # Parallel branch 2
        (join, router),                       # After join
        (router, {"billing": bill, "tech": tech}),  # Conditional
    ],
)
```

### Function Nodes Receive `node_input`

```python
def my_node(node_input):
    """Receives the output of the previous node."""
    return {"processed": node_input}
```

### Routing with EventActions

```python
from google.adk import Event
from google.adk.events.event_actions import EventActions

def router(node_input):
    return Event(output=data, actions=EventActions(route="billing"))
```

### State Access

```python
def my_node(node_input, ctx):
    """ctx parameter gives access to session state."""
    ctx.state["key"] = "value"
    count = ctx.state.get("count", 0)
```

---

*Part of [ADK Workflow Patterns](../README.md)*
