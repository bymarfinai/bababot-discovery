---
title: Product Vision
status: approved
version: 1.0
last_updated: 2026-07-31
owner: ceo
dependencies: []
related:
  - 02-MVP-SCOPE.md
  - 04-AI-PIPELINE.md
  - 05-DESIGN-INTELLIGENCE.md
---

# Product Vision

## What SlideCraft AI Is

An AI Presentation Designer — not a template filler, not a slide generator, not a chatbot with PowerPoint output.

The system works like a Presentation Designer and Art Director who:
- analyzes the communication objective,
- structures the narrative,
- decides the message per slide,
- directs the visual composition per slide,
- generates hero visuals when needed,
- builds editable layouts,
- reviews quality before showing anything.

## Pipeline

```
ChatGPT → MCP → Presentation Strategy → Story + Slide Intent
→ Art Direction per Slide → Hero Visual Generation
→ Editable Layout Engine → Web Editor → Editable PPTX
```

MCP is the control channel, not the source of design quality. Quality comes from the AI pipeline and design intelligence layer.

## Visual Quality Target

Output must approach the quality of slides designed by premium agencies (McKinsey, BCG, Apple Keynote). The difference: SlideCraft output is editable, not a flat image.

### What AI Generates

- Hero images, atmosphere, textures, conceptual product visuals, visual backgrounds.
- These are the "wow factor" — the visual that makes the slide feel premium.

### What Stays Native Editable

- Text, numbers, charts, tables, cards, logos, timelines, diagrams, callouts, lines, labels.
- These are never burned into AI-generated images.

### The Line

If a user needs to edit it later, it must be a native object. If it's purely atmospheric or visual storytelling, AI image generation is appropriate.

## Premium Slide Generation Standard

Quality contract — every slide must satisfy:

1. One slide, one message.
2. Headline ≤ 8 words.
3. Maximum one subheadline.
4. Maximum 3–5 bullet points.
5. One clear focal point per slide.
6. Specific art direction per slide — not generic.
7. No repetitive compositions.
8. No same composition mode on consecutive slides without justification.
9. Hero image supports the slide's message, not decoration.
10. Typography is part of the design, not just content delivery.
11. Whitespace is intentional.
12. Use layering, overlap, bold crops, scale contrast, visual tension, visual rhythm.
13. Data remains editable.
14. Original logos remain native assets.
15. Small text is never burned into AI images.
16. Complex technical diagrams are never delegated to image generation.
17. Output renders in editor and exports to editable PPTX.
18. Every slide passes quality review before display.

## What This Is Not

**Not a template engine.** The system does not:
```
Prompt → Pick template → Fill text → Done
```

**The actual pipeline:**
```
Prompt → Analyze communication objective → Structure narrative
→ Determine main message per slide → Determine focal point
→ Determine composition mode → Determine hero visual needs
→ Generate visual if needed → Build editable layout
→ Quality review → Display in editor
```

Every slide gets its own art direction. Composition variety is enforced — the system actively avoids repetition.

## Competitive Position

| Competitor | Their Approach | Our Difference |
|------------|----------------|----------------|
| Gamma | Template fill, fast but generic | Art-directed, premium visual quality |
| Beautiful.ai | Smart templates, limited customization | AI-driven composition, hero visual generation |
| Canva | Manual drag-and-drop, no AI narrative | Fully automated narrative-to-slide pipeline |
| Tome | AI-generated but flat/non-editable | Editable output with native objects |
| ChatGPT + PPTX plugin | Text-only, no visual design | Full visual design with image generation |

## Design Principles

1. **Content-first editing** — User edits content, layout engine re-resolves. User never manually positions objects.
2. **AI decides composition** — Layout and art direction are AI decisions, not user choices from a menu.
3. **Visual variety is mandatory** — System enforces composition variety across the deck.
4. **Editability is non-negotiable** — Every text, number, and data element must be editable post-generation.
5. **Quality over speed** — An extra 5 seconds of generation time for better art direction is always worth it.
