# MANDAT DE RECHERCHE DOCTORALE & R&D QUANTITATIVE : CONCEPTION DU BOT V8 CONVEXE INVERSÉ (BOOM & CRASH)
## Destinataire : Claude Fable 5 | Réf. : V8-REVERSE-CONVEXITY-001 | Date : 2026-10-20
### Dépôt GitHub Officiel : https://github.com/Christ-yavn/bot-quant-

---

### 1. OBJET DU MANDAT : LA TRANSFORMATION MATHÉMATIQUE DE LA V7 EN V8 RENTABLE
En Phase 1, notre équipe a déployé et exécuté en direct sur compte réel MetaTrader 5 (Deriv-Demo, n° 32449166) le système de trading haute fréquence **DerivBoomCrashHFT_v7.mq5** intégrant un réseau de neurones Perceptron Multi-Couches ONNX entraîné sur 10 000 000 d'événements sans fuite d'information.

Les données médico-légales de la session complète (1 242 trades, 2 484 ordres/deals, 100 000 ticks par symbole) ont été extraites et analysées dans le dossier `data_summaries/v7/`.

Le diagnostic est sans appel :
1. **La v7.00 chassait la dérive calme (Drift Harvesting) :** Elle a généré un taux de réussite phénoménal de **85.91 %** (1 067 victoires pour 175 pertes), mais s'est soldée par une perte nette de **-406.14 USD** car chaque gain moyen n'était que de **+0.20 USD**, tandis que les rares pertes causées par les spikes adverses étaient de **-3.54 USD en moyenne (et jusqu'à -15.85 USD)**. C'est l'archétype même de la **concavité ruineuse (negative skewness / queue épaisse défavorable)**.
2. **La Découverte de l'Inversion :** En simulant l'exact opposé de la logique v7 (parier sur les spikes avec un stop temporel strict de 60 ticks), les 1 067 gains minuscules deviennent 1 067 petites pertes contrôlées (-0.25 USD avg, soit -260.71 USD de coût d'assurance), et les 175 spikes subis deviennent 175 gains massifs (+3.48 USD avg, soit +601.44 USD de profits). Le PnL net bascule à **+$340.73 USD (Profit Factor : 2.31)**.

**Votre mission :** Vous devez auditer l'intégralité des chiffres réels de la v7 ci-dessous, disséquer la logique d'entrée et de sortie, et concevoir l'architecture mathématique, probabiliste et logicielle complète du nouveau robot **`DerivBoomCrashHFT_v8.mq5`** pour que cette inversion devienne un moteur de production rentable et indestructible en trading réel.

---

### 2. TÉLÉMÉTRIE & RÉSULTATS RÉELS DE LA SESSION LIVE V7.00 (1 242 TRADES)

#### A. Métriques Globales du Compte
* **Solde Initial :** 9 927.65 USD
* **Solde Final :** 9 521.51 USD
* **P&L Net Réel v7.00 :** -406.14 USD
* **Trades Totaux :** 1 242 positions fermées (2 484 deals)
* **Taux de Victoire (Win Rate) :** 85.91 % (1 067 gains / 175 pertes)
* **Gains Bruts :** +213.50 USD (Moyenne par gain : +0.20 USD)
* **Pertes Brutes :** -619.64 USD (Moyenne par perte : -3.54 USD)
* **Profit Factor :** 0.34
* **Durée Moyenne de Rétention par Trade :** 239.7 secondes (~4 minutes)
* **Rejets d'Ordres MT5 [Invalid stops] :** 0 (Zéro rejet grâce au TP virtuel à req.tp = 0.0)
* **Coupe-Circuit Journalier :** Arrêt net et automatique à -400 USD (95.2 % du capital préservé).

#### B. Décomposition Complète par Symbole en Live
| Symbole MT5 | Trades | Wins | Losses | Win Rate | Gains Bruts ($) | Pertes Brutes ($) | P&L Net ($) | Profit Factor | Gain Moy. ($) | Perte Moy. ($) | Perte Max ($) | Durée Moy. (s) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Crash 1000 Index** | 130 | 119 | 11 | 91.54 % | +11.71 | -23.05 | **-11.34** | 0.51 | +0.098 | -2.095 | -3.40 | 244.5 s |
| **Crash 500 Index** | 166 | 143 | 23 | 86.14 % | +11.75 | -30.79 | **-19.04** | 0.38 | +0.082 | -1.339 | -2.52 | 249.7 s |
| **Boom 600 Index** | 136 | 113 | 23 | 83.09 % | +11.04 | -42.66 | **-31.62** | 0.26 | +0.098 | -1.855 | -3.56 | 250.3 s |
| **Boom 500 Index** | 208 | 181 | 27 | 87.02 % | +27.37 | -61.11 | **-33.74** | 0.45 | +0.151 | -2.263 | -3.97 | 287.7 s |
| **Boom 900 Index** | 176 | 155 | 21 | 88.07 % | +27.49 | -65.69 | **-38.20** | 0.42 | +0.177 | -3.128 | -4.78 | 338.7 s |
| **Crash 900 Index** | 202 | 176 | 26 | 87.13 % | +38.14 | -125.85 | **-87.71** | 0.30 | +0.217 | -4.840 | -9.60 | 152.5 s |
| **Crash 600 Index** | 224 | 180 | 44 | 80.36 % | +86.00 | -270.49 | **-184.49** | 0.32 | +0.478 | -6.148 | -15.85 | 179.6 s |

#### C. Décomposition par Motif de Clôture (Close Reason)
| Motif de Clôture | Trades | % Trades | Wins | Losses | Win Rate | P&L Net ($) | P&L Moyen ($) | Durée Moy. (s) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **GREEN_CASH_IN** (TP Virtuel atteint) | 980 | 78.9 % | 980 | 0 | 100.0 % | **+192.98** | +0.197 | 147.5 s |
| **SERVER_STOP_LOSS** (Spike plein fouet) | 106 | 8.5 % | 0 | 106 | 0.0 % | **-508.57** | -4.798 | 292.5 s |
| **RECOVERY_BE_GREEN** (Sortie post-spike) | 76 | 6.1 % | 75 | 1 | 98.7 % | **+4.62** | +0.061 | 923.3 s |
| **RECOVERY_2ND_SPIKE_CUT** (2e spike coupé) | 55 | 4.4 % | 0 | 55 | 0.0 % | **-74.03** | -1.346 | 372.5 s |
| **MAX_USD_RISK_CUT** (Plafond max USD) | 13 | 1.0 % | 0 | 13 | 0.0 % | **-35.30** | -2.715 | 152.3 s |
| **TRAILING_GREEN_LOCK** (Trailing stop) | 8 | 0.6 % | 8 | 0 | 100.0 % | **+0.17** | +0.021 | 181.0 s |
| **MARKET_CLOSE_OR_MANUAL** | 4 | 0.3 % | 4 | 0 | 100.0 % | **+13.99** | +3.498 | 7 031.8 s |

#### D. Résultats de la Simulation de la Stratégie Inverse (Spike Hunter Convexe)
* **Nombre de Trades Inversés :** 1 242 trades
* **Win Rate Inversé :** 14.09 % (175 spikes capturés)
* **Pertes Contrôlées (Time-Decay) :** 1 067 trades fermés à -0.25 USD en moyenne (-260.71 USD total)
* **Gains de Spikes Encaissés :** 175 trades fermés à +3.48 USD en moyenne, jusqu'à +15.00 USD (+601.44 USD total)
* **P&L Net Inversé :** **+$340.73 USD**
* **Profit Factor Inversé :** **2.31**

---

### 3. FONCTIONNEMENT TECHNIQUE DU BOT V7.00 QUI DOIT ÊTRE INVERSÉ
Dans la version v7.00 :
1. **Vecteur de 14 Features de Hawkes sans fuite :**
   * `[0] accel_tau1_tau2 = tau1 / (tau2 + 0.10)` : accélération des cycles.
   * `[1] hawkes_slope_fast = h_fast - h_med` : pente d'excitation rapide.
   * `[2] hawkes_fast`, `[3] hawkes_med`, `[4] hawkes_slow`.
   * `[5] c60_norm`, `[6] c300_norm` : compteurs normalisés par espérance Poisson intra-symbole.
   * `[7] time_since_last_spike_norm = t_last / tau`.
   * `[8] spike_amp_norm = last_amp / mean_amp`.
   * `[9] tick_volatility_norm`.
   * `[10] drift_consistency`.
   * `[11] cycle_progress_ratio = t_last / tau`.
   * `[12] hawkes_slope_slow = h_med - h_slow`.
   * `[13] amp_hawkes_interact = spike_amp_norm * h_fast`.
2. **Cerveau ONNX :** Perceptron Multi-Couches (14 -> 128 -> 64 -> 32 -> 2) avec sortie Softmax $[P_0, P_1]$ où $P_1 = P(\text{Survie sans spike pendant } 60\text{ ticks})$.
3. **Prise de Position v7 :** Si $P_1 \ge Q_{70} \approx 0.78$, le bot entrait en BUY sur Crash (pour surfer la montée lente) ou en SELL sur Boom (pour surfer la baisse lente).
4. **Sortie v7 :** Sortie à +0.15 $ à +0.25 $ de gain via TP virtuel (`req.tp = 0.0`), ou dévasté par un spike adverse.

---

### 4. VOS QUESTIONS DE RECHERCHE DOCTORALE & CAHIER DES CHARGES POUR LA V8

En tant qu'Architecte Quantitatif en Chef, nous vous demandons de produire une **spécification d'ingénierie mathématique et algorithmique exhaustive** répondant aux questions suivantes :

#### 1. L'Inversion Mathématique du Signal & du Cerveau ONNX
* Comment transformer la règle de décision probabiliste ? Doit-on ré-entraîner un modèle dédié à prédire $P(\text{Spike imminent dans les } M \text{ prochains ticks} \mid \mathcal{F}_t)$ ou simplement inverser le seuil $P_0 = 1 - P_1 \ge \theta_{\text{spike}}$ ?
* Quelles sont les variables pré-spike les plus discriminantes dans le vecteur de Hawkes pour détecter l'imminence d'une rupture ?

#### 2. Calibration Optimale du Stop Temporel Strict ($M^*$)
* Dans la stratégie inverse, si aucun spike ne survient, chaque tick qui passe engendre une perte de décroissance liée à la dérive ($d \cdot \Delta t$) plus le spread $S$.
* Formulez mathématiquement le problème d'optimisation de la durée maximale de détention $M^*$ (ex. 30, 45, 60 ou 90 ticks) sous une loi de saut de Poisson d'intensité $\lambda = 1/\tau$ :
  $$\max_{M} \; \mathbb{E}[\text{Payoff}(M)] = \int_0^M \left( \mu_S - d \cdot t - S \right) \lambda e^{-\lambda t} \, dt - \left( d \cdot M + S \right) e^{-\lambda M}$$
* Donnez la solution analytique exacte de $M^*$ en fonction de $(\mu_S, d, S, \tau)$ pour chaque symbole (Crash 600, Crash 900, Boom 500, etc.).

#### 3. Résolution de la Latence d'Exécution & Glissement Réel du Spike
* Vous aviez alerté que dans le monde réel, $A_{\text{capturé}} < A$. Sur MetaTrader 5, un spike de Crash ou de Boom s'exécute en un seul tick broker d'une durée de 0 ms.
* Quelle est la meilleure mécanique de sortie pour capturer 100 % du saut sans subir de slippage négatif :
  * Ordre Take-Profit en dur pré-calculé au niveau estimé du saut ?
  * Clôture immédiate au premier tick post-spike détecté dans `OnTick()` dès que le profit dépasse un seuil de points ?
  * Trailing stop ultrarapide avec verrouillage d'un plancher de gain ?

#### 4. Dimensionnement des Lots & Gestion du Risque (Critère de Kelly Convexe)
* Avec un taux de victoire de ~15 % et un ratio de gain/perte moyen de $R = \frac{3.48}{0.25} \approx 13.9$ :
  * Calculez la fraction de Kelly théorique : $f^* = \frac{p(R+1) - 1}{R}$.
  * Quelle fraction de Kelly conservatrice (Half-Kelly, Quarter-Kelly) recommandez-vous pour un capital de 10 000 USD afin de garantir une probabilité de ruine inférieure à $10^{-6}$ tout en maximisant la croissance logarithmique du capital ?
  * Donnez la table des lots optimaux par symbole (Crash 600, Crash 900, Boom 500, etc.) en tenant compte de la valeur du tick et du levier broker.

#### 5. Falsification Pré-Déploiement : Est-ce que cela va marcher en Live ?
* Dressez la liste exhaustive des **modes de défaillance potentiels (*failure modes*)** d'une telle stratégie sur Deriv :
  * Risque de faux départs (spikes miniatures avortés).
  * Élargissement dynamique du spread broker en période de haute fréquence.
  * Rejet d'ordres ou requotes lors des millisecondes entourant le spike.
* Définissez les filtres de sécurité stricts (coupe-circuits, filtres de spread max, filtres de volatilité) à intégrer dans `DerivBoomCrashHFT_v8.mq5`.

---

### 5. LIVRABLE ATTENDU
Un rapport d'ingénierie doctoral ultra-détaillé, contenant les formules mathématiques exactes, le pseudocode algorithmique de la fonction `OnTick()` du bot v8 inversé, la table des paramètres recommandés par instrument, et la démonstration formelle de la robustesse hors échantillon.
