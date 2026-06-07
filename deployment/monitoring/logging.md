# Logging

The production compose stack writes container logs through Docker's default logging driver.

Useful commands:

```bash
docker compose logs -f nginx
docker compose logs -f frontend
docker compose logs -f backend
docker compose logs -f postgres
docker compose logs -f qdrant
```

Backend logs are emitted to stdout/stderr by Gunicorn and the FastAPI logging layer. The frontend emits Next.js production logs to stdout. Nginx access and error logs are available through the `nginx` container logs.

Recommended VM hardening:

```bash
sudo tee /etc/docker/daemon.json >/dev/null <<'JSON'
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "50m",
    "max-file": "5"
  }
}
JSON
sudo systemctl restart docker
```
