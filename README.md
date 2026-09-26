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
- **Broken files** — empty files, images and RAW files that cannot be decoded (truncated JPEG,
  …), videos that cannot be opened.
- **Reversible** — every action is journaled; `undo` restores every deleted copy from the copy
  that was kept, and every quarantined file from the quarantine.
- **Orphan sidecars** — a sidecar file (`.xmp`, `.aae`, `.thm`) left without its photo is
  moved to the quarantine; one next to its photo is never touched.
- **Never touched** — bursts and "similar" photos, protected folders.

## Contents

- [What you see while it runs](#what-you-see-while-it-runs)
- [Reading the result](#reading-the-result)
- [Going further](#going-further)
- [How it keeps your photos safe](#how-it-keeps-your-photos-safe)
- [Mount points](#mount-points)
- [Commands](#commands)
- [Configuration](#configuration)
- [Warnings](#warnings)
- [Can you trust it?](#can-you-trust-it)
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
| Listing media files | Walks through every mounted folder and keeps the photos, RAW files and videos, [recognised by their extension](#going-further). Sidecars (`.xmp`, `.aae`, `.thm`) are noted with the files of the same name next to them. Other files (documents, …) are ignored, unless [`--ext` asks for them](#other-file-types). The total is not known yet: a running count replaces the bar. |
| Checking that files can be read | Finds broken files: empty ones (0 bytes), images that cannot be decoded (each one is decoded in full, one process per CPU), RAW files that LibRaw cannot decode (every pixel is unpacked), videos that `ffprobe` cannot open. Other file types asked for with `--ext` are not checked. |
| Comparing files of equal size | Two files can only be identical if they have the same size. For those, reads their first and last 64 KB: quick, and it rules most of them out. |
| Proving identity (full SHA-256) | Reads the remaining candidates in full and computes their SHA-256 fingerprint: same fingerprint, same content, byte for byte. The longest step with large videos. |
| Cleaning (`clean`) | Compares each copy again, byte for byte, with the kept one right before deleting it; deletes empty files; moves unreadable ones and [orphan sidecars](#sidecar-files) to the quarantine; journals every action. |
| Restoring (`undo`) | Rebuilds each deleted copy from the kept one (date included) and brings quarantined files back. |

A step with nothing to do is skipped: with the `/cache` volume, files already checked or hashed
by a previous audit are not read again.

## Reading the result

An example on a large photo folder (folder names changed):

```text
Audit summary
┌────────────────────────────────────┬─────────────┐
│ Media files scanned                │      67,947 │
│ Groups of identical files          │      11,274 │
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
| Media files scanned | Every photo, RAW file and video found, plus the files of the [other types](#other-file-types) asked for with `--ext`. Sidecars (`.xmp`, …) are not counted. |
| Groups of identical files | How many distinct photos or videos exist in several identical copies. Other tools, such as Czkawka, count the same groups: a handy number to compare. |
| Extra copies that can be deleted | The files `clean` would delete. For every photo or video present several times, one copy is kept and the others are extra: a photo stored in 3 folders gives 2 extra copies. |
| Space that can be freed | The total size of those extra copies. |
| Broken files | Empty files (0 bytes) and files that cannot be opened (truncated JPEG or RAW file, damaged video). `clean` deletes the empty ones and moves the others to the quarantine, never deleting them outright. |
| Orphan sidecars | [Sidecar files](#sidecar-files) (`.xmp`, `.aae`, `.thm`) with no file of the same name left next to them once `clean` has run. Moved to the quarantine. |
| Near duplicates | The same photo saved again: resized (WhatsApp), recompressed, rotated, or without its EXIF date. Not identical files: `clean` leaves them alone unless you add `--tier near`, see [below](#near-duplicates-and-bursts). |
| Burst series | Shots of one camera taken seconds apart. Listed with the sharpest one suggested, never cleaned. |
| Duration | How long the whole audit took. |

Each sentence of *Folders sharing identical files* is a pair of folders holding the same files:
the copies in the first folder are kept, those in the second one are deleted, and the space it
frees comes last. The pairs freeing the most space come first. When both are the
same folder, the files are duplicated inside it (`IMG_0001.jpg` and `IMG_0001 (1).jpg`). The kept
folder follows the [rules below](#how-it-keeps-your-photos-safe); not the one you want? Name it
in `--prefer` (or `folders.preferred`) and audit again.

When a folder loses **all** its photos and videos, each with a copy kept in the other folder,
the sentence ends with *"… holds nothing else: it is entirely a copy of …"*. This is the most
reassuring case: that folder is a plain copy.

## Going further

Each step adds one or two `-v` options to the same command. In PowerShell, the backtick `` ` ``
at the end of a line continues the command on the next one (nothing may follow it, not even a
space).

**Only some file types** — `--ext` limits the analysis to some extensions, repeatable or
comma-separated (`--ext png,webp`, case and leading dot do not matter); `[scan] extensions` in
`config.toml` does the same. The audit then says which extensions it analysed. The media
extensions, analysed by default (`media-dedup audit --help` lists them too), are below; [other
types](#other-file-types) (`--ext pdf`) are possible, with more precautions.

| Type | Extensions |
|---|---|
| Images | avif, bmp, gif, heic, heif, jpe, jpeg, jpg, png, tif, tiff, webp |
| RAW (decoded by LibRaw, previewed from the JPEG the camera embeds) | arw, cr2, cr3, dng, nef, orf, pef, raf, rw2, srw |
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
loses them. Each pair shows a few sample pictures and a badge when the folder is entirely a copy.
Click its number of files to see every copy, line by line: the file kept and the identical file
deleted.
`plan.csv`, next to the report, lists **every** file of the plan in a spreadsheet (group,
SHA-256, size, action, path, date), with no cap. It opens directly in Excel, accents included.
The report also explains *how we know these are duplicates*, shows a random sample of photo
groups (RAW files included, through the preview their camera embeds), and gives every group its SHA-256 with a *Check it yourself* command: paste it in
PowerShell (`Get-FileHash`) to see the same fingerprint for every copy, without trusting
media-dedup.

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
`cavo789/media-dedup:0.1.1` pins one.

### Near duplicates and bursts

Besides exact copies, the audit looks at what each photo looks like (perceptual hashes,
sharpness, EXIF date and camera), computed while it checks that the photo is readable, and
remembered in the cache.

- **Near duplicates**: the same photo saved again, smaller (WhatsApp, "reduced for email"),
  recompressed, rotated or without its date. Every test must agree: nearly identical hashes,
  the same shape, and the same shot date (or none on the smaller copy). Blank or black pictures
  never count. The highest resolution is kept. The report shows each group side by side, with
  the resolution, size and sharpness of every copy.
- **Burst series**: shots of one camera, a few seconds apart, of the same scene. This is
  curation, not duplication: they are only listed, the sharpest shot suggested. Nothing in a
  series is ever cleaned, and a burst shot is never taken for a near duplicate.

A plain `clean` never touches near duplicates. After checking them in the report, add
`--tier near`: the copies are **moved to the quarantine** (they are not identical, so they
cannot be rebuilt from the kept photo), and `undo` puts them back. `purge` deletes them for
good. This needs the `/quarantine` mount:

```powershell
docker run --rm -it `
  -v "C:\Photos:/data/c/Photos" `
  -v "$HOME\media-dedup\journal:/journal" `
  -v "$HOME\media-dedup\quarantine:/quarantine" `
  cavo789/media-dedup clean --tier near
```

### Sidecar files

Sidecars are small files next to a photo or a video, holding its metadata or its edits: `.xmp`
(Lightroom, digiKam, darktable), `.aae` (iPhone edits), `.thm` (camcorder thumbnails). A
sidecar belongs to the files of its folder with the same name: `IMG_1.xmp` to `IMG_1.jpg` or
`IMG_1.CR2`, and `IMG_1.CR2.xmp` to `IMG_1.CR2`, case ignored.

- **Next to its photo**, a sidecar is never touched.
- **Orphan**: once `clean` has deleted or moved every file of the same name next to it (or if
  there was none to begin with), a sidecar is useless. `clean` moves it to the quarantine,
  never deletes it, after checking that no file of the same name has come back. `undo` puts
  it back; `purge` deletes it for good. Without the `/quarantine` mount, orphans stay put.
- **With `--ext`**, the audit looks at some files only: sidecars already alone before the
  clean are left where they are, only those the clean itself leaves alone are moved.
- **Protected folders** are never modified, sidecars included.

The sidecar of a deleted copy is not moved next to the kept one. To keep a photo *with* its
edits, make sure that copy is the one kept: name its folder in `--prefer`.

### Other file types

media-dedup is made for photos and videos: without `--ext`, nothing else is analysed. `--ext`
(or `[scan] extensions`) also accepts other extensions, for instance to find the duplicate
documents of a family folder:

```powershell
docker run --rm -it `
  -v "C:\Users\Me\Documents:/data/c/Users/Me/Documents" `
  -v "$HOME\media-dedup\journal:/journal" `
  -v "$HOME\media-dedup\quarantine:/quarantine" `
  cavo789/media-dedup clean --ext pdf,docx
```

Such files are handled with more care than photos. For a photo, the folder is only a way to
sort; for a document or a program, **where the file lies can be what makes it work**: an
identical `LICENSE`, `__init__.py` or template in two projects is expected, and deleting "the
copy" breaks one of them.

- **Only compared**, byte for byte: never decoded (images go through Pillow, RAW files through
  LibRaw, videos through `ffprobe`; other types have no check), no preview, no near
  duplicates. An empty file is never "broken": it may be a marker a program needs.
- **Their copies are moved to the quarantine**, never deleted: `clean` refuses to run without
  the `/quarantine` mount. `undo` puts them back; `purge` deletes them for good.
- **Software folders are skipped**: `.git`, `.hg`, `.svn`, `node_modules`, `.venv`, `venv`,
  `site-packages`, `__pycache__`, `AppData`, `ProgramData`, `Program Files`,
  `Program Files (x86)` and `Windows`, whatever their case.
- **A typo is not refused**: `--ext jpgg` is a valid extension, that simply matches nothing.
  The audit names the extensions that are not photos or videos: read that warning.
- **Sidecars** (`.xmp`, `.aae`, `.thm`) cannot be asked for: they [follow their
  photo](#sidecar-files).
- **`--ext` still limits the analysis**: `--ext jpg,pdf` analyses JPEG photos and PDF
  documents, not the RAW files and videos.

Mount the folders holding your documents, never a whole drive or `C:\Users`: programs and
their data live there too.

## How it keeps your photos safe

| Step | Guarantee |
|---|---|
| `audit` | Read-only: mount your folders with `:ro` and Docker itself forbids any write. |
| Which copy is kept | Deterministic: a protected folder, then your preferred folders (in order), then a name that does not look like a copy (`IMG (1).jpg`, `IMG - Copie.jpg`, …), a name someone chose rather than one generated by a camera or an app (`Marie et Paul.jpg` rather than `IMG_1234.jpg`), a folder someone named rather than a generic one (`Vacances 2019` rather than `DCIM\100CANON`), the oldest date, the shortest path. The report says, for each group, which rule decided. |
| One file, two paths | A folder mounted twice is refused; a file reachable through two paths (hard link) is analysed once — never a duplicate of itself. |
| Before each deletion | The kept copy must still exist, be another file, and still be byte-for-byte identical — otherwise the file is skipped. |
| Each action | Written to the journal *before* (`pending`) and *after* (`done`) it happens: an interruption never loses track. |
| Duplicates | Really deleted (the space is freed immediately); `undo` rebuilds them from the kept copy, date included, even across disks. |
| Unreadable files | Moved to the quarantine, never deleted outright; `purge` deletes them for good when you are sure. |
| Near duplicates | Never touched by default. With `--tier near`, moved to the quarantine (never deleted) once checked: the kept photo still exists, the copy is the very file the audit saw. `undo` puts them back. |
| Other file types | Only when asked for with `--ext`: [their copies](#other-file-types) are moved to the quarantine (never deleted), and software folders (`.git`, `node_modules`, `AppData`, …) are skipped. |
| Sidecars | Never touched next to their photo. An orphan is moved to the quarantine (never deleted) once checked: unchanged since the audit, and no file of the same name next to it. `undo` puts it back. |
| Every group | Always keeps at least one copy. |

## Mount points

| Mount | Content | Needed |
|---|---|---|
| `/data/<drive>/<path>` | The folders to analyse (`C:\Photos` → `/data/c/Photos`). | always; `:ro` for `audit` |
| `/config` | `config.toml` only — created, commented, on first run. | optional |
| `/journal` | One JSONL journal per clean. | **required** by `clean`, `undo`, `history` |
| `/quarantine` | Unreadable files, orphan sidecars, near duplicates and copies of other file types set aside by `clean`. | to handle them |
| `/reports` | One folder per run (`report.html`, one page per folder pair, previews, `plan.csv`) and `index.html`. | optional |
| `/cache` | SQLite index: later audits only read new or changed files. | optional, recommended |

Missing mounts are explained by 💡 tips. The image also runs with `--read-only --tmpfs /tmp`.

## Commands

| Command | What it does |
|---|---|
| `audit` | Find exact duplicates and broken files. Never writes to `/data`. |
| `clean` | Audit, confirm, then delete duplicate copies, delete empty files and quarantine unreadable ones and orphan sidecars. |
| `undo [RUN]` | Restore every file of a clean run (the latest by default). |
| `history` | List the clean runs: files deleted, space freed, quarantine, restores. |
| `reports [--prune N]` | List the reports and refresh `index.html`; `--prune N` keeps the N most recent. |
| `purge [RUN]` | Permanently delete the quarantine of a run (of every run by default). |
| `crosscheck` | Audit again, then compare with the results of [Czkawka](#get-a-second-opinion-with-czkawka), an independent duplicate finder. |
| `config` | Show every setting, where it comes from, and the state of each mount point. |

Global options go **before** the command: `media-dedup --locale fr audit`.

| Option | Meaning |
|---|---|
| `--locale en\|fr` | Interface language (English by default); numbers and sizes follow it: `67,947` and `44.3 GB`, or `67.947` and `44,3 Go`. |
| `--verbosity error\|warning\|info\|debug` | How much to log. |
| `--color auto\|always\|never` | ANSI colours (`NO_COLOR` is honoured). |
| `--prefer PATH` | (`audit`, `clean`, `crosscheck`) Folder whose copies are kept first; repeatable, ordered. |
| `--protect PATH` | (`audit`, `clean`, `crosscheck`) Folder never modified; its files are the copies kept. |
| `--exclude PATH` | (`audit`, `clean`, `crosscheck`) Folder never analysed. |
| `--ext EXT` | (`audit`, `clean`, `crosscheck`) Only analyse these extensions (`--ext png,webp`); every photo, RAW and video one by default. [Other types](#other-file-types) too (`--ext pdf,docx`). |
| `--yes`, `-y` | (`clean`, `purge`) Do not ask for confirmation. |
| `--tier exact\|near` | (`clean`) `exact` (default): byte-for-byte copies only. `near`: also move [near duplicates](#near-duplicates-and-bursts) to the quarantine. |

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
extensions = []       # e.g. ["png", "webp"] or ["pdf"]; empty: every photo, RAW and video one

[keep]                 # leave commented: built-in lists ('media-dedup config' shows them)
# generated_names = ['IMG_\d+', 'DSC\d+']   # file names cameras and apps generate
# generic_folders = ['DCIM', 'Camera']       # folder names devices and apps create

[clean]
confirm = true
```

- **`preferred`**: their copies are kept first, in this order.
- **`protected`**: never modified — and their files are always the copies kept, so identical
  files *elsewhere are deleted*. Think "master library".
- **`excluded`**: never analysed. Use it for a real backup that must stay a second copy.
- **`extensions`**: [only these file types](#going-further) are analysed; [other
  types](#other-file-types) than photos and videos are allowed.
- **`generated_names`**, **`generic_folders`**: regular expressions matching a whole file name
  (without extension) or folder name, case ignored. Between identical copies, a name or folder
  that matches is worth less: `Mariage 2015\Marie et Paul.jpg` is kept rather than
  `DCIM\IMG_1234.jpg`. An empty list `[]` disables the rule.

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
  listed: [every step shows its progress](#what-you-see-while-it-runs). After an update to
  0.1.1, the first audit decodes every photo once more, to describe what it looks like.
- **Run with `-it`**: without a terminal, `clean` cannot ask for confirmation (use `--yes`) and
  colours are off.

## Can you trust it?

Before deleting family photos, everyone asks the same question: *are these really, really
duplicates?* This chapter explains what the tool calls a duplicate, what it checks before
deleting, how you can check it yourself, and what to watch out for.

### What counts as a duplicate

Only **byte-for-byte identical** files. The tool first compares sizes, then a SHA-256
fingerprint of the first 64 KB, then a SHA-256 fingerprint of the whole content. In practice,
two different files never share a SHA-256: the odds are far lower than those of a disk error.

- **The name and the date do not matter.** `IMG_1234.jpg` and `Marie et Paul.jpg` with the same
  bytes are duplicates. Two `IMG_0001.jpg` with different content are not.
- **Looking the same is not enough.** A resized, recompressed, rotated or re-tagged copy is a
  different file. The audit lists it as a [near duplicate](#near-duplicates-and-bursts), but
  `clean` leaves it alone unless you ask with `--tier near`, and then only moves it to the
  quarantine.
- **Only photos, RAW files and videos** are analysed, recognised by their extension. Other
  files only when you [ask for them](#other-file-types) with `--ext`, and then their copies
  are moved to the quarantine, never deleted.

### What the tool checks before deleting

The details are in [How it keeps your photos safe](#how-it-keeps-your-photos-safe). In short:

- **The audit never writes.** Mount your folders with `:ro` and Docker itself forbids any
  write.
- **One file seen twice is not a duplicate.** A folder mounted twice is refused, and a file
  reachable through two paths (a hard link) is analysed once.
- **Right before each deletion**, `clean` checks that the kept copy still exists, is another
  file, and is still byte-for-byte identical. Otherwise it leaves the file alone.
- **Every action is written to the journal**, and `undo` rebuilds the deleted copies from the
  kept one.

### Check it yourself

The report (`-v "…:/reports"`) is built for that:

- The **folder pairs** come first. A badge marks a folder that is *entirely a copy* of another
  one, and each pair has a page listing every copy.
- A **random sample** of photo groups comes with previews.
- **Check it yourself**, on every group, gives a PowerShell `Get-FileHash` command. Paste it:
  every copy shows the same SHA-256, computed by Windows, not by media-dedup.
- **`plan.csv`** lists every file of the plan with its SHA-256, ready for Excel.

### Get a second opinion with Czkawka

[Czkawka](https://github.com/qarmin/czkawka) is an independent, open-source duplicate finder,
written differently and with another hash function. Two tools written independently rarely
make the same mistake: when they agree, you can clean with confidence.

**1. Audit, with a reports folder.** When it finds duplicates, `audit` ends with a
*Second opinion* tip and the exact Czkawka command for your folders: the same `-v` options,
the same extensions, the same excluded folders, every file size. It looks like this (the
community image `jlesage/czkawka`, about 500 MB, ships Czkawka's command-line tool):

```powershell
docker run --rm -v "C:\Photos:/data/c/Photos:ro" -v "$HOME\media-dedup\reports:/out" `
  jlesage/czkawka:v26.09.2 czkawka_cli dup -d /data -m 1 -W -N -C /out/czkawka.json `
  -x 3g2,3gp,arw,avi,avif,bmp,cr2,cr3,dng,flv,gif,heic,heif,jpe,jpeg,jpg,m2ts,m4v,mkv,mov,mp4,mpeg,mpg,mts,nef,orf,pef,png,raf,rw2,srw,tif,tiff,ts,webm,webp,wmv
```

**2. Paste and run it.** Czkawka writes its results, `czkawka.json`, in your reports folder.
From WSL, write your folders as `/mnt/c/...` instead of `C:\...`.

**3. Compare**, with the same options as the audit:

```powershell
docker run --rm -it -v "C:\Photos:/data/c/Photos:ro" `
  -v "$HOME\media-dedup\reports:/reports" -v media-dedup-cache:/cache `
  cavo789/media-dedup crosscheck
```

`crosscheck` audits again (quickly, thanks to the cache) and compares the two tools group by
group:

- *Czkawka agrees: the same N extra copies in G groups*;
- or *Czkawka disagrees on N groups*, listing each group found by one tool only. Look at them
  before cleaning.

Files media-dedup deliberately leaves out are set aside and counted, not reported as
differences: other file types, excluded or system folders, broken files. The verdict also
goes into the HTML report, and `clean` recalls it before asking for confirmation. It is
information only: `clean` never requires it.

### Recommendations

- **Audit first, then read the folder pairs.** Open a few pairs, and check a few groups
  yourself.
- **Check which copy stays.** The kept file keeps its name and folder; the name of a deleted
  copy is lost. The tool already prefers `Mariage 2015\Marie et Paul.jpg` to
  `DCIM\IMG_1234.jpg`, and the report says why each copy was kept. Not the one you want? Name
  the folder in `--prefer` (or `folders.preferred`, or protect it), then audit again.
- **Back up your photos before the first clean**, for example on an external disk: the tool
  keeps one copy of each photo, not two.
- **Pause cloud synchronisation** (OneDrive, Google Drive, Dropbox, iCloud) while cleaning.
  Otherwise deletions are copied to the cloud and to your other devices.
- **Keep the journal folder**: `undo` needs it. Run `purge` only when you are sure.
- Read the [Warnings](#warnings) too: a real backup must be excluded, and each folder must be
  mounted only once.

## Development

**Build the image from the sources** — only needed to change the tool. Anywhere this README
says `cavo789/media-dedup`, use your local `media-dedup` instead:

```bash
git clone https://github.com/cavo789/media-deduplication-pipeline.git
cd media-deduplication-pipeline
docker build --tag media-dedup .
```

The image compiles its own `ffprobe`, about 1 MB instead of 141 MB for a full build: the tool
only asks whether a video container opens, so the `ffprobe` stage of the `Dockerfile` keeps the
demuxers of the video extensions it analyses and nothing else. A new video extension needs its
demuxer there too; a test checks that both lists agree.

Every push and pull request runs the quality gate and the end-to-end tests on GitHub Actions
([`.github/workflows/ci.yml`](.github/workflows/ci.yml)). To publish a new version, bump
`version` in `pyproject.toml`, commit and push `main`, then run `release` (see below). It tags
`vX.Y.Z` and pushes the tag. CI then builds the image for amd64 and arm64, runs the end-to-end
tests, and pushes `cavo789/media-dedup:<version>` and `:latest` to Docker Hub, with an SBOM and
a provenance attestation. This needs two repository secrets: `DOCKERHUB_USERNAME` and
`DOCKERHUB_TOKEN` (a Docker Hub access token with read/write scope).

Open the repository in the devcontainer (VS Code, *Reopen in Container*). Every new terminal
shows the cheatsheet of helper commands (`welcome` redraws it):

| Helper | Purpose |
|---|---|
| `check` | The full quality gate: pre-commit (ruff, mypy strict, pylint, shellcheck, shfmt, hadolint) then the tests with ≥ 90 % branch coverage. |
| `format`, `tests` | Auto-fix formatting; run targeted tests. |
| `dedup …`, `demo` | Run the tool from the sources against `/tmp/media-dedup/`; `demo` builds a sample tree and audits it. |
| `reports`, `reports_stop` | Serve the HTML reports on a free port chosen by the OS. |
| `build`, `e2e`, `dive`, `dive_ci` | Build the image, run the end-to-end tests, inspect or gate its layers. |
| `release` | Tag `vX.Y.Z` (the `pyproject.toml` version) and push it: CI publishes the image. |
| `i18n_extract`, `i18n_update` | Refresh the gettext catalogs after changing a user-facing string. |
| `todos` | List the open backlog (`.todos/`, see `/todo` and `/todo-plan`). |
| `ci`, `ci_logs` | Latest CI runs of the branch; logs of the failed steps of the latest failed run. The GitHub CLI asks for `gh auth login` once. |

Settings and logins of the tools (`~/.config`, e.g. the GitHub CLI token) live in the
`media-dedup-config` Docker volume, outside the workspace: they survive rebuilds and can never
be committed. Never write a token in a tracked file (`devcontainer.json` included): this
repository is public.

Code rules (enforced by the tooling): everything typed, at most 200 lines per file and 3
parameters per function, code in English, every user-facing string translated through gettext.
Caches never land in the repository (they live in `/tmp`).

The roadmap — near-duplicates, sharpness, bursts, review UI, … — is in
[.todos/plan.md](.todos/plan.md).
