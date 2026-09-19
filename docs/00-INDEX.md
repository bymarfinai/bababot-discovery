---
title: SlideCraft AI — Documentation Index
status: approved
version: 1.0
last_updated: 2026-07-31
owner: architecture
---

# SlideCraft AI — Documentation Index

## Product

| File | Status | Description |
|------|--------|-------------|
| [01-PRODUCT-VISION.md](01-PRODUCT-VISION.md) | approved | Product vision, quality contract, pipeline philosophy |
| [02-MVP-SCOPE.md](02-MVP-SCOPE.md) | approved | MVP scope, constraints, what's in/out, user journey |

## Architecture

| File | Status | Description |
|------|--------|-------------|
| [03-SYSTEM-ARCHITECTURE.md](03-SYSTEM-ARCHITECTURE.md) | draft | Stack, deployment, infrastructure, free-tier strategy |
| [04-AI-PIPELINE.md](04-AI-PIPELINE.md) | draft | 3-pass AI pipeline, prompt templates, BYOK |
| [05-DESIGN-INTELLIGENCE.md](05-DESIGN-INTELLIGENCE.md) | draft | Communication objectives, Design DNA, composition engine |
| [06-LAYOUT-ENGINE.md](06-LAYOUT-ENGINE.md) | draft | Layout registry, slot system, constraint resolution |
| [07-EDITOR-ARCHITECTURE.md](07-EDITOR-ARCHITECTURE.md) | draft | Editor philosophy, HTML/CSS renderer, editing model |
| [08-SCENE-GRAPH.md](08-SCENE-GRAPH.md) | draft | Deck → Slide → Layer → Object hierarchy, TypeScript types |
| [09-ASSET-PIPELINE.md](09-ASSET-PIPELINE.md) | draft | Image generation, asset storage, BYOK image providers |
| [10-MCP-SPEC.md](10-MCP-SPEC.md) | draft | MCP tool definitions, ChatGPT integration protocol |
| [11-PPTX-EXPORT.md](11-PPTX-EXPORT.md) | draft | PptxGenJS mapping, font fallback matrix, fidelity rules |
| [12-DATABASE.md](12-DATABASE.md) | draft | Supabase schema, JSONB storage, RLS policies |
| [13-API-CONTRACTS.md](13-API-CONTRACTS.md) | draft | Server actions, Edge Runtime, API routes |

## Execution

| File | Status | Description |
|------|--------|-------------|
| [14-SPRINT-PLAN.md](14-SPRINT-PLAN.md) | draft | 10-week sprint breakdown, work items, milestones |
| [15-DECISIONS.md](15-DECISIONS.md) | draft | Architecture Decision Records (ADR) |
| [16-BACKLOG.md](16-BACKLOG.md) | draft | Post-MVP features, parking lot |
| [17-CHANGELOG.md](17-CHANGELOG.md) | approved | All changes to documentation |

## Source Mapping

Content from Architecture v1–v5 is distributed as follows. Each topic has exactly one canonical file — all other references are cross-links only.

| Source Document | Maps To | Notes |
|-----------------|---------|-------|
| v1 — Software Architecture | 03-SYSTEM-ARCHITECTURE.md | Stack, deployment, Vercel/Supabase config |
| v1 — Software Architecture | 12-DATABASE.md | Schema, JSONB decision, RLS |
| v1 — Software Architecture | 13-API-CONTRACTS.md | Server actions, API routes |
| v2 — Layout Engine & Design System | 06-LAYOUT-ENGINE.md | Layouts, slots, constraints |
| v2 — Layout Engine & Design System | 08-SCENE-GRAPH.md | Object model, type definitions |
| v3 — AI Pipeline | 04-AI-PIPELINE.md | 3-pass pipeline, prompt design |
| v3 — AI Pipeline | 09-ASSET-PIPELINE.md | Image generation planning |
| v4 — Design Intelligence | 05-DESIGN-INTELLIGENCE.md | DNA, composition, visual language |
| v5 — Editor Architecture | 07-EDITOR-ARCHITECTURE.md | Editor model, operations, renderer |
| v5 — Editor Architecture | 08-SCENE-GRAPH.md | Scene graph detail, operation types |
| MVP Build Spec | 02-MVP-SCOPE.md | Scope, user journey, constraints |
| MVP Build Spec | 14-SPRINT-PLAN.md | Sprints, work breakdown |
| MVP Build Spec | 15-DECISIONS.md | ADRs extracted from decisions |

## Content Disposition

What happens to Architecture v1–v5 content:

| Content | Disposition | Reason |
|---------|-------------|--------|
| Product vision, quality standard | **New** in 01-PRODUCT-VISION.md | Upgraded per CEO directive — premium visual, MCP-first |
| MVP scope, user journey, batasan | **Migrated** to 02-MVP-SCOPE.md | Extracted from MVP Build Spec |
| Stack decisions (Next.js, Supabase, Vercel) | **Keep** in 03-SYSTEM-ARCHITECTURE.md | Unchanged |
| 3-pass AI pipeline | **Simplify** in 04-AI-PIPELINE.md | Remove duplicated explanations |
| Design DNA, composition engine | **Keep** in 05-DESIGN-INTELLIGENCE.md | Core IP |
| Layout registry, 10 layouts | **Keep** in 06-LAYOUT-ENGINE.md | Core IP |
| Editor philosophy, content-first | **Keep** in 07-EDITOR-ARCHITECTURE.md | Core IP |
| Scene graph types | **Keep** in 08-SCENE-GRAPH.md | Merge from v2 + v5 |
| Smart Components | **Post-MVP** in 16-BACKLOG.md | Cut from MVP |
| Drag/resize interaction | **Post-MVP** in 16-BACKLOG.md | Cut from MVP |
| AI chat sidebar | **Post-MVP** in 16-BACKLOG.md | Cut from MVP |
| Composition variants | **Post-MVP** in 16-BACKLOG.md | Cut — 1 default per layout |
| MCP tool spec | **Post-MVP** in 10-MCP-SPEC.md | Documented but not built for MVP |
| Future vision sections (all v1-v5) | **Delete** | Speculative — not actionable |
| Critique sections (all v1-v5) | **Delete** | Served their purpose in review |

## Rules

1. **Single source of truth** — Each topic explained fully in one file only. Others cross-reference.
2. **Delta-only updates** — Never rewrite an approved document. Patch, bump version, update changelog.
3. **No duplication** — If you find yourself writing something that exists in another file, link to it.
4. **Cross-reference format** — `See [06-LAYOUT-ENGINE.md](06-LAYOUT-ENGINE.md) § Composition Resolution`
5. **Change workflow** — Patch file → bump version → update 17-CHANGELOG.md → update dependencies if needed.
