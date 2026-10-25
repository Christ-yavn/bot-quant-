# REGISTRE OFFICIEL DES MODÈLES D'INTELLIGENCE ARTIFICIELLE & ONNX
## Traçabilité, Métriques Out-of-Sample et Appariement avec les EAs MetaTrader 5

Ce registre documente de manière exhaustive chaque modèle de réseau de neurones et d'apprentissage automatique (.onnx) déployé dans le projet. Il garantit la traçabilité intégrale entre chaque version de bot MQL5 et son cerveau d'inférence.

---

## 1. Table Récapitulative des Modèles IA

| Modèle ONNX | Taille | Architecture | Actif(s) Cible(s) | Bot MQL5 Associé | Tenseur Entrée | Tenseur Sortie | Métrique Clé Out-of-Sample | Statut |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`boom_crash_meta_brain.onnx`** | 50.9 Ko | DeepSurvival MLP (14 features) | Crash 600/900/1000<br>Boom 600/900 | [`DerivBoomCrashHFT_v830_Ultimate.mq5`](../src/mql5/DerivBoomCrashHFT_v830_Ultimate.mq5) | `[1, 14]` float | `[1]` label<br>`[1, 2]` probas | **Win Rate 88.91%**<br>Élimine 85% des faux départs | **ACTIF (Live MT5)** |
| **`c2_vol_filter.onnx`** | 20.2 Ko | Gradient Boosting Flat (No ZipMap) | Volatility 75 (1s)<br>Volatility 25 (1s) | [`Deriv_VolSqueeze_Breakout_EA_v3.mq5`](../src/mql5/Deriv_VolSqueeze_Breakout_EA_v3.mq5) | `[1, 7]` float | `[1]` label<br>`[1, 2]` probas | **Win Rate 62.86%**<br>Zéro erreur 5808 MT5 | **ACTIF (Live MT5)** |

---

## 2. Fiche Technique Détaillée : `boom_crash_meta_brain.onnx`

* **Rôle :** Filtre probabiliste haute fréquence post-spike (processus de Hawkes).
* **Entraînement :** Réalisé sur 10 000 000 de ticks réels MT5 condensés en 18 268 événements post-spike ([`boom_crash_10M_events.npz`](../src/python/colab_ai/boom_crash_10M_events.npz)).
* **Vecteur des 14 Caractéristiques :**
  1. `symbol_id` (Identifiant numérique de l'indice)
  2. `is_boom` (1 si Boom, 0 si Crash)
  3. `spike_amp_norm` (Amplitude normalisée de la pointe)
  4. `prev1_inter_spike_norm` (Temps écoulé depuis le dernier spike)
  5. `prev2_inter_spike_norm` (Temps écoulé 2 spikes avant)
  6. `prev3_inter_spike_norm` (Temps écoulé 3 spikes avant)
  7. `hawkes_intensity_fast` (Intensité de Hawkes fenêtre courte $\alpha=0.25$)
  8. `hawkes_intensity_med` (Intensité de Hawkes fenêtre moyenne $\alpha=0.10$)
  9. `hawkes_intensity_slow` (Intensité de Hawkes fenêtre longue $\alpha=0.03$)
  10. `cluster_count_60` (Nombre de spikes dans les 60 derniers ticks)
  11. `cluster_count_300` (Nombre de spikes dans les 300 derniers ticks)
  12. `post3_drift_velocity` (Vitesse de dérive sur les 3 ticks post-spike)
  13. `real_breakeven_ticks` (Nombre de ticks pour amortir le spread live)
  14. `cycle_cost_ratio` (Ratio coût du spread / espérance du spike)
* **Seuil de Décision Palier 1 :** $P \ge 0.9246$ (92.46%).
* **Emplacement Dépôt GitHub :** [`src/python/colab_ai/boom_crash_meta_brain.onnx`](../src/python/colab_ai/boom_crash_meta_brain.onnx)

---

## 3. Fiche Technique Détaillée : `c2_vol_filter.onnx`

* **Rôle :** Filtre de validation directionnelle après compression de volatilité ($Z \ge 1.50$ sur $\sigma_{20} \le q_{0.25}$).
* **Entraînement :** Réalisé sur chandeliers H1 réels extraits du compte live Deriv Demo.
* **Vecteur des 7 Caractéristiques :**
  1. `z_score` ($|r_{\text{bps}}| / \sigma_{20}$)
  2. `rolling_std` (Écart-type des rendements sur 20 barres)
  3. `ratio_compression` ($\sigma_{20} / q_{0.25}$)
  4. `wick_ratio` (Taille des mèches / range total de la barre)
  5. `tr_norm` (True Range normalisé en bps)
  6. `returns_bps` (Rendement de la dernière barre en bps)
  7. `spread_norm` (Spread normalisé par la volatilité)
* **Compatibilité MT5 :** Sérialisé via `skl2onnx` avec `options={'zipmap': False}`. Produit un tenseur plat sans dictionnaire.
* **Emplacement Dépôt GitHub :** [`src/models/c2_vol_filter.onnx`](../src/models/c2_vol_filter.onnx)

---

## 4. Politique de Gestion des Versions

* **Sur la machine de production / MT5 local :** Seules les versions actives les plus récentes sont maintenues dans `MQL5\Files` et `MQL5\Experts` pour éviter toute confusion opérateur et préserver l'espace mémoire.
* **Sur le dépôt GitHub :** Tous les modèles historiques, leurs fichiers de métadonnées JSON, leurs scripts d'entraînement et les datasets sources sont archivés de manière permanente et immuable dans l'historique Git.
