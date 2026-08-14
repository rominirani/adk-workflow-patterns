"""Complete Customer Support System: combines all graph workflow patterns.

1. Parallel Data Fetchers (Profile, Orders, Billing) + JoinNode
2. Dynamic Classification & Routing based on user message
3. Tech Path -> Dynamic Troubleshooting Loop (@node with ctx.run_node)
4. Billing Path -> Billing Agent -> Human-in-the-Loop (HITL) Approval Check
5. Shipping & General Specialists
"""
import asyncio
import os
import time
import warnings
import logging

# Suppress internal SDK noise and warnings
warnings.filterwarnings("ignore", category=UserWarning, module="google.genai")
warnings.filterwarnings("ignore", category=ResourceWarning)
logging.getLogger("google.genai").setLevel(logging.ERROR)
logging.getLogger("aiohttp").setLevel(logging.ERROR)

from google.adk import Workflow, Agent, Runner, Event
from google.adk.sessions import InMemorySessionService
from google.adk.workflow import START, JoinNode, node
from google.adk.events.event_actions import EventActions
from google.genai import types

MODEL = os.environ.get("ADK_MODEL", "gemini-2.5-flash")

# ===== Section 1: Parallel Data Fetchers =====
async def fetch_profile(node_input):
    await asyncio.sleep(0.3)
    return {"name": "Alice", "tier": "Gold", "account_age": "2 years"}

async def fetch_orders(node_input):
    await asyncio.sleep(0.3)
    return {"recent_orders": 3, "last_order": "Pro Laptop #8492"}

async def fetch_billing(node_input):
    await asyncio.sleep(0.3)
    return {"outstanding_balance": 0, "payment_method": "Visa-4242"}

# ===== Section 2: Classifier / Router =====
def classify_and_route(node_input, ctx):
    """Inspects user message in state and routes to the right specialist."""
    user_text = ctx.state.get("user_message", "").lower()
    profile = node_input.get("fetch_profile", {})
    context_summary = f"Customer: {profile.get('name', 'User')}, Tier: {profile.get('tier', 'Standard')}"
    
    if "approval_status" in ctx.state or "refund" in user_text or "charge" in user_text or "bill" in user_text:
        route = "billing"
    elif "crash" in user_text or "error" in user_text or "bug" in user_text:
        route = "tech"
    elif "track" in user_text or "package" in user_text or "delivery" in user_text:
        route = "shipping"
    else:
        route = "general"
        
    return Event(output=context_summary, actions=EventActions(route=route))

# ===== Section 3: Dynamic Tech Troubleshooting Node =====
diagnose_agent = Agent(
    name="tech_diagnostician",
    model=MODEL,
    instruction="Suggest ONE specific troubleshooting step in 1 sentence.",
)

@node(rerun_on_resume=True)
async def dynamic_troubleshoot(ctx):
    """Loops up to 2 attempts using ctx.run_node before escalating."""
    for attempt in (1, 2):
        print(f"  [Troubleshoot Loop] Attempt {attempt}...")
        result = await ctx.run_node(diagnose_agent)
        print(f"  [Diagnostician {attempt}]: {result}")
    return "Troubleshooting attempts completed. Escalated to Tier 2."

# ===== Section 4: Billing Agent & HITL Gate =====
billing_agent = Agent(
    name="billing_specialist",
    model=MODEL,
    instruction="Acknowledge the billing refund inquiry empathetically in 1 sentence.",
)

def check_refund_hitl(node_input, ctx):
    """HITL Gate: If refund amount > $100, pause for human approval."""
    already_approved = ctx.state.get("approval_status", None)
    if already_approved == "approved":
        return Event(output="Refund Processed: APPROVED by Manager", actions=EventActions(route="approved"))
    elif already_approved == "rejected":
        return Event(output="Refund Processed: REJECTED by Manager", actions=EventActions(route="rejected"))

    refund_amount = ctx.state.get("refund_amount", 150)
    ctx.state["pending_refund"] = refund_amount
    ctx.state["needs_approval"] = True
    print(f"  [HITL Gate] Refund of ${refund_amount} exceeds $100 auto-limit. Pausing for approval.")
    return Event(output=f"PAUSED: Requires manager approval for ${refund_amount} refund")

