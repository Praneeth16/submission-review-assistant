from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass


_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL | re.IGNORECASE)


class GeminiClientError(RuntimeError):
    pass


@dataclass
class GeminiResponse:
    text: str
    raw: dict


class GeminiClient:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.model = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")
        self.api_base = os.getenv(
            "GEMINI_API_BASE",
            "https://generativelanguage.googleapis.com/v1beta/models",
        )

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def generate_json(
        self,
        prompt: str,
        *,
        tools: list[dict] | None = None,
        temperature: float = 0.2,
    ) -> dict:
        response = self.generate_text(
            prompt,
            tools=tools,
            temperature=temperature,
            response_mime_type="application/json",
        )
        return self._parse_json(response.text)

    def generate_text(
        self,
        prompt: str,
        *,
        tools: list[dict] | None = None,
        temperature: float = 0.2,
        response_mime_type: str | None = None,
    ) -> GeminiResponse:
        if not self.configured:
            raise GeminiClientError("GEMINI_API_KEY is not configured")

        body: dict = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": temperature},
        }
        if response_mime_type:
            body["generationConfig"]["responseMimeType"] = response_mime_type
        if tools:
            body["tools"] = tools

        request = urllib.request.Request(
            f"{self.api_base}/{self.model}:generateContent",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": self.api_key or "",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise GeminiClientError(f"Gemini HTTP error {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise GeminiClientError(f"Gemini request failed: {exc}") from exc

        text = self._extract_text(payload)
        return GeminiResponse(text=text, raw=payload)

    def _extract_text(self, payload: dict) -> str:
        candidates = payload.get("candidates") or []
        if not candidates:
            raise GeminiClientError("Gemini returned no candidates")

        parts = candidates[0].get("content", {}).get("parts", [])
        text_parts = [part.get("text", "") for part in parts if part.get("text")]
        if not text_parts:
            raise GeminiClientError("Gemini returned no text parts")
        return "\n".join(text_parts).strip()

    def _parse_json(self, text: str) -> dict:
        # Fast path: already valid JSON.
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Fenced block ```json { ... } ```.
        match = _JSON_FENCE_RE.search(text)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        # Last resort: first "{" through matching last "}". Fragile, keep narrow.
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError as exc:
                raise GeminiClientError(
                    f"Gemini returned text that looked like JSON but failed to parse: {exc}"
                ) from exc
        raise GeminiClientError("Gemini did not return valid JSON")
