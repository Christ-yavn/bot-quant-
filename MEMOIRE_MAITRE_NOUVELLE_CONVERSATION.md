# MÉMOIRE MAÎTRE & PROTOCOLE DE REPRISE INTÉGRALE (QUANT BOT DERIV)
## Document de Continuité Cognitive pour Nouvelle Discussion / Nouvel Agent IA

**Date de dernière mise à jour certifiée** : 2 Novembre 2026 (00:25 UTC — Version `v3.31 Hardened` déployée live)  
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

### 3.2. BOT N°2 : VOLATILITY 25 (1s) [ACTIF ROI] & VOLATILITY 75 (1s) [EN PAUSE PROTECTRICE] (`Deriv_VolSqueeze_Breakout_EA_v3.mq5`) — VERSION `v3.31 HARDENED` ACTIVE ET RENTABLE
* **Architecture Mathématique & Ingénierie (`v3.31 Hardened` — Signal Pur S1 Quant)** :
  - **Hypothèse structurelle** : Sur **`Volatility 25 (1s) Index`** en H1 (où le spread réel exécutable n'est que de `0.62–0.74 bps`, soit `< 3.5 %` de $\sigma_{\text{H1}}$), la compression de volatilité (*Squeeze*) suivie d'une cassure d'impulsion (*Impulse Breakout*) combinée au verrouillage dynamique des excursions (*Dynamic Profit Lock*) génère un avantage net robuste ($t = +2.63$ sur 15 000 barres H1, Win Rate `58.0 %` en Train et `60.2 %` en Holdout OOS, $t = +1.89$).
  - **Les 3 Portes d'Entrée Déterministes en H1 (Mode Pure S1 — Zéro Boîte Noire)** :
    1. **Compression (Squeeze)** : $\sigma_{20}$ (calculée avec $ddof=1$ sur `shift=1`, zéro look-ahead) doit être inférieure ou égale au **30ème percentile** des 100 dernières barres ($\sigma_{20} \le Q_{0.30}$, `InpSqueezeQuantile = 0.30`).
    2. **Cassure d'Impulsion (Breakout)** : Le rendement de la bougie H1 qui vient de clôturer doit franchir $|Z| = |r_{1\text{h}}| / \sigma_{20} \ge 1.25$ (`InpBreakoutZScore = 1.25`).
    3. **Filtre de Spread Live** : Vérification en temps réel via `SymbolInfoTick` que $\text{Spread} \le 4.50\text{ bps}$ et $\text{Spread}/\text{ATR}_{20} \le 5.0\%$.
  - **Pourquoi le filtre IA ONNX est désactivé par défaut (`InpUseONNXFilter = false`) en `v3.31`** :
    - L'audit contradictoire `/agent-quant-pod` du `02/11/2026` a démontré que `c2_vol_filter.onnx` et `c2_vol_filter_v25.onnx` sont identiques bit à bit (`13 180` octets, SHA-256 `e641cd39...`) et affichent un **ROC-AUC Out-Of-Sample de `0.4457` (`< 0.50`)** post-août 2025 (le seuil `0.42` laissait passer `98.64 %` des trades tout en éliminant aléatoirement ~`1.4 %` de vrais signaux). Sur V75, `c2_vol_filter_v75.onnx` (`11 647` octets) affichait `-6.21 bps/trade` en Holdout (`DSR = 0.1863`). Tous les modèles `.onnx` et le pipeline 7 features sont préservés intacts dans `src/models/` (Règles 2, 3 et 4), mais court-circuités en production au profit du signal pur S1.
  - **Pourquoi `Volatility 75 (1s)` est placé en Pause Protectrice (`InpAllowV75Trading = false`)** :
    - Le spread réel live sur V75 (`3.22–3.74 bps`) absorbe l'avantage statistique H1 ($t_{\text{holdout}} = +0.45$). `v3.31` maintient le graphique V75 en mode `PAUSED_STANDBY` (`EN PAUSE PROTECTION CAPITAL`) et concentre 100 % du risque sur l'actif roi `Volatility 25 (1s)`.
* **Les Améliorations Majeures Déployées dans la Version Actuelle `v3.31 Hardened` (`archive/mql5_legacy/Deriv_VolSqueeze_Breakout_EA_v3_30.*` archivé)** :
  1. **Anti-Spam `PositionModify` sur ATR Clôturé (`Fix Bug 1 v3.31`)** :
     - Remplacement de `CopyBuffer(ExtATRHandle, 0, 0, 1, ...)` par **`shift=1`** (bougie H1 clôturée), ajout d'une tolérance stricte `> 0.5 * _Point` et d'un cooldown de `10 s` en cas d'échec, éliminant tout risque de rafale `PositionModify` à chaque tick (`1 Hz`) vers le serveur Deriv.
  2. **Normalisation Exacte au TickSize & `_Digits` (`Fix Bug 2 v3.31`)** :
     - Fonction `NormalizePrice()` appliquée systématiquement à `target_sl` (Profit Lock) et aux `sl`/`tp` d'entrée, avec vérification explicite de `SYMBOL_TRADE_STOPS_LEVEL` et `SYMBOL_TRADE_FREEZE_LEVEL` (zéro erreur `10015 TRADE_RETCODE_INVALID_PRICE`).
  3. **Priorité du Time-Stop avant Profit Lock & Clôture Vérifiée (`Hardening 3, 4 & 5 v3.31`)** :
     - Dans `ManageOpenPositions()`, le Time-Stop (`bars_elapsed >= InpMaxHoldBars = 4`) est exécuté **avant** le bloc Profit Lock (évitant un `PositionModify` inutile `1 ms` avant clôture), la valeur de retour de `ExtTrade.PositionClose(ticket)` est vérifiée avant de libérer le verrou de position, et `InpSlippagePoints` est relevé à `50` points.
  4. **Préservation intégrale des correctifs `v3.30` (`VULN-02`, `VULN-03`, `VULN-05/06`)** :
     - `ManageOpenPositions()` en tête de `OnTick()` avant le coupe-circuit journalier (`-3.0%`), remplissage dynamique `IOC/FOK/RETURN`, arrondi IEEE 754 `+ 1e-8` et plafond de lot (`0.05` sur V25, `0.02` sur V75).
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
