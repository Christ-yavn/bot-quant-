# Arsenal de Master Prompts Ultime — `quant-pod` v3.0 & `quant-pod-deriv` v3.0 (Mode Élevé L99)

Ces prompts ont été conçus par ingénierie de prompt institutionnelle pour pousser **`quant-pod` v3.0** et **`quant-pod-deriv` v3.0** au maximum absolu de leurs capacités (orchestration multi-agents à 2 niveaux façon *Team Mode Preview*, intégrité cryptographique `HashChainLedger`, inférence `SPA / StepM / MCS / N_eff`, régularisation `AST AlphaAgent`, ordonnanceur `UCB Bandit RD-Agent(Q)`, débat `Bull vs Bear`, forensique `NIST SP 800-22 / 800-90B / PIT`, et exécution événementielle anti-lookahead).

> **Conseil d'activation dans Antigravity** : Copiez-collez directement le prompt correspondant à votre mission et terminez-le par `/goal` (pour une campagne autonome longue qui ne s'arrête qu'une fois toutes les preuves générées) ou `/boost` (pour une revue contradictoire maximale).

---

## PROMPT MAÎTRE N°1 — Campagne Universelle `quant-pod` v3.0 (Tout Marché : Crypto CEX/DEX, Futures, Forex, Actions, Indices)

```markdown
Active immédiatement le skill `quant-pod` (v3.0 Institutionnel L99) en mode autonomie totale `/goal`.

### PARAMÈTRES DE LA MISSION
- **Marché / Univers cible** : [EX: BTCUSDT & ETHUSDT Perpétuels + Spot / EURUSD / NQ Futures / Univers Multi-Actifs]
- **Chemin des données** : [CHEMIN_DES_DONNÉES_OU_API]
- **Fréquence & Horizon exploré** : [EX: M15 / H1 / Ticks]
- **Frictions réelles LIVE obligatoires** : [EX: Spread live mesuré + Commission aller-retour + Funding/Swap + 1 barre de latence]
- **Capital & Risque max** : Capital = [EX: 10 000 $], Risque par trade ≤ [0.5%], Max Drawdown toléré ≤ [10%]
- **Budget maximal d'essais autorisé** : `K_max = 40`

### PROTOCOLE D'EXÉCUTION NON NÉGOCIABLE (ZÉRO MONOLOGUE SOLO)
1. **Initialisation Cryptographique Avant Toute Lecture (`research_integrity.py`)** :
   - Crée le dossier de campagne `quant_pod_runs/<nom_campagne>/` avec `TRUTH.md`, `cards/`, `code/`, `results/`, `holdout/`.
   - Sépare immédiatement les **20 % de données chronologiques les plus récentes**, scelle leur empreinte SHA-256 via `HashChainLedger` + `seal_holdout` et **interdis formellement** à tout agent de recherche/codage de les lire avant la Phase 6.
2. **Déploiement Obligatoire de la Flotte Multi-Agents à 2 Niveaux (`define_subagent` + `EnableSubagentTools: true` + `invoke_subagent`)** :
   - **Pilier 1 — `quant-deep-investigator`** (qui lance en parallèle `DGP & Chaos Scanner`, `Microstructure & Friction Auditor`, `Alpha Hypothesis Theorist`) :
     - Exécute `diagnose_market_dgp` (`quant_discovery_engine.py`), `pit_battery` et `surrogate_test` (`prng_forensics.py`), ainsi que le calcul exact de `break_even_probability` (`quant_inference_engine.py`).
     - Rédige 3 à 4 fiches d'hypothèses orthogonales `cards/H001.md`..`H004.md`, les passe au crible du débat contradictoire `bull_bear_hypothesis_debate` et de la porte d'originalité syntaxique `ast_originality_penalty` (AlphaAgent KDD'25), puis enregistre leur engagement salé via `commit_hypothesis`.
   - **Pilier 2 — `quant-deep-coder`** (qui lance en parallèle `Alpha Family Coder A`, `Alpha Family Coder B`, `Symbolic & Mutation Explorer`) :
     - Alloue dynamiquement le budget `K_max` via `UCBFamilyBandit` (RD-Agent(Q)).
     - Vérifie **chaque signal** avec `lookahead_truncation_test` et `warmup_stability_test` (`event_backtester.py`) — rejet immédiat à la moindre fuite du futur.
     - Exécute les backtests réalistes via `backtest_events` (latence ≥ 1, spread live bid/ask, priorité pessimiste SL avant TP intra-barre, exécution post-gap `SL_GAP`, courbe de sélection adverse `markouts`).
     - Enregistre **100 % des essais** (y compris chaque essai perdant et chaque mutation `O1..O6`) dans `HashChainLedger`.
   - **Pilier 3 — `quant-blind-validator`** (sous-agent totalement isolé ne recevant NI le récit NI les métriques du codeur, qui lance `Statistical Gates Prosecutor` et `Stress & Null-Model Breaker`) :
     - Calcule la longueur de bloc automatique de Politis-White-Patton (`optimal_block_length`), le nombre effectif d'essais indépendants `effective_number_of_trials` ($N_{\text{eff}}$), `deflated_sharpe_effective`, `haircut_sharpe`, `hansen_spa`, `romano_wolf_stepm`, `model_confidence_set`, `pbo_cscv`, `min_track_record_length`, le stress `Coûts × 2`, le `plateau_score` 2D, et la calibration sur `M ≥ 100` trajectoires du modèle nul (`null_models.py`).
   - **Pilier 4 — `quant-risk-architect`** (uniquement si un candidat survit à 100 % des portes `/boost`) :
     - Vérifie l'intégrité `ledger.verify()`, ouvre **une seule et unique fois** le Holdout 20 %, calibre le débruitage Marchenko-Pastur RMT, l'allocation HRP, le Fractional Kelly ¼ sous plafond CVaR 99 % EVT-GPD (`quant_scientific_arsenal.py`), et génère le module de Paper-Trading avec Kill-Switch statistique.

### CONTRAT D'HONNÊTETÉ ABSOLUE
Chaque métrique rapportée doit porter l'étiquette `[MESURÉ: script -> fichier]`. Si aucun edge ne survit aux frictions réelles et aux portes `SPA + DSR(N_eff) + Modèle Nul`, livre un rapport chirurgical **`NO-GO PROUVÉ`** documentant exactement pourquoi le capital est protégé. /goal
```

