# GUIDE OFFICIEL D'ENTRAÎNEMENT DU CERVEAU IA (GOOGLE COLAB)

Ce guide détaille la procédure complète pour ré-entraîner le réseau de neurones haute fréquence **boom_crash_meta_brain.onnx** (v7.00 Zero-Leakage) sur Google Colab avec accélération GPU ou TPU.

---

## 1. Fichiers Requis
Téléversez les fichiers suivants dans l'espace racine `/content` de Google Colab :
1. `boom_crash_10M_events.npz` : Le dataset haute fréquence (10 millions de ticks réels et 18 268 événements de spikes).
2. `train_boom_crash_l99_onnx.py` : Le script de vectorisation, normalisation intra-symbole, entraînement MLP et sérialisation ONNX autonome.
3. `real_live_spreads_mt5.json` : Table des spreads réels mesurés sur MetaTrader 5.

---

## 2. Lancement en 1 Commande dans Colab

Ouvrez une cellule de code Python dans votre notebook Colab et exécutez simplement :

```bash
!python3 train_boom_crash_l99_onnx.py --data boom_crash_10M_events.npz --epochs 25 --batch-size 1024
```

### Options Disponibles :
- `--data` : Chemin vers le fichier `.npz` (par défaut `boom_crash_10M_events.npz`).
- `--epochs` : Nombre d'époques d'apprentissage Adam (recommandé : 20 à 30).
- `--batch-size` : Taille des mini-lots (recommandé : 1024 ou 2048).
- `--lr` : Taux d'apprentissage initial (par défaut `0.001` avec décroissance cosine).
- `--output-onnx` : Nom du fichier binaire généré (par défaut `boom_crash_meta_brain.onnx`).

---

## 3. Sortie Générée
Une fois l'entraînement terminé avec succès, le script produit deux fichiers dans `/content` :
1. `boom_crash_meta_brain.onnx` (~50 Ko) : Le graphe computationnel ONNX optimisé pour MT5.
2. `onnx_model_metadata.json` : Les paramètres de centrage-réduction ($Z$-score) et le seuil de décision probabiliste $Q_{70}$.

Téléchargez ces deux fichiers et placez `boom_crash_meta_brain.onnx` dans le dossier MetaTrader 5 :  
`MQL5\Files\boom_crash_meta_brain.onnx`.
