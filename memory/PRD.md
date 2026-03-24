# PRD

## Original Problem Statement
User asked for a professional main README, then provided concrete local run, test, Docker, Kubernetes, provider manifest, routing policy, and current-vs-next architecture content to incorporate while keeping documentation current as the project evolves.

## User Direction
- Keep the documentation current and update it as the project evolves
- Incorporate the provided clone/run, testing, deployment template, and architecture guidance

## Architecture Decisions
- Kept the main README as the canonical entrypoint for users and developers
- Added actual self-hosting template assets to the repository instead of documenting non-existent files
- Clearly separated current live behavior from future-state / reference architecture so the docs stay honest
- Marked provider-manifest and routing config files as future-state templates, not active runtime config

## What’s Implemented
- Added `docker-compose.yml` plus working `backend/Dockerfile`, `frontend/Dockerfile`, and `frontend/nginx.conf`
- Added Kubernetes deployment templates in `/app/k8s` for namespace, secret, MongoDB, backend, frontend, and ingress
- Added future-state reference config templates in `/app/configs/providers.yaml` and `/app/configs/routing.yaml`
- Extended `README.md` with repository quick start, test instructions, shipped deployment templates, current-vs-next architecture, and remaining work roadmap
- Validated all new YAML files parse correctly and confirmed the README includes the new sections

## Prioritized Backlog
### P0
- Add image build/publish instructions and versioning guidance for Docker and Kubernetes templates

### P1
- Add Helm chart or Kustomize overlays for cluster deployment
- Add bundled CI/CD examples for image build, migration checks, and rollout

### P2
- Add deeper operations docs for backups, restore, secrets rotation, and observability dashboards

## Next Tasks
- Add production `.env.example` files and image tagging guidance
- Add Helm/Kustomize deployment packaging
- Add API examples and operations runbooks under a dedicated `docs/` folder
