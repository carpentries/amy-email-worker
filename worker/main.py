from typing import TypedDict

from aws_lambda_powertools.utilities.typing import LambdaContext


class WorkerOutput(TypedDict):
    message: str


def handler(event: dict, context: LambdaContext) -> WorkerOutput:
    print("Arguments:")
    print(f"{event=}")
    print(f"{context=}")
    return {"message": "Hello World"}
