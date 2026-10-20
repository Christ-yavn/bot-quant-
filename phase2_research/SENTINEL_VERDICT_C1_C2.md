# PH2-C1/C2 — VERDICT SENTINELLE & PLAN DE DÉPLOIEMENT GATE 5
**Date : 2026-10-20 | Branche : `research/c1-c2-results` | Manifeste scellé : `phase2_research/manifests/manifest_c1.json`**

## 1. Verdict C1 (validation Sentinel S1 Volatility Squeeze Breakout, H1)

| Condition | V25 (1s) | V75 (1s) |
| :--- | :---: | :---: |
| C1 — IC BCa 95 % exclut 0 | ✅ [+2,70 ; +10,80] bps | ❌ [−9,87 ; +15,97] |
| C2 — p(H₀) < 0,05 après BH | ✅ 0,0007 (BH 0,0037, **Holm α=1 % rejette aussi**) | ❌ 0,329 |
| C3 — Placebo GBM rang > 95 % | ✅ 1,0000 / 2 000 | ❌ 0,8225 |
| C4 — Pas de rupture structurelle | ✅ Welch t=+0,61, p=0,54 | ⚠️ t=+1,45, p=0,15 |

**DÉCISION : V25 (1s) = PASS (4/4). V75 (1s) = FAIL (1/4) → EXCLU DÉFINITIVEMENT.**
Le verdict « OVERALL: FAIL » affiché par le script est un **artefact v1** (agrégation `all()` des deux symboles) ; le verdict correct est **par symbole** et est consigné dans le manifeste.

### Preuves renforcées pour V25 (1s) — au-delà des conditions minimales
- p unilatéral = 0,000526 **< α Bonferroni-48 = 0,00104** : l'edge survit même à la correction la plus stricte des 48 écrans H1.
- **Holm–Bonferroni (FWER α = 1 %) rejette H₀** sur la famille honnête de 14 hypothèses.
- **DSR(N=48) = +0,011 > 0** (Bailey–López de Prado) : l'edge survit à la déflation du Sharpe pour 48 essais.
- Placebo GBM : rang **1,0000 / 2 000** (aucune trajectoire martingale simulée n'a reproduit ce t-stat).
- Splits chronologiques : Train +5,70 (t=+2,09) / Val +5,81 (t=+1,37) / OOS +10,66 (t=+2,31) — positif partout, y compris le premier 60 % (l'inquiétude de nullité du Train concernait la cellule baseline q=0,25/z=1,50, pas la cellule robuste q=0,30/z=1,25 déployée).
- Espérance nette : **+6,76 bps/trade** (N=632), WR 54,5 %, PF ≈ 1,38.

### V75 (1s) — autopsie du rejet
Train négatif (−4,94 bps, t=−0,60) ; tout l'« alpha » apparent vient de la fenêtre Val (+26,80 bps) ; IC BCa traverse 0 ; placebo non dépassé. C'est du bruit de sélection : le +14,77 bps du rapport Gemini était non significatif (p=0,33 sous H₀).

## 2. Verdict C2 (filtre ONNX)

| Métrique OOS | Valeur | Interprétation |
| :--- | :--- | :--- |
| Précision sur trades filtrés | 62,82 % (vs base 53,90 %) | Lift apparent |
| Accuracy globale | 55,83 % | — |
| **ROC-AUC OOS** | **0,554** | **≈ hasard — NON VALIDÉ** |

**Décision : la gate ONNX reste DÉSACTIVÉE dans l'EA v3.00** (`InpUseOnnxFilter = false`). L'edge de V25 est prouvé *sans* filtre. Le modèle `c2_vol_filter.onnx` est archivé, non déployé. Pour réactiver : AUC OOS ≥ 0,58 avec purged K-fold + embargo, et amélioration simultanée de l'espérance nette OOS *et* du PSR — exigences non satisfaites.

## 3. Livrables de cette branche

| Fichier | Rôle |
| :--- | :--- |
| `phase2_research/scripts/Deriv_VolSqueeze_Breakout_EA_v3.mq5` | **EA v3.00 production** : garde Sentinel (symbole autorisé = V25 1s uniquement), cellule robuste q=0,30/z=1,25, gate ONNX off par défaut (fail-open), coupe-circuits spread et −3 %/jour conservés |
| `phase2_research/manifests/manifest_c1.json` | Manifeste scellé SHA-256 (payload_sha256 = `debc8b31d89b248f…`) avec verdict par symbole et note sur l'artefact v1 |

## 4. Plan Gate 5 — déploiement démo MT5 (obligatoire avant tout live)

1. **Compiler** `Deriv_VolSqueeze_Breakout_EA_v3.mq5` dans MetaEditor 5 (F7, zéro erreur attendue).
2. **Attacher sur un graphique H1 de `Volatility 25 (1s) Index` UNIQUEMENT** (le garde Sentinel refuse tout autre symbole — c'est voulu).
3. **Compte DÉMO** (ex. 32449166 à 10 000 USD), Magic 20261021.
4. **Paramètres par défaut inchangés** : q=0,30, z=1,25, hold=4, risque 0,50 %/1σ, spread max 4,50 bps, −3 %/jour, ONNX off.
5. **Durée : 20 sessions minimum (~4 semaines, ~1-3 trades/jour attendus).** Ne toucher à aucun paramètre pendant la période.
6. **Critères de poursuite vers le live** (cumulatifs) :
   - Espérance live nette > 0 sur ≥ 60 trades ;
   - Divergence live vs backtest (C1 : +6,76 bps/trade attendu) **< 20 %** sur l'espérance par trade ;
   - Win rate dans [48 % ; 62 %] et PF > 1,10 ;
   - Zéro violation des coupe-circuits (toute violation = analyse avant reprise).
7. **Toute divergence > 20 % ⇒ STOP, analyse, recalibration ou rejet** — pas de « ça va passer ».

## 5. Rappel des interdictions permanentes (Phase 1 & 2)

Scalping M1 (toutes les 48 paires falsifiées post-spread) · Step Index (Rademacher pur) · mean-reversion sur niveaux de prix · V150/V250 (1s) · tout live sans Gate 5.

---
*Ce document est fourni à titre d'information et de recherche uniquement ; il ne s'agit pas d'un conseil en investissement. Les performances passées (backtests, Monte Carlo) ne garantissent aucun résultat futur.*
