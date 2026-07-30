# All-in-one image: Ollama + Gemma model + app logic, all running inside the same
# resource-capped container (see resource_caps.md for --memory/--cpus rationale).
FROM python:3.12-slim

ARG MODEL_NAME=gemma3n:e2b
ENV MODEL_NAME=${MODEL_NAME}
ENV OLLAMA_HOST=0.0.0.0:11434

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates zstd \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://ollama.com/install.sh | sh

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY docker/pull_model.sh /tmp/pull_model.sh
RUN chmod +x /tmp/pull_model.sh \
    && /tmp/pull_model.sh \
    && rm /tmp/pull_model.sh

COPY src/ /app/src

COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 5000 11434

ENTRYPOINT ["/entrypoint.sh"]
