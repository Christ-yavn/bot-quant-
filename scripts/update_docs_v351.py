import os

def update_docs():
    # 1. Update AGENT.md
    agent_file = os.path.abspath("AGENT.md")
    with open(agent_file, "r", encoding="utf-8") as f:
        agent_content = f.read()
    
    agent_content = agent_content.replace(
        "| `v3.50 Omni-Basket & Retractable UI` | **ACTIF EN PRODUCTION (Omni-Basket S1/S2/S3 & Dashboard Rétractable MQL5)** |",
        "| `v3.51 Surgical Patch (Lookback Shift & Profit Lock)` | **ACTIF EN PRODUCTION (Omni-Basket S1/S2/S3 & Dashboard Rétractable MQL5)** |"
    )
    agent_content = agent_content.replace(
        "• **4 Bugs v3.40 Corrigés** : Télémétrie temps réel continue (zéro 0.00 bps), Lookback Shift Bug (`rolling_std[1]`), garde marge `OrderCalcMargin`, filtre de direction (`InpDirectionMode`).",
        "• **Correctifs v3.50 & v3.51** : Télémétrie continue, correctif chirurgical v3.51 du Lookback Shift (`ExtLastStd20 = rolling_std[1]` et quantile pré-cassure sans contamination), statut Profit Lock live exact (`is_profit_locked = cur_sl > open_px`), garde marge `OrderCalcMargin`, filtre direction."
    )
    with open(agent_file, "w", encoding="utf-8") as f:
        f.write(agent_content)
    print("Updated AGENT.md")

    # 2. Update MEMOIRE_MAITRE_NOUVELLE_CONVERSATION.md
    memoire_file = os.path.abspath("MEMOIRE_MAITRE_NOUVELLE_CONVERSATION.md")
    with open(memoire_file, "r", encoding="utf-8") as f:
        mem_content = f.read()

    mem_content = mem_content.replace(
        "Date de dernière mise à jour certifiée** : 10 Novembre 2026 (09:20 UTC — Version `v3.50 Omni-Basket & Retractable UI` déployée live)",
        "Date de dernière mise à jour certifiée** : 10 Novembre 2026 (12:05 UTC — Version `v3.51 Surgical Patch` déployée live)"
    )
    
    v351_summary_block = """
### 3.3. DÉPLOIEMENT & VALIDATION CHIRURGICALE v3.51 (`10/11/2026`)
* **Archivage Immuable (Loi N°2)** : `archive/mql5_legacy/Deriv_VolSqueeze_Breakout_EA_v3_50.mq5` (53 583 octets) et `Deriv_VolSqueeze_Breakout_EA_v3_50.ex5` (76 248 octets).
* **Résolution des 2 Bugs Subtils Signalés lors de l'Audit L99** :
  1. *Bug Subtil A (Lookback Shift Contamination)* : `ExtLastStd20 = pre_breakout_std20;` (`rolling_std[1]`) et le quantile `squeeze_threshold` est calculé strictement sur les $M-1$ fenêtres passées (`rolling_std[1]` à `rolling_std[q_count]`), éliminant toute contamination par la bougie d'impulsion.
  2. *Bug Subtil B (Faux Positif Profit Lock)* : `is_profit_locked = (cur_sl > open_px)` pour BUY et `(cur_sl > 0.0 && cur_sl < open_px)` pour SELL. Le dashboard affiche rigoureusement `"ARMÉ (Seuil +1.20 ATR)"` tant que le seuil n'est pas franchi, puis `"VERROUILLÉ (+0.20 ATR)"`.
* **Cycle de Vie des Positions Live (10/11/2026)** :
  - **Ticket #8824875983** (`Volatility 25 (1s) Index`, SELL `0.011 lot`, ouvert à 07:46:49) : Clôturé automatiquement par le Time-Stop après 4 barres H1 exactes (`Bars Held = 4/4`) à 11:42:39 (Deal `#8703508901`).
  - **Ticket #8825110205** (`Volatility 5 (1s) Index, M30`, BUY `0.200 lot`) : Déclenché automatiquement à 12:00:00 sur impulsion post-compression ($Z=1.32 \ge 1.25$, $\sigma_{20} = 3.43\text{ bps} \le Q_{30}$), avec Hard SL à `95765.26` et Hard TP à `96133.88` (actuellement en cours de gestion en direct).
* **Compilation MetaEditor 64** : 0 erreur, 0 avertissement (76 286 octets).
"""
    if "### 3.3. DÉPLOIEMENT & VALIDATION CHIRURGICALE v3.51" not in mem_content:
        mem_content = mem_content.replace(
            "## 4. PISTES D'AMÉLIORATION & NOUVEAUX HORIZONS DE RECHERCHE DERIV",
            v351_summary_block + "\n---\n\n## 4. PISTES D'AMÉLIORATION & NOUVEAUX HORIZONS DE RECHERCHE DERIV"
        )
    with open(memoire_file, "w", encoding="utf-8") as f:
        f.write(mem_content)
    print("Updated MEMOIRE_MAITRE_NOUVELLE_CONVERSATION.md")

    # 3. Update CHANGELOG_AND_HISTORY.md
    changelog_file = os.path.abspath("CHANGELOG_AND_HISTORY.md")
    with open(changelog_file, "r", encoding="utf-8") as f:
        change_content = f.read()

    v351_changelog_section = """

### 14.12 Patch Chirurgical `v3.51` — Correction du Lookback Shift et Détection Précise du Profit Lock (`10/11/2026`)

À la suite de l'audit forensique approfondi de la version `v3.50`, deux subtilités logiques ont été corrigées avec une précision chirurgicale dans la version **`v3.51`** :

1. **Archivage Immuable (Loi N°2 quant-pod-deriv)** :
   - Sauvegarde préalable de la v3.50 intacte dans [`archive/mql5_legacy/Deriv_VolSqueeze_Breakout_EA_v3_50.mq5`](archive/mql5_legacy/Deriv_VolSqueeze_Breakout_EA_v3_50.mq5) (`53 583` octets) et [`archive/mql5_legacy/Deriv_VolSqueeze_Breakout_EA_v3_50.ex5`](archive/mql5_legacy/Deriv_VolSqueeze_Breakout_EA_v3_50.ex5) (`76 248` octets).

2. **Résolution du Bug Subtil A (Lookback Shift Contamination)** :
   - *Cause dans v3.50* : `UpdateMarketTelemetry()` calculait bien `pre_breakout_std20 = rolling_std[1]`, mais affectait ensuite `ExtLastStd20 = current_std20;` (`rolling_std[0]`), et incluait `rolling_std[0]` dans le tri du quantile `sorted_std`.
   - *Correctif dans v3.51* : 
     - Calcul du quantile strictement sur les $M-1$ fenêtres antérieures (`rolling_std[1]` à `rolling_std[q_count]`), excluant formellement la barre de cassure.
     - Affectation exacte `ExtLastStd20 = pre_breakout_std20;` (`rolling_std[1]`). La condition de squeeze dans `OnTick()` (`bool is_squeezed = ExtLastStd20 <= ExtLastSqueezeQ;`) compare désormais des grandeurs homogènes et pures, éliminant toute auto-annulation.

3. **Résolution du Bug Subtil B (Faux Positif du Profit Lock sur le Dashboard)** :
   - *Cause dans v3.50* : Le dashboard testait `(ExtPosition.StopLoss() > 0.0) ? "VERROUILLÉ" : "ACTIF"`. Comme le Hard Stop-Loss initial ($-2.50\times\text{ATR}$) est posé dès la milliseconde 0, `StopLoss() > 0.0` était systématiquement vrai, affichant `"VERROUILLÉ"` prématurément.
   - *Correctif dans v3.51* : Vérification dynamique de la position par rapport au prix d'ouverture :
     ```mql5
     double cur_sl = ExtPosition.StopLoss();
     double open_px = ExtPosition.PriceOpen();
     bool is_profit_locked = (ExtPosition.PositionType() == POSITION_TYPE_BUY) ? (cur_sl > open_px) : (cur_sl > 0.0 && cur_sl < open_px);
     pos_lock_str = is_profit_locked ? "VERROUILLÉ (+0.20 ATR)" : "ARMÉ (Seuil +1.20 ATR)";
     ```

4. **Cycle de Vie du Trade Live #8824875983 & Exécution du Trade #8825110205** :
   - Le trade vendeur sur `Volatility 25 (1s) Index` ouvert à `07:46:49` a été clôturé à `11:42:39` par le Time-Stop automatique après exactement 4 barres H1 (`Bars Held = 4/4`), conformément au plan mathématique.
   - À `12:00:00`, la barre M30 sur `Volatility 5 (1s) Index` a déclenché une nouvelle entrée BUY automatique (`Ticket #8825110205`, lot 0.200, Hard SL à `95765.26`, Hard TP à `96133.88`), immédiatement prise en charge et monitorée par le dashboard rétractable.

5. **Compilation & Vérification 100% Validée** :
   - Compilateur `metaeditor64.exe` : **0 erreur, 0 avertissement** (`76 286` octets).
   - Suite de vérification [`tests/verify_v351_surgical_patch.py`](tests/verify_v351_surgical_patch.py) validée avec succès sur les 6 tests.
"""
    if "### 14.12 Patch Chirurgical `v3.51`" not in change_content:
        change_content += v351_changelog_section
    with open(changelog_file, "w", encoding="utf-8") as f:
        f.write(change_content)
    print("Updated CHANGELOG_AND_HISTORY.md")

if __name__ == "__main__":
    update_docs()
