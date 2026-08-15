"""02: L2 Durable Cross-Session State — DatabaseSessionService and the user: scope prefix"""
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
from google.adk.sessions import DatabaseSessionService
from google.genai import types

MODEL = os.environ.get("ADK_MODEL", "gemini-2.5-flash")

# Cloud Database configuration (Google Cloud SQL PostgreSQL / Vertex AI Managed Sessions)
# For Google Cloud SQL (PostgreSQL): postgresql+asyncpg://<user>:<password>@<cloud_sql_host>/<database>
# Or fallback to persistent Database URL from environment:
CLOUDSQL_DB_URL = os.environ.get(
    "CLOUDSQL_DATABASE_URL", 
    "sqlite+aiosqlite:///chef_cloud_persisted.db"  # Async SQL engine compatible with Cloud SQL PostgreSQL & SQLite
)

# Agent that writes to user-scoped persistent state: user:allergies, user:cuisine
profile_agent = Agent(
    name="profile_manager",
    model=MODEL,
    instruction="""You are an account profile manager.
    Extract the user's permanent preferences:
    - User Allergy
    - User Favorite Cuisine
    Format: ALLERGY: <allergy> | CUISINE: <cuisine>""",
    output_key="user:dietary_preferences",  # Note the user: scope prefix!
)

chef_agent = Agent(
    name="persistent_chef",
    model=MODEL,
    instruction="""You are a personal chef.
    You have access to the user's permanent profile in your session state: {user:dietary_preferences}.
    Always adhere strictly to these preferences and allergies when suggesting dinner recipes.""",
)

def get_cloud_session_service():
    """Returns Cloud SQL DatabaseSessionService (or VertexAiSessionService in production)."""
    # Vertex AI / Google Cloud Managed Database Service:
    # If GOOGLE_GENAI_USE_VERTEXAI and VERTEX_SESSION_ENGINE are configured:
    # return VertexAiSessionService(project=PROJECT_ID, location=LOCATION)
    #
    # For Google Cloud SQL (PostgreSQL / AlloyDB):
    return DatabaseSessionService(db_url=CLOUDSQL_DB_URL)

async def main():
    if os.path.exists("chef_cloud_persisted.db"):
        os.remove("chef_cloud_persisted.db")

    session_service = get_cloud_session_service()

    # =========================================================================
    # DAY 1: Session 1 — User tells agent their permanent preferences
    # =========================================================================
    print("=== DAY 1: Initial onboarding in Session 1 (Stored in SQLite DB) ===")
    runner1 = Runner(
        agent=profile_agent,
        app_name="chef_app",
        session_service=session_service,
    )
    s1 = await session_service.create_session(app_name="chef_app", user_id="u_alex")
    
    msg1 = "Hello! Please remember that I am gluten-intolerant and I love Mediterranean food."
    print(f"Customer: {msg1}")
    content1 = types.Content(role="user", parts=[types.Part(text=msg1)])
    
    async for event in runner1.run_async(
        user_id="u_alex", session_id=s1.id, new_message=content1
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    print(f"[{event.author}]: {part.text}")

    # Inspect persisted state in database
    s1_check = await session_service.get_session(app_name="chef_app", user_id="u_alex", session_id=s1.id)
    print("\n[DB State Check]:")
    print(f"user:dietary_preferences = {s1_check.state.get('user:dietary_preferences')}")

    # =========================================================================
    # DAY 3: Complete Server Restart & New Session 2 for the same user
    # =========================================================================
    print("\n" + "="*65)
    print("=== DAY 3: SERVER RESTART -> Brand New Session 2 for u_alex ===")
    print("="*65)
    
    # Reinitialize service to simulate fresh server process connecting to Cloud SQL
    new_session_service = get_cloud_session_service()
    runner2 = Runner(
        agent=chef_agent,
        app_name="chef_app",
        session_service=new_session_service,
    )

    # When creating a new session for u_alex, user:* scoped state is automatically propagated!
    s2 = await new_session_service.create_session(app_name="chef_app", user_id="u_alex")
    print(f"New Session Created: {s2.id}")
    print(f"Pre-populated user:* state in Session 2: {s2.state.get('user:dietary_preferences')}")

    msg2 = "What should I cook for dinner tonight?"
    print(f"\nCustomer: {msg2}")
    content2 = types.Content(role="user", parts=[types.Part(text=msg2)])
    
    async for event in runner2.run_async(
        user_id="u_alex", session_id=s2.id, new_message=content2
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    print(f"[{event.author}]: {part.text}")

    # Clean up demo DB
    if os.path.exists("chef_memory.db"):
        os.remove("chef_memory.db")

if __name__ == "__main__":
    asyncio.run(main())
