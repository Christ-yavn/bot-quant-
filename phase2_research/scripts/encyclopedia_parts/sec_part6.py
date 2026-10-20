# -*- coding: utf-8 -*-

def get_content():
    return r"""<a id="partie-6"></a>
# PARTIE 6 : PROTOCOLE ET FEUILLE DE ROUTE POUR DEMAIN (SESSION GATE 5 & REVUE APPROFONDIE)

---

## 6.1. LE CAHIER DES CHARGES DE LA PHASE GATE 5 (20 SESSIONS DÉMO DE 24H)

Conformément à la gouvernance institutionnelle établie dans notre plan de déploiement ([`phase2_research/SENTINEL_VERDICT_C1_C2.md`](phase2_research/SENTINEL_VERDICT_C1_C2.md)), l'autorisation de déployer du capital réel sur un compte de trading est strictement subordonnée à la validation de la **Phase Gate 5**.

### Définition de la Phase Gate 5
La Phase Gate 5 consiste en une période d'incubation opérationnelle continue de **20 sessions de 24 heures (soit environ 3 semaines)** sur le compte Démo officiel `32449166`, sans aucune intervention manuelle discrétionnaire.

```text
========================================================================================
            MATRICE DE CONTRÔLE ET CRITÈRES DE SUCCÈS GATE 5
========================================================================================

1. CRITÈRES DE PERFORMANCE POUR LE TRACK 1 (BOOM & CRASH V8.20 CONVEXE) :
   * Objectif d'Asymétrie : Confirmation de l'asymétrie positive (Positive Skewness).
   * Ratio Gain Moyen / Perte Moyenne : Strictement > 8.0 (Les gains de spikes doivent
     écraser les micro-pertes de dérive).
   * Perte Maximale par Trade Non-Spike : Bornée à -0.25 USD (Preuve que le stop temporel
     de 60 ticks fonctionne sans défaillance).
   * Drawdown Maximal Toléré : < 8.0 % du capital alloué.

2. CRITÈRES DE PERFORMANCE POUR LE TRACK 2 (VOLATILITY 25 (1s) V3.00 ONNX) :
   * Taux de Réussite Réel (Win Rate) : Maintenu au-dessus de 58.0 % (Cohérent avec
     l'estimation hors-échantillon de 62.82 %).
   * Nombre de Signaux H1 Attendus : Entre 1 et 3 trades par jour.
   * Fiabilité du Filtre ONNX : 100 % des trades exécutés doivent afficher une probabilité
     P >= 0.60 dans le commentaire de l'ordre (ex: v3_S1_BUY_P100 ou v3_S1_SELL_P72).

3. CRITÈRES DE STABILITÉ INFRASTRUCTURELLE (SYSTÈME GLOBAL) :
   * Zéro crash du terminal MetaTrader 5 (Disponibilité 99.9 %).
   * Zéro fuite de mémoire (Vérification de la mémoire vive du process terminal64.exe).
   * Zéro erreur d'exécution OnnxRun ou MQL5 dans les journaux d'experts.
========================================================================================
```

---

## 6.2. LA GRILLE DE SUIVI BIQUOTIDIENNE (CHECKLIST OPÉRATIONNELLE)

Pour assurer un suivi scientifique rigoureux sans perturber l'exécution des bots, une routine de contrôle en deux étapes quotidiennes est instituée :

### Checkpoint Matin (08:00 UTC) & Soir (20:00 UTC)
1. **Lancement du Moniteur Unifié :**
   Exécuter dans le terminal la commande analytique :
   ```bash
   python src/python/analytics/monitor_dual_bots.py
   ```
2. **Relevé des Métriques Clés :**
   * Solde (*Balance*) et Équité (*Equity*) du compte `32449166`.
   * Nombre de trades exécutés par le Track 1 et par le Track 2.
   * PnL cumulé et Win Rate de chaque gamme.
   * Vérification des positions ouvertes et de leurs tickets.
3. **Audit des Fichiers Journaux :**
   Vérifier l'absence d'erreurs critiques dans les journaux MetaTrader 5 :
   * `C:\Users\CHRIST\AppData\Roaming\MetaQuotes\Terminal\FB9A56D617EDDDFE29EE54EBEFFE96C1\MQL5\Logs`

---

## 6.3. LES 6 PORTES DU PROTOCOLE VERS LE COMPTE RÉEL (GOVERNANCE GATEWAY)

Le passage d'une idée mathématique à un compte de trading réel avec des capitaux substantiels suit un protocole à 6 portes inviolables :

```mermaid
flowchart TD
    G1["GATE 1 : Preuve Mathématique & Théorème de Doob"] -->|Validé| G2["GATE 2 : Simulation Zéro-Leakage & Backtest"]
    G2 -->|Validé| G3["GATE 3 : Falsification Sentinelle (BCa, Welch, Placebo, DSR)"]
    G3 -->|Validé V25 (1s)| G4["GATE 4 : Compilation 0 Erreur & Inférence ONNX MQL5"]
    G4 -->|Validé Aujourd'hui| G5["GATE 5 : Incubation Démo 20 Sessions (EN COURS)"]
    G5 -->|Objectifs Atteints| G6["GATE 6 : Déploiement Réel Micro-Lots (0.01 lot)"]
```

* **Gate 1 (Théorie) :** Démonstration que l'espérance brute n'est pas une illusion ($\mathbb{E} > 0$). $\rightarrow$ **VALIDÉ**.
* **Gate 2 (Backtest) :** Backtest sans biais de lookahead ni fuite d'information. $\rightarrow$ **VALIDÉ**.
* **Gate 3 (Falsification Sentinelle) :** Réussite des 4 tests statistiques cumulatifs (V25 validé, V75 éliminé). $\rightarrow$ **VALIDÉ**.
* **Gate 4 (Génie Logiciel) :** Code MQL5 et ONNX compilé sans warning, modèles déployés sur MT5. $\rightarrow$ **VALIDÉ**.
* **Gate 5 (Incubation Démo 24h/24) :** Validation en conditions réelles de liquidité et de slippage. $\rightarrow$ **ACTUELLEMENT EN COURS**.
* **Gate 6 (Production Réelle) :** Démarrage avec des micro-lots de 0.01 lot sur capital propre, montée en charge graduée.

---

## 6.4. PRÉPARATION DE LA SESSION DE REVUE (CE SOIR À 0H OU DEMAIN MATIN)

Ce document pose le socle inaltérable de nos travaux. Comme convenu avec l'utilisateur, un rendez-vous stratégique est fixé à **ce soir 00:00 UTC ou demain matin** pour :
1. **Examiner chaque bot de fond en comble :**
   * Réexaminer le comportement de la position BUY `#8804827667` sur Volatility 25 (1s).
   * Analyser les premières captures de spikes par le Track 1 Boom/Crash v8.20.
2. **Stress-tester les paramètres dynamiques :**
   * Ajustement éventuel de la taille des lots et des trailing stops.
   * Vérification de la latence d'exécution broker.
3. **Poursuivre la marche vers l'excellence absolue (*Beastmode*) :**
   * Automatisation du reporting quotidien via Telegram ou Webhook si souhaité.
   * Consolidation continue des logs dans les archives de recherche.
"""
