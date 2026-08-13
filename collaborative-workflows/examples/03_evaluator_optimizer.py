"""03: Evaluator-Optimizer Loop — Draft, critique, refine"""
import asyncio
import os
from google.adk.agents import LoopAgent, LlmAgent
from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

MODEL = os.environ.get("ADK_MODEL", "gemini-2.5-flash")

response_writer = LlmAgent(
    name="response_writer",
    model=MODEL,
    instruction="""You are a customer support response writer. Write a response to the customer's issue.
    Requirements:
    - Show empathy for their frustration
    - Include specific next steps
    - Mention a timeline
    - Keep it under 80 words
    - Sign off as 'Support Team'
    
    If there is previous feedback from the evaluator in the conversation, incorporate it to improve your draft.""",
    output_key="draft_response",
)

quality_evaluator = LlmAgent(
    name="quality_evaluator",
    model=MODEL,
    instruction="""You are a quality evaluator for customer support responses. Score the latest draft on:
    1. Empathy (1-10): Does it acknowledge the customer's feelings?
    2. Specificity (1-10): Does it include concrete next steps and timelines?
    3. Professionalism (1-10): Is the tone appropriate?
    
    Output your scores and calculate the average. If average >= 8, say "APPROVED" on its own line.
    If average < 8, say "NEEDS REVISION" and provide specific feedback for improvement.
    
    IMPORTANT: You must eventually approve after seeing improvements. Do not be infinitely critical.""",
    output_key="evaluation",
)

refinement_loop = LoopAgent(
    name="response_refiner",
    sub_agents=[response_writer, quality_evaluator],
    max_iterations=3,
)

async def main():
    runner = Runner(
        agent=refinement_loop,
        app_name="support_loop",
        session_service=InMemorySessionService(),
    )
    session = await runner.session_service.create_session(
        app_name="support_loop", user_id="user_1"
    )

    ticket = "I was charged twice for my subscription this month. This is the third time this has happened!"

    print(f"TICKET: {ticket}\n")
    print('='*60)

    content = types.Content(role="user", parts=[types.Part(text=ticket)])
    iteration = 0
    async for event in runner.run_async(
        user_id="user_1",
        session_id=session.id,
        new_message=content,
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    if event.author == "response_writer":
                        iteration += 1
                        print(f"\n--- Draft {(iteration + 1) // 2} ---")
                    print(f"[{event.author}]: {part.text}")

if __name__ == "__main__":
    asyncio.run(main())
