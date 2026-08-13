import asyncio
import os
import time
from google.adk import Workflow, Runner
from google.adk.sessions import InMemorySessionService
from google.adk.workflow import START, JoinNode
from google.genai import types

MODEL = os.environ.get("ADK_MODEL", "gemini-2.5-flash")

async def fetch_profile(node_input):
    await asyncio.sleep(1)
    return {"name": "Alice", "tier": "gold"}

async def fetch_orders(node_input):
    await asyncio.sleep(1)
    return {"recent_orders": 5}

async def fetch_account(node_input):
    await asyncio.sleep(1)
    return {"status": "active"}

def process_results(node_input):
    data = node_input
    summary = f"User {data['fetch_profile']['name']} is {data['fetch_profile']['tier']} tier with {data['fetch_orders']['recent_orders']} recent orders. Account: {data['fetch_account']['status']}."
    print(f"Summary: {summary}")
    return summary

join_node = JoinNode(name="data_joiner")

workflow = Workflow(
    name="parallel_workflow",
    edges=[
        (START, fetch_profile, join_node),
        (START, fetch_orders, join_node),
        (START, fetch_account, join_node),
        (join_node, process_results),
    ],
)

async def main():
    runner = Runner(
        node=workflow,
        app_name="test_app",
        session_service=InMemorySessionService(),
        auto_create_session=True,
    )
    user_msg = types.Content(role="user", parts=[types.Part(text="start")])
    start_time = time.time()
    async for event in runner.run_async(
        user_id="user_1", session_id="session_1", new_message=user_msg
    ):
        if event.output is not None:
            print(f"[{event.author}] output: {event.output}")
    elapsed = time.time() - start_time
    print(f"Total time: {elapsed:.2f} seconds (3 tasks each taking 1s ran in parallel)")

if __name__ == "__main__":
    asyncio.run(main())
