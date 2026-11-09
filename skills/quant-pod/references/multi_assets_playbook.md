# Playbook Multi-Actifs Institutionnel : Crypto CEX/DEX, Futures, Forex, CFDs & Options (`quant-pod` v2)

Contrairement aux indices synthétiques générés par un CSPRNG, les marchés financiers réels (Crypto, Futures, Forex, Actions/Options) réunissent des **participants aux contraintes asymétriques** (hedgers commerciaux, fonds indiciels à rééquilibrage mécanique, spéculateurs retail en fort levier soumis aux appels de marge, fournisseurs de liquidité passifs). Ce sont ces contraintes qui créent la composante prévisible $A_t$ de la décomposition de Doob-Meyer.

---

## 1. Crypto : Contrats Perpétuels CEX (Binance, Bybit, Hyperliquid) & DEX On-Chain

### Stratégie Famille C1 — Arbitrage & Conditionnement de Funding Rate (Cash-and-Carry / Crowded Positioning)
- **Contrepartie perdante** : Traders particuliers utilisant un levier $10\times$ à $50\times$ qui paient le taux de financement (*Funding Rate*) toutes les 8 heures pour maintenir des positions directionnelles encombrées.
- **Deux modes d'exploitation** :
  1. **Delta-Neutre (Pur Portage)** : Long Spot (ou actif de staking liquide) + Short Perpétuel 1x lorsque le funding annualisé dépasse un seuil $\theta_{\text{entry}}$ (ex: $> 15\%\text{/an}$), sortie lorsque le funding redevient neutre et que l'écart de base (*Basis*) amortit $3\times$ les frais aller-retour.
  2. **Directionnel Contrarian Post-Exces de Funding + Chute d'Open Interest** : Lorsque le funding est dans son 95e percentile historique ET qu'un choc de prix provoque une baisse brutale de l'Open Interest (confirmant une cascade de liquidations forcées), entrer en rebond via `hawkes_shock_intensity` ([`quant_discovery_engine.py`](file:///C:/Users/CHRIST/.gemini/config/skills/quant-pod/scripts/quant_discovery_engine.py)).

### Stratégie Famille C2 — Cascades Auto-Excitées de Hawkes (Post-Liquidation Bounce H1/M15)
- **Mécanisme physique** : Les moteurs de liquidation des CEX et protocoles DeFi vendent/achètent au marché sans sensibilité au prix, créant une grappe de chocs ($\eta = \alpha / \beta \to 1$) suivie d'un vide d'offre et d'un retour élastique vers la juste valeur de Kalman.
- **Formule Point-in-Time** :
  $$\text{Signal}_t = -\text{ZScore}_{72}\left(\lambda_{\text{Hawkes}}(r_t; z_{\text{seuil}}=2.0, \beta=0.30)\right) \times \mathbb{I}\left(\text{JumpRatio}_{24, t} > 0.35\right)$$

### Stratégie Famille C3 — Breakout de Compression de Volatilité Conditionné au Flux de Volume Réel
- **Différence cruciale avec Deriv** : Sur BTC/ETH/SOL, une compression de volatilité de Yang-Zhang ($\sigma_{YZ, 16} / \sigma_{YZ, 96} < 0.80$) accompagnée d'une **explosion du volume signé** ($\text{Volume}_t > 2.0 \times \text{MA}_{48}(\text{Volume})$) traduit l'entrée d'un flux institutionnel réel.
- **Horizon** : H1 ou H4 (où la volatilité par barre est de $40$ à $120\text{ bps}$, soit $10\times$ à $20\times$ les frais Maker/Taker).

### Stratégie Famille C4 — DEX AMM & Couverture du Loss-Versus-Rebalancing (LVR)
- **Équation de Milionis et al.** : Le coût d'antisélection payé aux arbitragistes MEV par un LP sur Uniswap v3/v4 est $\text{LVR}_t = \int_0^t \frac{\sigma_s^2}{8} P_s^2 V''(P_s) ds$.
- **Règle de décision** : Ne fournir de la liquidité concentrée que lorsque $\text{Fees}_{\text{attendus}}(t, t+H) > 1.5 \times \widehat{\text{LVR}}(t, t+H)$ estimé via la volatilité Yang-Zhang, en couvrant le delta par un perpétuel.

