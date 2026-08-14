"""06: Custom Dynamic Workflow — BaseAgent with conditional logic"""
import asyncio
import os
import warnings
import logging

warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=ResourceWarning)
logging.getLogger("google.genai").setLevel(logging.ERROR)
logging.getLogger("aiohttp").setLevel(logging.ERROR)

from google.adk.agents import BaseAgent, LlmAgent, SequentialAgent, ParallelAgent
from google.adk.agents.context import Context
from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

MODEL = os.environ.get("ADK_MODEL", "gemini-2.5-flash")

# Sub-agents for different paths
triage_agent = LlmAgent(
    name="triage",
    model=MODEL,
    instruction="""Classify this ticket priority. Reply with ONLY one of: P1, P2, P3, or P4.
    P1 = system down/outage. P2 = major feature broken. P3 = normal issue. P4 = question.""",
    output_key="triage_priority",
)

# For P1/P2: parallel enrichment
sentiment_agent = LlmAgent(
    name="sentiment",
    model=MODEL,
    instruction="Analyze the sentiment. Reply with ONE word: Positive, Neutral, or Negative.",
    output_key="sentiment_result",
)

urgency_agent = LlmAgent(
    name="urgency",
    model=MODEL,
    instruction="Assess urgency. Reply with ONE word: Critical, High, Medium, or Low.",
    output_key="urgency_result",
)

# For P3/P4: simple response
simple_response = LlmAgent(
    name="simple_responder",
    model=MODEL,
    instruction="Give a brief, helpful response to the customer's question in under 50 words. Sign off as 'Support Team'.",
)

# For P1/P2: detailed response after enrichment
detailed_response = LlmAgent(
    name="detailed_responder",
    model=MODEL,
    instruction="Using the sentiment and urgency context in the conversation, draft an urgent response. Express urgency and provide an ETA. Under 80 words. Sign off as 'Support Team'.",
)

class SmartTriageAgent(BaseAgent):
    """Custom workflow that conditionally branches based on triage result."""

    model: str = MODEL

    async def _run_async_impl(self, ctx: Context):
        # Step 1: Run triage
        async for event in triage_agent.run_async(ctx):
            yield event

        # Read triage result from state (via ctx.session.state)
        priority = ctx.session.state.get("triage_priority", "P3").strip().upper()
        print(f"\n[SmartTriage] Priority detected: {priority}")

        if priority in ("P1", "P2"):
            # Step 2a: High priority → parallel enrichment then detailed response
            print("[SmartTriage] High priority → running parallel enrichment")
            parallel = ParallelAgent(
                name="enrichment",
                sub_agents=[sentiment_agent, urgency_agent],
            )
            async for event in parallel.run_async(ctx):
                yield event
            async for event in detailed_response.run_async(ctx):
                yield event
        else:
            # Step 2b: Low priority → simple response
            print("[SmartTriage] Low priority → simple response")
            async for event in simple_response.run_async(ctx):
                yield event

smart_triage = SmartTriageAgent(name="smart_triage")

async def main():
    runner = Runner(
        agent=smart_triage,
        app_name="smart_triage",
        session_service=InMemorySessionService(),
    )

    tickets = [
        ("Our entire payment system is down!", "P1 ticket"),
        ("What are your business hours?", "P4 ticket"),
    ]

    for ticket, label in tickets:
        session = await runner.session_service.create_session(
            app_name="smart_triage", user_id="user_1"
        )
        print(f"\n{'='*60}")
        print(f"{label}: {ticket}")
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
