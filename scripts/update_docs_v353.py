import os

def update_docs_v353():
    repo_root = r"C:\Users\CHRIST\Desktop\IA\ANTIGRAVITY\projets\general project   quant bot deriv"

    # 1. Update AGENT.md
    agent_path = os.path.join(repo_root, "AGENT.md")
    with open(agent_path, "r", encoding="utf-8") as f:
        agent_content = f.read()

    agent_content = agent_content.replace(
        "| `v3.52 Direction Fix (S1 Direction Bug Solved)` | **ACTIF EN PRODUCTION (Omni-Basket S1/S2/S3 & Dashboard Rétractable MQL5)** |",
        "| `v3.53 Basket & Lot Optimization (Scan 94 Actifs L99)` | **ACTIF EN PRODUCTION (Omni-Basket S1/S2/S3 & Dashboard Rétractable MQL5)** |"
    )
    agent_content = agent_content.replace(
        "• **Correctifs v3.50, v3.51 & v3.52** : Télémétrie continue, correctif chirurgical Lookback Shift (`ExtLastStd20 = rolling_std[1]`), statut Profit Lock exact, correctif critique v3.52 du sens BUY/SELL (`ExtLastRetBps = r_bps[0]` éliminant l'inversion d'indexation MQL5), garde marge `OrderCalcMargin`, filtre direction.",
        "• **Correctifs v3.50, v3.51, v3.52 & v3.53** : Télémétrie continue, correctif Lookback Shift (`ExtLastStd20 = rolling_std[1]`), statut Profit Lock exact, correctif critique sens BUY/SELL (`ExtLastRetBps = r_bps[0]`), optimisation panier v3.53 (V10 en pause, V15 lot cap 0.050, V25 dual TF M30/H1), garde marge `OrderCalcMargin`, filtre direction."
    )
    with open(agent_path, "w", encoding="utf-8") as f:
        f.write(agent_content)
    print("Updated AGENT.md")

    # 2. Update MEMOIRE_MAITRE_NOUVELLE_CONVERSATION.md
    mem_path = os.path.join(repo_root, "MEMOIRE_MAITRE_NOUVELLE_CONVERSATION.md")
    with open(mem_path, "r", encoding="utf-8") as f:
        mem_content = f.read()

    mem_content = mem_content.replace(
        "Date de dernière mise à jour certifiée** : 10 Novembre 2026 (13:15 UTC — Version `v3.52 Direction Fix` déployée live)",
        "Date de dernière mise à jour certifiée** : 10 Novembre 2026 (14:15 UTC — Version `v3.53 Basket & Lot Optimization` déployée live)"
    )

    v353_summary = """
* **Optimisation Panier v3.53 (Issu du Scan Quant-Pod L99 sur 94 Actifs Deriv)** :
  - *Désactivation Volatility 10 Index* : Espérance nette négative observée sur 3 944 trades (-0.561 bps, t = -1.693, Kelly = 0.00%). Désactivé avec `ExtIsSymbolPaused = true` et rôle `"V10_STD_PAUSED"`.
  - *Réduction Lot Cap Volatility 15 (1s)* : Réduit de 0.500 à 0.050 lot dans le code et les presets .set pour éviter l'écrasement des champions par un actif à faible gain moyen (+0.052 bps tombant à -0.543 bps sous friction 2x).
  - *Support Bi-Timeframe Volatility 25 (1s)* : Prise en charge native de M30 (H=8 barres) et H1 (H=4 barres), offrant 63.86% de Win Rate et +3.424 bps/trade avec 2x plus d'opportunités.
  - *Portefeuille Champions* : Ladder Volatility Up (H4, S2, 63.43%), DEX 1500 DOWN (M15/H1, S1, 56.50%), Crash 550 (H4, S1, 59.30%), Range Break 200 (H1, S3, 53.30%), V25 (1s) (M30/H1, S1) et V5 (1s) (M30, S1).
  - *Compilation MetaEditor 64* : 0 erreur, 0 avertissement (76 808 octets).
"""
    if "* **Optimisation Panier v3.53" not in mem_content:
        mem_content = mem_content.replace(
            "- *Compilation & Binaires* : 0 erreur, 0 avertissement (77 180 octets).",
            "- *Compilation & Binaires* : 0 erreur, 0 avertissement (77 180 octets)." + v353_summary
        )
    with open(mem_path, "w", encoding="utf-8") as f:
        f.write(mem_content)
    print("Updated MEMOIRE_MAITRE_NOUVELLE_CONVERSATION.md")

    # 3. Update CHANGELOG_AND_HISTORY.md
    change_path = os.path.join(repo_root, "CHANGELOG_AND_HISTORY.md")
    with open(change_path, "r", encoding="utf-8") as f:
        change_content = f.read()

    v353_changelog = """

### 14.14 Version `v3.53` — Optimisation Quantitative du Panier Multi-Actifs & Calibrage des Lots (`10/11/2026`)

Suite à la confrontation du code v3.52 avec le scan quantitatif institutionnel sur 94 actifs Deriv (1 607 essais chaînés SHA-256), 3 ajustements majeurs ont été implémentés dans `SyncEffectiveParameters()` :

1. **Mise en Pause de `Volatility 10 Index`** :
   - Sur 3 944 trades historiques H1, V10 présente un gain net négatif de **-0.561 bps / trade** ($t = -1.693$, Quarter-Kelly $= 0.00\\%$).
   - L'actif est mis en pause via `ExtIsSymbolPaused = true` et `ExtEffRole = "V10_STD_PAUSED"`, bloquant tout trade préjudiciable.

2. **Réduction du Lot Cap sur `Volatility 15 (1s) Index`** :
   - Gain net modeste de **+0.052 bps** ($t = +0.048$) devenant déficitaire (-0.543 bps) en cas de friction accrue.
   - Son plafond passe de 0.500 lot à **0.050 lot** dans le code et dans le preset `QuantPod_v350_03_V15_1s_M30_Stabilizer.set`.

3. **Prise en Charge Bi-Timeframe (M30 / H1) pour `Volatility 25 (1s) Index`** :
   - En M30 avec Time-Stop à $H=8$ barres (équivalent à 4h), V25 produit **63.86 % de Win Rate** et **+3.424 bps / trade**.
   - `ExtEffTimeframe = (_Period == PERIOD_M30 ? PERIOD_M30 : PERIOD_H1);` et `ExtEffMaxHoldBars = (ExtEffTimeframe == PERIOD_M30 ? 8 : 4);`.

4. **Archivage & Compilation** :
   - v3.52 sauvegardée dans `archive/mql5_legacy/Deriv_VolSqueeze_Breakout_EA_v3_52.mq5` (55 782 octets).
   - Binaire v3.53 compilé avec `metaeditor64.exe` : **0 erreur, 0 avertissement** (76 808 octets).
   - 9/9 tests automatisés validés (`tests/verify_v353_basket_optimization.py`).
"""
    if "### 14.14 Version `v3.53`" not in change_content:
        change_content += v353_changelog
    with open(change_path, "w", encoding="utf-8") as f:
        f.write(change_content)
    print("Updated CHANGELOG_AND_HISTORY.md")

if __name__ == "__main__":
    update_docs_v353()
