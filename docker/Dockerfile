FROM python:3.11-slim

WORKDIR /app

# Copy sources first so pip can install the local package.
COPY pyproject.toml /app/pyproject.toml
COPY app /app/app

# Keep the default image lightweight by NOT installing heavy ML deps.
# If you want local sentence-transformers reranking/embeddings, build with:
#   docker build --build-arg INSTALL_LOCAL_ML=1 ...
ARG INSTALL_LOCAL_ML=0

RUN pip install --no-cache-dir -U pip setuptools wheel \
 && if [ "$INSTALL_LOCAL_ML" = "1" ]; then \
      pip install --no-cache-dir ".[local_ml]"; \
    else \
      pip install --no-cache-dir .; \
    fi

ENV PYTHONPATH=/app
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
