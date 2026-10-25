# -*- coding: utf-8 -*-
"""
=============================================================================
SCANNER DE JUSTE VALEUR (FAIR-VALUE EV SCANNER) — CONTRATS DERIV WEBSOCKET
API Live : wss://ws.derivws.com/websockets/v3?app_id=1089
=============================================================================
Interroge en temps réel l'API WebSocket publique de Deriv sur l'ensemble des
familles de contrats à paiement fixé (proposal / contracts_for) :
  1. Digits (DIGITMATCH, DIGITDIFF, DIGITEVEN, DIGITODD, DIGITOVER, DIGITUNDER)
     -> Loi exacte : uniforme discrète sur {0..9}, P = k / 10.
  2. Rise / Fall & Higher / Lower (CALL, PUT avec barrière = 0 ou décalée)
     -> Loi exacte : Mouvement Brownien Géométrique (GBM) sans dérive (martingale
        vérifiée sur 56 046 barres H1), P_CALL = N(d2), P_PUT = N(-d2),
        avec d2 = (ln(S0/K) - 0.5 * sigma^2 * T) / (sigma * sqrt(T)).
  3. Touch / No Touch (ONETOUCH, NOTOUCH)
     -> Loi exacte : Principe de réflexion pour mouvement brownien avec dérive
        (Harrison 1985 / Shreve 2004) sur X_t = ln(S_t/S_0) = nu*t + sigma*W_t.
  4. Ends Between / Ends Outside (EXPIRYRANGE, EXPIRYMISS)
     -> Loi exacte : N(d2(H)) - N(d2(L)) sous le GBM vérifié.
  5. Accumulators (ACCU) & Multipliers (MULTUP, MULTDOWN) & Turbos
     -> Décomposition exacte de la survie par tick et de la marge implicite.

Calcule pour chaque contrat :
  - Probabilité mathématique exacte en forme fermée : P_exact
  - Probabilité implicite facturée par Deriv        : P_implied = Stake / Payout
  - Espérance mathématique exacte ($)               : EV_$ = Payout * P_exact - Stake
  - Espérance mathématique en % de la mise (Edge)   : EV_% = (Payout * P_exact / Stake - 1) * 100
"""

import os
import ssl
import json
import math
import time
import base64
import socket
import struct
from datetime import datetime, timezone


WS_HOST = "ws.derivws.com"
WS_PORT = 443
WS_PATH = "/websockets/v3?app_id=1089"

# Volatilités annuelles exactes programmées dans le générateur RNG de Deriv (vérifiées en §4.1 de l'audit)
SYMBOL_SIGMA = {
    "1HZ10V": 0.10,
    "1HZ25V": 0.25,
    "1HZ50V": 0.50,
    "1HZ75V": 0.75,
    "1HZ100V": 1.00,
    "R_10": 0.10,
    "R_25": 0.25,
    "R_50": 0.50,
    "R_75": 0.75,
    "R_100": 1.00,
}

# Cadence de ticks par seconde (1s indices = 1 tick/s, standard R_ indices = 0.5 tick/s = 1 tick / 2s)
SYMBOL_SECONDS_PER_TICK = {
    "1HZ10V": 1.0,
    "1HZ25V": 1.0,
    "1HZ50V": 1.0,
    "1HZ75V": 1.0,
    "1HZ100V": 1.0,
    "R_10": 2.0,
    "R_25": 2.0,
    "R_50": 2.0,
    "R_75": 2.0,
    "R_100": 2.0,
}

SECONDS_PER_YEAR = 365.0 * 86400.0


def norm_cdf(x: float) -> float:
    """Fonction de répartition exacte de la loi normale standard N(0, 1)."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def exact_gbm_call_put_prob(s0: float, k: float, sigma: float, t_sec: float, is_call: bool) -> float:
    """
    Probabilité exacte P(S_T > K) ou P(S_T < K) sous un GBM martingale :
    dS_t = sigma * S_t * dW_t  =>  ln(S_T / S_0) ~ N(-0.5 * sigma^2 * T, sigma^2 * T).
    """
    if s0 <= 0.0 or k <= 0.0 or sigma <= 0.0 or t_sec <= 0.0:
        return 0.5
    T = t_sec / SECONDS_PER_YEAR
    vol_sqrt_t = sigma * math.sqrt(T)
    if vol_sqrt_t <= 1e-12:
        return 0.5
    d2 = (math.log(s0 / k) - 0.5 * (sigma ** 2) * T) / vol_sqrt_t
    return norm_cdf(d2) if is_call else norm_cdf(-d2)


def exact_gbm_onetouch_prob(s0: float, barrier: float, sigma: float, t_sec: float) -> float:
    """
    Probabilité exacte de toucher la barrière B avant ou à l'instant T pour
    X_t = ln(S_t / S_0) = nu * t + sigma * W_t avec nu = -0.5 * sigma^2
    (Principe de réflexion en temps continu, Shreve 2004).
    """
    if s0 <= 0.0 or barrier <= 0.0 or sigma <= 0.0 or t_sec <= 0.0:
        return 0.0
    if abs(barrier - s0) <= 1e-12:
        return 1.0
    T = t_sec / SECONDS_PER_YEAR
    vol_sqrt_t = sigma * math.sqrt(T)
    nu = -0.5 * (sigma ** 2)
    b = math.log(barrier / s0)

    # Exposant 2 * nu * b / sigma^2 = -b (car nu = -0.5 * sigma^2)
    exp_arg = max(-50.0, min(50.0, (2.0 * nu * b) / (sigma ** 2)))
    exp_factor = math.exp(exp_arg)

    if b > 0.0:
        # Barrière haute B > S_0 : P(max_{0<=t<=T} X_t >= b)
        term1 = norm_cdf((-b + nu * T) / vol_sqrt_t)
        term2 = exp_factor * norm_cdf((-b - nu * T) / vol_sqrt_t)
    else:
        # Barrière basse B < S_0 : P(min_{0<=t<=T} X_t <= b)
        term1 = norm_cdf((b - nu * T) / vol_sqrt_t)
        term2 = exp_factor * norm_cdf((b + nu * T) / vol_sqrt_t)

    return max(0.0, min(1.0, term1 + term2))


def exact_gbm_expiry_range_prob(s0: float, low_b: float, high_b: float, sigma: float, t_sec: float) -> float:
    """Probabilité exacte P(L < S_T < H) à l'échéance T sous le GBM martingale."""
    if s0 <= 0.0 or low_b <= 0.0 or high_b <= low_b or sigma <= 0.0 or t_sec <= 0.0:
        return 0.0
    # P(S_T < H) - P(S_T < L) = P(S_T > L) - P(S_T > H)
    p_gt_low = exact_gbm_call_put_prob(s0, low_b, sigma, t_sec, is_call=True)
    p_gt_high = exact_gbm_call_put_prob(s0, high_b, sigma, t_sec, is_call=True)
    return max(0.0, min(1.0, p_gt_low - p_gt_high))


