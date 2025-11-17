"""Printer for translation results"""

import json
from robert_dict.models import TranslationResult
from robert_dict.constants import DEFAULT_JSON_INDENT


class TranslationPrinter:
    """Prints translation results in JSON format"""
    
    def __init__(self, indent: int = DEFAULT_JSON_INDENT):
        self.indent = indent
    
    def print(self, result: TranslationResult) -> str:
        """
        Convert TranslationResult to JSON string
        
        Args:
            result: The translation result to print
            
        Returns:
            JSON formatted string
        """
        output = {
            "query": result.query,
            "translation": result.translation,
            "explanations": result.explanations,
        }
        
        if result.context:
            output["context"] = result.context
        
        return json.dumps(output, ensure_ascii=False, indent=self.indent)

