---
name: drone-from-scratch
description: Concevoir un multirotor à partir de rien - références, dimensionnement au premier ordre, catalogue de pièces sourcées, pièces sur mesure, assemblage compilé, itérations sur l'épreuve. Charger pour le produit lift_challenge.
version: 2.0.0
category: engineering
---

# Concevoir un drone de zéro

Tu construis tout : références, calculs, catalogue, pièces, squelette. Enchaînement d'un projet :

1. **Références** : drones lourds réels (masses, diamètres, puissances, autonomie), avec URL dans le cahier.
2. **Dimensionnement** : un script Python dans `workspace/scripts/` qui, pour une configuration, calcule la masse par famille de pièces, le rayon minimal des rotors (hélices dégagées ou décalées), la flexion des bras, la poussée max et la marge de 1,6, la puissance chargée et à vide, l'énergie de mission et la marge de batterie. Garde-le : il sert à chaque cycle.
3. **Catalogue** (compétence component-research) : moteurs, hélices, batteries, variateurs, tubes, avionique, câblage, train, chacun avec fiche produit précise via `catalog_add`.
4. **Pièces sur mesure** (compétence part-design) : moyeu, supports moteur, manchons de bras, train si tu le fabriques ; choix du matériau et du procédé justifié par le calcul.
5. **Assemblage** (compétence assembly-design) : `assembly.json`, `assembly_compile`, inspection de l'image.
6. **Épreuve** (compétence lift-exam) : charge par paliers, lecture de la télémétrie, diagnostic.
7. **Itérer** : changer ce que le diagnostic désigne. Une nouvelle idée de squelette vaut plus qu'un réglage fin.

Conseils : nomme chaque version (`a1_quad`, `a2_hexa_stagger`…) sans réécrire une version déjà testée ; progresse par petits pas (d'abord un vol réussi avec une charge faible, puis augmenter) ; ne cale jamais une valeur sur un plafond de l'épreuve.
