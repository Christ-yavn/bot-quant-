# -*- coding: utf-8 -*-

def get_content():
    return r"""<a id="partie-4"></a>
# PARTIE 4 : LE COURS COMPLET DE STATISTIQUES QUANTITATIVES EXPLIQUÉ POUR UN ÉTUDIANT EN L1

> [!NOTE]
> Cette partie constitue le cœur théorique du système quantitatif. Chaque concept mathématique de pointe y est décortiqué avec une pédagogie intuitive adaptée à un étudiant de première année (Licence 1), avec des analogies de la vie courante, la définition explicite de chaque symbole, et la justification de son utilité pratique dans nos algorithmes.

---

## 4.1. LE TEST T DE STUDENT ET LE TEST DE WELCH

### 1. L'Analogie Intuitive : La Balance Électronique et le Pépite d'Or
Imaginez que vous cherchiez de l'or dans une rivière. Vous trouvez une petite pépite et vous voulez savoir si son poids est réellement positif ou s'il s'agit d'une illusion d'optique causée par les vibrations de votre balance de poche.
* La balance oscille sans cesse : parfois elle affiche $+0.05\text{ g}$, parfois $-0.02\text{ g}$, parfois $+0.08\text{ g}$.
* Si vous ne faites qu'une seule pesée (=1$), vous ne pouvez rien conclure.
* Mais si vous répétez la pesée 600 fois (=600$) et que la moyenne reste constamment au-dessus de zéro avec une oscillation minuscule, vous avez la certitude scientifique que la pépite existe réellement !

En trading quantitatif, la pépite d'or s'appelle l'**Alpha** (le gain moyen net $\bar{x}$), et les vibrations de la balance s'appellent la **Volatilité du marché** (l'écart-type $).

### 2. Les Hypothèses Statistiques ($ contre $)
Avant de lancer un bot avec de l'argent réel, tout scientifique pose deux hypothèses rivales :
* **L'Hypothèse Nulle ($) :** *"Le robot n'a aucun avantage mathématique (aucun talent). Tous ses gains passés sont le pur fruit du hasard et de la chance. Sa véritable espérance de gain est nulle ou négative ($\mu \le 0$)."*
* **L'Hypothèse Alternative ($) :** *"Le robot possède un avantage structurel réel (un véritable alpha). Son espérance de gain est strictement positive ($\mu > 0$)."*

Le travail des statistiques consiste à **tenter de détruire l'hypothèse $**. Si $ est rejetée avec un niveau de confiance écrasant, nous pouvons déployer le bot en toute sérénité.

### 3. La Formule Mathématique du t-stat
Le score de Student (appelé $-statistique ou $-score) mesure le nombre d'écarts-types séparant notre gain moyen observé de zéro :

t = \frac{\bar{x} - 0}{\text{SE}} = \frac{\bar{x}}{\frac{s}{\sqrt{N}}}

Décomposons chaque terme pour un étudiant de L1 :
1. **$\bar{x}$ (La moyenne empirique des gains par trade) :** C'est la somme de tous les gains divisée par le nombre de trades $. Dans notre test sur Volatility 25 (1s), $\bar{x} = +6.763\text{ bps}$ (points de base, où \text{ bps} = 0.01\%$).
2. **$ (L'écart-type de l'échantillon) :** Il mesure la dispersion, c'est-à-dire l'amplitude des hauts et des bas entre les différents trades.
3. **$ (La taille de l'échantillon) :** Le nombre total de trades analysés ( = 632$ trades sur V25).
4. **$\text{SE} = \frac{s}{\sqrt{N}}$ (L'Erreur-Type ou *Standard Error*) :** C'est l'incertitude pesant sur notre estimation de la moyenne. Remarquez la présence fondamentale de $\sqrt{N}$ au dénominateur : **plus nous analysons de trades, plus l'incertitude se rétrécit vers zéro !**

`	ext
========================================================================================
            SIGNIFICATION INTUITIVE DU SCORE T (T-STAT)
========================================================================================
  * Si t = 0.00 : Gain moyen nul, bruit parfait.
  * Si t = +1.00 : Trop faible, forte probabilité que ce soit de la chance.
  * Si t > +1.96 : Seuil classique (p < 0.05). Moins de 5 % de chances que ce soit du hasard.
  * Si t > +3.00 : Niveau institutionnel d'excellence (p < 0.0013).
  * NOTRE RÉSULTAT SUR VOLATILITY 25 (1s) : t = +3.291 (p = 0.0007) !
    Moins d'une chance sur 1 400 que notre stratégie soit un coup de chance !
  * RÉSULTAT SUR VOLATILITY 75 (1s) : t = +0.447 (p = 0.3286) -> ÉCHEC TOTAL !
    Près d'une chance sur trois que ce soit du bruit -> REJET IMMÉDIAT.
========================================================================================
`

### 4. Pourquoi le Test de Welch au lieu de Student pour la Rupture Structurelle ?
Pour vérifier que notre bot ne perdra pas son avantage dans le temps, nous découpons l'historique en deux périodes : la période d'entraînement (*Train*, avant février 2026) et la période récente (*OOS*, post-février 2026). Nous comparons les moyennes $\bar{x}_1$ et $\bar{x}_2$.

Le test classique de Student suppose que la variance est identique dans les deux périodes ($\sigma_1^2 = \sigma_2^2$). Or, en finance, les marchés changent constamment de régime de volatilité !
C'est pourquoi nous utilisons le **Test t de Welch (*Welch's Two-Sample t-test*)**, qui adapte automatiquement les degrés de liberté $\nu$ par la formule de Welch-Satterthwaite :

\nu \approx \frac{\left(\frac{s_1^2}{N_1} + \frac{s_2^2}{N_2}\right)^2}{\frac{(s_1^2 / N_1)^2}{N_1 - 1} + \frac{(s_2^2 / N_2)^2}{N_2 - 1}}

**Résultat du test de Welch sur Volatility 25 (1s) :**
t = +0.606, \quad p = 0.5445
Puisque la $-valeur est largement supérieure à .05$, **il n'y a aucune rupture structurelle statistiquement significative**. La performance du bot est remarquablement stable à travers les mois !

---

## 4.2. LE BOOTSTRAP STATIONNAIRE BCA (BIAS-CORRECTED AND ACCELERATED)

### 1. L'Analogie du Sac de Billes avec Remise
Imaginez que vous ayez un sac contenant les 632 résultats réels de nos trades passés.
Si nous voulons savoir ce qui pourrait se passer dans un futur parallèle, une méthode naïve consisterait à tirer 632 fois une bille au hasard dans le sac, en la remettant à chaque fois (*Bootstrap standard de Bradley Efron, 1979*). En répétant cela 2 000 fois, nous obtenons 2 000 réalités alternatives et nous traçons l'histogramme des gains moyens.

### 2. Le Problème du Temps en Finance : Pourquoi le Bootstrap Standard Échoue ?
En physique ou en biologie, les mesures sont indépendantes. Mais sur les marchés financiers, les cours ont de la mémoire locale : les périodes de haute volatilité se regroupent (*volatility clusters*). Si vous tirez les trades un par un au hasard, vous détruisez la structure temporelle des séries !

La solution mathématique d'élite a été développée par **Dimitris Politis et Joseph Romano (1994)** : le **Bootstrap Stationnaire par Blocs (*Stationary Bootstrap*)**.
Au lieu de tirer un trade isolé, l'algorithme tire des **blocs continus de trades** dont la longueur suit une loi géométrique de paramètre  = \frac{1}{b^*}$, où ^*$ est la longueur de bloc optimale calculée analytiquement par l'algorithme de **Patton, Politis et White (PPW, 2009)**.
Sur nos données de Volatility 25, ^* = 1.00$ a été calculé formellement.

### 3. Les Deux Corrections Magiques du BCa (Biais et Accélération)
Un intervalle de confiance classique à 95 % suppose que la distribution est symétrique (courbe en cloche de Gauss). Mais en trading, les gains et pertes sont asymétriques !
L'intervalle **BCa (*Bias-Corrected and Accelerated*)** introduit deux ajustements cruciaux :
1. **La Correction de Biais ($) :** Elle mesure la proportion de répliques bootstrap dont le gain est inférieur à la moyenne observée :
   z_0 = \Phi^{-1}\left(\frac{1}{B} \sum_{b=1}^B \mathbb{I}(\bar{x}^*_b < \bar{x})\right)
2. **Le Facteur d'Accélération ($) :** Il mesure l'asymétrie de l'estimateur par la méthode du Jackknife (calcul du troisième moment centré de la distribution).

Grâce à ces deux termes, l'intervalle BCa fournit une précision de second ordre $\mathcal{O}(1/N)$ contre $\mathcal{O}(1/\sqrt{N})$ pour les méthodes standard.

### 4. La Règle Inflexible Sentinelle C1
Pour qu'un bot soit autorisé à passer en production, **la borne inférieure de son intervalle de confiance BCa à 95 % doit être STRICTEMENT supérieure à zéro** :
\text{IC}_{95\%}^{\text{BCa}} = [\text{Borne Inférieure} \,;\, \text{Borne Supérieure}] \implies \text{Borne Inférieure} > 0

`	ext
========================================================================================
         VERDICT SENTINELLE C1 SUR L'INTERVALLE DE CONFIANCE BCA 95 %
========================================================================================
  * Volatility 25 (1s) Index :
    IC BCa 95 % = [+2.705 bps ; +10.796 bps]  <── LA BORNE INFÉRIEURE EST STRICTEMENT > 0 !
    Même dans le pire des scénarios probabilistes (les 2.5 % les plus défavorables),
    la stratégie dégage un gain net garanti d'au moins +2.705 points de base par trade !
    VERDICT : ✅ PASS DE HAUTE LUTTE.

  * Volatility 75 (1s) Index :
    IC BCa 95 % = [-9.872 bps ; +15.972 bps]  <── L'INTERVALLE TRAVERSE LARGEMENT ZÉRO !
    Il existe un risque majeur que la stratégie soit en réalité déficitaire de près de 10 bps.
    VERDICT : ❌ ÉCHEC ÉLIMINATOIRE (FAIL).
========================================================================================
`

---

## 4.3. LE PIÈGE DU DRAGAGE DE DONNÉES (*DATA SNOOPING*) ET LES CORRECTIONS MULTIPLES

### 1. L'Analogie des 48 Joueurs de Loto
Imaginez que vous vouliez prouver qu'une personne a le don de deviner l'avenir.
Vous demandez à **48 personnes différentes** de lancer 10 fois une pièce.
Par pure probabilité combinatoire, il y a une chance très élevée ( \times 0.05 \approx 2.4$) qu'au moins 2 ou 3 personnes fassent un score incroyable (par exemple 9 ou 10 Pile d'affilée) sans avoir le moindre don !
Si vous isolez le meilleur joueur et dites au monde entier : *"Regardez, cette personne a fait 10 Pile sur 10, c'est un génie !"*, vous commettez l'erreur scientifique suprême : le **Dragage de Données (*Data Snooping*)** ou **Biais de Sélection**.

En finance quantitative, si vous testez 48 combinaisons d'indicateurs sur un graphique H1 (48 "écrans"), certaines combinaisons afficheront d'excellentes performances passées par simple chance statistique !

### 2. Le Couperet de Bonferroni (Contrôle FWER)
Pour neutraliser ce risque, le mathématicien italien Carlo Emilio Bonferroni a établi une règle intransigeante :
Si vous testez $ hypothèses simultanément au seuil global $\alpha = 0.05$ (5 %), **chaque test individuel doit battre un seuil divisé par $** :

\alpha_{\text{Bonferroni}} = \frac{\alpha}{N} = \frac{0.05}{48} \approx 0.00104 \quad (0.104\%)

Pour qu'une stratégie soit reconnue comme authentique parmi 48 essais, sa $-valeur doit être inférieure à .00104$ !

### 3. La Procédure Descendante de Holm-Bonferroni
La correction de Bonferroni pure est parfois trop conservatrice. Le statisticien Sture Holm a perfectionné la méthode par un algorithme pas à pas :
1. On classe les $ hypothèses par $-valeurs croissantes : {(1)} \le p_{(2)} \le \dots \le p_{(m)}$.
2. Pour chaque rang $, on compare {(k)}$ au seuil ajusté dynamique :
   p_{(k)} \le \frac{\alpha}{m - k + 1}
3. Dès qu'une hypothèse échoue, la procédure s'arrête net et rejette toutes les suivantes.

### 4. La Maîtrise du Taux de Fausse Découverte de Benjamini-Hochberg (FDR)
Yoav Benjamini et Yosef Hochberg (1995) ont révolutionné ce domaine en contrôlant non pas le risque d'une seule erreur (*Family-Wise Error Rate*), mais la proportion de faux positifs parmi les stratégies sélectionnées (*False Discovery Rate*) :
p_{(k)} \le \frac{k}{m} \times Q

**La Consécration pour Volatility 25 (1s) :**
Sur nos 48 écrans de recherche H1, Volatility 25 (1s) a obtenu une $-valeur de :
p = 0.0007
Puisque .0007 < 0.00104$, **la stratégie S1 sur Volatility 25 (1s) survit même à la correction de Bonferroni la plus impitoyable qui soit !** Ce résultat atteste de la solidité mathématique intrinsèque de l'alpha découvert.

---

## 4.4. LE TEST PLACEBO PAR MOUVEMENT BROWNIEN GÉOMÉTRIQUE (GBM PERMUTATION TEST)

### 1. L'Analogie Médicale de l'Essai Clinique
Dans la recherche pharmaceutique pour valider un nouveau médicament contre une maladie, on donne le vrai comprimé à un groupe de patients, et une gélule de farine ou de sucre (un **placebo**) à un second groupe de patients. Si le groupe ayant pris le vrai médicament n'obtient pas des résultats nettement supérieurs au groupe placebo, le médicament est immédiatement jeté à la poubelle.

### 2. La Construction du Marché Placebo en Finance
En finance, comment fabriquer un marché "placebo" ?
Nous utilisons un simulateur de Monte-Carlo pour générer **2 000 marchés synthétiques artificiels** suivant un **Mouvement Brownien Géométrique pur (*Geometric Brownian Motion - GBM*)** :

S_{t+\Delta t} = S_t \cdot \exp\left( \left(\mu - \frac{1}{2}\sigma^2\right)\Delta t + \sigma \sqrt{\Delta t} \, Z_t \right)

Où  \sim \mathcal{N}(0, 1)$ est un tirage aléatoire gaussien pur.
Ces 2 000 marchés possèdent exactement la même volatilité $\sigma$ que Volatility 25, mais ils sont construits avec **zéro alpha, zéro tendance, zéro structure économique : du pur hasard de casino**.

### 3. La Confrontation Sentinelle C3
Nous lâchons notre robot algorithmique S1 sur ces 2 000 marchés de bruit pur et nous enregistrons le $-statistique obtenu sur chacun d'eux.
Nous calculons le **95e percentile de la distribution des placebos** ({95}$).
La Condition Sentinelle C3 exige que le score réel du bot dépasse obligatoirement ce {95}$ :
\text{Rang Observé} = \frac{\sum_{i=1}^{2000} \mathbb{I}(t_{\text{placebo}}^{(i)} < t_{\text{observé}})}{2000} \ge 0.9500 \quad (95\%)

`	ext
========================================================================================
            VERDICT DU TEST PLACEBO MONTE CARLO (2 000 MARCHÉS SIMULÉS)
========================================================================================
  * Seuil du 95e percentile placebo (Q95) : t = +1.276
  * Performance réelle observée sur V25    : t = +3.291
  * RANG DE VOLATILITY 25 (1s)             : 1.0000 / 2 000 (100.0 %) !
    AUCUN des 2 000 marchés aléatoires n'a réussi à égaler notre performance !
    La probabilité qu'un marché aléatoire produise ce résultat est mathématiquement < 0.05 %.
    VERDICT : ✅ PASS ABSOLU (Score Parfait).

  * RANG DE VOLATILITY 75 (1s)             : 0.8225 (82.25 %)
    17.75 % des marchés purement aléatoires ont fait mieux que V75 !
    VERDICT : ❌ FAIL (Rejet sans appel).
========================================================================================
`

---

## 4.5. LE RATIO DE SHARPE DÉFLATÉ (DSR) ET PROBABILISTE (PSR) DE MARCOS LÓPEZ DE PRADO

### 1. Le Génie de Marcos López de Prado
Marcos López de Prado (ancien responsable mondial de la recherche quantitative chez AQR Capital Management, professeur à Cornell et chercheur au Lawrence Berkeley National Laboratory) a publié en 2014 un article fondateur : *The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting, and Non-Normality*.

López de Prado a démontré que le célèbre **Ratio de Sharpe** inventé par William Sharpe en 1966 :
\text{SR} = \frac{\mu - r_f}{\sigma}
est **systématiquement surévalué et trompeur** lorsque plusieurs stratégies ont été explorées.

### 2. La Formule du Deflated Sharpe Ratio (DSR)
Le Ratio de Sharpe Déflaté calcule la probabilité que le vrai ratio de Sharpe soit supérieur à zéro, après avoir soustrait le seuil d'espérance maximale du meilleur score dû au hasard parmi $ essais :

\text{SR}^* = \sqrt{\text{Var}(\{\text{SR}_n\})} \left( (1 - \gamma_{\text{Euler}}) Z^{-1}\left(1 - \frac{1}{N}\right) + \gamma_{\text{Euler}} Z^{-1}\left(1 - \frac{1}{N} e^{-1}\right) \right)

Où $\gamma_{\text{Euler}} \approx 0.5772$ est la constante d'Euler-Mascheroni et ^{-1}$ est la fonction quantile gaussienne inverse.
Le DSR intègre également les moments d'ordre supérieur de la distribution des rendements : l'**asymétrie (*Skewness* $\gamma_3$)** et l'**aplatissement (*Kurtosis* $\gamma_4$)** :

\text{PSR}(\text{SR}^*) = \Phi\left( \frac{(\widehat{\text{SR}} - \text{SR}^*) \sqrt{T-1}}{\sqrt{1 - \gamma_3 \widehat{\text{SR}} + \frac{\gamma_4 - 1}{4}\widehat{\text{SR}}^2}} \right)

**La Règle de Décision Institutionnelle :**
* Si $\text{DSR} \le 0$ : L'alpha est une illusion statistique détruite par la multiplicité des tests.
* Si $\text{DSR} > 0$ : L'avantage est authentique et survit à la déflation d'un laboratoire quantitatif.

`	ext
========================================================================================
              RÉSULTATS DE LA DÉFLATION DE SHARPE (LÓPEZ DE PRADO)
========================================================================================
  * Volatility 25 (1s) Index :
    - Probabilistic Sharpe Ratio (PSR) : 0.9995 (99.95 % de certitude que SR > 0)
    - Deflated Sharpe Ratio (DSR, N=48) : +0.0114  <── POSITIF ! SURVIT À LA DÉFLATION !
    - VERDICT : ✅ VALIDÉ INSTITUTIONNELLEMENT.

  * Volatility 75 (1s) Index :
    - Probabilistic Sharpe Ratio (PSR) : 0.6729 (À peine 67 % de certitude)
    - Deflated Sharpe Ratio (DSR, N=48) : -0.3152  <── FORTEMENT NÉGATIF !
    - VERDICT : ❌ ÉCHEC PAR DÉFLATION DE SHARPE.
========================================================================================
`

---

## 4.6. LE CERVEAU IA ONNX : DU GRADIENT BOOSTING AU CLASSIFIEUR DÉCISIONNEL

Pour compléter le système S1 sur Volatility 25 (1s), nous avons entraîné un classifieur d'apprentissage automatique de pointe (**Gradient Boosted Decision Trees & MLP**) chargé de jouer le rôle de filtre de garde (*Gating Mechanism*).

### 1. Les 7 Descripteurs Microstructurels (*Features*)
À chaque bougie H1 où la stratégie S1 détecte une sortie de compression (*Squeeze Breakout*), le modèle extrait 7 variables quantitatives :
1. **$ (spread_bps) :** Le coût du spread réel du broker exprimé en points de base.
2. **$ (spread_to_atr) :** Le ratio entre le spread et la volatilité moyenne ATR(20). Permet de bloquer les ordres lorsque le frottement absorbe une part excessive du mouvement espéré.
3. **$ (ol_ratio_bb_kc) :** Le ratio de largeur entre les Bandes de Bollinger et les Canaux de Keltner. Mesure l'intensité explosive de l'expansion.
4. **$ (impulse_zscore) :** Le z-score de la vitesse de la cassure par rapport à l'historique récent.
5. **$ (
orm_momentum) :** La valeur normalisée de l'oscillateur de momentum linéaire.
6. **$ (levy_area_proxy) :** Approximation de l'Aire de Lévy issue de la théorie des chemins rugueux (*Rough Path Theory*), capturant les micro-torsions du prix.
7. **$ (	ail_fatness_kurt) :** L'aplatissement empirique mesurant la probabilité d'événements extrêmes.

### 2. Le Mécanisme de Filtrage Décisionnel en Production
Le modèle prédictif calcule la probabilité conditionnelle que le trade soit un succès :
P(\text{Trade Gagnant} \mid \mathbf{x} = [x_1, x_2, \dots, x_7])

* **Sans filtre (Win Rate brut) :** .90\,\%$ de victoires.
* **Seuil d'inférence ONNX :** Fixé rigoureusement à {\text{seuil}} = 0.60$ (\,\%$).
  * Si (\text{Trade Gagnant}) < 0.60$ : Le trade est considéré comme incertain. L'ordre d'envoi est **avorté instantanément** par le code MQL5.
  * Si (\text{Trade Gagnant}) \ge 0.60$ : Le trade est autorisé et envoyé au serveur Deriv.
* **Résultat Hors-Échantillon (Test OOS) :** **.82\,\%$ de précision** sur les trades autorisés !
Le filtre ONNX apporte un gain net de **$+8.92\,\%$ de taux de réussite**, transformant une stratégie déjà profitable en une machine de guerre quantitative d'une régularité remarquable.
"""
