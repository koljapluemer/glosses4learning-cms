from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path


SETTINGS_FILE = "settings.json"


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
    def __init__(self, data_root: Path):
        self.path = Path(data_root) / SETTINGS_FILE
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> Settings:
        if not self.path.exists():
            return Settings.default()
        with self.path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return Settings.from_dict(data)

    def save(self, settings: Settings) -> None:
        with self.path.open("w", encoding="utf-8") as handle:
            json.dump(settings.to_dict(), handle, indent=2)

