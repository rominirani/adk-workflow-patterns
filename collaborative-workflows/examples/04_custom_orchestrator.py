"""04: Custom Multi-Agent Orchestrator — BaseAgent with programmatic control & session state"""
import asyncio
import os
import warnings
import logging

warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=ResourceWarning)
logging.getLogger("google.genai").setLevel(logging.ERROR)
logging.getLogger("aiohttp").setLevel(logging.ERROR)

from google.adk.agents import BaseAgent, Agent
from google.adk.agents.context import Context
from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

MODEL = os.environ.get("ADK_MODEL", "gemini-2.5-flash")

# Specialized agents
triage_agent = Agent(
    name="triage_agent",
    model=MODEL,
    instruction="""Classify the ticket priority. Reply with ONLY one of: P1, P2, P3, or P4.
    P1 = entire system down or data breach.
    P2 = major broken feature affecting revenue.
    P3 = general software bug.
    P4 = question or account help.""",
    output_key="triage_priority",
)

enrichment_agent = Agent(
    name="enrichment_agent",
    model=MODEL,
    instruction="""Simulate fetching VIP account status. Output:
    'Customer Tier: Platinum Enterprise | SLA: 15-minute response | Account Value: $250k/yr'""",
    output_key="customer_enrichment",
    mode="single_turn",
)

urgent_responder = Agent(
    name="urgent_responder",
    model=MODEL,
    instruction="""You are an executive incident responder. Draft an urgent, high-priority SLA response.
    Acknowledge the enterprise tier and commit to an immediate war room ETA within 15 minutes.
    Keep it under 60 words. Sign off as 'Executive Escalation Team'.""",
)

standard_responder = Agent(
    name="standard_responder",
    model=MODEL,
    instruction="""You are a helpful customer support representative.
    Provide a friendly, helpful answer to the customer's question in under 50 words.
    Sign off as 'Customer Support Team'.""",
)

class SmartCustomOrchestrator(BaseAgent):
    """Custom BaseAgent that inspects session state and coordinates multi-agent flow."""

    model: str = MODEL

    async def _run_async_impl(self, ctx: Context):
        # Step 1: Run triage agent and stream events
        async for event in triage_agent.run_async(ctx):
            yield event

        # Step 2: Read state from session (ctx.session.state)
        raw_priority = ctx.session.state.get("triage_priority", "P3")
        priority = raw_priority.strip().upper() if isinstance(raw_priority, str) else "P3"
        print(f"\n[CustomOrchestrator] Evaluated Priority in state: {priority}")

        # Step 3: Programmatic dynamic routing & multi-agent execution
        if any(p in priority for p in ("P1", "P2")):
            print("[CustomOrchestrator] Escalating: Executing VIP Enrichment + Urgent Responder")
            # Run enrichment agent to populate VIP customer context
            async for event in enrichment_agent.run_async(ctx):
                yield event
            # Run urgent escalation response
            async for event in urgent_responder.run_async(ctx):
                yield event
        else:
            print("[CustomOrchestrator] Standard Flow: Executing Standard Responder")
            async for event in standard_responder.run_async(ctx):
                yield event

smart_orchestrator = SmartCustomOrchestrator(name="smart_orchestrator")

async def main():
    runner = Runner(
        agent=smart_orchestrator,
        app_name="custom_orchestrator",
        session_service=InMemorySessionService(),
    )

    tickets = [
        ("Our production database is unreachable and all API requests are failing 100%!", "P1 Critical Ticket"),
        ("Where can I find the invoice history for last quarter?", "P4 Standard Ticket"),
    ]

    for ticket, label in tickets:
        session = await runner.session_service.create_session(
            app_name="custom_orchestrator", user_id="user_1"
        )
        print(f"\n{'='*60}")
        print(f"[{label}] {ticket}")
        print('='*60)

        content = types.Content(role="user", parts=[types.Part(text=ticket)])
        async for event in runner.run_async(
            user_id="user_1",
            session_id=session.id,
            new_message=content,
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        print(f"[{event.author}]: {part.text}")

    await asyncio.sleep(0.25)

if __name__ == "__main__":
    asyncio.run(main())
