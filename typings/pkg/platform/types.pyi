from typing import Any

class Image:
    base64: str | None

    def __init__(self, *, base64: str | None = None, **kwargs: Any) -> None: ...

class MessageChain:
    def __init__(self, messages: list[Any]) -> None: ...

class Plain:
    text: str

    def __init__(self, text: str) -> None: ...
