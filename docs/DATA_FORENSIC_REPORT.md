# RAPPORT D'AUDIT FORENSIQUE QUANTITATIF L99
## Terminal MT5 & Compte Réel Deriv-Demo 32449166

```text
================================================================================
[QUANT_POD_STATUS: ACTIF]
[RÉGIME_MARCHÉ: DERIV_SYNTHETIC]
[ACTIVE_AGENT: DATA_CURATOR]
[ÉTAPE: 2_DATA_PIT]
[STATUT FORENSIQUE: CERTIFIÉ CONFORME & VECTORISÉ]
================================================================================
```

---

## 1. Synthèse Exécutive & État du Compte

À la demande du Directeur de Recherche du Quant Pod, une extraction exhaustive et un audit forensique non supervisé ont été conduits directement sur l'environnement de trading MetaTrader 5 (Build 6272, instance `FB9A56D617EDDDFE29EE54EBEFFE96C1`), les bases de données binaires de deals (`deals_2026.10.dat`), les journaux d'exécution du terminal (`Terminal/Logs`), les journaux MQL5 (`MQL5/Logs`), et le journal d'événements système Windows (`System & Application Event Logs`).

### Métriques Clés du Compte au 29 Octobre 2026 (17:55 UTC)
* **Login Compte** : `32449166` (Serveur : `Deriv-Demo`, Mode Hedging)
* **Dépôt Initial (18/10/2026 01:31 UTC)** : `10 000.00 USD` (Ticket deal `#8681938867`)
* **Balance Réelle** : `9 077.11 USD`
* **Equity Actuelle** : `9 055.84 USD` (flottante)
* **PnL Réalisé Cumulé** : **-922.89 USD** (-9.23% du capital initial)
* **Total Deals Exécutés (14 jours)** : **6 842 deals** (1 dépôt + 6 841 deals de trading)
* **Total Positions Traitées** : **3 421 positions** (3 420 fermées, 1 position active en direct)

---

## 2. Analyse Empirique des Deals sur 14 Jours (18 au 29 Octobre 2026)

Le tableau suivant présente les statistiques consolidées au niveau position (round-trip complets entrées/sorties via réconciliation stricte des `position_id`), ventilées par famille d'instruments.

### Tableau 1 : Comparatif Empirique par Famille d'Actifs

| Métrique Quantitative | Famille Boom / Crash | Famille Volatility 25 & 75 | Global Compte (Toutes Familles) |
| :--- | :---: | :---: | :---: |
| **Positions Clôturées** | **3 412** | **8** | **3 420** |
| **Positions Gagnantes (Wins)** | 1 601 | 5 | 1 606 |
| **Positions Perdantes (Losses)** | 1 809 | 3 | 1 812 |
| **Trades Nuls (Evens)** | 2 | 0 | 2 |
| **Taux de Réussite (Win Rate)** | **46.92 %** | **62.50 %** | **46.96 %** |
| **PnL Total Réalisé ($)** | **-$914.78** | **-$8.11** | **-$922.89** |
| **Gains Bruts Cumulés ($)** | +$513.10 | +$192.53 | +$705.63 |
| **Pertes Brutes Cumulées ($)** | -$1 427.88 | -$200.64 | -$1 628.52 |
| **Gain Moyen par Win ($)** | **+$0.3205** | **+$38.5060** | **+$0.4394** |
| **Perte Moyenne par Loss ($)** | **-$0.7893** | **-$66.8800** | **-$0.8987** |
| **Espérance Mathématique (EV/trade)** | **-$0.2681** | **-$1.0138** | **-$0.2699** |
| **Profit Factor (Gross Gain/Loss)** | **0.3593** | **0.9596** | **0.4333** |
| **Max Drawdown Réalisé ($)** | -$914.65 | -$200.64 | -$922.76 |
| **Durée Moyenne de Rétention** | **145.46 s** (~2.4 min) | **16 284.6 s** (~4.52 h) | **183.21 s** |

