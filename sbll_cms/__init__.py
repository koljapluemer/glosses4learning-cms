from __future__ import annotations

from flask import Flask

from .config import Config
from .language import LanguageStore
from .storage import GlossStorage
from .views import bp as glosses_bp
from .views_htmx import bp as htmx_bp


def create_app(config_class: type[Config] = Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)

    storage = GlossStorage(app.config["DATA_ROOT"])
    app.extensions["gloss_storage"] = storage
    language_store = LanguageStore(storage.data_root / "language")
    app.extensions["language_store"] = language_store

    app.register_blueprint(glosses_bp)
    app.register_blueprint(htmx_bp, url_prefix="/htmx")
    return app


# Convenience for `flask --app sbll_cms run`
app = create_app()
