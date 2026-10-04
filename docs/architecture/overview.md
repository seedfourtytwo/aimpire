# Architecture overview

Status: planning baseline, 2026-10-04. Derived from ADRs 0002–0009.

## System context

```mermaid
flowchart LR
  subgraph Browser["Browser (laptop / phone)"]
    UI["Web client<br/>React panels + PixiJS map"]
  end
  subgraph Local["Local machine (127.0.0.1)"]
    API["FastAPI<br/>REST + WebSocket deltas"]
    SCHED["Cognition scheduler<br/>asyncio barrier, budgets"]
    SIM["Simulation core<br/>pure, deterministic, single-thread"]
    DB[("runs/&lt;id&gt;/run.db<br/>SQLite + FTS5")]
    BLOB[("blobs/<br/>raw LLM I/O, checkpoints")]
  end
  subgraph Providers["Model providers (per-civ profiles)"]
    MOCK["mock / rule / recorded"]
    ANT["Anthropic API"]
    OAI["OpenAI-compatible:<br/>Ollama, llama.cpp, OpenRouter"]
  end
  PAGES["GitHub Pages<br/>static replay demo"]

  UI <--> API
  API --> SIM
  SIM --> SCHED
  SCHED --> MOCK & ANT & OAI
  SCHED -->|validated proposals| SIM
  SIM --> DB
  SCHED --> BLOB
  SIM -->|export replay bundle| PAGES
  PAGES -.ReplaySource.-> UI
```

## The cognition round (research mode)

```mermaid
sequenceDiagram
  participant Sim
  participant Proj as Observation projection
  participant Sched as Scheduler (barrier)
  participant P as Provider (per civ)
  participant Val as Validator
  Sim->>Proj: tick T = round end → freeze per-civ Observation (hash)
  Proj->>Sched: CognitionRequest[civ A], [civ B]
  par civ A
    Sched->>P: complete(obs, schema) — budget reserved
  and civ B
    Sched->>P: complete(obs, schema)
  end
  P-->>Sched: raw → parse (≤1 repair) | timeout → no_action
  Sched->>Val: proposals (seeded civ order)
  Val-->>Sim: accepted tasks + recorded rejections
  Sim->>Sim: commit at T+1, execute in world time
```

Key rules:
- **The sim never waits on wall-clock time.** Latency is recorded and never turned into turns.
- **Truth, evidence and belief are separate types.** `hidden_cause` and other civilizations' private data cannot be represented in an Observation.
- **Speech and visions are quoted data inside the observation,** never system-prompt content.

## Module map (`sim/src/aimpire/`)

| Package | Responsibility | May import |
|---|---|---|
| `sim/` | state, ids, fixed-point, rng, hashing, tick phases, fields, agents, knowledge, actions (schema/validate/execute), rules loader | stdlib, numpy, pydantic (contracts) |
| `cognition/` | scheduler, providers, prompt rendering, budgets, qualification | `sim`, `contracts` |
| `persistence/` | SQLite, migrations, blobs, checkpoints, replay, branching | `sim`, `contracts` |
| `contracts/` | Pydantic API/WS/proposal models → `schema/` | pydantic |
| `api/` | FastAPI routes, WebSocket stream | all of the above |
| `cli/` | `aimpire run / replay / branch / batch / qualify / export / serve` | all |

## Data flow for inspection

Every consequence is linkable:

`Intervention|NaturalCause → Event (truth) → Evidence (per witness) → Claim/Belief → Observation (hash) → Decision (prompt hash, raw blob, parsed, validation) → Task → Ledger entries / new Events`

`GET /runs/{id}/trace/{event_id}` walks this graph. The web client's Link Tracer renders it.

## Extension points (named, not built)
- births and aging
- multiple settlements per civilization
- institutions as carriers
- hydrology and irrigation
- rules v2 (metallurgy and later eras)
- map chunking for 256² worlds
- faction minds
- interactive asynchronous play mode
- Godot map renderer consuming the replay/delta contract
