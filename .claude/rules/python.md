---
paths:
  - "**/*.py"
---

# Python — always apply

Full rationale and more patterns: `python-best-practices` skill. Verify: `ruff check` / `mypy`.

- ✅ DO: type every parameter and return (`-> None` included). ❌ DON'T: `**kwargs: Any` or an
  untyped signature.
- ✅ DO: `if TYPE_CHECKING:` + `from __future__ import annotations` for type-only imports (avoids
  circular imports).
- ✅ DO: frozen value objects — `ConfigDict(frozen=True)` (pydantic) or `@dataclass(frozen=True)`.
  Update via `.model_copy(update={...})`, never in-place mutation.
- ✅ DO: `raise NewError(...) from exc` (or `from None` when deliberate) — never a bare `raise
  NewError(...)` that drops the original cause.
- ✅ DO: early return — `if bad: return; ...rest` — not a nested `if/else` tree.
- ✅ DO: 4+ parameters → a frozen dataclass/model (`run(opts: RunOpts)`), not a long positional
  signature (this project caps functions at **3** parameters — stricter than the skill's 6).
- ✅ DO: zero hardcoded strings/numbers/URLs/paths inline — an `Enum` (finite choices) or a config
  constant.
- ❌ DON'T: module-level mutable globals — a module-level frozen config instance instead.
- ❌ DON'T: third-party async runtimes or bare `create_task()` for fire-and-forget — pure
  `asyncio`, `TaskGroup` for structured concurrency, await or store every task handle.

## media-dedup — project specifics

These bind this repository on top of the generic rule above. Enforced by `pyproject.toml`
(ruff `ALL`, pylint, mypy strict) — run `check` (devcontainer cheatsheet) before declaring done.

- ✅ DO: **at most 200 lines per file** (pylint `max-module-lines`) — split into modules, classes and
  helpers beyond that. Tests included.
- ✅ DO: **at most 3 parameters per function** (ruff/pylint `max-args` and
  `max-positional-arguments`) — otherwise a frozen parameter object.
- ✅ DO: code, comments, docstrings and log messages in American English; every string shown to
  the user goes through gettext `_()` (`media_dedup.i18n`) and gets a French translation in
  `src/media_dedup/i18n/locales/fr/LC_MESSAGES/media_dedup.po` (`i18n_update`).
- ✅ DO: Google-style docstrings on every module, class and function — "what is not documented
  does not exist". Every CLI command and option carries a `help=` text.
- ✅ DO: long text (HTML, the default `config.toml`) lives in `src/media_dedup/**/templates/`, loaded
  by path — never inline.
- ✅ DO: every mount point path comes from `media_dedup.paths` (overridable through
  `MEDIA_DEDUP_*_DIR`), never a literal `/data`, `/journal`, ...
- ❌ DON'T: write anything in the working tree at runtime or in tests — `tmp_path` / `/tmp` only
  (zero junk in the repository).
