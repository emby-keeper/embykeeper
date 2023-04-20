FROM python:3.10-slim-buster

WORKDIR /app

VOLUME ["/root/.local/share/embykeeper"]

COPY . .
RUN touch config.toml
RUN pip install -i https://pypi.tuna.tsinghua.edu.cn/simple/ -U pip
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple/
RUN pip install .

ENTRYPOINT ["embykeeper"]
CMD ["config.toml"]
