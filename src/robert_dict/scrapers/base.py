"""Base scraper protocol defining the interface for dictionary scrapers"""

from typing import Protocol, Union
from robert_dict.models import WordResult, ConjugationResult


class Scraper(Protocol):
    """Protocol for dictionary scraper implementations"""
    
    def fetch(self, word: str) -> Union[WordResult, ConjugationResult]:
        """
        Fetch dictionary information for a word.
        
        Args:
            word: The word to look up
            
        Returns:
            WordResult or ConjugationResult depending on the page type
            
        Raises:
            ValueError: If the word is not found
            Exception: For other errors (network, parsing, etc.)
        """
        ...

