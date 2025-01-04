import asyncio
import logging
import sys

from dotenv import load_dotenv

from src.bot import main

load_dotenv()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
