from dataclasses import dataclass


@dataclass
class OperationResult:
    ok: bool
    message: str
    code: int | None = None
    category: str = "info"

    def text(self) -> str:
        return self.message
