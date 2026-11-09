# Playbook de Recherche Quantitative Autonome (`quant-pod` v2)

Ce document définit la méthodologie scientifique permettant au desk `quant-pod` de **découvrir, formuler, tester et faire évoluer** de nouvelles stratégies sur n'importe quel marché, sans jamais tomber dans le *data snooping* ou l'illusion statistique.

---

## 1. Anatomie d'une Fiche d'Hypothèse (`cards/H###.md`)

Aucune ligne de code de backtest ne doit être écrite sans une fiche d'hypothèse préalable enregistrée dans `cards/H###.md`.

### Template obligatoire (`cards/H###.md`)
```markdown
# H### — [Titre court et précis du mécanisme]
- **Date** : YYYY-MM-DD
- **Marché / Univers** : [ex: Crypto Perps Binance/Bybit | Forex G10 | Futures CME | Deriv Synthetics]
- **Horizon / Fréquence** : [ex: M15, H1, Event-driven funding 8h]
- **Statut** : [PROPOSÉE | EN_TEST | RÉFUTÉE | VALIDÉE_BOOST | VALIDÉE_HOLDOUT]
- **Essais cumulés avant H### ($K_{\text{start}}$)** : <int>

## 1. Mécanisme Structurel & Contrepartie (Pourquoi l'edge existe ?)
- **Acteur contraint / Contrepartie perdante** : Qui paie cet alpha et pourquoi ne peut-il pas l'arbitrer immédiatement ? (ex: longs retail utilisant un levier 20x forcés de payer le funding rate ; hedgers commerciaux sur futures matières premières ; rééquilibrage mécanique d'ETF à 16h00 EST ; teneurs de marché élargissant le spread avant annonces macro).
- **Prédiction sur le Processus Générateur (DGP)** : Quelle propriété mesurable du DGP cette hypothèse exploite-t-elle ? (ex: autocorrélation conditionnelle des rendements après compression de volatilité et volume anormal ; prime de variance implicite > réalisée ; mean-reversion post-liquidation en cascade).

## 2. Formule Mathématique Parcimonieuse ($\le 3$ paramètres libres)
- **Signal d'entrée** : [Équation exacte Point-in-Time, uniquement dépendante de $\mathcal{F}_t$]
- **Règle de sortie / Horizon** : [Stop, cible ou horizon fixe $H$]
- **Paramètres libres ($d \le 3$)** :
  1. $\theta_1 \in [a, b]$ (justification physique)
  2. $\theta_2 \in [c, d]$ (justification physique)

## 3. Modèle de Friction Réaliste (Live vs Historique)
- **Spread live mesuré ($\text{bps}$)** : ...
- **Commission aller-retour ($\text{bps}$)** : ...
- **Slippage / Impact de marché estimé ($\text{bps}$)** : ...
- **Coût total 1x ($\text{bps}$)** et **Coût stress 2x ($\text{bps}$)** : ...

## 4. Critère de Falsification Pré-Enregistré (Avant exécution)
- **Condition de rejet immédiat** :
  - $\text{PnL}_{\text{net}}(\text{coûts } 1\times) \le 0$ ou $t\text{-stat} < 2.0$
  - $\text{DSR}(K_{\text{total}}) < 0.95$
  - $p_{\text{null}} > 0.05$ face au DGP nul calibré
  - $\text{Plateau} < 0.60$ sur les voisins de paramètres
```

---

## 2. Les 6 Opérateurs d'Exploration du Chercheur (Génération d'Idées au-delà du Connu)

Lorsqu'une hypothèse échoue ou qu'un nouveau marché est exploré, l'`[ALPHA_RESEARCHER]` utilise ces 6 opérateurs formels pour engendrer des variantes structurellement distinctes (et non du *curve-fitting* cosmétique) :

### Opérateur O1 — Conditionnement de Régime (Filtre d'État Latent)
Un signal d'espérance nulle en inconditionnel peut posséder une espérance positive lorsqu'il est conditionné à un état de marché observable en $\mathcal{F}_t$ :
- **Compression / Expansion de Volatilité** : Ratio de volatilité de Yang-Zhang court/long $\sigma_{\text{short}} / \sigma_{\text{long}} < q_{\alpha}$ combiné à un choc directionnel $|r_t| / \sigma_t > z$.
- **Régime de Liquidité / Carnet d'Ordres** : Déséquilibre du carnet (Order Book Imbalance $\text{OBI}$), VPIN (Volume-Synchronized Probability of Informed Trading) ou élargissement soudain du spread Bid-Ask.
- **Régime Macro / Calendrier** : Fenêtres temporelles autour des fixings (WM/Reuters 16h00 Londres, ouverture US 09h30 EST, settlement des options à 08h00 UTC sur Deribit).

