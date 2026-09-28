"""Application factory.

Configuration is layered, later sources overriding earlier ones:

1. Defaults set here.
2. instance/config.py, which `flask set-password` writes (SECRET_KEY and
   ADMIN_PASSWORD_HASH). The instance folder is not committed to git.
3. Environment variables prefixed FLASK_, e.g. FLASK_SECRET_KEY, for hosts
   where a file is awkward.
"""

from pathlib import Path

import markdown
from flask import Flask
from markupsafe import Markup

from . import admin, cli, reader
from .models import db


def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SQLALCHEMY_DATABASE_URI="sqlite:///textbook.db",
        # Lax stops the session cookie being sent on cross-site POSTs, which
        # on its own blocks most CSRF; the admin blueprint adds a token too.
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_HTTPONLY=True,
    )
    app.config.from_pyfile("config.py", silent=True)
    app.config.from_prefixed_env()

    Path(app.instance_path).mkdir(exist_ok=True)
    db.init_app(app)

    app.register_blueprint(reader.bp)
    app.register_blueprint(admin.bp)
    cli.register(app)

    app.add_template_filter(render_markdown, "markdown")
    app.after_request(add_isolation_headers)

    return app


def render_markdown(text):
    """Jinja filter: Markdown -> HTML, trusted (only the admin writes it)."""
    html = markdown.markdown(text or "", extensions=["fenced_code", "tables"])
    return Markup(html)


# --- Cross-origin isolation ---------------------------------------------------
# PyScript's worker terminal uses SharedArrayBuffer so that input() can block
# the worker while the main thread stays responsive. Browsers only expose
# SharedArrayBuffer to "cross-origin isolated" pages, which requires these two
# headers on every document we serve (the chapter page *and* each playground
# iframe, which inherits isolation from its same-origin parent).
#
# The trade-off: with require-corp, every cross-origin resource we load must
# opt in via a CORP or CORS header. The CDNs used here (pyscript.net and
# jsdelivr) do, so this is fine. If you later add assets from a CDN that does
# not, they will be blocked, and you would switch to
#     Cross-Origin-Embedder-Policy: credentialless
# which Chrome and Firefox support and which does not require opt-in.

def add_isolation_headers(response):
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    response.headers["Cross-Origin-Embedder-Policy"] = "require-corp"
    return response
