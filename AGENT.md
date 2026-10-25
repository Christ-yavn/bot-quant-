# GUIDE OPÉRATIONNEL & PROTOCOLE POUR AGENTS IA (AGENT.md)
## Cadre Quantitatif, Invariants Mathématiques, Architecture & Procédures d'Exécution

Ce document constitue le **point d'entrée unique et obligatoire** pour tout agent d'intelligence artificielle (Antigravity, Claude Code, Gemini, Cursor, ChatGPT ou tout sous-agent automatisé) intervenant sur le dépôt `Christ-yavn/bot-quant-`.

---

## 1. MISSION DU RÉPERTOIRE & OBJECTIFS SYSTÈME

Le projet **QUANT BOT DERIV** est un environnement d'ingénierie quantitative, d'audit économétrique haute fréquence et de trading algorithmique appliqué aux indices synthétiques continus du courtier **Deriv** :
1. **Indices Boom & Crash (Track 1 — Haute Fréquence Ticks)** : Sondes convexes sur sauts de prix (`SELL` Crash / `BUY` Boom) conditionnées par l'épuisement de Markov, filtrées par un réseau neuronal ONNX à 14 variables et protégées par une porte d'espérance mathématique (EV Gate).
2. **Indices de Volatilité Continue (Track 2 — Breakout H1)** : Détecteur de compression de volatilité H1 ($\sigma_{20} \le q_{0.25}$) et cassure directionnelle ($|Z| \ge 1.50$), filtré par des modèles GBDT ONNX dédiés par actif (`c2_vol_filter_v25.onnx` et `c2_vol_filter_v75.onnx`) avec maintien temporel strict de 4 heures.
3. **Scanner de Juste Valeur WebSocket (Track 3 — Arbitrage Dérivés)** : Évaluation temps réel en forme fermée de 349 contrats options Deriv via API WebSocket live.

---

## 2. LES 7 INVARIANTS ABSOLUS DU PROJET (RÈGLES INVIOLABLES)

Tout agent opérant sur ce code **doit respecter sans exception** les sept lois fondamentales suivantes :

