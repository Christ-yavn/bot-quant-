# ÉTAT DE LA VÉRITÉ SCIENTIFIQUE ET EMPIRIQUE — QUANT BOT DERIV

**Date de mise à jour :** 25 Octobre 2026  
**Compte audité :** Deriv-Demo `32449166`  
**Répertoire des preuves reproductibles :** [`research/audit_2026-10-25/`](../research/audit_2026-10-25/)  
**Rapport d'audit intégral :** [`research/audit_2026-10-25/AUDIT_COMPLET_MODELES_ET_BOTS_DERIV.md`](../research/audit_2026-10-25/AUDIT_COMPLET_MODELES_ET_BOTS_DERIV.md)

---

## 🎯 Objectif de ce Document

Ce document constitue la **source de vérité scientifique unique (Ground Truth)** du dépôt `bot-quant-`. Tout agent IA ou chercheur quantitatif intervenant sur ce projet doit **impérativement lire ce document en premier** afin de ne jamais repartir d'hypothèses réfutées, de simulations biaisées par le spread historique, ou de formules contrefactuelles non exécutables.

Conformément à la politique d'archivage immuable du projet, **aucun fichier historique (v1 à v8.30, Tome I, Tome II, rapports intermédiaires) n'est supprimé**, mais toute affirmation antérieure contredite par les preuves empiriques ci-dessous est officiellement classée comme **RÉFUTÉE**.

---

## 📊 1. Registre des Hypothèses : Vérifiées, Réfutées et Non Testées

### A. Hypothèses VÉRIFIÉES Empiriquement ✅

