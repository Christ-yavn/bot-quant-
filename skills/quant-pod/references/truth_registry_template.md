# Registre d'État de la Vérité (`TRUTH.md` — Template)

Ce fichier est la mémoire scientifique vivante et immuable du projet quantitatif.
Il empêche l'agent (et l'utilisateur) de tourner en rond en retestant des idées déjà réfutées ou en oubliant l'écart entre les coûts théoriques et les coûts live.

> **Règle d'Or** : Toute ligne ajoutée dans ce registre doit pointer vers un script reproductible et un fichier de résultats JSON/CSV horodaté. On ne supprime jamais une hypothèse réfutée : un résultat négatif rigoureux protège le capital.

---

```markdown
# ÉTAT DE LA VÉRITÉ — [Nom du Projet / Repository]
**Dernière mise à jour** : YYYY-MM-DD
**Compteur cumulé d'essais ($K_{\text{total}}$)** : <int> (source : `research_ledger.jsonl`)

---

## 1. Caractérisation Empirique des Marchés & Coûts Réels (`[MESURÉ]`)

| Actif / Famille | Période & Taille Échantillon | Propriétés DGP Mesurées (ACF, VR, Vol, Sauts) | Spread Historique (MT5/CSV) | Spread Live Réel Mesuré | Verdict Structurel (Plafond de Doob) | Preuve / Script |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Ex: Boom/Crash (6 indices) | 6.8M ticks (mars 2026) + 648 trades live | Inter-spike $\text{CV} \approx 1.00$, $\text{ACF}(1) \approx 0$, hasard plat | 1 point (fictif) | 300 à 2600 points (96.5% de la perte live) | **Martingale pure** : $\mathbb{E}[\text{PnL}] = -\text{Spread}_{\text{live}} < 0$ | `docs/ETAT_DE_LA_VERITE.md` |
| Ex: Step Index | 1.37M ticks + 50k M1 | Marche aléatoire symétrique $\pm 0.1$ ($p=0.5008$, $\text{ACF}(1) \approx 0$) | 0.10 pt | 0.10 pt (~1 bps) | **Martingale pure** : aucun edge directionnel possible | `audit_step_volatility.py` |
| Ex: Volatility 25 (1s) | 56 046 barres H1 (2020-2026) | Vol clustering ($\text{ACF}(|r|, 1) \approx 0.21$), mais rendements signés $\text{ACF}(r, 1) \approx 0$ | ~1.5 bps | ~1.5-2.0 bps | Non-significatif sur 6.3 ans ($t=+1.58$, $\text{DSR}=0.053$) | `audit_vol_squeeze.py` |

---

## 2. Manifeste du Holdout Verrouillé (SHA-256)

| Dataset ID | Chemin du Fichier Holdout | Plage Temporelle (20% finaux) | Empreinte SHA-256 | Statut |
| :--- | :--- | :--- | :--- | :--- |
| `<dataset_id>` | `<path_to_holdout.parquet>` | `YYYY-MM-DD` $\to$ `YYYY-MM-DD` | `<sha256_hex>` | `LOCKED (Unused)` ou `CONSUMED (YYYY-MM-DD)` |

---

## 3. Registre des Hypothèses Validées (`/boost` 5/5 + Holdout)

| ID | Titre & Mécanisme | Marché / TF | $N_{\text{trades}}$ | Sharpe Ann. (Net 1x) | Sharpe (Stress 2x) | $\text{DSR}(K)$ | $\text{PBO}$ | $p_{\text{null}}$ | Plateau | Verdict Holdout | Script & Artefact |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| *Aucune à ce jour* | - | - | - | - | - | - | - | - | - | - | - |

---

## 4. Cimetière des Hypothèses Réfutées (Ne Jamais Retester à l'Identique)

| ID | Hypothèse Testée | Marché / TF | Résultat Observé | Porte `/boost` Échouée | Cause Racine de l'Échec | Date & Script de Preuve |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| H001 | Inversion convexe post-spike Boom/Crash (v8.30/v8.40) | Boom/Crash 300-1000 (Tick) | $-311.20\$$ sur 648 trades live ; $\text{EV} < 0$ sur les 6 indices | Pré-filtre DGP (Martingale) + G4 (Coûts live) | Processus de Poisson sans mémoire ; abaisser `InpMinEvUsd` sous $0\$$ force des trades à $\text{EV} < 0$. | `ETAT_DE_LA_VERITE.md` |
| H002 | Volatility Squeeze Breakout `(q=0.30, z=1.25, H=4)` | 12 indices Volatility (H1) | $+6.85\text{ bps}$ ($t=3.33$) sur V25(1s) 15k barres, mais $+2.21\text{ bps}$ ($t=1.58$) sur 56k barres ; 1 seul indice sur 12 a $t>2$ | G1 ($\text{DSR}=0.053 < 0.95$ pour $K=1500$) & G3 ($p_{\text{null}}=0.171 > 0.05$) | Biais de sélection multiple ($125 \times 12 = 1500$ essais) : un bruit gaussien pur produit $\max t \approx 2.89$ en moyenne et $t \ge 3.33$ dans $17.1\%$ des cas. | `verify_volsqueeze_claim.py` & `null_all12.json` |
| H003 | Filtre ML ONNX `c2_vol_filter.onnx` sur VolSqueeze | Volatility 25 (1s) H1 | $\text{ROC-AUC OOS} = 0.4671 < 0.50$ | G1 / Prédiction nulle | Absence de persistance directionnelle prédictible après normalisation causale. | `c2_vol_filter_metadata.json` |
| H004 | Contrats à paiement fixe Deriv (349 contrats sur 9 familles) | Multipliers, Turbos, Vanillas, Accumulators | $0 / 349$ contrats avec $\text{EV} > 0$ ($\text{EV}_{\text{moy}} = -6.58\%$) | Pré-filtre $\text{EV} \le 0$ | Marge du broker intégrée dans le pricing analytique et le spread implicite de volatilité. | `deriv_contracts_ev_report.json` |

---

## 5. Pistes Ouvertes Prioritaires (Backlog de Recherche)

1. **[H005 — À définir]** : ...
```
