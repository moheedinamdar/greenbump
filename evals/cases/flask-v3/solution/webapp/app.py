from urllib.parse import quote

from flask import Flask, request
from markupsafe import Markup, escape


def create_app():
    app = Flask(__name__)

    @app.get("/hello")
    def hello():
        name = request.args.get("name", "world")
        return Markup("<h1>Hello, {}!</h1>").format(name)

    @app.get("/link")
    def link():
        query = request.args.get("q", "")
        return f'<a href="/search?q={quote(query)}">{escape(query)}</a>'

    return app
