# SwiftDeploy

A declarative CLI tool that generates and manages a full Docker stack 
from a single `manifest.yaml` source of truth.

---

## Prerequisites

- Docker Engine 24+
- Docker Compose v2+
- Python 3.10+
- pip packages: `pip install pyyaml jinja2`

---

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/swiftdeploy.git
cd swiftdeploy

# 2. Build the app image
docker build -t swift-deploy-1-node:latest ./app

# 3. Make CLI executable
chmod +x swiftdeploy

# 4. Deploy the full stack
./swiftdeploy deploy
```

---

## manifest.yaml — Single Source of Truth

Edit ONLY this file to configure your deployment:

```yaml
services:
  image: swift-deploy-1-node:latest
  port: 3000
  mode: stable        # stable | canary
  version: "1.0.0"
  restart_policy: unless-stopped
  log_volume: app_logs

nginx:
  image: nginx:latest
  port: 8080
  proxy_timeout: 30

network:
  name: swiftdeploy-net
  driver_type: bridge
```

---

## CLI Subcommands

### init
Generates `nginx.conf` and `docker-compose.yml` from templates:
```bash
./swiftdeploy init
```

### validate
Runs 5 pre-flight checks before deploying:
```bash
./swiftdeploy validate
```

Checks:
1. manifest.yaml exists and is valid YAML
2. All required fields present
3. Docker image exists locally
4. Nginx port is available
5. nginx.conf syntax is valid

### deploy
Generates configs, starts stack, waits for health checks:
```bash
./swiftdeploy deploy
```

### promote
Switches deployment mode with rolling restart:
```bash
./swiftdeploy promote canary    # switch to canary
./swiftdeploy promote stable    # switch back to stable
```

Canary mode:
- Adds `X-Mode: canary` header to every response
- Activates `/chaos` endpoint

### teardown
Removes all containers, networks and volumes:
```bash
./swiftdeploy teardown           # stop stack
./swiftdeploy teardown --clean   # also delete generated configs
```
---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Welcome message with mode, version, timestamp |
| `/healthz` | GET | Liveness check with uptime |
| `/chaos` | POST | Simulate degraded behavior (canary only) |

### Chaos Modes (canary only)
```bash
# Slow responses
curl -X POST http://localhost:8080/chaos \
  -H "Content-Type: application/json" \
  -d '{"mode": "slow", "duration": 2}'

# Random errors (~50%)
curl -X POST http://localhost:8080/chaos \
  -H "Content-Type: application/json" \
  -d '{"mode": "error", "rate": 0.5}'

# Recover
curl -X POST http://localhost:8080/chaos \
  -H "Content-Type: application/json" \
  -d '{"mode": "recover"}'
```

---

## Architecture
[Browser/curl]
↓
[Nginx :8080]          ← reverse proxy, headers, error pages
↓
[Python App :3000]     ← Flask/Gunicorn API (not exposed directly)
↓
[Docker Network]       ← swiftdeploy-net (bridge)

---

## Troubleshooting

### Port already in use
```bash
lsof -i :8080
kill -9 <PID>
```

### Image not found
```bash
docker build -t swift-deploy-1-node:latest ./app
```

### Docker permission denied
```bash
sudo usermod -aG docker $USER
newgrp docker
```

### View live logs
```bash
docker compose logs -f
docker compose logs nginx
docker compose logs app
```

### Health check failing
```bash
docker inspect --format='{{.State.Health.Status}}' \
  $(docker compose ps -q app)
docker compose logs app
```

---

## Project Structure
swiftdeploy-project/
├── manifest.yaml          ← ONLY file you edit
├── swiftdeploy            ← CLI tool
├── app/
│   ├── main.py            ← Flask API
│   ├── requirements.txt
│   └── Dockerfile
├── templates/
│   ├── nginx.conf.j2      ← nginx template
│   └── docker-compose.yml.j2
├── nginx.conf             ← GENERATED (do not edit)
├── docker-compose.yml     ← GENERATED (do not edit)
└── README.md

---

## Known Limitations
- Chaos state is in-memory — resets on container restart
- Single app instance (no load balancing)
- No TLS/SSL configured
- Designed for local/demo use