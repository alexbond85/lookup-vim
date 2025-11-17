"""ChatGPT-based translation service with contextual explanations"""

import os
from typing import Optional
from openai import OpenAI
from pydantic import BaseModel

from robert_dict.models import TranslationResult
from dotenv import load_dotenv
load_dotenv()

class TranslationOutput(BaseModel):
    """Structured output format for ChatGPT translation"""
    translation: str
    explanations: str


class ChatGPTTranslationService:
    """Service for translating French text to Russian with contextual explanations"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-5.1"):
        """
        Initialize the ChatGPT translation service
        
        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            model: OpenAI model to use (default: gpt-4o)
        """
        self.client = OpenAI(api_key=api_key)
        self.model = model
    
    def translate(self, query: str, context: Optional[str] = None) -> TranslationResult:
        """
        Translate a French word/expression to Russian with detailed explanations
        
        Args:
            query: The French word or expression to translate
            context: Optional paragraph providing context for the query
            
        Returns:
            TranslationResult containing translation and explanations
        """
        # Build the user prompt
        if context:
            user_content = f"""Le mot/expression "{query}" a été sélectionné dans ce contexte :

"{context}"

Donne une réponse courte et utile :
1. Traduction en russe
2. Sens littéral et explication (seulement si cela aide à comprendre le mot/expression)
3. Remarques supplémentaires (étymologie, connotation, nuances) - seulement si c'est important pour la compréhension"""
        else:
            user_content = f"""Traduis le mot/expression français "{query}" en russe et donne une réponse courte et utile :
1. Traduction
2. Sens littéral et explication (seulement si cela aide à comprendre le mot/expression)
3. Remarques supplémentaires (étymologie, connotation, nuances) - seulement si c'est important pour la compréhension"""
        
        # Call OpenAI API with structured output
        response = self.client.responses.parse(
            model=self.model,
            input=[
                {
                    "role": "system",
                    "content": "Tu es un traducteur du français vers le russe. Donne des traductions et explications courtes et précises. Utilise uniquement le français et le russe. Sois concis - ajoute des informations supplémentaires seulement si elles aident vraiment à comprendre le mot."
                },
                {
                    "role": "user",
                    "content": user_content
                },
            ],
            text_format=TranslationOutput,
            text={"verbosity": "low"}
        )
        
        # Extract the parsed output
        output = response.output_parsed
        
        # Create and return TranslationResult
        return TranslationResult(
            query=query,
            translation=output.translation,
            explanations=output.explanations,
            context=context
        )

