# Full Ecosystem — Cross-Component Briefing

> Generated 2026-02-26. For use by Claude Code instances working on any repo in this ecosystem.
> Covers ALL repos: server-monitor, nagz (3 repos), cardzerver (4 repos), adveyes, Flyz deployment.

---

## 1. Ecosystem Map

### Two Product Lines + Shared Infrastructure

```
NAGZ ECOSYSTEM (family nagging app)
  ~/nagzerver          Python 3.12 FastAPI    API server (68 endpoints, 27 metrics)
  ~/nagz-web           React 19 + TypeScript  Web frontend (orval-generated client)
  ~/nagz-ios           Swift 6 SwiftUI        iOS app (40+ endpoints, 215 tests)

CARD-ENGINE ECOSYSTEM (flashcards + trivia)
  ~/cardzerver        Python 3.12 FastAPI    Unified backend (replaced obo-server + alities-engine)
  ~/obo-ios            Swift SwiftUI          Flashcard app ("Flasherz")
  ~/alities-mobile     Swift SwiftUI          Trivia game app
  ~/obo-gen            Swift CLI              Deck generator (writes to Postgres)

MONITORING
  ~/server-monitor     Python 3.12 FastAPI    Dashboard backend + web + TUI
  ~/server-monitor-ios Swift SwiftUI          iOS/watchOS dashboard + widgets

ADVICE
  ~/adveyes            Python 3.12 FastAPI    Multi-tenant advice chatbot (Claude-powered)

DEPLOYMENT
  ~/Flyz               Docker + fly.toml      Hub repo for all Fly.io deploys

RETIRED
  ~/obo-server         (replaced by cardzerver)
  ~/alities-engine     (replaced by cardzerver)
```

### Port Registry (all localhost dev)

| Service | Port | Fly.io App | Live URL |
|---------|------|-----------|----------|
| nagzerver | 9800 | bd-nagzerver | https://bd-nagzerver.fly.dev |
| cardzerver | 9810 | bd-cardzerver | https://bd-cardzerver.fly.dev |
| adveyes | 9820 | (co-hosted) | https://bd-server-monitor.fly.dev/advice |
| server-monitor | 9860 | bd-server-monitor | https://bd-server-monitor.fly.dev |
| Postgres (Nagz) | 5433 | bd-postgres | bd-postgres.internal:5432 |
| Redis | 6379 | (Upstash) | fly-nagz-redis.upstash.io:6379 |
| nagz-web (Vite) | 5173 | (bundled) | (embedded in nagzerver) |

---

## 2. Configuration Consistency Audit

### Cross-Ecosystem Consistency Matrix

| Aspect | Status | Details |
|--------|--------|---------|
| **Port registry** | CONSISTENT | All services use documented 9800-9899 range |
| **METRICS_SPEC.md compliance** | CONSISTENT | nagzerver, cardzerver, adveyes, server-monitor all return `{"metrics": [...]}` |
| **Server-monitor YAML (local)** | CONSISTENT | All endpoints match actual service ports |
| **Server-monitor YAML (prod)** | CONSISTENT | Fly.io URLs match deployed apps |
| **Nagz API contract (web)** | CONSISTENT | orval auto-generates TS types from openapi.json |
| **Nagz API contract (iOS)** | CONSISTENT | 21 model files, all 40+ endpoints aligned with nagzerver |
| **cardzerver trivia contract** | CONSISTENT | alities-mobile Challenge matches ChallengeOut exactly |
| **cardzerver flashcard contract** | CONSISTENT | obo-ios OBODeckDetail matches FlashcardDeckOut exactly |
| **Status color system** | CONSISTENT | green/yellow/red/gray across web, TUI, iOS, watchOS |
| **Sticky warning behavior** | CONSISTENT | `had_error` tracked in backend, consumed by all frontends |

### Inconsistencies Found

