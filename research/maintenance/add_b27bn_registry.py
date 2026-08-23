#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REG = ROOT / 'BABA_BOT_RESEARCH_RESULTS_REGISTRY.md'
ENTRY = ROOT / 'research' / 'registry_entries' / 'B27BN.md'
MARK = '# B27BN — 24H Swing-Boundary Invalidation Audit'
ANCHOR = '# REGIME DETECTOR FOUNDATION\n'

text = REG.read_text()
if MARK in text:
    print('B27BN already present; no change.')
    raise SystemExit(0)
entry = ENTRY.read_text().strip()
assert ANCHOR in text, 'registry foundation anchor missing'
text = text.replace(ANCHOR, ANCHOR + '\n' + entry + '\n\n---\n\n', 1)
REG.write_text(text)
print('Inserted B27BN into master registry.')