### Opérateur O2 — Inversion de Munger & Changement d'Exécution
Si une stratégie directionnelle perd de l'argent :
1. **Décomposer la perte** : Quelle part vient du mouvement brut des prix ($\text{PnL}_{\text{gross}}$) et quelle part vient des coûts de transaction ($N_{\text{trades}} \times \text{Coût}$) ?
   - *Règle théorique (Plafond de Doob)* : Si $\text{PnL}_{\text{gross}} \approx 0$ et que la perte égale exactement $-\text{Spread}$, inverser les signaux (acheter au lieu de vendre) **ne produira aucun gain** — la stratégie inversée perdra elle aussi $-\text{Spread}$.
   - En revanche, si $\text{PnL}_{\text{gross}}$ est significativement négatif ($|\text{PnL}_{\text{gross}}| \gg 2 \times \text{Spread}$), l'inversion du signal transforme un mauvais système de *breakout* en système de *mean-reversion* (ou inversement).
2. **Inversion du type d'ordre (Taker $\to$ Maker)** : Si l'alpha brut est réel mais inférieur au spread Taker ($0 < \text{Alpha}_{\text{brut}} < \text{Spread}_{\text{Taker}}$), remplacer l'exécution au marché par des ordres limites passifs (*Maker*) sur carnet d'ordres (CEX, ECN, Futures) pour capturer le spread au lieu de le payer (en modélisant le risque de *adverse selection* sur les ordres exécutés).

### Opérateur O3 — Transfert Inter-Marchés (Lead-Lag & Cross-Asset)
Exploiter la vitesse de diffusion de l'information entre actifs liés :
- **Spot vs Futures Perpétuels (Basis & Funding)** : Divergence entre le prix Spot (Coinbase/Binance) et le contrat perpétuel, ou taux de financement extrême signalant un encombrement spéculatif (*crowded positioning*).
- **Leader vs Laggard Sectoriel** : Diffusion d'un choc de volatilité ou de rendement de BTC/ETH vers les altcoins liquides à bêta élevé, ou des taux US (ZN/ZB) vers les paires Forex (USD/JPY).
- **Implicite vs Réalisé** : Ratio entre la volatilité implicite des options (VIX, DVOL Deribit) et la volatilité réalisée haute fréquence (Yang-Zhang / Realized Kernel).

### Opérateur O4 — Contraintes Institutionnelles & Flux Forcés
Chercher les moments où un participant **doit** négocier indépendamment du prix :
- **Cascades de Liquidations (Crypto CEX/DEX)** : Lorsque l'Open Interest baisse violemment pendant une mèche de prix avec un funding très positif/négatif, les liquidations forcées créent une dislocation temporaire suivie d'un retour à la moyenne (*post-liquidation bounce*).
- **Cycles de Funding Rate (toutes les 8h : 00:00, 08:00, 16:00 UTC)** : Flux prévisibles d'entrée/sortie dans les minutes précédant et suivant le prélèvement du funding.
- **Effets de Fin de Mois / Roll de Futures** : Pression acheteuse/vendeuse prévisible lors du roulement des contrats futures (ex: S&P 500, pétrole WTI, bons du Trésor).

### Opérateur O5 — Combinaison Orthogonale de Signaux Faibles
Deux signaux faiblement prédictifs ($s_1, s_2$) mais **faiblement corrélés** ($\text{Corr}(s_1, s_2) < 0.25$) ont un ratio de Sharpe combiné supérieur :
$$\text{SR}_{\text{combiné}} = \frac{\text{SR}_1 + \text{SR}_2}{\sqrt{2(1 + \rho_{12})}}$$
*Attention* : Ne jamais combiner 5 indicateurs colinéaires (ex: RSI + Stochastique + CCI + Williams %R = 4 fois le même oscillateur de prix). Combiner uniquement des familles d'information orthogonales :
1. **Prix / Volatilité** (ex: compression Yang-Zhang)
2. **Volume / Flux d'ordres** (ex: CVD — Cumulative Volume Delta, ou volume relatif anormal)
3. **Positionnement / Coût de portage** (ex: Open Interest, Funding Rate, Basis)

