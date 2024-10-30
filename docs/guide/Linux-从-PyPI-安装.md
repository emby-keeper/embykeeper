# 从 PyPi 安装

## 配置与部署

Embykeeper 可以在 `python >= 3.8, < 3.11` 运行.

需要通过 [virtualvenv](https://virtualenv.pypa.io/) 进行环境管理和包安装:

```bash
python -m venv embykeeper-venv
. ./embykeeper-venv/bin/activate
pip install embykeeper
```

随后, 您需要执行:

```bash
embykeeper
```

命令将会在 `embykeeper` 目录下生成模板 `config.toml` 文件 (您也可以从[这里](https://github.com/emby-keeper/emby-keeper/blob/main/config.example.toml)下载).

<!--@include: ./_简要配置.md-->

然后, 再次运行:

```bash
embykeeper
```

您将被询问设备验证码以登录, 登录成功后, Embykeeper 将首先执行一次签到和保活, 此后每日进行一次签到和保活.

恭喜您！您已经成功安装了 Embykeeper.

::: info 支持

<!--@include: ./_支持.md-->

:::

## 后台运行

为了让 Embykeeper 长期后台运行, 您可以通过 `Ctrl + C` 停止, 然后运行:

```bash
tmux
```

这将启动一个 `tmux` 终端, 您可以在该终端中重新运行上述命令, 并按 `Ctrl + B`, 松开再按 `D`, 以脱离 `tmux` 终端.

您随时可以通过运行:

```bash
tmux a
```

以重新连接到 `tmux` 终端.

## 版本更新

当您需要更新版本时, 您需要执行:

```
pip install -U embykeeper
```

然后重新运行应用.
