import os
import pty
import select
import fcntl
import struct
import subprocess
import termios
import threading
import time
import signal

import typer
from loguru import logger
from flask import Flask, render_template, request, redirect, url_for, jsonify, abort
from flask_socketio import SocketIO
from flask_login import LoginManager, login_user, login_required, current_user

cli = typer.Typer()
app = Flask(__name__, static_folder="templates/assets")
app.config["SECRET_KEY"] = os.urandom(24)
socketio = SocketIO(app, cors_allowed_origins="*")
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

app.config["args"] = None
app.config["fd"] = None
app.config["pid"] = None
app.config["hist"] = ""
app.config["faillog"] = []

lock = threading.Lock()


class DummyUser:
    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return 0


@login_manager.user_loader
def load_user(_):
    return DummyUser()


@app.route("/")
def index():
    return redirect(url_for("console"))


@app.route("/console")
@login_required
def console():
    return render_template("console.html")


@app.route("/login", methods=["GET"])
def login():
    return render_template("login.html")


@app.route("/login", methods=["POST"])
def login_submit():
    password = request.form.get("password", "")
    webpass = os.environ.get("EK_WEBPASS", "")
    if not webpass:
        emsg = "Web console password not set."
    elif sum(t > time.time() - 3600 for t in app.config["faillog"][-5:]) == 5:
        emsg = "Too many login trials in one hour."
    else:
        if password == webpass:
            login_user(DummyUser())
            return redirect(request.args.get("next") or url_for("index"))
        else:
            emsg = "Wrong password."
            app.config["faillog"].append(time.time())
    return render_template("login.html", emsg=emsg)


@app.route("/healthz")
def healthz():
    return "200 OK"


@app.route("/heartbeat")
def heartbeat():
    webpass = os.environ.get("EK_WEBPASS", "")
    password = request.args.get("pass", None)
    if (not password) or (not webpass):
        return abort(403)
    if password == webpass:
        if app.config["pid"] is None:
            start({"rows": 32, "cols": 106}, auth=False)
            return jsonify({"status": "restarted", "pid": app.config["pid"]}), 201
        else:
            return jsonify({"status": "running", "pid": app.config["pid"]}), 200
    else:
        return abort(403)


@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404


@socketio.on("pty-input", namespace="/pty")
def pty_input(data):
    if not current_user.is_authenticated():
        return
    if app.config["fd"]:
        os.write(app.config["fd"], data["input"].encode())


def set_size(fd, row, col, xpix=0, ypix=0):
    logger.debug(f"Resizing pty to: {row} {col}.")
    size = struct.pack("HHHH", row, col, xpix, ypix)
    fcntl.ioctl(fd, termios.TIOCSWINSZ, size)


@socketio.on("resize", namespace="/pty")
def resize(data):
    if not current_user.is_authenticated():
        return
    if app.config["fd"]:
        set_size(app.config["fd"], data["rows"], data["cols"])


def read_and_forward_pty_output():
    max_read_bytes = 1024 * 20
    while True:
        socketio.sleep(0.01)
        if app.config["fd"]:
            (data, _, _) = select.select([app.config["fd"]], [], [], 0)
            if data:
                output = os.read(app.config["fd"], max_read_bytes).decode(errors="ignore")
                app.config["hist"] += output
                socketio.emit("pty-output", {"output": output}, namespace="/pty")


@socketio.on("connect", namespace="/pty")
def connected():
    logger.debug(f"Console connected.")


@socketio.on("disconnect", namespace="/pty")
def connected():
    logger.debug(f"Console disconnected.")


@socketio.on("embykeeper_start", namespace="/pty")
def start(data, auth=True):
    if auth and (not current_user.is_authenticated()):
        return
    with lock:
        if app.config["fd"]:
            set_size(app.config["fd"], data["rows"], data["cols"])
            socketio.emit("pty-output", {"output": app.config["hist"]}, namespace="/pty")
        else:
            (pid, fd) = pty.fork()
            if pid == 0:
                while True:
                    try:
                        p = subprocess.run(["embykeeper", *app.config["args"]])
                        if p.returncode:
                            raise RuntimeError()
                    except (KeyboardInterrupt, RuntimeError):
                        print()
                        while True:
                            try:
                                input("Embykeeper 已退出, 请按 Enter 以重新开始 ...")
                                print()
                                break
                            except KeyboardInterrupt:
                                print()
            else:
                app.config["fd"] = fd
                app.config["pid"] = pid
                logger.debug(f"Embykeeper started at: {pid}.")
                set_size(app.config["fd"], data["rows"], data["cols"])
                socketio.start_background_task(target=read_and_forward_pty_output)


@socketio.on("embykeeper_kill", namespace="/pty")
def stop():
    if not current_user.is_authenticated():
        return
    with lock:
        if app.config["pid"] is not None:
            os.kill(app.config["pid"], signal.SIGINT)
            for _ in range(50):
                try:
                    os.kill(app.config["pid"], 0)
                except OSError:
                    break
                else:
                    time.sleep(0.1)
            else:
                os.kill(app.config["pid"], signal.SIGKILL)
            app.config["fd"] = None
            app.config["pid"] = None
            app.config["hist"] = ""
            logger.debug(f"Embykeeper stopped.")


@cli.command(context_settings={"ignore_unknown_options": True, "allow_extra_args": True})
def run(
    ctx: typer.Context,
    port: int = typer.Option(1818, envvar="PORT", show_envvar=False),
    host: str = "0.0.0.0",
    debug: bool = False,
):
    app.config["args"] = ctx.args
    logger.info(f"Embykeeper webserver started at {host}:{port}.")
    socketio.run(app, port=port, host=host, debug=debug)


if __name__ == "__main__":
    cli()
