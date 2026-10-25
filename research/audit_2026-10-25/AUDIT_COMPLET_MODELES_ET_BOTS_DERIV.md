# Audit complet : modèles mathématiques, code des bots et rentabilité réelle
**Périmètre :** `DerivBoomCrashHFT_v830_Ultimate` (Boom & Crash) · `Deriv_VolSqueeze_Breakout_EA_v3` (Volatility 25 (1s) et 75 (1s)) · modèles ONNX · documentation GitHub
**Date :** 25/10/2026 · **Compte :** Deriv-Demo 32449166

> [!CAUTION]
> **Action urgente.** v8.30 a commencé à trader aujourd'hui à 10:29 (1er trade : −0,35 $ sur Crash 1000). Au démarrage, sa propre « porte EV » a affiché **REFUSE (EV insuffisante) sur les 5 indices** (journal MT5, 09:39 et 09:50). Mais cette porte n'est jamais appliquée dans le code, donc le bot trade quand même. À pleine cadence, la perte attendue est de plusieurs centaines de dollars par jour, jusqu'au coupe-circuit à −4 %. **Je recommande de désactiver v8.30 maintenant.**

---

## 0. Verdict en une page

| Question | Réponse vérifiée |
|---|---|
| Les modèles mathématiques sont-ils réalistes ? | **Non pour l'essentiel.** Les deux familles de marchés sont des **martingales** : l'espérance du prix futur est égale au prix actuel. Je l'ai vérifié sur 8,5 millions de ticks Boom/Crash et 6,3 ans de barres H1 V25/V75. Les sauts Boom/Crash sont **sans mémoire** (aucun effet Hawkes ni « maturation »). La volatilité de V25/V75 est **constante** (aucun « squeeze » réel). |
| Le code applique-t-il la stratégie ? | **Partiellement, avec des défauts bloquants.** Porte EV calculée mais jamais appliquée, filtre IA incapable de bloquer, features ONNX différentes de celles de l'entraînement (pour les deux bots), stop temporel en secondes inopérant. |
| La stratégie peut-elle gagner ? | **Non, et c'est démontrable.** Sur une martingale, *toute* règle d'entrée/sortie fondée sur les prix passés a une espérance égale à **−spread × lot** par trade (théorème d'arrêt de Doob). La perte live de v8 (−311 $) correspond à la théorie au centime près une fois le **vrai spread** pris en compte. |
| Le « +340 $ » et le bootstrap à 100 % ? | **Ce n'est pas une simulation de marché.** C'est une formule arbitraire (`gain = |perte_v7| × 0,92`, `perte = gain_v7 × 1,15 + 0,05`). Le bootstrap a rééchantillonné ces chiffres inventés. Résultat réel de la même logique en live : **−311,20 $ sur 648 trades**. |
| « V25 = 100 % de trades gagnants » ? | **3 trades sur 3** (probabilité 12,5 % par pur hasard). Sur 6,3 ans (1 473 trades), le taux de réussite est de 51,7 % et le gain n'est **pas statistiquement significatif** (t = +1,58). |
| Une stratégie « infaillible » existe-t-elle sur ces marchés ? | **Non.** Ces indices sont générés par un algorithme conçu pour être équitable, et le broker se rémunère sur le spread. La seule piste où une vraie certitude mathématique est possible est décrite en §6. |

---

## 1. Méthode et données (tout est reproductible)

| Test | Données | Script |
|---|---|---|
| Microstructure Boom/Crash (spread, dérive, sauts, martingale, fonction de hasard) | 8 indices × 10 jours = **~6,8 M ticks bid/ask** | [audit_boomcrash_micro.py](audit_boomcrash_micro.py) |
| Simulation tick par tick de v8.30, de l'inverse (v7) et d'entrées aléatoires | mêmes ticks, ~280 000 trades simulés | [sim_v830_ticks.py](sim_v830_ticks.py) |
| Forensique d'exécution des 648 trades live v8 | historique des deals MT5 et ticks | [forensic_v8_live.py](forensic_v8_live.py) |
| Reproduction exacte du signal Squeeze v3 et test de l'ONNX avec les features réellement envoyées par l'EA | **56 046 barres H1** par indice (06/2020 → 10/2026) | [audit_vol_squeeze.py](audit_vol_squeeze.py) |
| Dérive de long terme et swaps | barres D1 depuis l'origine (785 à 2 747 jours) | [audit_longrun_drift.py](audit_longrun_drift.py) |

---

## 2. Boom & Crash : ce que disent réellement les données

### 2.1 Le prix est une martingale (aucune dérive exploitable)
Variation moyenne du mid par tick, sur 10 jours :

| Indice | E[ΔMid] / tick | t-stat | Sur 60 ticks | Spread live |
|---|---:|---:|---:|---:|
| Crash 600 | +0,000117 | +0,10 | +0,007 | **3,281** |
| Crash 900 | +0,000907 | +1,29 | +0,054 | **1,362** |
| Crash 1000 | −0,000241 | −0,92 | −0,014 | **0,541** |
| Boom 600 | +0,000105 | +0,37 | +0,006 | **0,775** |
| Boom 900 | +0,000965 | +2,35 | +0,058 | **0,969** |
| Boom 1000 | +0,000405 | +0,62 | +0,024 | **1,726** |

Sur 8 tests, un |t| > 2 est attendu par hasard. Même en le prenant au sérieux, le mouvement attendu de Boom 900 sur 60 ticks (+0,058) reste **17 fois plus petit que le spread**. Sur le long terme (barres D1, jusqu'à 7,5 ans), aucun indice n'a de dérive significative (tous les |t| < 2). Les **swaps coûtent −16 % à −72 % par an des deux côtés**, ce qui interdit aussi la détention longue.

### 2.2 Les sauts sont sans mémoire : ni Hawkes, ni « maturation »
- **Coefficient de variation des intervalles entre sauts : 0,96 à 1,03.** Un processus géométrique pur (sans mémoire) donne exactement 1.
- **Autocorrélation entre intervalles successifs : −0,035 à +0,033.** Un processus de Hawkes (auto-excitation) donnerait une valeur nettement positive.
- **Fonction de hasard plate.** La probabilité d'un saut au tick suivant est la même 10 ticks ou 2 000 ticks après le dernier saut (Crash 600 : 1,88 → 1,57 pour 1000 ticks, dans le bruit).

**Conséquence :** aucune variable tirée de l'historique (temps depuis le dernier saut, intensité « Hawkes », grappes, vitesse de dérive) ne peut prédire le prochain saut. Les features d'entrée des modèles ONNX Boom/Crash n'ont donc rien à prédire.

### 2.3 Le vrai spread est environ 10 fois le spread historique
C'est **l'erreur fondatrice** de toutes les études v6 → v8.

| Indice | Spread de l'historique `CopyTicks` | Spread **réel exécutable** | Multiple |
|---|---:|---:|---:|
| Crash 600 | 0,297 | **3,281** | ×11 |
| Crash 900 | 0,193 | **1,362** | ×7 |
| Boom 1000 | 0,156 | **1,726** | ×11 |
| Boom 600 | 0,071 | **0,775** | ×11 |

La forensique des 648 trades live le confirme : **chaque fill est exactement 1,492 pt (Crash 600) / 0,585 pt (Crash 900) plus défavorable que le bid/ask historique**, avec un écart-type nul. Le fichier `real_live_spreads_mt5.json` du dépôt l'avait d'ailleurs mesuré le 18/10, mais les simulations et la « validation » ne l'ont pas utilisé.

### 2.4 Décomposition exacte de la perte live v8 (−311,20 $)

| Composante | Total | Par trade |
|---|---:|---:|
| Mouvement du marché (mid) | −10,82 $ | −0,017 $ (z = −0,34 : **pur hasard**) |
| Demi-spreads visibles | −31,82 $ | −0,049 $ |
| Spread caché à l'entrée | −134,23 $ | −0,207 $ |
| Spread caché à la sortie | −134,23 $ | −0,207 $ |
| **Total** | **−311,20 $** | **−0,480 $** |

**96,5 % de la perte vient du spread.** Le marché lui-même n'a ni aidé ni pénalisé la stratégie. Prédiction de Doob, −spread × 0,20 lot : Crash 600 **−0,656 $** prédit contre **−0,742 $** observé ; Crash 900 **−0,272 $** prédit contre **−0,222 $** observé.

### 2.5 Simulation tick par tick (spread historique, donc optimiste)
Même avec le spread 10 fois trop petit, **les trois approches perdent sur les 8 indices** :

| Indice | v8.30 (BUY Boom / SELL Crash) | Inverse v7 | Entrées aléatoires | −spread × lot (théorie) |
|---|---:|---:|---:|---:|
| Crash 600 | −0,044 $ (t −3,7) | −0,085 $ | −0,079 $ | −0,060 $ |
| Crash 900 | −0,050 $ (t −5,3) | −0,031 $ | −0,058 $ | −0,037 $ |
| Boom 600 | −0,019 $ (t −5,3) | −0,016 $ | −0,015 $ | −0,014 $ |
| Boom 1000 | −0,038 $ (t −4,5) | −0,037 $ | −0,024 $ | −0,031 $ |

v8.30, son exact inverse et le hasard donnent tous **≈ −spread**. C'est la signature d'une martingale : **le sens du trade et la règle de sortie ne changent pas l'espérance**, seulement la forme de la distribution (beaucoup de petites pertes et de rares gros gains, ou l'inverse). **La « convexité » change le profil des gains, pas l'espérance.**

> [!IMPORTANT]
> **L'erreur de raisonnement centrale du projet :** le théorème de Doob a été utilisé (à juste titre) pour réfuter la récolte de dérive v7, mais il s'applique **exactement de la même façon** à la stratégie inverse. Il n'y a pas d'échappatoire par l'inversion.

### 2.6 Pire design possible au regard du coût
Pour un trade de 60 ticks, l'écart-type du prix vaut environ 0,13 σ(H1). Le spread représente alors **0,28 à 0,40 écart-type par trade** (Crash 600 : 3,28 pts contre ~8,3 pts). Le HFT est donc le régime où le coût pèse **le plus** par unité de risque. À titre de comparaison, V25 (1s) tenu 4 h ne coûte que 0,015 écart-type.

---

## 3. Audit ligne à ligne de `DerivBoomCrashHFT_v830_Ultimate.mq5`

| # | Gravité | Défaut | Lignes |
|---|---|---|---|
| B1 | 🔴 Critique | **Porte EV jamais appliquée.** `ev_gate_pass` est calculé et affiché (REFUSE sur 5/5 aujourd'hui), mais aucune fonction ne le lit avant d'ouvrir un trade. | L995, L1871-1941 |
| B2 | 🔴 Critique | **Le filtre IA ne peut jamais bloquer.** `theta = 0,90 × base_p0` alors que `phys_p0 ≥ base_p0` par construction, et l'ONNX est fusionné par `max()`, ce qui ne peut qu'augmenter la probabilité. **L'ONNX n'a aucun effet sur les décisions.** | L717, L909 |
| B3 | 🔴 Critique | **Features ONNX incompatibles.** Le modèle a été entraîné sur `[symbol_id, is_boom, …, real_breakeven_ticks, cycle_cost_ratio]` (cf. `onnx_model_metadata.json`), mais le réglage par défaut `InpUseZeroCheatFeatures=true` lui envoie un **autre vecteur** (ratios tau, excès Hawkes…). | L763-847 |
| B4 | 🔴 Critique | **Modèle entraîné pour la direction opposée.** Il prédit la *survie de la dérive* (stratégie v7). Sur son propre jeu de test, le PnL après filtre IA est **négatif sur 9 indices sur 10** (total −18 728 unités de dérive). Le métadonnées du dépôt le montrent. | `onnx_model_metadata.json` |
| B5 | 🟠 Majeur | **Stop en secondes inopérant.** Le code compare `GetTickCount64()` (ms depuis le démarrage du PC) à `POSITION_TIME_MSC` (ms depuis 1970), donc `elapsed_sec` vaut toujours 0. | L1639, L1775 |
| B6 | 🟠 Majeur | **« Perte journalière » mal calculée.** Elle est mesurée depuis le lancement (`g_initial_equity`), et `g_day_start_equity` n'est jamais utilisé. | L2385 |
| B7 | 🟠 Majeur | **Sophisme du joueur codé en dur.** `calm_maturity_boost` augmente la probabilité de saut avec le calme, alors que la fonction de hasard mesurée est plate. | L711 |
| B8 | 🟠 Majeur | **Gain plancher artificiel.** `net_spike_pts ≥ 0,20 × mean_spike` garantit un « gain » positif même quand le spread le mange. | L923 |
| B9 | 🟡 Mineur | **Ré-entrée « cluster Hawkes »** fondée sur une auto-excitation qui n'existe pas (autocorrélation ≈ 0). | L2184 |

---

## 4. Volatility 25 (1s) / 75 (1s) : Squeeze Breakout v3

### 4.1 Les marchés sont des browniens géométriques à volatilité constante
| Test (56 046 barres H1) | V25 (1s) | V75 (1s) | Ce qu'il faudrait pour qu'un « squeeze » existe |
|---|---:|---:|---|
| Autocorrélation des rendements (lags 1 à 5) | ≤ 0,011 | ≤ 0,004 | ≠ 0 |
| Autocorrélation des rendements² (clustering de volatilité) | ≤ 0,005 | ≤ 0,007 | **> 0,1** (comme sur les vrais marchés) |
| Kurtosis H1 | 2,965 | 2,987 | > 3 |
| corr(σ des 20 dernières barres, \|r\| de la barre suivante) | **+0,002** | **+0,001** | > 0 |
| Volatilité annualisée réalisée | 24,9 % | 75,2 % | — (identique à l'annonce de Deriv) |

**La volatilité passée ne prédit pas la volatilité future (corrélation 0,001).** Une « compression » est un simple accident d'échantillonnage : elle ne contient aucune information sur la suite.

### 4.2 Reproduction exacte du signal de l'EA sur 6,3 ans

| Horizon | V25 : trades / WR / net moyen (t) | V75 : trades / WR / net moyen (t) |
|---|---|---|
| 1 h | 1 981 / 50,4 % / +0,33 bps (**+0,55**) | 1 958 / 48,2 % / −2,09 bps (**−1,14**) |
| 3 h | 1 593 / 51,9 % / +1,67 bps (**+1,42**) | 1 562 / 48,8 % / +3,04 bps (**+0,85**) |
| **4 h** (réglage V25) | 1 473 / 51,7 % / +2,21 bps (**+1,58**) | 1 440 / 49,6 % / +2,26 bps (**+0,53**) |

- **Aucun résultat n'est significatif**, surtout avec 10 tests simultanés (la correction de Bonferroni exige t > 2,8).
- Les chiffres précédents (« V75 WR 62,86 % à 3 h », « V25 PF 1,64 ») venaient de **1 000 barres** (~40 signaux). Choisir l'horizon *a posteriori* sur un échantillon aussi petit est du surapprentissage.
- **Live :** V25 a fait 3 trades, tous gagnants (+87 $) ; V75 a fait 5 trades, dont 2 gagnants (−95 $). Au total : −8 $. Cohérent avec le hasard.
- Même si le +2,2 bps de V25 était réel, il représenterait environ **+0,19 $ par trade** pour un risque d'environ 46 $ par trade (ratio de Sharpe quasi nul).

### 4.3 Le filtre ONNX `c2_vol_filter.onnx` : un générateur de bruit
| Position | Feature à l'**entraînement** (`train_volatility_colab.py`) | Feature **envoyée par l'EA** |
|---|---|---|
| 0 | z_score | vol_ratio |
| 1 | rolling_std | impulse_z |
| 2 | ratio_compression | direction (±1) |
| 3 | wick_ratio | levy_area |
| 4 | tr_norm | spread_atr (÷100 en plus) |
| 5 | returns_bps | skew20 |
| 6 | spread_norm | kurt20 |

- **Aucune des 7 positions ne correspond.** Le modèle reçoit des données qu'il n'a jamais vues.
- Le label a été calculé à **2 h** alors que l'EA tient 3 à 4 h. L'entraînement porte sur ~1 000 barres de V75, et la seule métrique produite est l'exactitude **sur le jeu d'entraînement**.
- Mesure réelle : avec les features exactes de l'EA, l'ONNX **bloque 94 à 95 % des signaux** (P moyen = 0,27). Les ~100 trades restants sur 6 ans ne sont pas significatifs (t < 1).

### 4.4 Autres points du code v3
- Les magic numbers ont été inversés entre les graphiques (l'historique V25 = 20261022, le graphique V25 actuel = 20261021) : le suivi de performance par bot est cassé.
- Par défaut, aucun stop catastrophe (`InpUseHardTPSL=false`). C'est acceptable sur un brownien, mais à documenter.
- Le reste (taille de position par parité de volatilité, √4 = 2 pour l'horizon 4 h, sortie à heure fixe) est **correctement implémenté**.

---

## 5. Bilan factuel et évaluation du travail précédent

**Compte :** 10 000 $ → **9 201,85 $**. v6 −68 $ · v7 −420 $ · v8 −311 $ · Volatilité −8 $ · v8.30 −0,35 $ (en cours).

**Ce qui était bon :** l'hygiène de compilation, le versionnage additif, la forensique de v7, la réfutation (correcte) de la récolte de dérive par Doob, la mesure des vrais spreads (json du 18/10) et les tailles de position par parité de volatilité.

**Ce qui a produit de fausses certitudes :**
1. Les simulations utilisaient le spread historique (10 fois trop petit).
2. Un résultat « contrefactuel » produit par une formule inventée, puis « validé » par bootstrap.
3. Des paramètres choisis sur ~40 trades et présentés comme des optimums.
4. Des modèles ONNX dont les entrées ne correspondent pas à celles de l'entraînement, qui sont entraînés pour la mauvaise direction et qui n'ont jamais été évalués hors échantillon.
5. Un vocabulaire avancé (Hawkes, Lévy, L99) sans test empirique des hypothèses qu'il suppose (auto-excitation, clustering de volatilité).

> [!WARNING]
> Le README et le Tome II présentent aujourd'hui comme établis des résultats réfutés : « +340 $ », « 100 % de trajectoires positives », « lift de hasard ×2 », « 100 % de gains sur V25 », « H* = 3 h/4 h ». **J'ai moi-même recopié dans le README de la session précédente un intervalle de confiance erroné ([+340,51 ; +340,52]).** Comme votre objectif est que tout futur agent parte du bon niveau de compréhension, ces sections doivent être corrigées en priorité. Sinon, chaque nouvel agent repartira de conclusions fausses.

---

## 6. Ce qui pourrait réellement fonctionner (propositions)

### P1. Un « Desk de validation » obligatoire (priorité absolue)
C'est exactement le « desk quant » que vous vouliez construire. Aucun bot ne passe en démo sans franchir **6 portes automatiques** :
1. **Rejeu tick par tick avec le spread live** (`SymbolInfoTick`, jamais `CopyTicks`).
2. **Test de martingale et de fonction de hasard** sur le marché ciblé : si le marché est une martingale, refus automatique de toute stratégie directionnelle fondée sur les prix.
3. **Comparaison à un placebo** : mêmes trades, entrées aléatoires. La stratégie doit battre 95 % des placebos.
4. **Correction des tests multiples** (Deflated Sharpe Ratio, Bailey & López de Prado 2014), en comptant chaque paramètre essayé.
5. **Hors échantillon strict** : ≥ 300 trades sur une période jamais vue.
6. **Moniteur live d'honnêteté** : comparer en continu le PnL réel à la prédiction −spread × N. Un écart supérieur à 3 écarts-types signale un bug ou une hypothèse fausse.

Ce desk aurait arrêté v8 avant le premier dollar perdu (porte 1) et le Squeeze v3 à la porte 4.

### P2. Scanner de juste valeur des contrats Deriv (la seule piste « certitude mathématique »)
Contrairement aux CFD, Deriv vend des **contrats à prix fixé** : Rise/Fall, Higher/Lower, Touch/No Touch, Digits, Accumulators, Turbos, Vanillas, Multipliers. Or **le processus générateur est connu et vérifié** (§2.2 et §4.1) :
- V25/V75 : brownien géométrique à σ exactement connue, donc prix exacts par formules fermées (digitale : `N(d₂)`, contrats à barrière par principe de réflexion) ;
- Boom/Crash : P(saut dans N ticks) = `1 − (1 − 1/τ)^N` exactement ;
- Digits : uniformité testable sur des millions de ticks.

Le scanner interrogerait l'API WebSocket de Deriv (`proposal`) pour chaque type de contrat, durée et barrière, puis calculerait **EV = paiement × P_exacte − mise**.
- **Si un contrat a une EV positive, c'est une certitude mathématique** (la loi des grands nombres sur un modèle vérifié), pas un pari sur un pattern.
- **Attente honnête :** la marge de la maison est très probablement négative partout (typiquement −2 % à −5 %). Mais c'est vérifiable en quelques jours, ça cartographie précisément le coût de chaque produit, et c'est le seul endroit où des « calculs extraordinaires » peuvent apporter une vraie supériorité.

### P3. Si vous voulez continuer à trader des CFD synthétiques : minimiser la perte certaine
Puisque **E[perte] = Σ spread × lot**, les seuls leviers sont : moins de trades, des lots plus petits, des instruments à faible coût par unité de risque et des horizons longs.

| Instrument et horizon | Coût en écarts-types par trade |
|---|---:|
| Crash 600, 60 ticks (v8.30) | **≈ 0,40** (le pire) |
| Boom 600, 60 ticks | ≈ 0,40 |
| V75 (1s), 4 h | ≈ 0,021 |
| **V25 (1s), 4 h** | **≈ 0,015** (le moins cher) |

Cela permet un budget de risque calculable à l'avance (par exemple « je dépense au maximum X $ par mois en spread »), mais **pas** des gains attendus.

### P4. Corriger la documentation et la mémoire du projet
Ajouter au dépôt un document `ETAT_DE_LA_VERITE.md` qui liste chaque hypothèse avec son statut : *vérifiée*, *réfutée* ou *non testée*, et le script de preuve. Marquer comme **réfutées** les sections concernées du README et du Tome II, en conservant l'historique (rien n'est supprimé).

---

## 7. Plan d'action proposé

| Étape | Action | Durée |
|---|---|---|
| 1 | **Désactiver v8.30** (et éventuellement le Squeeze v3, dont l'espérance est nulle moins le spread) | immédiat |
| 2 | Ajouter `ETAT_DE_LA_VERITE.md`, corriger le README et le Tome II, et pousser les scripts d'audit dans `research/audit_2026-10-25/` | 1 session |
| 3 | Construire le Desk de validation (P1) en Python, réutilisable par tous les futurs agents | 1 à 2 sessions |
| 4 | Construire le scanner de juste valeur des contrats Deriv (P2) et publier la carte EV de tous les contrats | 1 à 2 sessions |
| 5 | Décider sur preuves : s'il n'existe aucun contrat à EV ≥ 0, arrêter le trading algorithmique sur synthétiques, ou le cantonner à un budget de coût assumé (P3) | — |
