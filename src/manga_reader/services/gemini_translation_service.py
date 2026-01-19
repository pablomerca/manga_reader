"""Gemini Translation Service - Implements translation via Google Gemini API."""

from datetime import datetime

import google.genai as genai
from google.genai import types

from manga_reader.services.translation_service import TranslationResult, TranslationService


class GeminiTranslationService(TranslationService):
    """
    Translation service using Google Gemini API.

    Optimized for speed and consistency with lower temperature settings.
    Uses the new google.genai package (maintained actively).
    """

    MODEL_NAME = "gemini-2.5-flash-lite"

    TRANSLATION_PROMPT = """Translate the following Japanese text to natural, idiomatic English.
Preserve the tone and nuance of the original.
Only output the translation, nothing else.

Japanese text:
{text}"""

    def translate(self, text: str, api_key: str) -> TranslationResult:
        """
        Translate Japanese text to English using Gemini API.

        Args:
            text: Japanese text to translate.
            api_key: Gemini API key for authentication.

        Returns:
            TranslationResult with translated text or error message.
        """
        try:
            client = genai.Client(api_key=api_key)
            
            prompt = self.TRANSLATION_PROMPT.format(text=text)
            
            response = client.models.generate_content(
                model=self.MODEL_NAME,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3,
                    top_p=0.95,
                    top_k=40,
                    max_output_tokens=1024,
                ),
            )
            
            if not response.text:
                return TranslationResult(
                    text="",
                    model=self.MODEL_NAME,
                    error="Empty response from API",
                )
            
            return TranslationResult(
                text=response.text.strip(),
                model=self.MODEL_NAME,
            )
            
        except Exception as e:
            error_msg = str(e).lower()
            
            if "api_key" in error_msg or "authentication" in error_msg or "invalid" in error_msg:
                return TranslationResult(
                    text="",
                    model=self.MODEL_NAME,
                    error=f"Invalid API key or request: {str(e)}",
                )
            elif "quota" in error_msg or "rate_limit" in error_msg:
                return TranslationResult(
                    text="",
                    model=self.MODEL_NAME,
                    error="API quota exceeded. Please try again later.",
                )
            elif "deadline" in error_msg or "timeout" in error_msg:
                return TranslationResult(
                    text="",
                    model=self.MODEL_NAME,
                    error="Request timed out. Please check your connection.",
                )
            else:
                return TranslationResult(
                    text="",
                    model=self.MODEL_NAME,
                    error=f"Translation failed: {str(e)}",
                )
