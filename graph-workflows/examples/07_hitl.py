import asyncio
import os
from google.adk import Workflow, Agent, Runner, Event
from google.adk.sessions import InMemorySessionService
from google.adk.workflow import START
from google.adk.events.event_actions import EventActions
from google.genai import types

MODEL = os.environ.get("ADK_MODEL", "gemini-2.5-flash")

def check_refund(node_input, ctx):
    """Check refund amount. If > $100, pause for human approval."""
    already_approved = ctx.state.get("approval_status", None)

    if already_approved == "approved":
        print("[check_refund] Manager approved! Processing refund.")
        return Event(output="Refund Processed", actions=EventActions(route="approved"))
    elif already_approved == "rejected":
        print("[check_refund] Manager rejected the refund.")
        return Event(output="Refund Rejected", actions=EventActions(route="rejected"))

    # First time through: check the amount
    refund_amount = 500  # Simulated
    print(f"[check_refund] Refund amount is ${refund_amount}. Requires manager approval.")
    # Set state so the app layer can see it
    ctx.state["pending_refund"] = refund_amount
    ctx.state["needs_approval"] = True
    return Event(output=f"Pending approval for ${refund_amount} refund")

def process_approved(node_input):
    print(f"[process_approved] {node_input}")
    return f"Final Status: {node_input}"

def process_rejected(node_input):
    print(f"[process_rejected] {node_input}")
    return f"Final Status: {node_input}"

workflow = Workflow(
    name="hitl_workflow",
    edges=[
        (START, check_refund),
        (check_refund, {
            "approved": process_approved,
            "rejected": process_rejected,
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

    # --- First Run: Workflow pauses for approval ---
    print("=== RUN 1: Refund Request (Pauses) ===")
    user_msg = types.Content(role="user", parts=[types.Part(text="I want a refund for order #123")])
    async for event in runner.run_async(
        user_id="u1", session_id="s1", new_message=user_msg
    ):
        if event.output is not None:
            print(f"[{event.author}] output: {event.output}")

    print("\n--- Manager reviews... decides to approve ---\n")

    # --- Second Run: Manager approves, workflow resumes ---
    print("=== RUN 2: Manager Approves (Resumes) ===")
    approval_msg = types.Content(role="user", parts=[types.Part(text="Approved by manager")])
    async for event in runner.run_async(
        user_id="u1", session_id="s1", new_message=approval_msg,
        state_delta={"approval_status": "approved"},
    ):
        if event.output is not None:
            print(f"[{event.author}] output: {event.output}")

if __name__ == "__main__":
    asyncio.run(main())
