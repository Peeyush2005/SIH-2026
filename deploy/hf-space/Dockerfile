FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*
RUN useradd -m -u 1000 user
WORKDIR /app
RUN pip install --no-cache-dir torch==2.4.1+cpu torchvision==0.19.1+cpu --index-url https://download.pytorch.org/whl/cpu
COPY package /app/package
RUN pip install --no-cache-dir '/app/package[inspection,inference,onnx,geospatial,api]' huggingface_hub==1.31.0
COPY --chown=user app.py /app/app.py
USER user
ENV PYTHONUNBUFFERED=1 OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=1 PROJ_NETWORK=OFF YOLO_CONFIG_DIR=/tmp/ultralytics HF_HOME=/tmp/huggingface
EXPOSE 7860
CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860", "--proxy-headers", "--forwarded-allow-ips", "*"]
