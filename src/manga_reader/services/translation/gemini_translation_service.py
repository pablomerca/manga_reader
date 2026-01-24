"""Gemini Translation Service - Implements translation via Google Gemini API."""

import time
from datetime import datetime

import google.genai as genai
from google.genai import types

from manga_reader.services.translation.translation_service import TranslationResult, TranslationService


class GeminiTranslationService(TranslationService):
    """
    Translation service using Google Gemini API.

    Optimized for speed and consistency with lower temperature settings.
    Uses the new google.genai package (maintained actively).
    """

    MODEL_NAME = "gemini-2.0-flash"

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
        max_retries = 3
        retry_delay = 2  # Start with 2 seconds
        attempt = 0
        
        while attempt < max_retries:
            attempt += 1
            try:
                client = genai.Client(api_key=api_key)
                
                prompt = self.TRANSLATION_PROMPT.format(text=text)
                
                # Debug: Log the prompt and request details
                print(f"\n[TRANSLATION REQUEST DEBUG]")
                print(f"Attempt: {attempt}/{max_retries}")
                print(f"Model: {self.MODEL_NAME}")
                print(f"Input text: {repr(text[:100])}" + ("..." if len(text) > 100 else ""))
                print(f"Full prompt:\n{prompt}")
                print(f"Timestamp: {datetime.now().isoformat()}")
                print(f"API Key (first 20 chars): {api_key[:20]}...")
                print(f"{'-' * 50}")
                
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
                
                print(f"[TRANSLATION SUCCESS] Response received on attempt {attempt}")
                print(f"Response length: {len(response.text)} chars")
                print(f"Timestamp: {datetime.now().isoformat()}")
                print(f"{'-' * 50}\n")
                
                return TranslationResult(
                    text=response.text.strip(),
                    model=self.MODEL_NAME,
                )
                
            except Exception as e:
                error_msg = str(e).lower()
                
                # Debug: Log the full exception details
                print(f"\n[TRANSLATION ERROR DEBUG]")
                print(f"Attempt: {attempt}/{max_retries}")
                print(f"Exception type: {type(e).__name__}")
                print(f"Full error message: {str(e)}")
                print(f"Error lowercase: {error_msg}")
                print(f"Timestamp: {datetime.now().isoformat()}")
                
                # Check if it's a 429 rate limit error
                is_rate_limit = ("429" in error_msg or "resource_exhausted" in error_msg or "quota" in error_msg or "rate_limit" in error_msg)
                
                if is_rate_limit and attempt < max_retries:
                    print(f"Rate limit detected. Retrying in {retry_delay} seconds...")
                    print(f"{'-' * 50}\n")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                    continue
                
                print(f"{'-' * 50}")
                
                if "api_key" in error_msg or "authentication" in error_msg or "invalid" in error_msg:
                    return TranslationResult(
                        text="",
                        model=self.MODEL_NAME,
                        error=f"Invalid API key or request: {str(e)}",
                    )
                elif is_rate_limit:
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
