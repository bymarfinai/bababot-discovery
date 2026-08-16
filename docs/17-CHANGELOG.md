---
title: Changelog
status: approved
version: 1.0
last_updated: 2026-07-31
owner: architecture
---

# Changelog

## 2026-07-31 — Documentation System Initialized

### Created
- `00-INDEX.md` v1.0 — Documentation index, source mapping, content disposition, rules
- `01-PRODUCT-VISION.md` v1.0 — Product vision locked: AI Presentation Designer, MCP pipeline, 18-point quality standard
- `02-MVP-SCOPE.md` v1.0 — MVP scope: what's in, what's out, constraints, success criteria
- `17-CHANGELOG.md` v1.0 — This file

### Decisions
- Adopted modular documentation: 17 files, single source of truth per topic
- Established delta-only update rule for approved documents
- Mapped Architecture v1–v5 content to new file structure (see 00-INDEX.md § Source Mapping)
- Cut "Future Vision" and "Critique" sections from all v1-v5 docs — not migrating

### Product Vision Changes (vs. Architecture v1-v5)
- **Elevated MCP to primary pipeline entry point**: ChatGPT → MCP → Pipeline → Editor → PPTX
- **Added 18-point Premium Slide Generation Standard** as binding quality contract
- **Added art direction per slide** as mandatory pipeline stage
- **Added hero visual generation** as first-class pipeline stage
- **Explicitly prohibited template-engine behavior** — composition variety enforced
- **Clarified AI/native boundary**: hero images = AI, text/data/diagrams = native editable

### Pending
- Files 03–16 remain `draft` status — content to be migrated from v1-v5
