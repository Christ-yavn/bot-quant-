# GUIDE OPÉRATIONNEL & PROTOCOLE POUR AGENTS IA (AGENT.md)
## Cadre Quantitatif, Invariants Mathématiques, Architecture, Historique Complet & Procédures d'Exécution

Ce document constitue le **point d'entrée unique et obligatoire** pour tout agent d'intelligence artificielle (Antigravity, Claude Code, Gemini, Cursor, ChatGPT ou tout sous-agent du Quant Pod `/agent-quant-pod`) intervenant sur le dépôt `Christ-yavn/bot-quant-`.

> **INSTRUCTION IMPÉRATIVE POUR TOUT NOUVEL AGENT IA :**
> Si tu démarres une nouvelle session ou discussion, tu dois **obligatoirement** lire dans l'ordre :
> 1. Ce fichier **`AGENT.md`** (ton cockpit technique et les invariants inviolables).
> 2. **`MEMOIRE_MAITRE_NOUVELLE_CONVERSATION.md`** (la mémoire complète de toute la genèse du projet, des versions v1 à v8.30 et v3.30, des preuves mathématiques et des performances live).
> 3. **`CHANGELOG_AND_HISTORY.md`** (la chronologie intégrale des étapes 1 à 14.8).
> 4. Les rapports d'audit dans `docs/` : **`docs/ETAT_DE_LA_VERITE.md`**, **`docs/DATA_FORENSIC_REPORT.md`**, **`docs/CODE_ARCHITECTURE_AUDIT.md`** et **`docs/ADVERSARIAL_VERDICT_REPORT.md`**.

---

## 1. MISSION DU RÉPERTOIRE & ÉTAT ACTUEL DES SYSTÈMES (AU 10 NOVEMBRE 2026)

Le projet **QUANT BOT DERIV** est un environnement d'ingénierie quantitative, d'audit économétrique haute fréquence et de trading algorithmique appliqué aux indices synthétiques continus du courtier **Deriv** :

| Track / Système | Fichier Source Principal | Version Actuelle | Statut Opérationnel | Bilan & Performance Live Certifiée (Compte `32449166`) |
| :--- | :--- | :---: | :---: | :--- |
| **Track 1 : Boom & Crash HFT** | `src/mql5/DerivBoomCrashHFT_v830_Ultimate.mq5` | `v8.30 Ultimate` | **EN PAUSE / VETO `/boost`** (Retiré de MT5 le 29/10 à 09:20 UTC) | **3 412 trades** : **`-914.78 USD`** ($WR = 46.92\%$, $\text{EV} = -0.2681\$$/trade, $\text{DSR} = 0.0000$). Processus de Poisson sans mémoire prouvé sur 1,68M ticks + faille `VULN-01` ("Trapped Spike") identifiée. |
| **Track 2 : Panier Tri-Actifs Élite** | `src/mql5/Deriv_VolSqueeze_Breakout_EA_v3.mq5` | **`v3.40 Panier Tri-Actifs Élite`** | **ACTIF EN PRODUCTION (3 graphiques synchronisés : V25 H1, V5 M30, V15 M30)** | **Panier Tri-Actifs Déployé en Direct** :<br>• **Volatility 25 (1s) [ALPHA_KING, H1]** : $Q=0.30, Z=1.25, H=4\text{b}$, Magic `20261021`, Cap `0.05 lot`. $WR=58.33\%$, $+6.38\text{ bps/trade}$.<br>• **Volatility 5 (1s) [HIGH_FREQ, M30]** : $Q=0.30, Z=1.25, H=8\text{b}$ (4h), Magic `20261025`, Cap `0.20 lot`. $WR=61.90\%$, $+0.12\text{ à }+0.41\text{ bps/trade}$.<br>• **Volatility 15 (1s) [STABILIZER, M30]** : $Q=0.30, Z=1.25, H=8\text{b}$ (4h), Magic `20261015`, Cap `0.50 lot`. $WR=59.29\%$, $+0.46\text{ bps/trade}$.<br>• **Sécurités v3.40** : Cold-Boot Freshness Guard (300s max) + Hard Disaster SL serveur ($2.50\times\text{ATR20}$). |
| **Track 3 : Scanner WebSocket Deriv** | `src/python/deriv_fair_value_scanner.py` | `v1.0` | **OUTIL D'AUDIT** | Évaluation analytique de **349 contrats options Deriv** (9 familles) : 0 contrat à EV positive ($\text{EV}_{\max} = -0.45\%$). |
| **Track 4 : Recherche Multi-Marchés Deriv** | Skill `quant-pod` (`deriv_quant_engine.py` + `quant_scientific_arsenal.py`) | `L99` | **EN RECHERCHE ACTIVE** | Exploration scientifique des 11 familles synthétiques Deriv (DSI, DEX, Step, Multi-Step, Skew Step, Trek, Range Break, Jump, Volatility, Accumulators) pour concevoir la prochaine génération de bots. |

