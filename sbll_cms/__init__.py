from __future__ import annotations

from flask import Flask

from sbll_cms.config import Config
from sbll_cms.entities.language import LanguageStore
from sbll_cms.settings import SettingsStore
from sbll_cms.storage import GlossStorage
from sbll_cms.utils import filter_translations, paraphrase_display
from sbll_cms.views import register_views


def create_app(config_class: type[Config] = Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)

    storage = GlossStorage(app.config["DATA_ROOT"])
    app.extensions["gloss_storage"] = storage
    language_store = LanguageStore(storage.data_root / "language")
    app.extensions["language_store"] = language_store
    settings_store = SettingsStore()
    app.extensions["settings_store"] = settings_store

    app.jinja_env.filters["paraphrase"] = paraphrase_display
    app.jinja_env.filters["filter_translations"] = filter_translations

    register_views(app)
    return app


# Convenience for `flask --app sbll_cms run`
app = create_app()
