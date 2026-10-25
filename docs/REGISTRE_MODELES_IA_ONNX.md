# REGISTRE OFFICIEL DES MODÈLES D'INTELLIGENCE ARTIFICIELLE & ONNX
## Traçabilité, Métriques Out-of-Sample Réelles et Appariement Exact avec les EAs MetaTrader 5

> [!IMPORTANT]
> **Mise à jour post-audit du 25/10/2026 ([`docs/ETAT_DE_LA_VERITE.md`](ETAT_DE_LA_VERITE.md)) :**
> Les deux modèles ONNX et leurs EAs MQL5 associés ont été intégralement ré-alignés afin que chaque position du tenseur d'entrée envoyé par MetaTrader 5 corresponde **exactement** à la feature entraînée en Python, et évalués selon un protocole chronologique strict hors échantillon (60 % Train / 20 % Validation / 20 % Out-Of-Sample).

---

## 1. Table Récapitulative des Modèles IA (État Vérifié au 25/10/2026)

| Modèle ONNX | Taille | Architecture | Actif(s) Cible(s) | Bot MQL5 Associé | Tenseur Entrée | Tenseur Sortie | Bilan Hors Échantillon (OOS) Vérifié | Statut |
| :--- | :---: | :---: | :--- | :--- | :---: | :---: | :---: | :---: |
| **`boom_crash_meta_brain.onnx`** | 50.9 Ko | DeepSurvival MLP (14 features) | Boom & Crash (10 indices) | [`DerivBoomCrashHFT_v830_Ultimate.mq5`](../src/mql5/DerivBoomCrashHFT_v830_Ultimate.mq5) | `[1, 14]` float | `[1]` label<br>`[1, 2]` probas | Prédit $P(\text{Survie sur } \text{be\_ticks} + 15\text{t})$. PnL test dans `onnx_model_metadata.json` négatif sur 9/10 indices ($-18\,728$ unités) car les sauts sont sans mémoire ($\text{CV}\approx 1$). Converti en $1 - P_{\text{surv}}^{M^*/(\text{be\_ticks}+15)}$ dans v8.30. | **ALIGNÉ (Porte EV Active)** |
| **`c2_vol_filter.onnx`** | 12.7 Ko | Gradient Boosting Flat (`zipmap=False`) | Volatility 25 (1s)<br>Volatility 75 (1s) | [`Deriv_VolSqueeze_Breakout_EA_v3.mq5`](../src/mql5/Deriv_VolSqueeze_Breakout_EA_v3.mq5) | `[1, 7]` float | `[1]` label<br>`[1, 2]` probas | Ré-entraîné sur 56 048 barres H1 (split 60/20/20 sans fuite du spread futur) avec les 7 features exactes de l'EA. Val ROC-AUC $= 0,573$ (V25) / $0,542$ (V75) ; OOS ROC-AUC $= 0,467$ (V25, Net $+5,47\text{ bps}$, $t=+1,23$) / $0,521$ (V75). Zéro erreur 5808 MT5. | **ALIGNÉ & RE-ENTRAÎNÉ** |

---

## 2. Fiche Technique Détaillée : `boom_crash_meta_brain.onnx`

