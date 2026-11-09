# Encyclopédie SOTA 2024–2026 : Repos GitHub Quantitatifs, Backtesting Institutionnel, Microstructure DEX/CEX & Forensique Cryptographique CSPRNG

Ce document constitue la référence théorique et opérationnelle de **`quant-pod` v3.0 (L99 Institutionnel)**. Chaque brique recensée ci-dessous est reliée à son implémentation exécutable exacte dans `scripts/`.

---

## 1. Cartographie Critique des Meilleurs Repositories GitHub Quantitatifs (2024–2026)

| Repository / Papier | Architecture & Innovation Clé | Forces & Limites Réelles | Implémentation dans `quant-pod` v3.0 |
|---|---|---|---|
| **`microsoft/RD-Agent`** (`RD-Agent(Q)`, arXiv:2505.15155) | Co-optimisation Facteurs + Modèles (**Co-STEER**) pilotée par un **ordonnanceur Multi-Armed Bandit** qui alloue le budget de recherche selon le gain marginal sur feedback réel de backtest. | Évite de brûler le budget d'essais sur des familles mortes. Limite native : dépend de Qlib et n'intègre ni PBO ni SPA par défaut. | `UCBFamilyBandit` + `diagnose_failure_mode` dans `scripts/quant_discovery_engine.py` |
| **`AlphaAgent`** (Tang et al., **KDD 2025**, arXiv:2502.16789) | Régularisation structurelle par **Arbres Syntaxiques Abstraits (AST)** : mesure la similarité de sous-arbres face au *Factor Zoo* existant pour contrer l'*alpha decay* et le *crowding*, et borne la profondeur syntaxique. | Empêche le LLM de reformuler des clones algébriques (`(a+b)*c` vs `c*(b+a)`) ou d'empiler des constantes surajustées. | `ast_canonical_shingles`, `ast_similarity_score`, `ast_originality_penalty` dans `scripts/quant_discovery_engine.py` |
| **`TauricResearch/TradingAgents`** (Xiao et al., arXiv:2412.20138) | Architecture multi-agents reproduisant un desk : Analystes spécialisés $\to$ **Débat contradictoire Bull vs Bear Researchers** $\to$ Trader $\to$ Risk/Portfolio Gatekeeper. | Le débat contradictoire pré-exécution filtre les narratifs séduisants mais physiquement impossibles. Manque de tests économétriques formels dans le repo d'origine. | `bull_bear_hypothesis_debate` (`quant_discovery_engine.py`) + Sous-agent aveugle `quant-blind-validator` |
| **`nkaz001/hftbacktest`** & **`nautechsystems/nautilus_trader`** | Simulation événementielle déterministe : latence explicite d'ordre et de flux, position dans la file d'attente L2/L3 (*queue position*), séparation Maker/Taker, et parité stricte code recherche = code live. | Référence absolue contre l'illusion des backtests vectorisés `close-to-close` sans latence ni sélection adverse. | `backtest_events`, `markouts` dans `scripts/event_backtester.py` |
| **`freqtrade/freqtrade`** (`lookahead-analysis` & `recursive-analysis`) | **Sonde empirique anti-lookahead par troncation** : compare `signal(data[:t])` à `signal(data_complète)[:t]` sur des points de contrôle aléatoires ; et **sonde d'instabilité de warmup** sur les filtres récursifs (EMA/Kalman/RSI). | Détecte 100 % des fuites subtiles (`rolling(center=True)`, normalisation globale, jointures non causales) qu'une relecture statique manque. | `lookahead_truncation_test`, `warmup_stability_test` dans `scripts/event_backtester.py` |
| **`bashtage/arch`** (Kevin Sheppard) | Implémentation économétrique de référence du **Stationary Bootstrap** de Politis-Romano, sélection automatique de bloc **Politis-White (2004) + correction Patton (2009)**, **White Reality Check**, **Hansen SPA**, **Romano-Wolf StepM**, et **Model Confidence Set (MCS)**. | Indispensable dès que $K > 1$ stratégies sont comparées sur la même série dépendante et hétéroscédastique. | Ré-implémenté nativement en `numpy`/`scipy` pur dans `scripts/quant_inference_engine.py` |
| **`shiyu-coder/Kronos`** (Tsinghua, arXiv:2508.02739) vs **`Chronos` / `TimesFM`** | Modèle de fondation pré-entraîné sur $12 \times 10^9$ bougies OHLCV via tokenisation hiérarchique discrète BSQ, surpassant les modèles de séries temporelles génériques (`TimesFM`, `Chronos`, `PatchTST`) dont le $R^2$ zéro-shot sur OHLCV financier est quasi nul. | Utile comme *feature extractor* de régime ou prévision de volatilité sur marchés réels ; **inutile sur une martingale CSPRNG pure** (plafond de Doob). | Intégré dans la doctrine Phase 1/Phase 2 (interdiction d'entraîner du ML sur une martingale sans structure DGP prouvée) |
| **`usnistgov/SP800-90B_EntropyAssessment`** & **NIST STS SP 800-22** | Batteries officielles d'évaluation d'entropie minimale non-IID (MCV, Markov, $t$-Tuple, LRS) et tests fréquentiels/spectraux de générateurs aléatoires. | Seul standard recevable en cryptanalyse de générateurs synthétiques ; interdit de conclure à un biais PRNG sur un simple test de runs isolé. | `nist_sp800_22_battery`, `sp800_90b_min_entropy`, `pit_battery` dans `scripts/prng_forensics.py` |

---

## 2. Standards des Pods Quantitatifs Institutionnels (Two Sigma, Citadel, Jane Street, AQR, Man AHL)

### 2.1 Inférence sous Tests Multiples & Dépendance Temporelle (`quant_inference_engine.py`)
Lorsqu'un chercheur ou un agent IA explore $K$ variantes (signaux, seuils, horizons, actifs), la statistique $t$ naïve est biaisée par sélection :
1. **Seuil minimal de découverte** (Harvey, Liu & Zhu, *Review of Financial Studies*, 2016) :
   $$|t_{\text{net}}| \ge 3.0 \quad (\text{et } \ge 3.5 \text{ en fouille automatique d'alpha})$$
   Correction du **Haircut Sharpe Ratio** sous dépendance arbitraire (Benjamini-Hochberg-Yekutieli, 2001, facteur harmonique $c(K) = \sum_{i=1}^K \frac{1}{i}$).
2. **Nombre Effectif d'Essais Indépendants $N_{\text{eff}}$** (López de Prado, 2020) :
   Les $K$ essais d'une grille ne sont ni indépendants ($N_{\text{eff}} = K$) ni identiques ($N_{\text{eff}} = 1$). Soit $\{\lambda_i\}_{i=1}^K$ le spectre de la matrice de corrélation des rendements des $K$ essais :
   $$N_{\text{eff}}^{\text{spectral}} = \frac{\left(\sum_{i=1}^K \lambda_i\right)^2}{\sum_{i=1}^K \lambda_i^2}$$
   Complété par le clustering hiérarchique de Ward maximisant le score de silhouette (`effective_number_of_trials`), puis injecté dans `deflated_sharpe_effective` :
   $$\mathbb{E}[\max_{k \le N_{\text{eff}}} \widehat{SR}_k \mid H_0] \approx \sqrt{V[\widehat{SR}]} \left[(1 - \gamma_{\text{Euler}})\Phi^{-1}\!\left(1 - \frac{1}{N_{\text{eff}}}\right) + \gamma_{\text{Euler}}\Phi^{-1}\!\left(1 - \frac{1}{N_{\text{eff}} e}\right)\right]$$
3. **Longueur Optimale de Bloc Automatique** (Politis & White, 2004 ; Patton, Politis & White, 2009) :
   Estime la fenêtre spectrale plate sur l'autocorrélation empirique et applique la correction exacte de Patton (2009) pour le Stationary Bootstrap ($D_{SB} = 2 g^2(0)$) afin de préserver le clustering de volatilité GARCH et la dépendance sérielle.
4. **Hiérarchie des Tests Bootstrap Groupés** :
   - **White's Reality Check (2000)** : teste $\max_k \bar{d}_k \le 0$, mais perd de la puissance si l'on inclut des stratégies très perdantes dans le pool.
   - **Hansen's SPA (2005)** (`hansen_spa`) : studentise par $\hat{\omega}_k$ et recentre par $\hat{\mu}_k^c = \bar{d}_k \cdot \mathbf{1}\{\sqrt{T}\bar{d}_k/\hat{\omega}_k \le -\sqrt{2 \ln \ln T}\}$, éliminant l'effet parasite des mauvaises variantes.
   - **Romano-Wolf StepM (2005)** (`romano_wolf_stepm`) : procédure *step-down* identifiant le sous-ensemble exact de stratégies contrôlant le FWER au niveau $\alpha$.
   - **Model Confidence Set — MCS** (Hansen, Lunde & Nason, *Econometrica*, 2011) (`model_confidence_set`) : élimine séquentiellement le pire modèle jusqu'à obtenir l'ensemble $\widehat{\mathcal{M}}_{1-\alpha}^*$ des stratégies statistiquement indiscernables de la meilleure.
5. **Minimum Track Record Length (`min_track_record_length`)** (Bailey & López de Prado, 2012) :
   $$T_{\min} = 1 + \left[1 - \hat{\gamma}_3 \widehat{SR} + \frac{\hat{\gamma}_4 - 1}{4}\widehat{SR}^2\right] \left(\frac{z_{1-\alpha}}{\widehat{SR} - SR^*}\right)^2$$
   Une stratégie à skew négatif ($\hat{\gamma}_3 < 0$, typique du portage, de la vente de volatilité ou du trading contre des spikes Boom/Crash) exige un historique **beaucoup plus long** qu'une stratégie gaussienne de même Sharpe.

### 2.2 Intégrité Cryptographique Anti-Triche (`research_integrity.py`)
- **`HashChainLedger`** : journal JSONL chaîné où chaque entrée $i$ stocke $h_i = \text{SHA256}(h_{i-1} \,\|\, \text{canonical\_json}(\text{payload}_i))$. Supprimer un essai perdant après coup brise immédiatement la chaîne (`ledger.verify()`).
- **Pré-engagement cryptographique (`commit_hypothesis` / `reveal_verify`)** : hachage salé de la fiche `cards/H###.md` enregistré dans le ledger avant d'observer le moindre backtest.
- **Arbre de Merkle des données (`data_manifest`, `seal_holdout`)** : fige l'empreinte binaire exacte des fichiers de marché et verrouille le Holdout 20 %.

### 2.3 Réalisme Microstructurel & Détection de Sélection Adverse (`event_backtester.py`)
- **Exécution avec latence, spread bid/ask et gaps** (`backtest_events`) : décision en $t$, exécution à l'ouverture de $t + \text{latency\_bars}$ à `open ± spread/2`, priorité pessimiste au Stop-Loss si SL et TP sont touchés dans la même bougie, et **exécution au prix post-gap (`SL_GAP`)** lorsque l'ouverture franchit le stop (crucial sur Boom/Crash, Jump Indices et gaps week-end).
- **Courbe de Markout** (`markouts`) : mesure $\text{side} \cdot \frac{\text{mid}_{t+h} - \text{mid}_t}{\text{mid}_t}$ pour $h \in \{1, 2, 5, 10, 30\}$. Une courbe de markout immédiatement négative à $h=1$ diagnostique une **sélection adverse (toxic flow)** : on est exécuté exactement quand un teneur informé décale le prix contre nous.

---

## 3. Modèles Mathématiques DEX / DeFi & CEX Perpétuels (`crypto_defi_engine.py`)

### 3.1 Loss-Versus-Rebalancing (LVR) & Arbitrage d'AMM (Milionis, Moallemi, Roughgarden & Zhang, 2022–2023)
Sur un AMM à fonction constante (CPMM $x \cdot y = L^2$ ou liquidité concentrée Uniswap v3 sur $[P_a, P_b]$), le coût d'antisélection payé par le fournisseur de liquidité (LP) face aux arbitragistes continus est le **LVR instantané** :
$$\text{LVR}_{\text{inst}} = \frac{\sigma^2}{2} P^2 |x''(P)| = \frac{\sigma^2 L \sqrt{P}}{4}$$
Pour un CPMM pleine plage ($V(P) = 2 L \sqrt{P}$), le taux de perte par unité de valeur déposée vaut exactement :
$$\frac{\text{LVR}}{V} = \frac{\sigma^2}{8}$$
En temps de bloc discret Poissonnien de moyenne $\Delta t = \lambda^{-1}$ et frais de pool $\gamma$ (Milionis et al., EC '23, arXiv:2305.14604), la probabilité qu'un bloc déclenche un arbitrage est (`arb_with_fees_ptrade`) :
$$P_{\text{trade}} = \frac{1}{1 + \frac{\gamma}{\sigma}\sqrt{\frac{2}{\Delta t}}}$$
et un LP n'est structurellement rentable que si le volume organique (bruit non toxique) vérifie (`lp_breakeven_volume`) :
$$\gamma \cdot \text{Volume}_{\text{organique}} > \text{LVR}(\sigma, \gamma, \Delta t, \text{concentration})$$

### 3.2 Arbitrage Optimal CPMM (`cpmm_optimal_arbitrage`)
Face à un prix externe CEX $P_{\text{ext}}$ et des réserves $(x, y)$ taxées au taux $\gamma$, la taille optimale exacte d'achat/vente d'actif risqué maximisant le profit net de gaz se déduit en forme fermée :
$$\Delta x^* = \sqrt{\frac{x \cdot y}{(1 - \gamma) P_{\text{ext}}}} - x \quad \text{(si } P_{\text{AMM}} < (1-\gamma) P_{\text{ext}}\text{)}$$

### 3.3 Portage Delta-Neutre Spot + Perpétuel & Risque de Liquidation (`funding_carry_backtest`)
Conformément à Ackerer, Hugonnier & Jermann (NBER w32936, sept. 2024), l'arbitrage de *funding rate* (Long Spot + Short Perp) n'est **pas** un arbitrage sans risque :
- Le PnL net combine les versements périodiques de financement, la variation de la base $B_t = F_t - S_t$, les 4 jambes de frais/slippage d'entrée/sortie, et la **contrainte d'arrêt absorbante de liquidation** lorsque la marge de la jambe Perp tombe sous `maint_margin` lors d'un squeeze haussier brutal (`liquidated: True` dans `funding_carry_backtest`).

### 3.4 Market Making Optimal en Carnet d'Ordres (`avellaneda_stoikov_quotes`, `glft_quotes`)
- **Avellaneda & Stoikov (2008)** : prix de réserve ajusté de l'inventaire $q_t$ :
  $$r(s, q, t) = s - q \gamma \sigma^2 (T - t), \qquad \delta^a + \delta^b = \gamma \sigma^2 (T - t) + \frac{2}{\gamma}\ln\!\left(1 + \frac{\gamma}{k}\right)$$
- **Guéant, Lehalle & Fernandez-Tapia (2013)** : régime asymptotique stationnaire sans horizon terminal artificiel $T$, bornant naturellement l'inventaire maximal.

---

## 4. Forensique Cryptographique CSPRNG & Modèles Nuls des 11 Familles Deriv (`prng_forensics.py` & `null_models.py`)

### 4.1 Réalité Cryptographique vs Illusions Statistiques
1. **État de l'art de la cryptanalyse de PRNG** (`mt19937_recover_and_predict`, `prng_attack_feasibility`) :
   - Un PRNG **linéaire non cryptographique** tel que Mersenne Twister (`MT19937`) est inversible algébriquement dès que l'on observe $624$ sorties brutes consécutives de $32$ bits sans troncation (dé-tempérage exact bit à bit prouvé dans `mt19937_recover_and_predict`).
   - En revanche, dès que le serveur utilise un **CSPRNG moderne** (AES-CTR, ChaCha20, HMAC-DRBG — architecture certifiée par auditeurs tiers indépendants sur les indices synthétiques réglementés) **ou** que les sorties subissent un hachage/transformation non linéaire avec perte de bits, la complexité de reconstruction d'état est $\ge 2^{128}$ opérations : **mathématiquement infaisable**.
2. **Protocole Forensique Rigoureux (`prng_forensics.py`)** :
   - **Batterie NIST SP 800-22** (`nist_sp800_22_battery`) : découpage en $m$ séquences indépendantes, vérification simultanée de la **proportion de séquences réussies** $\ge (1-\alpha) - 3\sqrt{\alpha(1-\alpha)/m}$ et de l'**uniformité KS des p-values** sur les 8 tests fondamentaux (Fréquence, Fréquence par bloc, Runs, Plus longue série de 1, CUSUM, Entropie Approchée, Serial, FFT Spectrale).
   - **Entropie Minimale Non-IID NIST SP 800-90B §6.3** (`sp800_90b_min_entropy`) : prend le minimum conservateur entre Most Common Value (`MCV`), Markov, $t$-Tuple et Longest Repeated Substring (`LRS`).
   - **Batterie PIT — Probability Integral Transform** (`pit_battery`) : transforme les innovations par la CDF du modèle $u_t = F(x_t \mid \mathcal{F}_{t-1})$ et applique simultanément Kolmogorov-Smirnov, **Anderson-Darling exact (Marsaglia 2004)** sensible aux queues, Cramér-von Mises, Ljung-Box sur $z_t$ et $z_t^2$, et le test du rapport de vraisemblance de **Berkowitz (2001)**.
   - **Tests par Séries Substituts (`surrogate_test` — IAAFT)** : toute métrique dite « chaotique » (Hurst, Lyapunov, BDS, RQA) DOIT être comparée à $N_{\text{surr}} \ge 99$ substituts IAAFT préservant exactement la distribution marginale et le spectre de puissance linéaire.
3. **Condition d'Exploitabilité Économique (`exploitability_verdict`)** :
   Un écart statistique $p_{\text{obs}} = 0.5008$ sur $10^7$ ticks est statistiquement détectable mais **économiquement inexploitable** si la borne inférieure de confiance de Wilson corrigée de Bonferroni reste sous la probabilité de break-even imposée par le spread live :
   $$p^* = \frac{1}{2} + \frac{\text{Coût Aller-Retour}}{2 \cdot \mathbb{E}[|\Delta S_H|]}$$
   Seul `CI_low(p_obs) > p^*` autorise le verdict `EXPLOITABLE`.
4. **Simulateurs de Modèles Nuls Martingales Exactes (`null_models.py`)** :
   Toute stratégie testée sur l'une des familles Deriv (`volatility`, `boom_crash`, `jump`, `step`, `multi_step`, `skew_step`, `dsi`, `range_break`, `dex`, `trek`) est obligatoirement confrontée à $M \ge 100$ trajectoires synthétiques générées par `null_models.py` (calibrées sur les moments réels via `calibrate_family`, avec espérance martingale nulle par construction) afin de mesurer le vrai taux de faux positifs de **toute la chaîne de sélection**.
