# MÉMOIRE MAÎTRE & PROTOCOLE DE REPRISE INTÉGRALE (QUANT BOT DERIV)
## Document de Continuité Cognitive pour Nouvelle Discussion / Nouvel Agent IA

**Date de dernière mise à jour certifiée** : 10 Novembre 2026 (08:50 UTC — Version `v3.40 Panier Tri-Actifs Élite` déployée live)  
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

### 3.2. BOT N°2 : PANIER TRI-ACTIFS ÉLITE (`Deriv_VolSqueeze_Breakout_EA_v3.mq5`) — VERSION `v3.40` ACTIVE SUR 3 GRAPHIQUES SIMULTANÉS
* **Architecture Mathématique & Ingénierie (`v3.40 Panier Tri-Actifs Élite` — Signal Pur S1 Quant)** :
  - **Hypothèse structurelle** : La diversification horizontale sur 3 actifs non corrélés ($|\rho| \le 0.026$) à spreads infimes permet de tripler le nombre d'opportunités de trading (~100 trades/mois) sans abaisser la timeframe en-deçà du seuil critique de frottement brownien ($\text{Friction} \propto \frac{2s}{\sigma\sqrt{\Delta t}}$).
  - **La Matrice Tri-Actifs Déployée sur MT5** :
    1. **Graphique 1 : `Volatility 25 (1s) Index` (PERIOD_H1, Role `ALPHA_KING`)** : $Q=0.30, Z=1.25, H=4\text{ barres}$ (4.0h), Magic `20261021`, Cap `0.05 lot`. $WR = 58.33\%$, $+6.38\text{ bps/trade}$. Gère également le ticket live `#8824875983` (Magic `20261022`).
    2. **Graphique 2 : `Volatility 5 (1s) Index` (PERIOD_M30, Role `HIGH_FREQ`)** : $Q=0.30, Z=1.25, H=8\text{ barres}$ (4.0h), Magic `20261025`, Cap `0.20 lot`. $WR = 61.90\%$, $+0.12\text{ à }+0.41\text{ bps/trade}$.
    3. **Graphique 3 : `Volatility 15 (1s) Index` (PERIOD_M30, Role `STABILIZER`)** : $Q=0.30, Z=1.25, H=8\text{ barres}$ (4.0h), Magic `20261015`, Cap `0.50 lot`. $WR = 59.29\%$, $+0.46\text{ bps/trade}$.
  - **Sécurités Durcies Déployées en `v3.40`** :
    - **Cold-Boot Freshness Guard** : Initialisation stricte `ExtLastBarTime = iTime(_Symbol, ExtEffTimeframe, 0)` dans `OnInit()` et rejet systématique si `TimeCurrent() - bar_time > InpMaxEntryDelaySec` (300 s). Empêche définitivement l'ouverture retardée d'une position sur une bougie ancienne au redémarrage du terminal si le PC était éteint.
    - **Hard Disaster Stop-Loss Serveur (`InpUseHardTPSL = true`)** : Transmission obligatoire au serveur Deriv d'un Hard Stop-Loss natif à l'ouverture du trade à $2.50\times\text{ATR20}$ et d'un Take-Profit à $4.00\times\text{ATR20}$, protégeant le compte contre tout crash matériel ou coupure réseau.
    - **Profit Lock Dynamique Anti-Spam** : Calculé sur l'ATR de la bougie clôturée (`shift=1`) avec normalisation `NormalizePrice()`, cooldown de 10 s et vérification `SYMBOL_TRADE_STOPS_LEVEL`.
    - **Priorité Time-Stop** : Clôture temporelle stricte évaluée avant tout `PositionModify`.
  - **Audit Forensique des Trades du 06/11 et 10/11/2026** :
    - Les deux pertes du 06/11 étaient dues à l'arrêt du PC pendant 8h27 (retardant le time-stop de `#8821123131`) et à une sortie normale au time-stop (`#8821764050`).
    - L'entrée immédiate du 10/11 (`#8824875983`) était causée par `ExtLastBarTime = 0` évaluant la barre de 07:00 avec 46 min de retard. Elle est désormais impossible grâce au Cold-Boot Guard. Le trade `#8824875983` est activement et sécuritairement géré par `v3.40` sur le Graphique 1.
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
