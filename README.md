# media-dedup

Find and safely clean duplicate photos and videos spread over several folders and disks — from
one `docker run`, on Windows (PowerShell) or WSL.

🇫🇷 [Version française](README_FR.md)

## Quick start

With Docker installed, one command audits a folder:

```powershell
docker run --rm -it -v "C:\Photos:/data/c/Photos:ro" cavo789/media-dedup audit
```

It lists the duplicate and broken photos and videos of `C:\Photos`, and changes nothing: `:ro`
(read-only) makes Docker itself forbid any write. The first run downloads the image by itself.

What it does:

- **Exact duplicates** — same size and same SHA-256, compared again byte for byte right before
  any deletion. Found across folders *and* disks (`C:` and `D:` in the same run).
- **Broken files** — empty files, images that cannot be decoded (truncated JPEG, …), videos that
  cannot be opened.
- **Reversible** — every action is journaled; `undo` restores every deleted copy from the copy
  that was kept, and every quarantined file from the quarantine.
- **Never touched** — bursts and "similar" photos, sidecar files (`.xmp`, `.aae`, `.thm`),
  protected folders.

## Contents

- [What you see while it runs](#what-you-see-while-it-runs)
- [Reading the result](#reading-the-result)
- [Going further](#going-further)
- [How it keeps your photos safe](#how-it-keeps-your-photos-safe)
- [Mount points](#mount-points)
- [Commands](#commands)
- [Configuration](#configuration)
- [Warnings](#warnings)
- [Development](#development)

## What you see while it runs

Each step shows one line of progress and, below it in grey, what it really does:

```text
⠴ Proving identity (full SHA-256) ━━━━━━━━━╸━━━━━━━━ 11,707/23,907 elapsed 0:00:47 · about 0:02:19 left
  Reads the remaining candidates in full: same SHA-256 means identical, byte for byte.
```

- **`11,707/23,907`**: files done in *this step*, out of the files it has to process.
- **`elapsed`**: time spent in this step. **`about … left`**: an estimate for this step only,
  based on its speed so far. It moves: a few large videos slow it down, small photos speed it up.
- **Total duration**: the *Duration* line of the summary, at the end.
- **Ctrl+C** stops at any moment, without error messages. An audit never changes anything; an
  interrupted `clean` is journaled, so `undo` still restores what it did.

| On screen | What it really does |
|---|---|
| Listing media files | Walks through every mounted folder and keeps the photos, RAW files and videos, [recognised by their extension](#going-further). Other files (`.xmp`, documents, …) are ignored. The total is not known yet: a running count replaces the bar. |
| Checking that files can be read | Finds broken files: empty ones (0 bytes), images that cannot be decoded (each one is decoded in full, one process per CPU), videos that `ffprobe` cannot open. RAW files are only checked for emptiness. |
| Comparing files of equal size | Two files can only be identical if they have the same size. For those, reads their first and last 64 KB: quick, and it rules most of them out. |
| Proving identity (full SHA-256) | Reads the remaining candidates in full and computes their SHA-256 fingerprint: same fingerprint, same content, byte for byte. The longest step with large videos. |
| Cleaning (`clean`) | Compares each copy again, byte for byte, with the kept one right before deleting it; deletes empty files; moves unreadable ones to the quarantine; journals every action. |
| Restoring (`undo`) | Rebuilds each deleted copy from the kept one (date included) and brings quarantined files back. |

A step with nothing to do is skipped: with the `/cache` volume, files already checked or hashed
by a previous audit are not read again.

## Reading the result

An example on a large photo folder (folder names changed):

```text
Audit summary
┌────────────────────────────────────┬─────────────┐
│ Media files scanned                │      67,947 │
│ Extra copies that can be deleted   │      12,633 │
│ Space that can be freed            │     44.3 GB │
│ Broken files (empty or unreadable) │         180 │
│ Duration                           │ 31 min 12 s │
└────────────────────────────────────┴─────────────┘

Folders sharing identical files
• 1,426 files are both in C:\Photos\2013\Holidays (kept) and in C:\Photos\Old phone\Holidays
  (deleted), 4.5 GB freed.
• 739 files are present several times in C:\Photos\Tablet: one copy of each is kept (2.1 GB
  freed).
• 530 files are both in C:\Photos\Phone (kept) and in C:\Photos\2013\New folder (deleted),
  1.6 GB freed.
```

| Line | What it means |
|---|---|
| Media files scanned | Every photo and video found. Other files (`.xmp`, documents, …) are ignored. |
| Extra copies that can be deleted | The files `clean` would delete. For every photo or video present several times, one copy is kept and the others are extra: a photo stored in 3 folders gives 2 extra copies. |
| Space that can be freed | The total size of those extra copies. |
| Broken files | Empty files (0 bytes) and files that cannot be opened (truncated JPEG, damaged video). `clean` deletes the empty ones and moves the others to the quarantine, never deleting them outright. |
| Duration | How long the whole audit took. |

Each sentence of *Folders sharing identical files* is a pair of folders holding the same files:
the copies in the first folder are kept, those in the second one are deleted, and the space it
frees comes last. The pairs freeing the most space come first. When both are the
same folder, the files are duplicated inside it (`IMG_0001.jpg` and `IMG_0001 (1).jpg`). The kept
folder follows the [rules below](#how-it-keeps-your-photos-safe); not the one you want? Name it
in `--prefer` (or `folders.preferred`) and audit again.

## Going further

Each step adds one or two `-v` options to the same command. In PowerShell, the backtick `` ` ``
at the end of a line continues the command on the next one (nothing may follow it, not even a
space).

**Only some file types** — `--ext` limits the analysis to some extensions, repeatable or
comma-separated (`--ext png,webp`, case and leading dot do not matter); `[scan] extensions` in
`config.toml` does the same. The audit then says which extensions it analysed. Supported
extensions (`media-dedup audit --help` lists them too):

| Type | Extensions |
|---|---|
| Images | avif, bmp, gif, heic, heif, jpe, jpeg, jpg, png, tif, tiff, webp |
| RAW | arw, cr2, cr3, dng, nef, orf, pef, raf, rw2, srw |
| Videos | 3g2, 3gp, avi, flv, m2ts, m4v, mkv, mov, mp4, mpeg, mpg, mts, ts, webm, wmv |

```powershell
docker run --rm -it -v "C:\Photos:/data/c/Photos:ro" cavo789/media-dedup audit --ext png,webp
```

**Several folders, several disks** — one `-v` per folder: `X:\path` is mounted on
`/data/x/path`. Quotes make paths with spaces work. Mount each folder once: a folder already
includes its subfolders, and the tool refuses a folder visible twice (`C:\Photos` plus
`C:\photos\2019`: Windows ignores case, Docker does not), whose photos would look like
duplicates of themselves.

```powershell
docker run --rm -it `
  -v "C:\Family Photos:/data/c/Family Photos:ro" `
  -v "D:\Old phone:/data/d/Old phone:ro" `
  cavo789/media-dedup audit
```

**Keep an HTML report** — give the tool a folder of yours on `/reports`, then double-click
`index.html` in it (no server needed). The `media-dedup-cache` volume makes the next audits much
faster: only new or changed files are read again.

```powershell
mkdir "$HOME\media-dedup\reports"
docker run --rm -it `
  -v "C:\Photos:/data/c/Photos:ro" `
  -v "$HOME\media-dedup\reports:/reports" `
  -v media-dedup-cache:/cache `
  cavo789/media-dedup audit
```

In the report, start with the *folder pairs* table: which folder keeps its copies, which folder
loses them.

**Clean** — the same folders **without `:ro`**, plus a journal (what makes `undo` possible) and
a quarantine (where unreadable files are set aside):

```powershell
mkdir "$HOME\media-dedup\journal", "$HOME\media-dedup\quarantine"
docker run --rm -it `
  -v "C:\Photos:/data/c/Photos" `
  -v "$HOME\media-dedup\journal:/journal" `
  -v "$HOME\media-dedup\quarantine:/quarantine" `
  -v "$HOME\media-dedup\reports:/reports" `
  -v media-dedup-cache:/cache `
  cavo789/media-dedup clean
```

`clean` shows the summary and asks for confirmation (`--yes` skips it). Changed your mind?
Run the same command with `undo` instead of `clean`.

**The current folder** — `cd` into the folder, then (PowerShell's `${PWD}` is Linux's `$(pwd)`;
in the old `cmd.exe` console, write `%cd%`):

```powershell
docker run --rm -it -v "${PWD}:/data/current:ro" cavo789/media-dedup audit
```

**From WSL**, use Linux paths and run as yourself so new files belong to you:

```bash
docker run --rm -it --user "$(id -u):$(id -g)" \
  -v "/mnt/c/Family Photos:/data/c/Family Photos:ro" \
  cavo789/media-dedup audit
```

**Update** — `docker pull cavo789/media-dedup` fetches the latest version; a tag such as
`cavo789/media-dedup:0.1.0` pins one.

## How it keeps your photos safe

| Step | Guarantee |
|---|---|
| `audit` | Read-only: mount your folders with `:ro` and Docker itself forbids any write. |
| Which copy is kept | Deterministic: a protected folder, then your preferred folders (in order), then a name that does not look like a copy (`IMG (1).jpg`, `IMG - Copie.jpg`, …), the oldest date, the shortest path. |
| One file, two paths | A folder mounted twice is refused; a file reachable through two paths (hard link) is analysed once — never a duplicate of itself. |
| Before each deletion | The kept copy must still exist, be another file, and still be byte-for-byte identical — otherwise the file is skipped. |
| Each action | Written to the journal *before* (`pending`) and *after* (`done`) it happens: an interruption never loses track. |
| Duplicates | Really deleted (the space is freed immediately); `undo` rebuilds them from the kept copy, date included, even across disks. |
| Unreadable files | Moved to the quarantine, never deleted outright; `purge` deletes them for good when you are sure. |
| Every group | Always keeps at least one copy. |

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
| `--locale en\|fr` | Interface language (English by default); numbers and sizes follow it: `67,947` and `44.3 GB`, or `67.947` and `44,3 Go`. |
| `--verbosity error\|warning\|info\|debug` | How much to log. |
| `--color auto\|always\|never` | ANSI colours (`NO_COLOR` is honoured). |
| `--prefer PATH` | (`audit`, `clean`) Folder whose copies are kept first; repeatable, ordered. |
| `--protect PATH` | (`audit`, `clean`) Folder never modified; its files are the copies kept. |
| `--exclude PATH` | (`audit`, `clean`) Folder never analysed. |
| `--ext EXT` | (`audit`, `clean`) Only analyse these extensions (`--ext png,webp`); all supported ones by default. |
| `--yes`, `-y` | (`clean`, `purge`) Do not ask for confirmation. |

`media-dedup --help` and `media-dedup <command> --help` document everything, in both languages.

## Configuration

The tool runs in a container: it only sees the folders of your computer that you *mount*, and
`-v "<folder of yours>:<place in the container>"` does that. The configuration lives in the
container at `/config/config.toml`, so give it a folder of yours on `/config`:

```powershell
mkdir "$HOME\media-dedup\config"
docker run --rm -it -v "$HOME\media-dedup\config:/config" cavo789/media-dedup config
```

On this first run, a commented `config.toml` appears in that folder: open
`%USERPROFILE%\media-dedup\config\config.toml` with any text editor. Its comments are written
in the language of that run, and that language is saved in it: created with `--locale fr`, the
file is commented in French and holds `locale = "fr"`, so the next runs speak French without
`--locale`. The file is never overwritten; delete it to get a fresh one. Keep the same
`-v …:/config` in every command so the tool reads it. `media-dedup config` shows each setting
and where it comes from, and the folder of your computer behind each mount point.

Precedence, from the strongest: command-line
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

[scan]
extensions = []       # e.g. ["png", "webp"]; empty: every supported extension

[clean]
confirm = true
```

- **`preferred`**: their copies are kept first, in this order.
- **`protected`**: never modified — and their files are always the copies kept, so identical
  files *elsewhere are deleted*. Think "master library".
- **`excluded`**: never analysed. Use it for a real backup that must stay a second copy.
- **`extensions`**: [only these file types](#going-further) are analysed.

Write Windows paths between **single quotes**: in double quotes, TOML turns `\b` of `"D:\backup"`
into a control character (the tool refuses such a path rather than ignoring it).

## Warnings

- **Real backup**: if `D:\backup` must remain a second copy of your photos, exclude it (or do
  not mount it). Otherwise the tool, rightly, sees its files as duplicates.
- **OneDrive "Files On-Demand"**: analysing a folder whose files are online-only downloads them
  all. Make them available offline first, or leave that folder out.
- **Windows drives are slow through Docker**: the first audit reads every image and every
  file that shares its size with another one. With `-v media-dedup-cache:/cache` the next audits
  only read new or changed files. Tens of thousands of files take a few minutes just to be
  listed: [every step shows its progress](#what-you-see-while-it-runs).
- **Run with `-it`**: without a terminal, `clean` cannot ask for confirmation (use `--yes`) and
  colours are off.

## Development

**Build the image from the sources** — only needed to change the tool. Anywhere this README
says `cavo789/media-dedup`, use your local `media-dedup` instead:

```bash
git clone https://github.com/cavo789/media-deduplication-pipeline.git
cd media-deduplication-pipeline
docker build --tag media-dedup .
```

Maintainers publish a new version with `push` (see below): it builds the image, then pushes
`cavo789/media-dedup:latest` and `:<version>` (read from `pyproject.toml`) to Docker Hub.
Log in once beforehand with `docker login --username cavo789`.

Open the repository in the devcontainer (VS Code, *Reopen in Container*). Every new terminal
shows the cheatsheet of helper commands (`welcome` redraws it):

| Helper | Purpose |
|---|---|
| `check` | The full quality gate: pre-commit (ruff, mypy strict, pylint, shellcheck, shfmt, hadolint) then the tests with ≥ 90 % branch coverage. |
| `format`, `tests` | Auto-fix formatting; run targeted tests. |
| `dedup …`, `demo` | Run the tool from the sources against `/tmp/media-dedup/`; `demo` builds a sample tree and audits it. |
| `reports`, `reports_stop` | Serve the HTML reports on a free port chosen by the OS. |
| `build`, `push`, `e2e`, `dive`, `dive_ci` | Build the image, publish it to Docker Hub (`cavo789/media-dedup`, `:latest` and `:<version>`), run the end-to-end tests, inspect or gate its layers. |
| `i18n_extract`, `i18n_update` | Refresh the gettext catalogs after changing a user-facing string. |
| `todos` | List the open backlog (`.todos/`, see `/todo` and `/todo-plan`). |

Code rules (enforced by the tooling): everything typed, at most 200 lines per file and 3
parameters per function, code in English, every user-facing string translated through gettext.
Caches never land in the repository (they live in `/tmp`).

The roadmap — near-duplicates, sharpness, bursts, review UI, … — is in
[.todos/plan.md](.todos/plan.md).
