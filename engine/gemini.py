"""Gemini (безкоштовний API, flash-lite) з ротацією кількох ключів.

Ключі: GEMINI_API_KEY, GEMINI_API_KEY_2, GEMINI_API_KEY_3 ... у Secrets.
Модель: GEMINI_MODEL (за замовчуванням gemini-flash-lite-latest).
"""
from __future__ import annotations

import json
import os
import time

import requests

from .common import env_list, log

API = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
MIN_INTERVAL = float(os.environ.get("GEMINI_MIN_INTERVAL", "4.5"))  # ~13 запитів/хв на ключ


class QuotaExhausted(Exception):
    """Усі ключі вперлися в ліміт — зупиняємо прогін, продовжимо наступного разу."""


class Gemini:
    _instance: "Gemini | None" = None

    @classmethod
    def get(cls) -> "Gemini":
        # один екземпляр на процес
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        self.keys = env_list("GEMINI_API_KEY")
        if not self.keys:
            raise RuntimeError("Немає GEMINI_API_KEY у Secrets")
        self.model = os.environ.get("GEMINI_MODEL", "gemini-flash-lite-latest")
        self.dead: set[int] = set()
        self.last_call: dict[int, float] = {}
        self.idx = 0
        self.session = requests.Session()
        self.calls = 0

    def _next_key(self) -> int:
        for _ in range(len(self.keys)):
            i = self.idx % len(self.keys)
            self.idx += 1
            if i not in self.dead:
                return i
        raise QuotaExhausted("усі ключі Gemini у ліміті")

    def json(self, prompt: str, temperature: float = 0.6) -> dict:
        body = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "responseMimeType": "application/json",
                "maxOutputTokens": 16384,
            },
        }
        attempts = 0
        while True:
            attempts += 1
            i = self._next_key()
            wait = MIN_INTERVAL - (time.time() - self.last_call.get(i, 0))
            if wait > 0:
                time.sleep(wait)
            self.last_call[i] = time.time()
            r = self.session.post(
                API.format(model=self.model),
                params={"key": self.keys[i]},
                json=body,
                timeout=120,
            )
            self.calls += 1
            if r.status_code == 429:
                log(f"gemini: ключ #{i + 1} у ліміті (429)")
                self.dead.add(i)
                continue
            if r.status_code >= 500 and attempts < 4:
                log(f"gemini: {r.status_code}, повтор")
                time.sleep(5 * attempts)
                continue
            if r.status_code != 200:
                raise RuntimeError(f"gemini HTTP {r.status_code}: {r.text[:300]}")
            data = r.json()
            try:
                text = data["candidates"][0]["content"]["parts"][0]["text"]
            except (KeyError, IndexError) as e:
                raise RuntimeError(f"gemini: порожня відповідь {json.dumps(data)[:300]}") from e
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                if attempts < 3:
                    log("gemini: битий JSON, повтор")
                    continue
                raise
