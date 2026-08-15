"""03: L3 Searchable Long-Term Memory — add_session_to_memory & preload_memory_tool"""
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
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.tools.preload_memory_tool import preload_memory_tool
from google.genai import types

MODEL = os.environ.get("ADK_MODEL", "gemini-2.5-flash")

# Agent equipped with preload_memory_tool to automatically retrieve relevant past context
chef_agent = Agent(
    name="memory_chef",
    model=MODEL,
    instruction="""You are a personal chef.
    Always take into account past dietary preferences, restrictions, and conversations with the user.
    Provide delicious, tailored meal recommendations.""",
    tools=[preload_memory_tool],
)

async def main():
    session_service = InMemorySessionService()
    memory_service = InMemoryMemoryService()

    runner = Runner(
        agent=chef_agent,
        app_name="memory_chef_app",
        session_service=session_service,
        memory_service=memory_service,
    )

    # =========================================================================
    # CONVERSATION 1: Monday — User shares detailed preferences and past history
    # =========================================================================
    print("=== MONDAY (Session 1): User shares dietary preferences ===")
    s1 = await session_service.create_session(app_name="memory_chef_app", user_id="u_sophia")
    msg1 = "Hi! I am allergic to peanuts and pine nuts, and my absolute favorite cuisine is authentic Italian pasta."
    print(f"Customer: {msg1}\n")

    content1 = types.Content(role="user", parts=[types.Part(text=msg1)])
    async for event in runner.run_async(
        user_id="u_sophia", session_id=s1.id, new_message=content1
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    print(f"[{event.author}]: {part.text}")

    # =========================================================================
    # INGESTION: Session 1 ends -> We index the entire session into Memory
    # =========================================================================
    print("\n" + "-"*60)
    print("INGESTING Session 1 into Long-Term Memory (add_session_to_memory)...")
    s1_full = await session_service.get_session(app_name="memory_chef_app", user_id="u_sophia", session_id=s1.id)
    await memory_service.add_session_to_memory(s1_full)
    print("Session 1 successfully indexed in vector/semantic memory store.")
    print("-"*60)

    # =========================================================================
    # CONVERSATION 2: Wednesday — User returns in a completely new session
    # =========================================================================
    print("\n=== WEDNESDAY (Session 2): User returns in a brand new session ===")
    s2 = await session_service.create_session(app_name="memory_chef_app", user_id="u_sophia")
    msg2 = "What should I cook for dinner tonight? Any quick pasta ideas?"
    print(f"Customer: {msg2}\n")

    content2 = types.Content(role="user", parts=[types.Part(text=msg2)])
    async for event in runner.run_async(
        user_id="u_sophia", session_id=s2.id, new_message=content2
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    print(f"[{event.author}]: {part.text}")

if __name__ == "__main__":
    asyncio.run(main())
