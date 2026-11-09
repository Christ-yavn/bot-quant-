# Arsenal Mathématique, Algorithmique, Cryptographique & Microstructural Complet (`quant-pod` v2)

Ce document constitue le socle théorique de niveau recherche institutionnelle (PhD / Quantitative Desk) utilisé par `quant-pod` v2. Toutes les équations ci-dessous sont directement implémentées dans les 4 moteurs Python du skill :
- [`quant_discovery_engine.py`](file:///C:/Users/CHRIST/.gemini/config/skills/quant-pod/scripts/quant_discovery_engine.py)
- [`quant_validation_engine.py`](file:///C:/Users/CHRIST/.gemini/config/skills/quant-pod/scripts/quant_validation_engine.py)
- [`quant_scientific_arsenal.py`](file:///C:/Users/CHRIST/.gemini/config/skills/quant-pod/scripts/quant_scientific_arsenal.py)
- [`deriv_quant_engine.py`](file:///C:/Users/CHRIST/.gemini/config/skills/quant-pod/scripts/deriv_quant_engine.py)

---

## 1. Décomposition de Doob-Meyer & Condition Fondamentale d'Existence d'un Alpha

Tout processus de log-prix adapté $(X_t)_{t \ge 0}$ qui est une semimartingale spéciale admet une **décomposition canonique unique de Doob-Meyer** :
$$X_t = X_0 + M_t + A_t$$
où :
- $M_t$ est une **martingale locale** ($\mathbb{E}[M_{t+H} - M_t \mid \mathcal{F}_t] = 0$) : imprévisible quelle que soit la sophistication de l'algorithme ou du réseau de neurones.
- $A_t$ est un processus **prévisible à variation finie** ($\mathcal{F}_t$-mesurable) : la dérive conditionnelle prédictible.

### Théorème du Plafond de Doob sous Coûts de Transaction
Pour toute stratégie prévisible bornée $\theta_t \in [-1, +1]$ entrant en $t$ et sortant au temps d'arrêt borné $\tau = t + H$ avec un coût d'exécution aller-retour $C_t = \text{Spread}_{\text{live}, t} + 2 \cdot \text{Fee} + \text{Slippage}_t$ :
$$\mathbb{E}\left[\text{PnL}_{\text{net}}(t, \tau) \;\middle|\; \mathcal{F}_t\right] = \theta_t \cdot \mathbb{E}\left[A_{\tau} - A_t \;\middle|\; \mathcal{F}_t\right] - |\theta_t| \cdot C_t$$

**Conséquence opératoire immédiate** :
1. Si $A_t \equiv 0$ (ex: processus de Poisson compensé sur Boom/Crash ou marche de Rademacher sur Step Index), alors $\mathbb{E}[\text{PnL}_{\text{net}}] = -C_t < 0$ **pour toute règle d'arrêt $\tau$ et tout signe $\theta_t$**.
2. Une stratégie ne peut être rentable que sur le sous-ensemble d'états $\Omega_{\text{alpha}} \subset \mathcal{F}_t$ où la dérive conditionnelle prévisible dépasse strictement la friction :
   $$\left|\mathbb{E}[X_{t+H} - X_t \mid \mathcal{F}_t]\right| > C_t$$

---

## 2. Économétrie Non-Asymptotique du Processus Générateur (DGP)

### A. Test du Ratio de Variance Hétéroscédastique de Lo & MacKinlay (1988)
Pour distinguer une martingale d'un processus à mémoire (momentum ou mean-reversion) en présence de volatilité conditionnelle GARCH :
$$\text{VR}(q) = \frac{\text{Var}(r_t(q))}{q \cdot \text{Var}(r_t)} = 1 + 2 \sum_{k=1}^{q-1} \left(1 - \frac{k}{q}\right) \rho(k)$$
La statistique $z^*(q)$ robuste à l'hétéroscédasticité est :
$$z^*(q) = \frac{\sqrt{T}(\text{VR}(q) - 1)}{\sqrt{\hat{\theta}(q)}}, \quad \hat{\theta}(q) = \sum_{j=1}^{q-1} \left(\frac{2(q-j)}{q}\right)^2 \hat{\delta}_j, \quad \hat{\delta}_j = \frac{T \sum_{t=j+1}^T (r_t - \hat{\mu})^2 (r_{t-j} - \hat{\mu})^2}{\left(\sum_{t=1}^T (r_t - \hat{\mu})^2\right)^2}$$
- $z^*(q) > +1.96 \implies$ **Persistance (Momentum)** à l'horizon $q$.
- $z^*(q) < -1.96 \implies$ **Anti-persistance (Mean-Reversion)** à l'horizon $q$.

### B. Séparation Diffusion Continue vs Sauts (Barndorff-Nielsen & Shephard, 2004)
Sur une fenêtre de $W$ barres, la **Variance Réalisée ($RV_t$)** converge vers la variation quadratique totale (diffusion + sauts), tandis que la **Variation Bi-Puissance ($BV_t$)** converge uniquement vers la variance diffusive continue :
$$RV_t = \sum_{i=0}^{W-1} r_{t-i}^2 \xrightarrow{p} \int_{t-W}^t \sigma_s^2 ds + \sum_{t-W < s \le t} (\Delta X_s)^2$$
$$BV_t = \frac{\pi}{2} \frac{W}{W-1} \sum_{i=0}^{W-2} |r_{t-i}| \cdot |r_{t-i-1}| \xrightarrow{p} \int_{t-W}^t \sigma_s^2 ds$$
La part relative d'énergie due aux sauts discontinus est :
$$\text{JumpRatio}_t = \frac{\max(0, RV_t - BV_t)}{RV_t} \in [0, 1]$$

### C. Estimateur de Volatilité Efficace de Yang-Zhang (2000)
Combine la variance overnight ($r_{o,t} = \ln(O_t / C_{t-1})$), la variance open-to-close ($r_{c,t} = \ln(C_t / O_t)$) et l'estimateur sans dérive de Rogers-Satchell ($RS_t$) pour atteindre une efficacité $14\times$ supérieure à l'écart-type close-to-close :
$$\sigma_{YZ}^2 = \sigma_o^2 + k \sigma_c^2 + (1 - k) \sigma_{RS}^2, \quad k = \frac{0.34}{1.34 + \frac{W+1}{W-1}}$$

### D. Différenciation Fractionnaire à Fenêtre Fixe (FFD — López de Prado)
Préserve la mémoire longue (corrélation élevée avec le log-prix) tout en rendant la série stationnaire ($p_{\text{ADF}} < 0.05$) :
$$(1 - B)^d X_t = \sum_{k=0}^{K(\tau)} w_k X_{t-k}, \quad w_0 = 1, \quad w_k = -w_{k-1} \frac{d - k + 1}{k}, \quad |w_k| \ge \tau$$

---

## 3. Filtrage en Espace d'État, Processus Auto-Excités & Changements de Régime

### A. Filtre de Kalman 1D Causal (Innovation Normalisée)
Modélise le log-prix observé $y_t$ autour d'un état d'équilibre dynamique latent $x_t$ :
$$\begin{cases} x_t = x_{t-1} + \eta_t, & \eta_t \sim \mathcal{N}(0, Q) \\ y_t = x_t + \varepsilon_t, & \varepsilon_t \sim \mathcal{N}(0, R) \end{cases}$$
À chaque pas $t$, l'innovation prédictive $v_t = y_t - \hat{x}_{t|t-1}$ de variance $F_t = P_{t|t-1} + R$ fournit un Z-score sans retard de fenêtre mobile :
$$z_{\text{Kalman}, t} = \frac{y_t - \hat{x}_{t|t-1}}{\sqrt{P_{t|t-1} + R}}$$

### B. Processus Ponctuels Auto-Excités de Hawkes (Cascades de Liquidations)
Les krachs éclair et liquidations forcées sur Crypto/Futures ne suivent pas un processus de Poisson homogène mais un processus de Hawkes dont l'intensité $\lambda(t)$ s'auto-excite à chaque choc $t_i$ :
$$\lambda(t) = \mu + \sum_{t_i < t} \alpha e^{-\beta (t - t_i)}$$
Le **rapport de branchement** $\eta = \alpha / \beta$ mesure l'endogénéité du marché ($\eta \to 1$ indique une criticité de cascade de liquidations). Lorsque l'intensité directionnelle signée dépasse un quantile extrême, l'épuisement des vendeurs/acheteurs forcés crée un rebond de retour à la moyenne (*post-liquidation bounce*).

### C. Test Séquentiel du Rapport de Vraisemblance de Wald (SPRT / Page's CUSUM)
Pour détecter en temps minimal (optimalité de Moustakides) le passage d'une dérive $\mu_0 = 0$ à une dérive $\mu_1 \neq 0$ sous bruit gaussien $\sigma$ :
$$S_t^+ = \max\left(0, S_{t-1}^+ + \frac{r_t - \mu_1 / 2}{\sigma}\right), \quad S_t^- = \max\left(0, S_{t-1}^- + \frac{-r_t - \mu_1 / 2}{\sigma}\right)$$

---

## 4. Cryptanalyse de Générateurs Pseudo-Aléatoires (CSPRNG / PRNG)

Lorsqu'un marché est généré algorithmiquement (indices synthétiques Deriv), l'audit ne cherche pas une « psychologie de foule » (inexistante), mais vérifie si l'implémentation serveur du PRNG ou de la transformation en loi normale présente un défaut mathématique :

1. **Cryptanalyse Polaire de Box-Muller & Effet Neave (1973)** :
   Si un serveur transforme deux uniformes $(U_1, U_2) \in (0,1]^2$ en deux gaussiennes $(Z_1, Z_2)$ via Box-Muller :
   $$Z_1 = \sqrt{-2 \ln U_1} \cos(2\pi U_2), \quad Z_2 = \sqrt{-2 \ln U_1} \sin(2\pi U_2)$$
   alors en inversant les paires consécutives de rendements normalisés $(z_{2k}, z_{2k+1})$ :
   $$\hat{U}_1 = \exp\left(-\frac{z_{2k}^2 + z_{2k+1}^2}{2}\right), \quad \hat{U}_2 = \frac{\text{atan2}(z_{2k+1}, z_{2k}) + \pi}{2\pi}$$
   doivent suivre deux lois uniformes indépendantes sur $[0, 1]$. Si le PRNG sous-jacent est un LCG ou XORShift à faible période, $(z_{2k}, z_{2k+1})$ forme des spirales (effet Neave) et tronque les queues au-delà de $3.5\sigma$ (`audit_gaussian_generator_tails` dans [`quant_discovery_engine.py`](file:///C:/Users/CHRIST/.gemini/config/skills/quant-pod/scripts/quant_discovery_engine.py)).
2. **Complexité Linéaire sur $\mathbb{F}_2$ (Algorithme de Berlekamp-Massey)** :
   Détermine la taille minimale $L$ du registre à décalage à rétroaction linéaire (LFSR) reproduisant une suite binaire de signes de longueur $N$. Pour une vraie source aléatoire, $\mathbb{E}[L] = N/2 + O(1)$. Si $L \ll N/2$, la suite est algébriquement prédictible.
3. **Entropie de Permutation de Bandt & Pompe (2002)** :
   Pour une dimension d'immersion $m$ et un délai $\tau$, compare l'histogramme des $m!$ motifs d'ordre ordinaux à la loi uniforme :
   $$\mathcal{H}_p(m) = -\frac{1}{\ln(m!)} \sum_{\pi \in S_m} p(\pi) \ln p(\pi)$$

---

## 5. Physique de la Microstructure & Coûts Implicites

1. **Spread Effectif Implicite de Roll (1984)** :
   Le rebond Bid-Ask induit une autocovariance négative d'ordre 1 sur les variations de prix :
   $$s_{\text{Roll}} = 2 \sqrt{\max\left(0, -\text{Cov}(\Delta P_t, \Delta P_{t-1})\right)}$$
2. **Illiquidité d'Amihud (2002) & Lambda de Kyle (1985)** :
   $$\text{ILLIQ}_t = \frac{1}{W} \sum_{i=0}^{W-1} \frac{|r_{t-i}|}{\text{Volume}_{\$, t-i}}, \quad \Delta P_t = \lambda_{\text{Kyle}} \cdot \text{OFI}_t + \varepsilon_t$$
3. **Loss-Versus-Rebalancing (LVR — Milionis, Moallemi, Roughgarden)** :
   Coût instantané d'antisélection payé par les fournisseurs de liquidité passifs sur un AMM à fonction constante face aux arbitragistes informés :
   $$\text{LVR}_t = \int_0^t \frac{\sigma_s^2}{8} P_s^2 V''(P_s) ds$$

---

## 6. Statistique des Tests Multiples & Contrôle du Faux Positif (`/boost`)

1. **Deflated Sharpe Ratio (Bailey & López de Prado, 2014)** :
   Soit $\widehat{SR}$ le ratio de Sharpe (non-annualisé par observation) du meilleur essai parmi $K$ essais de variance empirique $\sigma_{\widehat{SR}}^2$ sur un échantillon de taille $T$ d'asymétrie $\hat{\gamma}_3$ et de kurtosis $\hat{\gamma}_4$. Le seuil de bruit maximal attendu sous l'hypothèse nulle est :
   $$SR_0 = \sigma_{\widehat{SR}} \left[ (1 - \gamma_{\text{Euler}}) \Phi^{-1}\left(1 - \frac{1}{K}\right) + \gamma_{\text{Euler}} \Phi^{-1}\left(1 - \frac{1}{K \cdot e}\right) \right]$$
   Et la probabilité que le vrai Sharpe dépasse $SR_0$ est :
   $$\text{DSR} = \Phi\left( \frac{(\widehat{SR} - SR_0)\sqrt{T - 1}}{\sqrt{1 - \hat{\gamma}_3 \widehat{SR} + \frac{\hat{\gamma}_4 - 1}{4}\widehat{SR}^2}} \right) \ge 0.95$$
2. **Probabilité de Sur-Apprentissage du Backtest (PBO via CSCV — Bailey et al., 2017)** :
   En partitionnant la matrice des rendements $M \in \mathbb{R}^{T \times N}$ en $S$ sous-blocs temporels et en formant les $\binom{S}{S/2}$ combinaisons $(J, \bar{J})$ d'entraînement et de test :
   $$\text{PBO} = \frac{1}{\binom{S}{S/2}} \sum_{c} \mathbb{I}\left( \omega_c \le 0.5 \right), \quad \omega_c = \frac{\text{Rang}_{\text{OOS}}(n^*_{\text{IS}})}{N + 1}$$
3. **Bootstrap Stationnaire de Politis & Romano (1994)** :
   Ré-échantillonne par blocs de longueurs géométriques aléatoires $\ell \sim \text{Geom}(1/L)$ pour préserver la dépendance sérielle et l'hétéroscédasticité lors du calcul des intervalles de confiance à $95\%$.
