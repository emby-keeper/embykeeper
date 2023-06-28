window.addEventListener('DOMContentLoaded', function() {
    const term = new Terminal({
        cursorBlink: false,
        macOptionIsMeta: true,
        allowTransparency: true,
        altClickMovesCursor: false,
        fontFamily: 'Cascadia Code, Courier New, Courier, -apple-system, Noto Sans, Helvetica Neue, Helvetica, Nimbus Sans L, Arial, Liberation Sans, PingFang SC, Hiragino Sans GB, Noto Sans CJK SC, Source Han Sans SC, Source Han Sans CN, Microsoft YaHei, Wenquanyi Micro Hei, WenQuanYi Zen Hei, ST Heiti, SimHei, WenQuanYi Zen Hei Sharp, sans-serif',
        cursorStyle: 'bar',
        minimumContrastRatio: 7,
        smoothScrollDuration: 150,
        scrollback: 100000,
        rightClickSelectsWord: false,
        theme: {
            background: '#ffffff00',
            foreground: '#303030',
            cursor: '#303030',
            cursorAccent: '#ffffff00',
            selectionBackground: '#b1e2facc',
            selectionForeground: '#303030',
            selectionInactiveBackground: '#d8d8d8cc',
        }
    });

    const fit = new FitAddon.FitAddon();
    term.loadAddon(fit);
    term.loadAddon(new SearchAddon.SearchAddon());

    term.open(document.getElementById("terminal"));
    fit.fit();
    console.debug("Web console init: ", term.cols, term.rows);

    const socket = io.connect("/pty", {'reconnection': false});
    socket.on("connect", () => {
        var statusIcon = document.getElementById("status-icon");
        statusIcon.style.backgroundColor = "green";
        var statusMsg = document.getElementById("status-msg");
        statusMsg.textContent = "Program Connected";
        var restartIcon = document.getElementById("restart-icon");
        restartIcon.style.animationPlayState = "paused";
        console.info("Web console connected: ", term.cols, term.rows);
        term.focus();
        term.clear();
        term.reset();
        const dims = { cols: term.cols, rows: term.rows };
        socket.emit("embykeeper_start", dims);
    });

    socket.on("disconnect", (reason) => {
        var statusIcon = document.getElementById("status-icon");
        statusIcon.style.backgroundColor = "red";
        var statusMsg = document.getElementById("status-msg");
        statusMsg.textContent = "Program Disconnected";
        var restartIcon = document.getElementById("restart-icon");
        restartIcon.style.animationPlayState = "running";
        console.info("Web console disconnected: ", reason);
    });

    var restartBtn = document.getElementById("restart-btn");
    restartBtn.addEventListener('click', () => {
        socket.emit("embykeeper_kill");
        socket.disconnect();
        var statusMsg = document.getElementById("status-msg");
        statusMsg.textContent = "Program Restarting"
        console.info("Web console restarting.");
        socket.open();
    });

    function resize() {
        fit.fit();
        console.debug("Web console resize: ", term.cols, term.rows);
        const dims = { cols: term.cols, rows: term.rows };
        socket.emit("resize", dims);
    }

    function debounce(func, wait_ms) {
        let timeout;
        return function (...args) {
            const context = this;
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(context, args), wait_ms);
        };
    }

    window.onresize = debounce(resize, 50);

    term.onData((data) => {
        console.debug(data)
        socket.emit("pty-input", { input: data });
    });

    socket.on("pty-output", (data) => {
        term.write(data.output);
    });

    function customKeyEventHandler(e) {
        if (e.type !== "keydown") {
            return true;
        }
        if (e.ctrlKey) {
            const key = e.key.toLowerCase();
            if (key === "v") {
                navigator.clipboard.readText().then((toPaste) => {
                    term.writeText(toPaste);
                });
                return false;
            } else if (key === "c" || key === "x") {
                const toCopy = term.getSelection();
                navigator.clipboard.writeText(toCopy);
                term.focus();
                return false;
            }
        }
        return true;
    }

    term.attachCustomKeyEventHandler(customKeyEventHandler);
});
