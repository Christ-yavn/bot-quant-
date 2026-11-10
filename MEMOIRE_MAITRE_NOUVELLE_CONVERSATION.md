# MÉMOIRE MAÎTRE & PROTOCOLE DE REPRISE INTÉGRALE (QUANT BOT DERIV)
## Document de Continuité Cognitive pour Nouvelle Discussion / Nouvel Agent IA

**Date de dernière mise à jour certifiée** : 10 Novembre 2026 (13:15 UTC — Version `v3.52 Direction Fix` déployée live)  
**Dépôt GitHub Officiel** : `https://github.com/Christ-yavn/bot-quant-.git` (Branche `main`)  
**Dossier Local du Projet (Workspace)** : `C:\Users\CHRIST\Desktop\IA\ANTIGRAVITY\projets\general project   quant bot deriv`

---

## 1. ORDRE DE MISSION POUR LE NOUVEL AGENT IA (LECTURE OBLIGATOIRE)

Tu prends le relais d'un projet d'ingénierie quantitative institutionnelle sur les marchés synthétiques **Deriv**. L'ancienne discussion a été archivée/supprimée pour libérer la fenêtre de contexte, mais **100 % du code, des modèles ONNX, des preuves mathématiques, des historiques de trades et des rapports forensiques ont été sauvegardés dans le dépôt Git local et sur GitHub**.

### Protocole d'initialisation impératif avant toute action :
Dès le premier message d'une nouvelle discussion, tu dois **consulter physiquement** avec tes outils de lecture (`read_file` / `run_command`) les fichiers suivants dans le dossier `C:\Users\CHRIST\Desktop\IA\ANTIGRAVITY\projets\general project   quant bot deriv` :
1. **`AGENT.md`** : Les 7 invariants mathématiques et techniques inviolables, la cartographie du repo et les commandes de compilation MQL5.
2. **`MEMOIRE_MAITRE_NOUVELLE_CONVERSATION.md`** (ce fichier) : L'état exact des bots, leurs versions, leurs performances réelles et la feuille de route de recherche.
3. **`CHANGELOG_AND_HISTORY.md`** : La chronologie complète du projet de la Section 1 à la Section 14.8.
4. **`docs/ETAT_DE_LA_VERITE.md`** : Le registre scientifique des théorèmes prouvés et des hypothèses réfutées.
5. **Les 3 rapports de l'audit Quant Pod (`/teamwork` + `/boost`)** :
   - **`docs/DATA_FORENSIC_REPORT.md`** (Audit forensique des 3 420 trades réels MT5 et des journaux système).
   - **`docs/CODE_ARCHITECTURE_AUDIT.md`** (Audit du code source MQL5/ONNX et des failles corrigées).
   - **`docs/ADVERSARIAL_VERDICT_REPORT.md`** (Verdict mathématique hostile sur 1,68 million de ticks, DSR, PBO et validation des 5 portes).
6. **Le Skill Institutionnel `/agent-quant-pod`** :
   - Manifeste maître : `C:\Users\CHRIST\.gemini\config\skills\quant-pod\SKILL.md`
   - Moteur Deriv : `C:\Users\CHRIST\.gemini\config\skills\quant-pod\scripts\deriv_quant_engine.py`
   - Arsenal Scientifique : `C:\Users\CHRIST\.gemini\config\skills\quant-pod\scripts\quant_scientific_arsenal.py`
   - Référentiel des 11 familles Deriv : `C:\Users\CHRIST\.gemini\config\skills\quant-pod\references\deriv_11_families.md`

> **RÈGLE DE FONCTIONNEMENT `/teamwork` EXIGÉE PAR L'UTILISATEUR :**
> Lorsque l'utilisateur demande d'utiliser `/agent-quant-pod` ou de mener une recherche/audit complexe, **ne fais jamais tout le travail seul dans un fil séquentiel unique**. Tu dois obligatoirement diviser le travail en créant et lançant de vrais sous-agents spécialisés via `define_subagent` et `invoke_subagent` (ex: `QuantAlphaResearcher`, `QuantDataCurator`, `QuantCodeAuditor`, `QuantAdversarialValidator`, `QuantRiskAllocator`), leur déléguer des tâches précises, puis synthétiser leurs rapports.

---

