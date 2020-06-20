import logging
import os
from functools import wraps
from io import BytesIO
from pathlib import Path

from flask import Flask, abort, jsonify, request, send_file

from .bencode import bdecode
from .clients import parse_libtc_url
from .exceptions import FailedToExecuteException

logger = logging.getLogger(__name__)

app = Flask(__name__)


def get_client():
    return parse_libtc_url(os.environ["LILTORRENT_CLIENT"])


def require_apikey(view_function):
    @wraps(view_function)
    def decorated_function(*args, **kwargs):
        apikey = os.environ["LILTORRENT_APIKEY"]
        if apikey and request.headers.get("authorization") == f"Bearer {apikey}":
            return view_function(*args, **kwargs)
        else:
            abort(401)

    return decorated_function


def handle_exception(view_function):
    @wraps(view_function)
    def decorated_function(*args, **kwargs):
        try:
            return view_function(*args, **kwargs)
        except FailedToExecuteException as e:
            logger.exception("Failed to handle request")
            return jsonify(e.args), 500

    return decorated_function


@app.route("/list")
@require_apikey
def list():
    client = get_client()
    return jsonify([t.serialize() for t in client.list()])


@app.route("/list_active")
@require_apikey
def list_active():
    client = get_client()
    return jsonify([t.serialize() for t in client.list_active()])


@app.route("/start", methods=["POST"])
@require_apikey
def start():
    client = get_client()
    client.start(request.args.get("infohash"))
    return jsonify({})


@app.route("/stop", methods=["POST"])
@require_apikey
def stop():
    client = get_client()
    client.stop(request.args.get("infohash"))
    return jsonify({})


@app.route("/test_connection")
@require_apikey
def test_connection():
    client = get_client()
    return jsonify(client.test_connection())


@app.route("/add", methods=["POST"])
@require_apikey
def add():
    client = get_client()
    destination_path = Path(request.args.get("destination_path"))
    fast_resume = request.args.get("fast_resume") == "true"
    add_name_to_folder = request.args.get("add_name_to_folder") == "true"
    stopped = request.args.get("stopped") == "true"
    torrent = bdecode(request.files["torrent"].read())
    client.add(
        torrent,
        destination_path,
        fast_resume=fast_resume,
        add_name_to_folder=add_name_to_folder,
        minimum_expected_data=request.args.get("minimum_expected_data"),
        stopped=stopped,
    )
    return jsonify({})


@app.route("/remove", methods=["POST"])
@require_apikey
def remove():
    client = get_client()
    client.remove(request.args.get("infohash"))
    return jsonify({})


@app.route("/retrieve_torrentfile")
@require_apikey
def retrieve_torrentfile():
    client = get_client()
    infohash = request.args.get("infohash")
    torrent_file = BytesIO(client.retrieve_torrentfile(infohash))
    return send_file(
        torrent_file,
        mimetype="application/x-bittorrent",
        as_attachment=True,
        attachment_filename=f"{infohash}.torrent",
    )


@app.route("/get_download_path")
@require_apikey
def get_download_path():
    client = get_client()
    return jsonify(str(client.get_download_path(request.args.get("infohash"))))


@app.route("/get_files")
@require_apikey
def get_files():
    client = get_client()
    return jsonify(
        [t.serialize() for t in client.get_files(request.args.get("infohash"))]
    )


def cli():
    try:
        port = int(os.environ.get("LILTORRENT_PORT"))
    except (ValueError, TypeError):
        port = 10977
    import waitress

    waitress.serve(app, port=port, url_scheme="http")


if __name__ == "__main__":
    cli()
