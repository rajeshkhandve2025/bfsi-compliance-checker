"""Grounding layer — wraps bfsifiles advisory module with a singleton catalog."""

import sys
from pathlib import Path

# Ensure project root (containing bfsifiles/) is importable
_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from bfsifiles.bfsi_advisor import (  # noqa: E402
    SourceCatalog,
    AnswerValidator,
    fetch_amfi_nav,
    PolicyViolation,
    TopicNotFound,
)

_BFSIFILES = _PROJECT_ROOT / "bfsifiles"
_catalog: SourceCatalog | None = None


def get_catalog() -> SourceCatalog:
    global _catalog
    if _catalog is None:
        _catalog = SourceCatalog(
            _BFSIFILES / "bfsi_sources.yaml",
            _BFSIFILES / "bfsi_schema.json",
        )
    return _catalog


__all__ = [
    "SourceCatalog",
    "AnswerValidator",
    "fetch_amfi_nav",
    "PolicyViolation",
    "TopicNotFound",
    "get_catalog",
]
