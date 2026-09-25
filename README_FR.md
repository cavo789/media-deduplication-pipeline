# media-dedup

Trouve et nettoie en toute sécurité les photos et vidéos en double, réparties sur plusieurs
dossiers et plusieurs disques — d'un seul `docker run`, sous Windows (PowerShell) ou WSL.

🇬🇧 [English version](README.md)

- **Doublons exacts** : même taille et même SHA-256, comparés à nouveau octet par octet juste
  avant toute suppression. Détectés entre dossiers *et* entre disques (`C:` et `D:` dans la même
  exécution).
- **Fichiers cassés** : fichiers vides, images impossibles à décoder (JPEG tronqué, …), vidéos
  impossibles à ouvrir.
- **Réversible** : chaque action est journalisée ; `undo` reconstruit chaque copie supprimée à
  partir de la copie conservée, et ressort chaque fichier de la quarantaine.
- **Jamais touchés** : les rafales et photos « similaires », les fichiers compagnons (`.xmp`,
  `.aae`, `.thm`), les dossiers protégés.

## Sommaire

- [Comment vos photos restent en sécurité](#comment-vos-photos-restent-en-sécurité)
- [Démarrage rapide](#démarrage-rapide)
- [Points de montage](#points-de-montage)
- [Commandes](#commandes)
- [Configuration](#configuration)
- [Mises en garde](#mises-en-garde)
- [Développement](#développement)

## Comment vos photos restent en sécurité

| Étape | Garantie |
|---|---|
| `audit` | Lecture seule : montez vos dossiers avec `:ro` et Docker lui-même interdit toute écriture. |
| Copie conservée | Choix déterministe : un dossier protégé, puis vos dossiers préférés (dans l'ordre), puis un nom qui ne ressemble pas à une copie (`IMG (1).jpg`, `IMG - Copie.jpg`, …), la date la plus ancienne, le chemin le plus court. |
| Avant chaque suppression | La copie conservée doit encore exister et être identique octet par octet ; sinon, le fichier est ignoré. |
| Chaque action | Écrite dans le journal *avant* (`pending`) et *après* (`done`) : une interruption ne fait jamais perdre le fil. |
| Doublons | Réellement supprimés (l'espace est libéré tout de suite) ; `undo` les reconstruit depuis la copie conservée, date comprise, même d'un disque à l'autre. |
| Fichiers illisibles | Déplacés en quarantaine, jamais supprimés directement ; `purge` les supprime définitivement quand vous êtes sûr·e. |
| Chaque groupe | Garde toujours au moins une copie. |

## Démarrage rapide

**1. Construire l'image** (depuis un clone de ce dépôt) :

```bash
docker build --tag media-dedup .
```

**2. Créer un dossier pour les données de l'outil** : configuration, journal, quarantaine,
rapports.

```powershell
mkdir "$HOME\media-dedup\config", "$HOME\media-dedup\journal", "$HOME\media-dedup\quarantine", "$HOME\media-dedup\reports"
```

**3. Auditer**, en lecture seule (notez le `:ro`). Chaque dossier `X:\chemin` est monté sur
`/data/x/chemin`, ce qui permet à l'outil d'afficher les vrais chemins Windows. Les chemins avec
des espaces fonctionnent, entre guillemets.

```powershell
docker run --rm -it `
  -v "C:\Family Photos:/data/c/Family Photos:ro" `
  -v "C:\Users\Public\Pictures:/data/c/Users/Public/Pictures:ro" `
  -v "D:\backup:/data/d/backup:ro" `
  -v "$HOME\media-dedup\config:/config" `
  -v "$HOME\media-dedup\reports:/reports" `
  -v media-dedup-cache:/cache `
  media-dedup --locale fr audit
```

**4. Lire le rapport** : double-cliquez sur `%USERPROFILE%\media-dedup\reports\index.html`, aucun
serveur n'est nécessaire. Commencez par le tableau des *paires de dossiers* : il montre quel
dossier garde ses copies et quel dossier les perd.

**5. Nettoyer** avec les mêmes dossiers, **sans `:ro`**, plus le journal et la quarantaine :

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
  media-dedup --locale fr clean
```

`clean` affiche le résumé et demande confirmation (`--yes` s'en passe). Vous changez d'avis ?
Relancez la même commande en remplaçant `clean` par `undo`.

**Depuis WSL**, utilisez les chemins Linux et lancez le conteneur sous votre identité, pour que
les fichiers créés vous appartiennent :

```bash
docker run --rm -it --user "$(id -u):$(id -g)" \
  -v "/mnt/c/Family Photos:/data/c/Family Photos:ro" \
  -v "$HOME/media-dedup/reports:/reports" \
  media-dedup --locale fr audit
```

## Points de montage

| Montage | Contenu | Nécessaire |
|---|---|---|
| `/data/<lecteur>/<chemin>` | Les dossiers à analyser (`C:\Photos` → `/data/c/Photos`). | toujours ; `:ro` pour `audit` |
| `/config` | `config.toml` uniquement, créé et commenté au premier lancement. | facultatif |
| `/journal` | Un journal JSONL par nettoyage. | **obligatoire** pour `clean`, `undo`, `history` |
| `/quarantine` | Fichiers illisibles mis de côté par `clean`. | s'il y a des fichiers cassés |
| `/reports` | Un dossier par exécution (`report.html`, vignettes) et `index.html`. | facultatif |
| `/cache` | Index SQLite : les audits suivants ne relisent que les fichiers nouveaux ou modifiés. | facultatif, recommandé |

Chaque montage manquant est expliqué par une astuce 💡. L'image fonctionne aussi avec
`--read-only --tmpfs /tmp`.

## Commandes

| Commande | Rôle |
|---|---|
| `audit` | Trouve les doublons exacts et les fichiers cassés. N'écrit jamais dans `/data`. |
| `clean` | Audite, demande confirmation, puis supprime les copies en double et les fichiers vides, et met les fichiers illisibles en quarantaine. |
| `undo [EXÉCUTION]` | Restaure chaque fichier d'un nettoyage (le plus récent par défaut). |
| `history` | Liste les nettoyages : fichiers supprimés, espace libéré, quarantaine, restaurations. |
| `reports [--prune N]` | Liste les rapports et régénère `index.html` ; `--prune N` garde les N plus récents. |
| `purge [EXÉCUTION]` | Supprime définitivement la quarantaine d'un nettoyage (de tous par défaut). |
| `config` | Affiche chaque réglage, son origine, et l'état de chaque point de montage. |

Les options globales se placent **avant** la commande : `media-dedup --locale fr audit`.

| Option | Rôle |
|---|---|
| `--locale en\|fr` | Langue de l'interface (anglais par défaut). |
| `--verbosity error\|warning\|info\|debug` | Niveau de détail des journaux. |
| `--color auto\|always\|never` | Couleurs ANSI (`NO_COLOR` est respecté). |
| `--prefer CHEMIN` | (`audit`, `clean`) Dossier dont les copies sont conservées en priorité ; répétable, l'ordre compte. |
| `--protect CHEMIN` | (`audit`, `clean`) Dossier jamais modifié ; ses fichiers sont les copies conservées. |
| `--exclude CHEMIN` | (`audit`, `clean`) Dossier jamais analysé. |
| `--yes`, `-y` | (`clean`, `purge`) Ne pas demander de confirmation. |

`media-dedup --help` et `media-dedup <commande> --help` documentent tout, dans les deux langues.

## Configuration

`/config/config.toml` est créé au premier lancement. Priorité, de la plus forte à la plus
faible : options de ligne de commande, puis variables d'environnement
`MEDIA_DEDUP_<SECTION>__<CLÉ>` (p. ex. `MEDIA_DEDUP_GENERAL__LOCALE=fr` ; listes en tableau JSON),
puis le fichier, puis les valeurs par défaut.

```toml
[general]
locale = "fr"          # en | fr
verbosity = "info"     # error | warning | info | debug
color = "auto"         # auto | always | never

[folders]              # chemins hôte, entre 'apostrophes'
preferred = ['C:\Family Photos', 'C:\Users\Public\Pictures']
protected = []
excluded = ['D:\backup']

[clean]
confirm = true
```

- **`preferred`** : leurs copies sont conservées en priorité, dans cet ordre.
- **`protected`** : jamais modifiés. Leurs fichiers sont toujours les copies conservées, donc
  les fichiers identiques *ailleurs sont supprimés*. C'est le rôle d'une « bibliothèque de
  référence ».
- **`excluded`** : jamais analysés. À utiliser pour une vraie sauvegarde qui doit rester une
  seconde copie.

Écrivez les chemins Windows entre **apostrophes**. Entre guillemets, TOML transforme le `\b` de
`"D:\backup"` en caractère de contrôle ; l'outil refuse alors ce chemin au lieu de l'ignorer.

## Mises en garde

- **Vraie sauvegarde** : si `D:\backup` doit rester une seconde copie de vos photos,
  excluez-la, ou ne la montez pas. Sinon, l'outil voit ses fichiers comme des doublons, ce qui
  est exact.
- **OneDrive « fichiers à la demande »** : analyser un dossier dont les fichiers sont
  uniquement en ligne les télécharge tous. Rendez-les d'abord disponibles hors connexion, ou
  laissez ce dossier de côté.
- **Les disques Windows sont lents via Docker** : le premier audit lit chaque image, ainsi que
  chaque fichier qui a la même taille qu'un autre. Avec `-v media-dedup-cache:/cache`, les
  audits suivants ne lisent que les fichiers nouveaux ou modifiés.
- **Lancez avec `-it`** : sans terminal, `clean` ne peut pas demander confirmation (utilisez
  `--yes`) et les couleurs sont désactivées.

## Développement

Ouvrez le dépôt dans le devcontainer (VS Code, *Reopen in Container*). Chaque nouveau
terminal affiche la liste des commandes d'aide (`welcome` la réaffiche) :

| Commande | Rôle |
|---|---|
| `check` | La barrière qualité complète : pre-commit (ruff, mypy strict, pylint, shellcheck, shfmt, hadolint), puis les tests avec au moins 90 % de couverture des branches. |
| `format`, `tests` | Corrige la mise en forme ; lance des tests ciblés. |
| `dedup …`, `demo` | Lance l'outil depuis les sources sur `/tmp/media-dedup/` ; `demo` crée une arborescence d'exemple et l'audite. |
| `reports`, `reports_stop` | Sert les rapports HTML sur un port libre choisi par le système. |
| `image`, `e2e`, `dive`, `dive_ci` | Construit l'image, lance les tests de bout en bout, inspecte ou contrôle ses couches. |
| `i18n_extract`, `i18n_update` | Met à jour les catalogues gettext après la modification d'un texte affiché. |
| `todos` | Liste les TODOs ouverts (`.todos/`, voir `/todo` et `/todo-plan`). |

Règles de code, appliquées par l'outillage :

- tout est typé ;
- 200 lignes maximum par fichier et 3 paramètres maximum par fonction ;
- code en anglais ;
- chaque texte affiché passe par gettext.

Les caches n'atterrissent jamais dans le dépôt : ils vivent dans `/tmp`.

La feuille de route (quasi-doublons, netteté, rafales, interface de revue, …) se trouve dans
[.todos/plan.md](.todos/plan.md).
