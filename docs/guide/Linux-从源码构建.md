# 从源码构建

## 配置与部署

Embykeeper 可以从源码构建, 首先请拉取并设置环境:

```bash
git clone https://github.com/emby-keeper/embykeeper.git
make install && make run
```

命令将会在 `embykeeper` 目录下生成模板 `config.toml` 文件 (您也可以从[这里](https://github.com/emby-keeper/embykeeper/blob/main/config.example.toml)下载).

<!--@include: ./_简要配置.md-->

然后, 再次运行:

```bash
make run
```

您将被询问设备验证码以登录, 登录成功后, Embykeeper 将首先执行一次签到和保活, 此后每日进行一次签到和保活.

恭喜您！您已经成功构建了 Embykeeper.

::: info 支持

<!--@include: ./_支持.md-->

:::

## 服务持久化

您可以通过 [systemd](https://www.ruanyifeng.com/blog/2016/03/systemd-tutorial-commands.html) 部署自启动服务.

首先, 您需要成功登录运行一次, 然后请运行:

```bash
make systemd
```

这将在 `~/.config/systemd/user` 中创建服务, 使 Embykeeper 在用户登录时自动启动.

## 版本更新

当您需要更新版本时, 您需要执行:

```
git pull
```

然后重新运行应用.
