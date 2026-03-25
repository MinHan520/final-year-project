from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class Finding:
    """A single diagnostic finding."""
    category: str        # e.g., "Anatomical Error", "Lighting Inconsistency"
    description: str     # Human-readable explanation
    severity: str        # "low", "medium", "high"
    location: str = ""   # Optional: coordinates, timestamp, or text position


@dataclass
class DiagnosticReport:
    """Complete diagnostic report for a piece of media."""
    media_type: str                    # "image", "video", "text"
    findings: list[Finding] = field(default_factory=list)

    @property
    def summary(self) -> str:
        if not self.findings:
            return (
                f"This is a highly realistic generation with very few obvious flaws. "
                f"However, our underlying detection models have identified AI signatures "
                f"within the file's data/metadata."
            )
        n = len(self.findings)
        return (
            f"Our detection system has flagged this {self.media_type} as AI-generated. "
            f"Upon review, here are the key indicators ({n} found):"
        )


class BaseAnalyzer(ABC):
    """Abstract base class for all media analyzers."""

    @abstractmethod
    def analyze(self, data) -> DiagnosticReport:
        """Analyze the given media data and return a diagnostic report."""
        ...
