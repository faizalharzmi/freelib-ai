from typing import Protocol, Any


class BookProvider(Protocol):
    """
    Contract for external book search providers.
    """

    def search(
        self,
        query: str,
        access: str,
        page: int
    ) -> dict[str, Any]:
        ...