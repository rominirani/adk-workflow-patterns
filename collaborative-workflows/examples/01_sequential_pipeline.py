"""01: Sequential Pipeline — Triage → Enrich → Respond"""
import asyncio
import os
import warnings
import logging

warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=ResourceWarning)
logging.getLogger("google.genai").setLevel(logging.ERROR)
logging.getLogger("aiohttp").setLevel(logging.ERROR)

from google.adk.agents import SequentialAgent, LlmAgent
from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

MODEL = os.environ.get("ADK_MODEL", "gemini-2.5-flash")

# Stage 1: Triage
triage_agent = LlmAgent(
    name="triage",
    model=MODEL,
    instruction="""You are a support ticket triage specialist. Analyze the ticket and output:
    Priority: P1 (critical), P2 (high), P3 (normal), or P4 (low)
    Category: billing, technical, shipping, or general
    Summary: one sentence
    Format exactly as shown above, one per line.""",
    output_key="triage_result",
)

# Stage 2: Enrichment
enrichment_agent = LlmAgent(
    name="enrichment",
    model=MODEL,
    instruction="""You are a customer data enrichment agent. Based on the triage in the conversation,
    add simulated customer data:
    - Customer tier: Gold/Silver/Bronze (Gold for P1/P2, Silver for P3, Bronze for P4)
    - Account age: simulate realistic value
    - Previous tickets: simulate 0-5
    Output the triage data PLUS enrichment data.""",
    output_key="enrichment_result",
)

# Stage 3: Response Drafter
response_agent = LlmAgent(
    name="response_drafter",
    model=MODEL,
    instruction="""You are a customer support response writer. Using all context in the conversation,
    draft a professional, empathetic response to the customer.
    - For Gold customers, be extra attentive
    - For P1/P2, express urgency and provide an ETA
    - Keep it under 100 words
    - Sign off as 'Support Team'""",
)

# Build the pipeline
pipeline = SequentialAgent(
    name="support_pipeline",
    sub_agents=[triage_agent, enrichment_agent, response_agent],
)

async def main():
    runner = Runner(
        agent=pipeline,
        app_name="support_pipeline",
        session_service=InMemorySessionService(),
    )

    tickets = [
        "Our entire checkout system is down! No customers can complete purchases.",
        "Hi, what's your return policy for electronics?",
    ]

    for ticket in tickets:
        print(f"\n{'='*60}")
        print(f"TICKET: {ticket[:60]}...")
        print('='*60)

        # Create a new session per ticket to avoid cross-contamination
        session = await runner.session_service.create_session(
            app_name="support_pipeline", user_id="user_1"
        )

        content = types.Content(role="user", parts=[types.Part(text=ticket)])
        async for event in runner.run_async(
            user_id="user_1",
            session_id=session.id,
            new_message=content,
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        print(f"\n[{event.author}]:\n{part.text}")

    await asyncio.sleep(0.25)

if __name__ == "__main__":
    asyncio.run(main())