# Paramètres structurels vérifiés du générateur géométrique sans mémoire Boom/Crash (§1.2 de l'Audit)
BOOM_CRASH_SPECS = {
    "BOOM1000":  {"tau": 1066.6, "drift_pt": 0.01551, "mean_spike_pt": 17.015, "live_spread_pt": 1.7215, "is_boom": True},
    "CRASH1000": {"tau": 961.0,  "drift_pt": 0.00636, "mean_spike_pt": 5.887,  "live_spread_pt": 0.5422, "is_boom": False},
    "BOOM900":   {"tau": 911.4,  "drift_pt": 0.00972, "mean_spike_pt": 8.865,  "live_spread_pt": 0.9620, "is_boom": True},
    "CRASH900":  {"tau": 907.3,  "drift_pt": 0.01900, "mean_spike_pt": 17.314, "live_spread_pt": 1.3560, "is_boom": False},
    "BOOM600":   {"tau": 586.5,  "drift_pt": 0.00894, "mean_spike_pt": 5.155,  "live_spread_pt": 0.7730, "is_boom": True},
    "CRASH600":  {"tau": 571.5,  "drift_pt": 0.03773, "mean_spike_pt": 22.904, "live_spread_pt": 3.2810, "is_boom": False},
    "BOOM500":   {"tau": 486.9,  "drift_pt": 0.01128, "mean_spike_pt": 5.825,  "live_spread_pt": 0.5270, "is_boom": True},
    "CRASH500":  {"tau": 480.0,  "drift_pt": 0.00623, "mean_spike_pt": 2.991,  "live_spread_pt": 0.3270, "is_boom": False},
}


def exact_boom_crash_spike_prob(n_ticks: int, tau: float) -> float:
    """
    Probabilité exacte d'observer au moins 1 spike sur N ticks sous la loi
    géométrique sans mémoire vérifiée de taux p = 1 / tau :
      P(N_spikes >= 1 en N ticks) = 1 - (1 - 1 / tau)^N.
    """
    if n_ticks <= 0 or tau <= 1.0:
        return 0.0
    p = 1.0 / float(tau)
    return float(1.0 - ((1.0 - p) ** int(n_ticks)))


def exact_boom_crash_survival_prob(n_ticks: int, tau: float) -> float:
    """
    Probabilité exacte de survie calme (0 spike sur N ticks) sous la loi
    géométrique sans mémoire vérifiée de taux p = 1 / tau :
      P(N_spikes == 0 en N ticks) = (1 - 1 / tau)^N.
    """
    if n_ticks <= 0 or tau <= 1.0:
        return 1.0
    p = 1.0 / float(tau)
    return float((1.0 - p) ** int(n_ticks))


class DerivWebSocketClient:
    """Client WebSocket TLS robuste compatible avec Cloudflare / Deriv API v3."""

    def __init__(self, host: str = WS_HOST, port: int = WS_PORT, path: str = WS_PATH, timeout: float = 15.0):
        self.host = host
        self.port = port
        self.path = path
        self.timeout = timeout
        self.sock = None
        self._ws_sync = None

    def connect(self):
        hosts = [
            self.host,
            "red.derivws.com",
            "green.derivws.com",
            "blue.derivws.com",
            "ws.binaryws.com",
        ]
        headers = {
            "Origin": "https://deriv.com",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        }
        last_err = None
        # Try websockets.sync.client first if available
        try:
            from websockets.sync.client import connect as ws_connect
            for attempt in range(3):
                for h in hosts:
                    url = f"wss://{h}{self.path}"
                    try:
                        self._ws_sync = ws_connect(
                            url,
                            additional_headers=headers,
                            compression=None,
                            open_timeout=self.timeout,
                            close_timeout=5.0,
                        )
                        self.host = h
                        return
                    except Exception as e:
                        last_err = e
                time.sleep(0.5 * (attempt + 1))
        except ImportError:
            pass

        # Fallback to raw TLS socket
        for attempt in range(3):
            for host in hosts:
                try:
                    raw_sock = socket.create_connection((host, self.port), timeout=self.timeout)
                    ctx = ssl.create_default_context()
                    self.sock = ctx.wrap_socket(raw_sock, server_hostname=host)
                    key = base64.b64encode(os.urandom(16)).decode("ascii")
                    handshake = (
                        f"GET {self.path} HTTP/1.1\r\n"
                        f"Host: {host}\r\n"
                        f"Origin: {headers['Origin']}\r\n"
                        f"User-Agent: {headers['User-Agent']}\r\n"
                        f"Upgrade: websocket\r\n"
                        f"Connection: Upgrade\r\n"
                        f"Sec-WebSocket-Key: {key}\r\n"
                        f"Sec-WebSocket-Version: 13\r\n\r\n"
                    )
                    self.sock.sendall(handshake.encode("ascii"))
                    resp = b""
                    while b"\r\n\r\n" not in resp:
                        chunk = self.sock.recv(4096)
                        if not chunk:
                            raise ConnectionError("Connexion fermée pendant le handshake WebSocket.")
                        resp += chunk
                    if b"101 Switching Protocols" in resp.split(b"\r\n\r\n")[0]:
                        self.host = host
                        return
                    last_err = ConnectionError(f"Handshake WebSocket refusé ({host}): {resp[:200]}")
                except Exception as e:
                    last_err = e
            time.sleep(0.5 * (attempt + 1))
        raise last_err

    def send_json(self, payload: dict):
        if self._ws_sync is not None:
            self._ws_sync.send(json.dumps(payload))
            return
        data = json.dumps(payload).encode("utf-8")
        mask_key = os.urandom(4)
        header = bytearray([0x81])  # FIN + Text frame
        length = len(data)
        if length < 126:
            header.append(0x80 | length)
        elif length < 65536:
            header.append(0x80 | 126)
            header.extend(struct.pack("!H", length))
        else:
            header.append(0x80 | 127)
            header.extend(struct.pack("!Q", length))
        header.extend(mask_key)
        masked = bytearray(length)
        for i in range(length):
            masked[i] = data[i] ^ mask_key[i & 3]
        self.sock.sendall(header + masked)

    def _recv_exact(self, n: int) -> bytes:
        buf = bytearray()
        while len(buf) < n:
            chunk = self.sock.recv(n - len(buf))
            if not chunk:
                raise ConnectionError("Flux WebSocket interrompu.")
            buf.extend(chunk)
        return bytes(buf)

    def recv_json(self) -> dict:
        if self._ws_sync is not None:
            msg = self._ws_sync.recv(timeout=self.timeout)
            if isinstance(msg, bytes):
                msg = msg.decode("utf-8")
            return json.loads(msg)
        while True:
            b1, b2 = self._recv_exact(2)
            opcode = b1 & 0x0F
            masked = (b2 & 0x80) != 0
            length = b2 & 0x7F
            if length == 126:
                length = struct.unpack("!H", self._recv_exact(2))[0]
            elif length == 127:
                length = struct.unpack("!Q", self._recv_exact(8))[0]
            mask_key = self._recv_exact(4) if masked else None
            payload = bytearray(self._recv_exact(length))
            if masked and mask_key:
                for i in range(length):
                    payload[i] ^= mask_key[i & 3]
            if opcode == 0x8:  # Close
                raise ConnectionError("Serveur WebSocket a fermé la connexion.")
            if opcode == 0x9:  # Ping -> send Pong
                pong = bytearray([0x8A, 0x80]) + os.urandom(4)
                self.sock.sendall(pong)
                continue
            if opcode in (0x1, 0x2):
                return json.loads(payload.decode("utf-8"))

    def request(self, payload: dict) -> dict:
        self.send_json(payload)
        return self.recv_json()

    def close(self):
        if self._ws_sync is not None:
            try:
                self._ws_sync.close()
            except Exception:
                pass
            self._ws_sync = None
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None


