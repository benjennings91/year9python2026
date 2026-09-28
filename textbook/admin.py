"""Authoring interface, mounted at /admin.

Access control is a single password. The hash lives in config
(ADMIN_PASSWORD_HASH, written by `flask set-password`); a successful login
sets session["admin"]. Every request to this blueprint is checked in
`require_login`, so individual views don't need a decorator.

Every POST is also checked for a CSRF token: a random value stored in the
session and echoed back as a hidden form field, so a form on another site
can't submit here on the admin's behalf.
"""

import re
import secrets

from flask import (
    Blueprint, abort, flash, redirect, render_template, request, session,
    url_for,
)
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash

from flask import current_app

from .models import Chapter, Section, db

bp = Blueprint("admin", __name__, url_prefix="/admin")


# --- Access control -----------------------------------------------------------

@bp.before_request
def require_login():
    if request.endpoint == "admin.login":
        return None
    if not session.get("admin"):
        return redirect(url_for("admin.login", next=request.path))
    if request.method == "POST":
        token = session.get("csrf_token")
        if not token or not secrets.compare_digest(token, request.form.get("csrf_token", "")):
            abort(400, "Invalid or missing CSRF token")
    return None


@bp.app_context_processor
def inject_csrf_token():
    """Make csrf_token() available in every template."""
    def csrf_token():
        if "csrf_token" not in session:
            session["csrf_token"] = secrets.token_hex(16)
        return session["csrf_token"]
    return {"csrf_token": csrf_token, "is_admin": session.get("admin", False)}


@bp.route("/login", methods=["GET", "POST"])
def login():
    password_hash = current_app.config.get("ADMIN_PASSWORD_HASH")
    if not password_hash:
        return render_template("admin/login.html", not_configured=True)

    if request.method == "POST":
        if check_password_hash(password_hash, request.form.get("password", "")):
            session.clear()
            session["admin"] = True
            next_url = request.args.get("next", "")
            if not next_url.startswith("/"):        # only allow local redirects
                next_url = url_for("admin.chapters")
            return redirect(next_url)
        flash("Wrong password.", "danger")

    return render_template("admin/login.html")


@bp.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("reader.index"))


# --- Helpers ------------------------------------------------------------------

def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def move(items, item, direction):
    """Move `item` one place up or down within `items` and renumber positions."""
    items = list(items)
    i = items.index(item)
    j = i - 1 if direction == "up" else i + 1
    if 0 <= j < len(items):
        items.insert(j, items.pop(i))
    for position, it in enumerate(items, start=1):
        it.position = position


def section_from_form(form, section):
    """Copy validated form fields onto `section`."""
    kind = form.get("kind", "exercise")
    size = form.get("size", "large")
    if kind not in Section.KINDS or size not in Section.SIZES:
        abort(400, "Invalid kind or size")
    section.kind = kind
    section.size = size
    section.body = form.get("body", "")
    section.starting_code = form.get("starting_code", "")
    return section


# --- Chapters -----------------------------------------------------------------

@bp.route("/")
def chapters():
    chapters = db.session.scalars(
        db.select(Chapter).order_by(Chapter.position)
    ).all()
    return render_template("admin/chapters.html", chapters=chapters)


@bp.post("/chapter")
def create_chapter():
    title = request.form.get("title", "").strip()
    if not title:
        flash("A chapter needs a title.", "danger")
        return redirect(url_for("admin.chapters"))
    slug = request.form.get("slug", "").strip() or slugify(title)
    count = db.session.scalar(db.select(db.func.count(Chapter.id)))
    chapter = Chapter(title=title, slug=slug, position=count + 1)
    db.session.add(chapter)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash(f"The slug '{slug}' is already in use.", "danger")
        return redirect(url_for("admin.chapters"))
    return redirect(url_for("admin.chapter", chapter_id=chapter.id))


@bp.route("/chapter/<int:chapter_id>", methods=["GET", "POST"])
def chapter(chapter_id):
    chapter = db.get_or_404(Chapter, chapter_id)
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        slug = request.form.get("slug", "").strip()
        if not title or not slug:
            flash("Title and slug are both required.", "danger")
        else:
            chapter.title, chapter.slug = title, slug
            try:
                db.session.commit()
                flash("Chapter saved.", "success")
            except IntegrityError:
                db.session.rollback()
                flash(f"The slug '{slug}' is already in use.", "danger")
        return redirect(url_for("admin.chapter", chapter_id=chapter.id))
    return render_template("admin/chapter.html", chapter=chapter)


@bp.post("/chapter/<int:chapter_id>/delete")
def delete_chapter(chapter_id):
    chapter = db.get_or_404(Chapter, chapter_id)
    db.session.delete(chapter)           # cascades to its sections
    db.session.commit()
    flash(f"Deleted '{chapter.title}'.", "success")
    return redirect(url_for("admin.chapters"))


@bp.post("/chapter/<int:chapter_id>/move/<direction>")
def move_chapter(chapter_id, direction):
    chapter = db.get_or_404(Chapter, chapter_id)
    chapters = db.session.scalars(
        db.select(Chapter).order_by(Chapter.position)
    ).all()
    move(chapters, chapter, direction)
    db.session.commit()
    return redirect(url_for("admin.chapters"))


# --- Sections -----------------------------------------------------------------

@bp.route("/chapter/<int:chapter_id>/section/new", methods=["GET", "POST"])
def new_section(chapter_id):
    chapter = db.get_or_404(Chapter, chapter_id)
    section = Section(kind="exercise", size="large", body="", starting_code="")
    if request.method == "POST":
        section_from_form(request.form, section)
        section.position = len(chapter.sections) + 1
        chapter.sections.append(section)
        db.session.commit()
        flash("Section added.", "success")
        return redirect(url_for("admin.chapter", chapter_id=chapter.id))
    return render_template("admin/section_form.html", chapter=chapter, section=section)


@bp.route("/section/<int:section_id>", methods=["GET", "POST"])
def section(section_id):
    section = db.get_or_404(Section, section_id)
    if request.method == "POST":
        section_from_form(request.form, section)
        db.session.commit()
        flash("Section saved.", "success")
        return redirect(url_for("admin.chapter", chapter_id=section.chapter_id))
    return render_template(
        "admin/section_form.html", chapter=section.chapter, section=section
    )


@bp.post("/section/<int:section_id>/delete")
def delete_section(section_id):
    section = db.get_or_404(Section, section_id)
    chapter_id = section.chapter_id
    db.session.delete(section)
    db.session.commit()
    flash("Section deleted.", "success")
    return redirect(url_for("admin.chapter", chapter_id=chapter_id))


@bp.post("/section/<int:section_id>/move/<direction>")
def move_section(section_id, direction):
    section = db.get_or_404(Section, section_id)
    move(section.chapter.sections, section, direction)
    db.session.commit()
    return redirect(url_for("admin.chapter", chapter_id=section.chapter_id))


@bp.post("/preview")
def preview():
    """Render a section from unsaved form data, for the editor's live preview.

    The section object is built but never added to the session, so nothing
    is written. For an exercise, the playground is rendered here too and
    embedded via srcdoc, since it has no database row to load from.
    """
    section = section_from_form(request.form, Section())
    playground_html = None
    if section.is_exercise:
        playground_html = render_template(
            "playground.html", section=section, preview=True
        )
    return render_template(
        "admin/preview.html", section=section, playground_html=playground_html
    )
