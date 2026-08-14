"""04: Coordinator-Dispatcher — LLM routes to the right specialist"""
import asyncio
import os
import warnings
import logging

warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=ResourceWarning)
logging.getLogger("google.genai").setLevel(logging.ERROR)
logging.getLogger("aiohttp").setLevel(logging.ERROR)

from google.adk.agents import LlmAgent
from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

MODEL = os.environ.get("ADK_MODEL", "gemini-2.5-flash")

# Specialist agents with clear descriptions
billing_specialist = LlmAgent(
    name="billing_specialist",
    model=MODEL,
    description="Handles billing inquiries: refunds, charges, payment disputes, invoices, pricing.",
    instruction="""You are a billing support specialist. Help the customer with their billing issue.
    - Be empathetic and professional
    - If a refund is needed, explain the process (5-7 business days)
    - Always confirm the specific charge or invoice in question
    - Keep your response under 60 words""",
)

tech_specialist = LlmAgent(
    name="tech_specialist",
    model=MODEL,
    description="Handles technical issues: bugs, errors, crashes, performance problems, setup help.",
    instruction="""You are a technical support engineer. Help the customer with their technical issue.
    - Ask for error messages or screenshots if relevant
    - Provide step-by-step troubleshooting
    - Keep your response under 60 words""",
)

shipping_specialist = LlmAgent(
    name="shipping_specialist",
    model=MODEL,
    description="Handles shipping and delivery: tracking, lost packages, delivery estimates, address changes.",
    instruction="""You are a shipping support specialist. Help with delivery inquiries.
    - Provide tracking information
    - For lost packages, initiate a trace (48 hours)
    - Keep your response under 60 words""",
)

general_specialist = LlmAgent(
    name="general_specialist",
    model=MODEL,
    description="Handles general questions: account info, policies, feature requests, feedback.",
    instruction="""You are a general support agent. Handle miscellaneous customer questions.
    - Be helpful and concise
    - Keep your response under 60 words""",
)

# The Coordinator — routes based on sub_agent descriptions
coordinator = LlmAgent(
    name="support_concierge",
    model=MODEL,
    instruction="""You are the customer support concierge. Your ONLY job is to:
    1. Understand the customer's issue
    2. Route them to the most appropriate specialist using transfer_to_agent
    
    Do NOT answer the question yourself. ALWAYS delegate to a specialist.""",
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