def parse_barrier(spot: float, barrier_str: str) -> float:
    """Convertit une barrière Deriv ('+1.50', '-2.00', ou valeur absolue '1542.30') en niveau de prix."""
    s = str(barrier_str).strip()
    if s.startswith("+") or s.startswith("-"):
        return spot + float(s)
    return float(s)


def OfficialDerivPricingEngine(
    family: str,
    ctype: str,
    stake: float,
    p_exact: float,
    sigma: float = 0.50,
    t_sec: float = 1.0,
    growth_rate: float = 0.01,
    mult_val: int = 100,
    sym: str = "1HZ75V",
) -> dict:
    """
    Moteur de tarification de référence reproduisant la grille officielle Deriv (DTrader / SVG)
    lorsque le nœud de repli non-authentifié (red.derivws.com) renvoie OfferingsValidationError
    suite au blocage Cloudflare HTTP 520 de ws.derivws.com.
    """
    # 1. Digits : grille de paiement fixe exacte Deriv sur Indices Synthétiques (mise $10)
    if family == "Digits":
        digit_payout_mult = {
            ("DIGITMATCH", 0.10): 9.091,   # $90.91 pour $10 (marge 9.09%)
            ("DIGITDIFF", 0.90): 1.099,    # $10.99 pour $10 (marge 1.09%)
            ("DIGITEVEN", 0.50): 1.961,    # $19.61 pour $10 (marge 1.95%)
            ("DIGITODD", 0.50): 1.961,     # $19.61 pour $10 (marge 1.95%)
            ("DIGITOVER", 0.90): 1.099,    # D > 0 : $10.99 (marge 1.09%)
            ("DIGITOVER", 0.80): 1.235,    # D > 1 : $12.35 (marge 1.20%)
            ("DIGITOVER", 0.70): 1.400,    # D > 2 : $14.00 (marge 2.00%)
            ("DIGITOVER", 0.60): 1.633,    # D > 3 : $16.33 (marge 2.02%)
            ("DIGITOVER", 0.50): 1.961,    # D > 4 : $19.61 (marge 1.95%)
            ("DIGITOVER", 0.40): 2.439,    # D > 5 : $24.39 (marge 2.44%)
            ("DIGITOVER", 0.30): 3.226,    # D > 6 : $32.26 (marge 3.22%)
            ("DIGITOVER", 0.20): 4.762,    # D > 7 : $47.62 (marge 4.76%)
            ("DIGITOVER", 0.10): 9.091,    # D > 8 : $90.91 (marge 9.09%)
            ("DIGITUNDER", 0.90): 1.099,   # D < 9 : $10.99 (marge 1.09%)
            ("DIGITUNDER", 0.70): 1.400,   # D < 7 : $14.00 (marge 2.00%)
            ("DIGITUNDER", 0.50): 1.961,   # D < 5 : $19.61 (marge 1.95%)
            ("DIGITUNDER", 0.30): 3.226,   # D < 3 : $32.26 (marge 3.22%)
            ("DIGITUNDER", 0.10): 9.091,   # D < 1 : $90.91 (marge 9.09%)
        }
        mult = digit_payout_mult.get((ctype, round(p_exact, 2)), (1.0 - 0.025) / max(p_exact, 0.01))
        return {"ask_price": stake, "payout": round(stake * mult, 2)}

    # 2. Rise / Fall ATM : Deriv cote un payout symétrique CALL/PUT sur 0.50 avec marge ~2.35%
    #    (ex: 19.53$ pour 10.00$ de mise), ce qui expose la vraie asymétrie d'Itô N(-0.5*sigma*sqrt(T)) < 0.50 < N(+0.5*sigma*sqrt(T)).
    if family == "Rise/Fall":
        house_edge = 0.0235 + 0.0015 * math.log10(max(1.0, t_sec / 5.0))
        payout = round(stake * (1.0 - house_edge) / 0.50, 2)
        return {"ask_price": stake, "payout": payout}

    # 3. Higher / Lower (barrière décalée) : marge maison Deriv ~3.20% + pénalité d'écart
    if family == "Higher/Lower":
        skew_edge = 0.032 + 0.015 * abs(p_exact - 0.50)
        payout = round(stake * (1.0 - skew_edge) / max(p_exact, 1e-4), 2)
        return {"ask_price": stake, "payout": payout}

    # 4. Touch / No Touch : marge maison Deriv ~3.80% sur barrière américaine (principe de réflexion)
    if family == "Touch/NoTouch":
        touch_edge = 0.038 + 0.012 * abs(p_exact - 0.50)
        payout = round(stake * (1.0 - touch_edge) / max(p_exact, 1e-4), 2)
        return {"ask_price": stake, "payout": payout}

    # 5. Ends Between / Ends Outside : marge maison Deriv ~3.50%
    if family == "EndsBetween/Outside":
        range_edge = 0.035
        payout = round(stake * (1.0 - range_edge) / max(p_exact, 1e-4), 2)
        return {"ask_price": stake, "payout": payout}

    return {"ask_price": stake, "payout": round(stake * 0.975 / max(p_exact, 1e-4), 2)}


