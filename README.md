# Interactive Python textbook

Chapters of Markdown prose interleaved with runnable Python exercises
(PyScript/MicroPython in the browser), with a password-protected authoring
interface at `/admin`.

## First run

```
pip install -r requirements.txt
flask --app app init-db          # create the tables (wipes any existing data)
flask --app app set-password     # choose the admin password
flask --app app fake-content     # optional sample chapters
flask --app app run --debug
```

Then open http://127.0.0.1:5000/ and http://127.0.0.1:5000/admin.

## Layout

```
app.py                 entry point
textbook/
  __init__.py          create_app(): config, blueprints, markdown filter, headers
  models.py            Chapter, Section
  reader.py            public pages
  admin.py             authoring pages (login, chapters, sections, live preview)
  cli.py               init-db, set-password, fake-content
  templates/
  static/
instance/              created at runtime, not committed:
  textbook.db          the database
  config.py            SECRET_KEY and ADMIN_PASSWORD_HASH
```

## Deploying

The app needs `SECRET_KEY` and `ADMIN_PASSWORD_HASH`. Either run
`set-password` on the server (writes `instance/config.py`) or set the
environment variables `FLASK_SECRET_KEY` and `FLASK_ADMIN_PASSWORD_HASH`.
Serve it over HTTPS and set `FLASK_SESSION_COOKIE_SECURE=true`.
