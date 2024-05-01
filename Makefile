.RECIPEPREFIX := >
.DEFAULT_GOAL := help
.PHONY: help help/simple help/all install develop venv venv/clean python/venv conda/venv conda/install run run/cli run/web systemd systemd/install systemd/uninstall lint test debugpy debugpy/cli debugpy/web version version/patch version/minor version/major push clean clean/build clean/pyc clean/test

USE_MIRROR ?= True

ifeq ($(USE_MIRROR), True)
    CONDA_URL := "https://mirrors.tuna.tsinghua.edu.cn/anaconda/miniconda/Miniconda3-latest-Linux-$$(uname -i).sh"
    CONDA_CHANNEL_URL := "https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main"
    PYPI_URL := "https://pypi.tuna.tsinghua.edu.cn/simple"
else
    CONDA_URL := "https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-$$(uname -i).sh"
    CONDA_CHANNEL_URL := "https://repo.anaconda.com/pkgs/main"
    PYPI_URL := "https://pypi.org/simple"
endif

PYTHON ?= python
PYTHON_COMPATIBLE := $(shell "$(PYTHON)" -c "import sys; print((sys.version_info >= (3, 8)) and (sys.version_info < (3, 10)))" 2>/dev/null || echo False)
CONDA_ROOT ?= conda
VENV := venv

help: help/simple

help/simple:
>   @echo "Welcome to embykeeper!"
>   @echo "\nUsage: make <subcommand>"
>   @echo "  install - create a venv and install embykeeper in it."
>   @echo "  develop - install embykeeper and also dev-related tools."
>   @echo "  run - run embykeeper with config.toml."
>   @echo "  systemd - make embykeeper autostart on current user first login after reboot."
>   @echo "  dev - run install "
>   @echo "  lint - check style with black and pre-commit."
>   @echo "  test - run pytest using current python."
>   @echo "  help/all - show all subcommands."
>   @echo "\nFor using embykeeper, you can run:"
>   @echo "  make install && make run"

help/all:
>   @echo "Welcome to embykeeper!"
>   @echo "Usage: make <subcommand>"
>   @echo "  install - create a venv and install embykeeper in it."
>   @echo "  develop - install embykeeper and also dev-related tools."
>   @echo "  venv - create a venv (if python compatible) or conda (if not)."
>   @echo "  venv/clean - remove all created venv."
>   @echo '  python/venv - create a venv using current python in "<CWD>/venv".'
>   @echo '  conda/venv - create a conda venv in "<CWD>/venv".'
>   @echo '  conda/install - install conda in "<CWD>/conda".'
>   @echo "  run - run embykeeper with config.toml."
>   @echo "  run/web - run embykeeperweb in public mode."
>   @echo "  systemd - make embykeeper autostart on current user first login after reboot."
>   @echo "  systemd/uninstall - remove systemd config and stop embykeeper from autostart."
>   @echo "  lint - check style with black and pre-commit."
>   @echo "  test - run pytest using current python."
>   @echo "  debugpy - start embykeeper with debugpy (vscode debug module) for remote connection at localhost:5678."
>   @echo "  debugpy/web - start embykeeperweb with debugpy (vscode debug module) for remote connection at localhost:5678."
>   @echo "  version - same as version/patch."
>   @echo "  version/patch - run bump2version patch and push."
>   @echo "  version/minor - run bump2version minor and push."
>   @echo "  version/major - run bump2version major and push."
>   @echo "  push - git push both commits and tags."
>   @echo "  clean - remove build and test caches."
>   @echo "  clean/build - remove build caches."
>   @echo "  clean/pyc - remove python caches."
>   @echo "  clean/test - remove test caches."

install: venv
>   @"$(VENV)/bin/python" -m pip install -i "$(PYPI_URL)" -U pip && \
>   "$(VENV)/bin/python" -m pip install -i "$(PYPI_URL)" -e . \
>   && echo "Info: Embykeeper has been installed successfully." \
>   && echo 'Info: Run "make run" to run embykeeper.' \
>   && echo 'Info: Run "make systemd" to enable autostart.' \
>   || echo "Error: Fail to install embykeeper."