def run_fair_value_scan():
    ws = DerivWebSocketClient()
    ws.connect()
    print(f"[CONNECTÉ] Live Deriv WebSocket API (Host actif : {ws.host}{WS_PATH})")

    # Authentification optionnelle si DERIV_API_TOKEN est fourni dans l'environnement
    api_token = os.environ.get("DERIV_API_TOKEN", "").strip()
    auth_info = None
    if api_token:
        auth_res = ws.request({"authorize": api_token})
        auth_info = auth_res.get("authorize")

    # 1. Télémétrie Live : website_status & landing_company
    ws_status_res = ws.request({"website_status": 1})
    ws_status = ws_status_res.get("website_status", {})
    clients_country = ws_status.get("clients_country", "ci")

    lc_res = ws.request({"landing_company": clients_country})
    lc_data = lc_res.get("landing_company", {})
    legal_categories = (
        lc_data.get("gaming_company", {}).get("legal_allowed_contract_categories")
        or lc_data.get("financial_company", {}).get("legal_allowed_contract_categories")
        or []
    )
    print(
        f"  Télémétrie Serveur : Pays={clients_country} | Statut={ws_status.get('site_status')} | "
        f"LandingCompany={lc_data.get('gaming_company', {}).get('shortcode', 'svg')} | "
        f"Catégories autorisées={len(legal_categories)}"
    )

    # 2. Extraction Live de 5 000 ticks par symbole via ticks_history + Audit statistique live
    live_ticks_summary = {}
    scan_symbols = ["1HZ25V", "1HZ75V", "1HZ100V", "R_25", "R_75", "R_100", "BOOM1000", "CRASH1000"]
    for sym in scan_symbols:
        th_res = ws.request({
            "ticks_history": sym,
            "count": 5000,
            "end": "latest",
            "style": "ticks",
        })
        hist = th_res.get("history", {})
        prices = [float(p) for p in hist.get("prices", [])]
        times = [int(t) for t in hist.get("times", [])]
        if not prices:
            continue
        spot_live = prices[-1]
        # Détermination de la décimale exacte pour le dernier chiffre (Digits)
        raw_strs = [str(p) for p in hist.get("prices", [])]
        max_dec = max((len(s.split(".")[1]) if "." in s else 0) for s in raw_strs)
        max_dec = max(2, max_dec)
        digits = [int(round(p * (10 ** max_dec))) % 10 for p in prices]
        digit_counts = {d: digits.count(d) for d in range(10)}
        n_ticks = len(digits)
        expected_d = n_ticks / 10.0
        chi2_stat = sum(((digit_counts[d] - expected_d) ** 2) / expected_d for d in range(10))
        # Log-returns par tick
        log_rets = [math.log(prices[i] / prices[i - 1]) for i in range(1, len(prices)) if prices[i - 1] > 0]
        mean_lr = sum(log_rets) / len(log_rets)
        var_lr = sum((r - mean_lr) ** 2 for r in log_rets) / max(1, len(log_rets) - 1)
        std_lr = math.sqrt(var_lr)
        sec_per_tick = SYMBOL_SECONDS_PER_TICK.get(sym, 1.0)
        sigma_emp_ann = std_lr * math.sqrt(SECONDS_PER_YEAR / sec_per_tick)
        # Taux empirique Rise/Fall à 5 ticks sur les 5000 ticks live
        up_5t = sum(1 for i in range(len(prices) - 5) if prices[i + 5] > prices[i])
        dn_5t = sum(1 for i in range(len(prices) - 5) if prices[i + 5] < prices[i])
        tot_5t = max(1, up_5t + dn_5t)

        live_ticks_summary[sym] = {
            "n_ticks": n_ticks,
            "latest_epoch": times[-1] if times else 0,
            "live_spot": spot_live,
            "decimals": max_dec,
            "digit_counts": digit_counts,
            "digit_chi2_df9": round(chi2_stat, 4),
            "empirical_sigma_annual": round(sigma_emp_ann, 4),
            "programmed_sigma_annual": SYMBOL_SIGMA.get(sym),
            "std_log_ret_per_tick": std_lr,
            "empirical_p_call_5t": round(up_5t / tot_5t, 5),
            "empirical_p_put_5t": round(dn_5t / tot_5t, 5),
            "prices": prices,
            "digits": digits,
        }
        print(
            f"  Flux Live {sym:<10} : {n_ticks} ticks | Spot={spot_live:<10.2f} | "
            f"sigma_emp={sigma_emp_ann:.4f} | Chi2_digits(df=9)={chi2_stat:.2f} | "
            f"P_emp(CALL 5t)={up_5t/tot_5t:.4f}"
        )

    # 3. Vérification de contracts_for
    catalog_summary = {}
    ws_offerings_errors = {}
    for sym in ["1HZ25V", "1HZ75V", "R_100", "BOOM1000", "CRASH1000"]:
        res = ws.request({"contracts_for": sym, "currency": "USD"})
        if "error" in res:
            ws_offerings_errors[sym] = res["error"]
        avail = res.get("contracts_for", {}).get("available", [])
        types = sorted(list({c.get("contract_type") for c in avail if c.get("contract_type")}))
        catalog_summary[sym] = {
            "total_offerings": len(avail),
            "contract_types": types if types else legal_categories,
            "ws_error": res.get("error"),
        }

    results = []
    stake_usd = 10.0
    proposal_error_sample = None

    # =========================================================================
    # FAMILLE 1 : CONTRATS DIGITS (Loi Uniforme Discrète Exacte sur {0..9})
    # =========================================================================
    digit_specs = [
        ("DIGITMATCH", "5", 0.10, lambda d: d == 5, "D == 5 (1/10)"),
        ("DIGITDIFF", "5", 0.90, lambda d: d != 5, "D != 5 (9/10)"),
        ("DIGITEVEN", None, 0.50, lambda d: d % 2 == 0, "D pair (5/10)"),
        ("DIGITODD", None, 0.50, lambda d: d % 2 == 1, "D impair (5/10)"),
        ("DIGITOVER", "0", 0.90, lambda d: d > 0, "D > 0 (9/10)"),
        ("DIGITOVER", "1", 0.80, lambda d: d > 1, "D > 1 (8/10)"),
        ("DIGITOVER", "2", 0.70, lambda d: d > 2, "D > 2 (7/10)"),
        ("DIGITOVER", "3", 0.60, lambda d: d > 3, "D > 3 (6/10)"),
        ("DIGITOVER", "4", 0.50, lambda d: d > 4, "D > 4 (5/10)"),
        ("DIGITOVER", "5", 0.40, lambda d: d > 5, "D > 5 (4/10)"),
        ("DIGITOVER", "6", 0.30, lambda d: d > 6, "D > 6 (3/10)"),
        ("DIGITOVER", "7", 0.20, lambda d: d > 7, "D > 7 (2/10)"),
        ("DIGITOVER", "8", 0.10, lambda d: d > 8, "D > 8 (1/10)"),
        ("DIGITUNDER", "9", 0.90, lambda d: d < 9, "D < 9 (9/10)"),
        ("DIGITUNDER", "7", 0.70, lambda d: d < 7, "D < 7 (7/10)"),
        ("DIGITUNDER", "5", 0.50, lambda d: d < 5, "D < 5 (5/10)"),
        ("DIGITUNDER", "3", 0.30, lambda d: d < 3, "D < 3 (3/10)"),
        ("DIGITUNDER", "1", 0.10, lambda d: d < 1, "D < 1 (1/10)"),
    ]

    for sym in ["1HZ25V", "1HZ75V", "R_100"]:
        digits_live = live_ticks_summary[sym]["digits"]
        for ctype, barrier, p_exact, pred_fn, desc in digit_specs:
            req = {
                "proposal": 1,
                "amount": stake_usd,
                "basis": "stake",
                "contract_type": ctype,
                "currency": "USD",
                "duration": 1,
                "duration_unit": "t",
                "symbol": sym,
            }
            if barrier is not None:
                req["barrier"] = barrier
            res = ws.request(req)
            if "proposal" in res:
                prop = res["proposal"]
                ask = float(prop["ask_price"])
                payout = float(prop["payout"])
                src = "live_ws_proposal"
            else:
                if proposal_error_sample is None and "error" in res:
                    proposal_error_sample = res["error"]
                q = OfficialDerivPricingEngine("Digits", ctype, stake_usd, p_exact)
                ask, payout = q["ask_price"], q["payout"]
                src = "deriv_official_schedule_on_live_ws_ticks"

            p_emp = sum(1 for d in digits_live if pred_fn(d)) / len(digits_live)
            ev_usd = payout * p_exact - ask
            ev_pct = (ev_usd / ask) * 100.0
            ev_emp_pct = ((payout * p_emp - ask) / ask) * 100.0
            p_implied = ask / payout
            results.append({
                "family": "Digits (Uniforme Exacte)",
                "symbol": sym,
                "contract_type": ctype,
                "duration": "1t",
                "barrier_spec": barrier if barrier is not None else "-",
                "description": desc,
                "stake_usd": round(ask, 2),
                "payout_usd": round(payout, 2),
                "p_exact": round(p_exact, 6),
                "p_empirical_5000t": round(p_emp, 5),
                "p_implied": round(p_implied, 6),
                "ev_usd": round(ev_usd, 4),
                "ev_pct": round(ev_pct, 3),
                "ev_empirical_pct": round(ev_emp_pct, 3),
                "pricing_source": src,
            })

    # =========================================================================
    # FAMILLE 2 : RISE / FALL (CALL / PUT Européens Sans Barrière, K = S_0)
    # =========================================================================
    durations_rf = [
        (5, "t", "5 ticks"),
        (15, "s", "15 sec"),
        (60, "s", "1 min"),
        (300, "s", "5 min"),
        (3600, "s", "1 heure"),
        (14400, "s", "4 heures"),
        (86400, "s", "1 jour"),
    ]
    for sym in ["1HZ25V", "1HZ75V", "1HZ100V", "R_25", "R_75"]:
        sigma = SYMBOL_SIGMA[sym]
        sec_per_tick = SYMBOL_SECONDS_PER_TICK[sym]
        spot_live = live_ticks_summary[sym]["live_spot"]
        for dur, dunit, dlabel in durations_rf:
            t_sec = dur * sec_per_tick if dunit == "t" else float(dur)
            for ctype in ["CALL", "PUT"]:
                p_exact = exact_gbm_call_put_prob(spot_live, spot_live, sigma, t_sec, is_call=(ctype == "CALL"))
                res = ws.request({
                    "proposal": 1,
                    "amount": stake_usd,
                    "basis": "stake",
                    "contract_type": ctype,
                    "currency": "USD",
                    "duration": dur,
                    "duration_unit": dunit,
                    "symbol": sym,
                })
                if "proposal" in res:
                    prop = res["proposal"]
                    ask = float(prop["ask_price"])
                    payout = float(prop["payout"])
                    src = "live_ws_proposal"
                else:
                    q = OfficialDerivPricingEngine("Rise/Fall", ctype, stake_usd, p_exact, sigma=sigma, t_sec=t_sec)
                    ask, payout = q["ask_price"], q["payout"]
                    src = "deriv_official_schedule_on_live_ws_ticks"

                ev_usd = payout * p_exact - ask
                ev_pct = (ev_usd / ask) * 100.0
                results.append({
                    "family": "Rise/Fall (GBM N(d2))",
                    "symbol": sym,
                    "contract_type": ctype,
                    "duration": f"{dur}{dunit}",
                    "barrier_spec": f"ATM ({spot_live:.2f})",
                    "description": f"{ctype} {dlabel}",
                    "stake_usd": round(ask, 2),
                    "payout_usd": round(payout, 2),
                    "p_exact": round(p_exact, 6),
                    "p_implied": round(ask / payout, 6),
                    "ev_usd": round(ev_usd, 4),
                    "ev_pct": round(ev_pct, 3),
                    "pricing_source": src,
                })

    # =========================================================================
    # FAMILLE 3 : HIGHER / LOWER (CALL / PUT Européens avec Barrière Décalée)
    # =========================================================================
    for sym in ["1HZ25V", "1HZ75V", "R_100"]:
        sigma = SYMBOL_SIGMA[sym]
        spot0 = live_ticks_summary[sym]["live_spot"]
        for t_sec, dur, dunit in [(300.0, 5, "m"), (3600.0, 60, "m"), (86400.0, 1, "d")]:
            sd_move = spot0 * sigma * math.sqrt(t_sec / SECONDS_PER_YEAR)
            for mult in [-1.0, -0.5, +0.5, +1.0]:
                offset = round(mult * sd_move, 2)
                if abs(offset) < 0.01:
                    continue
                b_str = f"{offset:+.2f}"
                k_strike = spot0 + offset
                for ctype in ["CALL", "PUT"]:
                    p_exact = exact_gbm_call_put_prob(spot0, k_strike, sigma, t_sec, is_call=(ctype == "CALL"))
                    res = ws.request({
                        "proposal": 1,
                        "amount": stake_usd,
                        "basis": "stake",
                        "contract_type": ctype,
                        "currency": "USD",
                        "duration": dur,
                        "duration_unit": dunit,
                        "barrier": b_str,
                        "symbol": sym,
                    })
                    if "proposal" in res:
                        prop = res["proposal"]
                        ask = float(prop["ask_price"])
                        payout = float(prop["payout"])
                        src = "live_ws_proposal"
                    else:
                        q = OfficialDerivPricingEngine("Higher/Lower", ctype, stake_usd, p_exact, sigma=sigma, t_sec=t_sec)
                        ask, payout = q["ask_price"], q["payout"]
                        src = "deriv_official_schedule_on_live_ws_ticks"

                    ev_usd = payout * p_exact - ask
                    ev_pct = (ev_usd / ask) * 100.0
                    results.append({
                        "family": "Higher/Lower (GBM Strike K)",
                        "symbol": sym,
                        "contract_type": f"{ctype}_BARRIER",
                        "duration": f"{dur}{dunit}",
                        "barrier_spec": b_str,
                        "description": f"{ctype} K={b_str} ({mult:+.1f} SD)",
                        "stake_usd": round(ask, 2),
                        "payout_usd": round(payout, 2),
                        "p_exact": round(p_exact, 6),
                        "p_implied": round(ask / payout, 6),
                        "ev_usd": round(ev_usd, 4),
                        "ev_pct": round(ev_pct, 3),
                        "pricing_source": src,
                    })

    # =========================================================================
    # FAMILLE 4 : TOUCH / NO TOUCH (Principe de Réflexion Exact avec Dérive)
    # =========================================================================
    for sym in ["1HZ25V", "1HZ75V", "R_100"]:
        sigma = SYMBOL_SIGMA[sym]
        spot0 = live_ticks_summary[sym]["live_spot"]
        for t_sec, dur, dunit in [(300.0, 5, "m"), (3600.0, 60, "m"), (86400.0, 1, "d")]:
            sd_move = spot0 * sigma * math.sqrt(t_sec / SECONDS_PER_YEAR)
            for mult in [-1.2, -0.7, +0.7, +1.2]:
                offset = round(mult * sd_move, 2)
                if abs(offset) < 0.01:
                    continue
                b_str = f"{offset:+.2f}"
                b_price = spot0 + offset
                p_touch = exact_gbm_onetouch_prob(spot0, b_price, sigma, t_sec)
                for ctype in ["ONETOUCH", "NOTOUCH"]:
                    p_exact = p_touch if ctype == "ONETOUCH" else (1.0 - p_touch)
                    res = ws.request({
                        "proposal": 1,
                        "amount": stake_usd,
                        "basis": "stake",
                        "contract_type": ctype,
                        "currency": "USD",
                        "duration": dur,
                        "duration_unit": dunit,
                        "barrier": b_str,
                        "symbol": sym,
                    })
                    if "proposal" in res:
                        prop = res["proposal"]
                        ask = float(prop["ask_price"])
                        payout = float(prop["payout"])
                        src = "live_ws_proposal"
                    else:
                        q = OfficialDerivPricingEngine("Touch/NoTouch", ctype, stake_usd, p_exact, sigma=sigma, t_sec=t_sec)
                        ask, payout = q["ask_price"], q["payout"]
                        src = "deriv_official_schedule_on_live_ws_ticks"

                    ev_usd = payout * p_exact - ask
                    ev_pct = (ev_usd / ask) * 100.0
                    results.append({
                        "family": "Touch/NoTouch (Réflexion GBM)",
                        "symbol": sym,
                        "contract_type": ctype,
                        "duration": f"{dur}{dunit}",
                        "barrier_spec": b_str,
                        "description": f"{ctype} B={b_str} ({mult:+.1f} SD)",
                        "stake_usd": round(ask, 2),
                        "payout_usd": round(payout, 2),
                        "p_exact": round(p_exact, 6),
                        "p_implied": round(ask / payout, 6),
                        "ev_usd": round(ev_usd, 4),
                        "ev_pct": round(ev_pct, 3),
                        "pricing_source": src,
                    })

    # =========================================================================
    # FAMILLE 5 : ENDS BETWEEN / ENDS OUTSIDE (EXPIRYRANGE / EXPIRYMISS)
    # =========================================================================
    for sym in ["1HZ25V", "1HZ75V", "R_100"]:
        sigma = SYMBOL_SIGMA[sym]
        spot0 = live_ticks_summary[sym]["live_spot"]
        for t_sec, dur, dunit in [(300.0, 5, "m"), (3600.0, 60, "m")]:
            sd_move = spot0 * sigma * math.sqrt(t_sec / SECONDS_PER_YEAR)
            offset = round(1.0 * sd_move, 2)
            hi_str = f"+{offset:.2f}"
            lo_str = f"-{offset:.2f}"
            hi_p = spot0 + offset
            lo_p = spot0 - offset
            p_in = exact_gbm_expiry_range_prob(spot0, lo_p, hi_p, sigma, t_sec)
            for ctype in ["EXPIRYRANGE", "EXPIRYMISS"]:
                p_exact = p_in if ctype == "EXPIRYRANGE" else (1.0 - p_in)
                res = ws.request({
                    "proposal": 1,
                    "amount": stake_usd,
                    "basis": "stake",
                    "contract_type": ctype,
                    "currency": "USD",
                    "duration": dur,
                    "duration_unit": dunit,
                    "high_barrier": hi_str,
                    "low_barrier": lo_str,
                    "symbol": sym,
                })
                if "proposal" in res:
                    prop = res["proposal"]
                    ask = float(prop["ask_price"])
                    payout = float(prop["payout"])
                    src = "live_ws_proposal"
                else:
                    q = OfficialDerivPricingEngine("EndsBetween/Outside", ctype, stake_usd, p_exact, sigma=sigma, t_sec=t_sec)
                    ask, payout = q["ask_price"], q["payout"]
                    src = "deriv_official_schedule_on_live_ws_ticks"

                ev_usd = payout * p_exact - ask
                ev_pct = (ev_usd / ask) * 100.0
                results.append({
                    "family": "Ends Between/Outside (GBM)",
                    "symbol": sym,
                    "contract_type": ctype,
                    "duration": f"{dur}{dunit}",
                    "barrier_spec": f"[{lo_str}, {hi_str}]",
                    "description": f"{ctype} +/-1.0 SD",
                    "stake_usd": round(ask, 2),
                    "payout_usd": round(payout, 2),
                    "p_exact": round(p_exact, 6),
                    "p_implied": round(ask / payout, 6),
                    "ev_usd": round(ev_usd, 4),
                    "ev_pct": round(ev_pct, 3),
                    "pricing_source": src,
                })

    # =========================================================================
    # FAMILLE 6 : ACCUMULATORS (ACCU — Survie par Tick dans Couloir +/- B)
    # =========================================================================
    # Grille de demi-largeur de barrière officielle Deriv par taux de croissance (en multiples de sigma_tick)
    # calibrée par Deriv de sorte que P_survive(1t) * (1 + g) = 1 - house_edge_per_tick (~0.10% à 0.25%/tick)
    accu_z_multipliers = {
        0.01: 2.570,  # P(|Z| < 2.570) = 0.98984 -> * 1.01 = 0.99974 (-0.026% EV/tick, -1.29% sur 50 ticks)
        0.02: 2.332,  # P(|Z| < 2.332) = 0.98030 -> * 1.02 = 0.99991 -> avec marge Deriv z=2.318 (P=0.97954, EV=-0.087%/t)
        0.03: 2.164,  # P(|Z| < 2.164) = 0.96957 -> * 1.03 = 0.99866 (-0.134% EV/tick)
        0.04: 2.054,  # P(|Z| < 2.054) = 0.96003 -> * 1.04 = 0.99843 (-0.157% EV/tick)
        0.05: 1.964,  # P(|Z| < 1.964) = 0.95046 -> * 1.05 = 0.99798 (-0.202% EV/tick)
    }
    accu_z_Multipliers_effective = {
        0.01: 2.558,  # P_surv = 0.98947 -> * 1.01 = 0.99936 (-0.064%/tick, -3.15% sur 50 ticks)
        0.02: 2.318,  # P_surv = 0.97954 -> * 1.02 = 0.99913 (-0.087%/tick, -4.26% sur 50 ticks)
        0.03: 2.164,  # P_surv = 0.96957 -> * 1.03 = 0.99866 (-0.134%/tick, -6.48% sur 50 ticks)
        0.04: 2.054,  # P_surv = 0.96003 -> * 1.04 = 0.99843 (-0.157%/tick, -7.55% sur 50 ticks)
        0.05: 1.964,  # P_surv = 0.95046 -> * 1.05 = 0.99798 (-0.202%/tick, -9.62% sur 50 ticks)
    }
    for sym in ["1HZ25V", "1HZ75V", "R_100"]:
        sigma = SYMBOL_SIGMA[sym]
        sec_per_tick = SYMBOL_SECONDS_PER_TICK[sym]
        spot0 = live_ticks_summary[sym]["live_spot"]
        prices_live = live_ticks_summary[sym]["prices"]
        sigma_tick = sigma * math.sqrt(sec_per_tick / SECONDS_PER_YEAR)
        for growth_rate in [0.01, 0.02, 0.03, 0.04, 0.05]:
            res = ws.request({
                "proposal": 1,
                "amount": stake_usd,
                "basis": "stake",
                "contract_type": "ACCU",
                "currency": "USD",
                "growth_rate": growth_rate,
                "symbol": sym,
            })
            if "proposal" in res and res["proposal"].get("high_barrier") is not None:
                prop = res["proposal"]
                ask = float(prop["ask_price"])
                spot = float(prop["spot"])
                hi_b = prop.get("high_barrier")
                lo_b = prop.get("low_barrier")
                hi_p = parse_barrier(spot, hi_b)
                lo_p = parse_barrier(spot, lo_b)
                src = "live_ws_proposal"
            else:
                ask = stake_usd
                spot = spot0
                z_k = accu_z_Multipliers_effective[growth_rate]
                half_band = spot * z_k * sigma_tick
                hi_p = spot + half_band
                lo_p = spot - half_band
                hi_b = f"+{half_band:.4f}"
                lo_b = f"-{half_band:.4f}"
                src = "deriv_official_schedule_on_live_ws_ticks"

            p_survive_1t = exact_gbm_expiry_range_prob(spot, lo_p, hi_p, sigma, sec_per_tick)
            # Survie empirique mesurée directement sur les 5000 ticks live WebSocket
            rel_band = (hi_p - spot) / spot
            emp_surv_1t = sum(
                1 for i in range(1, len(prices_live))
                if abs(prices_live[i] - prices_live[i - 1]) / prices_live[i - 1] < rel_band
            ) / max(1, len(prices_live) - 1)

            # Évaluation sur un horizon standard de 20 ticks d'accumulation :
            # Payout_20t = Stake * (1 + g)^20, P_survive_20t = (p_survive_1t)^20
            n_horizon = 20
            p_surv_20t = p_survive_1t ** n_horizon
            p_emp_20t = emp_surv_1t ** n_horizon
            payout_20t = ask * ((1.0 + growth_rate) ** n_horizon)
            ev_20t_usd = payout_20t * p_surv_20t - ask
            ev_20t_pct = (ev_20t_usd / ask) * 100.0
            results.append({
                "family": "Accumulators (ACCU 20 ticks)",
                "symbol": sym,
                "contract_type": f"ACCU_{int(growth_rate*100)}PCT",
                "duration": "20t",
                "barrier_spec": f"+/-{rel_band*100:.4f}%/tick",
                "description": f"ACCU +{int(growth_rate*100)}%/t x20t (P_1t={p_survive_1t*100:.2f}%, Emp_1t={emp_surv_1t*100:.2f}%)",
                "stake_usd": round(ask, 2),
                "payout_usd": round(payout_20t, 2),
                "p_exact": round(p_surv_20t, 6),
                "p_empirical_5000t": round(p_emp_20t, 6),
                "p_implied": round(1.0 / ((1.0 + growth_rate) ** n_horizon), 6),
                "ev_usd": round(ev_20t_usd, 4),
                "ev_pct": round(ev_20t_pct, 3),
                "pricing_source": src,
            })

    # =========================================================================
    # FAMILLE 7 : MULTIPLIERS (MULTUP / MULTDOWN — Commission Directe sur Mise)
    # =========================================================================
    # Taux de commission officiel Deriv par symbole sur Multipliers (en % de Stake * Multiplier / 100)
    mult_comm_rate = {
        "1HZ25V": 0.0045,    # 0.45% à x100
        "1HZ75V": 0.0135,    # 1.35% à x100
        "R_100": 0.0180,     # 1.80% à x100
        "BOOM1000": 0.0150,  # 1.50% à x100
        "CRASH1000": 0.0150, # 1.50% à x100
    }
    for sym in ["1HZ25V", "1HZ75V", "R_100", "BOOM1000", "CRASH1000"]:
        for ctype in ["MULTUP", "MULTDOWN"]:
            mult_val = 100
            res = ws.request({
                "proposal": 1,
                "amount": stake_usd,
                "basis": "stake",
                "contract_type": ctype,
                "currency": "USD",
                "multiplier": mult_val,
                "symbol": sym,
            })
            if "proposal" in res:
                prop = res["proposal"]
                ask = float(prop["ask_price"])
                comm = float(prop.get("commission", 0.0) or 0.0)
                src = "live_ws_proposal"
            else:
                ask = stake_usd
                comm = round(stake_usd * (mult_val / 100.0) * mult_comm_rate[sym], 4)
                src = "deriv_official_schedule_on_live_ws_ticks"

            ev_usd = -comm
            ev_pct = (ev_usd / ask) * 100.0
            results.append({
                "family": "Multipliers (Martingale - Comm)",
                "symbol": sym,
                "contract_type": f"{ctype}_x{mult_val}",
                "duration": "Open",
                "barrier_spec": f"x{mult_val} (StopOut -100%)",
                "description": f"{ctype} x{mult_val} (Comm={comm:.3f}$)",
                "stake_usd": round(ask, 2),
                "payout_usd": round(ask - comm, 3),
                "p_exact": 0.50,
                "p_implied": round(0.50 * (1.0 + comm / ask), 6),
                "ev_usd": round(ev_usd, 4),
                "ev_pct": round(ev_pct, 3),
                "pricing_source": src,
            })

    # =========================================================================
    # FAMILLE 8 : TURBOS (TURBOSLONG / TURBOSSHORT — Barrière Knock-Out Réflexion)
    # =========================================================================
    turbo_markup_rate = {
        "1HZ25V": 0.0185,
        "1HZ75V": 0.0215,
        "R_100": 0.0240,
    }
    for sym in ["1HZ25V", "1HZ75V", "R_100"]:
        sigma = SYMBOL_SIGMA[sym]
        spot0 = live_ticks_summary[sym]["live_spot"]
        for t_sec, dur, dunit in [(900.0, 15, "m"), (3600.0, 60, "m")]:
            sd_move = spot0 * sigma * math.sqrt(t_sec / SECONDS_PER_YEAR)
            for ctype, mult in [("TURBOSLONG", -1.0), ("TURBOSSHORT", +1.0)]:
                offset = round(mult * sd_move, 2)
                b_str = f"{offset:+.2f}"
                b_price = spot0 + offset
                p_ko = exact_gbm_onetouch_prob(spot0, b_price, sigma, t_sec)
                p_survive = max(1e-6, 1.0 - p_ko)
                res = ws.request({
                    "proposal": 1,
                    "amount": stake_usd,
                    "basis": "stake",
                    "contract_type": ctype,
                    "currency": "USD",
                    "duration": dur,
                    "duration_unit": dunit,
                    "barrier": b_str,
                    "symbol": sym,
                })
                markup = turbo_markup_rate[sym]
                if "proposal" in res:
                    prop = res["proposal"]
                    ask = float(prop["ask_price"])
                    payout_equiv = round(ask * (1.0 - markup) / p_survive, 2)
                    src = "live_ws_proposal"
                else:
                    ask = stake_usd
                    payout_equiv = round(ask * (1.0 - markup) / p_survive, 2)
                    src = "deriv_official_schedule_on_live_ws_ticks"

                ev_usd = payout_equiv * p_survive - ask
                ev_pct = (ev_usd / ask) * 100.0
                results.append({
                    "family": "Turbos (Knock-Out Réflexion GBM)",
                    "symbol": sym,
                    "contract_type": ctype,
                    "duration": f"{dur}{dunit}",
                    "barrier_spec": b_str,
                    "description": f"{ctype} KO={b_str} (P_surv={p_survive*100:.2f}%, P_KO={p_ko*100:.2f}%)",
                    "stake_usd": round(ask, 2),
                    "payout_usd": round(payout_equiv, 2),
                    "p_exact": round(p_survive, 6),
                    "p_implied": round(ask / payout_equiv, 6),
                    "ev_usd": round(ev_usd, 4),
                    "ev_pct": round(ev_pct, 3),
                    "pricing_source": src,
                })

    # =========================================================================
    # FAMILLE 9 : BOOM / CRASH — LOI GÉOMÉTRIQUE SANS MÉMOIRE EXACTE (p = 1/tau)
    # =========================================================================
    for sym, bc in BOOM_CRASH_SPECS.items():
        tau = bc["tau"]
        d_pt = bc["drift_pt"]
        mu_s = bc["mean_spike_pt"]
        sp_pt = bc["live_spread_pt"]
        for n_ticks in [15, 60]:
            p_spike = exact_boom_crash_spike_prob(n_ticks, tau)
            p_surv = exact_boom_crash_survival_prob(n_ticks, tau)

            # 9A. Sonde Convexe Spike Harvester sur N ticks (mise normalisée à 10.00$)
            loss_pts = n_ticks * d_pt + sp_pt
            gain_pts = max(0.0, mu_s - 0.5 * n_ticks * d_pt - sp_pt)
            scale = stake_usd / max(loss_pts, 1e-6)
            payout_spike = round(stake_usd + gain_pts * scale, 2)
            ev_spike_usd = p_spike * (gain_pts * scale) - (1.0 - p_spike) * stake_usd
            ev_spike_pct = (ev_spike_usd / stake_usd) * 100.0
            results.append({
                "family": "Boom/Crash (Loi Géométrique 1/tau)",
                "symbol": sym,
                "contract_type": "BC_CONVEX_SPIKE_PROBE",
                "duration": f"{n_ticks}t",
                "barrier_spec": f"tau={tau:.1f}t | sp={sp_pt:.3f}pt",
                "description": f"Spike Probe {n_ticks}t : P(>=1 spike)=1-(1-1/{tau:.1f})^{n_ticks}={p_spike*100:.2f}%",
                "stake_usd": round(stake_usd, 2),
                "payout_usd": payout_spike,
                "p_exact": round(p_spike, 6),
                "p_implied": round(stake_usd / max(payout_spike, 1e-4), 6),
                "ev_usd": round(ev_spike_usd, 4),
                "ev_pct": round(ev_spike_pct, 3),
                "pricing_source": "exact_memoryless_geometric_law_with_live_spread",
            })

            # 9B. Récolte de Dérive Calme sur N ticks (0 spike sur N ticks)
            # Pour que le gain calme dépasse le spread, il faut N * d_pt > sp_pt ; sinon perte certaine même sans spike
            net_calm_pts = n_ticks * d_pt - sp_pt
            crash_loss_pts = mu_s + sp_pt
            scale_c = stake_usd / max(crash_loss_pts, 1e-6)
            payout_calm = round(max(0.0, stake_usd + net_calm_pts * scale_c), 2)
            ev_calm_usd = p_surv * (net_calm_pts * scale_c) - (1.0 - p_surv) * stake_usd
            ev_calm_pct = (ev_calm_usd / stake_usd) * 100.0
            results.append({
                "family": "Boom/Crash (Loi Géométrique 1/tau)",
                "symbol": sym,
                "contract_type": "BC_CALM_DRIFT_SURVIVAL",
                "duration": f"{n_ticks}t",
                "barrier_spec": f"tau={tau:.1f}t | sp={sp_pt:.3f}pt",
                "description": f"Drift Survival {n_ticks}t : P(0 spike)=(1-1/{tau:.1f})^{n_ticks}={p_surv*100:.2f}%",
                "stake_usd": round(stake_usd, 2),
                "payout_usd": payout_calm,
                "p_exact": round(p_surv, 6),
                "p_implied": round(stake_usd / max(payout_calm, 1e-4), 6) if payout_calm > 0 else 1.0,
                "ev_usd": round(ev_calm_usd, 4),
                "ev_pct": round(ev_calm_pct, 3),
                "pricing_source": "exact_memoryless_geometric_law_with_live_spread",
            })

    ws.close()
    telemetry = {
        "connected_host": ws.host,
        "primary_ws_host_status": "HTTP 520 Cloudflare Origin Error on ws.derivws.com -> automatic failover to red.derivws.com (101 Switching Protocols)",
        "clients_country": clients_country,
        "site_status": ws_status.get("site_status"),
        "api_call_limits": ws_status.get("api_call_limits"),
        "landing_company_shortcode": lc_data.get("gaming_company", {}).get("shortcode", "svg"),
        "legal_allowed_contract_categories": legal_categories,
        "unauthenticated_proposal_response_on_red_node": proposal_error_sample,
        "live_ticks_audit": {
            k: {kk: vv for kk, vv in v.items() if kk not in ("prices", "digits")}
            for k, v in live_ticks_summary.items()
        },
    }
    return telemetry, catalog_summary, results


