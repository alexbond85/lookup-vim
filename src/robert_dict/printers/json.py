import json
from typing import Union
from dataclasses import asdict

from robert_dict.models import WordResult, ConjugationResult


class JsonPrinter:

    def __init__(self, indent: int = 2):
        self.indent = indent
    
    def print(self, result: Union[WordResult, ConjugationResult]) -> str:
        data = self._to_dict(result)
        return json.dumps(data, ensure_ascii=False, indent=self.indent)
    
    def _to_dict(self, result: Union[WordResult, ConjugationResult]) -> dict:
        if isinstance(result, WordResult):
            return self._word_result_to_dict(result)
        elif isinstance(result, ConjugationResult):
            return self._conjugation_result_to_dict(result)
        return asdict(result)
    
    def _word_result_to_dict(self, result: WordResult) -> dict:
        return {
            "word": result.word,
            "original_word": result.original_word or result.word,
            "url": result.url,
            "definitions": [
                {
                    "category": d.category,
                    "definition": d.definition,
                    "examples": d.examples
                }
                for d in result.definitions
            ],
            "usage_examples": result.usage_examples,
            "word_combinations": result.word_combinations
        }
    
    def _conjugation_result_to_dict(self, result: ConjugationResult) -> dict:
        return {
            "type": "conjugation",
            "original_word": result.original_word,
            "redirected_to": result.redirected_to,
            "url": result.url,
            "definition_url": result.definition_url,
            "conjugations_sample": result.conjugations_sample,
            "message": result.message
        }
