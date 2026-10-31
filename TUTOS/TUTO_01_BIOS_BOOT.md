# TUTO 01 — BIOS / BOOT / CGS ALPHA

**But :** reproduire l'ancrage initial sans modifier ComplexGitSync.
**Prérequis :** Python 3.11+ ; terminal ; aucun token GitHub.
**Durée indicative du TP :** selon l'environnement, non garantie.
**Livrable :** table BIOS contrôlée et statut `DECLARED_ONLY`.

## A. Identifier le noyau

L'entrée utilisateur est `atCGS`, la version de protocole `ALPHA 0.0.0`.
Le moteur est `ComplexGitSync M.m.p`, à verrouiller lors d'une intégration.
L'invariant initial proposé dans le fil était :

```text
BIOS BOOT CGS M.m.p
CGS L0 TIME POEX
```

Cette notation historique ne définit pas de format de timestamp ou de signature.
Ne substituez pas une horloge locale à une preuve d'existence vérifiée.

## B. Étape BIOS canonique

```text
atCGS ALPHA BIOS ComplexGitSync M.m.p
ComplexGitSync G POEX .gts
.gts G OPX TWX
TWX ENV HWX DEV
DEV HWX TWX USR
USR TWX G .cgs
```

La première ligne possède cinq jetons : c'est l'identité d'amorçage.
Les cinq suivantes ont exactement quatre jetons selon PRIME G.
La graphie `M.m.p` n'est pas remplacée dans le document canonique.
`POEX` est un symbole de frontière, pas une attestation signée.

## C. Versions antérieures conservées

```text
BIOS ENV HWX TWX
BOOT TWX POEX CGS
CGS POEX TWX GTS
GTS TWX OPX DEV
DEV HWX ENV USR
USR TWX GTS TWX
OPX HWX ENV TWX
```

Ces tuples sont conservés pour la reproductibilité de la conception.
Le dernier `TWX` du tuple `USR` n'est pas une erreur de duplication.
Une révision future devra préciser comment le BIOS appelle le BOOT.

## D. Contrôler les fixtures

```bash
python3 scripts/contract_check.py inspect
```

Cherchez `bios_new_rows = 5` et `bios_history_rows = 7`.
Le contrôle rejette toute mutation des tuples présents dans le TOML.
Aucune opération Git distante n'est lancée par cette commande.

## E. Examiner les données normatives

```bash
python3 - <<'PY'
import tomllib
with open('spec/contracts.toml','rb') as f:
    spec=tomllib.load(f)
print(spec['boot']['identity'])
for row in spec['boot']['current']:
    print(*row)

PY
```

Cette inspection est locale : elle n'ouvre ni GitRepo ni socket.

## Validation complémentaire : cas à automatiser

