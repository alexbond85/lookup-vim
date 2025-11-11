"""Text printer for dictionary results with beautiful console formatting"""

from typing import Union

from robert_dict.models import WordResult, ConjugationResult


class TextPrinter:
    """Format dictionary results as readable text for console"""
    
    def print(self, result: Union[WordResult, ConjugationResult]) -> str:
        """
        Format result as beautiful console text.
        
        Args:
            result: The word or conjugation result
            
        Returns:
            Formatted text string
        """
        if isinstance(result, ConjugationResult):
            return self._format_conjugation(result)
        return self._format_word(result)
    
    def _format_word(self, result: WordResult) -> str:
        """Format a WordResult as text"""
        lines = []
        
        # Header
        lines.append(self._create_header(result.word))
        lines.append("")
        
        # Definitions by category
        current_category = None
        definition_number = 1
        
        for definition in result.definitions:
            # Print category if it changes
            if definition.category != current_category:
                if current_category is not None:
                    lines.append("")
                lines.append(f"[{definition.category}]")
                lines.append("")
                current_category = definition.category
                definition_number = 1
            
            # Print definition
            lines.append(f"{definition_number}. {definition.definition}")
            
            # Print examples indented
            for example in definition.examples:
                lines.append(f"   → {example}")
            
            lines.append("")
            definition_number += 1
        
        # Usage examples section
        if result.usage_examples:
            lines.append("EXEMPLES D'USAGE")
            lines.append("─" * 35)
            for example in result.usage_examples[:10]:
                lines.append(f"• {example}")
            lines.append("")
        
        # Word combinations section
        if result.word_combinations:
            lines.append("MOTS FRÉQUEMMENT ASSOCIÉS")
            lines.append("─" * 35)
            # Group combinations in rows of ~60 chars
            combinations_text = ", ".join(result.word_combinations[:15])
            lines.append(combinations_text)
            lines.append("")
        
        # Footer with URL
        lines.append(f"Source: {result.url}")
        
        return "\n".join(lines)
    
    def _format_conjugation(self, result: ConjugationResult) -> str:
        """Format a ConjugationResult as text"""
        lines = []
        
        # Header
        lines.append(self._create_header(result.original_word))
        lines.append("")
        
        # Message
        lines.append(result.message)
        lines.append("")
        
        # Conjugations sample
        if result.conjugations_sample:
            lines.append("CONJUGAISON (échantillon)")
            lines.append("─" * 35)
            for tense, forms in result.conjugations_sample.items():
                lines.append(f"\n{tense.upper()}")
                for form in forms:
                    lines.append(f"  {form}")
            lines.append("")
        
        # Links
        if result.definition_url:
            lines.append(f"Définition: {result.definition_url}")
        lines.append(f"Conjugaison: {result.url}")
        
        return "\n".join(lines)
    
    def _create_header(self, word: str) -> str:
        """Create a formatted header for the word"""
        word_upper = word.upper()
        line_length = max(35, len(word_upper) + 4)
        separator = "═" * line_length
        
        # Center the word
        padding = (line_length - len(word_upper)) // 2
        centered_word = " " * padding + word_upper
        
        return f"{separator}\n{centered_word}\n{separator}"

