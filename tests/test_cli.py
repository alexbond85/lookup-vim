"""Tests for CLI module"""

import sys
import pytest
from io import StringIO
from unittest.mock import patch, MagicMock
from robert_dict.cli import main
from robert_dict.models import WordResult, Definition


class TestCLI:
    """Tests for command-line interface"""
    
    def test_cli_basic_lookup(self, monkeypatch, sample_word_result):
        """Test basic CLI lookup with text format"""
        # Mock sys.argv
        test_args = ["robert-dict", "bien"]
        monkeypatch.setattr(sys, "argv", test_args)
        
        # Mock the service to return a result
        with patch('robert_dict.cli.DictionaryService') as mock_service_class:
            mock_service = MagicMock()
            mock_service.lookup.return_value = "Formatted output"
            mock_service_class.return_value = mock_service
            
            # Mock sys.exit to prevent actual exit
            with patch('sys.exit') as mock_exit:
                main()
                
                # Verify service was called correctly
                mock_service.lookup.assert_called_once_with("bien")
                mock_exit.assert_called_once_with(0)
    
    def test_cli_json_format(self, monkeypatch):
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
    
    def test_cli_custom_indent(self, monkeypatch):
        """Test CLI with custom JSON indentation"""
        test_args = ["robert-dict", "test", "--format", "json", "--indent", "4"]
        monkeypatch.setattr(sys, "argv", test_args)
        
        with patch('robert_dict.cli.DictionaryService') as mock_service_class:
            with patch('robert_dict.cli.JsonPrinter') as mock_printer_class:
                mock_service = MagicMock()
                mock_service.lookup.return_value = "{}"
                mock_service_class.return_value = mock_service
                
                with patch('sys.exit'):
                    main()
                    
                    # Verify JsonPrinter was initialized with correct indent
                    mock_printer_class.assert_called_once_with(indent=4)
    
    def test_cli_word_not_found_text_format(self, monkeypatch, capsys):
        """Test CLI handles word not found with text format"""
        test_args = ["robert-dict", "nonexistent"]
        monkeypatch.setattr(sys, "argv", test_args)
        
        with patch('robert_dict.cli.DictionaryService') as mock_service_class:
            mock_service = MagicMock()
            mock_service.lookup.side_effect = ValueError("Word not found")
            mock_service_class.return_value = mock_service
            
            with patch('sys.exit') as mock_exit:
                main()
                
                # Should exit with code 1
                mock_exit.assert_called_once_with(1)
    
    def test_cli_word_not_found_json_format(self, monkeypatch, capsys):
        """Test CLI handles word not found with JSON format"""
        test_args = ["robert-dict", "nonexistent", "--format", "json"]
        monkeypatch.setattr(sys, "argv", test_args)
        
        with patch('robert_dict.cli.DictionaryService') as mock_service_class:
            mock_service = MagicMock()
            mock_service.lookup.side_effect = ValueError("Word not found")
            mock_service_class.return_value = mock_service
            
            with patch('sys.exit') as mock_exit:
                main()
                mock_exit.assert_called_once_with(1)
    
    def test_cli_network_error(self, monkeypatch):
        """Test CLI handles network errors"""
        test_args = ["robert-dict", "test"]
        monkeypatch.setattr(sys, "argv", test_args)
        
        with patch('robert_dict.cli.DictionaryService') as mock_service_class:
            mock_service = MagicMock()
            mock_service.lookup.side_effect = Exception("Network error")
            mock_service_class.return_value = mock_service
            
            with patch('sys.exit') as mock_exit:
                main()
                
                # Should exit with code 2 for general errors
                mock_exit.assert_called_once_with(2)
    
    def test_cli_multi_word_phrase(self, monkeypatch):
        """Test CLI with multi-word phrase"""
        test_args = ["robert-dict", "bien que"]
        monkeypatch.setattr(sys, "argv", test_args)
        
        with patch('robert_dict.cli.DictionaryService') as mock_service_class:
            mock_service = MagicMock()
            mock_service.lookup.return_value = "Output"
            mock_service_class.return_value = mock_service
            
            with patch('sys.exit'):
                main()
                
                # Verify the phrase was passed correctly
                mock_service.lookup.assert_called_once_with("bien que")