develop: install
>   "$(VENV)/bin/python" -m pip install -i "$(PYPI_URL)" -r requirements_dev.txt

ifeq ($(PYTHON_COMPATIBLE), True)
    venv: python/venv
else
    venv: conda/venv
endif

venv/require:
>   @[ ! -d "$(VENV)" ] && echo "Error: 尚未安装, 请先运行 make run 以安装!" && exit 1 || :

venv/clean:
>   rm -R -f venv conda &>/dev/null

python/venv:
>   @[ ! -d "$(VENV)" ] && echo "Info: 正在创建 Venv 环境 ..." && "$(PYTHON)" -m venv "$(VENV)" && echo "Info: Venv 环境创建完成" && \
>   echo "Info: 正在安装 Embykeeper ..." && \
>   "$(VENV)/bin/python" -m pip install -e . && \
>   echo "Info: Embykeeper 安装完成!" || :

conda/venv: conda/install
>   @[ ! -d "$(VENV)" ] && echo "Info: 正在创建 Conda 环境 ..." && "$(CONDA_ROOT)/condabin/conda" create -y --prefix venv --override-channels -c $(CONDA_CHANNEL_URL) python~=3.8.0 && echo "Info: Conda 环境创建完成" && \
>   echo "Info: 正在安装 Embykeeper ..." && \
>   "$(VENV)/bin/python" -m pip install -e . && \
>   echo "Info: Embykeeper 安装完成!" || :

conda/install:
>   @if [ ! -d "$(CONDA_ROOT)" ]; then \
>       while :; do \
>           read -p "请注意: 您当前的 Python 环境不符合要求 (python >=3.8, <3.11), 是否在当前目录安装一个新的 Conda Python 环境? [y/N]:" yn; \
>           case $$yn in \
>               [Yy]* ) break;; \
>               [Nn]* ) exit;; \
>               * ) echo "Info: 请回答 Y (确定) 或 N (取消).";; \
>           esac; \
>       done; \
>       echo "Info: 正在安装 Conda ..."; \
>       curl -o conda.sh "$(CONDA_URL)" && chmod +x conda.sh && bash conda.sh -b -f -p "$(CONDA_ROOT)"; \
>       rm conda.sh 2>/dev/null; \
>       echo "Info: Conda 安装完成!"; \
>   fi

run: run/cli

run/cli: venv/require
>   @"$(VENV)/bin/python" -m embykeeper

run/web: venv/require
>   @"$(VENV)/bin/python" -m embykeeperweb --public

systemd: systemd/install