| ID | Hypothèse / Fait | Statut | Données & Échantillon | Métriques Statistiques Vérifiées | Script de Preuve |
|---|---|---|---|---|---|
| **V1** | **Les indices Boom & Crash sont des martingales exactes** (dérive régulière compensée exactement par l'amplitude et la fréquence des sauts) | ✅ **VÉRIFIÉ** | 8 indices × 10 jours (**~6,8 M ticks** bid/ask) + Barres D1 jusqu'à **7,5 ans** | $\mathbb{E}[\Delta \text{Mid}]/\text{tick} \approx 0$ ($|t| < 2$ sur 7/8 indices ; sur 60 ticks, mouvement moyen $\le 0,058\text{ pt}$, soit **17× plus petit que le spread live**). Sur D1 (785 à 2 747 jours), tous les $\|t\| < 2$. | [`audit_boomcrash_micro.py`](../research/audit_2026-10-25/audit_boomcrash_micro.py), [`audit_longrun_drift.py`](../research/audit_2026-10-25/audit_longrun_drift.py) |
| **V2** | **Les sauts (spikes) Boom & Crash sont sans mémoire** (processus géométrique/Poisson pur, absence d'auto-excitation de Hawkes et de « maturation ») | ✅ **VÉRIFIÉ** | ~6,8 M ticks (8 indices Boom/Crash) | Coefficient de variation des inter-arrivées $\text{CV} \in [0,96 ; 1,03]$ (géométrique pur $= 1,00$). Autocorrélation $\text{ACF}(1) \in [-0,035 ; +0,033]$ ($\approx 0$). Fonction de hasard plate de 10 à 2 000+ ticks d'ancienneté. | [`audit_boomcrash_micro.py`](../research/audit_2026-10-25/audit_boomcrash_micro.py) |
| **V3** | **Le spread réel exécutable en live (`SymbolInfoTick`) sur Boom/Crash est 7× à 11× supérieur au spread historique (`CopyTicks`)** | ✅ **VÉRIFIÉ** | 648 positions live v8 (`magic=20261020`) + `real_live_spreads_mt5.json` | Crash 600 : `CopyTicks` $= 0,297\text{ pt}$ vs Live $= \mathbf{3,281\text{ pts}}$ ($\times 11$). Crash 900 : `CopyTicks` $= 0,193\text{ pt}$ vs Live $= \mathbf{1,362\text{ pts}}$ ($\times 7$). Boom 1000 : $\times 11$. Boom 600 : $\times 11$. Chaque fill live subit exactement ce demi-spread caché à l'entrée et à la sortie (écart-type nul). | [`forensic_v8_live.py`](../research/audit_2026-10-25/forensic_v8_live.py) |
| **V4** | **Le Théorème d'Arrêt Optionnel de Doob s'applique dans les deux sens (v7 ET v8)** : toute stratégie basée sur l'historique des prix a une espérance $\mathbb{E}[\text{PnL}] = -\text{Spread}_{\text{réel}} \times \text{Lot}$ | ✅ **VÉRIFIÉ** | 648 trades live v8 + ~280 000 trades simulés tick par tick | Live v8 (648 trades) : PnL total $= \mathbf{-311,20\text{ USD}}$ ($-0,480\text{ USD/trade}$), dont $-10,82\text{ USD}$ de mouvement mid ($z = -0,34$, pur hasard) et **$-300,28\text{ USD}$ ($96,5\%$) de coût de spread**. Prédiction de Doob ($-\text{spread}\times 0,20$) : Crash 600 $-0,656\$$ prédit vs $-0,742\$$ observé ; Crash 900 $-0,272\$$ prédit vs $-0,222\$$ observé. | [`forensic_v8_live.py`](../research/audit_2026-10-25/forensic_v8_live.py), [`sim_v830_ticks.py`](../research/audit_2026-10-25/sim_v830_ticks.py) |
| **V5** | **Volatility 25 (1s) et Volatility 75 (1s) sont des Mouvements Browniens Géométriques (GBM) à volatilité constante** | ✅ **VÉRIFIÉ** | **56 046 barres H1** par indice (06/2020 $\rightarrow$ 10/2026, soit 6,3 ans) | Volatilité annualisée réalisée : **24,9 %** (V25) et **75,2 %** (V75). Kurtosis H1 : $2,965$ (V25) et $2,987$ (V75) (gaussien $= 3,000$). Autocorrélation des rendements $|\text{ACF}| \le 0,011$. Autocorrélation des carrés des rendements $\text{ACF}(r^2) \le 0,007$. Corrélation $\text{corr}(\sigma_{20, t}, |r_{t+1}|) = +0,002$ (V25) et $+0,001$ (V75). | [`audit_vol_squeeze.py`](../research/audit_2026-10-25/audit_vol_squeeze.py) |
| **V6** | **Les swaps CFD sur tous les indices synthétiques Deriv sont fortement négatifs des deux côtés (Long et Short)** | ✅ **VÉRIFIÉ** | Spécifications des contrats MT5 sur 14 indices synthétiques | Coût de portage annuel : **$-15\%$ à $-72\%$ par an** en BUY comme en SELL, interdisant toute stratégie de détention à long terme. | [`audit_longrun_drift.py`](../research/audit_2026-10-25/audit_longrun_drift.py) |

---

### B. Hypothèses RÉFUTÉES Empiriquement ❌

| ID | Affirmation Antérieure (README / Tome II / Rapports v8) | Statut | Pourquoi c'est Réfuté (Preuve Formelle & Empirique) | Script de Preuve |
|---|---|---|---|---|
| **R1** | *« L'inversion convexe v8 génère +340,73 USD sur les 1 242 trades v7 avec 100 % de trajectoires positives au bootstrap ([+340,51 ; +340,52] USD) »* | ❌ **RÉFUTÉ** | **Artefact d'une formule algébrique inventée**, et non d'une simulation de marché : `src/python/analytics/counterfactual_v7_to_v8_sim.py` calculait `gain_v8 = abs(perte_v7) * 0.92` et `perte_v8 = gain_v7 * 1.15 + 0.05`. Le bootstrap rééchantillonnait ces nombres synthétiques. De plus, l'intervalle `[+340,51 ; +340,52]` était l'IC de la moyenne des moyennes bootstrap ($SE / \sqrt{10000}$). En exécution réelle live (648 trades), v8 a perdu **$-311,20\text{ USD}$**, et en simulation tick par tick réelle, v8.30 perd sur **8 indices sur 8**. | [`sim_v830_ticks.py`](../research/audit_2026-10-25/sim_v830_ticks.py), [`forensic_v8_live.py`](../research/audit_2026-10-25/forensic_v8_live.py) |
| **R2** | *« L'inversion convexe contourne le théorème de Doob grâce à une asymétrie positive ($b = 13,83$) »* | ❌ **RÉFUTÉ** | Sur une martingale, inverser la direction ou modifier le temps d'arrêt change la **forme de la distribution** (skewness positive au lieu de skewness négative), mais **jamais l'espérance mathématique**, qui reste $\mathbb{E}[\text{PnL}] = -\text{Spread}_{\text{réel}} \times \text{Lot} < 0$. | [`sim_v830_ticks.py`](../research/audit_2026-10-25/sim_v830_ticks.py) |
| **R3** | *« Le filtre IA ONNX `boom_crash_meta_brain.onnx` procure un lift de hasard $\times 2$ ($P \ge 15\%$) et bloque les mauvais trades »* | ❌ **RÉFUTÉ** | 1) La fonction de hasard empirique est plate (processus sans mémoire). 2) Dans `DerivBoomCrashHFT_v830_Ultimate.mq5` avant correction, `theta_eff = 0,90 * base_p0` et `spike_prob = MathMax(phys_spike_p0, ...)` rendaient le filtre mathématiquement incapable de bloquer le moindre trade. 3) `InpUseZeroCheatFeatures=true` envoyait 14 features différentes de celles de `onnx_model_metadata.json`. 4) Le modèle avait été entraîné pour prédire la survie de dérive v7, avec un PnL test négatif sur 9 indices sur 10 dans ses propres métadonnées (`-18 728` unités). | [`audit_boomcrash_micro.py`](../research/audit_2026-10-25/audit_boomcrash_micro.py), [`onnx_model_metadata.json`](../src/models/onnx_model_metadata.json) |
| **R4** | *« Volatility Squeeze Breakout v3 a un avantage statistique prouvé (100 % WR live sur V25, PF 1,64 à $H=4\text{h}$, WR 62,86 % à $H=3\text{h}$ sur V75) »* | ❌ **RÉFUTÉ** | 1) Le « 100 % WR live » reposait sur **3 trades** ($0,5^3 = 12,5\%$ par pur hasard ; cumul V25+V75 live $= -8\text{ USD}$ sur 8 trades). 2) Les chiffres PF 1,64 / WR 62,86 % provenaient d'un échantillon de **1 000 barres H1 (~40 signaux)**. 3) Sur l'historique complet de **56 046 barres H1 (6,3 ans)** : V25 à $H=4\text{h}$ donne 1 473 trades, WR $= 51,7\%$, gain net moyen $= +2,21\text{ bps}$ ($t = +1,58$, $p = 0,061$ vs hasard, non significatif après correction des tests multiples). V75 à $H=3\text{h}$ donne 1 562 trades, WR $= 48,8\%$, $t = +0,85$ (bruit pur). | [`audit_vol_squeeze.py`](../research/audit_2026-10-25/audit_vol_squeeze.py) |
| **R5** | *« Le classifieur `c2_vol_filter.onnx` filtre intelligemment les faux breakouts grâce à l'aire de Lévy »* | ❌ **RÉFUTÉ** | Avant la réparation du 25/10/2026, aucune des 7 features envoyées par l'EA ne correspondait aux 7 features d'entraînement de `train_volatility_colab.py`. Après alignement exact des 7 features et entraînement chronologique strict 60/20/20 sur 6,3 ans d'historique H1, le ROC-AUC hors échantillon (OOS) est $\approx 0,50$ (voir `src/models/c2_vol_filter_metadata.json`), confirmant qu'un GBM à volatilité constante n'a pas de mémoire exploitable. | [`audit_vol_squeeze.py`](../research/audit_2026-10-25/audit_vol_squeeze.py), [`train_volatility_colab.py`](../src/python/train_volatility_colab.py) |

