"""Tests for DictionaryService"""

import pytest
from robert_dict.service import DictionaryService
from robert_dict.models import WordResult, Definition


class MockScraper:
    """Mock scraper for testing"""
    
    def __init__(self, result=None, should_raise=None):
        self.result = result
        self.should_raise = should_raise
        self.fetch_called_with = None
    
    def fetch(self, word: str):
        self.fetch_called_with = word
        if self.should_raise:
            raise self.should_raise
        return self.result


class MockPrinter:
    """Mock printer for testing"""
    
    def __init__(self, output="formatted output"):
        self.output = output
        self.print_called_with = None
    
    def print(self, result):
        self.print_called_with = result
        return self.output


def test_service_initialization():
    """Test service initializes with scraper and printer"""
    scraper = MockScraper()
    printer = MockPrinter()
    service = DictionaryService(scraper=scraper, printer=printer)
    
    assert service.scraper == scraper
    assert service.printer == printer


def test_service_lookup_success(sample_word_result):
    """Test successful word lookup"""
    scraper = MockScraper(result=sample_word_result)
    printer = MockPrinter(output="Beautiful formatted text")
    service = DictionaryService(scraper=scraper, printer=printer)
    
    result = service.lookup("bien")
    
    assert result == "Beautiful formatted text"
    assert scraper.fetch_called_with == "bien"
    assert printer.print_called_with == sample_word_result


def test_service_lookup_word_not_found():
    """Test lookup with word not found"""
    scraper = MockScraper(should_raise=ValueError("Word not found"))
    printer = MockPrinter()
    service = DictionaryService(scraper=scraper, printer=printer)
    
    with pytest.raises(ValueError, match="Word not found"):
        service.lookup("nonexistentword")
    
    assert scraper.fetch_called_with == "nonexistentword"
    assert printer.print_called_with is None


def test_service_lookup_network_error():
    """Test lookup with network error"""
    scraper = MockScraper(should_raise=Exception("Network error"))
    printer = MockPrinter()
    service = DictionaryService(scraper=scraper, printer=printer)
    
    with pytest.raises(Exception, match="Network error"):
        service.lookup("test")

