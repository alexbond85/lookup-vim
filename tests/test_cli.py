"""Tests for CLI module"""

import sys
from unittest.mock import patch, MagicMock
from robert_dict.cli import main


def test_cli_basic_lookup(monkeypatch):
    """Test basic CLI lookup"""
    test_args = ["robert-dict", "bien"]
    monkeypatch.setattr(sys, "argv", test_args)
    
    with patch('robert_dict.cli.DictionaryService') as mock_service_class:
        mock_service = MagicMock()
        mock_service.lookup.return_value = "Formatted output"
        mock_service_class.return_value = mock_service
        
        with patch('sys.exit') as mock_exit:
            main()
            mock_service.lookup.assert_called_once_with("bien")
            mock_exit.assert_called_once_with(0)


def test_cli_json_format(monkeypatch):
    """Test CLI with JSON format flag"""
    test_args = ["robert-dict", "maison", "--format", "json"]
    monkeypatch.setattr(sys, "argv", test_args)
    
    with patch('robert_dict.cli.DictionaryService') as mock_service_class:
        mock_service = MagicMock()
        mock_service.lookup.return_value = '{"word": "maison"}'
        mock_service_class.return_value = mock_service
        
        with patch('sys.exit') as mock_exit:
            main()
            mock_exit.assert_called_once_with(0)


def test_cli_custom_indent(monkeypatch):
    """Test CLI initializes JsonPrinter with custom indent"""
    test_args = ["robert-dict", "test", "--format", "json", "--indent", "4"]
    monkeypatch.setattr(sys, "argv", test_args)
    
    with patch('robert_dict.cli.DictionaryService'):
        with patch('robert_dict.cli.JsonPrinter') as mock_printer_class:
            with patch('sys.exit'):
                main()
                mock_printer_class.assert_called_once_with(indent=4)


def test_cli_word_not_found(monkeypatch):
    """Test CLI exits with code 1 when word not found"""
    test_args = ["robert-dict", "nonexistent"]
    monkeypatch.setattr(sys, "argv", test_args)
    
    with patch('robert_dict.cli.DictionaryService') as mock_service_class:
        mock_service = MagicMock()
        mock_service.lookup.side_effect = ValueError("Word not found")
        mock_service_class.return_value = mock_service
        
        with patch('sys.exit') as mock_exit:
            main()
            mock_exit.assert_called_once_with(1)


def test_cli_network_error(monkeypatch):
    """Test CLI exits with code 2 on network error"""
    test_args = ["robert-dict", "test"]
    monkeypatch.setattr(sys, "argv", test_args)
    
    with patch('robert_dict.cli.DictionaryService') as mock_service_class:
        mock_service = MagicMock()
        mock_service.lookup.side_effect = Exception("Network error")
        mock_service_class.return_value = mock_service
        
        with patch('sys.exit') as mock_exit:
            main()
            mock_exit.assert_called_once_with(2)


def test_cli_multi_word_phrase(monkeypatch):
    """Test CLI passes multi-word phrase correctly"""
    test_args = ["robert-dict", "bien que"]
    monkeypatch.setattr(sys, "argv", test_args)
    
    with patch('robert_dict.cli.DictionaryService') as mock_service_class:
        mock_service = MagicMock()
        mock_service.lookup.return_value = "Output"
        mock_service_class.return_value = mock_service
        
        with patch('sys.exit'):
            main()
            mock_service.lookup.assert_called_once_with("bien que")