---

## PROMPT MAÎTRE N°2 — Campagne Spécialisée `quant-pod-deriv` v3.0 (94 Symboles / 11 Familles Deriv & Terminal MT5)

```markdown
Active immédiatement le skill `quant-pod-deriv` (et l'arsenal complet `quant-pod` v3.0) en mode `/goal`.

### CONTEXTE & SOURCES DE DONNÉES RÉELLES DU PROJET DERIV
- **Dossier Projet Deriv & Mémoire** : `C:\Users\CHRIST\Desktop\IA\ANTIGRAVITY\projets\general project   quant bot deriv\` (lis d'abord `AGENT.md` et `MEMOIRE_MAITRE_NOUVELLE_CONVERSATION.md` et respecte strictement les **7 Règles Inviolables** : archivage additif uniquement, ne touche jamais au terminal live ni aux bots actifs sans créer un fichier séparé, spread LIVE réel obligatoire vs `CopyTicks` ×7 à ×11, alignement strict si ONNX, H1 + `shift=1` anti-spam).
- **Moisson Officielle des 11 Familles (94 symboles)** : `C:\Users\CHRIST\Downloads\DERIV_ALL_11_FAMILIES_HARVEST\` (`HARVEST_MASTER_MANIFEST.csv` + archives `.zip` contenant D1/H4/H1/M15/M5/M1 + 500 000 ticks + `live_spread_bps` réel par symbole).
- **Familles / Symboles ciblés pour cette campagne** : [EX: Scan multi-familles sur `02_DRIFT_SWITCH_DSI`, `07_TREK_INDICES`, `08_RANGE_BREAK`, `10_VOLATILITY_INDICES` — ou audit ciblé d'un symbole précis]
- **Budget de recherche** : `K_max = 36` (enregistré dans `HashChainLedger`).

### ARCHITECTURE D'EXÉCUTION OBLIGATOIRE (CASCADE À 2 NIVEAUX)
Déploie obligatoirement via `define_subagent` (`EnableWriteTools: true`, `EnableSubagentTools: true`) et `invoke_subagent` les 4 Piliers (`quant-deep-investigator`, `quant-deep-coder`, `quant-blind-validator`, `quant-risk-architect`) et leurs sous-agents de Niveau 2 :

1. **Séquestration du Holdout 20 %** : Pour chaque symbole inspecté en mémoire depuis les `.zip`, scelle immédiatement les 20 % chronologiques les plus récents dans `HashChainLedger` avant toute statistique.
2. **Tri Théorique & Forensique CSPRNG (`prng_forensics.py` + `deriv_quant_engine.py` + `null_models.py`)** :
   - Sépare rigoureusement les **familles Martingales pures à loi connue** (`Step`, `Multi-Step`, `Skew Step`, `Volatility`, `Jump`, `Boom/Crash` net de dérive de compensation, `DEX`, `Range Break`) des **familles à persistance de régime par design** (`Drift Switch Index 10/20/30`, `Trek`) ou **contrats options/barrières mal tarifés** (Track 3 Fair-Value).
   - Exécute `nist_sp800_22_battery`, `sp800_90b_min_entropy`, `pit_battery`, `exploitability_verdict` (IC de Wilson corrigé de Bonferroni face au `live_spread_bps` réel du `HARVEST_MASTER_MANIFEST.csv`) et `martingale_drift_check`.
   - Interdiction absolue du sophisme du joueur (« spike attendu après N ticks ») ou de l'empilement de stops/trailing sur une martingale pure (Théorème d'Arrêt Optionnel de Doob : $\mathbb{E}[\text{PnL}] = -\text{Spread Live}$).
3. **Découverte Causale & Backtest Événementiel Réaliste (`quant_discovery_engine.py` + `event_backtester.py`)** :
   - Sur les seules familles/horizons qui franchissent `bull_bear_hypothesis_debate` (persistance mesurée > `live_spread_bps` + délai de détection), déploie les filtres d'état causaux (Filtre Bayésien 3 états de Wonham, CUSUM/SPRT, Weibull MLE, Yang-Zhang Squeeze, Kalman, Hawkes) ordonnancés par `UCBFamilyBandit` et régularisés par `ast_originality_penalty`.
   - Vérifie `lookahead_truncation_test` = `OK` et simule avec `backtest_events` au **vrai `live_spread_bps`** du manifeste + swaps + exécution exacte post-saut `SL_GAP`.
4. **Tribunal Aveugle `/boost` (`quant_inference_engine.py` + `quant_validation_engine.py` + `null_models.py`)** :
   - Le `quant-blind-validator` confronte tous les essais aux portes `DSR(N_eff) >= 0.95`, `Hansen SPA p <= 0.05`, `Romano-Wolf StepM`, `PBO <= 0.20`, `Coûts Live × 2 > 0`, et **$M = 100$ simulations du modèle nul exact** de la famille (`null_models.calibrate_family` + `make_null_generator`).
5. **Livrable** : Rapport complet en français étiqueté `[MESURÉ]`, mise à jour de `TRUTH.md`, vérification `ledger.verify()`, et code MQL5/Python séparé prêt pour le Paper-Trading uniquement si les portes et le Holdout unique sont validés. /goal
```

