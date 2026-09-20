"""textstats: plain-English text statistics and readability scores.

Deterministic, offline, standard-library only.
"""

__version__ = "1.0.0"

from .analyze import (  # noqa: F401
    Analysis,
    analyze,
    flesch,
    flesch_kincaid,
    gunning_fog,
    smog,
    syllables,
    tokenize_sentences,
    tokenize_words,
)

__all__ = [
    "Analysis",
    "__version__",
    "analyze",
    "flesch",
    "flesch_kincaid",
    "gunning_fog",
    "smog",
    "syllables",
    "tokenize_sentences",
    "tokenize_words",
]