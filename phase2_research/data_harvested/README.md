# EXPORT_DRIVE_PHASE2_STEP_VOLATILITY
## Base de Données Quantitative Complète — 18 Actifs Synthétiques Deriv

Ce dossier contient l'ensemble des données récoltées et auditées lors de la **Phase 2** du projet de recherche quantitative :
* **1 280 000 barres** (D1, H1, M1)
* **286 514 ticks** haute résolution
* **18 actifs synthétiques** audités

---

### Structure des Données

1. **Manifeste de Récolte :**
   * [HARVEST_MANIFEST.csv](./HARVEST_MANIFEST.csv) : Inventaire exhaustif des 18 symboles, spreads mesurés en direct, dates et nombres de barres/ticks.

2. **Famille Step Index (6 actifs) :**
   * Step Index (Ticks, M1, H1)
   * Step Index 200 (D1, H1, M1)
   * Step Index 300 (D1, H1, M1)
   * Step Index 500 (D1, H1, M1)
   * Multi Step 2 Index (D1, H1, M1)
   * Multi Step 4 Index (D1, H1, M1)
   * *Conclusion d'audit :* Bruit blanc déterministe (Bernoulli =0.50$, =0.50$, Doob $\mathbb{E}[Trade] = -0.10\). Trading directionnel exclu.

3. **Famille Volatility Indices (12 actifs) :**
   * Volatility 10 Index & Volatility 10 (1s) Index
   * Volatility 25 Index & Volatility 25 (1s) Index ⭐ *(Alpha Validé : Spread 0.80 bps, Win Rate 61.5%, PF 1.73 OOS)*
   * Volatility 50 Index & Volatility 50 (1s) Index
   * Volatility 75 Index & Volatility 75 (1s) Index ⭐ *(Alpha Validé : Spread 3.22 bps)*
   * Volatility 100 Index & Volatility 100 (1s) Index
   * Volatility 150 (1s) Index & Volatility 250 (1s) Index

---

### Références Associées
* **Rapport Scientifique Complet :** [../../docs/Deriv_Synthetic_Indices_Phase2_Alpha_Audit_Report.pdf](../../docs/Deriv_Synthetic_Indices_Phase2_Alpha_Audit_Report.pdf)
* **Expert Advisor Validé MQL5 :** [../../src/mql5/Deriv_VolSqueeze_Breakout_EA.mq5](../../src/mql5/Deriv_VolSqueeze_Breakout_EA.mq5)
