# Windows 安装脚本安装

::: info 提示
推荐使用该方式安装, 方便后续更新.
:::

## 安装教程

您需要转到 [Release](https://github.com/emby-keeper/embykeeper/releases) 界面, 选择最新版本 (`Latest`), 然后展开 `Assets`, 点击下载 `embykeeper-win-vx.x.x.zip` 文件 (请注意**不是** `exe`!).

解压后运行 `Embykeeper.bat`, Embykeeper 将会自动安装到当前文件夹中.

安装后 Embykeeper 将首次运行并在当前目录下生成模板 `config.toml` 文件 (您也可以从[这里](https://github.com/emby-keeper/embykeeper/blob/main/config.example.toml)下载).

请您根据模板文件中的注释 (以`#`开头), 配置您的账户信息.

您也可以使用最小配置, 例如:

```toml
[[telegram]]
phone = "+8612109347899"

[[emby]]
url = "https://weiss-griffin.com:443"
username = "carrie19"
password = "s*D7MMCpS$"
```

<details>
<summary>查看更多可用配置的简要介绍 (代理, 群组监控, 自动水群等)</summary>

### 更多可用配置

您可以只使用机器人签到或 Emby 模拟观看:

<details>
<summary>查看只进行机器人签到的配置</summary>

```toml
[[telegram]]
phone = "+8612109347899"
```

</details>

<details>
<summary>查看只进行 Emby 模拟观看的配置</summary>

```toml
[[emby]]
url = "https://weiss-griffin.com:443"
username = "carrie19"
password = "s*D7MMCpS$"
```

</details>

若您需要连接代理, 还需要在 `config.toml` 中追加代理配置:

```toml
[proxy]
hostname = "127.0.0.1"
port = 1080
scheme = "socks5"
```

<details>
<summary>查看带代理的完整配置</summary>

```toml
[proxy]
hostname = "127.0.0.1"
port = 1080
scheme = "socks5"

[[telegram]]
phone = "+8612109347899"

[[emby]]
url = "https://weiss-griffin.com:443"
username = "carrie19"
password = "s*D7MMCpS$"
```

</details>

若您是[高级用户](/guide/高级用户)并希望开启群组监控与自动水群功能, 请调节 `[[telegram]]` 账户设置内的 `monitor` 和 `send` 选项.

<details>
<summary>查看带群组监控与自动水群的完整配置</summary>

```toml
[[telegram]]
phone = "+8612109347899"
send = false # 启用该账号的自动水群功能 (需要高级账号, 谨慎使用)
monitor = false # 启用该账号的自动监控功能 (需要高级账号)

[[emby]]
url = "https://weiss-griffin.com:443"
username = "carrie19"
password = "s*D7MMCpS$"
time = [120, 240] # 模拟观看的时长范围 (秒)
```

</details>

更多配置项详见 [Wiki](/guide/配置文件).

</details>

随后, 重新运行 `Embykeeper.bat`, 即可启动程序.

您将被询问设备验证码以登录, 登录成功后, Embykeeper 将首先执行一次签到和保活, 此后每日进行一次签到和保活.

恭喜您！您已经成功部署了 Embykeeper.

## 后台运行

您可以使用多种工具实现后台运行, 包括 [NSSM](https://nssm.cc/), [AHK](https://superuser.com/a/1106399) 等.

您可以自行探索, 但推荐新手用户前台运行, 以观察输出日志.

## 版本更新

当您需要更新版本时, 您需要关闭 Embykeeper, 然后运行 `Embykeeper.bat` 同一目录下的 `Update.bat`.

脚本将提示您更新信息.

更新后, 重新运行 `Embykeeper.bat`.
