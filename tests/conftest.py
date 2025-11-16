"""Pytest configuration and shared fixtures"""

import pytest
from robert_dict.models import Definition, WordResult, ConjugationResult


@pytest.fixture
def sample_definition():
    """Sample definition for testing"""
    return Definition(
        category="nom masculin",
        definition="Un exemple de définition",
        examples=["Exemple 1", "Exemple 2"]
    )


@pytest.fixture
def sample_word_result():
    """Sample word result for testing"""
    return WordResult(
        word="bien",
        url="https://dictionnaire.lerobert.com/definition/bien",
        original_word="bien",
        definitions=[
            Definition(
                category="adverbe",
                definition="D'une manière satisfaisante",
                examples=["Elle danse bien.", "Il a très bien réussi."]
            ),
            Definition(
                category="nom masculin",
                definition="Ce qui est utile, bon, agréable",
                examples=["Le bien commun."]
            )
        ],
        usage_examples=["Bien évidemment."],
        word_combinations=["bien commun", "bien-être"]
    )


@pytest.fixture
def sample_conjugation_result():
    """Sample conjugation result for testing"""
    return ConjugationResult(
        original_word="écrivaient",
        redirected_to="écrire",
        url="https://dictionnaire.lerobert.com/conjugaison/ecrire",
        definition_url="https://dictionnaire.lerobert.com/definition/ecrire",
        conjugations_sample={"imparfait": ["écrivais", "écrivait"]},
        message="This is a conjugated form"
    )


class _MockScraper:
    """Mock scraper for testing"""
    
    def __init__(self):
        self.result = None
        self.should_raise = None
        self.fetch_called_with = None
    
    def fetch(self, word: str):
        self.fetch_called_with = word
        if self.should_raise:
            raise self.should_raise
        return self.result


class _MockPrinter:
    """Mock printer for testing"""
    
    def __init__(self):
        self.output = "formatted output"
        self.print_called_with = None
    
    def print(self, result):
        self.print_called_with = result
        return self.output


@pytest.fixture
def mock_scraper():
    """Mock scraper instance"""
    return _MockScraper()


@pytest.fixture
def mock_printer():
    """Mock printer instance"""
    return _MockPrinter()