| # | Issue | Repos Affected | Severity | Fix |
|---|-------|---------------|----------|-----|
| 1 | **Metric threshold color mismatch** | server-monitor-ios vs web+TUI | Medium | iOS `computedColor` returns `"yellow"` for threshold breach; web+TUI return `"red"`. Change iOS Models.swift:87 |
| 2 | **iOS missing `web_url` field** | server-monitor-ios | Low | `ServerSnapshot.swift` doesn't decode `web_url` sent by backend (silently dropped) |
| 3 | **iOS missing `lan_ip` field** | server-monitor-ios | Low | `StatusResponse.swift` doesn't decode `lan_ip` (not needed for production URL) |
| 4 | **iOS missing `sparkline_history`** | server-monitor-ios | Low | `Metric.swift` doesn't decode sparkline data (no sparkline UI on iOS yet) |
| 5 | **help.html server table outdated** | server-monitor | Low | Still lists alities-engine and OBO Server (both retired) |
| 6 | **obo-gen writes to legacy schema** | obo-gen vs cardzerver | Medium | obo-gen uses `obo` database with SERIAL IDs; cardzerver uses `card_engine` with UUIDs + JSONB. Migration documented but not implemented |
| 7 | **alities-mobile URL hardcoded** | alities-mobile | Low | No env var override for base URL (obo-ios has `OBO_API_URL`) |
| 8 | **Metrics endpoint paths inconsistent** | nagzerver vs cardzerver vs adveyes | Info | nagzerver: `/api/v1/metrics`, others: `/metrics`. Works fine but not uniform |
| 9 | **nagzerver missing health check in fly.toml** | nagzerver | Low | cardzerver has `[[http_service.checks]]` but nagzerver doesn't |
| 10 | **alities-mobile test references missing field** | alities-mobile | Low | Tests reference `status.providers` array that doesn't exist in EngineStatusResponse |
| 11 | **Env var prefix inconsistency** | obo-gen vs cardzerver | Info | obo-gen uses `OBO_DB_*`, cardzerver uses `CE_DB_*`, nagzerver uses `NAGZ_*` |
| 12 | **Bundle ID naming** | server-monitor-ios | Info | project.yml uses `ZerverMonitor`, CLAUDE.md says `ServerMonitor` |

---

## 3. Per-Repo Sync Contracts

### Nagz Ecosystem Sync

```
nagzerver (source of truth)
    │
    ├──► nagz-web: openapi.json → orval → TypeScript types + endpoint functions
    │    Sync command: cd ~/nagz-web && npm run api:generate
    │    220+ auto-generated model files, 28 endpoint modules
    │
    └──► nagz-ios: Manual model updates in Nagz/Models/*.swift (21 files)
         Must match: APIEndpoint.swift (40+ endpoints), Constants.swift (version)
         Version constant: clientAPIVersion = "1.0.0" must match server API_VERSION
```

| Change in nagzerver | Required actions |
|---------------------|-----------------|
| New optional response field | Add to nagz-ios model + regenerate nagz-web |
| Removed/renamed field | Update nagz-ios model + bump MIN_CLIENT_VERSION + regenerate nagz-web |
| New endpoint | Add APIEndpoint func + models in nagz-ios; auto-generated in nagz-web |
| Enum value added | Add case in nagz-ios Enums.swift; auto-generated in nagz-web |
| Schema migration | Run `alembic upgrade head` locally; auto-runs on deploy |

### Card-Engine Ecosystem Sync

```
cardzerver (source of truth)
    │
    ├──► obo-ios: GET /api/v1/flashcards → OBOClient.swift → FlashcardStore
    │    Models: OBOFlashcardsResponse, OBODeckDetail, OBOCardResponse
    │    Fallback: TopicGroup.sample (17 bundled decks)
    │
    ├──► alities-mobile: GET /api/v1/trivia/gamedata → GameService.swift
    │    Models: GameDataOutput, Challenge (field-for-field match with ChallengeOut)
    │    Also polls: GET /api/v1/ingestion/status
    │
    └──► obo-gen: Writes directly to Postgres (LEGACY obo schema, NOT cardzerver schema)
         Migration pending: obo-gen → cardzerver UUID/JSONB schema
```