## 2. IDENTITÉ DE L'ENVIRONNEMENT TECHNIQUE LOCAL

* **Système d'exploitation** : Windows 11 x64
* **Dépôt Git Local** : `C:\Users\CHRIST\Desktop\IA\ANTIGRAVITY\projets\general project   quant bot deriv`
* **Dépôt GitHub Distant** : `https://github.com/Christ-yavn/bot-quant-.git`
* **Terminal MetaTrader 5 (Exclusivement celui de Deriv)** :
  - Exécutable : `C:\Program Files\MetaTrader 5 Terminal\terminal64.exe`
  - Raccourci Bureau : `C:\Users\CHRIST\Desktop\Deriv MT5.lnk`
  - Compilateur MQL5 : `C:\Program Files\MetaTrader 5 Terminal\metaeditor64.exe`
  - Data Folder MT5 : `C:\Users\CHRIST\AppData\Roaming\MetaQuotes\Terminal\FB9A56D617EDDDFE29EE54EBEFFE96C1`
  - Dossier Experts : `...\FB9A56D617EDDDFE29EE54EBEFFE96C1\MQL5\Experts\`
  - Dossier Modèles ONNX : `...\FB9A56D617EDDDFE29EE54EBEFFE96C1\MQL5\Files\`
  - Dossier Profils Graphiques : `...\FB9A56D617EDDDFE29EE54EBEFFE96C1\MQL5\Profiles\Charts\Default\`
  - Compte MT5 : `32449166` sur serveur `Deriv-Demo`
* *(Attention : Ne jamais utiliser l'autre installation `C:\Program Files\MetaTrader 5\terminal64.exe` qui correspond à un ancien compte Forex standard).*

---

## 3. SYNTHÈSE EXHAUSTIVE DE CE QUI A ÉTÉ CONÇU, PROUVÉ ET RÉALISÉ

### 3.1. BOT N°1 : BOOM & CRASH HFT (`DerivBoomCrashHFT_v830_Ultimate.mq5`) — ACTUELLEMENT EN PAUSE
* **Cheminement historique (`v1` $\to$ `v8.30`)** :
  - **Versions `v1` à `v6`** : Approches classiques de suivi de dérive ou de moyenne mobile sur Boom & Crash. Réfutées par le risque de queue asymétrique (les Spikes traversent les Stop-Loss avec un *gap-through slippage* massif).
  - **Version `v7`** : Introduction d'un modèle neuronal ONNX (`boom_crash_meta_brain.onnx`, 14 features) estimant la probabilité de survie entre deux spikes.
  - **Versions `v8` à `v8.30 Ultimate`** : Inversion complète de la polarité (*Convex Spike Hunter* : `BUY` uniquement sur Boom, `SELL` uniquement sur Crash) pour chasser les spikes via des sondes courtes de $M^* = 60\text{ ticks}$ ($65\text{ secondes}$), protégées par une porte d'espérance mathématique (`Static EV Gate`) basée sur les vrais spreads live (`SymbolInfoTick`).
* **Pourquoi le Bot Boom & Crash est mis en pause (Preuve Scientifique Irréfutable)** :
  1. **Audit Empirique de 3 412 Trades Réels MT5** : Sur 14 jours de trading réel, le bot a totalisé **`-914.78 USD`** ($1\,601$ gains de $+0.32\$$ en moyenne contre $1\,809$ pertes de $-0.79\$$ en moyenne, Win Rate $= 46.92\%$, $\text{EV} = -0.2681\$$/trade, Profit Factor $= 0.359$). **100 % des 13 indices Boom/Crash tradés ont affiché une espérance négative**.
  2. **Preuve Microstructurale sur 1 686 833 Ticks (`deriv_quant_engine.py`)** :
     - *Absence totale de mémoire (Loi de Poisson pure)* : Corrélation de rang de Spearman Lag-1 entre temps d'attente successifs $\rho = +0.00993$ ($p = 0.6776 \gg 0.05$ sur Boom 500) et $\rho = +0.00314$ ($p = 0.8948$ sur Crash 500). Attendre 60 ou 500 ticks ne change strictement rien à la probabilité du tick suivant.
     - *Absence d'accumulation d'énergie* : Corrélation entre temps d'attente et taille du spike nulle ($\rho = -0.020$, $p = 0.40$).
     - *Absence de fuite temporelle serveur* : Test de Kolmogorov-Smirnov sur les deltas millisecondes non significatif ($p = 0.654$).
     - *Deflated Sharpe Ratio (DSR)* : **`0.0000`** (Sharpe annualisé $= -16.88$).
  3. **Faille de Code identifiée (`VULN-01` - "Trapped Spike Bug")** : Lorsqu'un micro-saut atteignait $0.80 \times \text{seuil}$ sans générer $+0.10\$$ net (absorbé par le spread), le compteur `spikes_while_open` passait à `1`, ce qui désactivait à la fois le Time-Stop de 60 ticks et le coupe-circuit à $-0.35\$$, laissant la position dériver jusqu'au Stop-Loss serveur ($-1.27\$$ à $-1.36\$$).
* **Statut actuel** : Retiré des graphiques MT5 le **29 octobre 2026 à 09:20 UTC**. Maintenu en pause stricte (Veto `/boost`), mais intégralement conservé dans `src/mql5/` à titre de patrimoine technique.

---

### 3.2. BOT N°2 : OMNI-BASKET & RETRACTABLE UI (`Deriv_VolSqueeze_Breakout_EA_v3.mq5`) — VERSION `v3.50` DÉPLOYÉE
* **Architecture Mathématique & Ingénierie (`v3.50 Omni-Basket & Retractable UI`)** :
  - **3 Moteurs d'Alpha Intégrés** :
    - `STRAT_S1_VOL_SQUEEZE_BREAKOUT` (S1) : Cassure d'impulsion post-compression ($|Z| \ge 1.25$, direction = signe du rendement).
    - `STRAT_S2_MOMENTUM_CONTINUATION` (S2) : Suivi de momentum sur 20 barres ($|\text{mom\_z}| \ge 1.50$, direction = signe de mom_z).
    - `STRAT_S3_OU_MEAN_REVERSION` (S3) : Retour à la moyenne d'Ornstein-Uhlenbeck ($|\text{mom\_z}| \ge 2.00$, direction opposée / contrarienne).
  - **Matrice Auto-Configurée à 8 Actifs Élite** :
    1. `Volatility 25 (1s) Index` : H1, Mode S1, $Q=0.30, Z=1.25, H=4$, Magic `20261021`, Cap `0.05 lot` (`ALPHA_KING_V25`).
    2. `Volatility 5 (1s) Index` : M30, Mode S1, $Q=0.30, Z=1.25, H=8$, Magic `20261025`, Cap `0.20 lot` (`HIGH_FREQ_V5`).
    3. `Volatility 15 (1s) Index` : M30, Mode S1, $Q=0.30, Z=1.25, H=8$, Magic `20261015`, Cap `0.50 lot` (`STABILIZER_V15`).
    4. `Volatility Crash 550 Index` : H4, Mode S1, $Q=0.30, Z=1.25, H=4$, Magic `20261550`, Cap `0.50 lot` (`CHAMPION_VC550`).
    5. `DEX 1500 DOWN Index` : M15/H1, Mode S1, $Q=0.30, Z=1.25, H=4$, Magic `20261500`, Cap `0.20 lot` (`DEX1500_ELITE`).
    6. `Range Break 200 Index` : M15/H1, Mode S3 Mean-Rev, $Z=2.00, H=4$, Magic `20261200`, Cap `0.20 lot` (`RANGE_MEANREV`).
    7. `Ladder Volatility Up Index` : H4, Mode S2 Momentum, $Z=1.50, H=4$, Magic `20261400`, Cap `0.20 lot` (`LADDER_MOM`).
    8. `Boom 300 Index` : D1, Mode S2 Swing Momentum, $Z=1.50, H=4$, Magic `20261300`, Cap `0.50 lot` (`BOOM300_SWING`).
    9. `Volatility 10 Index` (Standard) : H1, Mode S1, $Q=0.30, Z=1.25, H=4$, Magic `20261010`, Cap `0.50 lot` (`V10_STD_ALPHA`).
  - **Les 4 Correctifs Critiques v3.50** :
    1. *Télémétrie Continue (Fix Bug 1)* : `UpdateMarketTelemetry()` calculée à $t=0$ dans `OnInit()` et cadencée à 500 ms dans `OnTick()` *avant* tout return. Zéro affichage 0.00 bps au démarrage ou pendant les trades ouverts.
    2. *Lookback Shift Bug Fix (Fix Bug 2)* : La compression utilise `pre_breakout_std20 = rolling_std[1]` (les 20 barres précédant la barre de cassure), empêchant la bougie d'impulsion d'annuler son propre squeeze.
    3. *Plafonnement Marge Libre (Fix Bug 3)* : `CalculateVolParityLot()` utilise `OrderCalcMargin()` et cap le lot si la marge requise dépasse 25 % de la marge libre.
    4. *Filtre Direction (Fix Bug 4)* : `InpDirectionMode` (`DIR_BOTH`, `DIR_LONG_ONLY`, `DIR_SHORT_ONLY`).
  - **Dashboard Graphique MQL5 Rétractable (`OnChartEvent`)** :
    - Panneau natif MQL5 (`QP350_*`, $X=12, Y=26$, largeur 440 px) avec bouton interactif `QP350_BTN_MINIMIZE` pour replier en bandeau compact (32 px) ou déplier en mode complet (285 px).
  - **Fichiers de Préréglages .set** :
    - 6 fichiers `.set` prêts à l'emploi créés dans `presets_v3_50/` et `MQL5/Presets/`.
* **Performance Réelle Certifiée sur le Compte MT5 `32449166` (au 1er Novembre 2026)** :
  - **Sur `Volatility 25 (1s) Index`** :
    - **4 trades clôturés : 4 victoires / 0 perte (100.0 % Win Rate)** !
    - **Profit Net Réalisé : `+$195.15 USD`** (soit **`+$48.79 USD` par trade** en moyenne).
    - **Validation Live de `v3.30` le 01/11/2026 à 18:43 UTC** : Le trade `#8813604600` (ouvert à `930,533.91` avec `0.01 lot`) a vu la version `v3.30` activer automatiquement `[v3.30 PROFIT LOCK]` (SL verrouillé à `931,571.30`, soit `+1,037.39 pts` au-dessus de l'entrée) puis exécuter `[v3.30 TIME-STOP EXIT]` à `941,333.29` (Deal `#8695210964`), encaissant **`+$107.99 USD` net** (`+109.43$` brut) !
  - **Sur `Volatility 75 (1s) Index`** :
    - 5 trades historiques clôturés (sous l'ancienne version `v3.10` avant le cap de lot) : 2 victoires / 3 pertes (`-$95.27 USD`).
    - Pendant les 72 dernières heures de marché en surchauffe ($\sigma_{20} = 75\text{ à }89\text{ bps} > Q_{25} = 60\text{ à }64\text{ bps}$), le filtre de Squeeze a **bloqué 100 % des faux breakouts** (économisant `-255.17 bps` de pertes contre-factuelles).
  - **Bilan Cumulé Global du Bot Volatility (`V25` + `V75`)** :
    - **9 trades clôturés, 6 victoires (66.7 % Win Rate), Profit Net = `+$99.88 USD`**.
* **Correction de l'Horloge Windows Certifiée** :
  - L'ancien décalage de `326 secondes` (5 min 26s) de l'horloge PC locale a été corrigé : les logs du `01/11/2026` montrent que l'évaluation horaire s'exécute désormais à **`19:00:00.189`** (synchronisation milliseconde parfaite avec le serveur Deriv UTC).

---


### 3.3. DÉPLOIEMENT & VALIDATION CHIRURGICALE v3.51 (`10/11/2026`)
* **Archivage Immuable (Loi N°2)** : `archive/mql5_legacy/Deriv_VolSqueeze_Breakout_EA_v3_50.mq5` (53 583 octets) et `Deriv_VolSqueeze_Breakout_EA_v3_50.ex5` (76 248 octets).
* **Résolution des 2 Bugs Subtils Signalés lors de l'Audit L99** :
  1. *Bug Subtil A (Lookback Shift Contamination)* : `ExtLastStd20 = pre_breakout_std20;` (`rolling_std[1]`) et le quantile `squeeze_threshold` est calculé strictement sur les $M-1$ fenêtres passées (`rolling_std[1]` à `rolling_std[q_count]`), éliminant toute contamination par la bougie d'impulsion.
  2. *Bug Subtil B (Faux Positif Profit Lock)* : `is_profit_locked = (cur_sl > open_px)` pour BUY et `(cur_sl > 0.0 && cur_sl < open_px)` pour SELL. Le dashboard affiche rigoureusement `"ARMÉ (Seuil +1.20 ATR)"` tant que le seuil n'est pas franchi, puis `"VERROUILLÉ (+0.20 ATR)"`.
* **Cycle de Vie des Positions Live (10/11/2026)** :
  - **Ticket #8824875983** (`Volatility 25 (1s) Index`, SELL `0.011 lot`, ouvert à 07:46:49) : Clôturé automatiquement par le Time-Stop après 4 barres H1 exactes (`Bars Held = 4/4`) à 11:42:39 (Deal `#8703508901`).
  - **Ticket #8825110205** (`Volatility 5 (1s) Index, M30`, BUY `0.200 lot`) : Déclenché automatiquement à 12:00:00 sur impulsion post-compression ($Z=1.32 \ge 1.25$, $\sigma_{20} = 3.43	ext{ bps} \le Q_{30}$), avec Hard SL à `95765.26` et Hard TP à `96133.88` (actuellement en cours de gestion en direct).
* **Compilation MetaEditor 64** : 0 erreur, 0 avertissement (76 286 octets).
* **Patch Critique v3.52 (Correction Inversion BUY/SELL sur S1)** :
  - *Cause du bug* : Un tableau local `double last_closes[2];` non indexé comme série (`AsSeries=false` par défaut en MQL5) recevait `last_closes[0] = Close[2]` et `last_closes[1] = Close[1]`, inversant le calcul du rendement (`Close[2] - Close[1]`) et déclenchant des BUY sur cassure baissière et SELL sur cassure haussière.
  - *Correctif v3.52 certifié* : Déclaration de `ExtLastRetBps` dans la télémétrie globale, affectation directe de `ExtLastRetBps = r_bps[0];` dans `UpdateMarketTelemetry()` (où `closes` est déjà strictement indexé en série), et utilisation directe de `ExtLastRetBps` dans `OnTick()`. Direction BUY/SELL 100% alignée avec le mouvement du marché.
  - *Clôture du trade inversé #8825110205* : Clôturé immédiatement et proprement via API FOK avec une variation négligeable (-1.52 USD).
  - *Compilation & Binaires* : 0 erreur, 0 avertissement (77 180 octets).


---

## 4. PISTES D'AMÉLIORATION & NOUVEAUX HORIZONS DE RECHERCHE DERIV

### 4.1. Améliorations Possibles sur le Bot Volatility (`v3.30` $\to$ `v3.40`)
1. **Trailing Stop Multi-Paliers (Ratchet Lock)** :
   - Actuellement, `v3.30` verrouille `Entry + 0.20 ATR` dès que le prix atteint `+1.20 ATR`.
   - *Amélioration possible* : Ajouter un second palier dynamique : si le prix atteint `+2.50 ATR`, monter le Stop-Loss à `+1.20 ATR` ; s'il atteint `+4.00 ATR`, suivre à `-1.00 ATR` sous le plus haut (permettant de sécuriser 70% des grands mouvements comme celui de `+$107.99$`).
2. **Déploiement sur d'autres indices de la famille Volatility (GBM)** :
   - Étendre l'architecture Squeeze H1 + GBDT ONNX aux indices `Volatility 10 (1s)`, `Volatility 50 (1s)` et `Volatility 100 (1s)` après vérification du ratio $\text{Spread} / \sigma_{\text{H1}}$.
3. **Hébergement VPS Windows 24/7** :
   - Éliminer les coupures d'alimentation ou mises en veille du PC local pour ne manquer aucun setup H1 nocturne.

### 4.2. Programme de Recherche Scientifique sur les 11 Familles Synthétiques Deriv
Pour la nouvelle discussion dédiée à la recherche et à la création de nouveaux bots spécifiques, voici les **familles prioritaires** à auditer avec `deriv_quant_engine.py` et `/agent-quant-pod` :
1. **Drift Switch Indices (`DSI 10`, `DSI 20`, `DSI 30`)** :
   - *Mécanisme serveur* : Processus à changement de régime markovien caché (bascule entre dérive positive Bull, négative Bear et neutre Sideways toutes les 10 à 30 minutes en moyenne).
   - *Outil déjà prêt dans le skill* : `cusum_sprt_regime_detector()` (Test séquentiel du rapport de vraisemblance de Wald / CUSUM) pour détecter la bascule de dérive en moins de 60 secondes et suivre le régime jusqu'à la bascule suivante.
2. **Range Break Indices (`Range Break 100`, `Range Break 200`)** :
   - *Mécanisme serveur* : Processus borné dans un canal avec probabilité de cassure franche. Analyse de la distribution du temps de séjour dans le range et du coût de spread.
3. **DEX Indices (`DEX 600`, `DEX 900`, `DEX 1500 UP/DOWN`) & Jump Indices (`Jump 10` à `Jump 100`)** :
   - *Mécanisme serveur* : Diffusion à sauts bilatéraux de Merton (sauts haussiers et baissiers superposés à une diffusion continue). Audit de la symétrie des sauts et de la compression de volatilité inter-sauts.
4. **Step, Multi-Step & Skew Step Indices** :
   - *Mécanisme serveur* : Marche aléatoire discrète à pas fixes ou asymétriques. Audit d'entropie NIST SP 800-90B (`nist_800_90b_min_entropy_estimate`) et du ratio spread/pas.
5. **Trek Indices (`Trek UP`, `Trek DOWN`)** :
   - *Mécanisme serveur* : Distribution à durée de vie de Weibull. Vérification empirique du taux de hasard $h(t)$ croissant ou constant.

---

## 5. COMMENT ACCÉDER AU REPO ET LANCER LA NOUVELLE DISCUSSION

### 5.1. Accès Humain vs Accès Agent IA
* **Pour toi (Humain) sur GitHub Web** :
  - Rendez-vous sur : **`https://github.com/Christ-yavn/bot-quant-`**
  - La page d'accueil affiche automatiquement **`README.md`** (rédigé en français clair, sans formules mathématiques lourdes, avec schémas d'architecture).
