# CAHIER D'APPROFONDISSEMENT DOCTORAL & R&D DE SECOND TOUR — NIVEAU L99 / PHD
## Destinataire : Claude Fable 5 (Direction de la Recherche Quantitative)
### Réf. : PH2-QUANT-002-L99 | Sujet : Résolution des Frontières Mathématiques de Phase 2 & Protocole d'Exécution Imperméable

---

### 1. RECONNAISSANCE DES APPORTS DU RAPPORT PH2-QUANT-001
La Direction de Recherche prend acte et salue la rigueur sans compromis de votre rapport initial (`PH2-QUANT-001`). Sont formellement intégrés comme axiomes non négociables du projet :
1. **L'Axiome de non-catégorisation (C.0) :** Rejet absolu de tout modèle Ornstein-Uhlenbeck sur le niveau de prix brut des indices Volatility (GBM à vol nominale constante). La mean-reversion est restreinte aux sous-espaces de projection stationnaires : résidus GARCH standardisés $r_t / \hat{\sigma}_t$, scores $z$ de dérive Kalman locale, log-variance réalisée $\ln \text{RV}_t$, et dispersion d'enveloppe.
2. **L'Axiome de minimalité de friction sur Step Index (B.0) :** Priorité d'allocation de recherche sur le Step Index vanilla dont le ratio friction/pas $S/\delta = 1$ maximise le ratio signal/coût par rapport à tout autre actif synthétique.
3. **Le principe de censure et latence sur la convexité inversée (A.2) :** L'exigence formelle d'un bootstrap par blocs stationnaires ($10\,000$ rééchantillons) et de la prise en compte du glissement d'exécution virtuel $A_{\text{capturé}} = A - \epsilon(\tau_{\text{latence}})$ sur les spikes.

Afin d'armer l'équipe de calcul lourd (**Gemini 4 Argon**) avec un niveau de spécification mathématique et algorithmique ultime avant l'exécution sur GPU/Colab, nous ouvrons ce **Second Tour de Cadrage Doctoral (Niveau L99)**. Nous vous demandons de résoudre formellement les **5 frontières théoriques et opérationnelles suivantes** :

---

### 2. LES 5 FRONTIÈRES MATHÉMATIQUES À RÉSOUDRE (NIVEAU DOCTORAL L99)

#### FRONTIÈRE 1 : Topologie du Contrôle Optimal & Équation HJB sur Step Index
Dans votre section B.2, vous formalisez la distribution du premier temps de passage (FPT) vers une barrière absorbante simple. Cependant, en microstructure de trading, les barrières ne sont ni passives ni symétriques : le coût de transaction $S = \delta$ induit une zone d'inactivité (*hysteresis / no-trade region*).
* **Question formelle :** Formulez l'équation de programmation dynamique de **Hamilton-Jacobi-Bellman (HJB) / Enveloppe de Snell** pour le problème d'arrêt optimal :
  $$v(x) = \max \left( g(x), \; \mathbb{E}\left[ e^{-\rho \Delta t} v(X_{t+1}) \mid X_t = x \right] \right)$$
  avec fonction de payoff net $g(x) = (x - S) \cdot \text{vol}$.
* **Dérivation analytique :** Quel est le seuil critique d'asymétrie conditionnelle $\epsilon^* = |p^* - 0.5|$ de la matrice de transition $P_{ij}$ en deçà duquel **AUCUNE politique d'arrêt n'admet d'espérance strictement positive nette de spread** ? Donnez l'expression analytique reliant $\epsilon^*$, l'horizon maximal de détention $M$, et le taux d'actualisation $\rho$.

#### FRONTIÈRE 2 : Cryptanalyse Statistique du Générateur Pseudo-Aléatoire (PRNG)
Les indices synthétiques Deriv ne sont pas des phénomènes physiques naturels mais des flux déterministes émis par des générateurs congruentiels ou des registres à décalage (familles Mersenne Twister MT19937, xoroshiro128+, ou PCG). D'après le théorème de Marsaglia (1968), tout PRNG linéaire concentre ses $n$-uplets dans un nombre fini d'hyperplans (*lattices*).
* **Question formelle :** Comment concevoir une batterie de **tests de distinction statistique de type cryptographique** à appliquer sur les flux de ticks bruts moissonnés (100 000 ticks de Step Index et Volatility 100 1s) ?
* **Spécification :** Formulez le test de complexité linéaire via l'algorithme de **Berlekamp-Massey**, le test d'entropie spectrale de Walsh-Hadamard, et le test de dépendance non-linéaire par information mutuelle conditionnelle $I(X_t ; X_{t+k} \mid X_{t-1}, \dots, X_{t-p})$ pour détecter d'éventuelles périodes de récurrence déterministes ou des défauts de dimension supérieure.

#### FRONTIÈRE 3 : Analyse des Chemins Rugueux (Rough Paths) & Signatures de Trajectoires
Sur les indices de volatilité (notamment la série 1s à 1 tick/seconde), les approches linéaires échouent à capturer la géométrie non-linéaire des chocs conjoints dérive/volatilité. La théorie des chemins rugueux (Terry Lyons, 1998) démontre que la **signature tronquée d'un chemin** $\mathbb{X}_{s,t}^{\le N}$ constitue une base universelle d'approximation des fonctionnelles continues.
* **Question formelle :** Définissez formellement le tenseur de signature de niveau 2 et 3 :
  $$\mathbb{X}_{s,t}^2 = \iint_{s < u_1 < u_2 < t} dX_{u_1} \otimes dX_{u_2}$$
  appliqué au chemin bidimensionnel augmenté du temps $X_t = (t, P_t, \ln \text{RV}_t)^\top$.
* **Application :** Comment utiliser l'aire de Lévy stochastique (la composante antisymétrique de la signature de niveau 2) pour détecter en avance de phase les changements de microstructure ou les transitions de régime avant même qu'elles n'apparaissent dans la moyenne mobile ?

#### FRONTIÈRE 4 : Protocole Exact du Bootstrap Stationnaire (Désamorçage du Biais v7)
Vous avez exigé à juste titre un bootstrap de 10 000 rééchantillons pour conférer un statut d'inférence valide au $+340.73\$$ de la convexité inversée.
* **Question formelle :** Spécifiez l'algorithme exact du **Stationary Bootstrap de Politis & Romano (1994)** ou du **Moving Block Bootstrap de Künsch (1989)** :
  1. Donnez la formule du choix optimal data-driven de la longueur moyenne des blocs $b^*$ (critère de minimisation de l'erreur quadratique moyenne asymptotique de Patton, Politis & White, 2009).
  2. Spécifiez la construction de l'intervalle de confiance non-paramétrique *studentisé* BCa (Bias-Corrected and Accelerated) pour le Sharpe Ratio et le PnL cumulé.
  3. Définissez la règle de décision formelle : à quel seuil de $p$-valeur bootstrap la stratégie inversée est-elle rejetée ?

#### FRONTIÈRE 5 : Spécification d'Implémentation pour Gemini 4 Argon
Pour que Gemini 4 Argon puisse générer le code Python sans aucune latitude d'improvisation :
* Fournissez les **dimensions exactes des tenseurs**, les structures des classes Python recommandées (`StepIndexMarkovEngine`, `RoughSignatureEstimator`, `SentinelValidator`), et le format exact du dictionnaire de métadonnées JSON de sortie scellé par SHA-256 dans `manifest.json`.

---

### 3. FORMAT DE SORTIE ATTENDU
* Niveau mathématique et technique : **L99 / Publication de référence**.
* Formalisme complet, équations standardisées, exhaustivité sans concession.
