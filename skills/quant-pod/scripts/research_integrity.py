"""
research_integrity.py
=====================
Cryptographie APPLIQUÉE À L'INTÉGRITÉ DE LA RECHERCHE (quant-pod v3).

Pourquoi : le Deflated Sharpe Ratio, le PBO et la calibration sous modèle nul ne valent
que si le nombre d'essais K est exact et si le holdout n'a jamais été vu. Un agent IA
(ou un humain) peut "oublier" des essais perdants ou re-découper les données.
Ce module rend ces fraudes DÉTECTABLES mathématiquement :

  1. HashChainLedger     : registre append-only chaîné par SHA-256 (comme une blockchain
                           sans consensus). Supprimer/modifier un essai casse la chaîne.
  2. commit / reveal     : pré-enregistrement d'hypothèse (schéma d'engagement
                           commit-reveal, H(salt || fiche)). Prouve que la règle de
                           falsification a été écrite AVANT de voir le résultat.
  3. data_manifest       : empreinte SHA-256 de chaque fichier de données + racine de
                           Merkle -> toute modification des données est détectée.
  4. derive_seed         : graines reproductibles dérivées par HMAC-SHA256
                           (projet, rôle, essai) -> simulations rejouables à l'identique.
  5. seal_holdout        : scellement du holdout (hash + horodatage dans la chaîne).

Dépendances : bibliothèque standard uniquement (hashlib, hmac, json, os, secrets).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Any, Dict, Iterable, List, Optional

GENESIS = "0" * 64


# ============================================================================
# Utilitaires
# ============================================================================
def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(path: str, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def canonical_json(obj: Any) -> bytes:
    """Sérialisation déterministe (clés triées, sans espaces) -> hash stable."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      default=str).encode("utf-8")