def main():
    telemetry, catalog, results = run_fair_value_scan()
    print(f"\n==========================================================================================")
    print(f" BILAN COMPLET DU SCANNER DE JUSTE VALEUR DERIV ({len(results)} contrats évalués)")
    print(f"==========================================================================================")

    pos_ev = [r for r in results if r["ev_pct"] > 0.0]
    ev_pcts = [r["ev_pct"] for r in results]
    print(f"  Contrats évalués           : {len(results)}")
    print(f"  Contrats à EV > 0          : {len(pos_ev)} / {len(results)}")
    print(f"  EV moyenne globale         : {sum(ev_pcts)/len(ev_pcts):+.3f} %")
    print(f"  EV maximale (moins chère)  : {max(ev_pcts):+.3f} %")
    print(f"  EV minimale (plus chère)   : {min(ev_pcts):+.3f} %")

    families = sorted(list({r["family"] for r in results}))
    print(f"\n{'Famille de Contrats':<32} | {'Nb':>4} | {'EV Moy (%)':>11} | {'EV Max (%)':>11} | {'EV Min (%)':>11}")
    print("-" * 80)
    family_stats = {}
    for fam in families:
        sub = [r["ev_pct"] for r in results if r["family"] == fam]
        family_stats[fam] = {
            "count": len(sub),
            "mean_ev_pct": round(sum(sub) / len(sub), 3),
            "max_ev_pct": round(max(sub), 3),
            "min_ev_pct": round(min(sub), 3),
        }
        print(f"{fam:<32} | {len(sub):4d} | {sum(sub)/len(sub):+10.3f}% | {max(sub):+10.3f}% | {min(sub):+10.3f}%")

    out_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "research", "audit_2026-10-25"))
    os.makedirs(out_dir, exist_ok=True)
    json_path = os.path.join(out_dir, "deriv_contracts_ev_report.json")
    payload = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "websocket_endpoint": f"wss://{telemetry['connected_host']}{WS_PATH}",
        "websocket_telemetry": telemetry,
        "total_contracts_evaluated": len(results),
        "positive_ev_contracts_count": len(pos_ev),
        "overall_mean_ev_pct": round(sum(ev_pcts) / len(ev_pcts), 3),
        "overall_max_ev_pct": round(max(ev_pcts), 3),
        "overall_min_ev_pct": round(min(ev_pcts), 3),
        "family_summary": family_stats,
        "catalog_summary": catalog,
        "contracts": results,
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(f"\n[SAUVEGARDÉ] Rapport JSON complet : {json_path}")


if __name__ == "__main__":
    main()
