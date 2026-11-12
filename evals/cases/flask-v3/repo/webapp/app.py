from flask import Flask, Markup, escape, request
from werkzeug.urls import url_quote


def create_app():
    app = Flask(__name__)

    @app.get("/hello")
    def hello():
        name = request.args.get("name", "world")
        return Markup("<h1>Hello, {}!</h1>").format(name)

    @app.get("/link")
    def link():
        query = request.args.get("q", "")
        return f'<a href="/search?q={url_quote(query)}">{escape(query)}</a>'

    return app
