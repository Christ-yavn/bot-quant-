# RAPPORT COMPLET D'EXTRACTION ET D'ANALYSE DE SESSION - DERIV BOOM & CRASH HFT (VERSION 6.00)

**Date d'extraction** : 2026-10-19 00:52:09 UTC  
**Compte MT5** : `32449166` (Deriv-Demo) | Devise : `USD`  
**Solde Initial (Dépôt virtuel)** : 10 000.00 USD  
**Solde Actuel au moment de la pause** : 9927.65 USD  
**Équité Actuelle** : 9927.65 USD  
**Positions ouvertes en cours** : 0 (toutes les positions sont closes)  
**Dossier d'exportation** : `C:\Users\CHRIST\Desktop\IA\ANTIGRAVITY\projets\DONNER  TRADE V6`  

---

## 1. VUE D'ENSEMBLE DU COMPTE & CHRONOLOGIE DES VERSIONS

| Phase | Horodatage (UTC) | Deals | Trades Fermés | P&L Net (USD) | Solde Cumulé (USD) |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Dépôt Initial** | 2026-10-18 08:50:00 | 1 | - | +10 000.00 | 10 000.00 |
| **Sessions Antérieures (v1.00 à v5.00)** | 2026-10-18 08:51:09 → 11:28:34 | 391 | 196 | -46.01 | 9 953.99 |
| **Session v6.00 (Golden 7 + Turbo Drift + ONNX)** | 2026-10-18 11:28:34 → 2026-10-19 00:43:16 | 525 | 262 | -26.34 | 9 927.65 |
| **BILAN TOTAL DU COMPTE** | **Total Session Complète** | **917** | **458** | **-72.35** | **9 927.65** |

