# Windows 安装脚本安装

::: info 提示
推荐使用该方式安装, 方便后续更新.
:::

## 安装教程

您需要转到 [Release](https://github.com/emby-keeper/emby-keeper/releases) 界面, 选择最新版本 (`Latest`), 然后展开 `Assets`, 点击下载 `embykeeper-win-vx.x.x.zip` 文件 (请注意**不是** `exe`!).

解压后运行 `Embykeeper.bat`, Embykeeper 将会自动安装到当前文件夹中.

安装后 Embykeeper 将首次运行并在当前目录下生成模板 `config.toml` 文件 (您也可以从[这里](https://github.com/emby-keeper/emby-keeper/blob/main/config.example.toml)下载).

<!--@include: ./_简要配置.md-->

随后, 重新运行 `Embykeeper.bat`, 即可启动程序.

您将被询问设备验证码以登录, 登录成功后, Embykeeper 将首先执行一次签到和保活, 此后每日进行一次签到和保活.

恭喜您！您已经成功部署了 Embykeeper.

若您后续需要修改 `config.toml` 文件, 您需要结束程序并重新运行.

::: info 支持

<!--@include: ./_支持.md-->

:::

## 后台运行

您可以使用多种工具实现后台运行, 包括 [NSSM](https://nssm.cc/), [AHK](https://superuser.com/a/1106399) 等.

您可以自行探索, 但推荐新手用户前台运行, 以观察输出日志.

## 版本更新

当您需要更新版本时, 您需要关闭 Embykeeper, 然后运行 `Embykeeper.bat` 同一目录下的 `Update.bat`.

脚本将提示您更新信息.

更新后, 重新运行 `Embykeeper.bat`.
