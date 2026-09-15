# Azure Web App for Containers image. The frontend must already be built
# (non-browser-engine, real backend mode) into src/bluecho/dashboard/static
# before this image is built — the CI workflow does `npm run build --prefix
# frontend` immediately before `az acr build`.
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 curl && rm -rf /var/lib/apt/lists/*
WORKDIR /app

RUN pip install --no-cache-dir torch==2.4.1+cpu torchvision==0.19.1+cpu --index-url https://download.pytorch.org/whl/cpu
COPY pyproject.toml README.md LICENSE MANIFEST.in ./
COPY src ./src
RUN pip install --no-cache-dir ".[inspection,inference,onnx,geospatial,api]"

# Bake the checksum-verified ONNX model into the image so the container never
# needs outbound network access at runtime.
RUN bluecho models fetch --model fls11-debris --registry /app/registry \
 && bluecho models verify --model fls11-debris --registry /app/registry

RUN useradd -m -u 1000 bluecho && mkdir -p /app/data && chown -R bluecho:bluecho /app
COPY --chown=bluecho:bluecho deploy/azure/app.py /app/app.py

USER bluecho
ENV PYTHONUNBUFFERED=1 \
    OMP_NUM_THREADS=2 \
    MKL_NUM_THREADS=2 \
    OPENBLAS_NUM_THREADS=1 \
    PROJ_NETWORK=OFF \
    YOLO_CONFIG_DIR=/tmp/ultralytics \
    BLUECHO_STORAGE=/app/data \
    BLUECHO_REGISTRY=/app/registry \
    WEBSITES_PORT=8000

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD curl -f http://127.0.0.1:8000/api/v1/health || exit 1

CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
