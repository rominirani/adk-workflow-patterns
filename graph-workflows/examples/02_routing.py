import asyncio
import os
from google.adk import Workflow, Agent, Runner
from google.adk.sessions import InMemorySessionService
from google.adk.workflow import START
from google.adk.events.event_actions import EventActions
from google.adk import Event
from google.genai import types

MODEL = os.environ.get("ADK_MODEL", "gemini-2.5-flash")

def router_node(node_input):
    """Classify the user message and route to the correct specialist."""
    text = ""
    if isinstance(node_input, types.Content):
        text = node_input.parts[0].text.lower()
    else:
        text = str(node_input).lower()

    if "charge" in text or "refund" in text:
        route = "billing"
    elif "where" in text or "tracking" in text:
        route = "shipping"
    else:
        route = "default"

    return Event(
        output=text,
        actions=EventActions(route=route),
    )

billing_agent = Agent(name="billing_agent", model=MODEL, instruction="Handle billing queries. Be brief.")
shipping_agent = Agent(name="shipping_agent", model=MODEL, instruction="Handle shipping queries. Be brief.")
general_agent = Agent(name="general_agent", model=MODEL, instruction="Handle general queries. Be brief.")

workflow = Workflow(
    name="routing_workflow",
    edges=[
        (START, router_node),
        (router_node, {
            "billing": billing_agent,
            "shipping": shipping_agent,
            "default": general_agent,
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

    queries = ["Where is my tracking number?", "I want a refund!"]
    for i, q in enumerate(queries):
        print(f"\n--- Testing: {q} ---")
        user_msg = types.Content(role="user", parts=[types.Part(text=q)])
        async for event in runner.run_async(
            user_id="user_1", session_id=f"session_{i}", new_message=user_msg
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        print(f"[{event.author}]: {part.text}")

if __name__ == "__main__":
    asyncio.run(main())
