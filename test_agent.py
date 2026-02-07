import asyncio
import os
from dotenv import load_dotenv
from src.agent.runner import create_agent, run_agent

load_dotenv()

# Set dummy env vars if needed, but we rely on execution env
# os.environ["OPENAI_API_KEY"] = "sk-..."

async def main():
    try:
        print("Testing Agent Creation...")
        agent, mcp, config = await create_agent()
        print("Agent Created Successfully")
        print(f"Model: {config.model.model}")
        
        print("Testing Agent Run...")
        response = await run_agent(
            user_id="test_user",
            message="Hello, can you help me?"
        )
        print(f"Response: {response}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
