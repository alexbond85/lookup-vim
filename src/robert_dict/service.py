"""Dictionary service orchestrating scraping and printing"""

from typing import Union

from robert_dict.models import WordResult, ConjugationResult
from robert_dict.scrapers.base import Scraper
from robert_dict.printers.base import Printer


class DictionaryService:
    """Service layer that orchestrates dictionary lookup and formatting"""
    
    def __init__(self, scraper, printer):
        """
        Initialize service with scraper and printer.
        
        Args:
            scraper: Implementation of Scraper protocol
            printer: Implementation of Printer protocol
        """
        self.scraper = scraper
        self.printer = printer
    
    def lookup(self, word: str) -> str:
        """
        Look up a word and return formatted result.
        
        Args:
            word: The word to look up
            
        Returns:
            Formatted string output
            
        Raises:
            ValueError: If word not found
            Exception: For other errors
        """
        result = self.scraper.fetch(word)
        return self.printer.print(result)

