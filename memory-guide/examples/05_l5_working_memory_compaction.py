"""05: L5 Working-Memory Management — Compaction, Rewind, and Context Caching"""
import asyncio
import os
import warnings
import logging

warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=ResourceWarning)
logging.getLogger("google.genai").setLevel(logging.ERROR)
logging.getLogger("aiohttp").setLevel(logging.ERROR)

from google.adk.agents import Agent
from google.adk.agents.context_cache_config import ContextCacheConfig
from google.adk.apps.compaction import EventsCompactionConfig
from google.adk.events import Event
from google.adk.events.event_actions import EventActions
from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

MODEL = os.environ.get("ADK_MODEL", "gemini-2.5-flash")

# Master Chef agent handling multi-turn working memory
master_chef = Agent(
    name="master_chef",
    model=MODEL,
    instruction="""You are a world-renowned master chef with exhaustive knowledge of culinary techniques,
    flavor pairings, international food chemistry, temperature safety tables, and wine terroirs.
    Provide concise, authoritative advice.""",
)

from google.adk.apps import App

async def main():
    session_service = InMemorySessionService()

    # 2. Compaction Config: Automatically compacts conversation events when token thresholds are reached
    compaction_config = EventsCompactionConfig(
        compaction_interval=5, # Compact every 5 events
        overlap_size=1,        # Keep 1 recent event for immediate context
    )

    app = App(
        name="compaction_app",
        root_agent=master_chef,
        events_compaction_config=compaction_config,
    )

    runner = Runner(
        app=app,
        session_service=session_service,
    )

    session = await session_service.create_session(app_name="compaction_app", user_id="u_kitchen")

    print("=== 1. Simulating a Multi-Turn Chat (Working-Memory Accumulation) ===")
    turns = [
        "What is the ideal sous-vide temperature for medium-rare duck breast?",
        "How long should I sear the skin afterwards?",
        "What sauce would you pair with this?",
    ]

    for i, turn in enumerate(turns):
        print(f"\n[Turn {i+1}]: {turn}")
        content = types.Content(role="user", parts=[types.Part(text=turn)])
        async for event in runner.run_async(
            user_id="u_kitchen", session_id=session.id, new_message=content
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        print(f"[{event.author}]: {part.text[:120]}...")

    # 3. Demonstration of Memory Rewind: Rolling back an accidental or hallucinated turn
    print("\n" + "="*65)
    print("=== 2. Conversation Rewind — Pruning bad turns from working memory ===")
    print("="*65)
    
    current_session = await session_service.get_session(
        app_name="compaction_app", user_id="u_kitchen", session_id=session.id
    )
    print(f"Total events currently recorded in session: {len(current_session.events)}")
    
    # We can emit an event with rewind_before_invocation_id to roll working memory back
    if current_session.events:
        target_invocation = current_session.events[-1].invocation_id
        print(f"Rolling back working memory prior to invocation: {target_invocation}")
        rewind_event = Event(
            author="system",
            actions=EventActions(rewind_before_invocation_id=target_invocation)
        )
        await session_service.append_event(current_session, rewind_event)
        print("Rewind action appended! The working memory window has been cleanly pruned.")

if __name__ == "__main__":
    asyncio.run(main())