---

### Tableau 2 : Décomposition Microstructurale Boom / Crash par Instrument

La stratégie de sondes convexes HFT (`DerivBoomCrashHFT_v830_Ultimate`) visait à accumuler des micro-gains par clôture rapide (time-stop à 60 ticks) tout en encaissant les spikes favorables. L'audit statistique révèle une **faillite microstructurale totale** : **100 % des 13 indices présentent une EV négative et un PnL net négatif**.

| Symbole | Trades | Wins | Losses | Win Rate | Gain Brut | Perte Brute | Gain Moy. | Perte Moy. | EV / Trade | PnL Net ($) | Durée Moy. |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Crash 900 Index** | 750 | 422 | 328 | 56.27 % | +$124.54 | -$303.76 | +$0.2951 | -$0.9261 | **-$0.2390** | **-$179.22** | 128.3 s |
| **Boom 500 Index** | 652 | 277 | 375 | 42.48 % | +$78.53 | -$158.84 | +$0.2835 | -$0.4236 | **-$0.1232** | **-$80.31** | 143.6 s |
| **Crash 600 Index** | 555 | 214 | 341 | 38.56 % | +$178.02 | -$599.23 | +$0.8319 | -$1.7573 | **-$0.7589** | **-$421.21** | 108.4 s |
| **Boom 600 Index** | 499 | 156 | 343 | 31.26 % | +$48.60 | -$128.25 | +$0.3115 | -$0.3739 | **-$0.1596** | **-$79.65** | 125.1 s |
| **Crash 500 Index** | 452 | 171 | 281 | 37.83 % | +$26.11 | -$69.04 | +$0.1527 | -$0.2457 | **-$0.0950** | **-$42.93** | 162.0 s |
| **Boom 900 Index** | 224 | 165 | 59 | 73.66 % | +$29.87 | -$77.73 | +$0.1810 | -$1.3175 | **-$0.2137** | **-$47.86** | 281.3 s |
| **Crash 1000 Index** | 143 | 129 | 14 | **90.21 %** | +$11.97 | -$23.78 | +$0.0928 | -$1.6986 | **-$0.0826** | **-$11.81** | 231.9 s |
| **Crash 50 Index** | 36 | 9 | 27 | 25.00 % | +$4.62 | -$18.33 | +$0.5133 | -$0.6789 | **-$0.3808** | **-$13.71** | 90.9 s |
| **Boom 50 Index** | 30 | 12 | 18 | 40.00 % | +$3.34 | -$12.33 | +$0.2783 | -$0.6850 | **-$0.2997** | **-$8.99** | 94.1 s |
| **Crash 150 Index** | 24 | 13 | 9 | 54.17 % | +$2.23 | -$3.24 | +$0.1715 | -$0.3600 | **-$0.0421** | **-$1.01** | 100.8 s |
| **Boom 150 Index** | 21 | 13 | 8 | 61.90 % | +$2.03 | -$4.67 | +$0.1562 | -$0.5838 | **-$0.1257** | **-$2.64** | 92.0 s |
| **Boom 1000 Index** | 16 | 13 | 3 | 81.25 % | +$1.02 | -$7.65 | +$0.0785 | -$2.5500 | **-$0.4144** | **-$6.63** | 188.3 s |
| **Crash 300 Index** | 10 | 7 | 3 | 70.00 % | +$2.22 | -$21.03 | +$0.3171 | -$7.0100 | **-$1.8810** | **-$18.81** | 103.5 s |

#### Cause microstructurale du désastre Boom/Crash :
Sur Crash 1000 et Boom 1000, le bot affichait des taux de réussite miroirs impressionnants (> 80 % à 90 %). Cependant, le ratio Gain/Perte est destructeur : sur Crash 1000, le gain moyen n'est que de **+0.09 $** alors que la perte moyenne en cas de dérive adverse ou de slippage est de **-1.70 $** (ratio asymétrique inverse de 1:18). Sur Crash 600, le slippage d'exécution et les sauts de prix ont détruit à eux seuls **-421.21 $**.

