from eventlet.patcher import monkey_patch

monkey_patch()

import binascii
import base64
import re
import atexit
import os
import pty
import select
import fcntl
import struct
from subprocess import Popen, PIPE
import termios
import threading
import time
import signal

import tomlkit
import typer
from loguru import logger
from flask import Flask, render_template, request, redirect, url_for, jsonify, abort
from flask_socketio import SocketIO
from flask_login import LoginManager, login_user, login_required, current_user

from . import __version__

cli = typer.Typer()
app = Flask(__name__, static_folder="templates/assets")
app.config["SECRET_KEY"] = os.urandom(24)
socketio = SocketIO(app, cors_allowed_origins="*")
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

app.config["lock"] = threading.Lock()
app.config["args"] = []
app.config["fd"] = None
app.config["proc"] = None
app.config["hist"] = ""
app.config["faillog"] = []
app.config["config"] = os.environ.get("EK_CONFIG", "")

version = f"V{__version__}"


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


def exit_handler():
    proc = app.config["proc"]
    if proc:
        kill_proc(proc)


@app.route("/")
def index():
    return redirect(url_for("console"))


def is_authenticated():
    webpass = app.config.get("webpass", None)
    if (not webpass) or current_user.is_authenticated:
        return True
    else:
        return False


@app.route("/console")
@login_required
def console():
    return render_template("console.html", version=version)


@app.route("/login", methods=["GET"])
def login():
    return render_template("login.html", version=version)


@app.route("/login", methods=["POST"])
def login_submit():
    password = request.form.get("password", "")
    webpass = os.environ.get("EK_WEBPASS", "")
    if not webpass:
        emsg = "后台没有设置控制台密码, 无法登录."
    elif sum(t > time.time() - 3600 for t in app.config["faillog"][-5:]) == 5:
        emsg = "一小时内有过多次失败登录, 请稍后再试."
    else:
        if password == webpass:
            login_user(DummyUser())
            return redirect(request.args.get("next") or url_for("index"))
        else:
            emsg = "密码错误, 请重试."
            app.config["faillog"].append(time.time())
    return render_template("login.html", emsg=emsg, version=version)


@app.route("/config", methods=["GET"])
@login_required
def config():
    return render_template("config.html", version=version)


@app.route("/config/current", methods=["GET"])
def config_current():
    if not is_authenticated():
        return "Not authenticated", 401
    data = app.config["config"]
    if not data:
        return "Config missing", 404
    try:
        data = base64.b64decode(re.sub(r"\s+", "", data).encode()).decode()
    except binascii.Error:
        logger.error("Config string malformed.")
        return "Config malformed", 400
    if isinstance(data, bytes):
        logger.error("Config string malformed.")
        return "Config malformed", 400
    return jsonify(data), 200


@app.route("/config/example", methods=["GET"])
def config_example():
    if not is_authenticated():
        return "Not authenticated", 401
    example, _ = Popen(["embykeeper", "--example-config"], stdout=PIPE, text=True).communicate()
    return jsonify(example), 200


@app.route("/config/save", methods=["POST"])
def config_save():
    if not is_authenticated():
        return "Not authenticated", 401
    data = request.get_json().get("config")
    clean_data = tomlkit.dumps(tomlkit.parse(data))
    encoded_data = base64.b64encode(clean_data.encode()).decode()
    app.config["config"] = encoded_data
    return jsonify(encoded_data), 200


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
        if app.config["proc"] is None:
            start_proc()
            return jsonify({"status": "restarted", "pid": app.config["proc"].pid}), 201
        else:
            return jsonify({"status": "running", "pid": app.config["proc"].pid}), 200
    else:
        return abort(403)


@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html", version=version), 404


@socketio.on("pty-input", namespace="/pty")
def pty_input(data):
    if not is_authenticated():
        return
    with app.config["lock"]:
        if app.config["fd"]:
            i = data["input"].encode()
            os.write(app.config["fd"], i)