| Change in cardzerver | Required actions |
|----------------------|-----------------|
| Flashcard adapter response shape | Update obo-ios OBOClient.swift + Models.swift |
| Trivia adapter response shape | Update alities-mobile GameModels.swift |
| New metric in /metrics | Auto-displays in server-monitor (no change needed) |
| Database schema change | Check obo-gen compatibility (still on legacy schema) |
| Port change | Update server-monitor servers.yaml (both local + prod) |

### Server-Monitor Ecosystem Sync

```
server-monitor backend (source of truth for /api/status)
    │
    ├──► static/index.html: Reads servers[], metrics[], had_error, web_url, lan_ip
    ├──► static/mini.html: Reads servers[], error, had_error
    ├──► server-monitor-ios: Reads StatusResponse, ServerSnapshot, Metric, MetricValue
    │    Missing fields: web_url, lan_ip, sparkline_history (silently dropped)
    │
    └──► config/servers.yaml: Defines what gets monitored
         Local: polls localhost:PORT
         Prod: polls Fly.io URLs + internal networking
```

---

## 4. Deployment Architecture

### Fly.io Container Map

| App | Container | Always On | Memory | Co-hosted | Health Check |
|-----|-----------|-----------|--------|-----------|-------------|
| bd-server-monitor | Python 3.12-slim | Yes (min=1) | 256MB | adveyes at /advice | None |
| bd-nagzerver | Python 3.12-slim + React build | No (min=0) | 512MB | nagz-web static | None (missing!) |
| bd-cardzerver | Python 3.12-slim | Yes (min=1) | 256MB | Standalone | GET /health every 30s |
| bd-postgres | postgres:16-alpine + volume | Always | 256MB | Standalone | TCP :5432 |

### Deploy Workflow (via ~/Flyz)

```bash
~/Flyz/scripts/deploy.sh <app-name>

# What happens:
# 1. Creates temp build context from source repo
# 2. Overlays Fly-specific Dockerfile + fly.toml + config
# 3. For nagzerver: bundles ~/nagz-web into build context
# 4. For server-monitor: bundles ~/adveyes into advice_app/
# 5. Runs: flyctl deploy --remote-only
```

### Config Overlay Pattern

Each app has two configs — local and production:

| App | Local Config | Production Config |
|-----|-------------|-------------------|
| server-monitor | `~/server-monitor/config/servers.yaml` (localhost URLs) | `~/Flyz/apps/server-monitor/config/servers.yaml` (Fly.io URLs) |
| nagzerver | `.env` or env vars (port 9800) | `fly.toml` env (PORT=8080) |
| cardzerver | env vars (CE_PORT=9810) | `fly.toml` env (CE_PORT=8080) |

### Production Networking

```
Internet ──► bd-server-monitor.fly.dev ──► container:8080
                ├── /           → static/index.html (dashboard)
                ├── /api/status → FastAPI (polls all services)
                ├── /advice     → adveyes sub-app
                └── /metrics    → self-monitoring

Internet ──► bd-nagzerver.fly.dev ──► container:8080
                ├── /           → nagz-web React SPA
                └── /api/v1/*   → FastAPI (68 endpoints)

Internet ──► bd-cardzerver.fly.dev ──► container:8080
                ├── /api/v1/flashcards  → obo-ios adapter
                ├── /api/v1/trivia      → alities-mobile adapter
                ├── /api/v1/studio      → content management
                └── /metrics            → server-monitor

Internal only:
  bd-postgres.internal:5432 ──► PostgreSQL 16
  fly-nagz-redis.upstash.io:6379 ──► Managed Redis
```

---

## 5. Benefits of Multi-Repo Structure for Context Management

