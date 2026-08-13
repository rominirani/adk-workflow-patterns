import asyncio
import os
from google.adk import Workflow, Runner
from google.adk.sessions import InMemorySessionService
from google.adk.workflow import START
from google.genai import types

MODEL = os.environ.get("ADK_MODEL", "gemini-2.5-flash")

def step_a(node_input):
    print("[sub] step_a: Sub process started")
    return "Sub process started"

def step_b(node_input):
    print(f"[sub] step_b: Received '{node_input}', finishing sub process")
    return "Sub process finished"

sub_workflow = Workflow(
    name="sub_process",
    edges=[(START, step_a, step_b)],
)

def prepare(node_input):
    print("[main] prepare: Getting ready")
    return "Ready"

def finalize(node_input):
    print(f"[main] finalize: Sub gave us '{node_input}'")
    return f"Done. Sub gave: {node_input}"

main_workflow = Workflow(
    name="main_process",
    edges=[(START, prepare, sub_workflow, finalize)],
)

async def main():
    runner = Runner(
        node=main_workflow,
        app_name="test_app",
        session_service=InMemorySessionService(),
        auto_create_session=True,
    )
    user_msg = types.Content(role="user", parts=[types.Part(text="go")])
    async for event in runner.run_async(
        user_id="u1", session_id="s1", new_message=user_msg
    ):
        if event.output is not None:
            print(f"[{event.author}] output: {event.output}")

if __name__ == "__main__":
    asyncio.run(main())
