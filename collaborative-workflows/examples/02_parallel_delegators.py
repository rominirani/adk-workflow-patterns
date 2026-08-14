"""02: Parallel Delegators — Analyze ticket from 3 angles simultaneously"""
import asyncio
import os
import time
import warnings
import logging

warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=ResourceWarning)
logging.getLogger("google.genai").setLevel(logging.ERROR)
logging.getLogger("aiohttp").setLevel(logging.ERROR)

from google.adk.agents import ParallelAgent, LlmAgent
from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

MODEL = os.environ.get("ADK_MODEL", "gemini-2.5-flash")

sentiment_agent = LlmAgent(
    name="sentiment_analyzer",
    model=MODEL,
    instruction="Analyze the sentiment of the user's message. Reply with ONLY one word: Positive, Neutral, or Negative.",
    output_key="sentiment",
)

history_agent = LlmAgent(
    name="history_lookup",
    model=MODEL,
    instruction="Simulate looking up customer history. Reply with ONE sentence of simulated history, e.g. 'Customer has 3 previous tickets, last one resolved 2 weeks ago.'",
    output_key="history",
)

policy_agent = LlmAgent(
    name="policy_checker",
    model=MODEL,
    instruction="Identify if the message relates to returns, billing, or technical support. State the relevant standard policy in ONE sentence.",
    output_key="policy",
)

parallel_analyzer = ParallelAgent(
    name="parallel_context_gatherer",
    sub_agents=[sentiment_agent, history_agent, policy_agent],
)

async def main():
    runner = Runner(
        agent=parallel_analyzer,
        app_name="support_parallel",
        session_service=InMemorySessionService(),
    )
    session = await runner.session_service.create_session(
        app_name="support_parallel", user_id="user_1"
    )

    ticket = "I am so frustrated. I ordered a laptop two weeks ago and it arrived completely smashed. I want a refund right now!"

    print(f"TICKET: {ticket}\n")
    print('='*60)

    start_time = time.time()
    content = types.Content(role="user", parts=[types.Part(text=ticket)])
    async for event in runner.run_async(
        user_id="user_1",
        session_id=session.id,
        new_message=content,
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    print(f"[{event.author}]: {part.text}")

    elapsed = time.time() - start_time
    print(f"\nTotal time: {elapsed:.2f}s (3 agents ran in parallel)")

    await asyncio.sleep(0.25)

if __name__ == "__main__":
    asyncio.run(main())
