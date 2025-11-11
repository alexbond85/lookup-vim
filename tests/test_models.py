"""Tests for domain models"""

import pytest
from robert_dict.models import Definition, WordResult, ConjugationResult


def test_definition_creation():
    """Test Definition dataclass creation"""
    definition = Definition(
        category="nom masculin",
        definition="Une définition",
        examples=["exemple 1", "exemple 2"]
    )
    
    assert definition.category == "nom masculin"
    assert definition.definition == "Une définition"
    assert len(definition.examples) == 2
    assert definition.examples[0] == "exemple 1"


def test_definition_default_examples():
    """Test Definition with default empty examples list"""
    definition = Definition(
        category="adverbe",
        definition="Une définition sans exemples"
    )
    
    assert definition.examples == []


def test_word_result_creation(sample_definition):
    """Test WordResult dataclass creation"""
    result = WordResult(
        word="maison",
        url="https://dictionnaire.lerobert.com/definition/maison",
        original_word="maison",
        definitions=[sample_definition],
        usage_examples=["Une belle maison"],
        word_combinations=["maison blanche"]
    )
    
    assert result.word == "maison"
    assert result.original_word == "maison"
    assert len(result.definitions) == 1
    assert result.definitions[0] == sample_definition


def test_word_result_defaults():
    """Test WordResult with default values"""
    result = WordResult(
        word="test",
        url="https://example.com"
    )
    
    assert result.word == "test"
    assert result.original_word is None
    assert result.definitions == []
    assert result.usage_examples == []
    assert result.word_combinations == []


def test_conjugation_result_creation():
    """Test ConjugationResult dataclass creation"""
    result = ConjugationResult(
        original_word="écrivaient",
        redirected_to="écrire",
        url="https://dictionnaire.lerobert.com/conjugaison/ecrire"
    )
    
    assert result.original_word == "écrivaient"
    assert result.redirected_to == "écrire"
    assert result.url == "https://dictionnaire.lerobert.com/conjugaison/ecrire"
    assert result.definition_url is None
    assert result.conjugations_sample == {}
    assert result.message == ""