* **Pour l'Agent IA (dans la nouvelle discussion)** :
  - L'agent a un accès direct aux fichiers sur ton disque dur dans `C:\Users\CHRIST\Desktop\IA\ANTIGRAVITY\projets\general project   quant bot deriv\`.
  - Il lui suffit de lire **`AGENT.md`** et **`MEMOIRE_MAITRE_NOUVELLE_CONVERSATION.md`** pour récupérer instantanément 100 % de la mémoire de cette discussion.

### 5.2. Prompt Exact à Copier-Coller dans ta Nouvelle Discussion
Lorsque tu ouvres ta nouvelle discussion (et même après avoir supprimé celle-ci), colle simplement le bloc suivant comme premier message :

```text
Bonjour. Nous reprenons notre travail sur le projet QUANT BOT DERIV.
Avant toute réponse ou action, utilise immédiatement ton outil de lecture de fichier pour lire intégralement ces 3 fichiers situés dans mon dépôt local "C:\Users\CHRIST\Desktop\IA\ANTIGRAVITY\projets\general project   quant bot deriv" :
1. "C:\Users\CHRIST\Desktop\IA\ANTIGRAVITY\projets\general project   quant bot deriv\AGENT.md"
2. "C:\Users\CHRIST\Desktop\IA\ANTIGRAVITY\projets\general project   quant bot deriv\MEMOIRE_MAITRE_NOUVELLE_CONVERSATION.md"
3. "C:\Users\CHRIST\Desktop\IA\ANTIGRAVITY\projets\general project   quant bot deriv\CHANGELOG_AND_HISTORY.md"

Lis également le skill "/agent-quant-pod" dans "C:\Users\CHRIST\.gemini\config\skills\quant-pod\SKILL.md".
Rappelle-toi la règle absolue : lorsque nous lançons une recherche ou un audit avec /agent-quant-pod, tu dois travailler en vrai mode /teamwork en créant et déléguant les tâches à des sous-agents spécialisés (invoke_subagent) et en synthétisant leurs rapports.

Confirme-moi que tu as bien lu ces fichiers, résume-moi en 5 points l'état exact de nos bots (Boom/Crash v8.30 en pause et Volatility v3.30 Hardened actif avec son dernier trade à +107.99$), et tiens-toi prêt pour mes instructions de recherche sur les marchés Deriv.
```
