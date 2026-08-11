# Shared Draw.io Engine Scripts (Upstream Reuse)

This directory contains **encapsulated** copies of select scripts from the
upstream [`Agents365-ai/drawio-skill`](https://github.com/Agents365-ai/drawio-skill)
repository (MIT License, © 2026 Agents365-ai), which we reuse verbatim as the
generic drawing backend for the ChipDraw skill suite.

They are **not modified** — per the upstream-sync strategy in
`docs/architecture.md` (建设方案 §6 / §15), the generic engine stays a
faithful snapshot so it can be re-synced or upstream-merged without conflict.
Chip-specific semantics, schemas, adapters and validators live in the parent
`chipdiagram/` package, never here.

## Reused scripts and their role in ChipDraw

| Script | Upstream purpose | ChipDraw usage |
| --- | --- | --- |
| `autolayout.py` | Graphviz deterministic layout (nodes + orthogonal edges) | SoC/IP/FSM node placement |
| `validate.py` | `.drawio` structural lint (dangling edges, overlaps, line-through-block) | Gate 3 layout quality check |
| `seqlayout.py` | Deterministic sequence-diagram geometry | Transaction sequence views |
| `drawiodiff.py` | Diagram diff (added/removed/changed) | `chipdiagram diff` |
| `shapesearch.py` | Search 10k+ official shapes for exact style strings | Chip symbol / icon lookup |
| `repair_png.py` | Fix truncated IEND chunk in `-e` PNG exports | Post-export PNG repair |
| `explain.py` | Reverse-describe an existing `.drawio` | Diagram QA / docs |
| `relabel.py` | Language variant / bulk text swap | EN ↔ 中文 bilingual labels |
| `restyle.py` | Re-theme an existing `.drawio` with a preset | Theme conversion |
| `encode_drawio_url.py` | Browser fallback (diagrams.net viewer/editor URL) | CLI-missing degradation |

## Resource-path layout (kept compatible with upstream)

These scripts resolve bundled resources relative to `chipdiagram/`:

- `shapesearch.py` → `chipdiagram/data/shape-index.json.gz`
- `restyle.py` / `autolayout.py` → `chipdiagram/styles/built-in/*.json`

Do not move these resources without updating the scripts.
