import json
import logging
import re
import threading
import time

from google.api_core.exceptions import ResourceExhausted

from app.config import settings

# Rate limiter disabled - user has 2000 RPM quota
_rate_limiter_lock = threading.Lock()
_last_request_time = 0.0
_min_interval = 0.0  # No rate limiting needed

logger = logging.getLogger(__name__)


class LLMService:
    def __init__(self) -> None:
        self.provider = settings.LLM_PROVIDER.lower()

        if self.provider == "gemini":
            import google.generativeai as genai
            genai.configure(api_key=settings.GEMINI_API_KEY)
            model_name = settings.GEMINI_MODEL
            if not model_name.startswith("models/"):
                model_name = f"models/{model_name}"
            logger.info("Initializing Gemini with model: %s", model_name)
            self.model = genai.GenerativeModel(model_name)
        else:
            from openai import OpenAI
            self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
            self.openai_model = settings.OPENAI_MODEL

    def generate_json(self, system_prompt: str, user_payload: dict) -> dict:
        if self.provider == "gemini":
            return self._generate_gemini(system_prompt, user_payload)
        else:
            return self._generate_openai(system_prompt, user_payload)

    def _rate_limit_wait(self) -> None:
        """Wait if necessary to respect rate limits."""
        global _last_request_time
        with _rate_limiter_lock:
            now = time.time()
            elapsed = now - _last_request_time
            if elapsed < _min_interval:
                wait_time = _min_interval - elapsed
                logger.debug("Rate limiting: waiting %.1fs", wait_time)
                time.sleep(wait_time)
            _last_request_time = time.time()

    def _generate_gemini(
        self, system_prompt: str, user_payload: dict, max_retries: int = 5
    ) -> dict:
        prompt = f"{system_prompt}\n\nInput:\n{json.dumps(user_payload, ensure_ascii=False)}"
        text = ""

        for attempt in range(max_retries):
            try:
                # Apply rate limiting
                self._rate_limit_wait()

                response = self.model.generate_content(
                    prompt,
                    generation_config={
                        "temperature": 0.7,
                        "response_mime_type": "application/json",
                    },
                )

                text = response.text
                if not text:
                    logger.warning("Gemini response was empty")
                    return {}

                return json.loads(text)

            except ResourceExhausted as e:
                wait_time = 2 ** (attempt + 1)
                logger.warning(
                    "Gemini rate limit (429), retry %d/%d in %ds",
                    attempt + 1,
                    max_retries,
                    wait_time,
                )
                if attempt < max_retries - 1:
                    time.sleep(wait_time)
                else:
                    logger.error("Gemini rate limit exceeded after %d retries", max_retries)
                    return {}

            except json.JSONDecodeError as e:
                logger.error("Invalid JSON from Gemini: %s", e)
                return self._try_extract_json(text) if text else {}

            except Exception as e:
                logger.exception("Gemini API error: %s", e)
                return {}

        return {}

    def _generate_openai(self, system_prompt: str, user_payload: dict) -> dict:
        try:
            response = self.client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
                ],
                temperature=0.7,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            if not content:
                logger.warning("OpenAI response was empty")
                return {}

            return json.loads(content)

        except json.JSONDecodeError as e:
            logger.error("Invalid JSON from OpenAI: %s", e)
            return self._try_extract_json(content) if content else {}

        except Exception as e:
            logger.exception("OpenAI API error: %s", e)
            return {}

    def _try_extract_json(self, text: str) -> dict:
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return {}
