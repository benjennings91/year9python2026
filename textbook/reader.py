"""Public, read-only pages: contents, chapters and the exercise playgrounds."""

from flask import Blueprint, abort, render_template

from .models import Chapter, Section, db

bp = Blueprint("reader", __name__)


@bp.route("/")
def index():
    chapters = db.session.scalars(
        db.select(Chapter).order_by(Chapter.position)
    ).all()
    return render_template("index.html", chapters=chapters)


@bp.route("/chapter/<slug>")
def chapter(slug):
    chapter = db.one_or_404(db.select(Chapter).where(Chapter.slug == slug))
    return render_template("chapter.html", chapter=chapter)


@bp.route("/playground/<int:section_id>")
def playground(section_id):
    section = db.get_or_404(Section, section_id)
    if not section.is_exercise:
        abort(404)      # text sections have nothing to run
    return render_template("playground.html", section=section)
