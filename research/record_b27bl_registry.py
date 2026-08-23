#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REG = ROOT / 'BABA_BOT_RESEARCH_RESULTS_REGISTRY.md'
ENTRY = ROOT / 'research' / 'registry_entries' / 'B27BL.md'
MARKER = '## B27BL — 24H Temporal Transition Resolution Audit'
ANCHOR = '# REGIME DETECTOR FOUNDATION\n'

text = REG.read_text()
if MARKER in text:
    print('B27BL already recorded')
else:
    entry = ENTRY.read_text().strip()
    assert ANCHOR in text
    text = text.replace(ANCHOR, ANCHOR + '\n' + entry + '\n\n---\n\n', 1)
    REG.write_text(text)
    print('B27BL registry entry inserted')
