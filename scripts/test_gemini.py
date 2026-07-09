import dotenv
import os
dotenv.load_dotenv(os.getenv("ENV_FILE", ".env"))

import asyncio
from src.app.llm.provider import get_llm


async def main():
    llm = get_llm(provider="gemini")
    response = await llm.ainvoke("Say 'Gemini provider works' and nothing else.")
    print(f"Response: {response.content}")


if __name__ == "__main__":
    asyncio.run(main())