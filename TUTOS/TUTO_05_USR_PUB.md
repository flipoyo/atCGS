# TUTO 05 — README, USR / PUB, .bit et .wth

**Objectif :** intégrer sans altération les cinq tuples de publication.

## 1. Nouvelle frontière canonique

```text
README atCGS USR PUB
PUB 256 256 .bit
.bit .computo .omniscience .wth
.wth .computo .gts .cgs
.cgs USR PUB .toml
```

Il s'agit de cinq enregistrements `NAME NODE EDGE OP`.
Les deux `256` ne doivent jamais être dédupliqués.
L'extension `.wth` est opaque, sans sérialiseur défini ici.

## 2. Lien avec les anciennes transitions

```text
.gts OPX DEV .cgs
.cgs DEV USR .toml
.toml USR PUB .omniscience
```

La nouvelle table et la table OpFrontier ont des finalités distinctes.
Ne fusionnez pas leurs champs pour construire des tuples de cinq colonnes.
Ne créez pas de quatrième transition OpFrontier artificielle.

## 3. La représentation `.bit`

Le symbole `PUB` associe les dimensions 256 et 256 à `.bit`.
Le simulateur traite 256×256 bits comme 8 192 octets, ligne par ligne.
Le champ `.bit` ne prouve pas à lui seul l'authenticité du GLYPH.
Le fichier du laboratoire n'est pas un objet artistique signé.

## 4. Deux espaces et un moteur

```text
.computo       PRIVATE  (ComplexGraphSync)
.omniscience   PUBLIC   (ComplexGraphSync)
.cgitsync      INTERNAL (ComplexGitSync)
```

Aucun tuple n'est une déclaration de droits d'accès.
La sémantique exacte de `.wth` devra être spécifiée séparément.
Le registre interne Omniscience ne devient pas PUBLIC sans projection.

## 5. Inspecter la nouvelle table

```bash
python3 scripts/contract_check.py inspect
```

Résultat attendu : `public_rows = 5`.
La comparaison est stricte, y compris sur la répétition de `256`.

## 6. Générer un manifeste non publié

```bash
python3 scripts/poex_4x256_simulator.py --output candidate.json
python3 scripts/contract_check.py candidate candidate.json
```

Le candidat doit conserver `poex_verified=false` et `NOT_PUBLISHED`.
Le script ne contacte pas le domaine PUBLIC et n'écrit rien sur GitHub.
Le manifeste contient seulement l'engagement, les tailles et le statut.
Il ne doit jamais transporter les 8 192 octets bruts par défaut.

## 7. Essai négatif

Dans une copie du manifeste, remplacer `poex_verified` par `true`.
Le validateur `candidate` doit refuser cette promotion non justifiée.
Un résultat local exact ne constitue pas un checkpoint authentifié.

## 8. Perspectives de `.wth`

Le protocole doit encore préciser le sens des trois champs associés.
Un format de fichier, une opération de routage et un type d'adresse
ne peuvent pas être déduits de quatre lettres et d'un point initial.

## 9. Définition de réussite

Les cinq tuples sont strictement conservés et contrôlables.
La matrice `.bit` se séquence correctement en 64 paquets.
Aucun contenu PRIVATE n'est exposé comme réponse publique validée.
Le tutoriel 06 regroupe les vérifications et l'agenda de 24 h.

## Validation complémentaire : cas à automatiser

- Tuple 0: `README` reste NAME.
- Tuple 0: `atCGS` reste NODE.
- Tuple 0: `USR` reste EDGE.
- Tuple 0: `PUB` reste OP.
- Tuple 0: refuser la permutation des deux derniers champs.
- Tuple 0: refuser les champs supprimés.
- Tuple 0: refuser la normalisation de casse.
- Tuple 0: aucune permission PRIVATE implicite.
- Tuple 1: `PUB` reste NAME.
- Tuple 1: `256` reste NODE.
- Tuple 1: `256` reste EDGE.
- Tuple 1: `.bit` reste OP.
- Tuple 1: refuser la permutation des deux derniers champs.
- Tuple 1: refuser les champs supprimés.
- Tuple 1: refuser la normalisation de casse.
- Tuple 1: aucune permission PRIVATE implicite.
- Tuple 2: `.bit` reste NAME.
- Tuple 2: `.computo` reste NODE.
- Tuple 2: `.omniscience` reste EDGE.
- Tuple 2: `.wth` reste OP.
- Tuple 2: refuser la permutation des deux derniers champs.
- Tuple 2: refuser les champs supprimés.
- Tuple 2: refuser la normalisation de casse.
- Tuple 2: aucune permission PRIVATE implicite.
- Tuple 3: `.wth` reste NAME.
- Tuple 3: `.computo` reste NODE.
- Tuple 3: `.gts` reste EDGE.
- Tuple 3: `.cgs` reste OP.
- Tuple 3: refuser la permutation des deux derniers champs.
- Tuple 3: refuser les champs supprimés.
- Tuple 3: refuser la normalisation de casse.
- Tuple 3: aucune permission PRIVATE implicite.
- Tuple 4: `.cgs` reste NAME.
- Tuple 4: `USR` reste NODE.
- Tuple 4: `PUB` reste EDGE.
- Tuple 4: `.toml` reste OP.
- Tuple 4: refuser la permutation des deux derniers champs.
- Tuple 4: refuser les champs supprimés.
- Tuple 4: refuser la normalisation de casse.
- Tuple 4: aucune permission PRIVATE implicite.
- Publication: vérifier un checkpoint signé.
- Publication: vérifier les données explicitement autorisées.
- Publication: vérifier le rejet des chemins locaux.
- Publication: vérifier la distinction candidat/public.
- Publication: vérifier les URL de dépôt filtrées.
- Publication: vérifier les champs de réponse minimalistes.
- Publication: vérifier une identité ancrée.
- Publication: vérifier une racine indépendante.
- Le nom `.wth` est opaque dans ALPHA 0.0.0.
- Un champ `.omniscience` ne publie pas une preuve par magie.
- Le 256 répété est fixé par contrat.
- Le contenu PRIVATE doit rester inaccessible à PUB.
- La sortie candidate ne comporte aucune clé secrète.
- Un checkpoint réel doit être authentifié.
- Les tuples récents ne remplacent pas la grammaire `.cgs` du moteur.
- La matrice est binaire, pas un PNG.
- La racine candidate n’est pas un enregistrement mondial.
- L’interface doit signaler `NOT_PUBLISHED` sans ambiguïté.
- Les extensions sont des identifiants littéraux.
