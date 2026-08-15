"""07: L7 Managed Cloud Memory — VertexAiSessionService, VertexAiMemoryBankService, GcsArtifactService"""
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
from google.adk.tools.preload_memory_tool import preload_memory_tool
from google.genai import types

# In local / self-hosted environments:
from google.adk.sessions import InMemorySessionService, DatabaseSessionService
from google.adk.memory import InMemoryMemoryService
from google.adk.artifacts import FileArtifactService

# In managed Google Cloud / Vertex AI enterprise production:
from google.adk.sessions.vertex_ai_session_service import VertexAiSessionService
from google.adk.memory.vertex_ai_memory_bank_service import VertexAiMemoryBankService
from google.adk.artifacts.gcs_artifact_service import GcsArtifactService

MODEL = os.environ.get("ADK_MODEL", "gemini-2.5-flash")
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "gcp-experiments-349209")
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
USE_MANAGED_SERVICES = os.environ.get("USE_VERTEX_MEMORY_SERVICES", "False").lower() == "true"

# The core agent code is 100% identical regardless of backend
enterprise_chef = Agent(
    name="enterprise_chef",
    model=MODEL,
    instruction="""You are an enterprise catering and culinary advisor.
    Always take into account past user conversations, dietary restrictions, and regional guidelines.
    Be concise, helpful, and professional.""",
    tools=[preload_memory_tool],
)

def create_services():
    """Factory creating local services or managed cloud services with zero agent code changes."""
    if USE_MANAGED_SERVICES:
        print("[Cloud Architecture] Initializing fully managed Vertex AI and Cloud Storage services...")
        session_service = VertexAiSessionService(project=PROJECT_ID, location=LOCATION)
        memory_service = VertexAiMemoryBankService(project=PROJECT_ID, location=LOCATION)
        artifact_service = GcsArtifactService(bucket_name=f"{PROJECT_ID}-adk-artifacts")
    else:
        print("[Local Architecture] Initializing self-hosted / local developer memory services...")
        session_service = InMemorySessionService()
        memory_service = InMemoryMemoryService()
        artifact_service = FileArtifactService(root_dir="./local_artifacts")
    
    return session_service, memory_service, artifact_service

async def main():
    session_service, memory_service, artifact_service = create_services()

    runner = Runner(
        agent=enterprise_chef,
        app_name="enterprise_chef_app",
        session_service=session_service,
        memory_service=memory_service,
        artifact_service=artifact_service,
    )

    print("\n=== Simulating Enterprise Interaction across Managed Memory ===")
    s = await session_service.create_session(app_name="enterprise_chef_app", user_id="u_corp_vip")
    query = "Plan a 3-course executive lunch for 15 executives with Mediterranean options."
    print(f"Customer: {query}\n")

    content = types.Content(role="user", parts=[types.Part(text=query)])
    async for event in runner.run_async(user_id="u_corp_vip", session_id=s.id, new_message=content):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    print(f"[{event.author}]: {part.text}")

if __name__ == "__main__":
    asyncio.run(main())