* **Rôle initial :** Prédire la probabilité de survie de la dérive sur $H_{\text{train}} = \text{be\_ticks} + 15$ ticks (`out_proba[0][1]`), convertie dans v8.30 en probabilité de saut sur $M^*$ ticks via $P_{\text{spike}}(M^*) = 1 - P_{\text{surv}, H_{\text{train}}}^{M^* / (\text{be\_ticks} + 15)}$.
* **Correction B3 & B2 (25/10/2026) :** Suppression du mode `InpUseZeroCheatFeatures=true` qui envoyait un vecteur incompatible, et suppression du `MathMax(phys_spike_p0, ...)` qui empêchait le modèle de réduire la probabilité sous le seuil `theta_eff`.
* **Vecteur Exact des 14 Caractéristiques (`src/models/onnx_model_metadata.json`) :**
  1. `symbol_id` (`0` à `9` selon l'indice Boom/Crash)
  2. `is_boom` (`1.0` si Boom, `0.0` si Crash)
  3. `spike_amp_norm` (Amplitude du dernier spike normalisée par l'amplitude moyenne)
  4. `prev1_inter_spike_norm` ($\tau_1 / \bar{\tau}$)
  5. `prev2_inter_spike_norm` ($\tau_2 / \bar{\tau}$)
  6. `prev3_inter_spike_norm` ($\tau_3 / \bar{\tau}$)
  7. `hawkes_intensity_fast` ($\sum (A_i/\bar{A}) e^{-0.05 \Delta t_i}$)
  8. `hawkes_intensity_med` ($\sum (A_i/\bar{A}) e^{-0.015 \Delta t_i}$)
  9. `hawkes_intensity_slow` ($\sum (A_i/\bar{A}) e^{-0.003 \Delta t_i}$)
  10. `cluster_count_60` ($\max(1, c_{60})$)
  11. `cluster_count_300` ($\max(1, c_{300})$)
  12. `post3_drift_velocity` (Vitesse de dérive sur 3 ticks normalisée)
  13. `real_breakeven_ticks` ($\text{Spread}_{\text{réel}} / d$)
  14. `cycle_cost_ratio` ($\text{breakeven\_ticks} / \bar{\tau}$)
* **Vérité Empirique :** Comme vérifié dans [`audit_boomcrash_micro.py`](../research/audit_2026-10-25/audit_boomcrash_micro.py), les intervalles entre sauts suivent une loi géométrique sans mémoire ($\text{CV} \approx 1,0$, $\text{ACF}(1) \approx 0$). Aucune combinaison de ces 14 features passées ne peut prédire le prochain saut. C'est pourquoi la **Porte EV Statique et Dynamique (Fix B1)** est verrouillée en amont.

---

## 3. Fiche Technique Détaillée : `c2_vol_filter.onnx`

* **Rôle :** Filtre de probabilité sur les signaux de breakout impulsif après compression de volatilité ($Z \ge 1,50$ et $\sigma_{20} \le q_{0,25}$).
* **Correction du Désalignement des 7 Features (25/10/2026) :** Avant l'audit, `train_volatility_colab.py` entraînait le modèle sur `[z_score, rolling_std, ratio_compression, wick_ratio, tr_norm, returns_bps, spread_norm]` tandis que l'EA MQL5 envoyait `[vol_ratio, impulse_z, direction, levy_area, spread_atr, skew20, kurt20]`. Désormais, Python et MQL5 partagent **exactement** le même vecteur de 7 features :
  1. `vol_ratio` : $\sigma_{20} / (q_{0,25} + 10^{-8})$
  2. `impulse_z` : $|r_{1\text{h, bps}}| / \sigma_{20}$
  3. `direction` : $+1,0$ (BUY) ou $-1,0$ (SELL)
  4. `levy_area` : Aire de Lévy sur la trajectoire normalisée des 20 dernières clôtures H1
  5. `spread_to_atr` : Ratio du spread exact sur l'ATR(20) H1 ($\text{spread\_pts} / \text{atr\_pts}$)
  6. `skew20` : Skewness des rendements H1 sur 20 barres
  7. `kurt20` : Kurtosis des rendements H1 sur 20 barres
* **Résultats Chronologiques 60/20/20 (56 048 barres H1, 2020–2026) :** Documentés dans [`src/models/c2_vol_filter_metadata.json`](../src/models/c2_vol_filter_metadata.json). Sur V25 ($H=4\text{h}$), le modèle obtient un ROC-AUC de validation de $0,5733$ et un PnL OOS filtré de $+5,47\text{ bps/trade}$ ($t = +1,23$, WR $55,6\%$, PF $1,31$, ROC-AUC OOS $= 0,4666$), demeurant sous le seuil de significativité $t \ge 1,96$ d'un mouvement brownien géométrique à volatilité constante.
* **Compatibilité MT5 :** Sérialisé via `skl2onnx` avec `options={'zipmap': False}` (`[1, 7]` $\rightarrow$ `[1]`, `[1, 2]`).
* **Emplacement Dépôt GitHub :** [`src/models/c2_vol_filter.onnx`](../src/models/c2_vol_filter.onnx)
