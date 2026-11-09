# Encyclopédie Critique des 11 Familles Synthétiques Deriv : Modèles DGP, Cryptanalyse & Limites Réelles (`quant-pod` v2)

Sur Deriv, les prix ne sont pas formés par un carnet d'ordres d'acheteurs et de vendeurs humains, mais par un **générateur de nombres pseudo-aléatoires cryptographique (CSPRNG)** exécuté côté serveur selon des équations différentielles stochastiques (EDS) programmées.

> **Règle d'Honnêteté Scientifique (`quant-pod` v2)** :
> Ne jamais plaquer de concepts de psychologie humaine (Smart Money Concepts, Order Blocks, chasse aux stops retail) sur un générateur algorithmique. Sur un indice synthétique, seules **deux sources d'alpha** peuvent mathématiquement exister :
> 1. **Une dépendance d'état programmée dans l'EDS du serveur** (ex: changement de dérive Markovien sur DSI, mémoire de durée Weibull $k \neq 1$ sur Trek, ou clustering de volatilité mal intégré dans le prix d'une barrière) **à condition que l'alpha brut par trade dépasse strictement le spread live**.
> 2. **Un défaut d'implémentation statistique/cryptographique** dans la transformation uniforme $\to$ normale/exponentielle (ex: troncature des queues de Box-Muller ou erreur de tarification analytique d'un contrat d'option).

---

## 1. Les 3 Lois Mathématiques Inviolables sur Crash & Boom (`[MESURÉ]`)

1. **Loi de Poisson / Géométrique Sans Mémoire (Memorylessness)** :
   L'arrivée d'un Spike suit un processus de Bernoulli/Poisson d'intensité constante $\lambda = 1 / N$ par tick ($N \in \{150, 300, 500, 600, 900, 1000\}$) :
   $$h(\tau) = \mathbb{P}(\text{Spike à } t+1 \mid \text{aucun Spike depuis } \tau \text{ ticks}) = \lambda$$
   Sur 6,8 millions de ticks réels (`ETAT_DE_LA_VERITE.md`), le coefficient de variation inter-spikes vaut $\text{CV} \approx 1.00$ et $\text{ACF}(1) \approx 0$. Attendre $1\,500$ ticks sans spike ne modifie en rien la probabilité du tick suivant.
2. **Théorème d'Arrêt Optionnel de Doob (Plafond de Martingale)** :
   La trajectoire brute est calibrée par le serveur pour être une martingale compensée :
   $$dS_t = \mu_{\text{drift}} dt + J_t dN_t, \quad \mu_{\text{drift}} + \lambda \mathbb{E}[J_t] \approx 0$$
   Par le théorème de Doob, pour **tout** temps d'arrêt borné $\tau$ et **tout** sens de position (scalping de dérive v7 ou achat de convexité post-spike v8), l'espérance nette vaut exactement :
   $$\mathbb{E}[\text{PnL}_{\text{net}}] = -\text{Spread}_{\text{live}} \times \text{Lot} < 0$$
   *Attention au piège du backtest MT5* : les fichiers historiques MT5 affichent un spread fictif de `1 point`, alors que le spread live réel vaut `300 à 2600 points` (96,5 % de la perte réelle).
3. **Slippage Intégral de Saut (Gap-Through Stop-Loss)** :
   Un Stop-Loss placé dans le sens opposé à un Spike subit l'intégralité de l'amplitude du saut discontinu.

---

## 2. Anatomie Mathématique & Protocole de Test des 11 Familles

### Famille 1 : Crash & Boom Indices (150, 300, 500, 600, 900, 1000)
- **Équation DGP** : Processus de Poisson composé compensé à dérive déterministe par tick.
- **Protocole d'Audit (`audit_boom_crash` dans [`deriv_quant_engine.py`](file:///C:/Users/CHRIST/.gemini/config/skills/quant-pod/scripts/deriv_quant_engine.py))** :
  - Vérifier si $|\mu_{\text{drift}} + \lambda \mathbb{E}[J_t]| > \text{Spread}_{\text{live}} / H$.
  - Sur les données empiriques mesurées des 6 indices standards, $\text{EV}_{\text{net}} < 0$ : **interdiction formelle d'abaisser `InpMinEvUsd` sous `+0.02$`** pour forcer des trades.

### Famille 2 : Drift Switch Indices (DSI 10, 20, 30)
- **Équation DGP** : Diffusion à saut de régime de Markov caché $S_t \in \{+1, 0, -1\}$ où la dérive $\mu(S_t)$ reste constante pendant une durée aléatoire avant de basculer.
- **Vecteur de Recherche (`cusum_sprt_regime_detector`)** :
  - Détecter le changement d'état $S_t$ par le filtre séquentiel optimal **CUSUM / SPRT de Wald**.
  - **Condition de viabilité `[HYPOTHÈSE À TESTER]`** : La durée moyenne résiduelle du régime après le délai de détection $\tau_{\text{CUSUM}}$ multipliée par $|\mu_{\text{régime}}|$ doit excéder $2 \times \text{Spread}_{\text{live}}$.

### Famille 3 : DEX Indices (DEX 600, 900, 1500 UP/DOWN)
- **Équation DGP** : Diffusion à sauts doubles asymétriques (modèle de Kou : petits sauts fréquents + grands sauts directionnels rares).
- **Protocole d'Audit** : Décomposition Bi-Puissance (`barndorff_nielsen_jump_decomposition` dans [`quant_discovery_engine.py`](file:///C:/Users/CHRIST/.gemini/config/skills/quant-pod/scripts/quant_discovery_engine.py)) et test d'information mutuelle entre les grappes de petits sauts et les grands sauts.

### Famille 4 : Classic Step Indices (Step 100 à 500)
- **Équation DGP** : Marche aléatoire symétrique de Rademacher ($\Delta P_t \in \{-s, +s\}$ avec $p = 0.50$).
- **Réalité Empirique (`[MESURÉ]`)** : Sur 1,37 million de ticks (`ETAT_DE_LA_VERITE.md`), $p = 0.5008$, $\text{ACF}(1) \approx 0$, complexité linéaire de Berlekamp-Massey $\approx N/2$. C'est une martingale pure : toute stratégie directionnelle a $\mathbb{E}[\text{PnL}] = -\text{Spread}$.

### Famille 5 : Multi Step Indices (Multi Step 2, 3, 4)
- **Équation DGP** : Marche symétrique en signe à pas discrets multiples ($\pm 0.1$ fréquent, $\pm 0.2 \dots 0.5$ rares).
- **Protocole d'Audit** : Tester l'indépendance entre l'amplitude $|\Delta P_t|$ et le signe suivant $\text{sign}(\Delta P_{t+1})$ via $\chi^2$ d'indépendance et ratio de variance Lo-MacKinlay.

### Famille 6 : Skew Step Indices (Skew Step 4, 5 UP/DOWN)
- **Équation DGP** : Marche discrète asymétrique compensée (80–90 % de petits pas dans un sens, 10–20 % de pas plus grands opposés, de sorte que $\mathbb{E}[\Delta P_t] = 0$).
- **Protocole d'Audit** : Vérifier si la compensation exacte $\sum p_i \Delta x_i = 0$ présente un biais résiduel supérieur au spread.

### Famille 7 : Trek Indices (Trek UP, Trek DOWN)
- **Équation DGP** : Processus gouverné par une loi de durée de Weibull $f(\tau; k, \lambda) = \frac{k}{\lambda}\left(\frac{\tau}{\lambda}\right)^{k-1} e^{-(\tau/\lambda)^k}$.
- **Vecteur de Recherche** : Si l'exposant de forme estimé par Maximum de Vraisemblance vérifie $k \neq 1$ de façon statistiquement significative hors-échantillon, le taux de hasard $h(\tau) \propto \tau^{k-1}$ dépend de l'âge $\tau$ depuis le dernier événement (contrairement à Boom/Crash où $k = 1$).

### Famille 8 : Range Break Indices (Range Break 100, 200)
- **Équation DGP** : Processus confiné entre deux barrières $[L_t, U_t]$ avec probabilité géométrique de cassure.
- **Protocole d'Audit** : Vérifier le slippage réel d'exécution des ordres Stop à la frontière du range ($U_t, L_t$) avant de conclure à un edge de breakout.

### Famille 9 : Jump Indices (Jump 10, 25, 50, 75, 100)
- **Équation DGP** : Diffusion à sauts de Merton (diffusion continue + sauts symétriques de Poisson).
- **Protocole d'Audit** : Utiliser `barndorff_nielsen_jump_decomposition` et `hawkes_shock_intensity` pour tester s'il existe une réversion ou une persistance post-saut sur barres M1/M5/H1.

### Famille 10 : Volatility Indices (V10 à V250, Standard & 1s)
- **Équation DGP** : Mouvement Brownien Géométrique discret à volatilité cible programmée.
- **Réalité Empirique (`[MESURÉ]`)** :
  - Les valeurs absolues des rendements $|r_t|$ présentent parfois une légère dépendance ($\text{ACF}(|r|, 1) > 0$), mais les rendements signés ont $\text{ACF}(r, 1) \approx 0$.
  - La stratégie `VolSqueeze (q=0.30, z=1.25, H=4)` qui semblait donner $t = 3.33$ sur 15 000 barres de `V25(1s)` échoue au test `/boost` global ($\text{DSR}(K=1500) = 0.053$, $p_{\text{null}} = 0.171$, et $t = 1.58$ sur 56 046 barres).
  - Audit cryptographique disponible via `audit_gaussian_generator_tails` (test polaire de Box-Muller et queues à $3.5\sigma$).

### Famille 11 : Contrats à Paiement Fixe (Accumulators, Multipliers, Turbos, Vanillas)
- **Équation Analytique (`accumulator_survival_probability`)** :
  $$P_{\text{survie}}(K) = \left[\Phi\left(\frac{b}{\sigma \sqrt{\Delta t}}\right) - \Phi\left(-\frac{b}{\sigma \sqrt{\Delta t}}\right)\right]^K, \quad \text{EV} = (1 + g)^K P_{\text{survie}}(K) - 1$$
- **Réalité Empirique (`[MESURÉ]`)** : Le scanner live (`deriv_fair_value_scanner.py`) sur 349 contrats a mesuré $0 / 349$ contrats avec $\text{EV} > 0$ ($\text{EV}_{\text{moyen}} = -6.58\%$). Ne jamais trader ces contrats sans qu'un scan temps réel ne prouve un écart de volatilité implicite/réalisée générant $\text{EV}_{\text{net}} > +1\%$.
