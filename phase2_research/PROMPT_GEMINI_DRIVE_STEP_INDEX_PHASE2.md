# MISSION ANALYSE EMPIRIQUE & CALCUL MASSIF SUR GOOGLE DRIVE (LEAD DATA QUANT)
## Destinataire : Gemini 4 Argon / Gemini 1.5 Pro (Connecté au Google Drive)
### Référence : PH2-GEMINI-DRIVE-001 | Date : 2026-10-20
### Dépôt Git Officiel : `Christ-yavn/bot-quant-` | Environnement : MetaTrader 5 (Deriv)

---

### 1. CONTEXTE GLOBAL & TRANSMISSION FORMELLE DU PROJET

Tu es l'Ingénieur en Chef du Calcul Quantitatif au sein du collège d'agents IA (Antigravity, Gemini 4 Argon, Claude Fable 5) pour le projet institutionnel `Christ-yavn/bot-quant-`.

#### État d'avancement des travaux :
1. **Phase 1 (Boom & Crash — v1.00 à v8.10) :**
   - La stratégie de récolte de dérive (drift harvesting v7.00) a été falsifiée par le théorème de Doob (85,91% de wins ruinés par les queues épaisses des spikes, P&L -406,14 USD).
   - L'audit médico-légal a prouvé que l'inversion pure du payoff (pari systématique sur les spikes avant déclenchement, stop temporel analytique strict à 60 ticks) produit une asymétrie positive (skew > 0) avec une espérance contrefactuelle de +340,73 USD sur 1 242 trades réels.
   - La version de production **v8.10 Spike Hunter Convexe** est actuellement déployée et en cours d'exécution live sous MetaTrader 5 sur le compte démo institutionnel (10 000 USD de capital) pour valider la porte G1 du protocole quantitatif.

2. **Phase 2 (Step Index & Indices de Volatilité) :**
   - Nous ouvrons immédiatement la recherche fondamentale sur les 18 actifs synthétiques récoltés dans le dossier Google Drive : `EXPORT_DRIVE_PHASE2_STEP_VOLATILITY`.
   - Ton rôle avec l'accès Google Drive est d'exécuter l'analyse de données, les calculs de matrices de transition, les tests statistiques de marche aléatoire et la modélisation empirique des fichiers.

---

### 2. ARBORESCENCE DES DONNÉES DISPONIBLES SUR TON GOOGLE DRIVE

Dans le dossier Google Drive partagé `EXPORT_DRIVE_PHASE2_STEP_VOLATILITY`, tu disposes de 45 fichiers CSV haute fidélité issus de MT5 :

1. **Série Step Index (Cœur de la recherche de convexité) :**
   - `Step_Index_ticks_sample.csv` (échantillon de ticks à haute fréquence avec timestamp milliseconde, bid, ask, last).
   - `Step_Index_M1_deep.csv` (historique profond en barres M1).
   - `Step_Index_H1_history.csv` (historique en barres H1).
   - Variantes par seuil : `Step_Index_200_...`, `Step_Index_300_...`, `Step_Index_500_...` (D1, H1, M1).
   - Variantes multi-pas : `Multi_Step_2_Index_...`, `Multi_Step_4_Index_...` (D1, H1, M1).

2. **Série Volatilités Synthétiques (V10 à V250 1s) :**
   - `Volatility_10_Index_...`, `Volatility_25_Index_...`, `Volatility_50_Index_...`, `Volatility_75_Index_...`, `Volatility_100_Index_...`.
   - Versions 1-seconde : `Volatility_10_1s_...`, `Volatility_25_1s_...`, `Volatility_50_1s_...`, `Volatility_75_1s_...`, `Volatility_100_1s_...`, `Volatility_150_1s_...`, `Volatility_250_1s_...`.
   - Fichiers de ticks : `Volatility_75_Index_ticks_sample.csv`, `Volatility_100_1s_Index_ticks_sample.csv`.
   - Manifeste complet des volumes : `HARVEST_MANIFEST.csv`.

---

### 3. MICROSTRUCTURE ÉTABLIE DU STEP INDEX (GROUND TRUTH)

