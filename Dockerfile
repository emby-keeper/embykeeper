FROM python:3.10-slim-buster

WORKDIR /app

COPY . .
RUN pip install .

CMD ["embykeeper"]
