FROM python:3.8 AS builder

WORKDIR /src
COPY . .

RUN python -m venv /opt/venv \
    && . /opt/venv/bin/activate \
    && pip install --no-cache-dir -U pip setuptools wheel \
    && pip install --no-cache-dir .

FROM python:3.8-slim
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /src/scripts/docker-entrypoint.sh /entrypoint.sh

ENV TZ="Asia/Shanghai"
RUN useradd -m -u 1000 embykeeper
RUN mkdir /app & chown -R embykeeper:embykeeper /app
RUN chmod +x /entrypoint.sh && touch config.toml
USER user
WORKDIR /app
ENV HOME=/app
ENV PATH="/opt/venv/bin:$PATH"

ENTRYPOINT ["/entrypoint.sh"]
