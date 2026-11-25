---
name: quant-pod-deriv
description: Specialized Quantitative Research Skill v3.0 for Synthetic Stochastic Processes & Jump-Diffusion Markets (94 symbols / 11 stochastic families) — Doob's Optional Stopping Theorem enforcement, NIST SP 800-22/90B/PIT CSPRNG forensics, 10 exact martingale null models, Wonham 3-state continuous-time Bayesian filtering, and 2-level multi-agent validation.
---

# Quant Pod Deriv v3.0 — Synthetic Jump-Diffusion & Regime-Switching Specialization

## English Overview

This skill extends [`../quant-pod/SKILL.md`](../quant-pod/SKILL.md) for **synthetic stochastic processes, jump-diffusion indices, and barrier/accumulator contracts** (covering 11 mathematical families across 94 instruments). It inherits the full 2-level multi-agent architecture and all 10 pure-Python scientific engines of `quant-pod`, while adding strict domain laws for known-distribution stochastic processes:

1. **Doob's Optional Stopping Theorem Enforcement**: On pure memoryless CSPRNG martingales (constant-volatility diffusions, step random walks, or compensated Poisson jump processes), no entry rule, stop-loss, take-profit, or position-sizing scheme based solely on past price history can turn a negative net-of-spread expectation positive ($\mathbb{E}[\text{PnL}] = -\text{Live Spread} - \text{Financing}$).
2. **Three Valid Sources of Mathematical Edge**:
   - **(Class A — Generator Anomaly)**: A statistically significant departure from IID uniformity confirmed by `prng_forensics.py` (`nist_sp800_22_battery`, `sp800_90b_min_entropy`, `pit_battery`) that exceeds the transaction cost hurdle in `exploitability_verdict`.
   - **(Class R — Regime Persistence by Design)**: Processes engineered with latent regime persistence (such as continuous-time Markov regime-switching *Drift Switch Indices* or *Trek* processes), provided that the drift captured after Bayesian detection delay (`wonham_bayesian_regime_filter_dsi` or Page-Lorden CUSUM in `deriv_quant_engine.py`) strictly exceeds live spreads and beats $M \ge 100$ exact null simulations in `null_models.py`.
   - **(Class O — Nonlinear Contract Mispricing)**: Fair-value pricing discrepancies on barrier options or accumulators evaluated via exact survival probabilities (`accumulator_survival_probability`, `audit_range_break_barriers`).
3. **Mandatory Post-Jump Stop Slippage (`SL_GAP`)**: On Poisson jump processes (*Crash/Boom*), stops placed inside a jump are never filled at the requested stop price; `event_backtester.py` forces execution at the post-spike price (`SL_GAP`).

---

## Spécification Complète en Français

Ce skill est l'extension spécialisée **Processus Stochastiques Synthétiques & Options/CFD** de [`../quant-pod/SKILL.md`](../quant-pod/SKILL.md). Il hérite de **100 % des lois, de l'orchestration multi-agents à 2 niveaux (`define_subagent` + `EnableSubagentTools: true` + `invoke_subagent`) et des 10 moteurs Python** de `quant-pod`.

---

## 1. CONFIGURATION DES DONNÉES & MANIFESTE DE MICROSTRUCTURE

1. **Moisson Historique & Microstructure (94 Symboles / 11 Familles)** :
   - Répertoire configurable via la variable d'environnement `DERIV_HARVEST_DIR` (ou dossier de données local `./data/deriv_harvest/`).
   - Manifeste maître : `HARVEST_MASTER_MANIFEST.csv` & `.parquet` (contient `symbol`, `family`, `digits`, `point`, `tick_size`, `tick_value`, `contract_size`, `live_tick_spread_mean_pts`, `live_tick_spread_p95_pts`, **`live_spread_bps`**, `swap_long`, `swap_short`, et compteurs de barres/ticks).
   - Archives par famille (`01_CRASH_BOOM` à `11_HYBRID_TACTICAL`) : barres `D1, H4, H1, M15, M5, M1` + échantillons de `500,000` ticks (`*_TICKS_SAMPLE.parquet`) lisibles directement en mémoire via `zipfile` + `pyarrow`/`pandas`.

---

## 2. LES 7 LOIS INVIOLABLES SPÉCIFIQUES AUX PROCESSUS SYNTHÉTIQUES

1. **Loi du Spread Live vs Spread Historique ($\times 7$ à $\times 11$)** :
   Les spreads historiques sous-estiment souvent les spreads réellement exécutés sur certains indices à sauts. **Toujours** injecter le `live_spread_bps` / `live_tick_spread_p95_pts` mesuré dans `HARVEST_MASTER_MANIFEST.csv` (et tester `Coûts Live × 2` en Phase 5).
2. **Loi d'Archivage Additif Non-Destructif** :
   Tout nouveau candidat est écrit dans un dossier de campagne isolé (`quant_pod_runs/<campagne>/`) avec journalisation complète dans `HashChainLedger`.
