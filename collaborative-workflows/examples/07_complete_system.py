"""07: Complete Collaborative Support System — All patterns combined"""
import asyncio
import os
from google.adk.agents import LlmAgent, SequentialAgent, LoopAgent
from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

MODEL = os.environ.get("ADK_MODEL", "gemini-2.5-flash")

# ===== Billing Pipeline (SequentialAgent) =====
billing_triage = LlmAgent(
    name="billing_triage",
    model=MODEL,
    instruction="Classify this billing issue type: refund, overcharge, or payment_failed. Reply with ONLY the type.",
    output_key="billing_type",
)

billing_resolver = LlmAgent(
    name="billing_resolver",
    model=MODEL,
    instruction="""Based on the billing type in the conversation, draft a resolution response.
    - For refund: explain 5-7 business day processing
    - For overcharge: confirm investigation and credit
    - For payment_failed: suggest alternative payment methods
    Keep under 60 words. Sign off as 'Billing Team'.""",
)

billing_pipeline = SequentialAgent(
    name="billing_pipeline",
    description="Handles all billing issues: refunds, overcharges, payment failures. Routes billing tickets through triage and resolution.",
    sub_agents=[billing_triage, billing_resolver],
)

# ===== Tech Support Loop (LoopAgent) =====
tech_diagnostician = LlmAgent(
    name="tech_diagnostician",
    model=MODEL,
    instruction="""You are a tech support diagnostician. Based on the user's issue (and any previous 
    diagnostic attempts in the conversation), suggest the NEXT troubleshooting step.
    Be specific and actionable. One step only, under 40 words.""",
    output_key="diagnosis",
)

tech_evaluator = LlmAgent(
    name="tech_evaluator",
    model=MODEL,
    instruction="""Review the diagnostic step suggested. Score it:
    - Relevance (1-10): Does it address the user's actual issue?
    - Actionability (1-10): Can the user follow this step?
    If average >= 7, say APPROVED. Otherwise say NEEDS REVISION with feedback.
    IMPORTANT: Be reasonable - approve good suggestions.""",
    output_key="evaluation",
)

tech_loop = LoopAgent(
    name="tech_support_loop",
    description="Handles technical issues through iterative diagnosis: bugs, errors, crashes, app problems.",
    sub_agents=[tech_diagnostician, tech_evaluator],
    max_iterations=2,
)

# ===== Shipping Specialist (single_turn) =====
shipping_specialist = LlmAgent(
    name="shipping_specialist",
    model=MODEL,
    description="Handles shipping inquiries: tracking, lost packages, delivery status. Quick lookup, no conversation needed.",
    instruction="Simulate a shipping lookup. Return tracking status, estimated delivery, and next steps if delayed. Under 50 words.",
    mode="single_turn",
)

# ===== General Support (chat) =====
general_specialist = LlmAgent(
    name="general_specialist",
    model=MODEL,
    description="Handles general questions: policies, account info, feature requests.",
    instruction="Answer the customer's general question helpfully. Under 50 words.",
)

# ===== The Coordinator =====
coordinator = LlmAgent(
    name="support_concierge",
    model=MODEL,
    instruction="""You are the customer support concierge. Your ONLY job is to:
    1. Understand the customer's issue
    2. Transfer to the most appropriate specialist:
       - billing_pipeline for refunds, charges, payments
       - tech_support_loop for bugs, crashes, errors
       - shipping_specialist for package tracking, delivery
       - general_specialist for everything else
    
    Do NOT answer directly. ALWAYS delegate.""",
    sub_agents=[billing_pipeline, tech_loop, shipping_specialist, general_specialist],
)

async def main():
    runner = Runner(
        agent=coordinator,
        app_name="complete_support",
        session_service=InMemorySessionService(),
    )

    tests = [
        ("I was charged twice for my subscription!", "Billing"),
        ("The app crashes when I upload photos", "Tech"),
        ("Where is my package? Order #789", "Shipping"),
    ]

    for query, label in tests:
        session = await runner.session_service.create_session(
            app_name="complete_support", user_id="user_1"
        )
        print(f"\n{'='*60}")
        print(f"[{label}] CUSTOMER: {query}")
        print('='*60)

        content = types.Content(role="user", parts=[types.Part(text=query)])
        async for event in runner.run_async(
            user_id="user_1",
            session_id=session.id,
            new_message=content,
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        print(f"[{event.author}]: {part.text}")

if __name__ == "__main__":
    asyncio.run(main())
