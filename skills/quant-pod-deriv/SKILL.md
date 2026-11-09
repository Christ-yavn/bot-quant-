---
name: quant-pod-deriv
description: Desk Quantitatif Institutionnel v3.0 L99 dédié à l'écosystème Deriv (94 symboles / 11 familles synthétiques, MT5 CFD & API WebSocket Options/Multipliers/Accumulators) — câblé sur la moisson officielle DERIV_ALL_11_FAMILIES_HARVEST, les 7 règles inviolables du projet Deriv, la forensique CSPRNG NIST SP 800-22/90B/PIT, les 10 modèles nuls martingales exacts, et la flotte multi-agents à 2 niveaux de quant-pod v3.0.
---

# Quant Pod Deriv v3.0 — Desk de Recherche Quantitative Spécialisé Deriv (94 Symboles / 11 Familles)

Ce skill est l'extension spécialisée **Deriv Synthetic & Options/CFD** de [`quant-pod` v3.0](file:///C:/Users/CHRIST/.gemini/config/skills/quant-pod/SKILL.md). Il hérite de **100 % des lois, de l'orchestration multi-agents à 2 niveaux (`define_subagent` + `EnableSubagentTools: true` + `invoke_subagent`) et des 10 moteurs Python** de `quant-pod`, tout en intégrant nativement l'infrastructure, l'historique empirique et les garde-fous inviolables du projet Deriv de l'utilisateur.

---

## 1. INFRASTRUCTURE & DONNÉES RÉELLES CÂBLÉES PAR DÉFAUT

