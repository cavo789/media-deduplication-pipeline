# media-dedup

Find and safely clean duplicate photos and videos spread over several folders and disks — from
one `docker run`, on Windows (PowerShell) or WSL.

🇫🇷 [Version française](README_FR.md)

- **Exact duplicates** — same size and same SHA-256, compared again byte for byte right before
  any deletion. Found across folders *and* disks (`C:` and `D:` in the same run).
- **Broken files** — empty files, images that cannot be decoded (truncated JPEG, …), videos that
  cannot be opened.
- **Reversible** — every action is journaled; `undo` restores every deleted copy from the copy
  that was kept, and every quarantined file from the quarantine.
- **Never touched** — bursts and "similar" photos, sidecar files (`.xmp`, `.aae`, `.thm`),
  protected folders.

## Contents

- [How it keeps your photos safe](#how-it-keeps-your-photos-safe)
- [Quick start](#quick-start)
- [Mount points](#mount-points)
- [Commands](#commands)
- [Configuration](#configuration)
- [Warnings](#warnings)
- [Development](#development)

## How it keeps your photos safe

| Step | Guarantee |
|---|---|
| `audit` | Read-only: mount your folders with `:ro` and Docker itself forbids any write. |
| Which copy is kept | Deterministic: a protected folder, then your preferred folders (in order), then a name that does not look like a copy (`IMG (1).jpg`, `IMG - Copie.jpg`, …), the oldest date, the shortest path. |
| Before each deletion | The kept copy must still exist and still be byte-for-byte identical — otherwise the file is skipped. |
| Each action | Written to the journal *before* (`pending`) and *after* (`done`) it happens: an interruption never loses track. |
| Duplicates | Really deleted (the space is freed immediately); `undo` rebuilds them from the kept copy, date included, even across disks. |
| Unreadable files | Moved to the quarantine, never deleted outright; `purge` deletes them for good when you are sure. |
| Every group | Always keeps at least one copy. |

## Quick start

**1. Build the image** (from a clone of this repository):

```bash
docker build --tag media-dedup .
```

**2. Create a folder for the tool's data** — configuration, journal, quarantine, reports:

```powershell
mkdir "$HOME\media-dedup\config", "$HOME\media-dedup\journal", "$HOME\media-dedup\quarantine", "$HOME\media-dedup\reports"
```

**3. Audit** (read-only — note the `:ro`). Each folder `X:\path` is mounted on `/data/x/path`,
which lets the tool show you the real Windows paths. Paths with spaces are fine between quotes.

```powershell
docker run --rm -it `
  -v "C:\Family Photos:/data/c/Family Photos:ro" `
  -v "C:\Users\Public\Pictures:/data/c/Users/Public/Pictures:ro" `
  -v "D:\backup:/data/d/backup:ro" `
  -v "$HOME\media-dedup\config:/config" `
  -v "$HOME\media-dedup\reports:/reports" `
  -v media-dedup-cache:/cache `
  media-dedup audit
```

**4. Read the report**: double-click `%USERPROFILE%\media-dedup\reports\index.html` — no server
needed. Start with the *folder pairs* table: which folder keeps its copies, which folder loses them.

**5. Clean** — the same folders **without `:ro`**, plus the journal and the quarantine:

```powershell
docker run --rm -it `
  -v "C:\Family Photos:/data/c/Family Photos" `
  -v "C:\Users\Public\Pictures:/data/c/Users/Public/Pictures" `
  -v "D:\backup:/data/d/backup" `
  -v "$HOME\media-dedup\config:/config" `
  -v "$HOME\media-dedup\journal:/journal" `
  -v "$HOME\media-dedup\quarantine:/quarantine" `
  -v "$HOME\media-dedup\reports:/reports" `
  -v media-dedup-cache:/cache `
  media-dedup clean
```

`clean` shows the summary and asks for confirmation (`--yes` skips it). Changed your mind?
Run the same command with `undo` instead of `clean`.

**From WSL**, use Linux paths and run as yourself so new files belong to you:

```bash
docker run --rm -it --user "$(id -u):$(id -g)" \
  -v "/mnt/c/Family Photos:/data/c/Family Photos:ro" \
  -v "$HOME/media-dedup/reports:/reports" \
  media-dedup audit
```

## Mount points

| Mount | Content | Needed |
|---|---|---|
| `/data/<drive>/<path>` | The folders to analyse (`C:\Photos` → `/data/c/Photos`). | always; `:ro` for `audit` |
| `/config` | `config.toml` only — created, commented, on first run. | optional |
| `/journal` | One JSONL journal per clean. | **required** by `clean`, `undo`, `history` |
| `/quarantine` | Unreadable files set aside by `clean`. | when broken files exist |
| `/reports` | One folder per run (`report.html`, previews) and `index.html`. | optional |
| `/cache` | SQLite index: later audits only read new or changed files. | optional, recommended |

Missing mounts are explained by 💡 tips. The image also runs with `--read-only --tmpfs /tmp`.

## Commands

| Command | What it does |
|---|---|
| `audit` | Find exact duplicates and broken files. Never writes to `/data`. |
| `clean` | Audit, confirm, then delete duplicate copies, delete empty files and quarantine unreadable ones. |
| `undo [RUN]` | Restore every file of a clean run (the latest by default). |
| `history` | List the clean runs: files deleted, space freed, quarantine, restores. |
| `reports [--prune N]` | List the reports and refresh `index.html`; `--prune N` keeps the N most recent. |
| `purge [RUN]` | Permanently delete the quarantine of a run (of every run by default). |
| `config` | Show every setting, where it comes from, and the state of each mount point. |

Global options go **before** the command: `media-dedup --locale fr audit`.

| Option | Meaning |
|---|---|
| `--locale en\|fr` | Interface language (English by default). |
| `--verbosity error\|warning\|info\|debug` | How much to log. |
| `--color auto\|always\|never` | ANSI colours (`NO_COLOR` is honoured). |
| `--prefer PATH` | (`audit`, `clean`) Folder whose copies are kept first; repeatable, ordered. |
| `--protect PATH` | (`audit`, `clean`) Folder never modified; its files are the copies kept. |
| `--exclude PATH` | (`audit`, `clean`) Folder never analysed. |
| `--yes`, `-y` | (`clean`, `purge`) Do not ask for confirmation. |

`media-dedup --help` and `media-dedup <command> --help` document everything, in both languages.

## Configuration

`/config/config.toml` is created on first run. Precedence, from the strongest: command-line
options, then `MEDIA_DEDUP_<SECTION>__<KEY>` environment variables (e.g.
`MEDIA_DEDUP_GENERAL__LOCALE=fr`; lists as JSON arrays), then the file, then the defaults.

```toml
[general]
locale = "fr"          # en | fr
verbosity = "info"     # error | warning | info | debug
color = "auto"         # auto | always | never

[folders]              # host paths, between 'single quotes'
preferred = ['C:\Family Photos', 'C:\Users\Public\Pictures']
protected = []
excluded = ['D:\backup']

[clean]
confirm = true
```

- **`preferred`**: their copies are kept first, in this order.
- **`protected`**: never modified — and their files are always the copies kept, so identical
  files *elsewhere are deleted*. Think "master library".
- **`excluded`**: never analysed. Use it for a real backup that must stay a second copy.

Write Windows paths between **single quotes**: in double quotes, TOML turns `\b` of `"D:\backup"`
into a control character (the tool refuses such a path rather than ignoring it).

## Warnings

- **Real backup**: if `D:\backup` must remain a second copy of your photos, exclude it (or do
  not mount it). Otherwise the tool, rightly, sees its files as duplicates.
- **OneDrive "Files On-Demand"**: analysing a folder whose files are online-only downloads them
  all. Make them available offline first, or leave that folder out.
- **Windows drives are slow through Docker**: the first audit reads every image and every
  file that shares its size with another one. With `-v media-dedup-cache:/cache` the next audits
  only read new or changed files.
- **Run with `-it`**: without a terminal, `clean` cannot ask for confirmation (use `--yes`) and
  colours are off.

## Development

Open the repository in the devcontainer (VS Code, *Reopen in Container*). Every new terminal
shows the cheatsheet of helper commands (`welcome` redraws it):

| Helper | Purpose |
|---|---|
| `check` | The full quality gate: pre-commit (ruff, mypy strict, pylint, shellcheck, shfmt, hadolint) then the tests with ≥ 90 % branch coverage. |
| `format`, `tests` | Auto-fix formatting; run targeted tests. |
| `dedup …`, `demo` | Run the tool from the sources against `/tmp/media-dedup/`; `demo` builds a sample tree and audits it. |
| `reports`, `reports_stop` | Serve the HTML reports on a free port chosen by the OS. |
| `image`, `e2e`, `dive`, `dive_ci` | Build the image, run the end-to-end tests, inspect or gate its layers. |
| `i18n_extract`, `i18n_update` | Refresh the gettext catalogs after changing a user-facing string. |
| `todos` | List the open backlog (`.todos/`, see `/todo` and `/todo-plan`). |

Code rules (enforced by the tooling): everything typed, at most 200 lines per file and 3
parameters per function, code in English, every user-facing string translated through gettext.
Caches never land in the repository (they live in `/tmp`).

The roadmap — near-duplicates, sharpness, bursts, review UI, … — is in
[.todos/plan.md](.todos/plan.md).
