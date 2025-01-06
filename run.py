import asyncio

from dotenv import load_dotenv
from loguru import logger

from src.bot import main
from src.utils import setup_logger

load_dotenv()

if __name__ == "__main__":
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()
    setup_logger(logger, level="DEBUG" if args.debug else "INFO")
    asyncio.run(main())