1. **Moisson Historique & Microstructure Officielle (94 Symboles / 11 Familles)** :
   - Répertoire : `C:\Users\CHRIST\Downloads\DERIV_ALL_11_FAMILIES_HARVEST\`
   - Manifeste maître : `DERIV_HARVEST_ARCHIVE_00_MANIFEST.zip` $\to$ `HARVEST_MASTER_MANIFEST.csv` & `.parquet` (contient `symbol`, `family`, `digits`, `point`, `tick_size`, `tick_value`, `contract_size`, `live_tick_spread_mean_pts`, `live_tick_spread_p95_pts`, **`live_spread_bps`**, `swap_long`, `swap_short`, et compteurs de barres/ticks).
   - Archives par famille (`01_CRASH_BOOM` à `11_HYBRID_TACTICAL`) : barres `D1, H4, H1, M15, M5, M1` + `500,000` ticks (`*_TICKS_SAMPLE.parquet`) lisibles directement en mémoire via `zipfile` + `pyarrow`/`pandas` sans décompresser des gigaoctets sur le disque.
2. **Dossier Projet & Mémoire Historique Deriv** :
   - Répertoire : `C:\Users\CHRIST\Desktop\IA\ANTIGRAVITY\projets\general project   quant bot deriv\`
   - Fichiers de vérité à lire avant toute action sur le projet : `AGENT.md` et `MEMOIRE_MAITRE_NOUVELLE_CONVERSATION.md`.
   - Terminal MT5 Deriv : `C:\Program Files\MetaTrader 5 Terminal\terminal64.exe` | Data Folder : `C:\Users\CHRIST\AppData\Roaming\MetaQuotes\Terminal\FB9A56D617EDDDFE29EE54EBEFFE96C1\`.

---

## 2. LES 7 LOIS INVIOLABLES SPÉCIFIQUES DERIV (Tirées du sang versé en Live/Demo)

1. **Loi du Spread Live vs `CopyTicks` ($\times 7$ à $\times 11$)** :
   Les spreads historiques MT5 sous-estiment massivement les spreads exécutés sur certains indices synthétiques (ex. Boom/Crash). **Toujours** injecter le `live_spread_bps` / `live_tick_spread_p95_pts` mesuré dans `HARVEST_MASTER_MANIFEST.csv` (et tester `Coûts Live × 2` en Phase 5).
2. **Loi d'Archivage Additif Non-Destructif** :
   **Ne JAMAIS écraser, supprimer ou casser** un EA MQL5 actif (ex. `Deriv_VolSqueeze_Breakout_EA_v3.mq5` Track 2) ni perturber le terminal MT5 ouvert. Tout nouveau candidat est écrit dans un dossier isolé (`quant_pod_runs/<campagne>/`) avec un `MagicNumber` dédié.
3. **Théorème d'Arrêt Optionnel de Doob & Classification des 11 Familles** :
   - **Classe M — Martingales CSPRNG pures à loi stationnaire connue** (`04_CLASSIC_STEP`, `05_MULTI_STEP`, `06_SKEW_STEP`, `10_VOLATILITY_INDICES`, `09_JUMP_INDICES`, `01_CRASH_BOOM` net de la dérive compensatrice, `03_DEX_INDICES`, `08_RANGE_BREAK`) :
     - Sur les CFD au comptant, si aucune anomalie forensique CSPRNG ne franchit `exploitability_verdict` ($\text{CI}_{\text{low}}(p) > p^*$) dans `prng_forensics.py`, toute combinaison de stops, trailing stops, filtres techniques ou martingales de lots a $\mathbb{E}[\text{PnL}] = -\text{Spread Live} - \text{Swaps}$.
     - Interdiction absolue du **sophisme du joueur** sur Boom/Crash (« pas de spike depuis $N$ ticks $\implies$ probabilité accrue » : processus de Poisson sans mémoire, réfuté sur $3\,412$ trades réels Track 1).
     - Exécution obligatoire du Stop-Loss au prix **post-spike (`SL_GAP`)** dans `event_backtester.backtest_events` (un stop placé dans un spike Crash/Boom glisse de toute l'amplitude du saut).
   - **Classe R — Processus à Changement de Régime / Persistance par Design** (`02_DRIFT_SWITCH_DSI` : DSI 10/20/30, `07_TREK_INDICES`, et sous-familles tactiques `11_HYBRID_TACTICAL`) :
     - Possèdent une dérive latente persistante par construction, mais assortie d'un **spread live plus large** (ex. `7.86 bps` sur `Drift Switch Index 10`) et d'un délai de détection Bayésien.
     - L'edge n'existe que si : $\mathbb{E}[\text{Dérive captée après détection (Wonham/CUSUM/Weibull)}] > \text{Spread Live} + \text{Swaps}$, prouvé face au simulateur nul `sim_dsi` / `sim_trek` (`null_models.py`) et `hansen_spa`.
   - **Classe O — Arbitrage de Juste Valeur sur Contrats Non-Linéaires (API WebSocket Deriv : Options Barrières, Touch/No-Touch, Digits, Accumulators)** :
     - Compare la probabilité exacte de survie/franchissement sous le DGP calibré (`accumulator_survival_probability`, `audit_range_break_barriers`, Monte-Carlo exact) au payout offert par l'API Deriv (`break_even_probability`).
4. **Loi Anti-Surajustement ML / ONNX** :
   Interdiction de déployer un filtre ONNX/XGBoost/LSTM dont l'AUC hors-échantillon purgée est $\le 0.52$ ou qui échoue à `lookahead_truncation_test`. Par défaut, préférer des filtres d'état causaux parcimonieux ($\le 3$ paramètres : Wonham 3-états, Yang-Zhang Squeeze, Kalman 1D) validés par `ast_originality_penalty`.
5. **Loi d'Alignement Vectoriel & d'Échelle `[0, 1]`** (si modèle ML validé) : alignement strict feature-par-feature Python $\leftrightarrow$ MQL5 et échelle de probabilité vérifiée.
6. **Loi Anti-Spam d'Exécution (`shift=1`)** : toute décision sur bougie se prend sur bougie **clôturée** (`shift=1`, soit `latency_bars=1` à l'ouverture suivante dans `backtest_events`) pour éliminer le *repainting* intra-barre.
7. **Loi du Modèle Nul Spécifique par Famille (`null_models.py`)** :
   Aucun candidat Deriv ne peut être déclaré `GO PAPER` sans avoir battu ($p_{\text{null}} \le 0.05$) le maximum d'une recherche identique menée sur $M \ge 100$ trajectoires synthétiques générées par le modèle nul exact de sa famille (`calibrate_family` + `make_null_generator`).

---

## 3. WORKFLOW D'EXÉCUTION `quant-pod-deriv` EN 5 ÉTAPES

1. **Initialisation & Séquestration Holdout 20 %** :
   Lire `HARVEST_MASTER_MANIFEST.csv`, sceller les 20 % les plus récents de chaque série dans `HashChainLedger` (`scripts/research_integrity.py`).
2. **Déploiement de la Flotte Multi-Agents à 2 Niveaux (`define_subagent` + `invoke_subagent`)** :
   Conformément à la Section `0.bis` de [`../quant-pod/SKILL.md`](file:///C:/Users/CHRIST/.gemini/config/skills/quant-pod/SKILL.md) (`quant-deep-investigator`, `quant-deep-coder`, `quant-blind-validator`, `quant-risk-architect`).
3. **Forensique CSPRNG & Diagnostic DGP** :
   Exécuter `nist_sp800_22_battery`, `sp800_90b_min_entropy`, `pit_battery`, `exploitability_verdict` (`scripts/prng_forensics.py`) et `diagnose_market_dgp` (`scripts/quant_discovery_engine.py`).
4. **Recherche Ordonnancée par Bandit UCB, Régularisation AST & Backtest `SL_GAP`** :
   Exécuter `UCBFamilyBandit`, `ast_originality_penalty`, `bull_bear_hypothesis_debate`, `lookahead_truncation_test`, et `backtest_events` avec le `live_spread_bps` exact du manifeste.
5. **Tribunal Aveugle `/boost` & Modèles Nuls des 10 Familles Deriv** :
   Exécuter `hansen_spa`, `romano_wolf_stepm`, `deflated_sharpe_effective`, `pbo_cscv`, `Coûts Live × 2`, et `null_models.py` avant toute ouverture unique du Holdout.

### Chemins Directs vers les Moteurs & Références Partagés :
- Moteurs Python (`10/10`) : `C:\Users\CHRIST\.gemini\config\skills\quant-pod\scripts\`
- Référence 11 Familles Deriv : [`../quant-pod/references/deriv_11_families.md`](file:///C:/Users/CHRIST/.gemini/config/skills/quant-pod/references/deriv_11_families.md)
- Encyclopédie SOTA 2026 : [`../quant-pod/references/sota_github_quant_crypto_prng_2026.md`](file:///C:/Users/CHRIST/.gemini/config/skills/quant-pod/references/sota_github_quant_crypto_prng_2026.md)
- Master Prompts prêts à copier : [`../quant-pod/references/master_prompts_arsenal.md`](file:///C:/Users/CHRIST/.gemini/config/skills/quant-pod/references/master_prompts_arsenal.md)