---

### C. Pistes Évaluées par le Scanner de Juste Valeur WebSocket (Étape 4) 🔬

| ID | Hypothèse | Statut | Résultat Empirique Live (`wss://ws.derivws.com/websockets/v3?app_id=1089`) | Script de Preuve |
|---|---|---|---|---|
| **S1** | **Existence d'anomalies de tarification ($\text{EV} > 0$) sur les contrats à paiement fixé de Deriv** (Digits, Rise/Fall, Higher/Lower, Touch/No Touch, Ends Between/Outside, Accumulators, Multipliers) | ❌ **RÉFUTÉ (0 / 305 contrats à EV > 0)** | Sur **305 contrats** évalués à travers les **7 familles** (et **40 000 ticks live** vérifiés sur `wss://red.derivws.com/websockets/v3?app_id=1089`), **0 contrat sur 305** n'a une espérance positive : $\text{EV}_{\text{moy}} = \mathbf{-3,285\%}$ (de $-0,450\%$ sur Multipliers `1HZ25V` à $-9,090\%$ sur `DIGITMATCH`). Voir [`docs/RAPPORT_SCANNER_EV_CONTRATS_DERIV.md`](RAPPORT_SCANNER_EV_CONTRATS_DERIV.md) et [`deriv_contracts_ev_report.json`](../research/audit_2026-10-25/deriv_contracts_ev_report.json). | [`src/python/deriv_fair_value_scanner.py`](../src/python/deriv_fair_value_scanner.py) |

---

## 🛠️ 2. Registre des Réparations Techniques Appliquées (25/10/2026)

### 2.1 Verrouillage et Réparation de `src/mql5/DerivBoomCrashHFT_v830_Ultimate.mq5` (Défauts B1 à B9)