- **ALPHA** `ComplexGitSync G POEX .gts` : vérifier la séquence littérale.
- **ALPHA** `ComplexGitSync G POEX .gts` : supprimer un champ et attendre un refus.
- **ALPHA** `ComplexGitSync G POEX .gts` : permuter les champs 2 et 3 et attendre un refus.
- **ALPHA** `ComplexGitSync G POEX .gts` : changer la casse et attendre un refus.
- **ALPHA** `.gts G OPX TWX` : vérifier la séquence littérale.
- **ALPHA** `.gts G OPX TWX` : supprimer un champ et attendre un refus.
- **ALPHA** `.gts G OPX TWX` : permuter les champs 2 et 3 et attendre un refus.
- **ALPHA** `.gts G OPX TWX` : changer la casse et attendre un refus.
- **ALPHA** `TWX ENV HWX DEV` : vérifier la séquence littérale.
- **ALPHA** `TWX ENV HWX DEV` : supprimer un champ et attendre un refus.
- **ALPHA** `TWX ENV HWX DEV` : permuter les champs 2 et 3 et attendre un refus.
- **ALPHA** `TWX ENV HWX DEV` : changer la casse et attendre un refus.
- **ALPHA** `DEV HWX TWX USR` : vérifier la séquence littérale.
- **ALPHA** `DEV HWX TWX USR` : supprimer un champ et attendre un refus.
- **ALPHA** `DEV HWX TWX USR` : permuter les champs 2 et 3 et attendre un refus.
- **ALPHA** `DEV HWX TWX USR` : changer la casse et attendre un refus.
- **ALPHA** `USR TWX G .cgs` : vérifier la séquence littérale.
- **ALPHA** `USR TWX G .cgs` : supprimer un champ et attendre un refus.
- **ALPHA** `USR TWX G .cgs` : permuter les champs 2 et 3 et attendre un refus.
- **ALPHA** `USR TWX G .cgs` : changer la casse et attendre un refus.
- **BIOS** `BIOS ENV HWX TWX` : vérifier la séquence littérale.
- **BIOS** `BIOS ENV HWX TWX` : supprimer un champ et attendre un refus.
- **BIOS** `BIOS ENV HWX TWX` : permuter les champs 2 et 3 et attendre un refus.
- **BIOS** `BIOS ENV HWX TWX` : changer la casse et attendre un refus.
- **BIOS** `BOOT TWX POEX CGS` : vérifier la séquence littérale.
- **BIOS** `BOOT TWX POEX CGS` : supprimer un champ et attendre un refus.
- **BIOS** `BOOT TWX POEX CGS` : permuter les champs 2 et 3 et attendre un refus.
- **BIOS** `BOOT TWX POEX CGS` : changer la casse et attendre un refus.
- **BIOS** `CGS POEX TWX GTS` : vérifier la séquence littérale.
- **BIOS** `CGS POEX TWX GTS` : supprimer un champ et attendre un refus.
- **BIOS** `CGS POEX TWX GTS` : permuter les champs 2 et 3 et attendre un refus.
- **BIOS** `CGS POEX TWX GTS` : changer la casse et attendre un refus.
- **BIOS** `GTS TWX OPX DEV` : vérifier la séquence littérale.
- **BIOS** `GTS TWX OPX DEV` : supprimer un champ et attendre un refus.
- **BIOS** `GTS TWX OPX DEV` : permuter les champs 2 et 3 et attendre un refus.
- **BIOS** `GTS TWX OPX DEV` : changer la casse et attendre un refus.
- **BIOS** `DEV HWX ENV USR` : vérifier la séquence littérale.
- **BIOS** `DEV HWX ENV USR` : supprimer un champ et attendre un refus.
- **BIOS** `DEV HWX ENV USR` : permuter les champs 2 et 3 et attendre un refus.
- **BIOS** `DEV HWX ENV USR` : changer la casse et attendre un refus.
- **BIOS** `USR TWX GTS TWX` : vérifier la séquence littérale.
- **BIOS** `USR TWX GTS TWX` : supprimer un champ et attendre un refus.
- **BIOS** `USR TWX GTS TWX` : permuter les champs 2 et 3 et attendre un refus.
- **BIOS** `USR TWX GTS TWX` : changer la casse et attendre un refus.
- **BIOS** `OPX HWX ENV TWX` : vérifier la séquence littérale.
- **BIOS** `OPX HWX ENV TWX` : supprimer un champ et attendre un refus.
- **BIOS** `OPX HWX ENV TWX` : permuter les champs 2 et 3 et attendre un refus.
- **BIOS** `OPX HWX ENV TWX` : changer la casse et attendre un refus.
- **ID** `atCGS ALPHA BIOS ComplexGitSync M.m.p` : vérifier la séquence littérale.
- **ID** `atCGS ALPHA BIOS ComplexGitSync M.m.p` : supprimer un champ et attendre un refus.
- **ID** `atCGS ALPHA BIOS ComplexGitSync M.m.p` : permuter les champs 2 et 3 et attendre un refus.
- **ID** `atCGS ALPHA BIOS ComplexGitSync M.m.p` : changer la casse et attendre un refus.
- Vérifier le BOOT : aucun chemin privé n’est publié.
- Vérifier le BOOT : aucun checkpoint n’est fabriqué.
- Vérifier le BOOT : aucun GitRepo n’est cloné.
- Vérifier le BOOT : aucune commande n’est interprétée comme tuple.
- Vérifier le BOOT : aucune transition n’est exécutée.
- Vérifier le BOOT : la source conserve le format TOML.
- `M.m.p` doit être épinglée avant un boot réel.
- La fixture du BOOT ne contient pas de secret.
- Un champ vide rend l’identité non conforme.
- La preuve L0 reste séparée de l’horloge locale.
- La table courante compte cinq tuples à quatre champs.
- La table antérieure en compte sept.
- `GTS` reste distinct de `.gts`.
- La répétition de TWX est normative.
- Les droits PRIVATE ne dérivent pas de la forme des tuples.
- Aucun clone de dépôt n’est exécuté.
- Une nouvelle version nécessite un changement documenté.
