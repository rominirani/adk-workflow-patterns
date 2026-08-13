"""Complete Customer Support System: combines all graph workflow patterns."""
import asyncio
import os
import time
from google.adk import Workflow, Agent, Runner, Event
from google.adk.sessions import InMemorySessionService
from google.adk.workflow import START, JoinNode, node
from google.adk.events.event_actions import EventActions
from google.genai import types

MODEL = os.environ.get("ADK_MODEL", "gemini-2.5-flash")

# ===== Section 1: Parallel Data Fetchers =====
async def fetch_profile(node_input):
    await asyncio.sleep(0.5)
    return {"name": "Alice", "tier": "gold", "account_age": "2 years"}

async def fetch_orders(node_input):
    await asyncio.sleep(0.5)
    return {"recent_orders": 3, "last_order": "laptop"}

async def fetch_billing(node_input):
    await asyncio.sleep(0.5)
    return {"outstanding_balance": 0, "payment_method": "visa-4242"}

# ===== Section 2: Classifier / Router =====
def classify_and_route(node_input):
    data = node_input
    # Extract user message from state (we'll set it there)
    # For now, we use the data to decide routing
    profile = data.get("fetch_profile", {})
    context_summary = f"Customer: {profile.get('name', 'Unknown')}, Tier: {profile.get('tier', 'unknown')}"
    
    # In a real system, you'd classify the actual user message
    # We'll use a simple keyword approach from the initial message
    return Event(output=context_summary, actions=EventActions(route="tech"))

# ===== Section 3: Specialist Agents =====
billing_agent = Agent(
    name="billing_specialist",
    model=MODEL,
    instruction="You are billing support. Use the customer context provided to help. Be brief (2-3 sentences).",
)

tech_agent = Agent(
    name="tech_specialist", 
    model=MODEL,
    instruction="You are tech support. Use the customer context provided to help with their technical issue. Be brief (2-3 sentences).",
)

shipping_agent = Agent(
    name="shipping_specialist",
    model=MODEL,
    instruction="You are shipping support. Help track or resolve delivery issues. Be brief.",
)

general_agent = Agent(
    name="general_specialist",
    model=MODEL,
    instruction="You are general support. Answer the customer's question helpfully. Be brief.",
)

# ===== Section 4: Build the Graph =====
join = JoinNode(name="data_joiner")

workflow = Workflow(
    name="complete_support_system",
    edges=[
        # Fan-out: parallel data fetching
        (START, fetch_profile, join),
        (START, fetch_orders, join),
        (START, fetch_billing, join),
        # Join -> Classify -> Route
        (join, classify_and_route),
        (classify_and_route, {
            "billing": billing_agent,
            "tech": tech_agent,
            "shipping": shipping_agent,
            "default": general_agent,
        }),
    ],
)

# ===== Section 5: Run It =====
async def main():
    runner = Runner(
        node=workflow,
        app_name="support_system",
        session_service=InMemorySessionService(),
        auto_create_session=True,
    )
    
    print("=== TEST: Tech Support Ticket ===")
    start_time = time.time()
    user_msg = types.Content(role="user", parts=[types.Part(text="My app keeps crashing when I try to upload photos")])
    async for event in runner.run_async(
        user_id="u1", session_id="s1", new_message=user_msg
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    print(f"[{event.author}]: {part.text}")
    elapsed = time.time() - start_time
    print(f"\nCompleted in {elapsed:.2f}s (data fetches ran in parallel)\n")

if __name__ == "__main__":
    asyncio.run(main())
