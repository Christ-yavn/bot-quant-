# 🧠 Registre Historique des Modèles IA ONNX (`archive/models_legacy/`)

Ce dossier conserve toutes les versions antérieures des réseaux de neurones et modèles ONNX utilisés au fil de l'évolution des robots MetaTrader 5, afin de garantir une traçabilité scientifique et historique complète sur GitHub tout en gardant le dossier `MQL5\Files` local de MetaTrader 5 strictement propre.

---

## 📋 Tableau de Correspondance : Modèles ONNX $\leftrightarrow$ Versions des Bots

| Fichier ONNX | Taille | Date d'Création | Bot MQL5 Associé | Architecture & Features | Statut & Raison de l'Archivage |
|---|---:|---|---|---|---|
| [`boom_crash_meta_brain_v2_50kb_20261018.onnx`](boom_crash_meta_brain_v2_50kb_20261018.onnx) | `50 986 o` | 18/10/2026 | [`DerivBoomCrashHFT_v6.mq5`](../../src/mql5/DerivBoomCrashHFT_v6.mq5) | MLP / Gradient Boosting 14 features (survie de dérive calme v6) | **Archivé** (copie initiale présente dans `MQL5\Experts`). |
| [`boom_crash_meta_brain_v1_49kb_20261019.onnx`](boom_crash_meta_brain_v1_49kb_20261019.onnx) | `49 773 o` | 19/10/2026 | [`DerivBoomCrashHFT_v7.mq5`](../../src/mql5/DerivBoomCrashHFT_v7.mq5) | Modèle intermédiaire 14 features calibré lors du passage v6 $\rightarrow$ v7 | **Archivé** (remplacé par la version finale accompagnée de `onnx_model_metadata.json`). |
| [`c2_vol_filter_v1_unaligned_20261021.onnx`](c2_vol_filter_v1_unaligned_20261021.onnx) | `20 294 o` | 21/10/2026 | [`Deriv_VolSqueeze_Breakout_EA_v3.mq5` (v3.00)](../../src/mql5/Deriv_VolSqueeze_Breakout_EA_v3.mq5) | Gradient Boosting 7 features (entraîné avant correction du désalignement Python/MQL5 et du spread 2026) | **Archivé suite à l'Audit du 25/10/2026** (remplacé en production par [`src/models/c2_vol_filter.onnx`](../../src/models/c2_vol_filter.onnx) réaligné sur les 7 features exactes et entraîné en split chronologique strict 60/20/20 sur 56 046 bougies H1). |

---

## ✅ Modèles Actifs en Production (`src/models/` et `MQL5\Files\`)

1. **[`src/models/boom_crash_meta_brain.onnx`](../../src/models/boom_crash_meta_brain.onnx)** (`50 986 octets`) + **[`src/models/onnx_model_metadata.json`](../../src/models/onnx_model_metadata.json)** :
   - **Bot associé :** [`DerivBoomCrashHFT_v830_Ultimate.mq5`](../../src/mql5/DerivBoomCrashHFT_v830_Ultimate.mq5) (corrigé B1–B9).
   - **Entrée :** Tensor `float32 [1, 14]` strictement aligné sur les 14 features de `onnx_model_metadata.json` (`InpUseZeroCheatFeatures = false`).
   - **Sortie :** Probabilité de survie convertie sur l'horizon $M^* = 60$ ticks via $P_{\text{spike}}(M^*) = 1 - P_{\text{surv}}^{M^* / (\text{be\_ticks} + 15)}$.

2. **[`src/models/c2_vol_filter.onnx`](../../src/models/c2_vol_filter.onnx)** (`12 967 octets`) + **[`src/models/c2_vol_filter_metadata.json`](../../src/models/c2_vol_filter_metadata.json)** :
   - **Bot associé :** [`Deriv_VolSqueeze_Breakout_EA_v3.mq5`](../../src/mql5/Deriv_VolSqueeze_Breakout_EA_v3.mq5) (`v3.10`).
   - **Entrée :** Tensor `float32 [1, 7]` strictement aligné entre Python et MQL5 : `[vol_ratio, impulse_z, direction, levy_area, spread_to_atr, skew20, kurt20]`.
   - **Protocole :** Split chronologique 60 % Train / 20 % Validation / 20 % Out-Of-Sample sur 56 046 barres H1 (2020–2026) sans fuite du spread futur.