| Benefit | Explanation |
|---------|-------------|
| **Context window efficiency** | Each CLAUDE.md loads 50-100 lines of project-specific context, not 500+ for a monorepo |
| **Language isolation** | Glob/Grep stays within one ecosystem. No Swift false positives when debugging Python |
| **Independent commit history** | Clean single-purpose commits per repo. `git log` shows only relevant changes |
| **Parallel Claude sessions** | Run Claude on nagzerver (Python) and nagz-ios (Swift) simultaneously, no conflicts |
| **Deployment isolation** | `~/Flyz/` owns Docker configs separately from source. Bad deploy config doesn't pollute source |
| **CLAUDE.md as contract** | Cross-project sync tables are explicit API contracts between repos |
| **Selective context** | Claude working on obo-ios only needs to know cardzerver's API shape, not its internals |
| **Test isolation** | Each repo has its own test suite: `pytest` (Python), `vitest` (TS), `swift test` / `xcodebuild test` (Swift) |

**Risk: Sync drift** — When one repo changes an API contract, no automated check ensures consumers are updated. Mitigation: CLAUDE.md sync tables + version checking (nagz has `clientAPIVersion` compatibility check).

**Recommendation:** The nagz ecosystem solves this best — openapi.json is auto-generated from nagzerver and orval auto-generates the TypeScript client. cardzerver and server-monitor could adopt the same pattern.

---

## 6. Componentization Opportunities

### Already Well-Componentized

| Component | Why It Works |
|-----------|-------------|
| `collectors/` module | Zero UI deps, clean ABC, usable by both TUI and web |
| `Shared/` in server-monitor-ios | Single source compiled into 4 targets (app, widget, watch, watch widget) |
| cardzerver adapters | Layer 2 adapters map unified schema to app-specific response shapes |
| orval codegen in nagz-web | Auto-generated TypeScript client from OpenAPI spec |

### Opportunities for Further Componentization

| Opportunity | Effort | Impact | Details |
|-------------|--------|--------|---------|
| **Shared metrics schema package** | Medium | High | Extract METRICS_SPEC.md to JSON Schema / OpenAPI → auto-gen Swift models for server-monitor-ios |
| **Publish collectors as library** | Low | Medium | `server-monitor-collectors` pip package, reusable for Prometheus exporters, CLI tools |
| **Decouple adveyes** | Low | Medium | Own Fly.io app (`bd-adveyes`), own Dockerfile. Simplifies server-monitor build |
| **obo-gen → cardzerver migration** | Medium | High | Update obo-gen to write to cardzerver's UUID/JSONB schema instead of legacy `obo` DB |
| **Unified env var convention** | Low | Low | Standardize on `{APP}_DB_HOST` pattern across all services |
| **Static CDN container** | Low | Low | nginx/Caddy serving index.html + mini.html with proper cache headers |

### Docker Container Opportunities on Fly.io

| New Container | Purpose | Justification |
|---------------|---------|---------------|
| **bd-adveyes** | Standalone advice app | Decouple from server-monitor; independent scaling; remove anthropic dep from monitor |
| **bd-redis** | Self-hosted Redis | Replace Upstash; lower latency on Fly private network; ~$2/mo |
| **bd-healthcheck** | Uptime bot | Lightweight pinger + email alerts; cheaper than always-on dashboard |
| **bd-static** | Static file server | nginx/Caddy for all web frontends; proper caching; free up Python from static serving |
| **bd-prometheus** | Metrics aggregator | Poll all /metrics endpoints; expose Prometheus format; integrate with Grafana Cloud free tier |

---

## 7. Metrics Endpoint Comparison

| Service | Path | Metrics Count | Auth | Warn Thresholds | Sparklines |
|---------|------|--------------|------|-----------------|------------|
| nagzerver | `/api/v1/metrics` | 27 | None | Yes (rps, memory, cpu, nags, deliveries) | Yes (rps) |
| cardzerver | `/metrics` | 3 | None | No | No |
| adveyes | `/metrics` | 3 | None | No | No |
| server-monitor | `/metrics` | 6 | None | Yes (servers_errored) | No |

All comply with METRICS_SPEC.md: `{"metrics": [{"key", "label", "value", "unit", ...}]}`

