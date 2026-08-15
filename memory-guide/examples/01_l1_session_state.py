"""01: L1 In-Session Scratchpad — Using ctx.session.state for conversation variables"""
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

# Specialized agents sharing state via session.state
preference_collector = Agent(
    name="preference_collector",
    model=MODEL,
    instruction="""You are a dietary intake specialist.
    Extract the customer's allergy and favorite cuisine.
    Format as: ALLERGY: <allergy> | CUISINE: <cuisine>""",
    output_key="dietary_profile",
)

meal_planner = Agent(
    name="meal_planner",
    model=MODEL,
    instruction="""You are a personalized meal planner.
    Use the dietary profile in the conversation context to suggest 2 tailored dinner recipes.
    Ensure strict avoidance of allergies.""",
)

async def main():
    runner = Runner(
        agent=preference_collector,
        app_name="scratchpad_app",
        session_service=InMemorySessionService(),
    )

    session = await runner.session_service.create_session(
        app_name="scratchpad_app", user_id="user_chef"
    )

    print("=== TURN 1: Storing state into session.state via output_key ===")
    msg1 = "I am strictly allergic to shellfish and love Japanese cuisine."
    print(f"Customer: {msg1}")
    
    content1 = types.Content(role="user", parts=[types.Part(text=msg1)])
    async for event in runner.run_async(
        user_id="user_chef", session_id=session.id, new_message=content1
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    print(f"[{event.author}]: {part.text}")

    # Inspect the session state whiteboard directly
    session_obj = await runner.session_service.get_session(
        app_name="scratchpad_app", user_id="user_chef", session_id=session.id
    )
    print("\n[Direct State Inspection]:")
    print(f"session.state['dietary_profile'] = {session_obj.state.get('dietary_profile')}")

    print("\n" + "="*60)
    print("=== TURN 2: Downstream Agent reads from accumulated session context ===")
    print("="*60)
    # Switch runner to meal planner within the SAME session
    planner_runner = Runner(
        agent=meal_planner,
        app_name="scratchpad_app",
        session_service=runner.session_service,
    )
    msg2 = "Give me 2 quick dinner ideas for tonight."
    print(f"Customer: {msg2}")
    
    content2 = types.Content(role="user", parts=[types.Part(text=msg2)])
    async for event in planner_runner.run_async(
        user_id="user_chef", session_id=session.id, new_message=content2
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    print(f"[{event.author}]: {part.text}")

if __name__ == "__main__":
    asyncio.run(main())
