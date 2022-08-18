FROM python:3.10.6-slim

WORKDIR /starr

COPY requirements.txt ./
RUN apt-get update && \
    apt-get install -y git && \
    python -m venv .venv && \
    .venv/bin/pip install --no-cache-dir -r requirements.txt

COPY . .

CMD [ ".venv/bin/python", "launch.py" ]