---

### Tableau 3 : Décomposition Détaillée de la Famille Volatility 25 & 75

L'EA `Deriv_VolSqueeze_Breakout_EA_v3` opère sur timeframe H1 avec horizon de maintien non chevauchant de $H = 4$ barres et filtre ONNX 7-features. Deux comportements diamétralement opposés émergent :

| Sous-Famille | Positions | Wins | Losses | Win Rate | Total PnL ($) | Avg Win ($) | Avg Loss ($) | EV / Trade ($) | Profit Factor |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Volatility 25 (1s)** | **3** | **3** | **0** | **100.0 %** | **+$87.16** | **+$29.05** | $0.00 | **+$29.05** | $\infty$ |
| **Volatility 75 (1s)** | **5** | **2** | **3** | **40.0 %** | **-$95.27** | +$52.69 | -$66.88 | **-$19.05** | **0.5252** |
| **Consolidé Volatility (Clôturé)** | **8** | **5** | **3** | **62.5 %** | **-$8.11** | +$38.51 | -$66.88 | **-$1.01** | **0.9596** |

#### Historique Exhaustif des 8 Trades Clôturés sur Volatility 25 & 75 :
1. **Position `#8804827667` (V25 1s)** : 20/10 18:23 UTC | BUY 0.014 lot à 890 410.31 | Sortie 22:00 UTC à 893 472.08 (4h) | **PnL Net: +41.99 $** (Gain brut +42.86$, Swap -0.87$) | Comment: `v3_S1_BUY_P100`
2. **Position `#8804855105` (V75 1s)** : 20/10 19:00 UTC | SELL 0.710 lot à 4 868.22 | Sortie 23:00 UTC à 4 743.32 (4h) | **PnL Net: +87.97 $** (Gain brut +88.68$, Swap -0.71$) | Comment: `VSB_S_z-1.91_q0.25`
3. **Position `#8805131619` (V25 1s)** : 21/10 04:00 UTC | BUY 0.016 lot à 898 403.64 | Sortie 08:00 UTC à 899 321.01 (4h) | **PnL Net: +14.68 $** | Comment: `v3_S1_BUY_P100`
4. **Position `#8806005731` (V75 1s)** : 21/10 22:00 UTC | BUY 0.870 lot à 4 923.87 | Sortie 22/10 02:00 UTC à 4 943.87 (4h) | **PnL Net: +17.40 $** | Comment: `VSB_L_z1.50_q0.25`
5. **Position `#8806133277` (V75 1s)** : 22/10 02:00 UTC | BUY 1.050 lot à 4 945.10 | Sortie 06:00 UTC à 4 865.23 (4h) | **PnL Net: -83.86 $** | Comment: `VSB_L_z1.50_q0.25`
6. **Position `#8806346212` (V75 1s)** : 22/10 08:00 UTC | BUY 0.760 lot à 4 943.99 | Sortie 16:34 UTC à 4 921.29 (8.5h) | **PnL Net: -17.25 $** | Comment: `VSB_L_z1.67_q0.25`
7. **Position `#8807821190` (V75 1s)** : 23/10 15:00 UTC | BUY 0.860 lot à 5 039.80 | Sortie 19:00 UTC à 4 924.07 (4h) | **PnL Net: -99.53 $** | Comment: `VSB_L_z1.63_q0.25`
8. **Position `#8807876622` (V25 1s)** : 23/10 16:00 UTC | SELL 0.011 lot à 903 377.99 | Sortie 20:00 UTC à 900 606.25 (4h) | **PnL Net: +30.49 $** | Comment: `v3_S1_SEL_P100`

---

## 3. Reconstitution Chronologique Forensique (28 & 29 Octobre 2026)

