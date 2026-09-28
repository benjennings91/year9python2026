"""Database models."""

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Chapter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.Text, unique=True, nullable=False)   # used in URLs
    title = db.Column(db.Text, nullable=False)
    position = db.Column(db.Integer, nullable=False, default=0)

    sections = db.relationship(
        "Section",
        back_populates="chapter",
        order_by="Section.position",
        cascade="all, delete-orphan",
    )


class Section(db.Model):
    """One block of a chapter: either prose ('text') or an 'exercise'.

    `body` is Markdown. For a text section only `body` is used;
    `starting_code` and `size` sit at their defaults and are ignored.
    """

    KINDS = ("text", "exercise")
    SIZES = ("large", "mini")

    __table_args__ = (
        db.CheckConstraint("kind IN ('text', 'exercise')"),
        db.CheckConstraint("size IN ('large', 'mini')"),
    )

    id = db.Column(db.Integer, primary_key=True)
    chapter_id = db.Column(
        db.Integer,
        db.ForeignKey("chapter.id", ondelete="CASCADE"),
        nullable=False,
    )
    position = db.Column(db.Integer, nullable=False, default=0)
    kind = db.Column(db.Text, nullable=False, default="exercise")
    body = db.Column(db.Text, nullable=False, default="")
    starting_code = db.Column(db.Text, nullable=False, default="")
    size = db.Column(db.Text, nullable=False, default="large")

    chapter = db.relationship("Chapter", back_populates="sections")

    @property
    def is_exercise(self):
        return self.kind == "exercise"
