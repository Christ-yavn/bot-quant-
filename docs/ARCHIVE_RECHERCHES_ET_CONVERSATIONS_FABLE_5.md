# ARCHIVE OFFICIELLE DES RECHERCHES ET CONVERSATIONS AVEC CLAUDE FABLE 5
## R&D Systémique, Inversion de Convexité & Falsification Quantitative (Multi-Track)
### Référence : ARCHIVE-FABLE5-V8-20261020 | Dépôt Git : https://github.com/Christ-yavn/bot-quant-

---

> [!IMPORTANT]
> **Statut du Document :**  
> Ce document constitue l'inventaire officiel, exhaustif et pérenne de l'ensemble des sessions de recherche menées avec **Claude Fable 5** (Ashna AI) par la Direction de Recherche Quantitative.  
> Il synthétise les théorèmes stochastiques, les protocoles de falsification statistique et les solutions d'ingénierie logicielle ayant permis le déploiement du système dual en direct sur MetaTrader 5.

---

## 1. REGISTRE CENTRAL DES CONVERSATIONS OFFICIELLES (ASHNA AI)

| Session # | Date | URL Pérenne Ashna AI | Thématique Fondamentale & Livrables Majeurs |
| :---: | :---: | :--- | :--- |
| **Session 1** | 2026-10-20 | [https://app.ashna.ai/chat/6ad691c5a83de54d569d8c5a?agent=claude-fable-5](https://app.ashna.ai/chat/6ad691c5a83de54d569d8c5a?agent=claude-fable-5) | **Phase 2 Track 2 :** Analyse microstructurelle des indices de Volatilité H1 et Step Index. Falsification par Doob du Step Index. Découverte de l'asymétrie de compression sur Volatility 25 (1s). Validation Sentinel C1/C2 (DSR, BCa bootstrap, Welch, Placebo). Intégration des aires de Lévy (Rough Paths) et entraînement du classifieur ONNX C2. Spécification de l'EA Deriv_VolSqueeze_Breakout_EA_v3.mq5. |
| **Session 2** | 2026-10-20 | [https://app.ashna.ai/chat/6ad75c564b55dd601aa09d82?agent=claude-fable-5](https://app.ashna.ai/chat/6ad75c564b55dd601aa09d82?agent=claude-fable-5) | **Forensique v7 & Inversion Convexe (Track 1) :** Audit des 1 242 trades réels v7 (-406.14 USD). Découverte que la v7 achetait du drift calme et sous-payait le risque de saut (asymétrie négative). Réfutation mathématique de la martingale. Preuve contrefactuelle du miroir (+340.73 USD). Dérivation analytique du stop temporel optimal ^*$. Mécanique de capture hybride (Take-Profit dur + Watchdog de clôture tick-exacte). Dimensionnement Kelly convexe et gestion de ruine. |
| **Session 3** | 2026-10-20 | [https://app.ashna.ai/chat/6ad7ef4cfd29d02fc4aaef4c?agent=claude-fable-5](https://app.ashna.ai/chat/6ad7ef4cfd29d02fc4aaef4c?agent=claude-fable-5) | **Audit Statique & Checklist d'Implémentation v8 :** Examen rigoureux du code DerivBoomCrashHFT_v8.mq5. Établissement de la grille de conformité FIX-1 à FIX-10. Curseur CopyTicks sans perte de tick, alignement des horloges 	ime_msc et débit tick/s mesuré. Suppression du mode urgence bloquant. Mesure dynamique du capture ratio ({\\text{capture}} / A_{\\text{MFE}}$). Filtre d'entrée EV (Expected Value) conservative. Calibration Kelly sur le Stop-Loss serveur réel. Refus strict des symboles non calibrés. |

---

## 2. SYNTHÈSE THÉORIQUE ET MATHÉMATIQUE DES ÉCHANGES

### 2.1 La Falsification du Drift Harvesting (v7) et l'Origine de l'Alpha Convexe (v8)
Sur les indices Boom et Crash de Deriv, le processus générateur de prix suit une dynamique de saut-diffusion asymétrique :
dp_t = \\mu \\, dt + \\sigma \\, dW_t + J_t \\, dN_t
où :
- Sur **Crash Index** : $\\mu > 0$ (drift régulier haussier tick par tick),  < 0$ (sauts descendants instantanés d'amplitude exponentielle $\\sim \\text{Exp}(1/\\bar{A})$), $ est un processus de Poisson composé d'intensité $\\lambda_t$.
- Sur **Boom Index** : $\\mu < 0$ (drift régulier baissier tick par tick),  > 0$ (sauts ascendants instantanés).

La version v7 vendait Crash (ou achetait Boom) pour récolter le drift calme $\\mu$.  
Elle affichait un taux de réussite de **85.91 %** (1 067 gains / 175 pertes), mais un gain moyen de $+0.20$ USD contre une perte moyenne de $-3.54$ USD, conduisant à un P&L net de **-406.14 USD**.  
L'analyse de Claude Fable 5 a démontré que **le filtre v7 sélectionnait paradoxalement les régimes où le taux de saut $\\lambda_t$ était anormalement élevé**, vendant précisément au moment où la probabilité de spike était maximale.

En appliquant le **principe d'inversion de Charlie Munger**, la v8 inverse intégralement la posture :
- Crash Index $\\rightarrow$ **SELL** (au lieu de BUY), pariant sur l'occurrence du spike baissier.
- Boom Index $\\rightarrow$ **BUY** (au lieu de SELL), pariant sur l'occurrence du spike haussier.
- Taux de gain attendu : $\\sim 15 - 25\\%$, mais ratio gain/perte  \\ge 8.0 - 15.0$, transformant l'asymétrie de concave (pertes rares mais cataclysmiques) à **convexe (gains rares mais colossaux)**.

---

### 2.2 Dérivation Analytique du Stop Temporel ^*$
L'une des contributions majeures de la Session 2 est la **réfutation de l'existence d'un optimum intérieur non contraint** pour un processus de Poisson pur.  
Si  \\sim \\text{Exp}(\\lambda)$, l'espérance de gain en sortant à $ ticks sans survenance de saut s'écrit :
\\mathbb{E}[\\Pi(M)] = (1 - e^{-\\lambda M})(k_{\\text{TP}} \\bar{A} - S) - e^{-\\lambda M} (\\mu M + S)
La dérivée première par rapport à $ vaut :
\\frac{d\\mathbb{E}}{dM} = \\lambda e^{-\\lambda M} (k_{\\text{TP}} \\bar{A} + \\mu M) - \\mu e^{-\\lambda M} = e^{-\\lambda M} [\\lambda k_{\\text{TP}} \\bar{A} - \\mu (1 - \\lambda M)]
Pour que cette dérivée s'annule, la dépendance montre que ^*$ opérationnel est dicté par trois contraintes physiques contraignantes :
1. **Borne inférieure du spread :**  \\ge M_{\\min} = \\frac{S}{\\mu \\cdot (k_{\\text{TP}} \\bar{A} / S - 1)}$, garantissant que l'espérance amortit le spread payé au broker.
2. **Borne supérieure de variance (Kelly) :**  \\le M_{\\max} = \\frac{L_{\\max}}{\\mu}$, limitant la perte adverse maximale par trade pour éviter le risque de ruine.
3. **Horizon empirique calibré :** Pour un horizon de rétention de ^* = 60$ ticks (~1 minute), le ratio de capture de spike $\\mathbb{P}(T \\le 60) \\approx 6.0\\% - 10.0\\%$ offre le meilleur compromis variance / turnover.

---

### 2.3 Mécanique de Sortie Hybride : Take-Profit Dur Serveur + Watchdog Tick-Exact
L'analyse de la microstructure de Deriv a établi que **le spike est un saut discontinu d'une durée de 0 milliseconde** (tick unique).  
Trois architectures de sortie ont été comparées :
1. *Take-Profit dur sur le serveur :* Indispensable pour capter le saut au niveau du carnet sans subir le round-trip réseau (30-80 ms).
2. *Watchdog côté client (tick à tick) :* Surveille chaque variation $|\Delta p| > \\theta_{\\text{spike}}$ pour clôturer immédiatement si le serveur n'a pas déclenché le TP (ex. spike partiel ou slippage).
3. *Stop temporel ^*$ :* Sortie au marché immédiate dès que l'âge du trade atteint ^*$ ticks sans qu'un saut ne soit survenu.

L'architecture v8 implémente la combinaison exacte :
- 
eq.tp fixé à {\\text{entry}} \\pm (k_{\\text{TP}} \\cdot \\bar{A})$ dès l'ordre initial.
- Détection instantanée post-spike et clôture de confirmation.
- Clôture au marché non négociable dès que $\\text{age} \\ge M^*$.

---

### 2.4 La Grille de Contrôle Qualité Statique FIX-1 à FIX-10 (Session 3)

| ID | Domaine | Problème Détecté | Solution Implémentée dans DerivBoomCrashHFT_v8.mq5 |
| :---: | :--- | :--- | :--- |
| **FIX-1** | Flux Ticks | Perte de ticks due à la réinitialisation de last_time_msc | Curseur CopyTicks persistant avec déduplication par last_ms_consumed |
| **FIX-2** | Horloges | Désynchronisation entre temps serveur et temps CPU local | Horloge 	ime_msc unifiée et débit réel 	icks_per_sec mesuré en continu |
| **FIX-3** | Coupe-circuit | Le mode urgence figeait les positions sans pouvoir les fermer | Urgence = flatten immédiat + gestion continue active (seules les entrées sont gelées) |
| **FIX-4** | Métriques | Ratio de capture {\\text{capture}}/A$ fixé artificiellement à 0.90 | Mesure réelle  / MFE$ clampée entre 0.0 et 1.5 par position fermée |
| **FIX-5** | Lift d'aléa | Calcul du lift faussé par le décompte de ticks | $\\text{Lift} = \\sum \\text{spikes} / \\sum \\text{aléa de base à l'entrée}$ sur fenêtre glissante |
| **FIX-6** | Payoff | Hypothèse de gain certain au Take-Profit | Espérance conservatrice : $\\mathbb{P}(A \\ge TP) = e^{-TP / \\bar{A}}$, dérive payée $= \\mathbb{E}[T \\mid T \\le M]$ |
| **FIX-7** | Sizing Kelly | Kelly calculé sur un Stop-Loss virtuel théorique | Dimensionnement basé sur le Stop-Loss réel serveur + marge de slippage broker |
| **FIX-8** | Univers | Risque d'exécution sur symboles non caractérisés | Refus catégorique de tout symbole absent de la table des priors calibrés |
| **FIX-9** | Comptabilité | P&L calculé sur deals partiels au lieu de la position | Agrégation rigoureuse de tous les deals OUT d'une position fermée |
| **FIX-10**| Drawdown | Seuil de perte journalière persistant d'un jour sur l'autre | Réinitialisation automatique du solde de référence chaque jour à 00:00 UTC |

---

## 3. PROTOCOLE DE GO / NO-GO MULTI-ÉTAPES (G0 À G3)

L'implémentation de la v8 est régie par le protocole formel de déploiement progressif :
- **G0 (Backtest & Simulation) :** Backtest tick-par-tick multi-sessions $\\ge 300$ trades, Profit Factor $\\ge 1.50$, espérance $> 0$ sur $\\ge 3$ sessions distinctes.
- **G1 (Incubation Démo 2 semaines) :** Compte démo officiel (Deriv MT5 32449166), lots minimums broker (0.20 lot) : $\\ge 500$ trades,  \\ge 1.60$, ratio de capture mesuré $\\ge 0.90$, rejets [Invalid stops] = 0, lift $\\ge 1.40$.
- **G2 (Fraction de Kelly Prudente) :** Passage à /8$ Kelly uniquement après signature formelle de validation du Gate G1.
- **G3 (Montée en Charge Capitalisée) :** Augmentation de $+25\\%$ de risque par palier de 250 trades conformes ( < 3\\%$).

---

## 4. LOCALISATION DES FICHIERS SOURCES ASSOCIÉS DANS LE DÉPÔT

- **Robot v8 MQL5 :** [src/mql5/DerivBoomCrashHFT_v8.mq5](../src/mql5/DerivBoomCrashHFT_v8.mq5)
- **Robot Track 2 (Vol 25 1s) :** [src/mql5/Deriv_VolSqueeze_Breakout_EA_v3.mq5](../src/mql5/Deriv_VolSqueeze_Breakout_EA_v3.mq5)
- **Modèle ONNX C2 :** [src/models/c2_vol_filter.onnx](../src/models/c2_vol_filter.onnx)
- **Rapport d'Inversion v8 :** [docs/RAPPORT_CLAUDE_FABLE_5_V8.md](RAPPORT_CLAUDE_FABLE_5_V8.md)
- **Prompt Maître d'Inversion :** [docs/PROMPT_AUDIT_ET_INVERSION_V7_A_V8_POUR_AUTRE_AGENT.md](PROMPT_AUDIT_ET_INVERSION_V7_A_V8_POUR_AUTRE_AGENT.md)
- **Encyclopédie Tome II :** [docs/ENCYCLOPEDIE_TOME_2_SYSTEME_DUAL_HFT_ET_ONNX_VOLATILITE.md](ENCYCLOPEDIE_TOME_2_SYSTEME_DUAL_HFT_ET_ONNX_VOLATILITE.md)
- **Télémétrie Live Python :** [src/python/analytics/monitor_dual_bots.py](../src/python/analytics/monitor_dual_bots.py)
