# TUTO 06 — Intégration ALPHA et roadmap de 24 h

**Objectif :** exécuter le laboratoire de bout en bout, sans fausse release.

## 1. Contrats actifs

`BIOS` est un protocole d'amorçage en cours de formalisation.
`PRIME G` fixe quatre champs stricts par tuple.
`PRIME CGS` fixe les quatre layers OPX, DEV, USR, PUB.
`OpFrontier` décrit trois transitions d'artefacts.
`POEX` séquence les matrices 256×256 en 64 paquets 4×256.
Les nouveaux tuples décrivent la frontière README/USR/PUB.

## 2. Moteur et espaces

```text
ComplexGraphSync = interface et réponse publique contrôlée
ComplexGitSync = moteur GitTree, Memory, State et Integrity
PUBLIC = .omniscience
PRIVATE = .computo
INTERNAL = .cgitsync
```

Ne pas réimplémenter le moteur Git/Merkle dans le décorateur.
Ne pas transformer un suffixe de fichier en ordre de mutation.

## 3. Démonstration hors réseau

```bash
python3 scripts/contract_check.py inspect
python3 scripts/poex_4x256_simulator.py --output candidate.json
python3 scripts/contract_check.py candidate candidate.json
python3 -m unittest discover -s tests -v
```

L'ensemble produit un rapport local, pas une publication réelle.
Les sorties sont reproductibles avec Python 3.11+.

## 4. Roadmap P0

| Étape | Fenêtre | Livrable |
|---|---|---|
| BIOS | H0–H4 | Figer les tuples, version et identité |
| POEX | H4–H10 | Paquets, Merkle, émetteur OpFrontier |
| `@cgs` | H10–H16 | 4 sélecteurs System Layers |
| Sécurité | H16–H21 | Refus de fuite PRIVATE et preuve invalide |
| Release candidate | H21–H24 | PR, tests CI et décision de promotion |

Ce découpage est un objectif de développement, pas une promesse horaire.

## 5. État GitHub constaté

La PR #1 de `atCGS` est en brouillon et non fusionnée.
Le décorateur existant relaie plusieurs commandes `cgitsync` brutes.
La cible à quatre sélecteurs reste un travail d'implémentation.
La validation de ce paquet ne modifie aucun repository GitHub.

## 6. Exécuter l'ancien prototype en option

```bash
git clone --branch feature/alpha-pixi-opfrontier \
  https://github.com/flipoyo/atCGS.git
cd atCGS
pixi install
pixi run '@cgs' --help
pixi run test
```

Cette séquence nécessite Git, Pixi et un réseau accessible.
Elle est distincte du TP Python autonome de ce dossier.
Ne lancez pas de `release freeze` sur un projet réel sans contexte.

## 7. Critères de validation

Les fixtures doivent préserver tous les champs et leurs positions.
Les paquets POEX doivent être complets, ordonnés et reconstructibles.
Le candidat doit rester `NOT_PUBLISHED` sans checkpoint fiable.
La publication doit être indépendante des droits du GitTree interne.
L'intégration ne doit pas modifier les hash schema-1 historiques.
Le statut de la PR doit être observé, pas deviné.

## 8. Hors périmètre

Pas de passage forcé de `.cgitsync` à `.computo`.
Pas de service GX4G distant prétendu opérationnel.
Pas de signataire PoE fictif ni d'horodatage inventé.
Pas de migration de données sans preuve et rollback documentés.

## 9. Suivi

ComplexGitSync : https://github.com/flipoyo/ComplexGitSync/issues/193
atCGS : https://github.com/flipoyo/atCGS/issues/2
Prototype : https://github.com/flipoyo/atCGS/pull/1

Le résultat attendu est un démonstrateur contrôlé, pas un serveur PUBLIC.

## Validation complémentaire : cas à automatiser

- H0–H4 BIOS: vérifier fixture exacte.
- H0–H4 BIOS: vérifier sortie reproductible.
- H0–H4 BIOS: vérifier erreur non nulle si échec.
- H0–H4 BIOS: vérifier aucun accès non autorisé.
- H0–H4 BIOS: vérifier résultat de test consigné.
- H0–H4 BIOS: vérifier stade réalisé/simulé distingué.
- H0–H4 BIOS: vérifier possibilité de revue du PR.
- H0–H4 BIOS: vérifier dépendance moteur inchangée.
- H4–H10 POEX: vérifier fixture exacte.
- H4–H10 POEX: vérifier sortie reproductible.
- H4–H10 POEX: vérifier erreur non nulle si échec.
- H4–H10 POEX: vérifier aucun accès non autorisé.
- H4–H10 POEX: vérifier résultat de test consigné.
- H4–H10 POEX: vérifier stade réalisé/simulé distingué.
- H4–H10 POEX: vérifier possibilité de revue du PR.
- H4–H10 POEX: vérifier dépendance moteur inchangée.
- H10–H16 @cgs: vérifier fixture exacte.
- H10–H16 @cgs: vérifier sortie reproductible.
- H10–H16 @cgs: vérifier erreur non nulle si échec.
- H10–H16 @cgs: vérifier aucun accès non autorisé.
- H10–H16 @cgs: vérifier résultat de test consigné.
- H10–H16 @cgs: vérifier stade réalisé/simulé distingué.
- H10–H16 @cgs: vérifier possibilité de revue du PR.
- H10–H16 @cgs: vérifier dépendance moteur inchangée.
- H16–H21 Sécurité: vérifier fixture exacte.
- H16–H21 Sécurité: vérifier sortie reproductible.
- H16–H21 Sécurité: vérifier erreur non nulle si échec.
- H16–H21 Sécurité: vérifier aucun accès non autorisé.
- H16–H21 Sécurité: vérifier résultat de test consigné.
- H16–H21 Sécurité: vérifier stade réalisé/simulé distingué.
- H16–H21 Sécurité: vérifier possibilité de revue du PR.
- H16–H21 Sécurité: vérifier dépendance moteur inchangée.
- H21–H24 Release candidate: vérifier fixture exacte.
- H21–H24 Release candidate: vérifier sortie reproductible.
- H21–H24 Release candidate: vérifier erreur non nulle si échec.
- H21–H24 Release candidate: vérifier aucun accès non autorisé.
- H21–H24 Release candidate: vérifier résultat de test consigné.
- H21–H24 Release candidate: vérifier stade réalisé/simulé distingué.
- H21–H24 Release candidate: vérifier possibilité de revue du PR.
- H21–H24 Release candidate: vérifier dépendance moteur inchangée.
- Critère de clôture : pas de preuve d’existence inventée.
- Critère de clôture : compatibilité Merkle conservée.
- Critère de clôture : aucun chemin PRIVATE exposé.
- Critère de clôture : résolution de version.
- Critère de clôture : CI vérifiée.
- Critère de clôture : état de publication exact.
- Les résultats de tests sont attachés à la PR.
- Les commandes de production ne sont pas lancées par le laboratoire.
- Les ACL PRIVATE sont évaluées séparément.
- La release est bloquée sans publication attestée.
- Les hash schema-1 historiques restent inchangés.
- Les régressions interplateformes restent à contrôler.