---

## PROMPT MAÎTRE N°3 — Recherche Quantitative DEX / AMM (Uniswap v3 / LVR) & Arbitrage CEX Perpétuels (`crypto_defi_engine.py`)

```markdown
Active immédiatement le skill `quant-pod` v3.0 en mode `/goal` pour une campagne **Crypto Microstructure DEX/AMM & CEX Perpetual Carry**.

### MISSION
1. Déploie la flotte hiérarchique à 2 niveaux (`quant-deep-investigator`, `quant-deep-coder`, `quant-blind-validator`, `quant-risk-architect`).
2. Scelle le Holdout 20 % via `HashChainLedger` (`research_integrity.py`).
3. Avec `scripts/crypto_defi_engine.py` et `scripts/quant_scientific_arsenal.py` :
   - **Volet DEX / LP Uniswap v3** : Mesure la volatilité réalisée causale, calcule le coût exact d'antisélection `lvr_rate` ($\sigma^2/8$ et version concentrée $[P_a, P_b]$), la probabilité d'arbitrage par bloc Poissonnien `arb_with_fees_ptrade`, et le ratio minimal Volume Organique / TVL `lp_breakeven_volume` requis pour battre le LVR net de gaz.
   - **Volet CEX Spot-Perp Carry** : Exécute `funding_carry_backtest` en intégrant les 4 jambes de frais/slippage, le risque de base $F_t - S_t$ et la distance exacte à la liquidation (`maint_margin`) lors des squeezes haussiers (Ackerer-Hugonnier-Jermann 2024).
   - **Volet Carnet d'Ordres / Exécution** : Calcule `kyle_lambda`, `amihud_illiquidity`, `compute_vpin_toxicity`, les cotes optimales `glft_quotes` (Guéant-Lehalle-Fernandez-Tapia), et les courbes de sélection adverse `markouts`.
4. Soumets toutes les configurations testées au `quant-blind-validator` (`hansen_spa`, `romano_wolf_stepm`, `deflated_sharpe_effective`, `min_track_record_length` tenant compte du skew négatif, et `Coûts × 2`). /goal
```