systemd/install: venv/require
>   @if ! type systemctl > /dev/null; then \
>       echo "Error: 找不到 systemctl 命令."; \
>       exit 1; \
>   elif [ ! -f config.toml ]; then \
>       echo 'Error: config.toml 还没有被生成. 您应该首先运行 "make run" 并编辑生成的配置文件.'; \
>       exit 1; \
>   else \
>       if [ "$$(id -u)" -eq 0 ]; then \
>           mkdir -p "/etc/systemd/system" && echo " \
>           [Unit]\n \
>           Description=Embykeeper Daemon\n \
>           After=network.target\n\n \
>           [Service]\n \
>           Type=simple\n \
>           RestartSec=5s\n \
>           Restart=on-failure\n \
>           WorkingDirectory=$$(readlink -f .)\n \
>           ExecStart="$$(readlink -f .)/$(VENV)/bin/python" -m embykeeper --simple-log\n\n \
>           [Install]\n \
>           WantedBy=multi-user.target" \
>           | sed 's/^[[:space:]]*//' \
>           > "/etc/systemd/system/embykeeper.service" && \
>           systemctl enable embykeeper && \
>           systemctl start embykeeper && \
>           echo "Info: 已经将 embykeeper 添加到系统的 systemd 配置文件目录 (/etc/systemd/system/). Embykeeper 会在系统启动时自动启动." && \
>           echo 'Info: 运行 "systemctl status embykeeper" 以检查程序状态.' && \
>           echo 'Info: 运行 "sudo make systemd/uninstall" 以移除.'; \
>       else \
>           mkdir -p "$(HOME)/.config/systemd/user" && echo " \
>           [Unit]\n \
>           Description=Embykeeper Daemon\n \
>           After=network.target\n\n \
>           [Service]\n \
>           Type=simple\n \
>           RestartSec=5s\n \
>           Restart=on-failure\n \
>           WorkingDirectory=$$(readlink -f .)\n \
>           ExecStart="$$(readlink -f .)/$(VENV)/bin/python" -m embykeeper --simple-log\n\n \
>           [Install]\n \
>           WantedBy=default.target" \
>           | sed 's/^[[:space:]]*//' \
>           > "$(HOME)/.config/systemd/user/embykeeper.service" && \
>           systemctl --user enable embykeeper && \
>           systemctl --user start embykeeper && \
>           echo "Info: 已经将 embykeeper 添加到用户的 systemd 配置文件目录 ($(HOME)/.config/systemd/user). Embykeeper 会在当前用户登录时自动启动." && \
>           echo 'Info: 运行 "sudo make systemd/uninstall" 添加到系统的 systemd 配置文件目录.' && \
>           echo 'Info: 运行 "systemctl --user status embykeeper" 以检查程序状态.' && \
>           echo 'Info: 运行 "make systemd/uninstall" 以移除.'; \
>       fi \
>   fi

systemd/uninstall:
>   @if [ "$$(id -u)" -eq 0 ]; then \
>       systemctl stop embykeeper && \
>       systemctl disable embykeeper && \
>       rm "/etc/systemd/system/embykeeper.service" && \
>       echo 'Info: 已移除 systemd 配置. Embykeeper 不再自动启动.'; \
>   else \
>       systemctl --user stop embykeeper && \
>       systemctl --user disable embykeeper && \
>       rm "$(HOME)/.config/systemd/user/embykeeper.service" && \
>       echo 'Info: 已移除 systemd 配置. Embykeeper 不再自动启动.'; \
>   fi

lint: venv/require
>   "$(VENV)/bin/python" -m black .
>   "$(VENV)/bin/python" -m pre_commit run -a

test: venv/require
>   "$(VENV)/bin/python" -m pytest

debugpy: debugpy/cli

debugpy/cli: venv/require
>   "$(VENV)/bin/python" -m debugpy --listen localhost:5678 --wait-for-client cli.py

debugpy/web: venv/require
>   "$(VENV)/bin/python" -m debugpy --listen localhost:5678 --wait-for-client web.py --public

version: version/patch

version/patch: venv/require
>   "$(VENV)/bin/python" -m bump2version patch
>   git push && git push --tags

version/minor: venv/require
>   "$(VENV)/bin/python" -m bump2version minor
>   git push && git push --tags

version/major: venv/require
>   "$(VENV)/bin/python" -m bump2version major
>   git push && git push --tags

push:
>   git push && git push --tags

clean: clean/build clean/pyc clean/test
>   @echo "Info: 清除了构建和测试缓存."

clean/build:
>   rm -fr build/
>   rm -fr dist/
>   rm -fr .eggs/
>   find . -name '*.egg-info' -exec rm -fr {} +
>   find . -name '*.egg' -exec rm -f {} +

clean/pyc:
>   find . -name '*.pyc' -exec rm -f {} +
>   find . -name '*.pyo' -exec rm -f {} +
>   find . -name '*~' -exec rm -f {} +
>   find . -name '__pycache__' -exec rm -fr {} +

clean/test:
>   rm -fr .tox/
>   rm -f .coverage
>   rm -fr htmlcov/