### Opérateur O6 — Réduction de Fréquence & Filtrage d'Horizon
Si l'alpha par trade en M1/M5 est de $+1.5\text{ bps}$ mais que le spread + slippage coûte $4.0\text{ bps}$, augmenter l'horizon de détention ($H \in \text{H1, H4, D1}$) : la volatilité croît en $\sqrt{H}$ tandis que le coût d'entrée/sortie reste fixe par transaction.

---

## 3. Cartographie Réaliste des Marchés : Où Chercher de Vrais Edges ?

L'`[ALPHA_RESEARCHER]` doit orienter l'effort de recherche là où des contreparties humaines ou institutionnelles créent de vraies inefficiences :

| Famille de Marché | Existence de Contreparties Contraintes ? | Sources d'Alpha Documentées & Testables | Pièges Mortels à Éviter |
| :--- | :--- | :--- | :--- |
| **Crypto CEX (Perps & Spot)** | **OUI (Élevée)** : Retail à fort levier, mineurs, arbitragistes de funding, liquidations automatiques. | Arbitrage Cash-and-Carry / Funding Rate ; Rebond post-liquidation forcée (Open Interest drop) ; Momentum cross-sectionnel conditionné au volume ; Breakout de compression de volatilité sur H1/H4. | Frais Taker (4-6 bps/side) sur scalping M1 ; biais de survivance des tokens délistés ; délais de latence API lors des krachs. |
| **Crypto DEX / On-Chain** | **OUI (Moyenne à Élevée)** : LP passifs sur AMM ($x \cdot y = k$), traders retail avec tolérance de slippage élevée. | Arbitrage CEX-DEX (Loss-Versus-Rebalancing des LP) ; suivi de flux on-chain vérifiables avant listage ou rééquilibrage. | MEV / Sandwich attacks ; frais de gas ; honeypots et tokens illiquides. |
| **Futures (CME Indices, Taux, Commodités)** | **OUI (Institutionnelle)** : Hedgers commerciaux, CTA trend-followers, fonds à parité de risque, rolls calendaires. | Time-Series Momentum (TSMOM Moskowitz et al.) sur H4/D1 ; Carry / Roll-yield sur courbes à terme ; Saisonnalité intraday autour des ouvertures/clôtures cash. | Sous-estimer la taille minimale de contrat et le risque overnight. |
| **Forex (Spot / CFD)** | **OUI (Banques centrales, entreprises, hedgers)** | Carry trade conditionné au régime de risque global ; Momentum post-annonces macro (PEAD / surprises de taux) ; Effets de fixing 16h00 Londres. | Scalping M1 sur CFD retail (le spread absorbe tout) ; croire aux patterns de chandeliers isolés sur EUR/USD M5. |
| **Actions & Options** | **OUI (Fonds indiciels, retail, hedgers)** | Post-Earnings Announcement Drift (PEAD) ; Prime de risque de variance (VRP : vendre de la vol implicite couverte quand IV $\gg$ RV) ; Momentum factoriel résiduel. | Biais de survivance ; look-ahead sur la date exacte de publication des bilans (utiliser la date *filing* PIT). |
| **Indices Synthétiques Deriv (CSPRNG)** | **NON (Contrepartie = Broker algorithmique)** | **Uniquement si un défaut de paramétrage du générateur existe** (ex: dépendance d'état GARCH mal tarifée dans le spread). Sur Boom/Crash et Step Index, le DGP mesuré est une martingale sans mémoire ($\text{EV} = -\text{Spread}$). | **Illusion majeure** : Croire que le Smart Money Concept (SMC, Order Blocks, FVG) ou la prédiction de spikes fonctionne sur un générateur cryptographique mémoire-zéro. |

---

## 4. Règle d'Arrêt de la Boucle de Recherche (`K_max`)

Pour éviter qu'une boucle autonome ne finisse par sur-optimiser le bruit à force d'itérer :
1. Avant de lancer une campagne de recherche, fixer un budget maximal d'essais $K_{\text{max}}$ (typiquement $K_{\text{max}} \le 20$ variantes d'hypothèses sur un même jeu de données).
2. À chaque itération $k \in \{1, \dots, K_{\text{max}}\}$, enregistrer l'essai dans `ResearchLedger` et recalculer $\text{DSR}(K_{\text{total}})$ où $K_{\text{total}}$ inclut **tous** les essais historiques sur ce dataset.
3. Si $K_{\text{total}}$ atteint $K_{\text{max}}$ sans qu'aucune variante ne franchisse simultanément les 5 portes `/boost`, **arrêter la recherche sur cet actif/dataset** et conclure par un verdict `[FALSIFIÉ]` documenté dans `TRUTH.md`.
