FROM python:3.11

RUN apt update && apt install -y \
    git \
    curl \
    build-essential \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*


WORKDIR /workspace

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt