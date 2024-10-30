# Windows 安装包安装

::: tip 说明

该安装方式适用于不需要频繁更新的情况, 例如稳定版本.

若您需要更新版本, 推荐使用 [**⌨️ 自动安装脚本**](/guide/Windows-通过脚本安装) 方式安装, 方便后续更新.

:::

## 安装教程

您需要转到 [Release](https://github.com/emby-keeper/emby-keeper/releases) 界面, 选择最新版本 (`Latest`), 然后展开 `Assets`, 点击下载 `embykeeper-win-vx.x.x.exe` 文件.

运行 `embykeeper-win-vx.x.x.exe`, 跟随安装向导安装, 安装后 Embykeeper 将会启动, 并提示修改配置.

程序将会打开模板 `config.toml` 文件 (您也可以从[这里](https://github.com/emby-keeper/emby-keeper/blob/main/config.example.toml)下载).

<!--@include: ./_简要配置.md-->

保存配置文件后, 按任意键继续, 即可启动程序.

您将被询问设备验证码以登录, 登录成功后, Embykeeper 将首先执行一次签到和保活, 此后每日进行一次签到和保活.

恭喜您！您已经成功部署了 Embykeeper.

若您后续需要修改 `config.toml` 文件, 您可以从 `开始菜单` > `Embykeeper` > `配置文件` 快捷方式访问此文件.

::: info 支持

<!--@include: ./_支持.md-->

:::

## 后台运行

您可以使用多种工具实现后台运行, 包括 [NSSM](https://nssm.cc/), [AHK](https://superuser.com/a/1106399) 等.

您可以自行探索, 但推荐新手用户前台运行, 以观察输出日志.

## 版本更新

当您需要更新版本时, 您需要重新下载并安装版本对应的安装包.
