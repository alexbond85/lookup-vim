"""Tests for printer implementations"""

import json
import pytest
from robert_dict.printers.text import TextPrinter
from robert_dict.printers.json import JsonPrinter
from robert_dict.models import Definition, WordResult, ConjugationResult


class TestTextPrinter:
    """Tests for TextPrinter"""
    
    def test_text_printer_word_result(self, sample_word_result):
        """Test text printer formats word result correctly"""
        printer = TextPrinter()
        output = printer.print(sample_word_result)
        
        assert "bien" in output
        assert "adverbe" in output
        assert "D'une manière satisfaisante" in output
        assert "Elle danse bien." in output
        assert isinstance(output, str)
    
    def test_text_printer_conjugation_result(self, sample_conjugation_result):
        """Test text printer formats conjugation result correctly"""
        printer = TextPrinter()
        output = printer.print(sample_conjugation_result)
        
        # Text printer uppercases the word in the header
        assert "ÉCRIVAIENT" in output or "écrivaient" in output
        # "écrire" appears in the URL
        assert "ecrire" in output.lower()
        assert isinstance(output, str)
    
    def test_text_printer_empty_definitions(self):
        """Test text printer handles empty definitions"""
        result = WordResult(
            word="test",
            url="https://example.com",
            definitions=[]
        )
        printer = TextPrinter()
        output = printer.print(result)
        
        assert "test" in output or "TEST" in output
        assert isinstance(output, str)


class TestJsonPrinter:
    """Tests for JsonPrinter"""
    
    def test_json_printer_word_result(self, sample_word_result):
        """Test JSON printer formats word result correctly"""
        printer = JsonPrinter(indent=2)
        output = printer.print(sample_word_result)
        
        # Parse JSON to verify it's valid
        data = json.loads(output)
        
        assert data["word"] == "bien"
        assert data["original_word"] == "bien"
        assert len(data["definitions"]) == 2
        assert data["definitions"][0]["category"] == "adverbe"
        assert "bien commun" in data["word_combinations"]
    
    def test_json_printer_conjugation_result(self, sample_conjugation_result):
        """Test JSON printer formats conjugation result correctly"""
        printer = JsonPrinter(indent=2)
        output = printer.print(sample_conjugation_result)
        
        data = json.loads(output)
        
        assert data["original_word"] == "écrivaient"
        assert data["redirected_to"] == "écrire"
        assert "url" in data
    
    def test_json_printer_custom_indent(self):
        """Test JSON printer with custom indentation"""
        result = WordResult(word="test", url="https://example.com")
        
        # Compact format (indent=None for truly compact JSON)
        printer_compact = JsonPrinter(indent=None)
        output_compact = printer_compact.print(result)
        # With indent=None, JSON is on one line (though Python may still add some newlines)
        data_compact = json.loads(output_compact)
        assert data_compact["word"] == "test"
        
        # Pretty format (indent=4)
        printer_pretty = JsonPrinter(indent=4)
        output_pretty = printer_pretty.print(result)
        assert "\n" in output_pretty
        assert "    " in output_pretty  # 4 spaces
        data_pretty = json.loads(output_pretty)
        assert data_pretty["word"] == "test"
    
    def test_json_printer_french_characters(self):
        """Test JSON printer preserves French characters"""
        result = WordResult(
            word="être",
            url="https://example.com",
            definitions=[
                Definition(
                    category="verbe",
                    definition="Avoir une réalité",
                    examples=["Je suis, tu es"]
                )
            ]
        )
        printer = JsonPrinter()
        output = printer.print(result)
        
        # ensure_ascii=False should preserve French characters
        assert "être" in output
        assert "réalité" in output
        
        # Verify it's valid JSON
        data = json.loads(output)
        assert data["word"] == "être"

