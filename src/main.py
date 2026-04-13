import asyncio

from app.processes import process
from app import config, logger


async def run_loop():
    while True:
        try:
            await process()
        except Exception as e:
            logger.exception(f"Top-level error in process loop: {e}")


def main():
    asyncio.run(run_loop())


if __name__ == "__main__":
    main()