### Découverte Forensique Majeure : Le Biais d'Horloge Locale (Clock Drift de 326 s)
L'analyse des correspondances entre les journaux du terminal/MQL5 et les tickets de deal broker révèle un décalage systématique :
$$\Delta t = t_{\text{Serveur Deriv (UTC)}} - t_{\text{PC Local}} \approx +326\text{ secondes } (+5\text{ minutes et }26\text{ secondes})$$
* Lorsque les logs locaux MQL5 indiquent `14:54:34 UTC`, il est exactement `15:00:00 UTC` sur le serveur broker Deriv (clôture exacte de la bougie H1).
* Lorsque les logs locaux indiquent `09:20:00 UTC`, l'horodatage serveur broker est `09:25:26 UTC`.
Toutes les heures ci-dessous sont présentées avec les deux référentiels certifiés.

---

### Chronologie Événementielle Détaillée

#### Événement A : 28 Octobre 11:03:50 UTC (Arrêt Propre du Terminal)
1. **11:03:27 UTC (Local)** : Un crash critique mémoire de l'application `NSUNSC.exe` (`NARUTO X BORUTO Ultimate Ninja STORM CONNECTIONS`, Exception `0xc0000374` / heap corruption dans `ntdll.dll`) est consigné dans le journal Application Windows (ID 1000).
2. **11:03:49.279 UTC** : Les deux instances de l'EA `Deriv_VolSqueeze_Breakout_EA_v3` sur V25 et V75 reçoivent un ordre de désinitialisation propre :
   `[v3.20 DEINIT] Shutdown clean. Reason = 9` (`REASON_CLOSE`, fermeture initiée par l'utilisateur ou l'OS).
3. **11:03:50.687 UTC** : Le terminal enregistre `Terminal exit with code 0`, suivi de `disconnected from Deriv-Demo` à 11:03:51.383, et `Terminal shutdown with 0`.
4. **Impact trade orphelin** : Une sonde lancée par le bot Boom/Crash à 11:03:27 sur `Crash 500 Index` (0.20 lot SELL `#8812154299`) est restée orpheline sans le terminal. Le Stop-Loss placé côté serveur broker a été touché à **11:34:05 UTC** au prix de 3 033.891 (`[sl 3033.888]`), entraînant une perte de **-1.27 USD** (Deal `#8691349998`).

#### Événement B : 28 Octobre 12:26:17 à 12:47:00 UTC (Boucle de Relance)
* Entre 12:26:17 et 12:46:59 UTC, le terminal MT5 est relancé à **19 reprises successives** (12:26:17, 12:27:04, 12:28:09, 12:28:23, 12:28:55, 12:29:20, 12:29:32, 12:30:56, 12:31:11, 12:32:42, 12:34:13, 12:41:38, 12:41:49, 12:44:38, 12:44:54, 12:45:22, 12:45:42, 12:46:09, 12:46:59).
* Chaque instance chargeait les 3 EAs et s'autorisait sur le serveur de Londres, puis s'arrêtait immédiatement sans journaliser de code de sortie propre.
* **12:47:00.775 UTC** : Dernière ligne du log du 28 octobre. Aucune trace d'instruction `shutdown`. Interruption sèche de l'hôte (panne de courant / passage sur batterie déchargée / extinction matérielle).

