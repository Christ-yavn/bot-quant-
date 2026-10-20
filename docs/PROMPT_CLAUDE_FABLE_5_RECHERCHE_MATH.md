# MISSION DIRECTEUR DE RECHERCHE QUANTITATIVE (PHD / HEAD OF QUANT)
## Destinataire : Claude Fable 5 (Mode Haute Rigueur Mathématique & R&D Systémique)

---

### 1. CONTEXTE GLOBAL DU PROJET & ÉTAT DE L'ART ACQUIS
Vous intervenez en tant qu'**Architecte Principal de Recherche Quantitative** au sein d'une équipe de trading algorithmique haute fréquence.
Le projet porte sur la modélisation mathématique et l'exploitation systématique des indices synthétiques du courtier **Deriv**.

L'historique complet, les codes sources de production, les modèles d'intelligence artificielle ONNX et les audits empiriques des sessions de trading live sont intégralement documentés et accessibles sur le dépôt GitHub officiel du projet :
👉 **Dépôt GitHub du Projet :** https://github.com/Christ-yavn/bot-quant-
*Consultez en priorité :*
- `README.md` : Architecture système globale et résultats comparatifs.
- `CHANGELOG_AND_HISTORY.md` : Évolution de la v1.00 à la v7.00 et falsification empirique.
- `docs/MATHEMATICAL_PROOFS_AND_THEORY.md` : Preuve formelle de la martingale avec friction et convexité de Taleb.
- `docs/MICROSTRUCTURE_DERIV_SPEC.md` : Microstructure des ticks, spread réel (47 à 107 ticks) et TP virtuel.
- `docs/RAPPORT_COMPLET_SESSION_V7.md` : Analyse médico-légale de 1 242 trades live.

#### Ce qui a été formellement prouvé et falsifié en Phase 1 (Boom & Crash) :
1. **Falsification du "Drift Harvesting" (Concavité Ruineuse) :** Le générateur brut de Boom & Crash est une martingale compound Poisson pure ($\hat{n}_{\text{Hawkes}} \approx 0.000$, taux de hasard plat $h(t) \equiv 1/\tau$). Sous spread d'exécution réel $S > 0$, le théorème d'arrêt optionnel de Doob garantit que l'espérance mathématique de capture de dérive est strictement négative ($\mathbb{E}[\text{PnL}] = -S < 0$). En session réelle v7.00, 85.91 % de Win Rate (+0.20 $ avg) s'est soldé par une perte de -406.14 $ due aux queues épaisses négatives (-3.54 $ avg).
2. **Découverte de la Convexité Inversée (Asymétrie Positive de Taleb) :** Inverser la stratégie en chassant le saut avec un stop temporel strict de 60 ticks transforme le payoff en option d'achat synthétique : les pertes fréquentes sont minuscules (-0.25 $ avg) tandis que les gains de spikes sont massifs (+3.48 $ jusqu'à +15.00 $). PnL simulé sur les mêmes 1 242 trades réels : **+340.73 $ net de spread**.

---

### 2. PROTOCOLE SENTINEL VALIDÉ (MÉTHODOLOGIE D'OR DU PROJET)
L'équipe impose le respect strict du **Protocole d'Audit Médico-Légal Sentinel (Itération 16)** illustré dans l'infrastructure de recherche :
* **Frontières chronologiques strictes :** Les 18 partitions (`train`, `val`, `test`) respectent rigoureusement $\max(\text{train}) < \min(\text{val}) \le \max(\text{val}) < \min(\text{test})$. Aucun chevauchement temporel ni fuite informationnelle n'est toléré.
* **Coffre-fort cryptographique :** Empreintes SHA-256 scellées dans `manifest.json`. Toute lecture non autorisée du test set hors échantillon est bloquée et journalisée (`logs/quarantine_audit.log`).
* **Générateur de placebos certifié à espérance nulle :** Tout alpha découvert doit être comparé à un processus de diffusion et sauts de Poisson à moments appariés avec autocorrélations négligeables ($|\rho| < 0.001$).
* **Moteur de tests multiples certifié :** Correction rigoureuse du taux de faux positifs via Benjamini-Hochberg (FDR) et Holm-Bonferroni (FWER).