def process_approved(node_input):
    return f"Final Status: {node_input}"

# ===== Section 5: Shipping & General Agents =====
shipping_agent = Agent(
    name="shipping_specialist",
    model=MODEL,
    instruction="Provide a tracking status update for Order #8492 in 1 sentence.",
)

general_agent = Agent(
    name="general_specialist",
    model=MODEL,
    instruction="Answer general support inquiry helpfully in 1 sentence.",
)

# ===== Section 6: Build Unified Graph =====
join = JoinNode(name="data_joiner")

workflow = Workflow(
    name="complete_support_system",
    edges=[
        # 1. Parallel Fan-out from START to data fetchers
        (START, fetch_profile, join),
        (START, fetch_orders, join),
        (START, fetch_billing, join),
        
        # 2. Join -> Classify & Route
        (join, classify_and_route),
        
        # 3. Conditional branches
        (classify_and_route, {
            "tech": dynamic_troubleshoot,
            "billing": billing_agent,
            "shipping": shipping_agent,
            "general": general_agent,
        }),
        
        # 4. Billing flows into HITL Gate
        (billing_agent, check_refund_hitl),
        (check_refund_hitl, {
            "approved": process_approved,
        }),
    ],
)

# ===== Section 7: Demonstration of Multiple Paths =====
async def run_scenario(runner, label, user_text, session_id, initial_state=None, is_resume=False, resume_state=None):
    print(f"\n{'='*60}")
    print(f"=== {label} ===")
    print(f"Customer Input: \"{user_text}\"")
    print(f"{'='*60}")
    
    start_time = time.time()
    user_msg = types.Content(role="user", parts=[types.Part(text=user_text)])
    
    state_delta = initial_state or {}
    state_delta["user_message"] = user_text
    if is_resume and resume_state:
        state_delta.update(resume_state)

    async for event in runner.run_async(
        user_id="alice", session_id=session_id, new_message=user_msg, state_delta=state_delta
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    print(f"[{event.author}]: {part.text}")
        if event.output is not None and not isinstance(event.output, dict):
            print(f"[{event.author}] output: {event.output}")

    elapsed = time.time() - start_time
    print(f"Execution time: {elapsed:.2f}s")

async def main():
    runner = Runner(
        node=workflow,
        app_name="complete_support_app",
        session_service=InMemorySessionService(),
        auto_create_session=True,
    )
    
    # Path 1: Tech Ticket -> Parallel Fetch -> Classify -> Dynamic Troubleshoot Loop
    await run_scenario(
        runner,
        label="SCENARIO 1: Tech Support (Dynamic Troubleshoot Loop)",
        user_text="The application crashes every time I upload photos.",
        session_id="session_tech_1",
    )

    # Path 2a: Billing Ticket -> Parallel Fetch -> Classify -> Billing Agent -> HITL Pause
    await run_scenario(
        runner,
        label="SCENARIO 2a: Billing Ticket (HITL Pause for Approval)",
        user_text="I was charged twice and need a refund of $150.",
        session_id="session_billing_1",
        initial_state={"refund_amount": 150},
    )

    # Path 2b: Manager Approves -> Workflow Resumes & Completes
    await run_scenario(
        runner,
        label="SCENARIO 2b: Manager Approves Refund (HITL Resume)",
        user_text="Approved by Manager",
        session_id="session_billing_1",
        is_resume=True,
        resume_state={"approval_status": "approved"},
    )

    # Path 3: Shipping Ticket -> Parallel Fetch -> Classify -> Shipping Specialist
    await run_scenario(
        runner,
        label="SCENARIO 3: Shipping Inquiry",
        user_text="Where is my package for order #8492?",
        session_id="session_shipping_1",
    )

    # Allow background aiohttp connections to finish closing
    await asyncio.sleep(0.25)

if __name__ == "__main__":
    asyncio.run(main())
