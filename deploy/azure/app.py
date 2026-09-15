"""Azure Web App (Linux container) entrypoint. Serves the built frontend and the
FastAPI inspection API on 0.0.0.0 so Azure's front-end proxy can reach it. The
ONNX model is baked into the image registry at build time (see Dockerfile)."""
import os
from pathlib import Path
from bluecho.dashboard.service import create_app

registry = Path(os.environ.get('BLUECHO_REGISTRY', '/app/registry'))
storage = Path(os.environ.get('BLUECHO_STORAGE', '/app/data'))
storage.mkdir(parents=True, exist_ok=True)

# Azure App Service sets WEBSITE_HOSTNAME to the public <app-name>.azurewebsites.net
# host; custom domains can be added via BLUECHO_ALLOWED_HOSTS (comma-separated).
host = os.environ.get('WEBSITE_HOSTNAME', 'localhost')
extra_hosts = [h.strip() for h in os.environ.get('BLUECHO_ALLOWED_HOSTS', '').split(',') if h.strip()]
all_hosts = list(dict.fromkeys([host, 'localhost', '127.0.0.1', *extra_hosts]))

allowed_hosts = all_hosts
allowed_origins = [f'https://{h}' for h in all_hosts] + [f'http://{h}' for h in all_hosts]

app = create_app(
    storage,
    registry,
    queue_limit=4,
    memory_mib=2048,
    hosted=True,
    allowed_hosts=allowed_hosts,
    allowed_origins=allowed_origins,
)