---

## 8. Database Topology

| Database | Host (local) | Host (prod) | Used By | Schema Mgmt |
|----------|-------------|-------------|---------|-------------|
| nagz | localhost:5433 | bd-postgres.internal:5432 | nagzerver | Alembic (16 migrations) |
| card_engine | localhost:5432 | bd-postgres.internal:5432 | cardzerver | Raw SQL files (5 migrations) |
| obo | localhost:5432 | (legacy) | obo-gen (legacy) | Manual |

Production Postgres (`bd-postgres`) hosts multiple databases: nagz, obo, alities, card_engine.
Init script: `~/Flyz/apps/postgres/init/create-databases.sql`

---

## 9. API Version Management

| Ecosystem | Strategy | Client Version | Server Version | Compatibility Check |
|-----------|----------|---------------|----------------|-------------------|
| Nagz | Explicit versioning | nagz-ios: `1.0.0`, nagz-web: `1.0.0` | nagzerver: API `1.0.0`, Server `0.2.0` | Yes — `/api/v1/version` endpoint, semver comparison, blocks on breaking |
| cardzerver | Adapter pattern | None | None | No — adapters maintain backward compatibility by mapping |
| server-monitor | Schema tolerance | None | None | No — Codable/JSON silently drops unknown fields |

---

## 10. Testing Coverage

| Repo | Framework | Test Count | Command |
|------|-----------|-----------|---------|
| nagzerver | pytest + pytest-asyncio | ~50+ | `uv run pytest` |
| nagz-web | vitest + testing-library | 126 | `npx vitest run` |
| nagz-ios | XCTest | 215 | `xcodebuild test -scheme Nagz` |
| cardzerver | pytest | ~10 | `uv run pytest` |
| server-monitor-ios | XCTest (SPM) | 40+ | `swift test` |
| alities-mobile | XCTest (SPM) | 37 | `swift test` |
| obo-ios | None | 0 | — |
| obo-gen | None | 0 | — |
| adveyes | None | 0 | — |

---

## 11. Complete File Path Reference

