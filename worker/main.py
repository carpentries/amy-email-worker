import asyncio
import logging
from typing import Any

import httpx
from aws_lambda_powertools.utilities.typing import LambdaContext

from src.api import ScheduledEmailController
from src.handler import handle_email
from src.settings import SETTINGS, STAGE, read_mailgun_credentials
from src.token import TokenCache
from src.types import WorkerOutput

logging.basicConfig()
logger = logging.getLogger("amy-email-worker")
logger.setLevel(logging.INFO)  # use logging.DEBUG to see boto3 logs


# TODO:
# 1. rewrite to async ✅
# 2. make sure tests pass (even with async on) ✅
# 3. add mapping for API endpoints ✅
# 4. fetch and render emails ✅
# 5. write unit tests! ✅
# 6. create new simplified API in AMY ✅
# 7. use authentication in the new API ✅
# 8. use authentication in the worker ✅
# 9. limit access only for accounts with special permission ✅
# 10. update CDK with envvars ✅ / secrets (created by hand) ✅
# 11. create schemas for the endpoints ❌ (doesn't seem to be needed)
# 12. add endpoints for managing emails ✅
# 13. rewrite email logic from handler below to use the new email endpoints ✅
# 14. add tests for the new email management logic ✅


async def main(event: dict[Any, Any], context: LambdaContext) -> WorkerOutput:
    logger.info(f"Start handler with arguments: {event=}, {context=}")

    overwrite_outgoing_emails = SETTINGS.OVERWRITE_OUTGOING_EMAILS
    logger.info(f"Stage: {STAGE}")
    logger.info(f"Outgoing emails override: {overwrite_outgoing_emails}")

    mailgun_credentials = read_mailgun_credentials()
    logger.info("Obtained credentials for Mailgun.")

    result: WorkerOutput = {"emails": []}

    async with httpx.AsyncClient() as client:
        token_cache = TokenCache(client)

        controller = ScheduledEmailController(
            api_base_url=SETTINGS.API_BASE_URL,
            client=client,
            token_cache=token_cache,
        )
        emails = await controller.get_scheduled_to_run()

        result["emails"] = await asyncio.gather(
            *[
                handle_email(
                    email,
                    mailgun_credentials,
                    overwrite_outgoing_emails,
                    controller,
                    client,
                    token_cache,
                )
                for email in emails
            ]
        )

    logger.info(f"End handler with result: {result}")
    return result


def handler(event: dict[Any, Any], context: LambdaContext) -> WorkerOutput:
    return asyncio.run(main(event, context))
