# MANDAT DE SPÉCIFICATIONS MATHÉMATIQUES & THÉORIQUES — PHASE 2
## Destinataire : Claude 3.5 Sonnet / Claude Fable 5 (Architecte Quantitatif & Rigueur Formelle)
### Référence : PH2-FABLE-MATH-001 | Date : 2026-10-20
### Dépôt Git Officiel : `Christ-yavn/bot-quant-` | Projet : Quant Bot Deriv

---

### 1. MISSION & DIVISION DU TRAVAIL QUANTITATIF

Tu es le Directeur de la Recherche Quantitative et l'Architecte Théorique du collège d'agents.
- La **Phase 1 (Boom/Crash)** est clôturée pour la nuit : la version **v8.10 Spike Hunter Convexe** (inversion de payoff, TP dur à 0.8 E[A], stop temporel strict à 60 ticks, watchdog persistant anti-rejet) tourne actuellement sur MetaTrader 5 pour valider la porte G1.
- **Gemini 4 Argon** est connecté au Google Drive (`EXPORT_DRIVE_PHASE2_STEP_VOLATILITY`) pour calculer les distributions empiriques sur les 45 fichiers CSV de ticks et barres.
- **Ta mission :** Fournir les dérivations mathématiques formelles, les théorèmes d'arrêt et les conditions d'existence de l'alpha nécessaires à la conception de l'algorithme Phase 2 (**Step Index & Volatilité**).

---

### 2. MODÉLISATION DU STEP INDEX : MARCHE ALÉATOIRE DISCRÈTE ET CONVEXITÉ

L'analyse microstructurelle prouve que le Step Index est coté sur un réseau 1D discret :
- Pas temporel : $\Delta t = 1	ext{ s}$.
- Pas d'espace : $\Delta p \in \{-\delta, 0, +\delta\}$ avec $\delta = 0.10	ext{ pt}$.
- Coût de friction irréversible : Spread constant $S = \delta = 0.10	ext{ pt}$ (1 pas).

#### Question 1.1 : Théorème de Gambler's Ruin à Deux Barrières Asymétriques sous Spread
Considérons une position ouverte à $p_0$ avec un Take-Profit à $p_0 + M\delta$ et un Stop-Loss à $p_0 - K\delta$ ($M, K \in \mathbb{N}^*$, $M > K$).
Soit $p = P(\Delta p = +\delta)$ et $q = P(\Delta p = -\delta)$ avec $p + q = 1$.
1. Dérive l'expression exacte de la probabilité de toucher le Take-Profit avant le Stop-Loss, notée $\pi(p, K, M)$.
2. En intégrant le spread $S = \delta$ déduit à l'ouverture, donne la formule analytique complète de l'espérance mathématique de gain :
   $$\mathbb{E}[	ext{Gain}](p, K, M, S)$$
3. **Preuve de Doob sous Symétrie ($p = q = 0.5$) :** Démontre rigoureusement que quelle que soit l'asymétrie choisie entre $M$ et $K$ ($M \gg K$), $\mathbb{E}[	ext{Gain}] = -S < 0$.
4. **Condition d'Alpha de Seuil :** Détermine la valeur critique minimale $p^*(K, M, S)$ pour laquelle $\mathbb{E}[	ext{Gain}] > 0$.

#### Question 1.2 : Modélisation d'une Dépendance de Markov d'Ordre 1
Supposons que le générateur présente un biais de persistance ou de rebond modélisé par une chaîne de Markov :
$$P(	ext{Up}_t \mid 	ext{Up}_{t-1}) = p_1, \quad P(	ext{Down}_t \mid 	ext{Down}_{t-1}) = q_1$$
1. Dérive la distribution du temps de premier passage (*First Passage Time*) pour atteindre un gain de $+M$ pas.
2. Si $p_1 > 0.50$ (momentum discret), comment calibrer dynamiquement la taille du trade et le temps de maintien maximal $T^*$ pour maximiser le ratio de Sharpe ?

---

### 3. INTERDICTION DE L'ERREUR DE CATÉGORIE SUR LES INDICES DE VOLATILITÉ (V10 À V250)

Dans le rapport d'orientation préliminaire, tu as mis en garde contre l'erreur consistant à chercher un retour à la moyenne sur le niveau des prix d'un indice de volatilité synthétique.
1. **Rappel théorique formel :** Démontre pourquoi le prix d'un Volatility Index Deriv est un mouvement brownien géométrique (GBM) standard :
   $$dS_t = \sigma S_t dW_t$$
   avec drift $\mu = 0$ et volatilité $\sigma$ constante par construction algorithmique, rendant toute stratégie de Bollinger / RSI / Mean-Reversion structurellement perdante sous spread $S > 0$.
2. **Définition des Variables d'État Transformées Éligibles :**
   Formalise mathématiquement les 2 seules représentations où la mean-reversion existe sans violer Doob :
   - Le log-range de Parkinson / Garman-Klass : prouve qu'il suit un processus d'Ornstein-Uhlenbeck stationnaire.
   - La variance réalisée haute fréquence sur fenêtre glissante.
3. Donne les équations de pricing d'un canal de volatilité exploitable pour un bot HFT.

---

### 4. PROTOCOLE D'AUDIT SENTINEL & ARBORESCENCE DU CODE

Définis l'architecture modulaire recommandée pour le dépôt `Christ-yavn/bot-quant-` pour la Phase 2 :
- Nom des scripts Python d'analyse (ex: `phase2_research/scripts/...`).
- Découpage chronologique sans fuite (*Purged & Embargoed Cross-Validation*).
- Formule de correction des tests multiples (**Benjamini-Hochberg FDR** et **White's Reality Check**) à intégrer dans le script de validation d'alpha.

Livre un document doctoral intégral avec toutes les équations KaTeX/LaTeX, sans approximation, prêt à être codé par Antigravity.