```
NAGZ ECOSYSTEM
~/nagzerver/
  src/nagz/server/main.py              # App factory + SPA serving
  src/nagz/server/routers/metrics.py   # /api/v1/metrics (27 metrics, RateCounter)
  src/nagz/models/tables.py            # 20+ SQLAlchemy ORM tables
  src/nagz/schemas/*.py                # 19 Pydantic schema modules
  src/nagz/core/config.py              # Settings (NAGZ_ env prefix, port 9800)
  src/nagz/core/version.py             # SERVER_VERSION, API_VERSION, MIN_CLIENT_VERSION
  openapi.json                         # Auto-generated OpenAPI 3.1.0 (211 KB)
  compose.yml                          # Local dev: Postgres 5433, Redis 6379
  alembic/versions/                    # 16 migration files

~/nagz-web/
  src/api/axios-instance.ts            # Axios config (VITE_API_URL, Bearer token)
  src/api/endpoints/**/*.ts            # 28 auto-generated endpoint modules (orval)
  src/api/model/**/*.ts                # 220+ auto-generated TypeScript types
  src/auth.tsx                         # AuthProvider (sessionStorage JWT)
  src/version.tsx                      # VersionProvider (API compat check)
  orval.config.ts                      # OpenAPI → TypeScript codegen config
  openapi.json                         # Copied from nagzerver

~/nagz-ios/
  Nagz/Config/AppEnvironment.swift     # Base URL (https://bd-nagzerver.fly.dev/api/v1)
  Nagz/Config/Constants.swift          # clientAPIVersion = "1.0.0"
  Nagz/Services/APIClient.swift        # Actor, auto-refresh, snake_case codec
  Nagz/Services/APIEndpoint.swift      # 40+ endpoint definitions
  Nagz/Models/*.swift                  # 21 Codable model files (~1,060 lines)
  project.yml                          # xcodegen (com.nagz.app, team NEAY582ME4)

CARD-ENGINE ECOSYSTEM
~/cardzerver/
  server/app.py                        # FastAPI + lifespan + /health + /metrics
  server/db.py                         # asyncpg pool + CRUD helpers
  server/models.py                     # Pydantic schemas (DeckOut, ChallengeOut, etc.)
  server/adapters/flashcards.py        # /api/v1/flashcards (obo-ios compat)
  server/adapters/trivia.py            # /api/v1/trivia (alities-mobile compat)
  server/adapters/studio.py            # /api/v1/studio (content management)
  server/providers/daemon.py           # IngestionDaemon (OpenAI trivia gen)
  server/family/                       # Family tree personalization
  schema/001_initial.sql               # Core unified schema
  schema/002_migrate_obo.sql           # OBO → cardzerver mapping

~/obo-ios/
  obo/OBOClient.swift                  # API client (OBO_API_URL env override)
  obo/Models.swift                     # Deck, Flashcard, TopicGroup
  obo/FlashcardStore.swift             # Data loading + sample fallback

~/alities-mobile/
  Alities/Sources/Models/GameModels.swift   # Challenge, GameDataOutput
  Alities/Sources/Services/GameService.swift # Hardcoded bd-cardzerver.fly.dev
  Alities/Sources/Models/EngineStatus.swift  # Ingestion daemon status

~/obo-gen/
  Sources/main.swift                   # CLI + OpenAI + Postgres (legacy obo schema)
  Package.swift                        # PostgresNIO dependency

MONITORING
~/server-monitor/
  web.py                               # FastAPI + collectors + /api/status
  monitor.py                           # Textual TUI
  config/servers.yaml                  # Local dev monitoring targets
  collectors/{base,http,redis,postgres}_collector.py
  static/{index,mini,help}.html        # Web frontends
  METRICS_SPEC.md                      # /metrics JSON contract

~/server-monitor-ios/
  Shared/Models.swift                  # StatusResponse, ServerSnapshot, Metric
  Shared/StatusService.swift           # Actor (bd-server-monitor.fly.dev)

ADVICE
~/adveyes/
  main.py                             # FastAPI + Claude chat + admin + /metrics
  prompts/default/*.md                 # Tenant system prompt files
  static/index.html                    # Chat web UI

DEPLOYMENT
~/Flyz/
  scripts/deploy.sh                    # Orchestrates all deploys
  apps/server-monitor/Dockerfile       # Bundles adveyes
  apps/server-monitor/fly.toml         # Always-on, 256MB
  apps/server-monitor/config/servers.yaml  # Production monitoring targets
  apps/nagzerver/Dockerfile            # Multi-stage: Node (React) + Python
  apps/nagzerver/fly.toml              # min_machines=0, 512MB
  apps/cardzerver/Dockerfile          # Python only
  apps/cardzerver/fly.toml            # min_machines=1, health check
  apps/postgres/Dockerfile             # postgres:16-alpine
  apps/postgres/init/create-databases.sql  # Creates nagz, obo, alities, card_engine DBs
```

---

## 12. Action Items (Prioritized)

| Priority | Item | Repos | Effort |
|----------|------|-------|--------|
| 1 | Fix iOS metric threshold color (yellow → red) | server-monitor-ios | 5 min |
| 2 | Migrate obo-gen to cardzerver schema | obo-gen, cardzerver | 2-4 hrs |
| 3 | Update help.html server table | server-monitor | 10 min |
| 4 | Add health check to nagzerver fly.toml | Flyz | 5 min |
| 5 | Add `web_url` to server-monitor-ios model | server-monitor-ios | 15 min |
| 6 | Add env var override to alities-mobile GameService | alities-mobile | 10 min |
| 7 | Fix alities-mobile test referencing missing providers field | alities-mobile | 15 min |
| 8 | Consider extracting METRICS_SPEC to OpenAPI schema | server-monitor | 1-2 hrs |
| 9 | Consider decoupling adveyes to own Fly.io app | adveyes, Flyz | 1 hr |
