import asyncio
import os
from google.adk import Workflow, Agent, Runner
from google.adk.sessions import InMemorySessionService
from google.adk.workflow import START
from google.genai import types

MODEL = os.environ.get("ADK_MODEL", "gemini-2.5-flash")

def extract_data(node_input):
    """Extract text from the upstream output (user message content)."""
    if isinstance(node_input, types.Content):
        return {"original": node_input.parts[0].text, "category": "inquiry"}
    return {"original": str(node_input), "category": "inquiry"}

def format_prompt(node_input):
    """Format the extracted data into a prompt string."""
    if isinstance(node_input, dict):
        return f"Please summarize this inquiry in one sentence: {node_input['original']}"
    return f"Please summarize this inquiry in one sentence: {node_input}"

summarize_agent = Agent(
    name="summarize_agent",
    model=MODEL,
    instruction="You are a helpful summarizer. Provide a one-sentence summary.",
)

workflow = Workflow(
    name="sequential_workflow",
    edges=[
        (START, extract_data, format_prompt, summarize_agent),
    ],
)

async def main():
    runner = Runner(
        node=workflow,
        app_name="test_app",
        session_service=InMemorySessionService(),
        auto_create_session=True,
    )
    user_msg = types.Content(role="user", parts=[types.Part(text="How do I reset my password?")])
    async for event in runner.run_async(
        user_id="user_1", session_id="session_1", new_message=user_msg
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    print(f"[{event.author}]: {part.text}")
        if event.output is not None:
            print(f"[{event.author}] output: {event.output}")

if __name__ == "__main__":
    asyncio.run(main())
