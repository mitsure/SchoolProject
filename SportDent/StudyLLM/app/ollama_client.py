from __future__ import annotations

import ipaddress
import json
import socket
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from .extractor import BASE_DIR
from .models import FIELD_NAMES


class OllamaClient:
    provider = "ollama-local"

    def __init__(self, model: str, base_url: str = "http://127.0.0.1:11434", timeout: float = 120.0):
        if not model.strip():
            raise ValueError("Ollamaのモデル名が必要です")
        self.model = model.strip()
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._require_loopback(self.base_url)
        self.output_schema = self._load_output_schema()

    @staticmethod
    def _require_loopback(url: str) -> None:
        parsed = urlparse(url)
        if parsed.scheme != "http" or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("Ollama接続先は認証情報を含まないローカルHTTP URLだけ許可します")
        try:
            addresses = {item[4][0] for item in socket.getaddrinfo(parsed.hostname, parsed.port or 80)}
        except socket.gaierror as exc:
            raise ValueError("Ollama接続先を解決できません") from exc
        if not addresses or any(not ipaddress.ip_address(address).is_loopback for address in addresses):
            raise ValueError("Ollama接続先は127.0.0.1またはlocalhostに限定されています")

    @staticmethod
    def _load_output_schema() -> dict:
        schema = json.loads((BASE_DIR / "09_構造化出力JSONSchema.json").read_text(encoding="utf-8"))
        fields = schema["properties"]["fields"]
        return {
            "type": "object",
            "additionalProperties": False,
            "required": list(FIELD_NAMES),
            "properties": fields["properties"],
            "$defs": schema["$defs"],
        }

    def complete_json(self, system_prompt: str, user_payload: dict) -> dict:
        request_body = {
            "model": self.model,
            "stream": False,
            "think": False,
            "keep_alive": "10m",
            "format": self.output_schema,
            "options": {"temperature": 0},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
            ],
        }
        request = urllib.request.Request(
            self.base_url + "/api/chat",
            data=json.dumps(request_body, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read(2_000_001)
        except (TimeoutError, socket.timeout) as exc:
            raise TimeoutError("Ollama timeout") from exc
        except (urllib.error.URLError, urllib.error.HTTPError) as exc:
            raise RuntimeError("Ollama request failed") from exc
        if len(raw) > 2_000_000:
            raise RuntimeError("Ollama response too large")
        try:
            envelope = json.loads(raw)
            return json.loads(envelope["message"]["content"])
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise RuntimeError("Ollama response was not structured JSON") from exc
