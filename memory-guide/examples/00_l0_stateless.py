"""00: L0 Stateless Goldfish — Every request starts from absolute zero"""
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

# L0: A pure stateless agent. No session persistence across interactions.
chef_agent = Agent(
    name="goldfish_chef",
    model=MODEL,
    instruction="""You are a personal chef. Suggest dinner ideas based on user dietary preferences.
    If you don't know the user's preferences, ask them for details.""",
)

async def main():
    runner = Runner(
        agent=chef_agent,
        app_name="goldfish_app",
        session_service=InMemorySessionService(),
    )

    print("=== TURN 1: User introduces dietary preferences in Session A ===")
    session_a = await runner.session_service.create_session(
        app_name="goldfish_app", user_id="user_goldfish"
    )
    turn1_msg = "Hi! I am allergic to peanuts and love Italian pasta dishes."
    print(f"Customer: {turn1_msg}")
    
    content1 = types.Content(role="user", parts=[types.Part(text=turn1_msg)])
    async for event in runner.run_async(
        user_id="user_goldfish", session_id=session_a.id, new_message=content1
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    print(f"[{event.author}]: {part.text}")

    print("\n" + "="*60)
    print("=== TURN 2: User returns in a new Session B (Two days later) ===")
    print("="*60)
    # New session created — the agent has zero memory of Session A
    session_b = await runner.session_service.create_session(
        app_name="goldfish_app", user_id="user_goldfish"
    )
    turn2_msg = "What should I make for dinner tonight?"
    print(f"Customer: {turn2_msg}")

    content2 = types.Content(role="user", parts=[types.Part(text=turn2_msg)])
    async for event in runner.run_async(
        user_id="user_goldfish", session_id=session_b.id, new_message=content2
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    print(f"[{event.author}]: {part.text}")

if __name__ == "__main__":
    asyncio.run(main())
