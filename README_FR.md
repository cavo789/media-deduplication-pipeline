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
- **Fichiers cassés** : fichiers vides, images et fichiers RAW impossibles à décoder (JPEG
  tronqué, …), vidéos impossibles à ouvrir.
- **Réversible** : chaque action est journalisée ; `undo` reconstruit chaque copie supprimée à
  partir de la copie conservée, et ressort chaque fichier de la quarantaine.
- **Fichiers compagnons orphelins** : un fichier compagnon (`.xmp`, `.aae`, `.thm`) resté sans
  sa photo est déplacé en quarantaine ; celui qui accompagne sa photo n'est jamais touché.
- **Jamais touchés** : les rafales et photos « similaires », les dossiers protégés.

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
| Recherche des fichiers médias | Parcourt tous les dossiers montés et garde les photos, fichiers RAW et vidéos, [reconnus à leur extension](#aller-plus-loin). Les fichiers compagnons (`.xmp`, `.aae`, `.thm`) sont notés avec les fichiers du même nom à côté d'eux. Les autres fichiers (documents, …) sont ignorés, sauf si [`--ext` les demande](#autres-types-de-fichiers). Le total n'est pas encore connu : un compteur remplace la barre. |
| Vérification de la lisibilité des fichiers | Repère les fichiers cassés : vides (0 octet), images impossibles à décoder (chacune est décodée entièrement, un processus par cœur), fichiers RAW que LibRaw ne peut pas décoder (chaque pixel est lu), vidéos que `ffprobe` ne peut pas ouvrir. Les autres types de fichiers demandés avec `--ext` ne sont pas vérifiés. |
| Comparaison des fichiers de même taille | Deux fichiers ne peuvent être identiques que s'ils ont la même taille. Pour ceux-là, lit leurs premiers et derniers 64 Ko : rapide, et cela en écarte la plupart. |
| Preuve d'identité (SHA-256 complet) | Lit entièrement les candidats restants et calcule leur empreinte SHA-256 : même empreinte, même contenu, octet par octet. L'étape la plus longue avec de grosses vidéos. |
| Nettoyage (`clean`) | Recompare chaque copie, octet par octet, avec celle gardée juste avant de la supprimer ; supprime les fichiers vides ; déplace les illisibles et les [fichiers compagnons orphelins](#fichiers-compagnons) en quarantaine ; journalise chaque action. |
| Restauration (`undo`) | Recrée chaque copie supprimée à partir de celle gardée (date comprise) et ramène les fichiers mis en quarantaine. |

Une étape sans travail est sautée : avec le volume `/cache`, les fichiers déjà vérifiés ou
hachés par un audit précédent ne sont pas relus.

## Lire le résultat

Voici un exemple sur un gros dossier de photos (noms de dossiers modifiés) :

```text
Résumé de l'audit
┌───────────────────────────────────────┬─────────────┐
│ Fichiers média analysés               │      67.947 │
│ Groupes de fichiers identiques        │      11.274 │
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
| Fichiers média analysés | Toutes les photos, fichiers RAW et vidéos trouvés, plus les fichiers des [autres types](#autres-types-de-fichiers) demandés avec `--ext`. Les fichiers compagnons (`.xmp`, …) ne sont pas comptés. |
| Groupes de fichiers identiques | Combien de photos ou vidéos distinctes existent en plusieurs copies identiques. D'autres outils, comme Czkawka, comptent les mêmes groupes : un chiffre pratique pour comparer. |
| Copies en trop, supprimables | Les fichiers que `clean` supprimerait. Pour chaque photo ou vidéo présente plusieurs fois, un exemplaire est gardé et les autres sont en trop : une photo rangée dans 3 dossiers donne 2 copies en trop. |
| Espace libérable | La taille totale de ces copies en trop. |
| Fichiers cassés | Les fichiers vides (0 octet) et ceux qui ne s'ouvrent pas (JPEG ou fichier RAW tronqué, vidéo abîmée). `clean` supprime les vides et déplace les autres en quarantaine, sans jamais les supprimer directement. |
| Fichiers compagnons orphelins | Les [fichiers compagnons](#fichiers-compagnons) (`.xmp`, `.aae`, `.thm`) sans plus aucun fichier du même nom à côté d'eux une fois `clean` passé. Déplacés en quarantaine. |
| Quasi-doublons | La même photo enregistrée à nouveau : réduite (WhatsApp), recompressée, pivotée, ou sans sa date EXIF. Ce ne sont pas des fichiers identiques : `clean` n'y touche pas, sauf si vous ajoutez `--tier near`, voir [plus bas](#quasi-doublons-et-rafales). |
| Rafales | Des photos d'un même appareil prises à quelques secondes d'intervalle. Listées avec la plus nette suggérée ; `clean` ne déplace que les photos que vous [écartez avec `review`](#trier-les-rafales-au-clavier). |
| Durée | Le temps qu'a pris tout l'audit. |

Chaque phrase de *Dossiers partageant des fichiers identiques* décrit deux dossiers qui
contiennent les mêmes fichiers : les copies du premier sont gardées, celles du second sont
supprimées, et la phrase se termine par l'espace libéré. Les paires qui libèrent le plus d'espace
viennent en premier. Quand les deux sont le même dossier, les fichiers y sont en double (`IMG_0001.jpg` et
`IMG_0001 (1).jpg`). Le dossier gardé suit les [règles ci-dessous](#comment-vos-photos-restent-en-sécurité) ;
ce n'est pas celui que vous voulez ? Indiquez-le dans `--prefer` (ou `folders.preferred`) et
relancez l'audit, ou [décidez paire par paire dans le rapport](#aller-plus-loin).

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
extensions analysées. Les extensions des médias, analysées par défaut (`media-dedup audit
--help` les liste aussi), sont ci-dessous ; [d'autres types](#autres-types-de-fichiers)
(`--ext pdf`) sont possibles, avec plus de précautions.

| Type | Extensions |
|---|---|
| Images | avif, bmp, gif, heic, heif, jpe, jpeg, jpg, png, tif, tiff, webp |
| RAW (décodés par LibRaw, aperçu tiré du JPEG intégré par l'appareil) | arw, cr2, cr3, dng, nef, orf, pef, raf, rw2, srw |
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
aléatoire de groupes de photos (fichiers RAW compris, grâce à l'aperçu intégré par
l'appareil), et donne pour chaque groupe son SHA-256 avec une commande
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

**Décider dans le rapport** : ce n'est pas le dossier que vous voulez garder ? Dans le tableau
des *paires de dossiers* d'un rapport d'audit, chaque paire a une liste *Votre décision* :
*Inverser les dossiers* garde les copies du second dossier et supprime celles du premier ;
*Ne pas toucher* ne supprime rien de cette paire. Votre navigateur retient vos choix.
*Téléchargez decisions.json*, enregistrez-le dans le dossier monté sur `/reports`, et ajoutez
`--decisions decisions.json` à la commande `clean` ci-dessus. La page elle-même ne supprime
jamais rien : `clean` refait l'audit, applique vos décisions, montre les paires qui en
résultent et demande confirmation avant de nettoyer, avec toutes les protections (comparaison
octet par octet, journal, `undo`). Le fichier est refusé si d'autres dossiers sont montés, si
une paire décidée n'existe plus (des fichiers ont changé depuis le rapport), ou si une
inversion supprimerait les copies d'un dossier protégé.

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
`cavo789/media-dedup:0.2.0` en fixe une.

### Quasi-doublons et rafales

En plus des copies exactes, l'audit regarde à quoi ressemble chaque photo (empreintes
perceptuelles, netteté, date et appareil EXIF). Ces informations sont calculées pendant qu'il
vérifie que la photo est lisible, et gardées dans le cache.

- **Quasi-doublons** : la même photo enregistrée à nouveau, plus petite (WhatsApp, « réduite
  pour l'e-mail »), recompressée, pivotée ou sans sa date. Tous les tests doivent être
  d'accord : empreintes presque identiques, même forme, et même date de prise de vue (ou
  aucune sur la plus petite copie). Les images vides ou noires ne comptent jamais. La plus
  haute résolution est gardée. Le rapport montre chaque groupe côte à côte, avec la
  résolution, la taille et la netteté de chaque copie.
- **Rafales** : des photos d'un même appareil, à quelques secondes d'intervalle, de la même
  scène. C'est du tri, pas des doublons : elles sont listées, la plus nette suggérée. Un
  simple `clean` n'y touche jamais, et une photo de rafale n'est jamais prise pour un
  quasi-doublon. Vous choisissez les photos qui partent, [au clavier](#trier-les-rafales-au-clavier).

Un simple `clean` ne touche jamais aux quasi-doublons. Après les avoir vérifiés dans le
rapport, ajoutez `--tier near` : les copies sont **déplacées en quarantaine** (elles ne sont
pas identiques, on ne pourrait pas les reconstruire à partir de la photo gardée), et `undo`
les remet en place. `purge` les supprime définitivement. Il faut pour cela le montage
`/quarantine` :

```powershell
docker run --rm -it `
  -v "C:\Photos:/data/c/Photos" `
  -v "$HOME\media-dedup\journal:/journal" `
  -v "$HOME\media-dedup\quarantine:/quarantine" `
  cavo789/media-dedup clean --tier near
```

### Trier les rafales au clavier

Trier des milliers de photos de rafale fichier par fichier est fastidieux. `review` analyse,
puis sert dans votre navigateur une page qui montre **une série à la fois**, chaque photo en
grand, la plus nette marquée ⭐ :

| Touche | Action |
|---|---|
| `←` `→` (ou espace) | Série précédente ou suivante |
| `1` … `9` | Écarter cette photo, ou la garder à nouveau (un clic sur la photo fonctionne aussi) |
| `S` | Ne garder que la photo la plus nette |
| `A` | Garder toutes les photos de la série |

Chaque choix est **enregistré aussitôt** dans `decisions.json`, dans le dossier monté sur
`/reports` : arrêtez avec Ctrl+C quand vous voulez, le `review` suivant reprend vos choix. Une
photo d'un dossier protégé n'est jamais écartée, et chaque série garde toujours au moins une
photo.

```powershell
docker run --rm -it --name media-dedup-review -p 127.0.0.1::8080 `
  -v "C:\Photos:/data/c/Photos:ro" `
  -v "$HOME\media-dedup\reports:/reports" `
  -v media-dedup-cache:/cache `
  cavo789/media-dedup review
```

`-p 127.0.0.1::8080` laisse Docker choisir un port libre, joignable depuis votre ordinateur
seulement. Une fois l'analyse terminée, lancez `docker port media-dedup-review 8080` dans un
autre terminal : il donne l'adresse à ouvrir dans votre navigateur (par exemple
`127.0.0.1:49153`).

La page ne touche jamais une photo. Une fois le tri fini, ajoutez `--decisions decisions.json` à
la [commande `clean`](#aller-plus-loin) : les photos écartées sont **déplacées en quarantaine**
(ce ne sont pas des copies, rien ne pourrait les reconstruire), `undo` les remet en place et
`purge` les supprime définitivement. Le fichier est refusé si une série a changé depuis le tri ;
donnez à `review` et à `clean` les mêmes options `--prefer`, `--protect` et `--exclude`. Le même
fichier peut aussi contenir les [décisions sur les paires de dossiers](#aller-plus-loin) d'un
rapport : `review` les conserve.

### Fichiers compagnons

Les fichiers compagnons (*sidecars*) sont de petits fichiers posés à côté d'une photo ou d'une
vidéo, qui en gardent les métadonnées ou les retouches : `.xmp` (Lightroom, digiKam,
darktable), `.aae` (retouches de l'iPhone), `.thm` (vignettes des caméscopes). Un fichier
compagnon appartient aux fichiers de son dossier qui portent le même nom : `IMG_1.xmp` à
`IMG_1.jpg` ou `IMG_1.CR2`, et `IMG_1.CR2.xmp` à `IMG_1.CR2`, sans tenir compte de la casse.

- **À côté de sa photo**, un fichier compagnon n'est jamais touché.
- **Sa photo est gardée** : entre des copies identiques, celle qui a un fichier compagnon est
  gardée, et elle conserve ainsi ses retouches. Seul un dossier protégé ou préféré passe avant.
  Quand plusieurs copies ont chacune leur fichier compagnon, les autres règles les départagent.
- **Orphelin** : une fois que `clean` a supprimé ou déplacé tous les fichiers du même nom à
  côté de lui (ou s'il n'y en avait déjà aucun), un fichier compagnon ne sert plus à rien.
  `clean` le déplace en quarantaine, sans jamais le supprimer, après avoir vérifié qu'aucun
  fichier du même nom n'est revenu. `undo` le remet en place ; `purge` le supprime
  définitivement. Sans le montage `/quarantine`, les orphelins restent en place.
- **Avec `--ext`**, l'audit ne regarde qu'une partie des fichiers : les fichiers compagnons
  déjà seuls avant le nettoyage restent où ils sont, seuls ceux que le nettoyage lui-même
  laisse seuls sont déplacés.
- **Les dossiers protégés** ne sont jamais modifiés, fichiers compagnons compris.

Le fichier compagnon d'une copie supprimée n'est pas déplacé à côté de la copie gardée : il
devient orphelin. Pour garder une autre copie *avec* ses retouches, indiquez son dossier dans
`--prefer`.

### Autres types de fichiers

media-dedup est fait pour les photos et les vidéos : sans `--ext`, rien d'autre n'est
analysé. `--ext` (ou `[scan] extensions`) accepte aussi d'autres extensions, par exemple pour
trouver les documents en double d'un dossier familial :

```powershell
docker run --rm -it `
  -v "C:\Users\Moi\Documents:/data/c/Users/Moi/Documents" `
  -v "$HOME\media-dedup\journal:/journal" `
  -v "$HOME\media-dedup\quarantine:/quarantine" `
  cavo789/media-dedup --locale fr clean --ext pdf,docx
```

Ces fichiers sont traités avec plus de précautions que les photos. Pour une photo, le dossier
n'est qu'une façon de ranger ; pour un document ou un programme, **l'endroit où se trouve le
fichier peut être ce qui le fait fonctionner** : un `LICENSE`, un `__init__.py` ou un modèle
identique dans deux projets est normal, et supprimer « la copie » casse l'un d'eux.

- **Seulement comparés**, octet par octet : jamais décodés (les images passent par Pillow, les
  fichiers RAW par LibRaw, les vidéos par `ffprobe` ; les autres types n'ont aucune
  vérification), pas d'aperçu, pas de quasi-doublons. Un fichier vide n'est jamais « cassé » :
  ce peut être un marqueur dont un programme a besoin.
- **Leurs copies sont déplacées en quarantaine**, jamais supprimées : `clean` refuse de
  s'exécuter sans le montage `/quarantine`. `undo` les remet en place ; `purge` les supprime
  définitivement.
- **Les dossiers de logiciels sont ignorés** : `.git`, `.hg`, `.svn`, `node_modules`,
  `.venv`, `venv`, `site-packages`, `__pycache__`, `AppData`, `ProgramData`, `Program Files`,
  `Program Files (x86)` et `Windows`, quelle que soit leur casse.
- **Une faute de frappe n'est pas refusée** : `--ext jpgg` est une extension valable, qui ne
  correspond simplement à rien. L'audit nomme les extensions qui ne sont ni des photos ni des
  vidéos : lisez cet avertissement.
- **Les fichiers compagnons** (`.xmp`, `.aae`, `.thm`) ne peuvent pas être demandés : ils
  [suivent leur photo](#fichiers-compagnons).
- **`--ext` limite toujours l'analyse** : `--ext jpg,pdf` analyse les photos JPEG et les
  documents PDF, pas les fichiers RAW ni les vidéos.

Montez les dossiers qui contiennent vos documents, jamais un disque entier ni `C:\Users` :
les programmes et leurs données s'y trouvent aussi.

## Comment vos photos restent en sécurité

| Étape | Garantie |
|---|---|
| `audit` | Lecture seule : montez vos dossiers avec `:ro` et Docker lui-même interdit toute écriture. |
| Copie conservée | Choix déterministe : un dossier protégé, puis vos dossiers préférés (dans l'ordre), puis la copie qui a un [fichier compagnon](#fichiers-compagnons) (ses retouches), un nom qui ne ressemble pas à une copie (`IMG (1).jpg`, `IMG - Copie.jpg`, …), un nom choisi par quelqu'un plutôt que généré par un appareil photo ou une application (`Marie et Paul.jpg` plutôt que `IMG_1234.jpg`), un dossier nommé par quelqu'un plutôt qu'un dossier générique (`Vacances 2019` plutôt que `DCIM\100CANON`), la date la plus ancienne, le chemin le plus court. Le rapport indique, pour chaque groupe, la règle qui a décidé. Vos [décisions dans le rapport](#aller-plus-loin) (`--decisions`) passent par-dessus. |
| Un fichier, deux chemins | Un dossier monté deux fois est refusé ; un fichier accessible par deux chemins (lien physique) n'est analysé qu'une fois, jamais comme doublon de lui-même. |
| Avant chaque suppression | La copie conservée doit encore exister, être un autre fichier et être identique octet par octet ; sinon, le fichier est ignoré. |
| Chaque action | Écrite dans le journal *avant* (`pending`) et *après* (`done`) : une interruption ne fait jamais perdre le fil. |
| Doublons | Réellement supprimés (l'espace est libéré tout de suite) ; `undo` les reconstruit depuis la copie conservée, date comprise, même d'un disque à l'autre. |
| Fichiers illisibles | Déplacés en quarantaine, jamais supprimés directement ; `purge` les supprime définitivement quand vous êtes sûr·e. |
| Quasi-doublons | Jamais touchés par défaut. Avec `--tier near`, déplacés en quarantaine (jamais supprimés) après vérification : la photo gardée existe toujours, la copie est bien le fichier vu par l'audit. `undo` les remet en place. |
| Rafales | Jamais touchées par défaut. Les photos que vous [écartez avec `review`](#trier-les-rafales-au-clavier) sont déplacées en quarantaine (jamais supprimées) par `clean --decisions`, après vérification : une photo gardée est toujours là, la photo écartée est bien le fichier montré par le tri. `undo` les remet en place. |
| Autres types de fichiers | Seulement s'ils sont demandés avec `--ext` : [leurs copies](#autres-types-de-fichiers) sont déplacées en quarantaine (jamais supprimées), et les dossiers de logiciels (`.git`, `node_modules`, `AppData`, …) sont ignorés. |
| Fichiers compagnons | Jamais touchés à côté de leur photo. Un orphelin est déplacé en quarantaine (jamais supprimé) après vérification : inchangé depuis l'audit, et aucun fichier du même nom à côté de lui. `undo` le remet en place. |
| Chaque groupe | Garde toujours au moins une copie. |

## Points de montage

| Montage | Contenu | Nécessaire |
|---|---|---|
| `/data/<lecteur>/<chemin>` | Les dossiers à analyser (`C:\Photos` → `/data/c/Photos`). | toujours ; `:ro` pour `audit` |
| `/config` | `config.toml` uniquement, créé et commenté au premier lancement. | facultatif |
| `/journal` | Un journal JSONL par nettoyage. | **obligatoire** pour `clean`, `undo`, `history` |
| `/quarantine` | Fichiers illisibles, fichiers compagnons orphelins, quasi-doublons, photos de rafale écartées et copies d'autres types de fichiers déplacés par `clean`. | pour les traiter |
| `/reports` | Un dossier par exécution (`report.html`, une page par paire de dossiers, vignettes, `plan.csv`), `index.html`, et le `decisions.json` de `review`. | facultatif ; **obligatoire** pour `review` |
| `/cache` | Index SQLite : les audits suivants ne relisent que les fichiers nouveaux ou modifiés. | facultatif, recommandé |

Chaque montage manquant ou non accessible en écriture est expliqué par une astuce 💡. L'image
fonctionne aussi avec `--read-only --tmpfs /tmp`.

## Commandes

| Commande | Rôle |
|---|---|
| `audit` | Trouve les doublons exacts et les fichiers cassés. N'écrit jamais dans `/data`. |
| `review` | Analyse, puis [trie les rafales](#trier-les-rafales-au-clavier) dans votre navigateur, une à la fois, au clavier. N'écrit jamais dans `/data`. |
| `clean` | Audite, demande confirmation, puis supprime les copies en double et les fichiers vides, et met les fichiers illisibles et les fichiers compagnons orphelins en quarantaine. |
| `undo [EXÉCUTION]` | Restaure chaque fichier d'un nettoyage (le plus récent par défaut). |
| `history` | Liste les nettoyages : fichiers supprimés, espace libéré, quarantaine, restaurations. |
| `reports [--prune N]` | Liste les rapports et régénère `index.html` ; `--prune N` garde les N plus récents. |
| `purge [EXÉCUTION]` | Supprime définitivement la quarantaine d'un nettoyage (de tous par défaut). |
| `crosscheck` | Refait l'audit, puis le compare aux résultats de [Czkawka](#demander-un-second-avis-à-czkawka), un détecteur de doublons indépendant. |
| `config` | Affiche chaque réglage, son origine, et l'état de chaque point de montage. |

Les options globales se placent **avant** la commande : `media-dedup --locale fr audit`.

| Option | Rôle |
|---|---|
| `--locale en\|fr` | Langue de l'interface (anglais par défaut) ; les nombres et tailles la suivent : `67,947` et `44.3 GB`, ou `67.947` et `44,3 Go`. |
| `--verbosity error\|warning\|info\|debug` | Niveau de détail des journaux. |
| `--color auto\|always\|never` | Couleurs ANSI (`NO_COLOR` est respecté). |
| `--prefer CHEMIN` | (`audit`, `review`, `clean`, `crosscheck`) Dossier dont les copies sont conservées en priorité ; répétable, l'ordre compte. |
| `--protect CHEMIN` | (`audit`, `review`, `clean`, `crosscheck`) Dossier jamais modifié ; ses fichiers sont les copies conservées. |
| `--exclude CHEMIN` | (`audit`, `review`, `clean`, `crosscheck`) Dossier jamais analysé. |
| `--ext EXT` | (`audit`, `clean`, `crosscheck`) N'analyse que ces extensions (`--ext png,webp`) ; toutes celles des photos, RAW et vidéos par défaut. [D'autres types](#autres-types-de-fichiers) aussi (`--ext pdf,docx`). |
| `--yes`, `-y` | (`clean`, `purge`) Ne pas demander de confirmation. |
| `--tier exact\|near` | (`clean`) `exact` (par défaut) : seulement les copies identiques octet par octet. `near` : déplace aussi les [quasi-doublons](#quasi-doublons-et-rafales) en quarantaine. |
| `--decisions FICHIER` | (`clean`) Applique les [décisions sur les paires de dossiers téléchargées depuis un rapport](#aller-plus-loin) et les photos de rafale [écartées avec `review`](#trier-les-rafales-au-clavier) ; un chemin relatif est lu dans `/reports`. (`review`) Le fichier où les choix sont enregistrés, `decisions.json` par défaut. |
| `--port PORT` | (`review`) Port de la page dans le conteneur, `8080` par défaut ; publiez-le avec `-p 127.0.0.1::8080`. |

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
extensions = []       # p. ex. ["png", "webp"] ou ["pdf"] ; vide : photos, RAW et vidéos

[keep]                 # en commentaire : listes intégrées ('media-dedup config' les affiche)
# generated_names = ['IMG_\d+', 'DSC\d+']   # noms générés par les appareils et applications
# generic_folders = ['DCIM', 'Camera']       # dossiers créés par les appareils et applications

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
  analysés ; [d'autres types](#autres-types-de-fichiers) que les photos et vidéos sont
  permis.
- **`generated_names`**, **`generic_folders`** : expressions régulières portant sur un nom de
  fichier entier (sans extension) ou un nom de dossier, sans tenir compte de la casse. Entre
  copies identiques, un nom ou un dossier qui correspond vaut moins :
  `Mariage 2015\Marie et Paul.jpg` est gardé plutôt que `DCIM\IMG_1234.jpg`. Une liste vide
  `[]` désactive la règle.

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
  [chaque étape affiche sa progression](#ce-qui-saffiche-pendant-lanalyse). Après la mise à
  jour vers la 0.1.1, le premier audit décode encore une fois chaque photo, pour décrire à
  quoi elle ressemble.
- **Lancez avec `-it`** : sans terminal, `clean` ne peut pas demander confirmation (utilisez
  `--yes`) et les couleurs sont désactivées.
- **Dossiers où l'outil ne peut pas écrire** : quand un dossier donné à `-v` n'existe pas
  encore, Docker le crée pour `root`, et l'outil (qui ne tourne pas en `root`) ne peut pas y
  écrire. La commande s'arrête alors avant l'analyse et nomme le dossier. Créez vos dossiers
  avant `docker run` et, depuis WSL ou Linux, ajoutez `--user "$(id -u):$(id -g)"` ; un dossier
  déjà créé par Docker redevient le vôtre avec `sudo chown "$(id -u):$(id -g)" <dossier>`. Un
  `:ro` sur `/journal`, `/quarantine`, `/reports` ou `/cache` l'arrête de la même façon. Seul
  `config.toml` est facultatif : il n'est alors pas créé. Si seul le rapport échoue après un
  audit, un avertissement le signale et les résultats restent à l'écran.

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
  métadonnées ont changé est un autre fichier. L'audit la liste comme
  [quasi-doublon](#quasi-doublons-et-rafales), mais `clean` n'y touche pas, sauf si vous le
  demandez avec `--tier near`, et alors il la déplace seulement en quarantaine.
- **Seuls les photos, fichiers RAW et vidéos** sont analysés, reconnus par leur extension.
  Les autres fichiers seulement si vous [les demandez](#autres-types-de-fichiers) avec
  `--ext`, et leurs copies sont alors déplacées en quarantaine, jamais supprimées.

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
source, écrit différemment et avec une autre fonction de hachage. Deux outils écrits
indépendamment font rarement la même erreur : s'ils sont d'accord, vous pouvez nettoyer en
confiance.

**1. Lancez l'audit avec un dossier de rapports.** Quand il trouve des doublons, `audit` se
termine par une astuce *Second avis* et la commande Czkawka exacte pour vos dossiers : mêmes
options `-v`, mêmes extensions, mêmes dossiers exclus, toutes les tailles de fichier. Elle
ressemble à ceci (l'image communautaire `jlesage/czkawka`, environ 500 Mo, contient l'outil en
ligne de commande de Czkawka) :

```powershell
docker run --rm -v "C:\Photos:/data/c/Photos:ro" -v "$HOME\media-dedup\reports:/out" `
  jlesage/czkawka:v26.09.2 czkawka_cli dup -d /data -m 1 -W -N -C /out/czkawka.json `
  -x 3g2,3gp,arw,avi,avif,bmp,cr2,cr3,dng,flv,gif,heic,heif,jpe,jpeg,jpg,m2ts,m4v,mkv,mov,mp4,mpeg,mpg,mts,nef,orf,pef,png,raf,rw2,srw,tif,tiff,ts,webm,webp,wmv
```

**2. Collez-la et lancez-la.** Czkawka écrit ses résultats, `czkawka.json`, dans votre dossier
de rapports. Depuis WSL, écrivez vos dossiers `/mnt/c/...` au lieu de `C:\...`.

**3. Comparez**, avec les mêmes options que l'audit :

```powershell
docker run --rm -it -v "C:\Photos:/data/c/Photos:ro" `
  -v "$HOME\media-dedup\reports:/reports" -v media-dedup-cache:/cache `
  cavo789/media-dedup crosscheck
```

`crosscheck` refait l'audit (rapidement, grâce au cache) et compare les deux outils groupe par
groupe :

- *Czkawka est d'accord : les mêmes N copies en trop dans G groupes* ;
- ou *Czkawka n'est pas d'accord sur N groupes*, avec la liste des groupes trouvés par un seul
  des deux outils. Regardez-les avant de nettoyer.

Les fichiers que media-dedup laisse volontairement de côté sont mis à part et comptés, pas
signalés comme des différences : autres types de fichiers, dossiers exclus ou système, fichiers
cassés. Le verdict figure aussi dans le rapport HTML, et `clean` le rappelle avant de demander
confirmation. C'est une information : `clean` ne l'exige jamais.

### Recommandations

- **Commencez par un audit, puis lisez les paires de dossiers.** Ouvrez quelques paires et
  vérifiez vous-même quelques groupes.
- **Vérifiez quelle copie reste.** Le fichier gardé conserve son nom et son dossier ; le nom
  d'une copie supprimée est perdu. L'outil préfère déjà `Mariage 2015\Marie et Paul.jpg` à
  `DCIM\IMG_1234.jpg`, et le rapport indique pourquoi chaque copie a été gardée. Ce n'est pas
  celle que vous voulez ? Indiquez le dossier dans `--prefer` (ou `folders.preferred`, ou
  protégez-le), puis relancez l'audit.
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

L'image compile son propre `ffprobe`, environ 1 Mo au lieu de 141 Mo pour une version
complète : l'outil demande seulement si le conteneur d'une vidéo s'ouvre, donc l'étape
`ffprobe` du `Dockerfile` ne garde que les démultiplexeurs des extensions vidéo analysées. Une
nouvelle extension vidéo demande aussi son démultiplexeur à cet endroit ; un test vérifie que
les deux listes concordent.

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
| `ci`, `ci_logs` | Dernières exécutions de la CI sur la branche ; logs des étapes en échec de la dernière exécution ratée. La CLI GitHub demande `gh auth login` une fois. |

Les réglages et connexions des outils (`~/.config`, p. ex. le jeton de la CLI GitHub) sont
dans le volume Docker `media-dedup-config`, hors de l'espace de travail : ils survivent aux
reconstructions et ne peuvent jamais être commités. N'écrivez jamais de jeton dans un fichier
suivi par git (`devcontainer.json` compris) : ce dépôt est public.

Règles de code, appliquées par l'outillage :

- tout est typé ;
- 200 lignes maximum par fichier et 3 paramètres maximum par fonction ;
- code en anglais ;
- chaque texte affiché passe par gettext.

Les caches n'atterrissent jamais dans le dépôt : ils vivent dans `/tmp`.

La feuille de route (quasi-doublons, netteté, rafales, interface de revue, …) se trouve dans
[.todos/plan.md](.todos/plan.md).
