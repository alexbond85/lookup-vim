"""Tests for printer implementations"""

import json
from robert_dict.printers.text import TextPrinter
from robert_dict.printers.json import JsonPrinter
from robert_dict.models import Definition, WordResult


def test_text_printer_word_result(sample_word_result):
    """Test text printer formats word result"""
    printer = TextPrinter()
    output = printer.print(sample_word_result)
    
    assert "bien" in output
    assert "adverbe" in output
    assert "D'une manière satisfaisante" in output
    assert isinstance(output, str)


def test_text_printer_conjugation_result(sample_conjugation_result):
    """Test text printer formats conjugation result"""
    printer = TextPrinter()
    output = printer.print(sample_conjugation_result)
    
    assert "écrivaient" in output.lower()
    assert "ecrire" in output.lower()
    assert isinstance(output, str)


def test_text_printer_empty_definitions():
    """Test text printer handles empty definitions"""
    result = WordResult(word="test", url="https://example.com", definitions=[])
    printer = TextPrinter()
    output = printer.print(result)
    
    assert "test" in output.lower()
    assert isinstance(output, str)


def test_json_printer_word_result(sample_word_result):
    """Test JSON printer outputs valid JSON"""
    printer = JsonPrinter(indent=2)
    output = printer.print(sample_word_result)
    data = json.loads(output)
    
    assert data["word"] == "bien"
    assert len(data["definitions"]) == 2


def test_json_printer_conjugation_result(sample_conjugation_result):
    """Test JSON printer formats conjugation result"""
    printer = JsonPrinter(indent=2)
    output = printer.print(sample_conjugation_result)
    data = json.loads(output)
    
    assert data["original_word"] == "écrivaient"
    assert data["redirected_to"] == "écrire"


def test_json_printer_compact_format():
    """Test JSON printer with compact format"""
    result = WordResult(word="test", url="https://example.com")
    printer = JsonPrinter(indent=None)
    output = printer.print(result)
    data = json.loads(output)
    
    assert data["word"] == "test"


def test_json_printer_pretty_format():
    """Test JSON printer with pretty format"""
    result = WordResult(word="test", url="https://example.com")
    printer = JsonPrinter(indent=4)
    output = printer.print(result)
    
    assert "\n" in output
    assert "    " in output
    assert json.loads(output)["word"] == "test"


def test_json_printer_french_characters():
    """Test JSON printer preserves French characters"""
    result = WordResult(
        word="être",
        url="https://example.com",
        definitions=[
            Definition(
                category="verbe",
                definition="Avoir une réalité",
                examples=["Je suis"]
            )
        ]
    )
    printer = JsonPrinter()
    output = printer.print(result)
    
    assert "être" in output
    assert "réalité" in output
    assert json.loads(output)["word"] == "être"