---

## 2. Futures & Matières Premières / Indices (CME : ES, NQ, GC/Or, CL/Pétrole, ZN/Taux)

### Stratégie Famille F1 — Time-Series Momentum Adaptatif au Régime (TSMOM + Filtre d'Autocorrélation)
- **Contrepartie perdante** : Hedgers commerciaux et rééquilibrages lents de fonds institutionnels (Moskowitz, Ooi & Pedersen, 2012).
- **Formule Point-in-Time (`AlphaPrimitives` dans [`quant_discovery_engine.py`](file:///C:/Users/CHRIST/.gemini/config/skills/quant-pod/scripts/quant_discovery_engine.py))** :
  - Utiliser la série différenciée fractionnairement (`frac_diff_ffd` avec $d^* \approx 0.35$) ou le filtre de régime d'autocorrélation locale (`rolling_autocorr_regime`) pondéré par la volatilité cible (`compute_volatility_targeted_weights`).

### Stratégie Famille F2 — Décomposition du Roll Yield (Backwardation vs Contango)
- **Équation de portage** : $F_{t, T} = S_t e^{(r_t + u_t - \delta_t)(T - t)}$.
- **Signal Cross-Sectionnel** : Acheter les contrats en forte *Backwardation* ($F_{t, T_1} > F_{t, T_2}$, convenience yield $\delta_t$ élevé) et vendre ceux en fort *Contango* corrigé du momentum de court terme.

### Stratégie Famille F3 — Asymétrie Intraday d'Ouverture/Clôture Cash (09h30 – 16h00 EST)
- **Mécanisme physique** : Les ETF à levier et les hedgers d'options (0DTE / Gamma hedging) concentrent leurs flux directionnels dans les 30 premières et 30 dernières minutes de la séance cash US.

---

## 3. Forex & CFDs (G10, XAUUSD, Indices Cash)

### Stratégie Famille FX1 — Flux Contraints aux Fixings Institutionnels (Tokyo 00h55 UTC & Londres WM/Reuters 16h00 UTC)
- **Contrepartie perdante** : Entreprises multinationales et gestionnaires d'actifs passifs qui passent des ordres au fixing quel que soit le prix pour répliquer leurs indices de référence (surtout en fin de mois / fin de trimestre).
- **Mécanisme** : Dérive pré-fixing suivie d'une réversion post-fixing (16h00 $\to$ 16h30 Londres) mesurable par l'innovation du filtre de Kalman (`kalman_state_space_zscore`).

### Stratégie Famille FX2 — Carry Trade Filtré par le Régime de Stress Global
- **Mécanisme** : Le différentiel de taux d'intérêt ($i_{\text{long}} - i_{\text{short}}$) offre un rendement positif constant en régime calme, mais subit une asymétrie négative violente lors des chocs de liquidité.
- **Filtre de protection** : Couper ou inverser l'exposition Carry dès que la volatilité Yang-Zhang courte dépasse $1.4 \times$ la volatilité longue ou que le détecteur CUSUM signale une cassure baissière.

---

## 4. Actions & Options (Statistical Arbitrage & Prime de Variance)

1. **Prime de Risque de Variance (VRP : Implicite vs Réalisée)** :
   Les investisseurs paient structurellement une prime d'assurance ($\text{IV}_t > \mathbb{E}[\text{RV}_{t, t+H}]$). Vendre de la volatilité couverte uniquement lorsque le ratio $\text{IV}_t / \hat{\sigma}_{YZ, t}$ dépasse son 80e percentile historique et que `JumpRatio` est bas.
2. **Statistical Arbitrage par Filtre de Kalman & Ornstein-Uhlenbeck** :
   Sur des paires d'actifs économiquement liés (ex: valeurs minières vs Or, ou actions dual-class), estimer la demi-vie $HL = \ln(2)/\theta$ via `estimate_ou_half_life` ([`quant_scientific_arsenal.py`](file:///C:/Users/CHRIST/.gemini/config/skills/quant-pod/scripts/quant_scientific_arsenal.py)) et n'entrer que si $5 \le HL \le 30$ périodes.
