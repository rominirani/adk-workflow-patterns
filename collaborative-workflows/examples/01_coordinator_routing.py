"""01: Coordinator-Dispatcher — LLM routes to the right specialist via Agent descriptions"""
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

# Specialist agents with clear semantic descriptions
billing_specialist = Agent(
    name="billing_specialist",
    model=MODEL,
    description="Handles billing inquiries: refunds, double charges, payment disputes, invoices, and pricing.",
    instruction="""You are a billing support specialist. Help the customer with their billing issue.
    - Be empathetic and professional
    - If a refund is needed, explain the process (5-7 business days)
    - Always confirm the specific charge or invoice in question
    - Keep your response under 60 words""",
)

tech_specialist = Agent(
    name="tech_specialist",
    model=MODEL,
    description="Handles technical issues: bugs, errors, app crashes, performance problems, and setup help.",
    instruction="""You are a technical support engineer. Help the customer with their technical issue.
    - Ask for error messages or reproduction steps if relevant
    - Provide concise step-by-step troubleshooting
    - Keep your response under 60 words""",
)

shipping_specialist = Agent(
    name="shipping_specialist",
    model=MODEL,
    description="Handles shipping and delivery: tracking, lost packages, delivery estimates, and address changes.",
    instruction="""You are a shipping support specialist. Help with delivery inquiries.
    - Provide tracking information and delivery estimates
    - For lost packages, initiate a trace (48 hours)
    - Keep your response under 60 words""",
)

general_specialist = Agent(
    name="general_specialist",
    model=MODEL,
    description="Handles general questions: company info, store policies, feature requests, and feedback.",
    instruction="""You are a general support agent. Handle miscellaneous customer questions.
    - Be helpful and concise
    - Keep your response under 60 words""",
)

# The Coordinator — routes based on sub_agents descriptions without hardcoded graph edges
coordinator = Agent(
    name="support_concierge",
    model=MODEL,
    instruction="""You are the customer support concierge. Your job is to:
    1. Understand the customer's issue
    2. Route them to the most appropriate specialist based on their domain
    
    Do NOT attempt to resolve billing, technical, shipping, or general issues yourself.
    ALWAYS delegate to the corresponding specialist.""",
    sub_agents=[billing_specialist, tech_specialist, shipping_specialist, general_specialist],
)

async def main():
    runner = Runner(
        agent=coordinator,
        app_name="support_coordinator",
        session_service=InMemorySessionService(),
    )

    queries = [
        "I was charged twice for order #12345",
        "The app crashes every time I try to upload a photo",
        "Where is my package? It's been 2 weeks!",
        "What's your refund policy?",
    ]

    for query in queries:
        session = await runner.session_service.create_session(
            app_name="support_coordinator", user_id="user_1"
        )
        print(f"\n{'='*60}")
        print(f"CUSTOMER: {query}")
        print('='*60)

        content = types.Content(role="user", parts=[types.Part(text=query)])
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
