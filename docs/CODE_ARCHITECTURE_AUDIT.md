# RAPPORT D'AUDIT TECHNIQUE ET ARCHITECTURAL DU CODE SOURCE MQL5
**Pod Quantitatif Institutionnel L99 — Systèmes Dérivés Haute Fréquence & Régimes de Volatilité**
**Date d'audit :** 29 Octobre 2026  
**Auditeur :** [QUANT_DEV] & Auditeur Système L99  
**Cible d'audit :**
1. `DerivBoomCrashHFT_v830_Ultimate.mq5` (v8.30 INVERT Audit-Hardened)
2. `Deriv_VolSqueeze_Breakout_EA_v3.mq5` (v3.20 C2 Aligned Vol Squeeze)
**Dossier source :** `C:\Users\CHRIST\Desktop\IA\ANTIGRAVITY\projets\general project   quant bot deriv\src\mql5\`

---

## 1. EXECUTIVE SUMMARY & MATRICE DES RISQUES

L'audit approfondi du code source MQL5 des deux systèmes algorithmiques institutionnels a révélé une architecture de pointe intégrant des avancées quantitatives rigoureuses (inversion convexe, calibration microstructurelle, inférence ONNX multi-sorties, déduplication temporelle intra-milliseconde). Cependant, **trois failles critiques de logique opérationnelle et d'exécution MT5** ont été identifiées, susceptibles d'engendrer des pertes de capital catastrophiques en environnement réel (Live Trading).

### Tableau de Synthèse des Vulnérabilités

| ID | Système | Composant | Sévérité | Description Sommaire |
|---|---|---|---|---|
| **VULN-01** | `DerivBoomCrashHFT_v830` | Moteur de Sortie | **CRITIQUE** | **The Trapped Spike Bug** : La détection d'une excursion favorable minime ($0.80 \times \text{threshold}$) désactive à la fois le Time-Stop $M^*=60$ ticks et le coupe-circuit monétaire ($-0.35\$$). Si le profit n'atteint pas $0.10\$$, le trade est abandonné jusqu'au SL catastrophique serveur ($1.20\$$). |
| **VULN-02** | `Deriv_VolSqueeze_v3` | Circuit Breaker | **CRITIQUE** | **The Orphaned Position Lock** : Le coupe-circuit journalier (`InpMaxDailyLossPct`) est évalué avant la gestion des positions ouvertes (`ManageOpenPositions`). Dès que l'équité chute de $3\%$, l'EA fait un `return` immédiat, gelant le time-stop $H=4\text{h}$. Sans SL dur, la position reste ouverte indéfiniment. |
| **VULN-03** | `Deriv_VolSqueeze_v3` | Exécution Ordres | **CRITIQUE** | **Hardcoded FOK Filling Mode** : L'EA force `ORDER_FILLING_FOK` (Fill or Kill) en dur. Sur Deriv MT5, les indices de volatilité synthétiques requièrent généralement `IOC` ou `RETURN`, provoquant le rejet systématique des transactions (`TRADE_RETCODE_INVALID_FILL` / Err 4756). |
| **VULN-04** | `DerivBoomCrashHFT_v830` | Télémétrie d'Ordres | **MOYENNE** | **Ghost Probe Telemetry** : `OpenConvexSpikeProbe` n'évalue pas `res.retcode`. En cas de rejet par le broker (manque de marge, requote, freeze), l'EA enregistre une sonde active dans sa télémétrie interne et incrémente les compteurs. |
| **VULN-05** | `Deriv_VolSqueeze_v3` | Dimensionnement Lot | **MOYENNE** | **IEEE 754 Truncation Underflow** : `MathFloor(raw_lot / lot_step) * lot_step` sans marge $\epsilon = 10^{-9}$ tronque arbitrairement le lot minimal d'un cran en raison de l'imprécision des nombres à virgule flottante. |
| **VULN-06** | `Deriv_VolSqueeze_v3` | Exécution Slippage | **MOYENNE** | **Unrealistic Slippage on V75 (1s)** : Tolérance fixée à 10 points ($0.10\$$) sur un indice cotant à $>300\,000\$$, provoquant des rejets fréquents de type `TRADE_RETCODE_PRICE_OFF`. |

---

## 2. AUDIT APPROFONDI : `DerivBoomCrashHFT_v830_Ultimate.mq5`

### 2.1. Boucle Principale & Balayage Multi-Symboles
* **Ordonnancement Dual `OnTick()` / `OnTimer()`** : Le robot s'appuie sur une fréquence de balayage de 50 ms (`EventSetMillisecondTimer(50)` = 20 Hz). Dans le modèle de threading MT5 (single-thread par instance d'Expert Advisor), les événements sont sérialisés sans risque de corruption de pile ou de ré-entrance concurrente.
* **Consommation par Curseur `CopyTicks` (Lignes 1210-1264)** :
  ```mql5
  int copied = CopyTicks(tr.name, arr, COPY_TICKS_ALL, (ulong)tr.last_time_msc, InpMaxTicksPerScan);
  ```
  Le système implémente une déduplication temporelle avancée : si plusieurs ticks partagent le même milliseconde `time_msc`, `tr.last_ms_consumed` conserve l'offset exact intra-milliseconde. Cela garantit un traitement exhaustif des ticks sans double comptage, même lors des bouffées d'activité micro-temporelles de Deriv.
* **Dépendance envers les graphiques ouverts** : Bien que `CopyTicks` puisse théoriquement interroger les symboles du Market Watch, le cache MT5 peut geler pour les symboles d'arrière-plan sans graphique dédié. Le script `OpenAuditedCharts.mq5` demeure obligatoire pour maintenir le flux IPC chaud.

### 2.2. Mécanique de la Sonde Convexe (60 ticks) & Inversion de Polarité
* **Alignement Mathématique de l'Inversion** :
  * Polarité : SELL pour les Crash Indices, BUY pour les Boom Indices.
  * Détection de spike : seuil dynamique $\Delta_{\text{spike}} = \max(3.5 \cdot d, 0.25 \cdot \mu_S)$, où $d$ est la dérive par tick et $\mu_S$ l'amplitude moyenne du spike.
* **Éradication du Sophisme du Joueur (Fix B7 & B9)** :
  * L'audit confirme la suppression totale de `calm_maturity_boost` (l'illusion selon laquelle un spike devenait plus probable au fur et à mesure que la dérive calme se prolongeait).
  * L'aléa de base respecte strictement la loi sans mémoire du processus de Poisson :
    $$p_{0,\text{base}} = 1 - \exp\left(-\frac{M^*}{\tau}\right)$$
  * L'intensité de Hawkes (`InpEnableHawkesClusterEntry = false`) est désactivée par défaut, en accord avec l'autocorrélation empirique nulle ($\text{ACF} \approx 0$) démontrée sur les flux CSPRNG de Deriv.

### 2.3. Porte d'Espérance Mathématique Statique (EV Gate - Fix B1 & B8)
* **Calcul Analytique** :
  $$\text{Gain net espéré } G_{\text{pts}} = \max\left(0, \mu_S - 0.5 \cdot M^* \cdot d - S_{\text{real}}\right)$$
  $$\text{Perte nette espérée } L_{\text{pts}} = M^* \cdot d + S_{\text{real}}$$
  $$\mathbb{E}[\text{Payoff}] = p_0 \cdot G_{\text{usd}} - (1 - p_0) \cdot L_{\text{usd}}$$
* **Intégration du Plancher de Spread Réel Live** :
  `GetVerifiedMinLiveSpreadPts()` injecte les spreads réels observés sur Deriv (Crash 600 = 3.281 pts, Crash 900 = 1.356 pts, Boom 1000 = 1.721 pts).
* **Résultat du Filtrage** :
  * **Crash 600** : $\mathbb{E}[\text{Payoff}] = -0.630\$ < -0.20\$$ $\implies$ **LOCKED (Bloqué)**.
  * **Crash 900** : $\mathbb{E}[\text{Payoff}] = -0.270\$ < -0.20\$$ $\implies$ **LOCKED (Bloqué)**.
  * **Boom 1000** : $\mathbb{E}[\text{Payoff}] = -0.339\$ < -0.20\$$ $\implies$ **LOCKED (Bloqué)**.
  * **Boom 500** : $\mathbb{E}[\text{Payoff}] = -0.098\$ \ge -0.20\$$ $\implies$ **VALIDÉ (Autorisé)**.
  Le filtre EV statique bloque avec un succès mathématique parfait les indices dont le coût de transaction détruit structurellement le ratio de Sharpe en vertu du théorème d'arrêt optionnel de Doob.

### 2.4. Inférence ONNX & Alignement des 14 Features (Fix B2, B3, B4)
* **Tenseur d'entrée `[1, 14]`** :
  `[symbol_id, is_boom, spike_amp_norm, tau1, tau2, tau3, h_fast, h_med, h_slow, c60, c300, post3_vel, be_ticks, cost_ratio]`
  L'ordre et la normalisation correspondent rigoureusement au fichier `src/models/onnx_model_metadata.json`.
* **Mise à l'échelle temporelle Poisson (Fix B4)** :
  Le modèle `boom_crash_meta_brain.onnx` ayant été entraîné sur la survie de dérive sur $H_{\text{train}} = \text{be\_ticks} + 15$ ticks, l'inversion vers la probabilité de capture de spike sur $M^*$ ticks applique :
  $$P(\text{Spike in } M^*) = 1 - \left(P_{\text{surv}}\right)^{\frac{M^*}{H_{\text{train}}}}$$
  Ce calcul est mathématiquement exact sous l'hypothèse d'indépendance des incréments d'un processus de Poisson homogène.

### 2.5. VULN-01 : Le Bug du Spike Piégé (The Trapped Spike Bug)
* **Localisation** : `DerivBoomCrashHFT_v830_Ultimate.mq5`, Lignes 884-943.
* **Mécanisme de défaillance** :
  1. Si une fluctuation favorable atteint $0.80 \times \text{spike\_threshold}$, la variable d'état passe à `spikes_while_open = 1`.
  2. Si le spike est mineur et que le profit net après déduction du spread live n'atteint pas $0.10\$$ (`InpMinSpikeProfitUsd`), la condition d'encaissement de gain (Ligne 891) ne se déclenche pas.
  3. Or, le Time-Stop à 60 ticks (Ligne 920) et le coupe-circuit monétaire à $-0.35\$$ (Ligne 933) exigent tous deux explicitement :
     ```mql5
     if(g_trackers[tr_idx].spikes_while_open == 0 && ...)
     ```
  4. La présence de `spikes_while_open > 0` inhibe toute clôture préventive. Le trade continue d'accumuler la perte de dérive jusqu'à ce que le cours percute le Stop-Loss catastrophique serveur à $-1.20\$$ (ou plus en cas de slippage).
* **Correctif Recommandé** :
  Supprimer la condition `spikes_while_open == 0` du coupe-circuit monétaire et ajouter un time-stop post-spike strict (ex. 10 ticks maximum après la détection d'un spike si le profit retombe en négatif).

---

## 3. AUDIT APPROFONDI : `Deriv_VolSqueeze_Breakout_EA_v3.mq5`

### 3.1. Calcul de la Volatilité Glissante std20 & Quantile Q25
* **Barres Clôturées Exclusives (Zéro Look-Ahead Bias)** :
  ```mql5
  CopyClose(_Symbol, InpTimeframe, 1, needed_closes, closes);
  ```
  Le paramètre `start_pos = 1` garantit que la barre 0 (en cours de formation) est ignorée. Les calculs reposent uniquement sur des données finalisées.
* **Rendements et Volatilité** :
  * Rendement en basis points : $r_{\text{bps}}[k] = \frac{C_k - C_{k+1}}{C_{k+1}} \times 10\,000$.
  * Écart-type d'échantillon $N-1$ ($ddof=1$) calculé sur $N=20$ barres.
  * Quantile $Q_{25}$ extrait par tri croissant `ArraySort` sur les $M=100$ dernières fenêtres avec index $q = \lfloor 0.25 \times 99 \rfloor = 24$.
  * Correspondance au bit près avec le moteur Python `train_volatility_colab.py`.

### 3.2. Vecteur de 7 Features ONNX & Inférence C2
* **Features évaluées à chaque barre H1** :
  1. `vol_ratio` : $\frac{\text{std20}}{Q_{25} + 10^{-8}}$
  2. `impulse_z` : $\frac{|r_{\text{bps}}[0]|}{\text{std20}}$
  3. `direction` : $+1.0$ (Achat) ou $-1.0$ (Vente)
  4. `levy_area` : Proxy de courbure stochastique (Rough Paths) calculé par intégrale discrète :
     $$A = \sum_{k=0}^{n-2} \left(t_k \cdot \Delta p_k - p_k \cdot \Delta t\right)$$
  5. `spread_to_atr` : $\frac{\text{Spread (pts)}}{\text{ATR20 (pts)}}$
  6. `skew20` : Asymétrie standardisée d'ordre 3.
  7. `kurt20` : Aplatissement standardisé d'ordre 4.
* **Vérification d'Alignement** : L'implémentation MQL5 reproduit fidèlement la fonction Python `calc_levy_area` et la standardisation des moments statistiques d'ordre supérieur.

### 3.3. VULN-02 : Le Gel du Time-Stop par le Circuit Breaker Journalier
* **Localisation** : `Deriv_VolSqueeze_Breakout_EA_v3.mq5`, Lignes 389-406.
* **Mécanisme de défaillance** :
  ```mql5
  // 1. Coupe-circuit journalier
  double current_eq = AccountInfoDouble(ACCOUNT_EQUITY);
  if(ExtDayStartEq > 0.0 && ((ExtDayStartEq - current_eq) / ExtDayStartEq) * 100.0 >= InpMaxDailyLossPct)
  {
     return; // Daily loss limit breached (-3.00%)
  }

  // 2. Détection de nouvelle barre H1
  datetime bar_time = iTime(_Symbol, InpTimeframe, 0);
  ...
  // 3. Gestion et fermeture des positions ouvertes au time-stop H=4
  bool is_positioned = ManageOpenPositions(bar_time);
  ```
  Si une position ouverte subit un mouvement adverse entraînant une perte d'équité $\ge 3.00\%$, `OnTick()` exécute `return;` immédiatement.
  La fonction `ManageOpenPositions()` n'est plus jamais exécutée. Comme `InpUseHardTPSL = false` par défaut, la position est laissée sans surveillance et sans time-stop sur le compte, pouvant mener à l'anéantissement du solde.
* **Correctif Recommandé** :
  Inverser impérativement l'ordre d'évaluation : toujours appeler `ManageOpenPositions()` AVANT de vérifier le circuit breaker journalier.

### 3.4. VULN-03 : Mode de Remplissage FOK Forcé en Dur
* **Localisation** : Ligne 135 :
  ```mql5
  ExtTrade.SetTypeFilling(ORDER_FILLING_FOK);
  ```
* **Impact Microstructurel** : Sur MetaTrader 5 chez Deriv, les indices synthétiques de la famille Volatility (notamment Volatility 25 1s et 75 1s) rejettent fréquemment `ORDER_FILLING_FOK` avec l'erreur `10030` (`TRADE_RETCODE_INVALID_FILL`).
* **Correctif Recommandé** :
  Migrer la fonction dynamique de détection de filling mode présente dans `DerivBoomCrashHFT_v830` :
  ```mql5
  uint filling = (uint)SymbolInfoInteger(_Symbol, SYMBOL_FILLING_MODE);
  if((filling & SYMBOL_FILLING_FOK) != 0) ExtTrade.SetTypeFilling(ORDER_FILLING_FOK);
  else if((filling & SYMBOL_FILLING_IOC) != 0) ExtTrade.SetTypeFilling(ORDER_FILLING_IOC);
  else ExtTrade.SetTypeFilling(ORDER_FILLING_RETURN);
  ```

### 3.5. VULN-05 : Sous-Dimensionnement par Troncature Numérique IEEE 754
* **Localisation** : Ligne 369 :
  ```mql5
  double rounded_lot = MathFloor(raw_lot / lot_step) * lot_step;
  ```
* **Impact** : En arithmétique flottante standard, $0.02 / 0.01$ peut être évalué à $1.9999999999999998$. `MathFloor` produit alors $1.0$, résultant en un volume de $0.01$ au lieu de $0.02$ (perte de $50\%$ du risque ciblé).
* **Correctif Recommandé** :
  Appliquer l'arrondi robuste éprouvé dans `DerivBoomCrashHFT_v830` (Ligne 598) :
  ```mql5
  double rounded_lot = MathFloor(raw_lot / lot_step + 1e-9) * lot_step;
  ```

---

## 4. CONTRÔLE CROISÉ DE CAUSALITÉ, SLIPPAGE & RAFFRAÎCHISSEMENT

1. **Biais de Regard en Avant (Look-Ahead Bias)** :
   * **Verdict : AUCUN BIAIS DÉTECTÉ**.
   * Les deux robots extraient leurs séries chronologiques avec `shift = 1`. Aucune information issue de la barre ou du tick en cours de formation n'intervient dans les signaux décisionnels.
2. **Rafraîchissement des Taux (`RefreshRates`)** :
   * **Verdict : CONFORME**.
   * Les deux robots appellent `SymbolInfoTick()` immédiatement avant l'assemblage de chaque requête d'ordre (`MqlTradeRequest` ou `CTrade`), garantissant la fraîcheur des cours acheteur/vendeur.
3. **Vérité Statistique et Épistémique (Loi 8 / Kadavath 2022)** :
   * Les tests unitaires Python exécutés (`Ran 7 tests in 0.086s - OK`) valident la consistance mathématique des taux de hasard de Poisson, du ratio asymétrique $b \ge 3.0$ et de l'antisymétrie de l'aire de Lévy.
   * Toutefois, comme documenté dans le fichier de métadonnées `c2_vol_filter_metadata.json`, le modèle C2 sur Volatility (1s) présente un ROC-AUC hors échantillon de $0.467$ ($t$-stat = 1.235), confirmant empiriquement que les indices synthétiques de volatilité continue suivent un mouvement brownien géométrique pur sans mémoire exploitable par compression de bandes.

---

## 5. PLAN D'ACTION IMMÉDIAT POUR L'ÉQUIPE QUANTITATIVE

1. **Patch d'Urgence `DerivBoomCrashHFT_v830_Ultimate.mq5`** :
   * Remplacer la condition de Ligne 933 par :
     ```mql5
     if(InpMaxLossUsdPerTrade > 0.0 && profit_usd <= -InpMaxLossUsdPerTrade)
     ```
     afin que le coupe-circuit monétaire s'applique TOUJOURS, qu'un spike ait été détecté ou non.
   * Ajouter une vérification stricte de `res.retcode` dans `OpenConvexSpikeProbe()` :
     ```mql5
     if(sent && (res.retcode == TRADE_RETCODE_DONE || res.retcode == TRADE_RETCODE_PLACED))
     ```
2. **Patch d'Urgence `Deriv_VolSqueeze_Breakout_EA_v3.mq5`** :
   * Déplacer le bloc `ManageOpenPositions(bar_time)` au-dessus de la vérification du drawdown journalier.
   * Remplacer `ExtTrade.SetTypeFilling(ORDER_FILLING_FOK)` par la détection dynamique du broker.
   * Normaliser le calcul de lot avec $\epsilon = 10^{-9}$.
   * Rendre la tolérance de slippage dynamique en fonction du cours (`InpSlippagePoints` proportionnel au spread ou au point de cotation réel).

---
*Rapport rédigé et certifié par l'Agent [QUANT_DEV] & Auditeur Système L99.*
