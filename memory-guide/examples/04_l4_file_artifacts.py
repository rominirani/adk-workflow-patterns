"""04: L4 File Artifacts — Managing files, menus, and documents outside context window"""
import asyncio
import os
import shutil
import warnings
import logging

warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=ResourceWarning)
logging.getLogger("google.genai").setLevel(logging.ERROR)
logging.getLogger("aiohttp").setLevel(logging.ERROR)

from google.adk.agents import Agent
from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.artifacts.file_artifact_service import FileArtifactService
from google.adk.tools.load_artifacts_tool import load_artifacts_tool
from google.genai import types

MODEL = os.environ.get("ADK_MODEL", "gemini-2.5-flash")
ARTIFACT_DIR = "./chef_artifacts_store"

# Agent that has access to large documents / recipe books via artifact tools
menu_agent = Agent(
    name="sommelier_chef",
    model=MODEL,
    instruction="""You are an executive chef and sommelier.
    When asked about our seasonal tasting menu or wine pairings, load the menu artifact to answer accurately.""",
    tools=[load_artifacts_tool],
)

async def main():
    if os.path.exists(ARTIFACT_DIR):
        shutil.rmtree(ARTIFACT_DIR)
    os.makedirs(ARTIFACT_DIR, exist_ok=True)

    session_service = InMemorySessionService()
    artifact_service = FileArtifactService(root_dir=ARTIFACT_DIR)

    runner = Runner(
        agent=menu_agent,
        app_name="restaurant_app",
        session_service=session_service,
        artifact_service=artifact_service,
    )

    # 1. Pre-load a large structured menu artifact into the user's artifact store
    menu_part = types.Part(text="""
=== GRAND AUTUMN TASTING MENU 2026 ===
Course 1: Roasted Butternut Squash Velouté with Crispy Sage (Pairing: 2022 Domaine Leflaive Puligny-Montrachet)
Course 2: Wild Mushroom Risotto with Aged Parmesan & Truffle Oil (Pairing: 2019 Vietti Barolo Castiglione)
Course 3: Braised Wagyu Short Rib with Parsnip Puree (Pairing: 2018 Chateau Pontet-Canet Pauillac)
Dessert: Dark Chocolate Fondant with Espresso Gelato (Pairing: 20-Year Tawny Port)
Note: All risotto and soup courses are 100% nut-free and gluten-free by default.
""")
    
    await artifact_service.save_artifact(
        app_name="restaurant_app",
        user_id="u_vip",
        session_id="global_docs",
        filename="autumn_tasting_menu.txt",
        artifact=menu_part,
    )
    print("Artifact 'autumn_tasting_menu.txt' successfully saved into FileArtifactService!")

    # 2. User queries specific wine pairings from the menu without blowing up the context window
    s = await session_service.create_session(app_name="restaurant_app", user_id="u_vip")
    query = "What wine is paired with the Wagyu Short Rib on the Autumn Tasting Menu?"
    print(f"\nCustomer: {query}\n")

    content = types.Content(role="user", parts=[types.Part(text=query)])
    async for event in runner.run_async(
        user_id="u_vip", session_id=s.id, new_message=content
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    print(f"[{event.author}]: {part.text}")

    # Clean up demo dir
    if os.path.exists(ARTIFACT_DIR):
        shutil.rmtree(ARTIFACT_DIR)

if __name__ == "__main__":
    asyncio.run(main())
