"""03: Multi-Agent Collaboration — Supervisor coordinating Drafter & Critic specialists"""
import asyncio
import os
import warnings
import logging

warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=ResourceWarning)
logging.getLogger("google.genai").setLevel(logging.ERROR)
logging.getLogger("aiohttp").setLevel(logging.ERROR)

from google.adk.agents import Agent
from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

MODEL = os.environ.get("ADK_MODEL", "gemini-2.5-flash")

# Specialist 1: Technical Drafter (Single Turn tool-like specialist)
tech_drafter = Agent(
    name="tech_drafter",
    model=MODEL,
    description="Drafts initial technical troubleshooting steps and resolutions for complex software issues.",
    instruction="""You are a technical troubleshooting drafter.
    Analyze the user's issue and write a concise, 3-step action plan to resolve it.
    Be precise, technical, and concise (under 60 words).""",
    mode="single_turn",
)

# Specialist 2: Quality & Safety Critic (Single Turn review specialist)
quality_critic = Agent(
    name="quality_critic",
    model=MODEL,
    description="Reviews technical drafts for safety, customer empathy, clarity, and policy compliance.",
    instruction="""You are a senior support quality reviewer.
    Review the drafted response in the conversation.
    - Ensure it is empathetic and free of risky instructions
    - Provide a polished, customer-ready version of the response
    - Keep it under 60 words and sign off as 'Expert Support Team'""",
    mode="single_turn",
)

# The Supervisor Agent orchestrating the collaboration between Drafter and Critic
editorial_supervisor = Agent(
    name="editorial_supervisor",
    model=MODEL,
    instruction="""You are the technical support lead orchestrating high-quality responses.
    For technical customer inquiries:
    1. First, delegate to `tech_drafter` to generate a technical diagnosis and resolution plan.
    2. Next, delegate the draft to `quality_critic` to polish and review it for the customer.
    3. Finally, deliver the approved, polished response to the customer.
    
    Ensure both specialists contribute before finalizing the answer.""",
    sub_agents=[tech_drafter, quality_critic],
)

async def main():
    runner = Runner(
        agent=editorial_supervisor,
        app_name="supervisor_collaboration",
        session_service=InMemorySessionService(),
    )

    tickets = [
        "My database connection pool keeps exhausting during peak traffic and throwing 500 errors on our checkout page.",
        "Users report that session cookies are being invalidated immediately after login on mobile Safari.",
    ]

    for ticket in tickets:
        session = await runner.session_service.create_session(
            app_name="supervisor_collaboration", user_id="user_1"
        )
        print(f"\n{'='*60}")
        print(f"CUSTOMER TICKET: {ticket}")
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
                        print(f"[{event.author}]:\n{part.text}\n")

    await asyncio.sleep(0.25)

if __name__ == "__main__":
    asyncio.run(main())
