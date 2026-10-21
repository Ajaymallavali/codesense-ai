import asyncio
import json
import logging
import signal
import sys
import time
from uuid import UUID

from app.config import settings
from app.jobs import REDIS_QUEUE_KEY, get_redis_client, process_analysis_job

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [CodeSense-Worker] %(message)s",
)
logger = logging.getLogger("codesense.worker")


class DedicatedWorker:
    """
    Dedicated production Redis background worker.
    Continuously listens on `codesense:queue:analysis` for asynchronous job processing.
    """

    def __init__(self):
        self.running = True

    def stop(self, *args):
        logger.info("Worker received shutdown signal. Exiting gracefully...")
        self.running = False

    async def start(self):
        logger.info(f"Starting CodeSense Dedicated Background Worker (Redis: {settings.redis_url})")
        logger.info(f"Monitoring queue: '{REDIS_QUEUE_KEY}'")

        while self.running:
            client = get_redis_client()
            if client is None:
                logger.warning("Redis is not reachable. Retrying connection in 5 seconds...")
                await asyncio.sleep(5)
                continue

            try:
                # Blocking pop from Redis queue with 2 second timeout
                item = client.brpop(REDIS_QUEUE_KEY, timeout=2)
                if not item:
                    await asyncio.sleep(0.5)
                    continue

                _, message_raw = item
                data = json.loads(message_raw)
                analysis_id_str = data.get("analysis_id")

                if not analysis_id_str:
                    logger.warning(f"Discarding invalid message payload: {message_raw}")
                    continue

                logger.info(f"Dequeued analysis job: {analysis_id_str}")
                analysis_id = UUID(analysis_id_str)
                await process_analysis_job(analysis_id)
                logger.info(f"Completed job processing for: {analysis_id_str}")

            except Exception as exc:
                logger.error(f"Worker iteration encountered error: {exc}", exc_info=True)
                await asyncio.sleep(1)


def main():
    worker = DedicatedWorker()
    signal.signal(signal.SIGINT, worker.stop)
    signal.signal(signal.SIGTERM, worker.stop)
    try:
        asyncio.run(worker.start())
    except KeyboardInterrupt:
        logger.info("Worker stopped by user.")


if __name__ == "__main__":
    main()
