# SPÉCIFICATION TECHNIQUE OFFICIELLE — ULTIME V8.30
## Moteur Quantitative Convex Spike Harvester & Hawkes Self-Exciting Engine
### Synthèse Algorithmique : Argon Dynamic ONNX + Fable Static EV Gate + Antigravity Microstructure

**Fichier Source MQL5 :** [src/mql5/DerivBoomCrashHFT_v830_Ultimate.mq5](src/mql5/DerivBoomCrashHFT_v830_Ultimate.mq5)  
**Version :** 8.30 Ultimate  
**Compilation :** Certifiée MetaEditor 64 (0 erreur, 0 warning, 1 417 ms, binaire x64)  
**Statut Opérationnel :** Prêt en réserve dans le repository (Non déployé sur MT5 live conformément aux consignes)  
**Date :** 21 Octobre 2026  

---

## 1. Vue d'Ensemble & Objectif de Rentabilité Asymétrique

L'**Ultime V8.30** représente l'aboutissement de toutes les recherches forensiques menées sur les défaillances de la v7.00 (vente concave de convexité, -406.14 USD) et les 3 verrous de paralysie de la v8.20 (erreur ONNX 5800, seuil theta_eff impossible, payoff négatif bloquant).

Il fusionne en un seul moteur natif les meilleures composantes validées :
- **Fable 5 (Ashna AI)** : Porte EV statique à l'initialisation (spécifications de contrat MT5 réelles), curseur CopyTicks dédupliqué (zéro tick perdu), mesure du débit TPS live et reset journalier UTC.
- **Argon (Gemini 4)** : Introspection dynamique ONNX (support natif de [1,1], [1] et [1,2] via OnnxGetOutputCount), seuil relaxé non-bloquant (theta_eff = 0.90 * p0), double déclencheur (sonde 18t + réplique Hawkes 6t), trailing spike retrace à 8%.
- **Antigravity Live** : Normalisation stricte des prix broker (NormalizeDouble), marge de sécurité broker stop level (zéro rejet 10016), gestion d'urgence et exécution asynchrone sécurisée.

---

## 2. Les 8 Piliers de l'Architecture Ultime V8.30

### Pilier 1 : Rétro-Inversion Stochastique de Munger (INVERT)
- **Crash Indices** : Ordres SELL exécutés à tick.bid. La dérive lente monte contre la position, mais le saut plonge violemment dans le sens du gain.
- **Boom Indices** : Ordres BUY exécutés à tick.ask. La dérive lente descend contre la position, mais le saut explose à la hausse.
- **Borne de Perte Déterministe** : Clôture stricte sur le 60ème tick calme sans spike (M* = 60 ticks). Perte unitaire bornée :
  L_drift = M* * d + Spread ≈ -0.22 USD à -0.26 USD
- **Gain Convexe Asymétrique** : Les sauts de Poisson rapportent de +3.50$ à +15.00$ unitaire.
  Point mort : p_BE ≈ 5.35% << p0_Crash600 (9.97%).

### Pilier 2 : Cerveau ONNX à Introspection Dynamique
- Détection automatique de la topologie du tenseur de sortie via OnnxGetOutputCount().
- Supporte sans modification le format scalaire Colab [1, 1], [1] et le format classifieur [1, 2].
- En cas d'absence de fichier ou d'anomalie de graphe, bascule instantanément en mode Repli Analytique Hawkes + Poisson sans jamais faire planter la session MT5.

### Pilier 3 : Double Déclencheur d'Entrée Anti-Paralysie
1. **Sonde Périodique Standard (V8_CONVEX_PROBE)** : Déclenchée dès que le marché accumule 18 ticks calmes sans spike. Seuil de passage : theta_eff = 0.90 * p0_base (100% des sondes régulières autorisées).
2. **Ré-entrée Rapide sur Cluster de Hawkes (V8_CONVEX_HAWKES)** : Après un premier spike, si l'excitation rapide H_fast >= 0.85, le bot ré-entre après seulement 6 ticks calmes, ignorant le cooldown standard pour moissonner les répliques sismiques successives.

### Pilier 4 : Porte EV Statique à l'Initialisation (ComputeSymbolEvGate)
- Calculée une seule fois dans OnInit() pour chaque symbole avec les spécifications réelles de contrat MT5.
- Si l'espérance nette théorique E < +0.01 USD, le symbole est désactivé du scanner avec un log explicite.
- Zéro charge CPU tick-par-tick, zéro paralysie de boucle.

### Pilier 5 : Encaissement Convexe Intelligent par Trailing Retrace
- req.tp = 0.0 sur le broker (aucun niveau rigide qui briderait un méga-spike).
- Dès qu'un spike frappe et que le profit latent dépasse +2.00$ :
  - Fenêtre de grâce de 3 ticks pour observer l'inertie du saut.
  - Dès que le prix retrace de 8% par rapport au pic latent maximal, clôture immédiate au marché (V8_SPIKE_JACKPOT).

### Pilier 6 : Consommation Continue par Curseur CopyTicks Dédupliqué
- Curseur horodaté avec déduplication intra-milliseconde (last_time_msc et last_ms_consumed).
- Aucun tick n'est sauté ou comptabilisé deux fois lors des salves de ticks.
- Mesure glissante du débit TPS sur fenêtre de 30 secondes.

### Pilier 7 : Sécurité Multi-Couches du Capital
1. Couche 1 : Stop Temporel à 60 ticks (V8_TIME_STOP_M60) à -0.22$ / -0.26$.
2. Couche 2 : Coupe-Circuit Monétaire par Sonde (-0.35$ max).
3. Couche 3 : Stop-Loss Serveur Catastrophique (1.00$ max envoyé physiquement au broker).
4. Couche 4 : Coupe-Circuit Compte (Perte Jour >= 4.0% avec reset UTC ou Drawdown >= 10.0%).

### Pilier 8 : Conformité Microstructurelle & Zéro Rejet 10016
- Normalisation systématique de tous les prix d'ordres (NormalizeDouble(price, digits)).
- Marge de distance de sécurité calculée dynamiquement (stops_level + freeze_level + 5).

---

## 3. Protocole de Bascule Opérationnelle pour Demain

1. Le bot actuel v8.22 continue de tourner sans interruption sur MT5 live (compte 32449166).
2. Pour demain : dès validation, remplacement atomique de DerivBoomCrashHFT_v8.mq5 par DerivBoomCrashHFT_v830_Ultimate.mq5 et compilation vers MT5.
