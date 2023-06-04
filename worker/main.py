def handler(event, context) -> str:
    print("Arguments:")
    print(f"{event=}")
    print(f"{context=}")
    return "Hello world"
