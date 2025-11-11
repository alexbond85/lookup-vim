"""Base printer protocol defining the interface for result formatters"""

from typing import Protocol, Union
from robert_dict.models import WordResult, ConjugationResult


class Printer(Protocol):
    """Protocol for result printer implementations"""
    
    def print(self, result: Union[WordResult, ConjugationResult]) -> str:
        """
        Format a dictionary result for output.
        
        Args:
            result: The word or conjugation result to format
            
        Returns:
            Formatted string ready for output
        """
        ...