---

### 3. VOTRE OBJECTIF IMMÉDIAT : CADRAGE MATHÉMATIQUE DE LA PHASE 2
L'équipe passe à la **Phase 2 : Step Index & Indices de Volatilité (V10 à V100 1s)**.
Les données historiques complètes (D1 depuis inception, 15 000 barres H1, 50 000 barres M1, et 300 000 ticks) ont été extraites de MT5 pour 18 symboles cibles.

En tant que Directeur de Recherche Quant, vous devez produire un **Rapport d'Orientation & Spécifications Mathématiques (PhD Level)** couvrant :

#### A. Diagnostic Critique de la Phase 1
* Donnez votre avis d'expert quantitatif sur les réalisations de la v1.00 à la v7.00, la résolution du piège du spread via le TP virtuel, et la découverte de la convexité inversée.

#### B. Modélisation Mathématique Approfondie pour Step Index
* *Nature de l'actif :* Diffusion par pas discrets ($\pm 0.1$) avec microstructure spécifique.
* *Modèles formels à spécifier :*
  1. Chaîne de Markov à temps discret (DTMC) sur l'espace d'états des variations relatives $S = \{-K, \dots, +K\}$. Spécifiez la matrice de transition $P_{ij} = \mathbb{P}(X_{t+1} = j \mid X_t = i)$ et le test d'asymétrie de transition.
  2. Problème du premier temps de passage (First Passage Time - FPT) vers une barrière absorbante : formulation analytique de la distribution de $T_a = \inf \{t \ge 0 : X_t = a\}$.
  3. Tests de mémoire courte vs bruit de Bernoulli : Runs test de Wald-Wolfowitz et autocorrélation des durées (Autoregressive Conditional Duration - ACD).

#### C. Modélisation Mathématique Approfondie pour les Indices de Volatilité (V10 à V100 1s)
* *Nature de l'actif :* Mouvement brownien continu à variance contrôlée ou stochastique.
* *Modèles formels à spécifier :*
  1. Équation différentielle stochastique (EDS) d'Ornstein-Uhlenbeck (OU) pour les régimes de retour à la moyenne : $dX_t = \theta (\mu - X_t) dt + \sigma dW_t$. Formule d'estimation de la demi-vie $t_{\text{half}} = \frac{\ln 2}{\theta}$ et calibration par régression AR(1) discrétisée.
  2. Modélisation de l'hétéroscédasticité conditionnelle : GARCH(1,1) pour la prévision dynamique des clusters de volatilité : $\sigma_t^2 = \omega + \alpha \epsilon_{t-1}^2 + \beta \sigma_{t-1}^2$.
  3. Classification des régimes stochastiques par l'Exposant de Hurst $H$ (analyse R/S et DFA) : seuils stricts pour $H < 0.45$ (Mean-reversion), $0.45 \le H \le 0.55$ (Random Walk pur), et $H > 0.55$ (Momentum / Persistance).
  4. Filtrage d'état de Kalman : formulation pour extraire la dérive locale instantanée $\mu_t$ et la volatilité sous-jacente en temps réel.

#### D. Cahier des Charges & Prompt d'Exécution Détaillé pour l'Équipe de Calcul (Gemini 4 Argon)
* Formulez les étapes algorithmiques exactes, les fonctions de perte, les métriques d'évaluation hors échantillon (Sharpe, Sortino, ratio de Calmar, Max Drawdown sous embargo), et le protocole de rejet d'hypothèse nulle par Benjamini-Hochberg que l'équipe d'exécution (Gemini 4 Argon) devra implémenter sur les jeux de données CSV extraits.

---

### 4. FORMAT DE LIVRAISON ATTENDU
* Structure claire, rigueur universitaire intégrale, toutes équations en KaTeX standard.
* Aucun raccourci ni simplification de complaisance.
