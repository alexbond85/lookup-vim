"""Tests for DictionaryService"""

import pytest
from robert_dict.service import DictionaryService


def test_service_initialization(mock_scraper, mock_printer):
    """Test service initializes with scraper and printer"""
    service = DictionaryService(scraper=mock_scraper, printer=mock_printer)
    
    assert service.scraper == mock_scraper
    assert service.printer == mock_printer


def test_service_lookup_calls_scraper(mock_scraper, mock_printer, sample_word_result):
    """Test lookup calls scraper with correct word"""
    mock_scraper.result = sample_word_result
    service = DictionaryService(scraper=mock_scraper, printer=mock_printer)
    
    service.lookup("bien")
    
    assert mock_scraper.fetch_called_with == "bien"


def test_service_lookup_calls_printer(mock_scraper, mock_printer, sample_word_result):
    """Test lookup calls printer with scraper result"""
    mock_scraper.result = sample_word_result
    service = DictionaryService(scraper=mock_scraper, printer=mock_printer)
    
    service.lookup("bien")
    
    assert mock_printer.print_called_with == sample_word_result


def test_service_lookup_returns_printer_output(mock_scraper, mock_printer, sample_word_result):
    """Test lookup returns printer output"""
    mock_scraper.result = sample_word_result
    mock_printer.output = "Beautiful formatted text"
    service = DictionaryService(scraper=mock_scraper, printer=mock_printer)
    
    result = service.lookup("bien")
    
    assert result == "Beautiful formatted text"


def test_service_lookup_propagates_value_error(mock_scraper, mock_printer):
    """Test lookup propagates ValueError from scraper"""
    mock_scraper.should_raise = ValueError("Word not found")
    service = DictionaryService(scraper=mock_scraper, printer=mock_printer)
    
    with pytest.raises(ValueError, match="Word not found"):
        service.lookup("nonexistent")


def test_service_lookup_propagates_network_error(mock_scraper, mock_printer):
    """Test lookup propagates network errors from scraper"""
    mock_scraper.should_raise = Exception("Network error")
    service = DictionaryService(scraper=mock_scraper, printer=mock_printer)
    
    with pytest.raises(Exception, match="Network error"):
        service.lookup("test")