---

## 2. LES 7 INVARIANTS ABSOLUS DU PROJET (RÈGLES INVIOLABLES)

Tout agent opérant sur ce code **doit respecter sans exception** les sept lois fondamentales suivantes :

### Règle 1 : Vérité du Spread Live (`SymbolInfoTick` vs `CopyTicks`)
* L'historique `CopyTicks` de MetaTrader 5 sous-estime le spread réel exécuté d'un facteur 7 à 11 (ex. Crash 600 affiche $0.297\text{ pt}$ dans l'historique contre $3.281\text{ pts}$ en direct).
* **Interdiction absolue** de calculer une rentabilité, un backtest ou un filtre sans déduire le spread réel live fourni par `SymbolInfoTick(symbol, tick)` ou le référentiel `src/python/colab_ai/real_live_spreads_mt5.json`.

### Règle 2 : Principe d'Archivage Additif Immuable
* **Ne jamais supprimer ni écraser** les anciens codes, anciens manuels ou anciens modèles ONNX.
* Les versions historiques (`v6`, `v7`, `v8`, `v830`, `VolSqueeze v1`, `v3.10`, `v3.20`, `v3.30`, etc.) doivent rester intactes dans `archive/` ou dans `src/mql5/` pour garantir la reproductibilité forensique et l'historique complet du projet.

### Règle 3 : Alignement Strict des Vecteurs ONNX (Features MQL5 $\leftrightarrow$ Python)
* **Track 1 (Boom/Crash)** : Vecteur d'entrée strictement égal à `float[1][14]`, aligné dans l'ordre exact de `src/models/onnx_model_metadata.json` (`symbol_id`, `is_boom`, `spike_amp_norm`, `tau1..3`, `h_fast`, `h_med`, `h_slow`, `c60`, `c300`, `post3_vel`, `be_ticks`, `cost_ratio`).
* **Track 2 (Volatilité H1)** : Vecteur d'entrée strictement égal à `float[1][7]`, aligné dans l'ordre exact : `vol_ratio`, `impulse_z`, `direction`, `levy_area`, `spread_to_atr`, `skew20`, `kurt20`.

### Règle 4 : Cohérence d'Échelle des Probabilités (Base 1.0 vs Base 100.0)
* Les classifieurs ONNX génèrent une probabilité $P \in [0.0 ; 1.0]$.
* Dans les paramètres MQL5, `InpMinWinProbability` doit toujours être compris entre `0.0` et `1.0` (ex. `0.42` pour 42%, `0.50` pour 50%).
* `Deriv_VolSqueeze_Breakout_EA_v3.mq5` (`v3.30`) intègre un mécanisme de sécurité : `if (prob > 1.0) prob /= 100.0;`. Tout nouveau code doit obligatoirement préserver cette garde.

### Règle 5 : Chemins MT5, Compilation & Profils de Graphiques
* Deux installations MT5 existent sur cette machine. L'installation dédiée à Deriv est exclusivement :
  - **Exécutable Terminal** : `C:\Program Files\MetaTrader 5 Terminal\terminal64.exe`
  - **Compilateur MQL5** : `C:\Program Files\MetaTrader 5 Terminal\metaeditor64.exe`
  - **Répertoire de données (Data Folder)** : `C:\Users\CHRIST\AppData\Roaming\MetaQuotes\Terminal\FB9A56D617EDDDFE29EE54EBEFFE96C1`
  - **Dossier Experts MT5** : `C:\Users\CHRIST\AppData\Roaming\MetaQuotes\Terminal\FB9A56D617EDDDFE29EE54EBEFFE96C1\MQL5\Experts`
  - **Dossier Modèles ONNX MT5** : `C:\Users\CHRIST\AppData\Roaming\MetaQuotes\Terminal\FB9A56D617EDDDFE29EE54EBEFFE96C1\MQL5\Files`
  - **Compte de test** : `32449166` (`Deriv-Demo`).
* Les fichiers de profils graphiques (`chart02.chr`, `chart03.chr`) doivent obligatoirement posséder `expertmode=5` (Trading automatique = ACTIF, DLL = ACTIF).

### Règle 6 : Pas de Sur-Optimisation, Bypass ONNX par Défaut (`v3.31`) & Seuils Supportés
* L'audit contradictoire `/boost` du 02/11/2026 a établi que `c2_vol_filter.onnx` (`== c2_vol_filter_v25.onnx`, `13 180` octets) présente un `ROC-AUC = 0.4457 < 0.50` sur le Holdout strict post-août 2025, et que `c2_vol_filter_v75.onnx` (`11 647` octets) génère une espérance négative sur le Holdout V75 (`-6.21 bps/trade`, `DSR = 0.1863`).
* En production `v3.31 Hardened`, **`InpUseONNXFilter = false`** est le mode standard (**Signal Pur S1 Quant** sans boîte noire : `InpSqueezeQuantile = 0.30`, `InpBreakoutZScore = 1.25`), tout en conservant intacts les fichiers `.onnx` et le pipeline d'inférence à 7 features (si réactivé pour recherche, ne jamais utiliser un seuil `P_min >= 0.60` hors du support GBDT $[0.34 ; 0.59]$).

### Règle 7 : Architecture Multi-Graphiques `v3.40 Panier Tri-Actifs Élite` & Sécurités Durcies
* L'évaluation empirique multi-temporelle et la loi d'échelle brownienne prouvent que descendre en M5 ou M1 détruit l'edge à cause du frottement de spread relatif ($\text{Friction} \propto \frac{2s}{\sigma\sqrt{\Delta t}}$). En revanche, la diversification horizontale sur 3 actifs à corrélation nulle ($|\rho| \le 0.026$) permet de tripler le volume de trades tout en conservant une rentabilité d'élite.
* **Architecture Tri-Actifs `v3.40`** (3 graphiques MT5 simultanés avec auto-preset natif via `InpApplyV340TriActifsPreset=true`) :
  - **Graphique 1 : `Volatility 25 (1s) Index` (H1, Role `ALPHA_KING`)** : $Q=0.30, Z=1.25, H=4\text{ barres}$ (4.0h), Magic `20261021`, Cap `0.05 lot`. $WR=58.33\%$, $+6.38\text{ bps/trade}$. Gère également les tickets historiques via Magic `20261022`.
  - **Graphique 2 : `Volatility 5 (1s) Index` (M30, Role `HIGH_FREQ`)** : $Q=0.30, Z=1.25, H=8\text{ barres}$ (4.0h), Magic `20261025`, Cap `0.20 lot`. $WR=61.90\%$, $+0.12\text{ à }+0.41\text{ bps/trade}$.
  - **Graphique 3 : `Volatility 15 (1s) Index` (M30, Role `STABILIZER`)** : $Q=0.30, Z=1.25, H=8\text{ barres}$ (4.0h), Magic `20261015`, Cap `0.50 lot`. $WR=59.29\%$, $+0.46\text{ bps/trade}$.
* **Sécurités Durcies Inviolables v3.40** :
  - **Cold-Boot Freshness Guard** : Initialisation stricte `ExtLastBarTime = iTime(_Symbol, ExtEffTimeframe, 0)` dans `OnInit()`, et rejet immédiat de tout signal si la bougie clôturée a plus de 300 secondes (`TimeCurrent() - bar_time > InpMaxEntryDelaySec`). Empêche définitivement l'ouverture d'un trade obsolète au redémarrage de la machine si le PC était éteint.
  - **Hard Disaster Stop-Loss Serveur (`InpUseHardTPSL = true`)** : Transmission obligatoire au serveur Deriv d'un Hard Stop-Loss natif à l'ouverture du trade à $2.50\times\text{ATR20}$ et d'un Take-Profit à $4.00\times\text{ATR20}$, protégeant le compte contre tout crash matériel ou coupure réseau.
  - **Profit Lock dynamique anti-spam (`InpUseTrailingLock = true`)** : Calculé strictement sur l'**ATR de la bougie clôturée (`shift=1`)**, avec normalisation exacte `NormalizePrice` (`SYMBOL_TRADE_TICK_SIZE` + `_Digits`), garde `> 0.5 * _Point`, vérification `SYMBOL_TRADE_STOPS_LEVEL` / `FREEZE_LEVEL` et cooldown de `10 s` (zéro rafale `PositionModify` serveur).
  - **Priorité d'exécution dans `OnTick()`** : `ManageOpenPositions()` est appelé **avant** le coupe-circuit journalier (`InpMaxDailyLossPct = 3.0%`) pour qu'aucune position ouverte ne devienne orpheline.
  - **Remplissage dynamique & Slippage** : Sélection automatique `ORDER_FILLING_IOC` / `FOK` / `RETURN` et `InpSlippagePoints = 50`.

---

## 3. CARTOGRAPHIE STRUCTURELLE DU CODEBASE

```text
bot-quant-/
├── AGENT.md                                           <- Le présent guide opérationnel pour IA
├── MEMOIRE_MAITRE_NOUVELLE_CONVERSATION.md            <- Mémoire intégrale & prompt de reprise pour nouvelle session
├── README.md                                          <- Présentation générale claire et accessible (sans formules complexes)
├── CHANGELOG_AND_HISTORY.md                           <- Historique chronologique complet (Sections 1 à 14.8)
├── LICENSE                                            <- Licence MIT
│
├── docs/                                              <- Documentation scientifique, audits & registres formels
│   ├── ETAT_DE_LA_VERITE.md                           <- Registre central des hypothèses vérifiées / réfutées
│   ├── DATA_FORENSIC_REPORT.md                        <- Audit forensique du Data Curator (3 420 trades, logs, clock drift)
│   ├── CODE_ARCHITECTURE_AUDIT.md                     <- Audit de code MQL5/ONNX du Quant Dev (failles VULN-01 à VULN-06)
│   ├── ADVERSARIAL_VERDICT_REPORT.md                  <- Verdict hostile /boost (1,68M ticks, DSR=0.0000, 5 portes)
│   ├── RAPPORT_AUDIT_INSTITUTIONNEL_QUANT_POD_DERIV.md<- Synthèse exécutive de l'audit Quant Pod L99
│   ├── RAPPORT_FORENSIQUE_63H_V25_V75_BOOMCRASH.md    <- Analyse forensique des 63h live (25/10 au 28/10)
│   ├── GUIDE_PEDAGOGIQUE_L1_MATHS_...md               <- Synthèse pédagogique niveau L1 Mathématiques
│   ├── RAPPORT_OPTIMISATION_TIMEFRAME_ET_...md        <- Preuve empirique multi-TF et grille de probabilité
│   ├── RAPPORT_SCANNER_EV_CONTRATS_DERIV.md           <- Bilan de l'évaluation de 349 contrats options
│   ├── AUDIT_COMPLET_MODELES_ET_BOTS_DERIV.md         <- Audit complet des modèles et bots Deriv
│   ├── RAPPORT_AUDIT_L99_EXPERT_V8_FABLE_VS_ARGON.md  <- Comparaison architecturale Fable vs Argon (v8)
│   └── ENCYCLOPEDIE_TOME_2_...md                      <- Manuel mathématique et microstructures (Tomes I & II)
│
├── research/
│   └── audit_2026-10-25/                              <- Scripts d'audit empirique indépendants
│       ├── audit_boomcrash_micro.py                   <- Validation loi géométrique sans mémoire (6.8M ticks)
│       ├── sim_v830_ticks.py                          <- Simulation tick par tick de l'inversion convexe
│       ├── forensic_v8_live.py                        <- Décomposition des trades live réels
│       ├── audit_vol_squeeze.py                       <- Audit 6.3 ans (56 046 barres H1) V25/V75
│       └── deriv_contracts_ev_report.json             <- Résultats JSON du scanner WebSocket
│
├── src/
│   ├── models/                                        <- Modèles d'intelligence artificielle ONNX
│   │   ├── boom_crash_meta_brain.onnx                 <- MLP 14 features Boom & Crash (50 Ko)
│   │   ├── onnx_model_metadata.json                   <- Définition des 14 variables de survie
│   │   ├── c2_vol_filter_v25.onnx                     <- GBDT dédié Volatility 25 (1s) H1 Hold=4h
│   │   ├── c2_vol_filter_v75.onnx                     <- GBDT dédié Volatility 75 (1s) H1 Hold=4h
│   │   ├── c2_vol_filter.onnx                         <- Modèle GBDT générique baseline
│   │   └── c2_vol_filter_metadata.json                <- Métriques d'entraînement 60/20/20
│   │
│   ├── mql5/                                          <- Robots MetaTrader 5 (MQL5)
│   │   ├── Deriv_VolSqueeze_Breakout_EA_v3.mq5        <- Moteur Track 2 ACTIF (v3.30 Hardened, Profit Lock, H1)
│   │   ├── Deriv_VolSqueeze_Breakout_EA_v3.ex5        <- Binaire compilé v3.30 (57 352 octets)
│   │   ├── DerivBoomCrashHFT_v830_Ultimate.mq5        <- Moteur Track 1 EN PAUSE (v8.30, archivé pour référence)
│   │   └── ... (Archives historiques v6, v7, v8, VolSqueeze v1)
│   │
│   └── python/                                        <- Moteurs de recherche et optimisation
│       ├── optimize_timeframe_and_prob_grid.py        <- Optimisation multi-TF et grille de probabilité
│       ├── train_volatility_colab.py                  <- Pipeline d'entraînement chronologique 60/20/20
│       ├── deriv_fair_value_scanner.py                <- Scanner live WebSocket des contrats Deriv
│       └── colab_ai/real_live_spreads_mt5.json        <- Référentiel des spreads réels live
│
├── archive/
│   ├── models_legacy/                                 <- Anciens modèles ONNX archivés
│   └── profiles_legacy/                               <- Anciens profils MT5 archivés
│
└── tests/
    └── verify_step1_and_step4.py                      <- Suite de tests unitaires et validation d'intégrité
```

---

## 4. SKILL INSTITUTIONNEL QUANT POD (`/agent-quant-pod`)

Outre ce dépôt Git, la machine locale dispose du skill global **Quant Pod Institutionnel L99** installé dans :
* **Dossier Maître** : `C:\Users\CHRIST\.gemini\config\skills\quant-pod\`
* **Alias Slash Command** : `C:\Users\CHRIST\.gemini\config\skills\agent-quant-pod\SKILL.md`
* **Scripts Scientifiques Embarqués** :
  1. `C:\Users\CHRIST\.gemini\config\skills\quant-pod\scripts\deriv_quant_engine.py` (Extraction ticks MT5, audit loi de Poisson, test des séquences Wald-Wolfowitz, exposant de Hurst R/S, analyse spectrale de Welch, NIST SP 800-90B Min-Entropy, Berlekamp-Massey, détecteur CUSUM/SPRT pour DSI, Signatures de Chemins de Lévy 2D, probabilité analytique Accumulators).
  2. `C:\Users\CHRIST\.gemini\config\skills\quant-pod\scripts\quant_scientific_arsenal.py` (Différenciation fractionnaire FFD `find_min_ffd_d`, demi-vie Ornstein-Uhlenbeck, Deflated Sharpe Ratio `deflated_sharpe_ratio`, Purged & Embargoed K-Fold CV, Volatility Targeting et Fractional Kelly).
* **Références des 11 Familles Deriv** : `C:\Users\CHRIST\.gemini\config\skills\quant-pod\references\deriv_11_families.md`.

> **Règle d'Orchestration `/teamwork` + `/boost`** :
> Lorsque l'utilisateur invoque `/agent-quant-pod` ou demande un travail en équipe, l'agent principal ne doit **jamais** tout exécuter seul dans un fil unique. Il doit obligatoirement créer et déléguer le travail à des sous-agents spécialisés via `define_subagent` et `invoke_subagent` (`QuantDataCurator`, `QuantCodeAuditor`, `QuantAdversarialValidator`, `QuantAlphaResearcher`, `QuantRiskAllocator`), attendre leurs rapports et synthétiser leurs conclusions.

---

## 5. TOOLCHAIN & COMMANDES OFFICIELLES

### 5.1 Compilation et Déploiement d'un Robot MQL5
*Astuce critique : Toujours copier le `.mq5` dans le dossier `MQL5\Experts` du terminal avant de compiler avec `metaeditor64.exe`, puis synchroniser le `.ex5` généré vers `src/mql5/` dans le dépôt Git.*

```powershell
# 1. Copier la source vers MT5 Experts
Copy-Item "C:\Users\CHRIST\Desktop\IA\ANTIGRAVITY\projets\general project   quant bot deriv\src\mql5\Deriv_VolSqueeze_Breakout_EA_v3.mq5" "C:\Users\CHRIST\AppData\Roaming\MetaQuotes\Terminal\FB9A56D617EDDDFE29EE54EBEFFE96C1\MQL5\Experts\Deriv_VolSqueeze_Breakout_EA_v3.mq5" -Force

# 2. Compiler via metaeditor64.exe (Code de sortie 1 = Succès)
& "C:\Program Files\MetaTrader 5 Terminal\metaeditor64.exe" /compile:"C:\Users\CHRIST\AppData\Roaming\MetaQuotes\Terminal\FB9A56D617EDDDFE29EE54EBEFFE96C1\MQL5\Experts\Deriv_VolSqueeze_Breakout_EA_v3.mq5"

# 3. Synchroniser le binaire .ex5 vers le dépôt Git
Copy-Item "C:\Users\CHRIST\AppData\Roaming\MetaQuotes\Terminal\FB9A56D617EDDDFE29EE54EBEFFE96C1\MQL5\Experts\Deriv_VolSqueeze_Breakout_EA_v3.ex5" "C:\Users\CHRIST\Desktop\IA\ANTIGRAVITY\projets\general project   quant bot deriv\src\mql5\Deriv_VolSqueeze_Breakout_EA_v3.ex5" -Force
```

---

## 6. PIÈGES FRÉQUENTS ET SOLUTIONS (GOTCHAS)

1. **Ne jamais fermer le terminal MT5 de l'utilisateur par mégarde** :
   - En Python, appeler `mt5.initialize()` suivi de `mt5.shutdown()` lorsque MT5 n'était pas ouvert ou selon le contexte peut interagir avec l'instance. Préférer la lecture directe des fichiers journaux (`MQL5\Logs\YYYYMMDD.log` et `Logs\YYYYMMDD.log`) en mode binaire partagé (`open(..., 'rb').read().decode('utf-16', errors='ignore')`) lorsque l'on souhaite inspecter l'activité sans toucher au processus `terminal64.exe`.
2. **Terminal MT5 fantôme en arrière-plan (`MainWindowHandle = 0`)** :
   - Si l'utilisateur signale que MT5 ne s'ouvre pas quand il clique sur l'icône du bureau (`C:\Users\CHRIST\Desktop\Deriv MT5.lnk`), vérifier avec `Get-Process terminal64` s'il existe un processus bloqué sans fenêtre (`MainWindowTitle` vide en tâche de fond) et le terminer proprement avec `Stop-Process -Name terminal64 -Force`.
3. **Encodage UTF-16 des logs MT5** :
   - Toujours décoder les fichiers `.log` et `.chr` de MT5 avec `encoding='utf-16', errors='ignore'`.
