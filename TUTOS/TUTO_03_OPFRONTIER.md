# TUTO 03 — System Layers et OpFrontier

**Objectif :** distinguer API d'accès, orchestration et projection PUBLIC.

## 1. Quatre System Layers

```text
PRIME CGS = {OPX, DEV, USR, PUB}
```

`OPX` : frontière opérationnelle, traitement privé autorisé.
`DEV` : opérations de développement soumises aux protections du moteur.
`USR` : demandeurs authentifiés ou non selon la politique d'accès.
`PUB` : présentation contrôlée d'un résultat publiable.

Ce ne sont pas quatre réécritures de ComplexGitSync.
Ce ne sont pas les niveaux numériques des anciennes annotations Ring.

## 2. Les trois transitions canoniques

```text
.gts OPX DEV .cgs
.cgs DEV USR .toml
.toml USR PUB .omniscience
```

Chaque transition a exactement quatre champs.
Il y a **trois transitions**, non une quatrième transition implicite.
Ces quadruplets sont des descriptions, jamais des `cp` automatiques.

## 3. Séparation des espaces

```text
PUBLIC  = .omniscience
PRIVATE = .computo
INTERNAL = .cgitsync
```

Les deux premiers espaces sont des domaines de ComplexGraphSync.
Le troisième est la mémoire opérationnelle du moteur ComplexGitSync.
Il ne faut pas renommer `.cgitsync` en `.computo`.

## 4. Rôle d'OpFrontier

Valider un sélecteur et une transition.
Préserver l'identité Merkle native des `.gts` existants.
Faire exécuter les mutations par les API autorisées du moteur.
Refuser l'émission PUBLIC d'un arbre PRIVATE brut.
Émettre un résultat non vérifié lorsqu'il manque un checkpoint.

## 5. Interface cible

```bash
# Cible d'architecture, non implémentée dans atCGS PR #1.
pixi run '@cgs' OPX
pixi run '@cgs' DEV
pixi run '@cgs' USR
pixi run '@cgs' PUB
```

Actuellement la PR #1 transmet encore des verbes `cgitsync` bruts.
Ne présentez pas ces commandes cibles comme déjà opérationnelles.

## 6. Rôles des preuves

Le vecteur PoE peut limiter des champs exposés.
Il ne constitue pas une politique d'authentification.
`TreeProfile.USER/DEV` dérive de la configuration GitTree, pas d'un ACL.
Les droits doivent être décidés à chaque frontière du serveur PUBLIC.

## 7. Vérification des tuples

```bash
python3 scripts/contract_check.py inspect
```

Le compte rendu doit confirmer `opfrontier_rows = 3`.
Les changements de casse, d'ordre et de champ doivent être refusés.

## 8. Scénarios de sécurité

Une requête `USR` ne peut écrire sur `.computo` par défaut.
La réponse `PUB` ne doit pas inclure des secrets d'infrastructure.
Un hash valide ne certifie pas la portée des droits.
Une preuve absente est différente d'une preuve falsifiée.
Un dépôt supprimé peut être non disponible sans invalidité historique.

## 9. Critère de sortie

Trois transitions immuables sont décrites et vérifiées.
La procédure n'effectue aucune mutation Git.
La frontière PUBLIC n'est pas considérée en service.
Le tutoriel 04 teste le flux binaire 4×256.

## Validation complémentaire : cas à automatiser

- Transition 1: entrée `.gts` déclarée.
- Transition 1: couche source `OPX` exacte.
- Transition 1: couche destination `DEV` exacte.
- Transition 1: sortie `.cgs` exacte.
- Transition 1: une inversion doit échouer.
- Transition 2: entrée `.cgs` déclarée.
- Transition 2: couche source `DEV` exacte.
- Transition 2: couche destination `USR` exacte.
- Transition 2: sortie `.toml` exacte.
- Transition 2: une inversion doit échouer.
- Transition 3: entrée `.toml` déclarée.
- Transition 3: couche source `USR` exacte.
- Transition 3: couche destination `PUB` exacte.
- Transition 3: sortie `.omniscience` exacte.
- Transition 3: une inversion doit échouer.
- OPX: vérifier entrée autorisée explicite.
- OPX: vérifier accès PRIVATE refusé sans droit.
- OPX: vérifier rejet du nom en minuscule.
- OPX: vérifier pas de proxy brut.
- OPX: vérifier état de preuve respecté.
- OPX: vérifier pas de fuite de chemin interne.
- OPX: vérifier pas de mutation publique.
- DEV: vérifier entrée autorisée explicite.
- DEV: vérifier accès PRIVATE refusé sans droit.
- DEV: vérifier rejet du nom en minuscule.
- DEV: vérifier pas de proxy brut.
- DEV: vérifier état de preuve respecté.
- DEV: vérifier pas de fuite de chemin interne.
- DEV: vérifier pas de mutation publique.
- USR: vérifier entrée autorisée explicite.
- USR: vérifier accès PRIVATE refusé sans droit.
- USR: vérifier rejet du nom en minuscule.
- USR: vérifier pas de proxy brut.
- USR: vérifier état de preuve respecté.
- USR: vérifier pas de fuite de chemin interne.
- USR: vérifier pas de mutation publique.
- PUB: vérifier entrée autorisée explicite.
- PUB: vérifier accès PRIVATE refusé sans droit.
- PUB: vérifier rejet du nom en minuscule.
- PUB: vérifier pas de proxy brut.
- PUB: vérifier état de preuve respecté.
- PUB: vérifier pas de fuite de chemin interne.
- PUB: vérifier pas de mutation publique.
- Frontière .gts → .cgs : aucune publication automatique.
- Frontière .cgs → .toml : aucune publication automatique.
- Frontière .toml → .omniscience : aucune publication automatique.
- Une requête externe ne peut pas forcer `level=PUBLIC`.
- Aucune permission n’est déduite de l’index d’un layer.
- La lecture publique ne mutate aucun GitRepo.
- Le moteur garde ses propres verrous et contrôles.
- La projection PUBLIC expurge chemins et identifiants secrets.
- La présence d’une racine ne prouve pas la disponibilité d’un repo.
- Les trois transitions restent ordonnées.
- Le `PUB` cible peut répondre sans bootstrap privé.