L'audit des premiers ticks réels de `Step_Index_ticks_sample.csv` démontre la structure suivante :
- **Intervalle temporel :** $\Delta t = 1,000 	ext{ ms}$ (exactement 1 tick par seconde).
- **Taille de pas discret :** $\Delta p \in \{-0.10, 0.00, +0.10\}$.
- **Friction de transaction :** Spread fixe constant $S = 0.10 	ext{ pt}$ (soit exactement 1 pas de cotation).

---

### 4. TES TÂCHES DE CALCUL QUANTITATIF (LIVRABLES REQUIS)

En exploitant directement les fichiers du dossier Drive, exécute le pipeline d'analyse suivant et fournis les résultats numériques chiffrés :

#### TÂCHE 1 : Test de l'Hypothèse Nulle de Martingale sur le Step Index
Sur `Step_Index_ticks_sample.csv` et `Step_Index_M1_deep.csv` :
1. Calcule la distribution des incréments $\Delta p_t = p_t - p_{t-1}$.
2. Estime la probabilité non-conditionnelle de hausse $P(	ext{Up})$, de baisse $P(	ext{Down})$, et de pas nul $P(	ext{Flat})$.
3. **Chaîne de Markov d'ordre 1 & 2 :** Calcule la matrice de transition conditionnelle :
   $$P(	ext{Up}_t \mid 	ext{Up}_{t-1}), \quad P(	ext{Down}_t \mid 	ext{Up}_{t-1})$$
   $$P(	ext{Up}_t \mid 	ext{Up}_{t-1}, 	ext{Up}_{t-2}), \quad P(	ext{Down}_t \mid 	ext{Down}_{t-1}, 	ext{Down}_{t-2})$$
4. **Test de ratio de variance de Lo-MacKinlay** pour $k \in \{2, 4, 8, 16, 32\}$ avec z-statistiques corrigées de l'hétéroscédasticité. Existe-t-il une mémoire de corrélation ou une dépendance non-linéaire ?

#### TÂCHE 2 : Modélisation Empirique du Gambler's Ruin sous Friction Réelle
Soit un trade directionnel ouvert avec un Take-Profit à $+M$ pas et un Stop-Loss à $-K$ pas sous spread $S = 1$ pas ($0.10\$$) :
1. Sur les ticks réels, simule pour chaque combinaison $(K, M) \in \{ (1, 2), (2, 5), (3, 10), (5, 15), (5, 20) \}$ :
   - Le taux de succès empirique (Win Rate observé).
   - Le temps moyen d'atteinte de la barrière (First Passage Time $\mathbb{E}[T]$ en secondes).
   - Le P&L moyen net par trade après déduction du spread $S = 0.10$.
   - Le skew de la distribution des payoffs.
2. Identifie s'il existe une région $(K^*, M^*)$ où l'espérance mathématique nette dépasse strictement 0 ($\mathbb{E}[	ext{Trade}] > 0$), ou si le théorème de Doob condamne toute stratégie statique.

#### TÂCHE 3 : Audit Microstructurel des 10 Indices de Volatilité (V10 à V250 1s)
Pour éviter l'erreur de catégorie (modéliser un GBM comme un processus à retour à la moyenne) :
1. Vérifie sur `Volatility_..._H1_history.csv` et `_M1_deep.csv` que les séries de log-prix $\ln(P_t)$ sont bien des marches aléatoires pures (test ADF et KPSS confirmant la non-stationnarité en niveau).
2. Démontre que la stationnarité et la mean-reversion ne résident QUE dans les variables d'état transformées :
   - **Log-Range normalisé de Parkinson / Garman-Klass :** $\ln(	ext{High}_t / 	ext{Low}_t)$.
   - **Volatilité Réalisée (RV) à haute fréquence :** Distribution et clustering d'autocorrélation.
3. Quantifie la demi-vie de retour à la moyenne (Half-life de l'Ornstein-Uhlenbeck) sur la volatilité réalisée de ces 10 indices.

Livre un rapport complet de calcul avec toutes les tables numériques, les p-values et les recommandations concrètes pour l'architecture du prochain bot de trading.
