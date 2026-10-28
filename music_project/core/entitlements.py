from dataclasses import dataclass


@dataclass(frozen=True)
class Entitlements:
    """Future licensing belongs outside the analytical engine; v0.1 allows all features."""

    edition: str = "development"

    def allows(self, feature: str) -> bool:
        return True
