import os

def update_docs():
    repo_root = r"C:\Users\CHRIST\Desktop\IA\ANTIGRAVITY\projets\general project   quant bot deriv"

    # 1. Update AGENT.md
    agent_path = os.path.join(repo_root, "AGENT.md")
    with open(agent_path, "r", encoding="utf-8") as f:
        agent_content = f.read()
    agent_content = agent_content.replace(
        "| `v3.51 Surgical Patch (Lookback Shift & Profit Lock)` | **ACTIF EN PRODUCTION (Omni-Basket S1/S2/S3 & Dashboard Rétractable MQL5)** |",
        "| `v3.52 Direction Fix (S1 Direction Bug Solved)` | **ACTIF EN PRODUCTION (Omni-Basket S1/S2/S3 & Dashboard Rétractable MQL5)** |"
    )
    agent_content = agent_content.replace(
        "• **Correctifs v3.50 & v3.51** : Télémétrie continue, correctif chirurgical v3.51 du Lookback Shift (`ExtLastStd20 = rolling_std[1]` et quantile pré-cassure sans contamination), statut Profit Lock live exact (`is_profit_locked = cur_sl > open_px`), garde marge `OrderCalcMargin`, filtre direction.",
        "• **Correctifs v3.50, v3.51 & v3.52** : Télémétrie continue, correctif chirurgical Lookback Shift (`ExtLastStd20 = rolling_std[1]`), statut Profit Lock exact, correctif critique v3.52 du sens BUY/SELL (`ExtLastRetBps = r_bps[0]` éliminant l'inversion d'indexation MQL5), garde marge `OrderCalcMargin`, filtre direction."
    )
    with open(agent_path, "w", encoding="utf-8") as f:
        f.write(agent_content)
    print("Updated AGENT.md")

    # 2. Update MEMOIRE_MAITRE_NOUVELLE_CONVERSATION.md
    mem_path = os.path.join(repo_root, "MEMOIRE_MAITRE_NOUVELLE_CONVERSATION.md")
    with open(mem_path, "r", encoding="utf-8") as f:
        mem_content = f.read()
    mem_content = mem_content.replace(
        "Date de dernière mise à jour certifiée** : 10 Novembre 2026 (12:05 UTC — Version `v3.51 Surgical Patch` déployée live)",
        "Date de dernière mise à jour certifiée** : 10 Novembre 2026 (13:15 UTC — Version `v3.52 Direction Fix` déployée live)"
    )
    v352_summary = """
* **Patch Critique v3.52 (Correction Inversion BUY/SELL sur S1)** :
  - *Cause du bug* : Un tableau local `double last_closes[2];` non indexé comme série (`AsSeries=false` par défaut en MQL5) recevait `last_closes[0] = Close[2]` et `last_closes[1] = Close[1]`, inversant le calcul du rendement (`Close[2] - Close[1]`) et déclenchant des BUY sur cassure baissière et SELL sur cassure haussière.
  - *Correctif v3.52 certifié* : Déclaration de `ExtLastRetBps` dans la télémétrie globale, affectation directe de `ExtLastRetBps = r_bps[0];` dans `UpdateMarketTelemetry()` (où `closes` est déjà strictement indexé en série), et utilisation directe de `ExtLastRetBps` dans `OnTick()`. Direction BUY/SELL 100% alignée avec le mouvement du marché.
  - *Clôture du trade inversé #8825110205* : Clôturé immédiatement et proprement via API FOK avec une variation négligeable (-1.52 USD).
  - *Compilation & Binaires* : 0 erreur, 0 avertissement (77 180 octets).
"""
    if "* **Patch Critique v3.52" not in mem_content:
        mem_content = mem_content.replace(
            "* **Compilation MetaEditor 64** : 0 erreur, 0 avertissement (76 286 octets).",
            "* **Compilation MetaEditor 64** : 0 erreur, 0 avertissement (76 286 octets)." + v352_summary
        )
    with open(mem_path, "w", encoding="utf-8") as f:
        f.write(mem_content)
    print("Updated MEMOIRE_MAITRE_NOUVELLE_CONVERSATION.md")

    # 3. Update CHANGELOG_AND_HISTORY.md
    change_path = os.path.join(repo_root, "CHANGELOG_AND_HISTORY.md")
    with open(change_path, "r", encoding="utf-8") as f:
        change_content = f.read()

    v352_changelog = """

### 14.13 Patch Critique `v3.52` — Correction de l'Inversion de Direction BUY/SELL sur le Moteur S1 (`10/11/2026`)

Lors de l'audit forensique approfondi du code v3.51 par rapport au trade live `#8825110205` sur `Volatility 5 (1s) Index`, un bug critique d'indexation MQL5 a été identifié et corrigé :

1. **Mécanisme du Bug Inversé (Lignes 707-710 / 1110-1115 de la v3.51)** :
   - Dans `OnTick()`, la direction était évaluée par :
     ```mql5
     double r_bps_last = 0.0;
     double last_closes[2];
     if(CopyClose(_Symbol, ExtEffTimeframe, 1, 2, last_closes) == 2 && last_closes[1] > 0.0)
        r_bps_last = (last_closes[0] - last_closes[1]) / last_closes[1] * 10000.0;
     ```
   - En MQL5 natif, un tableau non déclaré via `ArraySetAsSeries(arr, true)` stocke par défaut les barres dans l'ordre chronologique croissant : `last_closes[0]` contenait `Close[shift=2]` (la bougie précédente) et `last_closes[1]` contenait `Close[shift=1]` (la bougie de cassure).
   - Par conséquent, `last_closes[0] - last_closes[1]` calculait `Close[2] - Close[1]`, soit l'exact opposé du rendement de la cassure ! Une cassure baissière devenait un signal BUY, et une cassure haussière devenait un signal SELL.

2. **Résolution Chirurgicale v3.52** :
   - Déclaration d'une variable globale de télémétrie : `double ExtLastRetBps = 0.0;`.
   - Dans `UpdateMarketTelemetry()`, où `closes` est déjà configuré en série (`ArraySetAsSeries(closes, true)`), affectation directe :
     `ExtLastRetBps = r_bps[0]; // (closes[0] - closes[1]) / closes[1] * 10000.0 (Close[1] - Close[2])`
   - Dans `OnTick()`, suppression de l'appel redondant et buggy à `CopyClose()`, et utilisation directe :
     `double r_bps_last = ExtLastRetBps;`
   - Lorsque la bougie casse à la hausse (`Close[1] > Close[2]`), `r_bps_last > 0` $\implies$ BUY (`direction = 1.0`).
   - Lorsque la bougie casse à la baisse (`Close[1] < Close[2]`), `r_bps_last < 0` $\implies$ SELL (`direction = -1.0`).

3. **Mesures Immédiates sur les Trades Live** :
   - Le ticket `#8825110205` ouvert à l'envers sur `Volatility 5 (1s)` a été clôturé proprement via l'API MT5 à `95900.94` (Deal `#8703597418`) avec un impact minime de seulement `-1.52 USD` (-0.016% du compte).
   - Le capital de trading (`9 026.06 USD`) est totalement préservé et le bot est prêt pour les prochains signaux directionnels parfaits.

4. **Archivage & Compilation** :
   - Sauvegarde de la v3.51 dans [`archive/mql5_legacy/Deriv_VolSqueeze_Breakout_EA_v3_51.mq5`](archive/mql5_legacy/Deriv_VolSqueeze_Breakout_EA_v3_51.mq5) (`55 670` octets).
   - Compilation MetaEditor 64 : **0 erreur, 0 avertissement** (`77 180` octets).
   - Suite de tests [`tests/verify_v352_direction_fix.py`](tests/verify_v352_direction_fix.py) validée à 100 % (7/7 tests).
"""
    if "### 14.13 Patch Critique `v3.52`" not in change_content:
        change_content += v352_changelog
    with open(change_path, "w", encoding="utf-8") as f:
        f.write(change_content)
    print("Updated CHANGELOG_AND_HISTORY.md")

    # 4. Generate DOSSIER_COMPLET_BOT_QUANT_v352.md on Desktop
    desktop_dossier_script = os.path.join(repo_root, "scripts", "generate_desktop_dossier.py")
    with open(desktop_dossier_script, "r", encoding="utf-8") as f:
        dossier_code = f.read()
    dossier_code = dossier_code.replace("v351", "v352").replace("v3.51", "v3.52")
    with open(desktop_dossier_script, "w", encoding="utf-8") as f:
        f.write(dossier_code)
    
if __name__ == "__main__":
    update_docs()
