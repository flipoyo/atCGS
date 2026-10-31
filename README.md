# atCGS — ComplexGraphSync ALPHA 0.0.0

**README canonique — USR / PUB / BIOS / POEX / OpFrontier.**

Ce dépôt décrit un prototype exécutable local, non un service PUBLIC déployé.
Il conserve le moteur de ComplexGitSync et matérialise les frontières de CGS.
Objectif : une architecture falsifiable, reproductible et minimale en 24 h.

## 1. Invariant PRIME G

`PRIME G = {NAME, NODE, EDGE, OP}` : exactement quatre champs ordonnés.
Les noms, extensions, répétitions et majuscules font partie du contrat.
`*G` désigne un OperatingSpace requestable, pas une réponse déjà vérifiée.

## 2. Nouvelle frontière README / USR / PUB

```text
README atCGS USR PUB
PUB 256 256 .bit
.bit .computo .omniscience .wth
.wth .computo .gts .cgs
.cgs USR PUB .toml
```

Ces cinq lignes sont des tuples PRIME G, conservés sans normalisation.
`PUB 256 256 .bit` fixe une représentation binaire 256×256 comme référence.
`.bit` constitue ici une désignation d'artefact, non une permission de le publier.
`.wth` est une étiquette opaque : aucune sémantique inventée par le tutoriel.
`.computo` appartient au domaine PRIVATE de ComplexGraphSync.
`.omniscience` désigne sa frontière PUBLIC, limitée aux preuves publiables.
Les chaînes de caractères ne sont pas des commandes d'exécution implicites.

## 3. BIOS / BOOT

```text
atCGS ALPHA BIOS ComplexGitSync M.m.p
ComplexGitSync G POEX .gts
.gts G OPX TWX
TWX ENV HWX DEV
DEV HWX TWX USR
USR TWX G .cgs
```

La première ligne est l'identité d'amorçage et la version du moteur à épingler.
`M.m.p` est un espace réservé : ne pas inventer une version installée.
Les cinq lignes suivantes constituent des tuples stricts à quatre champs.
`ENV`, `HWX`, `TWX` sont conservés comme symboles tant que non spécifiés.
`BOOT` ne signifie pas preuve d'existence authentifiée.

## 4. System Layers et OpFrontier

```text
PRIME CGS = {OPX, DEV, USR, PUB}
.gts OPX DEV .cgs
.cgs DEV USR .toml
.toml USR PUB .omniscience
```

Les quatre System Layers ne sont pas quatre moteurs Git.
Les trois frontières de quatre champs n'autorisent aucune copie automatique.
`OPX` et `DEV` restent liés aux opérations privées autorisées.
`USR` exprime la demande ; `PUB` limite ce qui peut être rendu public.
Le décorateur `@cgs` accepte uniquement ces quatre sélecteurs (ALPHA.md).
La CLI historique `cgitsync` demeure interne et autonome.

## 5. POEX — transport de 256×256 bits

```text
Matrix = 256 rows × 256 bits = 65 536 bits = 8 192 bytes
Packet = 4 rows × 256 bits = 1 024 bits = 128 bytes
Stream = 64 indexed packets, in ascending row-major order
.poe   = one zero-count report per 4-bit quartet
Total  = 16 384 reports; 256 reports per packet
```

Le compteur de zéros ne prouve ni identité ni existence à un instant donné.
La racine Merkle des paquets POEX est distincte du MerkleRoot du GitTree.
Un changement d'un bit, une permutation ou un paquet manquant sont rejetés.
Le dernier quartet est conservé logiquement ; aucun pointeur Rust n'est simulé.

## 6. Espaces et publication

```text
ComplexGraphSync PRIVATE = .computo
ComplexGraphSync PUBLIC  = .omniscience
ComplexGitSync INTERNAL  = .cgitsync
```

Un manifeste candidat n'est pas un checkpoint authentifié.
Aucune sortie publique ne contient de secret, chemin privé ou GitTree brut.
L'ancien registre Omniscience interne PRIVATE n'est pas rendu public de force.
Un succès local ne signifie pas publication sur un réseau.

## 7. Démarrage du laboratoire hors réseau

Requis : Python 3.11+ ; aucune dépendance externe pour ce démonstrateur.
Depuis la racine du répertoire extrait :

```bash
python3 scripts/contract_check.py inspect
python3 scripts/poex_4x256_simulator.py --output candidate.json
python3 scripts/contract_check.py candidate candidate.json
python3 -m unittest discover -s tests -v
```

L'option `inspect` valide les tuples du fichier `spec/contracts.toml`.
Le séquenceur utilise par défaut une matrice de démonstration déterministe.
`candidate` doit afficher `NOT_PUBLISHED` et `poex_verified=false`.
L'ensemble fonctionne sans clonage de dépôt ni accès à `.computo` réel.

## 8. TUTORIELS 150 lignes chacun

- [TUTO 01 — BIOS / BOOT](TUTOS/TUTO_01_BIOS_BOOT.md)
- [TUTO 02 — PRIME G et DELTA/NABLA](TUTOS/TUTO_02_PRIME_G.md)
- [TUTO 03 — System Layers et OpFrontier](TUTOS/TUTO_03_OPFRONTIER.md)
- [TUTO 04 — POEX 4×256](TUTOS/TUTO_04_POEX.md)
- [TUTO 05 — USR / PUB, .bit et .wth](TUTOS/TUTO_05_USR_PUB.md)
- [TUTO 06 — Intégration et roadmap 24 h](TUTOS/TUTO_06_INTEGRATION.md)

## 9. Réalité du code amont

`atCGS` PR #1 (fusionnée) relayait plusieurs commandes `cgitsync` brutes.
Elles sont désormais refusées hors d'un sélecteur `OPX`/`DEV` autorisé.
`ComplexGitSync` fournit le moteur GitTree / State / Memory / Integrity.
Les tutoriels du paquet sont des exemples reproductibles, non une PR fusionnée.

## 10. Critères de release ALPHA

- [ ] Les cinq tuples README/USR/PUB sont inchangés.
- [ ] Les six symboles BIOS nouveaux conservent leur ordre d'origine.
- [x] Les quatre System Layers sont les seules entrées `@cgs` exposées.
- [ ] La preuve cryptographique des paquets se vérifie indépendamment.
- [ ] Les accès PRIVATE ne sont jamais promus par le niveau PoE.
- [ ] `.omniscience` ne sert que des preuves autorisées et authentifiées.
- [ ] La compatibilité Merkle schema-1 de ComplexGitSync est préservée.
- [ ] Les tests CI documentent les échecs, pas seulement les succès.

## 11. Suivi

ComplexGitSync #193 : https://github.com/flipoyo/ComplexGitSync/issues/193
atCGS #2 : https://github.com/flipoyo/atCGS/issues/2
atCGS PR #1 : https://github.com/flipoyo/atCGS/pull/1

**Statut : modèle documentaire et démonstrateur offline ; pas de BOOT PUBLIC vérifié.**

## Validation complémentaire : cas à automatiser

- Toute réponse PUBLIC exige une politique de publication explicite.
- Ne jamais inférer un clone Git depuis un symbole de tuple.
- Un nom requestable ne signifie pas un service disponible.
