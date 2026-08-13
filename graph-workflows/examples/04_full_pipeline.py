import asyncio
import os
from google.adk import Workflow, Agent, Runner, Event
from google.adk.sessions import InMemorySessionService
from google.adk.workflow import START, JoinNode
from google.adk.events.event_actions import EventActions
from google.genai import types

MODEL = os.environ.get("ADK_MODEL", "gemini-2.5-flash")

def fetch_db1(node_input):
    return {"tier": "premium"}

def fetch_db2(node_input):
    return {"last_order": "laptop"}

def classify_router(node_input):
    data = node_input
    enriched_prompt = f"User is {data['fetch_db1']['tier']}. Last order: {data['fetch_db2']['last_order']}. Help with their billing inquiry."
    return Event(output=enriched_prompt, actions=EventActions(route="billing"))

billing_agent = Agent(name="billing_agent", model=MODEL, instruction="You are billing support. Answer based on context provided. Be brief.")
tech_agent = Agent(name="tech_agent", model=MODEL, instruction="You are tech support. Be brief.")

join = JoinNode(name="joiner")

workflow = Workflow(
    name="full_pipeline",
    edges=[
        (START, fetch_db1, join),
        (START, fetch_db2, join),
        (join, classify_router),
        (classify_router, {
            "billing": billing_agent,
            "tech": tech_agent,
        }),
    ],
)

async def main():
    runner = Runner(
        node=workflow,
        app_name="test_app",
        session_service=InMemorySessionService(),
        auto_create_session=True,
    )
    user_msg = types.Content(role="user", parts=[types.Part(text="I need help with my laptop charge")])
    async for event in runner.run_async(
        user_id="u1", session_id="s1", new_message=user_msg
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    print(f"[{event.author}]: {part.text}")

if __name__ == "__main__":
    asyncio.run(main())
