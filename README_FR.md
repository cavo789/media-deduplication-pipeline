# media-dedup

Trouve et nettoie en toute sécurité les photos et vidéos en double, réparties sur plusieurs
dossiers et plusieurs disques — d'un seul `docker run`, sous Windows (PowerShell) ou WSL.

🇬🇧 [English version](README.md)

## Démarrage rapide

Avec Docker installé, une seule commande audite un dossier :

```powershell
docker run --rm -it -v "C:\Photos:/data/c/Photos:ro" cavo789/media-dedup --locale fr audit
```

Elle liste les photos et vidéos en double ou cassées de `C:\Photos`, sans rien modifier : `:ro`
(lecture seule) fait interdire toute écriture par Docker lui-même. Le premier lancement
télécharge l'image tout seul.

Ce qu'elle fait :

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

- [Ce qui s'affiche pendant l'analyse](#ce-qui-saffiche-pendant-lanalyse)
- [Lire le résultat](#lire-le-résultat)
- [Aller plus loin](#aller-plus-loin)
- [Comment vos photos restent en sécurité](#comment-vos-photos-restent-en-sécurité)
- [Points de montage](#points-de-montage)
- [Commandes](#commandes)
- [Configuration](#configuration)
- [Mises en garde](#mises-en-garde)
- [Peut-on lui faire confiance ?](#peut-on-lui-faire-confiance-)
- [Développement](#développement)

## Ce qui s'affiche pendant l'analyse

Chaque étape affiche une ligne de progression et, en dessous en gris, ce qu'elle fait réellement :

```text
⠴ Preuve d'identité (SHA-256 complet) ━━━━━━━━╸━━━━━━━ 11.707/23.907 écoulé 0:00:47 · encore ~0:02:19
  Lit entièrement les candidats restants : même SHA-256 veut dire identiques, octet par octet.
```

- **`11.707/23.907`** : fichiers traités par *cette étape*, sur le nombre qu'elle doit traiter.
- **`écoulé`** : temps passé dans cette étape. **`encore ~…`** : une estimation pour cette étape
  seulement, d'après sa vitesse jusqu'ici. Elle bouge : quelques grosses vidéos la ralentissent,
  des petites photos l'accélèrent.
- **Durée totale** : la ligne *Durée* du résumé, à la fin.
- **Ctrl+C** arrête à tout moment, sans message d'erreur. Un audit ne modifie jamais rien ; un
  `clean` interrompu est journalisé, `undo` restaure donc ce qu'il a fait.

| À l'écran | Ce que l'étape fait réellement |
|---|---|
| Recherche des fichiers médias | Parcourt tous les dossiers montés et garde les photos, fichiers RAW et vidéos, [reconnus à leur extension](#aller-plus-loin). Les autres fichiers (`.xmp`, documents, …) sont ignorés. Le total n'est pas encore connu : un compteur remplace la barre. |
| Vérification de la lisibilité des fichiers | Repère les fichiers cassés : vides (0 octet), images impossibles à décoder (chacune est décodée entièrement, un processus par cœur), vidéos que `ffprobe` ne peut pas ouvrir. Les fichiers RAW sont seulement vérifiés comme non vides. |
| Comparaison des fichiers de même taille | Deux fichiers ne peuvent être identiques que s'ils ont la même taille. Pour ceux-là, lit leurs premiers et derniers 64 Ko : rapide, et cela en écarte la plupart. |
| Preuve d'identité (SHA-256 complet) | Lit entièrement les candidats restants et calcule leur empreinte SHA-256 : même empreinte, même contenu, octet par octet. L'étape la plus longue avec de grosses vidéos. |
| Nettoyage (`clean`) | Recompare chaque copie, octet par octet, avec celle gardée juste avant de la supprimer ; supprime les fichiers vides ; déplace les illisibles en quarantaine ; journalise chaque action. |
| Restauration (`undo`) | Recrée chaque copie supprimée à partir de celle gardée (date comprise) et ramène les fichiers mis en quarantaine. |

Une étape sans travail est sautée : avec le volume `/cache`, les fichiers déjà vérifiés ou
hachés par un audit précédent ne sont pas relus.

## Lire le résultat

Voici un exemple sur un gros dossier de photos (noms de dossiers modifiés) :

```text
Résumé de l'audit
┌───────────────────────────────────────┬─────────────┐
│ Fichiers média analysés               │      67.947 │
│ Groupes de fichiers identiques        │      11.904 │
│ Copies en trop, supprimables          │      12.633 │
│ Espace libérable                      │     44,3 Go │
│ Fichiers cassés (vides ou illisibles) │         180 │
│ Durée                                 │ 31 min 12 s │
└───────────────────────────────────────┴─────────────┘

Dossiers partageant des fichiers identiques
• 1.426 fichiers sont à la fois dans C:\Photos\2013\Vacances (gardés) et dans
  C:\Photos\Ancien téléphone\Vacances (supprimés), gain de 4,5 Go.
• 739 fichiers sont présents plusieurs fois dans C:\Photos\Tablette : un exemplaire de chacun
  est gardé (gain de 2,1 Go).
• 530 fichiers sont à la fois dans C:\Photos\Téléphone (gardés) et dans
  C:\Photos\2013\Nouveau dossier (supprimés), gain de 1,6 Go.
```

| Ligne | Ce qu'elle veut dire |
|---|---|
| Fichiers média analysés | Toutes les photos et vidéos trouvées. Les autres fichiers (`.xmp`, documents, …) sont ignorés. |
| Groupes de fichiers identiques | Combien de photos ou vidéos distinctes existent en plusieurs copies identiques. D'autres outils, comme Czkawka, comptent les mêmes groupes : un chiffre pratique pour comparer. |
| Copies en trop, supprimables | Les fichiers que `clean` supprimerait. Pour chaque photo ou vidéo présente plusieurs fois, un exemplaire est gardé et les autres sont en trop : une photo rangée dans 3 dossiers donne 2 copies en trop. |
| Espace libérable | La taille totale de ces copies en trop. |
| Fichiers cassés | Les fichiers vides (0 octet) et ceux qui ne s'ouvrent pas (JPEG tronqué, vidéo abîmée). `clean` supprime les vides et déplace les autres en quarantaine, sans jamais les supprimer directement. |
| Durée | Le temps qu'a pris tout l'audit. |

Chaque phrase de *Dossiers partageant des fichiers identiques* décrit deux dossiers qui
contiennent les mêmes fichiers : les copies du premier sont gardées, celles du second sont
supprimées, et la phrase se termine par l'espace libéré. Les paires qui libèrent le plus d'espace
viennent en premier. Quand les deux sont le même dossier, les fichiers y sont en double (`IMG_0001.jpg` et
`IMG_0001 (1).jpg`). Le dossier gardé suit les [règles ci-dessous](#comment-vos-photos-restent-en-sécurité) ;
ce n'est pas celui que vous voulez ? Indiquez-le dans `--prefer` (ou `folders.preferred`) et
relancez l'audit.

Quand un dossier perd **toutes** ses photos et vidéos, et qu'une copie de chacune est gardée
dans l'autre dossier, la phrase se termine par *« … ne contient rien d'autre : c'est
entièrement une copie de … »*. C'est le cas le plus rassurant : ce dossier est une simple copie.

## Aller plus loin

Chaque étape ajoute une ou deux options `-v` à la même commande. Dans PowerShell, la backtick
`` ` `` en fin de ligne continue la commande sur la ligne suivante (rien ne doit la suivre, pas
même un espace).

**Seulement certains types de fichiers** : `--ext` limite l'analyse à certaines extensions,
répétable ou séparées par des virgules (`--ext png,webp` ; la casse et le point initial
n'importent pas). `[scan] extensions` dans `config.toml` fait de même. L'audit indique alors les
extensions analysées. Extensions prises en charge (`media-dedup audit --help` les liste aussi) :

| Type | Extensions |
|---|---|
| Images | avif, bmp, gif, heic, heif, jpe, jpeg, jpg, png, tif, tiff, webp |
| RAW | arw, cr2, cr3, dng, nef, orf, pef, raf, rw2, srw |
| Vidéos | 3g2, 3gp, avi, flv, m2ts, m4v, mkv, mov, mp4, mpeg, mpg, mts, ts, webm, wmv |

```powershell
docker run --rm -it -v "C:\Photos:/data/c/Photos:ro" cavo789/media-dedup --locale fr audit --ext png,webp
```

**Plusieurs dossiers, plusieurs disques** : un `-v` par dossier, `X:\chemin` étant monté sur
`/data/x/chemin`. Grâce aux guillemets, les chemins avec des espaces fonctionnent. Montez
chaque dossier une seule fois : un dossier inclut déjà ses sous-dossiers, et l'outil refuse un
dossier visible deux fois (`C:\Photos` plus `C:\photos\2019` : Windows ignore la casse,
Docker non), dont les photos passeraient pour des doublons d'elles-mêmes.

```powershell
docker run --rm -it `
  -v "C:\Photos de famille:/data/c/Photos de famille:ro" `
  -v "D:\Ancien téléphone:/data/d/Ancien téléphone:ro" `
  cavo789/media-dedup --locale fr audit
```

**Garder un rapport HTML** : donnez à l'outil un de vos dossiers sur `/reports`, puis
double-cliquez sur son `index.html` (aucun serveur nécessaire). Le volume `media-dedup-cache`
rend les audits suivants bien plus rapides : seuls les fichiers nouveaux ou modifiés sont relus.

```powershell
mkdir "$HOME\media-dedup\reports"
docker run --rm -it `
  -v "C:\Photos:/data/c/Photos:ro" `
  -v "$HOME\media-dedup\reports:/reports" `
  -v media-dedup-cache:/cache `
  cavo789/media-dedup --locale fr audit
```

Dans le rapport, commencez par le tableau des *paires de dossiers* : il montre quel dossier garde
ses copies et quel dossier les perd. Chaque paire montre quelques photos d'exemple, et un badge
quand le dossier est entièrement une copie. Cliquez sur son nombre de fichiers pour voir chaque
copie, ligne par ligne : le fichier gardé et le fichier identique supprimé.
`plan.csv`, à côté du rapport, liste **chaque** fichier du plan dans un tableur (groupe,
SHA-256, taille, action, chemin, date), sans limite. Il s'ouvre directement dans Excel, accents
compris (séparateur `;` en français).
Le rapport explique aussi *comment on sait que ce sont des doublons*, montre un échantillon
aléatoire de groupes de photos, et donne pour chaque groupe son SHA-256 avec une commande
*Vérifiez vous-même* : collez-la dans PowerShell (`Get-FileHash`) pour voir la même empreinte
pour chaque copie, sans devoir croire media-dedup sur parole.

**Nettoyer** : les mêmes dossiers **sans `:ro`**, plus un journal (c'est lui qui rend `undo`
possible) et une quarantaine (où sont mis de côté les fichiers illisibles) :

```powershell
mkdir "$HOME\media-dedup\journal", "$HOME\media-dedup\quarantine"
docker run --rm -it `
  -v "C:\Photos:/data/c/Photos" `
  -v "$HOME\media-dedup\journal:/journal" `
  -v "$HOME\media-dedup\quarantine:/quarantine" `
  -v "$HOME\media-dedup\reports:/reports" `
  -v media-dedup-cache:/cache `
  cavo789/media-dedup --locale fr clean
```

`clean` affiche le résumé et demande confirmation (`--yes` s'en passe). Vous changez d'avis ?
Relancez la même commande en remplaçant `clean` par `undo`.

**Le dossier courant** : placez-vous dans le dossier avec `cd`, puis lancez la commande
ci-dessous (dans PowerShell, `${PWD}` est l'équivalent du `$(pwd)` de Linux ; dans l'ancienne
console `cmd.exe`, écrivez `%cd%`) :

```powershell
docker run --rm -it -v "${PWD}:/data/current:ro" cavo789/media-dedup --locale fr audit
```

**Depuis WSL**, utilisez les chemins Linux et lancez le conteneur sous votre identité, pour que
les fichiers créés vous appartiennent :

```bash
docker run --rm -it --user "$(id -u):$(id -g)" \
  -v "/mnt/c/Photos de famille:/data/c/Photos de famille:ro" \
  cavo789/media-dedup --locale fr audit
```

**Mettre à jour** : `docker pull cavo789/media-dedup` récupère la dernière version ; un tag comme
`cavo789/media-dedup:0.1.1` en fixe une.

## Comment vos photos restent en sécurité

| Étape | Garantie |
|---|---|
| `audit` | Lecture seule : montez vos dossiers avec `:ro` et Docker lui-même interdit toute écriture. |
| Copie conservée | Choix déterministe : un dossier protégé, puis vos dossiers préférés (dans l'ordre), puis un nom qui ne ressemble pas à une copie (`IMG (1).jpg`, `IMG - Copie.jpg`, …), la date la plus ancienne, le chemin le plus court. |
| Un fichier, deux chemins | Un dossier monté deux fois est refusé ; un fichier accessible par deux chemins (lien physique) n'est analysé qu'une fois, jamais comme doublon de lui-même. |
| Avant chaque suppression | La copie conservée doit encore exister, être un autre fichier et être identique octet par octet ; sinon, le fichier est ignoré. |
| Chaque action | Écrite dans le journal *avant* (`pending`) et *après* (`done`) : une interruption ne fait jamais perdre le fil. |
| Doublons | Réellement supprimés (l'espace est libéré tout de suite) ; `undo` les reconstruit depuis la copie conservée, date comprise, même d'un disque à l'autre. |
| Fichiers illisibles | Déplacés en quarantaine, jamais supprimés directement ; `purge` les supprime définitivement quand vous êtes sûr·e. |
| Chaque groupe | Garde toujours au moins une copie. |

## Points de montage

| Montage | Contenu | Nécessaire |
|---|---|---|
| `/data/<lecteur>/<chemin>` | Les dossiers à analyser (`C:\Photos` → `/data/c/Photos`). | toujours ; `:ro` pour `audit` |
| `/config` | `config.toml` uniquement, créé et commenté au premier lancement. | facultatif |
| `/journal` | Un journal JSONL par nettoyage. | **obligatoire** pour `clean`, `undo`, `history` |
| `/quarantine` | Fichiers illisibles mis de côté par `clean`. | s'il y a des fichiers cassés |
| `/reports` | Un dossier par exécution (`report.html`, une page par paire de dossiers, vignettes, `plan.csv`) et `index.html`. | facultatif |
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
| `--locale en\|fr` | Langue de l'interface (anglais par défaut) ; les nombres et tailles la suivent : `67,947` et `44.3 GB`, ou `67.947` et `44,3 Go`. |
| `--verbosity error\|warning\|info\|debug` | Niveau de détail des journaux. |
| `--color auto\|always\|never` | Couleurs ANSI (`NO_COLOR` est respecté). |
| `--prefer CHEMIN` | (`audit`, `clean`) Dossier dont les copies sont conservées en priorité ; répétable, l'ordre compte. |
| `--protect CHEMIN` | (`audit`, `clean`) Dossier jamais modifié ; ses fichiers sont les copies conservées. |
| `--exclude CHEMIN` | (`audit`, `clean`) Dossier jamais analysé. |
| `--ext EXT` | (`audit`, `clean`) N'analyse que ces extensions (`--ext png,webp`) ; toutes celles prises en charge par défaut. |
| `--yes`, `-y` | (`clean`, `purge`) Ne pas demander de confirmation. |

`media-dedup --help` et `media-dedup <commande> --help` documentent tout, dans les deux langues.

## Configuration

L'outil tourne dans un conteneur : il ne voit que les dossiers de votre ordinateur que vous
*montez*, et c'est le rôle de `-v "<un de vos dossiers>:<emplacement dans le conteneur>"`. La
configuration se trouve dans le conteneur en `/config/config.toml` : donnez-lui donc un de vos
dossiers sur `/config` :

```powershell
mkdir "$HOME\media-dedup\config"
docker run --rm -it -v "$HOME\media-dedup\config:/config" cavo789/media-dedup --locale fr config
```

À ce premier lancement, un `config.toml` commenté apparaît dans ce dossier : ouvrez
`%USERPROFILE%\media-dedup\config\config.toml` avec n'importe quel éditeur de texte. Ses
commentaires sont écrits dans la langue de ce lancement, et cette langue y est enregistrée : créé
avec `--locale fr`, le fichier est commenté en français et contient `locale = "fr"`, les
lancements suivants parlent donc français sans `--locale`. Le fichier n'est jamais écrasé ;
supprimez-le pour en obtenir un neuf. Gardez le
même `-v …:/config` dans chaque commande pour que l'outil le lise. `media-dedup config` montre
chaque réglage, son origine, et le dossier de votre ordinateur derrière chaque point de montage.

Priorité, de la plus forte à la plus
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

[scan]
extensions = []       # p. ex. ["png", "webp"] ; vide : toutes les extensions prises en charge

[clean]
confirm = true
```

- **`preferred`** : leurs copies sont conservées en priorité, dans cet ordre.
- **`protected`** : jamais modifiés. Leurs fichiers sont toujours les copies conservées, donc
  les fichiers identiques *ailleurs sont supprimés*. C'est le rôle d'une « bibliothèque de
  référence ».
- **`excluded`** : jamais analysés. À utiliser pour une vraie sauvegarde qui doit rester une
  seconde copie.
- **`extensions`** : [seuls ces types de fichiers](#aller-plus-loin) sont
  analysés.

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
  audits suivants ne lisent que les fichiers nouveaux ou modifiés. Rien que lister des dizaines
  de milliers de fichiers prend quelques minutes :
  [chaque étape affiche sa progression](#ce-qui-saffiche-pendant-lanalyse).
- **Lancez avec `-it`** : sans terminal, `clean` ne peut pas demander confirmation (utilisez
  `--yes`) et les couleurs sont désactivées.

## Peut-on lui faire confiance ?

Avant de supprimer des photos de famille, tout le monde se pose la même question : *est-ce
vraiment, vraiment des doublons ?* Ce chapitre explique ce que l'outil appelle un doublon, ce
qu'il vérifie avant de supprimer, comment le vérifier vous-même, et à quoi faire attention.

### Qu'est-ce qu'un doublon ?

Uniquement des fichiers **identiques octet par octet**. L'outil compare d'abord les tailles,
puis une empreinte SHA-256 des 64 premiers Ko, puis une empreinte SHA-256 de tout le contenu.
En pratique, deux fichiers différents n'ont jamais le même SHA-256 : c'est bien moins probable
qu'une erreur de disque.

- **Le nom et la date ne comptent pas.** `IMG_1234.jpg` et `Marie et Paul.jpg` avec les mêmes
  octets sont des doublons. Deux `IMG_0001.jpg` au contenu différent n'en sont pas.
- **Se ressembler ne suffit pas.** Une copie redimensionnée, recompressée, pivotée ou dont les
  métadonnées ont changé est un autre fichier : l'outil n'y touche pas.
- **Seules les photos et vidéos** sont analysées, reconnues par leur extension. Les autres
  fichiers sont ignorés.

### Ce que l'outil vérifie avant de supprimer

Le détail est dans [Comment vos photos restent en sécurité](#comment-vos-photos-restent-en-sécurité).
En bref :

- **L'audit n'écrit jamais.** Montez vos dossiers avec `:ro` et Docker lui-même interdit toute
  écriture.
- **Un fichier vu deux fois n'est pas un doublon.** Un dossier monté deux fois est refusé, et
  un fichier accessible par deux chemins (lien physique) n'est analysé qu'une fois.
- **Juste avant chaque suppression**, `clean` vérifie que la copie gardée existe toujours,
  qu'il s'agit bien d'un autre fichier, et qu'elle est toujours identique octet par octet.
  Sinon, il laisse le fichier en place.
- **Chaque action est écrite dans le journal**, et `undo` reconstruit les copies supprimées à
  partir de celle gardée.

### Vérifiez vous-même

Le rapport (`-v "…:/reports"`) est fait pour ça :

- Les **paires de dossiers** viennent en premier. Un badge signale un dossier qui est
  *entièrement une copie* d'un autre, et chaque paire a sa page qui liste toutes ses copies.
- Un **échantillon aléatoire** de groupes de photos est affiché avec des aperçus.
- **Vérifiez vous-même**, sur chaque groupe, donne une commande PowerShell `Get-FileHash`.
  Collez-la : chaque copie affiche le même SHA-256, calculé par Windows et non par
  media-dedup.
- **`plan.csv`** liste chaque fichier du plan avec son SHA-256, prêt pour Excel.

### Demander un second avis à Czkawka

[Czkawka](https://github.com/qarmin/czkawka) est un détecteur de doublons indépendant et open
source, écrit différemment et avec une autre fonction de hachage. L'image communautaire
`jlesage/czkawka` (environ 500 Mo) contient son outil en ligne de commande. Lancez-le avec les
**mêmes options `-v` que votre audit**. Les options ci-dessous lui donnent le même périmètre
que media-dedup : toutes les tailles de fichier (`-m 1`) et les mêmes extensions (`-x`) :

```powershell
docker run --rm -v "C:\Photos:/data/c/Photos:ro" jlesage/czkawka `
  czkawka_cli dup -d /data -m 1 -W `
  -x 3g2,3gp,arw,avi,avif,bmp,cr2,cr3,dng,flv,gif,heic,heif,jpe,jpeg,jpg,m2ts,m4v,mkv,mov,mp4,mpeg,mpg,mts,nef,orf,pef,png,raf,rw2,srw,tif,tiff,ts,webm,webp,wmv
```

Sa ligne de synthèse, *Found N duplicated files which in G groups*, doit correspondre aux
*Copies en trop, supprimables* (N) et aux *Groupes de fichiers identiques* (G) de media-dedup.
Causes connues d'un petit écart :

- des dossiers exclus dans `config.toml` : ajoutez `-e /data/c/Photos/<dossier>` à Czkawka ;
- un filtre `--ext` sur l'audit ;
- les fichiers cassés : media-dedup écarte les fichiers illisibles des groupes.

Deux outils écrits indépendamment font rarement la même erreur. S'ils sont d'accord, vous
pouvez nettoyer en confiance ; sinon, regardez les différences avant de nettoyer.

### Recommandations

- **Commencez par un audit, puis lisez les paires de dossiers.** Ouvrez quelques paires et
  vérifiez vous-même quelques groupes.
- **Choisissez quelle copie reste.** Le fichier gardé conserve son nom et son dossier ; le nom
  d'une copie supprimée est perdu. Si `Mariage 2015\Marie et Paul.jpg` compte plus que
  `DCIM\IMG_1234.jpg`, indiquez le dossier de l'album dans `--prefer` (ou `folders.preferred`,
  ou protégez-le), puis relancez l'audit.
- **Sauvegardez vos photos avant le premier nettoyage**, par exemple sur un disque externe :
  l'outil garde un exemplaire de chaque photo, pas deux.
- **Mettez en pause la synchronisation cloud** (OneDrive, Google Drive, Dropbox, iCloud)
  pendant le nettoyage. Sinon, les suppressions sont recopiées dans le cloud et sur vos autres
  appareils.
- **Gardez le dossier du journal** : `undo` en a besoin. Ne lancez `purge` que si vous êtes
  sûr.
- Lisez aussi les [Mises en garde](#mises-en-garde) : une vraie sauvegarde doit être exclue,
  et chaque dossier ne doit être monté qu'une fois.

## Développement

**Construire l'image depuis les sources** : utile seulement pour modifier l'outil. Partout où
ce README indique `cavo789/media-dedup`, utilisez alors votre image locale `media-dedup` :

```bash
git clone https://github.com/cavo789/media-deduplication-pipeline.git
cd media-deduplication-pipeline
docker build --tag media-dedup .
```

Chaque push et chaque pull request lancent la barrière qualité et les tests de bout en bout
sur GitHub Actions ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)). Pour publier une
nouvelle version, augmentez `version` dans `pyproject.toml`, commitez et poussez `main`, puis
lancez `release` (voir ci-dessous). Il crée le tag `vX.Y.Z` et le pousse. La CI construit alors
l'image pour amd64 et arm64, lance les tests de bout en bout, puis pousse
`cavo789/media-dedup:<version>` et `:latest` sur Docker Hub, avec un SBOM et une attestation de
provenance. Il faut pour cela deux secrets dans le dépôt : `DOCKERHUB_USERNAME` et
`DOCKERHUB_TOKEN` (un jeton d'accès Docker Hub en lecture/écriture).

Ouvrez le dépôt dans le devcontainer (VS Code, *Reopen in Container*). Chaque nouveau
terminal affiche la liste des commandes d'aide (`welcome` la réaffiche) :

| Commande | Rôle |
|---|---|
| `check` | La barrière qualité complète : pre-commit (ruff, mypy strict, pylint, shellcheck, shfmt, hadolint), puis les tests avec au moins 90 % de couverture des branches. |
| `format`, `tests` | Corrige la mise en forme ; lance des tests ciblés. |
| `dedup …`, `demo` | Lance l'outil depuis les sources sur `/tmp/media-dedup/` ; `demo` crée une arborescence d'exemple et l'audite. |
| `reports`, `reports_stop` | Sert les rapports HTML sur un port libre choisi par le système. |
| `build`, `e2e`, `dive`, `dive_ci` | Construit l'image, lance les tests de bout en bout, inspecte ou contrôle ses couches. |
| `release` | Crée le tag `vX.Y.Z` (la version de `pyproject.toml`) et le pousse : la CI publie l'image. |
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
