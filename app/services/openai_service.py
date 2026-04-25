import json
import logging
import re

from openai import OpenAI

from app.config import settings

logger = logging.getLogger(__name__)


class OpenAIService:
    def __init__(self) -> None:
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL

    def generate_json(self, system_prompt: str, user_payload: dict) -> dict:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
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
            logger.error("Invalid JSON from model: %s", e)
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
