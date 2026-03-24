# PRD

## Original Problem Statement
Build main README professional for user. How to deploy, inputs, how to use and docs.

## User Choices
- Deployment section: local setup + Docker + VM/server deployment
- Audience: both users and developers
- Tone: professional and detailed

## Architecture Decisions
- Kept the README as the single main documentation entrypoint for both operators and maintainers
- Documented deployment in three practical layers: local, Docker pattern, and VM/server production setup
- Included environment variables, API overview, accepted inputs, and step-by-step product usage so the README works as both onboarding and operations documentation
- Avoided exposing real secrets while keeping config examples concrete and copy-friendly

## What’s Implemented
- Rewrote `/app/README.md` into a professional user-facing guide
- Added sections for product overview, capabilities, workflows, inputs, environment variables, deployment, API overview, project structure, troubleshooting, and security notes
- Documented how scanner import, provider key management, report approval, and markdown export work in product terms
- Added local deployment instructions and practical Docker / VM deployment guidance for maintainers

## Prioritized Backlog
### P0
- Add dedicated `docs/` pages for API examples and operational SOPs if documentation grows further

### P1
- Add bundled Dockerfiles and compose assets to match the README’s Docker deployment guidance exactly
- Add architecture diagrams and screenshots for onboarding

### P2
- Add changelog, release notes, and role-based admin/operator handbooks

## Next Tasks
- Optionally add real Docker assets and production-ready deployment files
- Expand docs with API request/response examples and troubleshooting screenshots
- Add a docs section for backup, restore, and upgrade procedures
