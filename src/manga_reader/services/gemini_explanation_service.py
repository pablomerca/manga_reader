"""Gemini Explanation Service - Provides sentence-level explanations via Google Gemini API."""

import time

import google.genai as genai
from google.genai import types

from manga_reader.services.explanation_service import ExplanationService, ExplanationResult


class GeminiExplanationService(ExplanationService):
    """Explanation service using Google Gemini API.

    Mirrors error handling and tuning used for translation to keep behavior predictable.
    """

    MODEL_NAME = "gemini-2.0-flash"

    PROMPT_TEMPLATE = """You are a Japanese language tutor explaining a sentence to an English learner.

Original Japanese: {original_jp}
English Translation: {translation_en}

[Instruction]
Provide a short, concise explanation covering:

1. **Semantic Parsing** — If the sentence contains uncommon grammar or complex structure, briefly explain the grammatical pattern and how it contributes to meaning.
2. **Standard Form Suggestion (optional)** — Suggest the most common/standard way to express the same idea in conversational Japanese (for use in Jmdict-style lookups). Only if strictly relevant.
3. **Idioms & Cultural Notes (optional)** — Explain any idioms, cultural references, or pragmatic nuances that a literal translation might miss. Only include if relevant.

Focus on what a learner would not immediately understand from the translation alone.
Keep your response very concise and short, avoid redundancy and fillers.
"""

    def explain(self, original_jp: str, translation_en: str, api_key: str) -> ExplanationResult:
        """Generate a guided explanation grounded in translation context."""
        max_retries = 3
        retry_delay = 2  # Start with 2 seconds
        attempt = 0
        
        while attempt < max_retries:
            attempt += 1
            try:
                client = genai.Client(api_key=api_key)

                prompt = self.PROMPT_TEMPLATE.format(
                    original_jp=original_jp,
                    translation_en=translation_en,
                )

                # Debug: Log the prompt and request details
                from datetime import datetime
                print(f"\n[EXPLANATION REQUEST DEBUG]")
                print(f"Attempt: {attempt}/{max_retries}")
                print(f"Model: {self.MODEL_NAME}")
                print(f"Original JP: {repr(original_jp[:100])}" + ("..." if len(original_jp) > 100 else ""))
                print(f"Translation EN: {repr(translation_en[:100])}" + ("..." if len(translation_en) > 100 else ""))
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
                    return ExplanationResult(
                        text=None,
                        model=self.MODEL_NAME,
                        error="Empty response from API",
                    )

                from datetime import datetime
                print(f"[EXPLANATION SUCCESS] Response received on attempt {attempt}")
                print(f"Response length: {len(response.text)} chars")
                print(f"Timestamp: {datetime.now().isoformat()}")
                print(f"{'-' * 50}\n")

                return ExplanationResult(
                    text=response.text.strip(),
                    model=self.MODEL_NAME,
                    error=None,
                )

            except Exception as exc:  # pragma: no cover - defensive classification
                error_msg = str(exc).lower()

                # Debug: Log the full exception details
                from datetime import datetime
                print(f"\n[EXPLANATION ERROR DEBUG]")
                print(f"Attempt: {attempt}/{max_retries}")
                print(f"Exception type: {type(exc).__name__}")
                print(f"Full error message: {str(exc)}")
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
                    return ExplanationResult(
                        text=None,
                        model=self.MODEL_NAME,
                        error=f"Invalid API key or request: {exc}",
                    )
                if is_rate_limit:
                    return ExplanationResult(
                        text=None,
                        model=self.MODEL_NAME,
                        error="API quota exceeded. Please try again later.",
                    )
                if "deadline" in error_msg or "timeout" in error_msg:
                    return ExplanationResult(
                        text=None,
                        model=self.MODEL_NAME,
                    error="Request timed out. Please check your connection.",
                )

            return ExplanationResult(
                text=None,
                model=self.MODEL_NAME,
                error=f"Explanation failed: {exc}",
            )