### Règle 1 : Vérité du Spread Live (`SymbolInfoTick` vs `CopyTicks`)
* L'historique `CopyTicks` de MetaTrader 5 sous-estime le spread réel exécuté d'un facteur 7 à 11 (ex. Crash 600 affiche $0.297\text{ pt}$ dans l'historique contre $3.281\text{ pts}$ en direct).
* **Interdiction absolue** de calculer une rentabilité, un backtest ou un filtre sans déduire le spread réel live fourni par `SymbolInfoTick(symbol, tick)` ou le référentiel `src/python/colab_ai/real_live_spreads_mt5.json`.

### Règle 2 : Principe d'Archivage Additif Immuable
* **Ne jamais supprimer ni écraser** les anciens codes, anciens manuels ou anciens modèles ONNX.
* Les versions historiques (`v6`, `v7`, `v8`, `VolSqueeze v1`, etc.) doivent rester intactes dans `archive/` ou dans `src/mql5/` pour garantir la reproductibilité forensique et l'historique du projet.

### Règle 3 : Alignement Strict des Vecteurs ONNX (Features MQL5 $\leftrightarrow$ Python)
* **Track 1 (Boom/Crash)** : Vecteur d'entrée strictement égal à `float[1][14]`, aligné dans l'ordre exact de `src/models/onnx_model_metadata.json` (`symbol_id`, `is_boom`, `spike_amp_norm`, `tau1..3`, `h_fast`, `h_med`, `h_slow`, `c60`, `c300`, `post3_vel`, `be_ticks`, `cost_ratio`).
* **Track 2 (Volatilité H1)** : Vecteur d'entrée strictement égal à `float[1][7]`, aligné dans l'ordre exact : `vol_ratio`, `impulse_z`, `direction`, `levy_area`, `spread_to_atr`, `skew20`, `kurt20`.

### Règle 4 : Cohérence d'Échelle des Probabilités (Base 1.0 vs Base 100.0)
* Les classifieurs ONNX génèrent une probabilité $P \in [0.0 ; 1.0]$.
* Dans les paramètres MQL5, `InpMinWinProbability` doit toujours être compris entre `0.0` et `1.0` (ex. `0.42` pour 42%, `0.50` pour 50%).
* `Deriv_VolSqueeze_Breakout_EA_v3.mq5` (`v3.20`) intègre un mécanisme de sécurité : `if (prob > 1.0) prob /= 100.0;`. Tout nouveau code doit obligatoirement préserver cette garde.

### Règle 5 : Chemins MT5 & Profils de Graphiques Déverrouillés
* Deux installations MT5 existent sur cette machine. L'installation dédiée à Deriv est exclusivement :
  `C:\Program Files\MetaTrader 5 Terminal\terminal64.exe`
  Répertoire de données : `C:\Users\CHRIST\AppData\Roaming\MetaQuotes\Terminal\FB9A56D617EDDDFE29EE54EBEFFE96C1`
  Compte de test : `32449166` (`Deriv-Demo`).
* Les fichiers de profils graphiques (`chart01.chr`, `chart02.chr`, `chart03.chr`) doivent obligatoirement posséder `expertmode=5` (Trading automatique = ACTIF, DLL = ACTIF). Si `expertmode=1`, aucun ordre ne peut être exécuté par le terminal.

### Règle 6 : Pas de Sur-Optimisation ni de Seuils Hors-Support GBDT
* Les arbres de décision GBDT peu profonds (`max_depth=3`) produisent des probabilités régularisées bornées dans $[0.34 ; 0.59]$.
* Un seuil `P_min >= 0.60` (ou 70%) entraîne mathématiquement **zéro trade**. Les seuils optimaux empiriques démontrés sur 250 000+ barres sont :
  - `Volatility 25 (1s)` : `P_min = 0.42` (`Hold = 4h`, $+3\,241.5\text{ bps}$, $t = +3.51$).
  - `Volatility 75 (1s)` : `P_min = 0.50` (`Hold = 4h`, $+4\,120.8\text{ bps}$, $t = +2.48$) ou `P_min = 0.54` (haute précision, $WR = 65.6\%$, $t = +3.15$).

### Règle 7 : Timeframe H1 Absolue pour la Gamme Volatilité
* L'évaluation empirique multi-temporelle (`M5`, `M15`, `M30`, `H1`, `H4`) démontre que baisser la timeframe à `M15` ou `M5` détruit la rentabilité ($-558\text{ bps}$ à $-2\,691\text{ bps}$) car le spread fixe dévore l'amplitude $\sigma\sqrt{\Delta t}$.
* L'unité de temps opérationnelle de `Deriv_VolSqueeze_Breakout_EA_v3` est strictement **`PERIOD_H1`** avec un maintien de position fixé à **4 heures** (`InpMaxHoldBars = 4`).

---

## 3. CARTOGRAPHIE STRUCTURELLE DU CODEBASE

```text
bot-quant-/
├── AGENT.md                                           <- Le présent guide opérationnel pour IA
├── README.md                                          <- Présentation générale claire et accessible
├── CHANGELOG_AND_HISTORY.md                           <- Historique chronologique complet (v1 -> v8.30)
├── LICENSE                                            <- Licence MIT
│
├── docs/                                              <- Documentation scientifique & registres formels
│   ├── ETAT_DE_LA_VERITE.md                           <- Registre central des hypothèses vérifiées / réfutées
│   ├── GUIDE_PEDAGOGIQUE_L1_MATHS_...md               <- Synthèse pédagogique niveau L1 Mathématiques
│   ├── RAPPORT_OPTIMISATION_TIMEFRAME_ET_...md        <- Preuve empirique multi-TF et grille de probabilité
│   ├── RAPPORT_SCANNER_EV_CONTRATS_DERIV.md           <- Bilan de l'évaluation de 349 contrats options
│   └── ENCYCLOPEDIE_TOME_2_...md                      <- Manuel mathématique et microstructures
│
├── research/
│   └── audit_2026-10-25/                              <- Scripts d'audit empirique indépendants
│       ├── AUDIT_COMPLET_MODELES_ET_BOTS_DERIV.md     <- Rapport d'audit intégral du 25/10/2026
│       ├── audit_boomcrash_micro.py                   <- Validation loi géométrique sans mémoire (6.8M ticks)
│       ├── sim_v830_ticks.py                          <- Simulation tick par tick de l'inversion convexe
│       ├── forensic_v8_live.py                        <- Décomposition des 648 trades live réels
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
│   │   ├── DerivBoomCrashHFT_v830_Ultimate.mq5        <- Moteur Track 1 (Hardened B1-B9 + 5 sondes)
│   │   ├── Deriv_VolSqueeze_Breakout_EA_v3.mq5        <- Moteur Track 2 (v3.20, H1 Hold=4h, Dashboard)
│   │   └── ... (Archives historiques v6, v7, v8, etc.)
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

## 4. TOOLCHAIN & COMMANDES OFFICIELLES

### 4.1 Compilation d'un Robot MQL5
La compilation s'effectue via l'utilitaire `metaeditor64.exe` de l'installation MetaTrader 5 Terminal.
*Note : `metaeditor64.exe` renvoie le code de sortie `1` en cas de succès (nombre de fichiers compilés).*

```powershell
# Compiler Deriv_VolSqueeze_Breakout_EA_v3
& "C:\Program Files\MetaTrader 5 Terminal\metaeditor64.exe" /compile:"C:\Users\CHRIST\Desktop\IA\ANTIGRAVITY\projets\general project   quant bot deriv\src\mql5\Deriv_VolSqueeze_Breakout_EA_v3.mq5" /log:"compile_v3.log"

# Compiler DerivBoomCrashHFT_v830_Ultimate
& "C:\Program Files\MetaTrader 5 Terminal\metaeditor64.exe" /compile:"C:\Users\CHRIST\Desktop\IA\ANTIGRAVITY\projets\general project   quant bot deriv\src\mql5\DerivBoomCrashHFT_v830_Ultimate.mq5" /log:"compile_v830.log"
```

### 4.2 Exécution de l'Optimisation Multi-Timeframes & Probabilités
```powershell
cd "C:\Users\CHRIST\Desktop\IA\ANTIGRAVITY\projets\general project   quant bot deriv"
python src/python/optimize_timeframe_and_prob_grid.py
```

### 4.3 Exécution du Scanner WebSocket Live Deriv
```powershell
cd "C:\Users\CHRIST\Desktop\IA\ANTIGRAVITY\projets\general project   quant bot deriv"
python src/python/deriv_fair_value_scanner.py
```

### 4.4 Exécution de la Suite de Validation d'Intégrité
```powershell
cd "C:\Users\CHRIST\Desktop\IA\ANTIGRAVITY\projets\general project   quant bot deriv"
python tests/verify_step1_and_step4.py
```

---

## 5. DÉTAILS D'IMPLÉMENTATION DES DEUX MOTEURS DE TRADING

### 5.1 Track 1 : `DerivBoomCrashHFT_v830_Ultimate.mq5`
* **Logique de position** : Purement convexe (`SELL` sur indices Crash / `BUY` sur indices Boom) pour capter le saut favorable.
* **Condition d'entrée** : Détection d'épuisement sans saut sur $N \ge \theta_{\text{eff}}$ ticks, validée par la probabilité de saut ONNX mise à l'échelle de l'horizon :
  $$P_{\text{spike}}(M^*) = 1 - P_{\text{surv}}^{M^* / (\text{be\_ticks} + 15)}$$
* **Gestion du risque** : Horizon temporel analytique strict $M^* = 60\text{ ticks}$ ou $65\text{ secondes}$ serveur (`POSITION_TIME_MSC`), stop d'urgence à $-0.35\text{ USD}$.
* **Réglage actif en phase de test** :
  - `InpMinEvUsd = -0.20$`
  - `InpThetaEffBaseMult = 0.85`
  - `InpSymbolUniverse = UNIVERSE_GOLDEN_7_LIVE_WINNERS`
  - *Comportement garanti* : Autorise les 5 sondes à faible spread (`Crash 500`, `Boom 500`, `Crash 1000`, `Boom 600`, `Boom 900`) et maintient le verrouillage strict sur les indices toxiques à fort spread (`Crash 600` et `Crash 900`).

### 5.2 Track 2 : `Deriv_VolSqueeze_Breakout_EA_v3.mq5` (`v3.20`)
* **Cadence temporelle** : Évaluation uniquement à la clôture de chaque bougie H1 (`IsNewBar()` sur `PERIOD_H1`).
* **Condition de compression (Squeeze)** : L'écart-type des rendements sur 20 barres doit être inférieur ou égal au premier quartile historique :
  $$\sigma_{20} \le q_{0.25}$$
* **Condition de cassure (Breakout)** : Le rendement de la bougie précédente normalisé par la volatilité doit dépasser le seuil d'impulsion :
  $$|Z| = \frac{|r_{1\text{h}}|}{\sigma_{20}} \ge 1.50$$
* **Filtre décisionnel IA** : Sélection automatique du modèle dédié selon le symbole :
  - `Volatility 25 (1s)` : charge `c2_vol_filter_v25.onnx`, valide si $P(\text{Win}) \ge 0.42$.
  - `Volatility 75 (1s)` : charge `c2_vol_filter_v75.onnx`, valide si $P(\text{Win}) \ge 0.50$.
* **Sortie de position** : Clôture déterministe à l'issue de 4 barres H1 exactement (`InpMaxHoldBars = 4`), soit 4 heures de maintien.
* **Supervision graphique** : Dashboard temps réel rendu sur le graphique via `RenderVolSqueezeDashboard()` et journalisation structurée `[v3.20 BAR EVAL]` dans l'onglet Experts.

---

## 6. PIÈGES FRÉQUENTS ET SOLUTIONS (GOTCHAS)

1. **Terminal MT5 en arrière-plan (Session 0)** :
   - L'appel WMI `Win32_Process.Create` lance le processus dans la Session 0 (non interactive). Pour ouvrir l'interface visible sur le bureau de l'utilisateur, utiliser `explorer.exe "C:\Program Files\MetaTrader 5 Terminal\terminal64.exe"`.
2. **Buffering des journaux MQL5** :
   - MetaTrader 5 met en mémoire tampon les écritures dans `MQL5\Logs\YYYYMMDD.log`. L'absence immédiate de nouvelles lignes dans le fichier sur disque ne signifie pas que le bot ne tourne pas : le terminal vide son tampon périodiquement ou lors de la consultation des journaux.
3. **Erreur d'encodage console Windows** :
   - Les fichiers journaux de MT5 sont encodés en `UTF-16 Little Endian`. Lors de leur lecture via Python, toujours utiliser `.decode('utf-16', errors='ignore')` pour éviter l'erreur `UnicodeEncodeError: 'charmap'`.
4. **Conflit de deux installations MT5** :
   - Ne jamais lancer `C:\Program Files\MetaTrader 5\terminal64.exe` (compte Forex standard `114381370`). Toujours utiliser `C:\Program Files\MetaTrader 5 Terminal\terminal64.exe` (compte Deriv `32449166`).

---

## 7. RÉFÉRENCES SCIENTIFIQUES DU DÉPÔT

Pour tout approfondissement théorique avant modification d'un algorithme :
* [**`docs/ETAT_DE_LA_VERITE.md`**](file:///C:/Users/CHRIST/Desktop/IA/ANTIGRAVITY/projets/general%20project%20%20%20quant%20bot%20deriv/docs/ETAT_DE_LA_VERITE.md) : Registre officiel des théorèmes Doob, Hawkes et tests GBM.
* [**`docs/GUIDE_PEDAGOGIQUE_L1_MATHS_AUDIT_ET_REPARATIONS_2026.md`**](file:///C:/Users/CHRIST/Desktop/IA/ANTIGRAVITY/projets/general%20project%20%20%20quant%20bot%20deriv/docs/GUIDE_PEDAGOGIQUE_L1_MATHS_AUDIT_ET_REPARATIONS_2026.md) : Démonstrations complètes adaptées au formalisme mathématique fondamental.
* [**`docs/RAPPORT_OPTIMISATION_TIMEFRAME_ET_PROBABILITE_ONNX.md`**](file:///C:/Users/CHRIST/Desktop/IA/ANTIGRAVITY/projets/general%20project%20%20%20quant%20bot%20deriv/docs/RAPPORT_OPTIMISATION_TIMEFRAME_ET_PROBABILITE_ONNX.md) : Données brutes de performance multi-TF et grilles de rentabilité empiriques.
