"""05: Transfer Modes — chat, task, single_turn"""
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

# single_turn mode: runs once, returns result to coordinator, no user interaction
lookup_agent = LlmAgent(
    name="account_lookup",
    model=MODEL,
    description="Looks up account information. Use when the user asks about their account status or details.",
    instruction="Simulate looking up the user's account. Return: 'Account #42: Active, Gold tier, member since 2022.' Do not ask any questions.",
    mode="single_turn",
)

# task mode: can ask clarifying questions, auto-returns when done
booking_agent = LlmAgent(
    name="appointment_booker",
    model=MODEL,
    description="Books support appointments. Use when the user wants to schedule a callback or meeting.",
    instruction="""You book support appointments. Ask what day and time works best.
    Once you have the info, confirm the booking and call your finish_task tool.""",
    mode="task",
)

# chat mode (default): full conversation, must manually transfer back
advisor_agent = LlmAgent(
    name="product_advisor",
    model=MODEL,
    description="Provides detailed product advice and recommendations. Use for product questions.",
    instruction="""You are a product advisor. Have a detailed conversation about the user's needs.
    When the conversation is complete, transfer back to the coordinator.""",
    mode="chat",
)

# Coordinator
coordinator = LlmAgent(
    name="coordinator",
    model=MODEL,
    instruction="""You are the support coordinator. Based on the user's request:
    - For account inquiries → transfer to account_lookup
    - For scheduling → transfer to appointment_booker  
    - For product advice → transfer to product_advisor
    
    Always delegate. Do NOT answer directly.""",
    sub_agents=[lookup_agent, booking_agent, advisor_agent],
)

async def main():
    runner = Runner(
        agent=coordinator,
        app_name="transfer_modes",
        session_service=InMemorySessionService(),
    )

    # Test 1: single_turn — should get instant lookup, no user interaction
    print("=== TEST 1: single_turn mode (account lookup) ===")
    session = await runner.session_service.create_session(
        app_name="transfer_modes", user_id="user_1"
    )
    content = types.Content(role="user", parts=[types.Part(text="What's my account status?")])
    async for event in runner.run_async(
        user_id="user_1", session_id=session.id, new_message=content,
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    print(f"[{event.author}]: {part.text}")

    # Test 2: task mode — should ask a question then auto-return
    print("\n=== TEST 2: task mode (appointment booking) ===")
    session2 = await runner.session_service.create_session(
        app_name="transfer_modes", user_id="user_1"
    )
    content2 = types.Content(role="user", parts=[types.Part(text="I need to schedule a support callback")])
    async for event in runner.run_async(
        user_id="user_1", session_id=session2.id, new_message=content2,
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    print(f"[{event.author}]: {part.text}")

    await asyncio.sleep(0.25)

if __name__ == "__main__":
    asyncio.run(main())