#### Événement C : Interruption d'Infrastructure de 20h 32m
* Entre le 28 octobre 12:47:00 UTC et le 29 octobre 09:19:51 UTC, aucun processus MT5 n'était actif.
* Le journal Kernel-Power atteste de multiples transitions de source d'alimentation (`Changement de source d'alimentation`, ID 105) le 28/10 à 20:21:34, le 29/10 à 05:04:58, 07:13:39 et 09:07:31, ainsi que d'une sortie de veille forcée à 09:08:32 UTC (ID 1, Source : `Power Button`).

#### Événement D : 29 Octobre 09:19:51 UTC (Redémarrage et Retrait Définitif de Boom/Crash)
1. **09:19:51.515 UTC (Local) / 09:25:17 UTC (Serveur)** : Démarrage du terminal MT5 x64 build 6272.
2. **09:19:52.749 UTC** : `DerivBoomCrashHFT_v830_Ultimate` se charge sur `Boom 600 Index, M1`.
3. **09:19:59.635 UTC (Local) / 09:25:26 UTC (Serveur)** : Le bot Boom/Crash déclenche immédiatement une sonde d'achat :
   `>>> SONDE CONVEXE BUY_BOOM LANCÉE sur Boom 600 Index (0.20 lot | p0=8.56% >= theta=8.27% | E[Payoff]=-0.17$ | TimeStop=60t/65s) <<<`
   Exécution : Deal `#8692348614` BUY 0.20 lot à 5 388.427 (SL: 5 381.651).
4. **09:20:06.629 UTC (Local) / 09:25:32 UTC (Serveur)** : **Action de l'opérateur** :
   `expert DerivBoomCrashHFT_v830_Ultimate (Boom 600 Index,M1) removed`
   Le bot Boom/Crash est définitivement déchargé du graphique.
5. **09:20:31.688 UTC (Local) / 09:25:58 UTC (Serveur)** : Clôture manuelle du trade orphelin :
   L'opérateur ferme la position manuellement au marché : Deal `#8692348978` SELL 0.20 à 5 387.314, enregistrant une perte de **-0.22 USD** (commentaire vide `""`, absence de signature automatique de time-stop).

#### Événement E : 29 Octobre 14:54:33 UTC (Exécution BUY V25 Ticket #8813604600)
1. **14:54:33.737 UTC (Local) / 15:00:00 UTC (Serveur Deriv)** : Clôture de la bougie H1 de 14:00. L'EA `Deriv_VolSqueeze_Breakout_EA_v3` évalue les conditions d'entrée :
   * Symbole : `Volatility 25 (1s) Index` (TF: H1)
   * Écart-type rolling 20 : $\sigma_{20} = 23.74\text{ bps}$
   * Quantile 25 % (seuil squeeze) : $Q_{0.25} = 23.91\text{ bps}$ $\rightarrow$ **Squeeze Confirmé (`Sqz=YES`)**
   * Z-score de rupture d'impulsion : $Z = +1.78 \ge 1.50$ $\rightarrow$ **Breakout Haussier Confirmé (`Brk=YES`)**
   * Filtre IA ONNX (`c2_vol_filter_v25.onnx`, 7 features) : $P(\text{Win}) = 43.91\% \ge P_{\min} = 42.0\%$ $\rightarrow$ **Filtre Validé**
   * Spread Microstructure : $0.75\text{ bps} \le 4.50\text{ bps}$ $\rightarrow$ **Spread Validé**
2. **14:54:34.453 UTC (Local) / 15:00:01 UTC (Serveur)** : Ordre envoyé et exécuté :
   * Ticket Ordre : `#8813604600`
   * Ticket Deal : `#8692692650`
   * Type : **BUY 0.01 lot** au prix de **930 533.91**
   * Commentaire : `v3_S1_BUY_P44` (Stratégie S1, Achat, Probabilité prédite 44%)
   * Mode de gestion du risque : Pure Time-Stop $H = 4\text{ barres}$ (aucun Hard SL/TP initial).

---

## 4. Analyse en Temps Réel de la Position Active Volatility 25 (1s)

Relevé télémétrique direct effectué le **29 Octobre 2026 à 17:56:19 UTC (Serveur)** / 17:50:53 UTC (PC) :

