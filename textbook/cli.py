"""Command-line commands: `flask --app app <command>`."""

import secrets
from pathlib import Path

import click
from flask import current_app
from flask.cli import with_appcontext
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash

from .models import Chapter, Section, db


def register(app):
    app.cli.add_command(init_db)
    app.cli.add_command(fake_content)
    app.cli.add_command(set_password)


@click.command("init-db")
@with_appcontext
def init_db():
    """Drop and recreate all tables from the models."""
    db.drop_all()
    db.create_all()
    click.echo("Database initialised")


@click.command("set-password")
@click.password_option(help="The admin password (prompted if omitted).")
@with_appcontext
def set_password(password):
    """Set the admin password, writing instance/config.py."""
    config_path = Path(current_app.instance_path) / "config.py"

    # Keep any other settings already in the file, and the existing
    # SECRET_KEY so that current sessions survive a password change.
    kept = []
    secret_key = None
    if config_path.exists():
        for line in config_path.read_text().splitlines():
            if line.startswith("SECRET_KEY"):
                secret_key = line.split("=", 1)[1].strip().strip("'\"")
            elif not line.startswith("ADMIN_PASSWORD_HASH"):
                kept.append(line)
    secret_key = secret_key or secrets.token_hex(32)

    config_path.write_text(
        "\n".join(kept + [
            f"SECRET_KEY = {secret_key!r}",
            f"ADMIN_PASSWORD_HASH = {generate_password_hash(password)!r}",
        ]) + "\n"
    )
    click.echo(f"Password saved to {config_path}")


@click.command("fake-content")
@with_appcontext
def fake_content():
    """Add sample chapters for testing."""
    hello = Chapter(
        slug="hello",
        title="Chapter 1: Hello, Python",
        position=1,
        sections=[
            Section(
                position=1,
                kind="text",
                body=(
                    "Python is a language for telling the computer what to do, "
                    "one instruction at a time. In this book you will write real "
                    "Python in the boxes below and run it right here in the page.\n\n"
                    "The first thing every programmer learns is how to make the "
                    "computer say something."
                ),
            ),
            Section(
                position=2,
                kind="exercise",
                body="The `print()` function writes text to the screen. Press **Run** to try it.",
                starting_code='print("Hello, world!")',
                size="mini",
            ),
            Section(
                position=3,
                kind="exercise",
                body="You can print more than one thing. Change the message below, then run it.",
                starting_code='print("Python is")\nprint("fun")',
                size="mini",
            ),
        ],
    )
    variables = Chapter(
        slug="variables",
        title="Chapter 2: Variables and Input",
        position=2,
        sections=[
            Section(
                position=1,
                kind="text",
                body=(
                    "A *variable* is a name for a value:\n\n"
                    "```python\n"
                    'name = "Ada"\n'
                    "```\n\n"
                    "stores the text `Ada` under the name `name`, and you can use "
                    "that name anywhere you would have written the text."
                ),
            ),
            Section(
                position=2,
                kind="exercise",
                body="`input()` pauses and waits for the user to type something. Complete the program so it greets the user by name.",
                starting_code='name = input("What is your name? ")\n# Add a print() that says hello to them\n',
                size="large",
            ),
        ],
    )
    db.session.add_all([hello, variables])
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise click.ClickException(
            "Sample content already exists. Run init-db first to start again."
        )
    click.echo("Fake content added")
