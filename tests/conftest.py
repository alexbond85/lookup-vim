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

