import asyncio

from dotenv import load_dotenv
from loguru import logger

from src.bot import main
from src.utils import setup_logger

load_dotenv()

if __name__ == "__main__":
    setup_logger(logger)
    asyncio.run(main())
