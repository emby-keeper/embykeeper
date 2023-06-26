## 向 Embykeeper 贡献提交

欢迎! 很高兴你愿意让这个项目变得更好, 你可以通过以下您偏好的方式开始修改代码:

### 通过 Codesandbox 在线编辑与提交

1. 进入 [Codesandbox](https://codesandbox.io/): [项目链接](https://codesandbox.io/s/github/embykeeper/embykeeper/tree/main)
2. 点击右侧分栏的 `Terminal`, 点击 `Fork and convert`, 以启动一个云编辑器.
3. 在新建的项目中, 等待项目依赖安装完成.
4. 修改代码, 点击右侧命令列表中的命令, 即可查看效果.
5. 您也可以点击右上角的 `VS Code` 按钮, 以查看 `VS Code` 链接到[Codesandbox](https://codesandbox.io/) 的方法.
6. 点击最左侧文件树上方的 Git 图标, 即可 Push 到个人仓库.
7. 在 [Pull Requests](https://github.com/embykeeper/embykeeper/pulls) 提交新 Pull Request.

### 搭建本地开发环境编辑与提交

1. Fork 本仓库
2. 通过 `git clone <forked repo>` 以将仓库克隆到本地
3. 启用一个虚拟空间, 例如:

   ```bash
   python -m venv .venv
   . .venv/bin/activate
   ```
4. 安装项目为可编辑模式:

   ```bash
   pip install -e .
   ```
5. 修改代码以实现需求
6. 在提交 Pull Request 前, 请使用 `pre-commit` 工具检查代码:

   ```bash
   pre-commit run -a
   tox -e py
   ```
7. 在 [Pull Requests](https://github.com/embykeeper/embykeeper/pulls) 提交新 Pull Request.