3. **Théorème d'Arrêt Optionnel de Doob & Classification des 11 Familles** :
   - **Classe M — Martingales CSPRNG pures à loi stationnaire connue** (`04_CLASSIC_STEP`, `05_MULTI_STEP`, `06_SKEW_STEP`, `10_VOLATILITY_INDICES`, `09_JUMP_INDICES`, `01_CRASH_BOOM` net de la dérive compensatrice, `03_DEX_INDICES`, `08_RANGE_BREAK`) :
     - Sur les contrats linéaires au comptant, si aucune anomalie forensique CSPRNG ne franchit `exploitability_verdict` ($\text{CI}_{\text{low}}(p) > p^*$) dans `prng_forensics.py`, toute combinaison de stops, trailing stops, filtres techniques ou martingales de lots a $\mathbb{E}[\text{PnL}] = -\text{Spread Live} - \text{Swaps}$.
     - Interdiction absolue du **sophisme du joueur** sur Boom/Crash (« pas de spike depuis $N$ ticks $\implies$ probabilité accrue » : processus de Poisson sans mémoire).
     - Exécution obligatoire du Stop-Loss au prix **post-spike (`SL_GAP`)** dans `event_backtester.backtest_events`.
   - **Classe R — Processus à Changement de Régime / Persistance par Design** (`02_DRIFT_SWITCH_DSI` : DSI 10/20/30, `07_TREK_INDICES`, et sous-familles tactiques `11_HYBRID_TACTICAL`) :
     - Possèdent une dérive latente persistante par construction, mais assortie d'un **spread live plus large** et d'un délai de détection Bayésien.
     - L'edge n'existe que si : $\mathbb{E}[\text{Dérive captée après détection (Wonham/CUSUM/Weibull)}] > \text{Spread Live} + \text{Swaps}$, prouvé face au simulateur nul `sim_dsi` / `sim_trek` (`null_models.py`) et `hansen_spa`.
   - **Classe O — Arbitrage de Juste Valeur sur Contrats Non-Linéaires (Options Barrières, Touch/No-Touch, Digits, Accumulators)** :
     - Compare la probabilité exacte de survie/franchissement sous le DGP calibré (`accumulator_survival_probability`, `audit_range_break_barriers`) au payout offert (`break_even_probability`).
4. **Loi Anti-Surajustement ML / ONNX** :
   Interdiction de déployer un filtre ML dont l'AUC hors-échantillon purgée est $\le 0.52$ ou qui échoue à `lookahead_truncation_test`. Par défaut, préférer des filtres d'état causaux parcimonieux ($\le 3$ paramètres : Wonham 3-états, Yang-Zhang Squeeze, Kalman 1D) validés par `ast_originality_penalty`.
5. **Loi d'Alignement Vectoriel & d'Échelle `[0, 1]`** : alignement strict feature-par-feature entre l'entraînement et l'inférence.
6. **Loi d'Exécution Causale (`shift=1`)** : toute décision sur bougie se prend sur bougie **clôturée** (`shift=1`, soit `latency_bars=1` à l'ouverture suivante dans `backtest_events`) pour éliminer le *repainting* intra-barre.
7. **Loi du Modèle Nul Spécifique par Famille (`null_models.py`)** :
   Aucun candidat ne peut être déclaré `GO PAPER` sans avoir battu ($p_{\text{null}} \le 0.05$) le maximum d'une recherche identique menée sur $M \ge 100$ trajectoires synthétiques générées par le modèle nul exact de sa famille (`calibrate_family` + `make_null_generator`).

---

## 3. WORKFLOW D'EXÉCUTION `quant-pod-deriv` EN 5 ÉTAPES

1. **Initialisation & Séquestration Holdout 20 %** :
   Lire le manifeste de données, sceller les 20 % les plus récents de chaque série dans `HashChainLedger` (`../quant-pod/scripts/research_integrity.py`).
2. **Déploiement de la Flotte Multi-Agents à 2 Niveaux (`define_subagent` + `invoke_subagent`)** :
   Conformément à la Section `0.bis` de [`../quant-pod/SKILL.md`](../quant-pod/SKILL.md) (`quant-deep-investigator`, `quant-deep-coder`, `quant-blind-validator`, `quant-risk-architect`).
3. **Forensique CSPRNG, Diagnostic DGP & Planification Stratégique Algorithmique** :
   Exécuter `nist_sp800_22_battery`, `sp800_90b_min_entropy`, `pit_battery`, `exploitability_verdict` (`../quant-pod/scripts/prng_forensics.py`), `diagnose_market_dgp` et `plan_strategy_from_market_regime` (`AlgorithmicStrategyPlanner` dans `../quant-pod/scripts/quant_discovery_engine.py`).
4. **Recherche Ordonnancée par Bandit UCB, Régularisation AST & Backtest `SL_GAP`** :
   Exécuter `UCBFamilyBandit`, `ast_originality_penalty`, `bull_bear_hypothesis_debate`, `lookahead_truncation_test`, et `backtest_events` (chronologie intra-barre exacte + `bar_returns`) avec le `live_spread_bps` exact.
5. **Tribunal Aveugle `/boost`, Modèles Nuls des 10 Familles & Spanning de Portefeuille** :
   Exécuter `hansen_spa`, `romano_wolf_stepm`, `deflated_sharpe_effective`, `pbo_cscv`, `Coûts Live × 2`, `null_models.py` et `orthogonal_alpha_spanning_test` / `regime_conditional_book_allocator` (`quant_scientific_arsenal.py`) avant toute ouverture unique du Holdout.

### Chemins Relatifs vers les Moteurs & Références Partagés :
- Moteurs Python (`10/10`) : [`../quant-pod/scripts/`](../quant-pod/scripts/)
- Référence 11 Familles Synthétiques : [`../quant-pod/references/deriv_11_families.md`](../quant-pod/references/deriv_11_families.md)
- Encyclopédie SOTA 2026 : [`../quant-pod/references/sota_github_quant_crypto_prng_2026.md`](../quant-pod/references/sota_github_quant_crypto_prng_2026.md)
- Master Prompts prêts à copier : [`../quant-pod/references/master_prompts_arsenal.md`](../quant-pod/references/master_prompts_arsenal.md)
