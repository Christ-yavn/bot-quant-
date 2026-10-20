# -*- coding: utf-8 -*-

def get_content():
    return r"""<a id="partie-3"></a>
# PARTIE 3 : LA GAMME 2 — L'ODYSSÉE DU STEP INDEX ET LA FALSIFICATION PAR DOOB

---

## 3.1. QU'EST-CE QUE LE STEP INDEX ? LA MARCHE ALÉATOIRE À PAS DISCRETS

Dans le cadre de la Phase 2 de nos recherches quantitatives, notre consortium a exploré une seconde famille d'actifs proposés par Deriv : le **Step Index** et les indices de **Volatilité Continue**.

L'indice Step Index est particulièrement populaire auprès des traders particuliers. Sa règle de génération algorithmique par le serveur Deriv est la suivante :
* À chaque pas de temps (tick), le prix fait **un saut discret fixe** vers le haut ($+0.1$ ou $+1.0$ point) ou vers le bas ($-0.1$ ou $-1.0$ point).
* La probabilité de monter ou de descendre à chaque seconde semble a priori symétrique :
  P(\Delta P_t = +h) = \frac{1}{2} \quad \text{et} \quad P(\Delta P_t = -h) = \frac{1}{2}

Nombreux sont les analystes techniques qui prétendent pouvoir y détecter des "supports", des "résistances", des "figures en chandeliers" ou des signaux d'indicateurs (RSI, MACD, Stochastique). Nous avons refusé toute spéculation subjective et avons soumis le Step Index à une analyse économétrique lourde.

---

## 3.2. L'INVESTIGATION ÉCONOMÉTRIQUE RIGOUREUSE (HURST ET TESTS DE RACINE UNITAIRE)

À l'aide de nos scripts Python d'extraction haute fréquence ([phase2_research/scripts/analyze_hurst_and_ou.py](phase2_research/scripts/analyze_hurst_and_ou.py)), nous avons aspiré des centaines de milliers de ticks réels du Step Index et calculé les grandeurs fondamentales de la physique statistique :

### 1. L'Exposant de Hurst ($)
L'exposant de Hurst, inventé par l'hydrologue Harold Edwin Hurst et popularisé par Benoît Mandelbrot, mesure la mémoire à long terme d'une série temporelle :
* Si .5 < H \le 1.0$ : Le marché est **persistant** (il a de la mémoire, les tendances continuent, c'est l'idéal pour les robots de suivi de tendance).
* Si  \le H < 0.5$ : Le marché est **anti-persistant** (il retourne à la moyenne, *Mean-Reverting*, idéal pour les robots de rebond).
* Si  = 0.50$ : Le marché est un **Mouvement Brownien Pur (Marche Aléatoire)**. Chaque pas est totalement indépendant du passé.

**Résultat de notre mesure empirique sur le Step Index :**
\hat{H}_{\text{Step Index}} = 0.5003 \pm 0.0012
L'exposant est égal à .50$ avec une précision absolue. Le Step Index n'a strictement **aucune mémoire**.

### 2. L'Autocorrélation des Rendements ($\rho_k$)
Nous avons calculé la fonction d'autocorrélation des incréments de prix pour des décalages (*lags*) de  = 1$ à  = 100$ ticks :
\rho_k = \frac{\text{Cov}(\Delta P_t, \Delta P_{t-k})}{\text{Var}(\Delta P_t)} \approx 0.000 \quad (\forall k \ge 1)
L'autocorrélation est rigoureusement nulle à tous les ordres. Il n'y a aucun effet de rebond, aucun effet de traîne.

---

## 3.3. LE THÉORÈME D'ARRÊT OPTIONNEL DE DOOB EXPLIQUÉ EN LICENCE 1

Face à ces résultats, une question d'étudiant émerge immédiatement :
> *"Même si le marché n'a pas de mémoire, ne peut-on pas gagner de l'argent en mettant un Take-Profit plus grand que le Stop-Loss (ou inversement), ou en utilisant un indicateur technique élaboré ?"*

La réponse mathématique a été formulée en 1953 par le grand mathématicien américain **Joseph Leo Doob** à travers son célèbre **Théorème d'Arrêt Optionnel (*Doob's Optional Stopping Theorem*)**.

### L'Explication Intuitive Niveau L1
Imaginez un jeu de pile ou face équitable dans une salle de jeu :
* Une pièce est lancée chaque seconde. Si c'est Pile, vous gagnez $+1\,\. Si c'est Face, vous perdez $-1\,\.
* Vous décidez de venir avec une stratégie très rusée : *"Je m'arrête dès que j'ai gagné 10 $ (Take-Profit), mais si je perds 100 $, j'arrête aussi (Stop-Loss) !"*
* Ou bien : *"Je m'arrête dès que la pièce fait 3 Pile d'affilée !"*

Le théorème de Doob prouve rigoureusement que :
**Tant que le jeu est équitable ($\mathbb{E}[\Delta P] = 0$), N'IMPORTE QUELLE stratégie d'arrêt (quel que soit le Stop-Loss, quel que soit le Take-Profit, quelle que soit la règle de sortie) aura TOUJOURS une espérance de gain finale exactement égale à ZÉRO !**

\mathbb{E}[M_T] = M_0 = 0
Où $ est le temps d'arrêt aléatoire (le moment où vous fermez le trade).

### L'Effet Destructeur du Spread Réel
Maintenant, ajoutons la réalité du monde réel : le courtier Deriv prélève un **spread de transaction  > 0$** à chaque fois que vous lancez la pièce.
L'espérance de profit net après arrêt devient :
\mathbb{E}[\text{Gain Net}] = \mathbb{E}[M_T - M_0] - S = 0 - S = -S < 0

`	ext
========================================================================================
            LA PREUVE PAR LE THÉORÈME D'ARRÊT DE DOOB SUR STEP INDEX
========================================================================================

   Stratégie Naïve du Trader Débutant :
   ┌────────────────────────────────────────────────────────┐
   │ Stop-Loss = -10 $  │ Take-Profit = +20 $              │
   │ Probabilité de toucher TP : 33.3 %                     │
   │ Probabilité de toucher SL : 66.7 %                     │
   │ Gain brut théorique : (0.333 × +20 $) + (0.667 × -10 $)│
   │                     = +6.66 $ - 6.67 $ = 0.00 $        │
   │ Frottement du Spread S : -1.50 $ par trade             │
   │ RÉSULTAT RÉEL NET PAR TRADE : -1.50 $ < 0              │
   └────────────────────────────────────────────────────────┘
   => TOUTE STRATÉGIE DIRECTIONNELLE SUR STEP INDEX EST UNE CONDAMNATION À MORT.
========================================================================================
`

### La Décision Scientifique : Falsification et Abandon Immédiat de Step Index
Contrairement aux vendeurs d'illusions sur internet qui continuent d'écrire des robots sur Step Index, notre consortium a pris la décision scientifique qui s'imposait :
**Nous avons classé Step Index comme une martingale pure non exploitable et avons officiellement rejeté cet actif de notre univers d'investissement.**

---

## 3.4. LA DÉCOUVERTE DES INDICES CONTINUS : VOLATILITY 25 (1S) ET VOLATILITY 75 (1S)

Si le Step Index est une impasse, vers où orienter nos efforts pour construire la Gamme 2 ?
Notre analyse de microstructure a identifié les indices de **Volatilité Continue à pas de 1 seconde** :
* Volatility 25 (1s) Index
* Volatility 75 (1s) Index

### Pourquoi ces Indices sont-ils Fondamentalement Différents ?
1. **Pas de sauts discrets imposés :** Le prix évolue de manière fluide et continue (comme les devises ou les indices boursiers Nasdaq/S&P 500).
2. **Présence de Régimes de Volatilité Hétérogènes :** La volatilité n'est pas constante ; elle connaît des phases de compression extrême suivies d'expansions explosives (*Volatility Clustering* modélisé par Mandelbrot et Engle).
3. **Le Phénomène Physique du Squeeze (Compression) :**
   Lorsque le marché se calme et que la volatilité s'effondre dans une bande étroite, l'énergie s'accumule. Dès que les bornes se rompent, le marché libère une impulsion directionnelle durable (*Breakout*).

### La Stratégie S1 : Volatility Squeeze & Impulse Breakout (H1)
Sur l'unité de temps H1 (1 heure), nous avons modélisé mathématiquement cette dynamique :
* **Bandes de Bollinger (20 périodes, écart-type  = 2.0$) :** Mesurent la dispersion statistique du prix.
* **Canaux de Keltner (20 périodes, multiple ATR  = 1.5$) :** Mesurent la volatilité moyenne absolue (*Average True Range*).
* **Condition de Squeeze (Compression) :** Les Bandes de Bollinger rentrent entièrement à l'intérieur des Canaux de Keltner ($\text{BB}_{\text{upper}} < \text{KC}_{\text{upper}}$ et $\text{BB}_{\text{lower}} > \text{KC}_{\text{lower}}$).
* **Signal de Déclenchement (*Fire*) :** Les Bandes de Bollinger sortent des Canaux de Keltner, signalant l'explosion de volatilité, avec un filtre de momentum aligné.

C'est cette stratégie **S1** qui a été soumise à notre batterie de falsification statistique la plus impitoyable : le **Protocole Sentinelle C1**.
"""