# ============================================================================
# 1. REGISTRE CHAÎNÉ (tamper-evident)
# ============================================================================
class HashChainLedger:
    """
    Chaque ligne JSONL contient : payload, prev_hash, hash = SHA256(prev_hash || canonical(payload)).
    verify() recalcule toute la chaîne : toute suppression, insertion ou modification
    d'une ligne passée est détectée (la ligne fautive est indiquée).
    """

    def __init__(self, path: str):
        self.path = path
        d = os.path.dirname(os.path.abspath(path))
        os.makedirs(d, exist_ok=True)
        if not os.path.exists(path):
            open(path, "a", encoding="utf-8").close()

    def _rows(self) -> List[dict]:
        out = []
        with open(self.path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    out.append(json.loads(line))
        return out

    def head(self) -> str:
        rows = self._rows()
        for r in reversed(rows):
            if "hash" in r:
                return r["hash"]
        return GENESIS

    def append(self, payload: Dict[str, Any]) -> str:
        prev = self.head()
        body = dict(payload)
        body.setdefault("ts", time.strftime("%Y-%m-%dT%H:%M:%S"))
        digest = sha256_bytes(prev.encode() + canonical_json(body))
        row = {"payload": body, "prev_hash": prev, "hash": digest}
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
        return digest

    def payloads(self) -> List[dict]:
        return [r["payload"] for r in self._rows() if "payload" in r]

    def verify(self) -> Dict[str, Any]:
        prev = GENESIS
        rows = self._rows()
        n_chained = 0
        for i, r in enumerate(rows):
            if "payload" not in r:          # ligne héritée (ancien format) : signalée
                return {"ok": False, "n_rows": len(rows), "broken_at": i,
                        "reason": "ligne non chaînée (format hérité ou insertion manuelle)"}
            if r.get("prev_hash") != prev:
                return {"ok": False, "n_rows": len(rows), "broken_at": i,
                        "reason": "prev_hash incohérent (ligne supprimée/insérée/réordonnée)"}
            expect = sha256_bytes(prev.encode() + canonical_json(r["payload"]))
            if expect != r.get("hash"):
                return {"ok": False, "n_rows": len(rows), "broken_at": i,
                        "reason": "contenu modifié après écriture"}
            prev = r["hash"]
            n_chained += 1
        return {"ok": True, "n_rows": len(rows), "n_chained": n_chained, "head": prev}


# ============================================================================
# 2. PRÉ-ENREGISTREMENT COMMIT / REVEAL
# ============================================================================
def commit_hypothesis(card_text: str, ledger: Optional[HashChainLedger] = None,
                      hypothesis_id: str = "") -> Dict[str, str]:
    """
    Engagement cryptographique : c = SHA256(salt || card). On publie c (dans le ledger),
    on garde (salt, card). Masquant (salt aléatoire 256 bits) et liant (résistance
    aux collisions de SHA-256) : impossible de changer la fiche après coup.
    """
    salt = secrets.token_hex(32)
    c = sha256_bytes(bytes.fromhex(salt) + card_text.encode("utf-8"))
    if ledger is not None:
        ledger.append({"type": "hypothesis_commit", "hypothesis_id": hypothesis_id, "commitment": c})
    return {"commitment": c, "salt": salt}


def reveal_verify(card_text: str, salt: str, commitment: str) -> bool:
    return hmac.compare_digest(
        sha256_bytes(bytes.fromhex(salt) + card_text.encode("utf-8")), commitment)


# ============================================================================
# 3. MANIFESTE DE DONNÉES + RACINE DE MERKLE
# ============================================================================
def merkle_root(leaf_hashes: Iterable[str]) -> str:
    level = [bytes.fromhex(h) for h in leaf_hashes]
    if not level:
        return GENESIS
    while len(level) > 1:
        if len(level) % 2 == 1:
            level.append(level[-1])
        level = [hashlib.sha256(level[i] + level[i + 1]).digest() for i in range(0, len(level), 2)]
    return level[0].hex()


def data_manifest(paths: Iterable[str]) -> Dict[str, Any]:
    """Empreinte de chaque fichier (triés) + racine de Merkle = identifiant unique du jeu de données."""
    files = sorted(os.path.abspath(p) for p in paths)
    leaves = []
    entries = []
    for p in files:
        h = sha256_file(p)
        leaves.append(h)
        entries.append({"file": p, "sha256": h, "bytes": os.path.getsize(p)})
    return {"n_files": len(files), "merkle_root": merkle_root(leaves), "files": entries}


def verify_manifest(manifest: Dict[str, Any]) -> Dict[str, Any]:
    changed = [e["file"] for e in manifest["files"]
               if not os.path.exists(e["file"]) or sha256_file(e["file"]) != e["sha256"]]
    return {"ok": not changed, "changed_or_missing": changed}


# ============================================================================
# 4. GRAINES REPRODUCTIBLES (HMAC-SHA256)
# ============================================================================
def derive_seed(project_key: str, *labels: Any) -> int:
    """seed = HMAC-SHA256(project_key, 'label1|label2|...') tronqué à 63 bits (numpy-compatible)."""
    msg = "|".join(str(x) for x in labels).encode("utf-8")
    d = hmac.new(project_key.encode("utf-8"), msg, hashlib.sha256).digest()
    return int.from_bytes(d[:8], "big") & ((1 << 63) - 1)


# ============================================================================
# 5. SCELLEMENT DU HOLDOUT
# ============================================================================
def seal_holdout(ledger: HashChainLedger, file_path: str) -> str:
    h = sha256_file(file_path)
    ledger.append({"type": "holdout_sealed", "file": os.path.abspath(file_path), "sha256": h})
    return h


def holdout_status(ledger: HashChainLedger, file_path: str) -> Dict[str, Any]:
    fp = os.path.abspath(file_path)
    pl = ledger.payloads()
    sealed = [p for p in pl if p.get("type") in ("holdout_sealed", "holdout_registered") and p.get("file") == fp]
    opened = [p for p in pl if p.get("type") == "holdout_opened" and p.get("file") == fp]
    intact = bool(sealed) and os.path.exists(fp) and sha256_file(fp) == sealed[-1]["sha256"]
    return {"sealed": bool(sealed), "opened_count": len(opened), "file_intact": intact}


if __name__ == "__main__":
    import tempfile

    tmp = tempfile.mkdtemp()
    led = HashChainLedger(os.path.join(tmp, "ledger.jsonl"))
    for k in range(5):
        led.append({"type": "trial", "hypothesis_id": f"H{k}", "sr_per_period": 0.01 * k})
    v = led.verify()
    assert v["ok"] and v["n_chained"] == 5, v
    # Fraude : supprimer l'essai n°2 (perdant) -> doit être détecté
    with open(led.path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    with open(led.path, "w", encoding="utf-8") as f:
        f.writelines(lines[:2] + lines[3:])
    v2 = led.verify()
    assert not v2["ok"] and v2["broken_at"] == 2, v2
    # Commit / reveal
    card = "H001: mean-reversion OU, rejet si t_net < 2 après coûts x2"
    cm = commit_hypothesis(card)
    assert reveal_verify(card, cm["salt"], cm["commitment"])
    assert not reveal_verify(card + " (modifié)", cm["salt"], cm["commitment"])
    # Merkle + manifest
    p1 = os.path.join(tmp, "a.csv"); open(p1, "w").write("1,2,3\n")
    p2 = os.path.join(tmp, "b.csv"); open(p2, "w").write("4,5,6\n")
    man = data_manifest([p1, p2])
    assert verify_manifest(man)["ok"]
    open(p2, "a").write("7\n")
    assert not verify_manifest(man)["ok"]
    # Graines déterministes
    assert derive_seed("k", "null", 3) == derive_seed("k", "null", 3) != derive_seed("k", "null", 4)
    print("research_integrity : 6/6 auto-tests OK (chaîne, fraude détectée, commit-reveal, Merkle, seeds)")