def set_size(fd, row, col, xpix=0, ypix=0):
    logger.debug(f"Resizing pty to: {row} {col}.")
    size = struct.pack("HHHH", row, col, xpix, ypix)
    fcntl.ioctl(fd, termios.TIOCSWINSZ, size)


@socketio.on("resize", namespace="/pty")
def resize(data):
    logger.debug("Received resize socketio signal.")
    if not is_authenticated():
        return
    with app.config["lock"]:
        if app.config["fd"]:
            set_size(app.config["fd"], data["rows"], data["cols"])


@socketio.on("connect", namespace="/pty")
def connected():
    logger.debug(f"Console connected.")


@socketio.on("disconnect", namespace="/pty")
def connected():
    logger.debug(f"Console disconnected.")


def read_and_forward_pty_output():
    max_read_bytes = 1024 * 20
    while True:
        if app.config["fd"]:
            (data, _, _) = select.select([app.config["fd"]], [], [])
            if data:
                with app.config["lock"]:
                    if app.config["fd"]:
                        output = os.read(app.config["fd"], max_read_bytes).decode(errors="ignore")
                        app.config["hist"] += output
                        socketio.emit("pty-output", {"output": output}, namespace="/pty")
                    else:
                        break
        else:
            break


def disconnect_on_proc_exit(proc: Popen):
    returncode = proc.wait()
    if proc == app.config["proc"]:
        logger.debug(f"Command exited with return code {returncode}.")
        output = f"\r\n\n程序已退出, 返回值 {returncode}. " "\r\n请您刷新页面以重新启动程序."
        app.config["hist"] += output
        socketio.emit("pty-output", {"output": output}, namespace="/pty")


def start_proc():
    master_fd, slave_fd = pty.openpty()
    p = Popen(
        ["embykeeper", *app.config["args"]],
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=slave_fd,
        env={**os.environ, "EK_CONFIG": app.config["config"]},
        preexec_fn=os.setsid,
    )
    socketio.start_background_task(target=disconnect_on_proc_exit, proc=p)
    atexit.register(exit_handler)
    app.config["fd"] = master_fd
    app.config["proc"] = p
    logger.debug(f"Embykeeper started at: {p.pid}.")
    socketio.start_background_task(target=read_and_forward_pty_output)


@socketio.on("embykeeper_start", namespace="/pty")
def start(data, auth=True):
    logger.debug("Received embykeeper_start socketio signal.")
    if not is_authenticated():
        return
    with app.config["lock"]:
        if app.config["fd"] and app.config["proc"] and app.config["proc"].poll() is None:
            set_size(app.config["fd"], data["rows"], data["cols"])
            socketio.emit("pty-output", {"output": app.config["hist"]}, namespace="/pty")
        else:
            start_proc()
            set_size(app.config["fd"], data["rows"], data["cols"])


def kill_proc(proc: Popen):
    proc.send_signal(signal.SIGINT)
    for _ in range(10):
        poll = proc.poll()
        if poll is not None:
            break
    else:
        proc.kill()
    logger.debug(f"Embykeeper killed: {proc.pid}.")


@socketio.on("embykeeper_kill", namespace="/pty")
def kill():
    logger.debug("Received embykeeper_kill socketio signal.")
    if not is_authenticated():
        return
    with app.config["lock"]:
        proc = app.config["proc"]
        if proc is not None:
            app.config["fd"] = None
            app.config["proc"] = None
            app.config["hist"] = ""
    if proc is not None:
        socketio.start_background_task(target=kill_proc, proc=proc)


@cli.command(context_settings={"ignore_unknown_options": True, "allow_extra_args": True})
def run(
    ctx: typer.Context,
    port: int = typer.Option(1818, envvar="PORT", show_envvar=False),
    host: str = "0.0.0.0",
    debug: bool = False,
    wait: bool = False,
):
    app.config["args"] = ctx.args
    if not wait:
        start_proc()
    logger.info(f"Embykeeper webserver started at {host}:{port}.")
    socketio.run(app, port=port, host=host, debug=debug)


if __name__ == "__main__":
    cli()
