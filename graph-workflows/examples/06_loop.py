import asyncio
import os
from google.adk import Workflow, Agent, Runner, Event
from google.adk.sessions import InMemorySessionService
from google.adk.workflow import START
from google.adk.events.event_actions import EventActions
from google.genai import types

MODEL = os.environ.get("ADK_MODEL", "gemini-2.5-flash")

drafter = Agent(
    name="drafter",
    model=MODEL,
    instruction="Draft a short, 1-sentence customer apology for the issue described. Be specific and empathetic.",
)

def critic(node_input, ctx):
    """Evaluate the draft. Reject first 2 attempts, approve on 3rd."""
    attempts = ctx.state.get("attempts", 0) + 1
    ctx.state["attempts"] = attempts

    if attempts < 3:
        route = "fail"
        msg = f"Attempt {attempts} rejected. Too generic. Try again with more empathy."
    else:
        route = "pass"
        msg = f"Attempt {attempts} approved!"

    print(f"[critic] {msg}")
    return Event(output=msg, actions=EventActions(route=route))

finalize = Agent(
    name="finalize",
    model=MODEL,
    instruction="Output the approved message as the final customer response. Keep it brief.",
)

workflow = Workflow(
    name="loop_workflow",
    edges=[
        (START, drafter, critic),
        (critic, {
            "fail": drafter,   # Loop back!
            "pass": finalize,  # Break out
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
    user_msg = types.Content(role="user", parts=[types.Part(text="I got the wrong item in my order.")])
    async for event in runner.run_async(
        user_id="u1", session_id="s1", new_message=user_msg
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    print(f"[{event.author}]: {part.text}")

if __name__ == "__main__":
    asyncio.run(main())
