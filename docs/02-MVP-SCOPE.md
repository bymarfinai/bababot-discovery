---
title: MVP Scope
status: approved
version: 1.0
last_updated: 2026-07-31
owner: ceo
dependencies:
  - 01-PRODUCT-VISION.md
related:
  - 03-SYSTEM-ARCHITECTURE.md
  - 14-SPRINT-PLAN.md
---

# MVP Scope

## Target User

Startup founders and small business owners who need pitch decks, company profiles, or proposals — no design skills, can't afford a designer. Currently frustrated with Canva (layout breaks on edit) or Gamma (generic output).

## Core Problem

"I need a professional presentation, but I'm not a designer, and everything I make looks like a template."

## MVP Use Cases

1. Create a pitch deck from a natural language prompt.
2. Review and edit the outline before slides are generated.
3. Edit slide content (text, images) without breaking the design.
4. Request high-level AI revision ("more premium", "change theme").
5. Export to editable PPTX.

## User Journey

```
Login (magic link) → Dashboard → "Create New Deck"
→ Prompt input + Goal selection (Persuade/Inform/Establish/Propose)
→ Loading ~8-15s → Outline appears
→ Review outline (reorder, edit titles, add/remove slides) → "Generate Slides"
→ Slides appear progressively (~3-5s per slide)
→ Edit in editor (click text to edit, click image to replace, AI preset buttons)
→ Auto-save → Export PPTX
```

## What's In (MVP)

### Generation
- Natural language prompt → structured outline → slides
- 3-pass AI pipeline (Analyze+Plan → Design+Write → Validate)
- See [04-AI-PIPELINE.md](04-AI-PIPELINE.md)
- 4 communication goals: Persuade, Inform, Establish, Propose
- AI hero image generation (optional, BYOK)
- 10 layout types — see [06-LAYOUT-ENGINE.md](06-LAYOUT-ENGINE.md)
- 3 Design DNA presets: editorial-premium, corporate-clean, startup-bold
- 3 themes: light-neutral, dark-navy, warm-editorial

### Editor
- Content-first editing: click text to edit inline
- Image replacement: click → upload or AI generate
- 3 AI preset buttons: Change Theme, Change DNA, Regenerate Slide
- Slide thumbnail strip
- Undo/redo (12 operation types) — see [07-EDITOR-ARCHITECTURE.md](07-EDITOR-ARCHITECTURE.md)
- Auto-save to Supabase

### Export
- Client-side PPTX via PptxGenJS — see [11-PPTX-EXPORT.md](11-PPTX-EXPORT.md)
- Font fallback matrix (web → PPTX safe fonts)

### Infrastructure
- Supabase Free: Auth (magic link), PostgreSQL, Storage
- Vercel Free: hosting, Edge Runtime for AI actions
- BYOK: user provides own API keys for LLM and image generation
- Zero mandatory paid services

## What's Out (MVP)

| Feature | Status | Rationale |
|---------|--------|-----------|
| Smart Components | Post-MVP | Rendered as Groups for now |
| Object drag/resize | Post-MVP | Content-first editing sufficient |
| AI chat sidebar | Post-MVP | 3 preset buttons cover core needs |
| Composition variants | Post-MVP | 1 default composition per layout |
| MCP integration | Post-MVP | See [10-MCP-SPEC.md](10-MCP-SPEC.md) — documented, not built |
| Real-time collaboration | Post-MVP | Single user per deck |
| Animation/transitions | Post-MVP | Static slides only |
| Presenter mode | Post-MVP | Not needed for generation product |
| Brand kit upload | Post-MVP | Manual theme selection |
| Multi-language UI | Post-MVP | English UI, any content language |
| Auto image generation | Post-MVP | BYOK optional, deck works without images |

## Constraints

- **Timeline:** 8-10 weeks, 2-4 engineers
- **Budget:** Infrastructure ≈ Rp0/month (free tiers only)
- **No paid services required at launch** — LLM and image generation are BYOK
- **Architecture frozen** — v1-v5 architecture is final, no new engines or abstractions

## MVP Success Criteria

A user can:
1. Type a prompt
2. Review an outline
3. See premium-quality slides generated
4. Edit content without breaking layout
5. Export an editable PPTX

If all five work, MVP ships.

## Quality Gate

Every generated slide must pass the 18-point Premium Slide Generation Standard defined in [01-PRODUCT-VISION.md](01-PRODUCT-VISION.md) § Premium Slide Generation Standard.