> **Note importante de synchronisation** : Exactement 1 position (`Crash 1000 Index`, position #8802343654) avait été ouverte sous la version 5 à 11:27:33 UTC (+0.02 USD) et a été clôturée sous la version 6 à 11:29:10 UTC via le mécanisme Green Cash-In.

---

## 2. RÉSULTATS DÉTAILLÉS DE LA VERSION 6.00

### Métriques Clés de Performance (v6.00) :
- **Total Trades Exécutés (Allers-Retours)** : 262
- **Trades Gagnants** : 257 (98.1%)
- **Trades Perdants** : 5 (1.9%)
- **Trades Neutres (Breakeven)** : 0
- **P&L Net Total (v6.00)** : **-26.36 USD**
- **Profit Factor** : 0.25
- **Durée Moyenne d'un Trade** : 206.9 secondes
- **Durée Médiane** : 80.0 secondes

---

### Répartition de la Performance par Indice (v6.00) :

| symbol | total_trades | win_count | loss_count | breakeven_count | win_rate_pct | net_pnl_usd | gross_profit_usd | gross_loss_usd | profit_factor | avg_win_usd | avg_loss_usd | max_win_usd | max_loss_usd | avg_duration_sec | max_duration_sec | total_volume_lots |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Boom 500 Index | 54 | 52 | 2 | 0 | 96.3 | -5.34 | 2.05 | -7.39 | 0.28 | 0.039 | -3.695 | 0.04 | -3.82 | 166.8 | 3575 | 10.8 |
| Crash 1000 Index | 1 | 1 | 0 | 0 | 100.0 | 0.01 | 0.01 | -0.0 | 999.0 | 0.01 | 0.0 | 0.01 | 0.01 | 95.0 | 95 | 0.2 |
| Crash 900 Index | 207 | 204 | 3 | 0 | 98.6 | -21.03 | 6.71 | -27.74 | 0.24 | 0.033 | -9.247 | 0.3 | -11.66 | 217.9 | 5152 | 41.4 |

---

### Analyse des Raisons de Sortie (v6.00) :

| close_reason | trades_count | win_rate_pct | total_pnl_usd | avg_pnl_usd | avg_duration_sec |
| --- | --- | --- | --- | --- | --- |
| GREEN_CASH_IN | 254 | 100.0 | 8.39 | 0.033 | 172.5 |
| MARKET_CLOSE_OR_MANUAL | 3 | 66.7 | -4.57 | -1.523 | 1209.3 |
| STOP_LOSS | 4 | 0.0 | -30.48 | -7.62 | 1651.5 |
| TAKE_PROFIT | 1 | 100.0 | 0.3 | 0.3 | 159.0 |

---

## 3. ANALYSE CRITIQUE DES PERFORMANCES V6.00 (ASYMÉTRIE GAIN / PERTE & CAUSE RACINE)

1. **Crash 1000 Index (+0.01$ à +0.03$ | Win Rate 100.0%)** :
   - Performance parfaite : 100% de trades gagnants clôturés via *Green Cash-In*. Sorties ultra-rapides et sans aucune perte.
2. **Boom 500 Index (-5.34 USD | Win Rate 96.3%)** :
   - **52 victoires sur 54 trades** (taux de réussite exceptionnel de 96.3%).
   - Les 52 scalps de drift ont généré **+2.05 USD** de gains cumulés (moyenne de +0.039$ par trade).
   - Cependant, **2 seuls Stop-Loss** ont coûté **-7.39 USD** (moyenne de -3.70$ par SL).
3. **Crash 900 Index (-21.03 USD | Win Rate 98.6%)** :
   - **204 victoires sur 207 trades** (taux de réussite de 98.6%).
   - Les 204 scalps de drift ont généré **+6.71 USD** de gains cumulés (moyenne de +0.033$ par trade).
   - Mais **3 seuls Stop-Loss** ont coûté **-27.74 USD** (moyenne de -9.25$ par perte, avec une perte maximale de -11.66$ sur un seul spike violent traversant le SL).
4. **Diagnostic Fondamental pour l'Amélioration** :
   - Le moteur HFT / Dérive continue a un taux de victoire stratosphérique (**98.1%** sur l'ensemble de la session).
   - Le problème structurel réside dans l'**asymétrie Risk/Reward** : un gain moyen de +0.03$ contre une perte moyenne de -7.62$ sur SL (ratio 1:254). Chaque stop-loss efface plus de 200 micro-scalps réussis !
   - Le filtre ONNX et le trailing-stop/recovery doivent impérativement être renforcés avant le spike ou la distance SL doit être calibrée dynamiquement en fonction du tick-value spécifique de chaque indice (Crash 900 a un tick value beaucoup plus cher que Crash 1000).

---

## 4. INVENTAIRE COMPLET DES FICHIERS SAUVEGARDÉS

Le dossier `C:\Users\CHRIST\Desktop\IA\ANTIGRAVITY\projets\DONNER  TRADE V6` contient une structure rigoureuse et exhaustive :

```
C:\Users\CHRIST\Desktop\IA\ANTIGRAVITY\projets\DONNER  TRADE V6\
│
├── 01_TRADES\
│   ├── v6_deals.csv                         # 525 deals de la v6 avec timestamps ISO UTC et libellés
│   ├── v6_deals.json                        # Format JSON complet des deals v6
│   ├── v6_orders.csv                        # 525 ordres passés par la v6 (cours, SL, TP, statuts)
│   ├── v6_orders.json                       # Format JSON des ordres v6
│   ├── v6_closed_positions.csv              # 262 trades allers-retours reconstitués ouverts en v6
│   ├── v6_all_positions_closed_in_session.csv # 263 trades débouclés durant la fenêtre v6
│   ├── all_account_deals_since_deposit.csv  # 917 deals de l'intégralité du compte depuis le dépôt
│   ├── all_account_orders_since_deposit.csv # 916 ordres de l'intégralité du compte
│   └── all_account_closed_positions.csv     # 458 positions allers-retours totales du compte
│
├── 02_LOGS\
│   ├── v6_expert_logs.log                   # Logs experts filtrés précisément du démarrage v6 à la pause
│   ├── v6_expert_logs.csv                   # Table structurée des logs experts (horodatage, message, etc.)
│   ├── v6_terminal_logs.log                 # Logs de la plateforme terminal MT5 durant la session v6
│   ├── raw_expert_log_20261018.log          # Copie intégrale originale brute du log expert 18/10 (2.38 MB)
│   ├── raw_expert_log_20261019.log          # Copie intégrale originale brute du log expert 19/10
│   ├── raw_terminal_log_20261018.log        # Copie intégrale originale brute du terminal 18/10 (45.9 MB)
│   ├── raw_terminal_log_20261019.log        # Copie intégrale originale brute du terminal 19/10 (2.0 MB)
│   └── raw_metaeditor.log                   # Logs de compilation MetaEditor
│
├── 03_TICKS\
│   ├── ticks_summary_v6.csv                 # Résumé statistique des ticks extraits par indice
│   ├── ticks_v6_Crash_1000_Index.csv        # 46 576 ticks tick-by-tick (bid, ask, spread, time UTC)
│   ├── ticks_v6_Crash_900_Index.csv         # 47 532 ticks
│   ├── ticks_v6_Crash_600_Index.csv         # 47 709 ticks
│   ├── ticks_v6_Crash_500_Index.csv         # 46 341 ticks
│   ├── ticks_v6_Crash_300_Index.csv         # 47 545 ticks
│   ├── ticks_v6_Crash_150_Index.csv         # 47 757 ticks
│   ├── ticks_v6_Crash_50_Index.csv          # 47 790 ticks
│   ├── ticks_v6_Boom_1000_Index.csv         # 47 348 ticks
│   ├── ticks_v6_Boom_900_Index.csv          # 47 060 ticks
│   ├── ticks_v6_Boom_600_Index.csv          # 46 861 ticks
│   ├── ticks_v6_Boom_500_Index.csv          # 47 285 ticks
│   ├── ticks_v6_Boom_300_Index.csv          # 45 894 ticks
│   ├── ticks_v6_Boom_150_Index.csv          # 47 749 ticks
│   └── ticks_v6_Boom_50_Index.csv           # 47 814 ticks
│                                            # TOTAL : ~660 000 ticks haute fréquence archivés
│
├── 04_CONFIG_AND_MODEL\
│   ├── DerivBoomCrashHFT_v6.mq5             # Code source MQL5 exact ayant tourné
│   ├── DerivBoomCrashHFT_v6.ex5             # Binaire compilé exécuté
│   ├── boom_crash_meta_brain.onnx           # Modèle IA de survie ONNX chargé par le bot
│   ├── onnx_model_metadata.json             # Métadonnées et seuils Hawkes du modèle ONNX
│   └── session_metadata.json                # Paramètres du terminal et métadonnées d'exécution
│
├── 05_STATISTICS_AND_ANALYSIS\
│   ├── v6_performance_by_symbol.csv        # Analyse comparative par indice
│   ├── v6_performance_by_close_reason.csv  # Répartition par déclencheur de clôture
│   ├── v6_performance_by_hour.csv          # Répartition horaire de l'activité
│   └── v6_equity_curve.csv                  # Évolution tick/deal de l'équité et du solde
│
└── RAPPORT_COMPLET_SESSION_V6.md            # Ce rapport complet de synthèse
```
