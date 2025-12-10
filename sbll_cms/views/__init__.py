from __future__ import annotations

from flask import Flask

from sbll_cms.views.blueprints import glosses_bp, htmx_bp, settings_bp, situations_bp, tools_bp


def register_views(app: Flask) -> None:
    # Import routes so decorators attach to blueprints.
    from sbll_cms.views import (
        gloss_create,
        gloss_delete,
        gloss_edit,
        gloss_new,
        gloss_update,
        gloss_relation_add_htmx,
        gloss_relation_detach_htmx,
        gloss_relations_table_htmx,
        gloss_suggest_htmx,
        list_glosses,
        list_situations,
        gloss_manage_as_situation,
        export_situation,
        batch_export_situations,
        settings_api_get,
        settings_api_update,
        settings_page,
        tool_break_up_glosses,
        tool_create_situation,
        tool_missing_translations,
        tool_missing_target_translations,
        tool_missing_usage_examples,
        tool_translation,
        tool_translation_comparison,
    )  # noqa: F401

    app.register_blueprint(glosses_bp)
    app.register_blueprint(htmx_bp, url_prefix="/htmx")
    app.register_blueprint(settings_bp, url_prefix="/settings")
    app.register_blueprint(situations_bp)
    app.register_blueprint(tools_bp, url_prefix="/tools")
