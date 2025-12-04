from __future__ import annotations

from dataclasses import dataclass, asdict
from flask import session


@dataclass
class ApiKeys:
    openai: str | None = None
    deepl: str | None = None


@dataclass
class Settings:
    api_keys: ApiKeys

    @classmethod
    def default(cls) -> "Settings":
        return cls(api_keys=ApiKeys())

    def to_dict(self) -> dict:
        return {"api_keys": asdict(self.api_keys)}

    @classmethod
    def from_dict(cls, data: dict) -> "Settings":
        api_data = data.get("api_keys", {}) if data else {}
        return cls(api_keys=ApiKeys(openai=api_data.get("openai"), deepl=api_data.get("deepl")))


class SettingsStore:
    def load(self) -> Settings:
        settings_data = session.get("settings", {})
        return Settings.from_dict(settings_data)

    def save(self, settings: Settings) -> None:
        session["settings"] = settings.to_dict()

