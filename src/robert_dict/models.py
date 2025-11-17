"""Domain models for dictionary data"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Definition:
    """A single definition with its category and examples"""
    category: str
    definition: str
    examples: List[str] = field(default_factory=list)


@dataclass
class WordResult:
    """Result of a word lookup containing definitions and usage information"""
    word: str
    url: str
    original_word: Optional[str] = None
    definitions: List[Definition] = field(default_factory=list)
    usage_examples: List[str] = field(default_factory=list)
    word_combinations: List[str] = field(default_factory=list)


@dataclass
class ConjugationResult:
    """Result when a word redirects to a conjugation page"""
    original_word: str
    redirected_to: str
    url: str
    definition_url: Optional[str] = None
    conjugations_sample: dict = field(default_factory=dict)
    message: str = ""


@dataclass
class TranslationResult:
    """Result of a translation request with explanations"""
    query: str
    translation: str
    explanations: str
    context: Optional[str] = None
