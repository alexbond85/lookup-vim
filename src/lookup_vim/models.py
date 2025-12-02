from dataclasses import dataclass, field


@dataclass
class Definition:
    """A single definition with its category and examples"""

    category: str
    definition: str
    examples: list[str] = field(default_factory=list)


@dataclass
class WordResult:
    """Result of a word lookup containing definitions and usage information"""

    word: str
    url: str
    original_word: str | None = None
    definitions: list[Definition] = field(default_factory=list)
    usage_examples: list[str] = field(default_factory=list)
    word_combinations: list[str] = field(default_factory=list)


# not used yet
@dataclass
class ConjugationResult:
    """Result when a word redirects to a conjugation page"""

    original_word: str
    redirected_to: str
    url: str
    definition_url: str | None = None
    conjugations_sample: dict = field(default_factory=dict)
    message: str = ""


@dataclass
class TranslationResult:
    """Result of a translation request with explanations"""

    query: str
    translation: str
    explanations: str
    context: str | None = None


@dataclass
class SelectionData:
    """Data captured from text selection in Vim"""
    selection: str = ""
    phrase: str = ""
    paragraph: str = ""
    file: str = ""
