---
type: "query"
date: "2026-09-18T09:00:58.887182+00:00"
question: "Seven architecture questions about Phase 2, the orchestrator, Phase 1, spectral fixtures, module boundaries, and slskd isolation"
contributor: "graphify"
source_nodes: ["Phase 2 — Hybrid Hunt", "Pipeline orchestrator", "Phase 1 — Input Analysis", "Spectral anti-fraud check", "fraud_128.flac fixture", "slskd REST client", "Atomic filesystem helpers"]
---

# Q: Seven architecture questions about Phase 2, the orchestrator, Phase 1, spectral fixtures, module boundaries, and slskd isolation

## Answer

Graph findings: Phase 2 receives Phase 1 output, calls query cleaning and the slskd REST client, then passes the acquired artifact to Phase 3 and AcoustID indirectly. The Pipeline orchestrator directly wires all five phase workers, TrackJob, and JobEvent; file safety is reached through phase5_polish and Atomic filesystem helpers, not by a direct edge. Phase 1 unifies URL probing and batch scanning before the Phase 2 hunt. Spectral fixtures connect directly to Generated audio fixtures and FRAUD verdict, then indirectly to the M4 milestone, spectral gate, fallback triggers, and Phase 4; the weak fixture connectivity is a documentation gap. The graph supports splitting spectral analysis into detector, verdict policy, routing, and fixtures; splitting Phase 1 into URL and batch adapters behind one normalized facade; and isolating the slskd REST client behind a typed interface while keeping hunt policy and scoring separate.

## Source Nodes

- Phase 2 — Hybrid Hunt
- Pipeline orchestrator
- Phase 1 — Input Analysis
- Spectral anti-fraud check
- fraud_128.flac fixture
- slskd REST client
- Atomic filesystem helpers