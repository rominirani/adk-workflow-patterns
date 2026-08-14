"""05: Transfer Modes — chat, task, single_turn"""
import asyncio
import os
import warnings
import logging
from pydantic import BaseModel, Field

warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=ResourceWarning)
logging.getLogger("google.genai").setLevel(logging.ERROR)
logging.getLogger("aiohttp").setLevel(logging.ERROR)

from google.adk.agents import LlmAgent
from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

MODEL = os.environ.get("ADK_MODEL", "gemini-2.5-flash")

class BookingConfirmation(BaseModel):
    date_time: str = Field(description="The agreed date and time")
    contact_number: str = Field(description="Customer contact phone number")
    status: str = Field(default="confirmed", description="Booking status")

# 1. single_turn mode: runs once as a tool-like agent, returns result to coordinator with no user interaction
lookup_agent = LlmAgent(
    name="account_lookup",
    model=MODEL,
    description="Looks up account information. Use when the user asks about their account status or details.",
    instruction="Simulate looking up the user's account. Return: 'Account #42: Active, Gold tier, member since 2022.' Do not ask any questions.",
    mode="single_turn",
)

# 2. task mode: can ask clarifying questions across turns, auto-returns to coordinator once finish_task is called
booking_agent = LlmAgent(
    name="appointment_booker",
    model=MODEL,
    description="Books support callback appointments. Use when the user wants to schedule a callback.",
    instruction="""You are an appointment booking specialist.
    To book a callback, you MUST obtain both:
    1. Preferred date and time
    2. Phone number
    
    If either is missing, ask the user a polite clarifying question.
    Once you have BOTH pieces of information, confirm the appointment details and call your finish_task tool.""",
    mode="task",
    output_schema=BookingConfirmation,
)

# 3. chat mode (default): full conversational copilot
advisor_agent = LlmAgent(
    name="product_advisor",
    model=MODEL,
    description="Provides detailed product advice and recommendations. Use for product questions.",
    instruction="""You are a product advisor. Have a detailed conversation about the user's needs.
    When the conversation is complete, transfer back to the coordinator.""",
    mode="chat",
)

# The Coordinator
coordinator = LlmAgent(
    name="coordinator",
    model=MODEL,
    instruction="""You are the support coordinator. Based on the user's request:
    - For account inquiries → transfer to account_lookup
    - For scheduling → transfer to appointment_booker
    - For product advice → transfer to product_advisor
    
    Always delegate. When a specialist finishes a task, summarize the confirmation to the customer.""",
    sub_agents=[lookup_agent, booking_agent, advisor_agent],
)

async def main():
    runner = Runner(
        agent=coordinator,
        app_name="transfer_modes",
        session_service=InMemorySessionService(),
    )

    # -------------------------------------------------------------
    # TEST 1: single_turn mode (Account Lookup)
    # The coordinator delegates to account_lookup, which runs once
    # and immediately auto-returns its result to the coordinator.
    # -------------------------------------------------------------
    print("=== TEST 1: single_turn mode (Account Lookup) ===")
    print("User: 'What is my account status?'\n")
    session1 = await runner.session_service.create_session(
        app_name="transfer_modes", user_id="user_1"
    )
    content1 = types.Content(role="user", parts=[types.Part(text="What is my account status?")])
    async for event in runner.run_async(
        user_id="user_1", session_id=session1.id, new_message=content1,
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    print(f"[{event.author}]: {part.text}")

    # -------------------------------------------------------------
    # TEST 2: task mode (Multi-Turn Callback Booking)
    # Turn 1: User asks to book without details -> booker asks for time & phone
    # Turn 2: User supplies info -> booker calls finish_task -> control returns to coordinator
    # -------------------------------------------------------------
    print("\n" + "="*60)
    print("=== TEST 2: task mode (Multi-Turn Callback Booking) ===")
    print("="*60)

    session2 = await runner.session_service.create_session(
        app_name="transfer_modes", user_id="user_2"
    )

    # Turn 1: User initiates booking
    turn1_msg = "I need to schedule a technical support callback."
    print(f"\n[User -> Turn 1]: {turn1_msg}")
    content_t1 = types.Content(role="user", parts=[types.Part(text=turn1_msg)])
    async for event in runner.run_async(
        user_id="user_2", session_id=session2.id, new_message=content_t1,
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    print(f"[{event.author}]: {part.text}")

    # Turn 2: User provides requested phone and datetime in the same session
    turn2_msg = "Tomorrow at 2:00 PM EST. You can reach me at 555-0199."
    print(f"\n[User -> Turn 2]: {turn2_msg}")
    content_t2 = types.Content(role="user", parts=[types.Part(text=turn2_msg)])
    async for event in runner.run_async(
        user_id="user_2", session_id=session2.id, new_message=content_t2,
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    print(f"[{event.author}]: {part.text}")

    await asyncio.sleep(0.25)

if __name__ == "__main__":
    asyncio.run(main())
