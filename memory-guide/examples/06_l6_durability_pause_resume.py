"""06: L6 Durability & State Delta — Checkpointing, Pausing, and Resuming long-running workflows"""
import asyncio
import os
import warnings
import logging

warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=ResourceWarning)
logging.getLogger("google.genai").setLevel(logging.ERROR)
logging.getLogger("aiohttp").setLevel(logging.ERROR)

from google.adk import Workflow, Agent, Runner, Event
from google.adk.workflow import START
from google.adk.events.event_actions import EventActions
from google.adk.sessions import DatabaseSessionService
from google.genai import types

MODEL = os.environ.get("ADK_MODEL", "gemini-2.5-flash")

# Cloud Database configuration (Google Cloud SQL PostgreSQL / AlloyDB)
# Connection URL format: postgresql+asyncpg://<db_user>:<db_password>@<cloud_sql_host>/<database>
CLOUDSQL_DB_URL = os.environ.get(
    "CLOUDSQL_DATABASE_URL", 
    "sqlite+aiosqlite:///durable_cloud_workflow.db"
)

# Step 1: Automated Proposal Drafter
menu_drafter = Agent(
    name="menu_drafter",
    model=MODEL,
    instruction="""Draft a 3-course private catering menu for 20 guests based on the user's budget.
    Keep it concise. End with: 'Awaiting Host Approval.'""",
    output_key="draft_menu",
)

# Step 2: Human-in-the-Loop Gate Node (Pauses execution and checkpoints session state)
def approval_gate(node_input):
    """Examines state for approval. If not approved, pauses workflow."""
    return Event(
        output="Workflow paused: Waiting for Host approval and payment authorization.",
        actions=EventActions(
            state_delta={"workflow_status": "WAITING_FOR_HOST_APPROVAL"}
        )
    )

# Step 3: Kitchen Production Dispatcher (Executes only after resume)
kitchen_dispatcher = Agent(
    name="kitchen_dispatcher",
    model=MODEL,
    instruction="""You are the kitchen production dispatcher.
    The host has approved the catering proposal!
    Review the draft menu in the session and output an ingredient procurement list and chef roster.""",
)

catering_workflow = Workflow(
    name="durable_catering_pipeline",
    edges=[
        (START, menu_drafter),
        (menu_drafter, approval_gate),
    ],
)

resumed_workflow = Workflow(
    name="durable_catering_pipeline_resumed",
    edges=[
        (START, kitchen_dispatcher),
    ],
)

async def main():
    if os.path.exists("durable_cloud_workflow.db"):
        os.remove("durable_cloud_workflow.db")

    session_service = DatabaseSessionService(db_url=CLOUDSQL_DB_URL)

    # -------------------------------------------------------------------------
    # PHASE 1: Execution runs up to approval gate and checkpoints to Database
    # -------------------------------------------------------------------------
    print("=== PHASE 1: Workflow runs and pauses at Approval Gate ===")
    runner1 = Runner(
        node=catering_workflow,
        app_name="catering_app",
        session_service=session_service,
    )

    session = await session_service.create_session(app_name="catering_app", user_id="u_host")
    msg1 = types.Content(role="user", parts=[types.Part(text="We have a $150/person budget for our anniversary party.")])
    
    async for event in runner1.run_async(user_id="u_host", session_id=session.id, new_message=msg1):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    print(f"[{event.author}]: {part.text[:120]}...")

    # Check DB state
    s_paused = await session_service.get_session(app_name="catering_app", user_id="u_host", session_id=session.id)
    print(f"\n[Checkpointed DB State]: workflow_status = {s_paused.state.get('workflow_status')}")

    # -------------------------------------------------------------------------
    # PHASE 2: Hours/Days later — Human Approves -> Resume with state_delta
    # -------------------------------------------------------------------------
    print("\n" + "="*65)
    print("=== PHASE 2: Host Approves Proposal -> Resume with state_delta ===")
    print("="*65)

    # Human provides approval token and budget confirmation into session state
    approval_event = Event(
        author="host",
        actions=EventActions(
            state_delta={
                "workflow_status": "APPROVED",
                "payment_confirmed": True,
                "host_signature": "Alex Johnson, Verified",
            }
        )
    )
    await session_service.append_event(s_paused, approval_event)
    print("State delta applied: Host signature and payment confirmed in persistent DB.")

    # Resume execution with the kitchen dispatcher
    runner2 = Runner(
        node=resumed_workflow,
        app_name="catering_app",
        session_service=session_service,
    )
    
    resume_trigger = types.Content(role="user", parts=[types.Part(text="Proceed with kitchen production!")])
    async for event in runner2.run_async(user_id="u_host", session_id=session.id, new_message=resume_trigger):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    print(f"[{event.author}]: {part.text}")

    if os.path.exists("durable_workflow.db"):
        os.remove("durable_workflow.db")

if __name__ == "__main__":
    asyncio.run(main())
