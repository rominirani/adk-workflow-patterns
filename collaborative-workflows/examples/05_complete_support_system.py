"""05: Complete Collaborative Support System — Bringing all multi-agent patterns together"""
import asyncio
import os
import warnings
import logging
from pydantic import BaseModel, Field

warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=ResourceWarning)
logging.getLogger("google.genai").setLevel(logging.ERROR)
logging.getLogger("aiohttp").setLevel(logging.ERROR)

from google.adk.agents import Agent
from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

MODEL = os.environ.get("ADK_MODEL", "gemini-2.5-flash")

# --- Schema for Structured Task Mode ---
class CallbackRequest(BaseModel):
    contact_phone: str = Field(description="Customer phone number")
    preferred_time: str = Field(description="Preferred callback window e.g. 2pm Tomorrow")
    issue_topic: str = Field(description="Topic of callback")

# --- 1. Billing Specialist (Chat Mode) ---
billing_specialist = Agent(
    name="billing_specialist",
    model=MODEL,
    description="Handles billing inquiries: refunds, incorrect charges, subscription upgrades, and invoices.",
    instruction="""You are a billing support expert.
    - Be empathetic, courteous, and professional
    - Explain refund timelines (5-7 business days)
    - Keep responses under 50 words and sign off as 'Billing Specialist'""",
    mode="chat",
)

# --- 2. Shipping Lookup Specialist (Single-Turn Mode) ---
shipping_lookup = Agent(
    name="shipping_lookup",
    model=MODEL,
    description="Performs quick shipping tracking status lookups for order numbers and lost package inquiries.",
    instruction="""Simulate looking up tracking for the requested order.
    Return: 'Order #789: In Transit with FedEx. Estimated Delivery: Tomorrow by 4:00 PM.'
    Keep response under 40 words and do not ask follow-up questions.""",
    mode="single_turn",
)

# --- 3. Technical Troubleshooter Specialist (Chat Mode) ---
tech_specialist = Agent(
    name="tech_specialist",
    model=MODEL,
    description="Diagnoses and troubleshoots technical errors, crashes, API failures, and bugs.",
    instruction="""You are a senior technical support engineer.
    Provide immediate, actionable debugging steps for technical errors.
    Keep response under 50 words and sign off as 'Tech Engineering'.""",
    mode="chat",
)

# --- 4. Appointment & Callback Scheduler (Task Mode) ---
callback_scheduler = Agent(
    name="callback_scheduler",
    model=MODEL,
    description="Schedules technical support phone callbacks. Use when the user requests a phone call or callback.",
    instruction="""You are the callback booking agent.
    Collect both:
    1. Customer phone number
    2. Preferred callback date/time
    Once you have both, confirm the appointment and call your finish_task tool.""",
    mode="task",
    output_schema=CallbackRequest,
)

# --- Central Concierge Coordinator ---
coordinator = Agent(
    name="support_concierge",
    model=MODEL,
    instruction="""You are the customer support concierge for an enterprise platform.
    Your role is to understand the customer's request and delegate to the right specialist:
    - Transfer billing & charge questions to `billing_specialist`
    - Transfer package and shipping status inquiries to `shipping_lookup`
    - Transfer crashes, bugs, and API errors to `tech_specialist`
    - Transfer callback and phone appointment requests to `callback_scheduler`
    
    Always delegate. When a specialist completes their work, provide a warm summary to the customer.""",
    sub_agents=[billing_specialist, shipping_lookup, tech_specialist, callback_scheduler],
)

async def main():
    runner = Runner(
        agent=coordinator,
        app_name="complete_support_system",
        session_service=InMemorySessionService(),
    )

    test_scenarios = [
        ("Billing Inquiry", "I noticed a double charge on my subscription for last month."),
        ("Shipping Lookup", "Where is my package? Order number is #789."),
        ("Technical Support", "Our mobile app crashes whenever we click the export CSV button."),
    ]

    for label, query in test_scenarios:
        session = await runner.session_service.create_session(
            app_name="complete_support_system", user_id="user_enterprise"
        )
        print(f"\n{'='*65}")
        print(f"[{label}] CUSTOMER: {query}")
        print('='*65)

        content = types.Content(role="user", parts=[types.Part(text=query)])
        async for event in runner.run_async(
            user_id="user_enterprise",
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
