# Vendored third-party code and references

Plain copies, fetched as tarballs from codeload.github.com on 2026-11-24. Do not edit vendored
files; update by fetching a new pinned commit and recording it here.

| Upstream | Commit (date) | Copied to | What | Licence |
|---|---|---|---|---|
| [mforhm/max-gen-helper](https://github.com/mforhm/max-gen-helper) | `a7a05a72b07d218cdde6ac442d6d35ece4126d99` (2026-10-14, v0.1.2) | `tools/vendor/gencheck/` | `scripts/gencheck/gencheck.py`, `genflow.py` (static GenExpr checker, `--write-gendsp`) | MIT (`tools/vendor/gencheck/LICENSE`) |
| [Ableton/maxdevtools](https://github.com/Ableton/maxdevtools) | `5b39dec9a203d2747ff1d08e10c849742a4e654a` (2026-09-11) | `tools/vendor/maxdevtools/maxdiff/` | `maxdiff/*.py` + README (git textconv for `.maxpat`/`.amxd`/`.als`); `tests/`, `prep/`, images left out | MIT (`tools/vendor/maxdevtools/LICENSE.txt`) |
| Ableton/maxdevtools | same | `reference/m4l-production-guidelines.md` | M4L Production Guidelines. **One change:** image `src` paths rewritten to raw.githubusercontent.com URLs at the pinned commit (images not copied, 7.9 MB) | MIT |
| Ableton/maxdevtools | same | `reference/patch-code-standard.md` | Ableton's patch code standard | MIT |
| [ssdvtechno/maxpylang-claude-plugin](https://github.com/ssdvtechno/maxpylang-claude-plugin) | `a132b5b5ded48781908b0ea4e1e46de1527c7015` (2026-10-07) | `reference/m4l.md` | `skills/maxpylang/references/m4l.md` — compact M4L / `live.*` port reference. Note the upstream's own caveat that its device faces were not all opened in Max | MIT (`reference/m4l.md.LICENSE`) |

Not vendored (reasons in `docs/research/notes/m4l-toolchain-dependencies-2026-11-24.md`):
max-gen-helper's skill and hook (installed as a Claude Code plugin instead), gen-fmt and
GenExpr_VSCode (no licence file), m4l-typescript-base (GPL-3.0, legacy `js` target).
