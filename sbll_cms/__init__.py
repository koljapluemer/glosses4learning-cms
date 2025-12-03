from __future__ import annotations

from flask import Flask

from .config import Config
from .storage import GlossStorage
from .views import bp as glosses_bp


def create_app(config_class: type[Config] = Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)

    storage = GlossStorage(app.config["DATA_ROOT"])
    app.extensions["gloss_storage"] = storage

    app.register_blueprint(glosses_bp)
    return app


# Convenience for `flask --app sbll_cms run`
app = create_app()
