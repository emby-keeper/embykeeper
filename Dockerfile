FROM python:3.8-slim AS builder

WORKDIR /src
COPY . .

RUN python -m venv /opt/venv \
    && . /opt/venv/bin/activate \
    && pip install --no-cache-dir -U pip setuptools wheel \
    && pip install --no-cache-dir .

FROM python:3.8-slim
COPY --from=builder /opt/venv /opt/venv

VOLUME ["/root/.local/share/embykeeper"]

WORKDIR /app
RUN touch config.toml
ENV PATH="/opt/venv/bin:$PATH"

ENTRYPOINT ["embykeeper"]
CMD ["config.toml"]
