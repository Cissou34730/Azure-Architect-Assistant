from dataclasses import dataclass


@dataclass
class SummaryResult:
    summary: str


class SummaryChain:
    def __init__(self, enabled: bool = False):
        self.enabled = enabled

    @classmethod
    def disabled(cls) -> "SummaryChain":
        return cls(enabled=False)

    def summarize(self, messages: list[dict[str, str]]) -> SummaryResult | None:
        if not self.enabled:
            return None
        # No-op stub: return None to avoid changing behavior by default
        return None

