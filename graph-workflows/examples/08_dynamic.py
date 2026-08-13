import asyncio
import os
from google.adk import Agent, Runner
from google.adk.sessions import InMemorySessionService
from google.adk.workflow import Workflow, START, node
from google.genai import types

MODEL = os.environ.get("ADK_MODEL", "gemini-2.5-flash")

diagnose_agent = Agent(
    name="diagnose",
    model=MODEL,
    instruction="You are a tech support diagnostician. Suggest ONE specific troubleshooting step for the user's issue. Be brief (1-2 sentences).",
)

@node(rerun_on_resume=True)
async def troubleshoot_loop(ctx):
    """Dynamic node that runs the diagnose agent in a loop."""
    max_attempts = 2
    for i in range(1, max_attempts + 1):
        print(f"--- Iteration {i} ---")
        result = await ctx.run_node(diagnose_agent)
        print(f"[diagnose] result: {result}")
        # In a real system, you'd check if the issue is resolved
        if i == max_attempts:
            print(f"Max attempts reached. Escalating.")
            return f"Escalated after {max_attempts} iterations. Last suggestion: {result}"
    return "Issue resolved"

workflow = Workflow(
    name="dynamic_workflow",
    edges=[(START, troubleshoot_loop)],
)

async def main():
    runner = Runner(
        node=workflow,
        app_name="test_app",
        session_service=InMemorySessionService(),
        auto_create_session=True,
    )
    user_msg = types.Content(role="user", parts=[types.Part(text="My app keeps crashing when I upload photos")])
    async for event in runner.run_async(
        user_id="u1", session_id="s1", new_message=user_msg
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    print(f"[{event.author}]: {part.text}")
        if event.output is not None:
            print(f"[{event.author}] output: {event.output}")

if __name__ == "__main__":
    asyncio.run(main())