| Défaut | Problème Identifié lors de l'Audit | Correction Implémentée et Compilée (`0 error, 0 warning`) |
|---|---|---|
| **B1** | `tr.ev_gate_pass` calculé dans `ComputeSymbolEvGate()` mais jamais vérifié dans `OpenConvexSpikeProbe()`. | Ajout de `if(InpEnableStaticEvGate && !tr.ev_gate_pass) return false;` en tête de `OpenConvexSpikeProbe()` + activation par défaut de `InpEnforcePositivePayoffLock = true` (`InpMinExpectedPayoffUsd = 0.01`). Avec les spreads live réels, **10/10 indices sont verrouillés** (`REFUSE`), empêchant toute perte certaine. |
| **B2** | `theta_eff = 0,90 * base_p0` et `spike_prob = MathMax(phys_spike_p0, ...)` empêchaient tout blocage par le filtre IA. | Suppression du `MathMax(phys_spike_p0, ...)` lors de la fusion ONNX et passage de `InpThetaEffBaseMult` à `1.00` pour que toute baisse de probabilité prédite sous `theta_eff` bloque réellement la sonde. |
| **B3** | `InpUseZeroCheatFeatures=true` envoyait un vecteur de 14 features incompatible avec `boom_crash_meta_brain.onnx`. | Alignement strict du vecteur `x[0][0..13]` sur les 14 features exactes de `src/models/onnx_model_metadata.json` (`InpUseZeroCheatFeatures = false`). |
| **B4** | `boom_crash_meta_brain.onnx` prédit la survie sur 15 ticks ($P_{\text{surv},15}$), utilisée sans mise à l'échelle pour $M^*=60$ ticks. | Conversion mathématique exacte vers l'horizon $M^*$ : $P_{\text{spike}}(M^*) = 1 - (P_{\text{surv},15})^{M^* / 15}$. |
| **B5** | Stop temporel en secondes inopérant (`GetTickCount64()` comparé à `POSITION_TIME_MSC`). | Calcul de `elapsed_sec` à partir des horodatages epoch serveur (`live_pos_tick.time_msc - pos_time_msc` et repli `TimeCurrent() - POSITION_TIME`). |
| **B6** | Perte journalière calculée depuis `g_initial_equity` au lieu du début de journée UTC. | Initialisation et rollover quotidien UTC de `g_day_start_equity` dans `OnInit()` et `ScanAllBoomCrashSymbols()`. |
| **B7** | Sophisme du joueur codé en dur via `calm_maturity_boost`. | Suppression complète de `calm_maturity_boost` ($p_0 = 1 - \exp(-M^*/\tau)$). |
| **B8** | Plancher artificiel `0,20 * mean_sp` sur le gain de spike et oubli du spread dans la perte time-stop. | Suppression du plancher `0,20 * mean_sp` (`MathMax(0.0, mean_sp - 0.5*horizon*drift - real_spread_pts)`) et inclusion du coût du spread réel dans `loss_usd`. |
| **B9** | Ré-entrée « cluster Hawkes » activée par défaut alors que $\text{ACF}(1) \approx 0$. | Désactivation par défaut (`InpEnableHawkesClusterEntry = false`) et suppression de `hawkes_boost`. |

### 2.2 Réalignement et Ré-entraînement Chronologique de `c2_vol_filter.onnx` & `Deriv_VolSqueeze_Breakout_EA_v3.mq5`

1. **Alignement exact des 7 features** entre `src/python/train_volatility_colab.py` et `src/mql5/Deriv_VolSqueeze_Breakout_EA_v3.mq5` :
   - `[0] vol_ratio = current_std20 / (squeeze_threshold + 1e-8)`
   - `[1] impulse_z = abs(impulse_return_bps) / current_std20`
   - `[2] direction = +1.0 ou -1.0`
   - `[3] levy_area = CalcLevyArea(p_norm, 20)`
   - `[4] spread_to_atr = spread_pts / (atr_pts + 1e-8)` (suppression de la division parasite par `100.0` dans l'EA et lecture du vrai spread live via `SymbolInfoTick`)
   - `[5] skew20 = CalcSkewness(ret_sub, 20, r_mean, current_std20)`
   - `[6] kurt20 = CalcKurtosis(ret_sub, 20, r_mean, current_std20)`
2. **Protocole d'entraînement chronologique strict (60 % Train / 20 % Validation / 20 % Out-Of-Sample)** sur les **56 046 barres H1 (2020–2026)** avec étiquetage sur l'horizon réel ($H=4\text{h}$ pour V25, $H=3\text{h}$ pour V75) et déduction du vrai spread.
3. **Mise à jour du modèle `src/models/c2_vol_filter.onnx`** et de ses métadonnées d'évaluation OOS dans [`src/models/c2_vol_filter_metadata.json`](../src/models/c2_vol_filter_metadata.json), puis recompilation de `Deriv_VolSqueeze_Breakout_EA_v3.mq5` (`0 errors, 0 warnings`).
