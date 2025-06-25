from flask import Flask, request

from hazmate.redirect_server.config import PORT

app = Flask(__name__)


@app.route("/")
def callback():
    code = request.args.get("code")
    return f"Authorization code: {code}", 200


if __name__ == "__main__":
    app.run(port=PORT)