---

## PROMPT MAÎTRE N°4 — Audit Adversarial Destructif `/boost` d'un Bot ou d'une Stratégie Existante

```markdown
Active `quant-pod` v3.0 en mode **Audit Forensique & Destruction Scientifique `/boost`** sur la stratégie suivante :
- **Fichier / Code cible** : [CHEMIN_DU_BOT_MQL5_OU_PYTHON]
- **Marché & Timeframe** : [SYMBOLE_ET_TF]

Exécute sans aucune complaisance les 6 contrôles d'audit suivants via sous-agents séparés :
1. **Sonde Anti-Lookahead & Warmup (`event_backtester.py`)** : `lookahead_truncation_test` + `warmup_stability_test` + audit ligne par ligne des index temporels (`shift=0` vs `shift=1`, recalibration in-sample, fuite ONNX/ML).
2. **Audit de Physique DGP & Plafond de Doob (`quant_discovery_engine.py` + `prng_forensics.py`)** : Vérifie si le marché sous-jacent est une martingale sur l'horizon tradé et si la stratégie repose sur un sophisme du joueur ou un masquage de risque par asymétrie SL/TP (gros risque rare pour petits gains fréquents).
3. **Audit Microstructure & Frictions Réelles** : Recalcule l'espérance nette avec le **vrai spread live**, le slippage post-gap (`SL_GAP`), les swaps et `Coûts × 2`.
4. **Audit Statistique Multi-Essais (`quant_inference_engine.py`)** : Calcule `sharpe_ci`, `min_track_record_length` (ajusté du skew $\gamma_3$ et kurtosis $\gamma_4$ réels), `deflated_sharpe_effective`, `hansen_spa` et `pbo_cscv`.
5. **Calibration sur Modèle Nul Exact (`null_models.py`)** : Fais tourner exactement le même bot sur `M = 100` trajectoires synthétiques sans edge (`make_null_generator`) pour mesurer la p-value empirique $p_{\text{null}}$.
6. **Verdict binaire `GO PAPER` / `NO-GO IMMÉDIAT`** avec preuves `[MESURÉ]` et plan chirurgical de remédiation (ou d'abandon définitif). /boost
```