```text
================================================================================
TÉLÉMÉTRIE POSITION ACTIVE EN DIRECT
================================================================================
Ticket Position       : #8813604600
Symbole               : Volatility 25 (1s) Index
Sens de Position      : BUY (Achat)
Volume (Lots)         : 0.01 lot (Taille minimale de contrat)
Date/Heure d'Ouverture: 2026-10-29 15:00:01 UTC (Serveur)
Horodatage Deal       : 1793286001092 ms
Prix d'Entrée         : 930 533.91
Prix Actuel (Bid)     : 928 406.56
Écart Prix (Points)   : -2 127.35 points
PnL Non Réalisé       : -21.27 USD
Durée de Rétention    : 2h 56m 18s (10 578 secondes)
Magic Number          : 20261021
Commentaire d'Origine : v3_S1_BUY_P44
Stop-Loss / TP        : Aucun (0.00 / 0.00) — Encodage Pure Time-Stop H=4
================================================================================
EXCURSION DES PRIX SUR L'HORIZON H1 DE LA POSITION :
  Bougie 1 (15:00-16:00 UTC) : Open=930 463.86 | High=933 904.89 | Close=933 198.96 (+26.65$)
  Bougie 2 (16:00-17:00 UTC) : High atteint 935 714.35 (MFE Peak = +51.80 USD)
  Bougie 3 (17:00-18:00 UTC) : Revers violent, Low à 928 303.51 (MAE Trough = -22.30 USD)
  Bougie 4 (18:00-19:00 UTC) : En cours d'exécution
================================================================================
```

### Diagnostic Opérationnel & Sortie Programmée
1. **Non-encaissement du MFE (+51.80 USD)** : L'EA applique la règle stricte $H = 4$ sans Trailing Stop ni Hard Take-Profit (`InpUseHardTPSL = false`). La position a atteint un profit flottant supérieur à $+50\text{ USD}$ avant de subir le retracement moyen de la volatilité synthétique.
2. **Heure Prévue de Liquidation Automatique** :
   * L'instruction `ManageOpenPositions()` dans l'EA vérifie `bars_elapsed >= InpMaxHoldBars` ($H = 4$).
   * La 4ème barre H1 se terminera à **19:00:00 UTC (Serveur)**, soit approximativement **18:54:34 UTC (Heure Locale PC)**.
   * L'EA émettra l'ordre `PositionClose(8813604600)` dès le premier tick reçu après 19:00:00 UTC.

---

## 5. Recommandations Factuelles pour le Quant Pod

1. **Veto Formel & Rejet Définitif de `DerivBoomCrashHFT`** :
   Les données empiriques certifient que l'asymétrie de distribution de Poisson des spikes Deriv détruit systématiquement l'espérance mathématique des sondes de dérive (EV moyenne de -$0.27$ par trade sur 3 412 occurrences, Sharpe négatif, 13 indices sur 13 en déficit). L'interdiction de trading sur cette logique doit être maintenue.
2. **Synchronisation Horloge Système (NTP Urgent)** :
   Le drift d'horloge de **326 secondes** introduit un risque critique de causalité temporelle dans la recherche empirique. La synchronisation sur `time.windows.com` ou un serveur NTP local Deriv à milliseconde certifiée est obligatoire.
3. **Optimisation de la Sortie Volatility Breakout (Trailing Excursion)** :
   La stratégie Volatility 25 génère un alpha réel ($+87.16\text{ USD}$ sur les 3 premiers trades, et un MFE de $+51.80\text{ USD}$ sur le trade actuel). Cependant, l'absence de protection de profit flottant transforme un trade à $+50\text{ USD}$ en perte flottante de $-20\text{ USD}$. Un Trailing Stop basé sur $1.5 \times \text{ATR}_{20}$ dès que le gain dépasse $+1.5\text{ SD}$ est impératif.
4. **Dissociation du Sizing Volatility 75** :
   Les 5 trades de V75 ont enregistré un PnL de $-95.27\text{ USD}$ en raison de lots disproportionnés (0.71 à 1.05 lot) par rapport à la volatilité intrinsèque du sous-jacent. Le ciblage de volatilité doit être strictement plafonné.

---
*Rapport certifié conforme par le [DATA_CURATOR] du Quant Pod L99. Données MT5 extraites directement via l'API C/Python MetaTrader5 5.0.5735.*
