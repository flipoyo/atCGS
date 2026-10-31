# TUTO 04 — POEX : matrice 256×256 et paquets 4×256

**Objectif :** générer et vérifier un engagement binaire ordonné.

## 1. Matrice de départ

```text
M = 256 × 256 bits
M = 65 536 bits = 8 192 octets
1 ligne = 256 bits = 32 octets
```

Le binaire est interprété par lignes et par bits de poids fort en premier.
Un fichier `.bit` du laboratoire est un fichier de 8 192 octets bruts.
Il n'est ni un PNG ni une clé publique attestée.

## 2. Séquencement POEX

```text
POEX[k] = (W[4k], W[4k+1], W[4k+2], W[4k+3])
0 <= k < 64
1 paquet = 4 × 256 bits = 128 octets
64 × 128 = 8 192 octets
```

La recomposition dans l'ordre des indices donne exactement la matrice.
Un paquet tronqué, supplémentaire ou échangé doit être refusé.

## 3. Invariant `.poe`

Un rapport est émis après chaque quartet de quatre bits.
Un paquet contient 256 quartets ; la matrice en contient 16 384.
Le compteur enregistre le nombre de zéros rencontrés.
La référence logique au dernier quartet est conservée dans la simulation.
Le pointeur mémoire Rust `.poe` n'est pas implémenté dans ce TP.

## 4. Lancer le démonstrateur

```bash
python3 scripts/poex_4x256_simulator.py --output candidate.json
```

Le mode sans `--input` produit une matrice synthétique déterministe.
La sortie contient une racine candidate mais aucune signature d'existence.

## 5. Tester avec une matrice réelle du laboratoire

```bash
python3 scripts/poex_4x256_simulator.py \
  --input fixtures/demo_256x256.bit --output from_bit.json
```

Les racines des deux commandes doivent coïncider.
Le fichier `.bit` est synthétique, non issu d'un GitTree réel.

## 6. Vérification des preuves

```bash
python3 -m unittest discover -s tests -v
```

Les tests contrôlent la recomposition des 64 paquets.
Les 64 preuves d'inclusion Merkle sont vérifiées.
Une inversion de bit est détectée ; la permutation d'indice aussi.
L'index figure dans l'engagement d'une feuille de paquet.

## 7. Interprétation cryptographique

Une racine Merkle engage la suite choisie de paquets.
Elle n'établit ni l'identité de leur auteur ni leur date d'existence.
Une preuve d'inclusion n'est pas une autorisation de publication.
Le domaine SHA-256 POEX est distinct de celui du `.gts` GitTree.

## 8. Sortie attendue

```text
matrix_bits: 65536
packets: 64
bits_per_packet: 1024
nibble_reports: 16384
published: false
```

Le tutoriel 05 place l'engagement à la frontière USR/PUB.

## Validation complémentaire : cas à automatiser

- Paquet 0: index encodé et authentifié dans la feuille.
- Paquet 0: taille de 128 octets requise.
- Paquet 0: 256 rapports quartets attendus.
- Paquet 0: premier rang = 0.
- Paquet 0: dernier rang = 3.
- Paquet 1: index encodé et authentifié dans la feuille.
- Paquet 1: taille de 128 octets requise.
- Paquet 1: 256 rapports quartets attendus.
- Paquet 1: premier rang = 4.
- Paquet 1: dernier rang = 7.
- Paquet 2: index encodé et authentifié dans la feuille.
- Paquet 2: taille de 128 octets requise.
- Paquet 2: 256 rapports quartets attendus.
- Paquet 2: premier rang = 8.
- Paquet 2: dernier rang = 11.
- Paquet 7: index encodé et authentifié dans la feuille.
- Paquet 7: taille de 128 octets requise.
- Paquet 7: 256 rapports quartets attendus.
- Paquet 7: premier rang = 28.
- Paquet 7: dernier rang = 31.
- Paquet 15: index encodé et authentifié dans la feuille.
- Paquet 15: taille de 128 octets requise.
- Paquet 15: 256 rapports quartets attendus.
- Paquet 15: premier rang = 60.
- Paquet 15: dernier rang = 63.
- Paquet 31: index encodé et authentifié dans la feuille.
- Paquet 31: taille de 128 octets requise.
- Paquet 31: 256 rapports quartets attendus.
- Paquet 31: premier rang = 124.
- Paquet 31: dernier rang = 127.
- Paquet 32: index encodé et authentifié dans la feuille.
- Paquet 32: taille de 128 octets requise.
- Paquet 32: 256 rapports quartets attendus.
- Paquet 32: premier rang = 128.
- Paquet 32: dernier rang = 131.
- Paquet 47: index encodé et authentifié dans la feuille.
- Paquet 47: taille de 128 octets requise.
- Paquet 47: 256 rapports quartets attendus.
- Paquet 47: premier rang = 188.
- Paquet 47: dernier rang = 191.
- Paquet 62: index encodé et authentifié dans la feuille.
- Paquet 62: taille de 128 octets requise.
- Paquet 62: 256 rapports quartets attendus.
- Paquet 62: premier rang = 248.
- Paquet 62: dernier rang = 251.
- Paquet 63: index encodé et authentifié dans la feuille.
- Paquet 63: taille de 128 octets requise.
- Paquet 63: 256 rapports quartets attendus.
- Paquet 63: premier rang = 252.
- Paquet 63: dernier rang = 255.
- Cas all-zero: calculer ou refuser le résultat attendu.
- Cas all-one: calculer ou refuser le résultat attendu.
- Cas single-bit: calculer ou refuser le résultat attendu.
- Cas swapped-index: calculer ou refuser le résultat attendu.
- Cas truncated: calculer ou refuser le résultat attendu.
- Cas extra-packet: calculer ou refuser le résultat attendu.
- Cas changed-root: calculer ou refuser le résultat attendu.
- Cas wrong-branch: calculer ou refuser le résultat attendu.
- Cas wrong-digest: calculer ou refuser le résultat attendu.
- Le fichier `.bit` comprend exactement 8 192 octets.
- Le paquet 0 commence à la ligne 0.
- Le paquet 63 termine à la ligne 255.
- Chaque feuille engage l’indice du paquet.
