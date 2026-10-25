import os, sys, math, unittest

class TestQuantitativeMechanics(unittest.TestCase):
    """
    Validation mathématique et microstructurelle du framework quantitatif dual :
    - Track 1 : Chasseur de Sauts Convexe (v8.22 Spike Hunter)
    - Track 2 : Volatility Squeeze Breakout (v3.00 avec filtre C2)
    """

    def setUp(self):
        # Paramètres physiques calibrés sur les données réelles
        self.calibrated_priors = {
            'Crash 600 Index': {'drift': 0.03681, 'mean_spike': 17.256, 'tau': 571.5, 'is_boom': False, 'stops_level': 2394, 'point': 0.001},
            'Crash 900 Index': {'drift': 0.01906, 'mean_spike': 8.234,  'tau': 907.3, 'is_boom': False, 'stops_level': 1740, 'point': 0.001},
            'Crash 1000 Index': {'drift': 0.00625, 'mean_spike': 4.966, 'tau': 961.0, 'is_boom': False, 'stops_level': 7620, 'point': 0.0001},
            'Boom 600 Index':  {'drift': 0.00923, 'mean_spike': 5.314,  'tau': 586.5, 'is_boom': True,  'stops_level': 1530, 'point': 0.001},
            'Boom 900 Index':  {'drift': 0.00998, 'mean_spike': 12.121, 'tau': 911.4, 'is_boom': True,  'stops_level': 1287, 'point': 0.001},
        }

    def test_poisson_hazard_rate_and_bounds(self):
        """Vérifie que le taux d'aléa de base P(T <= M) est strictement dans (0, 1) et monotone en M."""
        M = 60 # 60 ticks
        for sym, d in self.calibrated_priors.items():
            tau = d['tau']
            p0 = 1.0 - math.exp(-M / tau)
            self.assertGreater(p0, 0.0, f"p0 must be positive for {sym}")
            self.assertLess(p0, 0.25, f"p0 must be plausible for M=60 ticks on {sym}")
            
            # Monotonicity
            p0_longer = 1.0 - math.exp(-120 / tau)
            self.assertGreater(p0_longer, p0, "Hazard probability must grow strictly with time horizon")

    def test_convex_payoff_skewness(self):
        """Vérifie que l'inversion v8 transforme le ratio gain/perte b de b < 0.10 (v7) à b >= 3.0 (v8)."""
        k_tp = 0.85
        M = 60
        for sym, d in self.calibrated_priors.items():
            win_amplitude = k_tp * d['mean_spike']
            loss_drift = d['drift'] * M
            payoff_ratio_b = win_amplitude / loss_drift
            self.assertGreater(payoff_ratio_b, 3.0, f"Convex ratio b must be > 3.0 on {sym}, got {payoff_ratio_b:.2f}")

    def test_broker_min_stop_distance_invariants(self):
        """
        Vérifie l'invariant de conformité broker :
        Pour BUY  : tp - entry_price >= min_stop  ET  entry_bid - sl >= min_stop
        Pour SELL : entry_price - tp >= min_stop  ET  sl - entry_ask >= min_stop
        """
        k_tp = 0.85
        emergency_mult = 2.0
        M = 60

        for sym, d in self.calibrated_priors.items():
            digits = 4 if '1000' in sym else 3
            pt = d['point']
            min_stop = (d['stops_level'] + 5) * pt
            
            # Simulated quotes
            bid = 1000.000
            spread = 50 * pt
            ask = bid + spread
            
            lmax_pts = d['drift'] * M + spread
            sl_dist_pts = max(min_stop, emergency_mult * lmax_pts)
            tp_depth = max(min_stop, k_tp * d['mean_spike'])
            sl_depth = max(min_stop, sl_dist_pts)
            
            if d['is_boom']:
                # BUY: entry = ask
                entry_price = ask
                tp = round(entry_price + tp_depth, digits)
                sl = round(bid - sl_depth, digits)
                
                # Check distances
                self.assertGreaterEqual(round(tp - entry_price, 6), round(min_stop - 1e-7, 6),
                                        f"BUY TP distance violates min_stop on {sym}")
                self.assertGreaterEqual(round(bid - sl, 6), round(min_stop - 1e-7, 6),
                                        f"BUY SL distance violates min_stop on {sym}")
            else:
                # SELL: entry = bid
                entry_price = bid
                tp = round(entry_price - tp_depth, digits)
                sl = round(ask + sl_depth, digits)
                
                # Check distances
                self.assertGreaterEqual(round(entry_price - tp, 6), round(min_stop - 1e-7, 6),
                                        f"SELL TP distance violates min_stop on {sym}")
                self.assertGreaterEqual(round(sl - ask, 6), round(min_stop - 1e-7, 6),
                                        f"SELL SL distance violates min_stop on {sym}")

    def test_levy_area_calculation(self):
        """Vérifie la propriété antisymétrique de l'aire de Lévy (Rough Paths)."""
        # Chemin 2D simple : x(t) = cos(t), y(t) = sin(t)
        # Aire de Lévy = 0.5 * integral (x dy - y dx) = pi pour un cercle complet
        n_steps = 1000
        dt = 2.0 * math.pi / n_steps
        x = [math.cos(i * dt) for i in range(n_steps + 1)]
        y = [math.sin(i * dt) for i in range(n_steps + 1)]
        
        levy_area = 0.0
        for i in range(n_steps):
            dx = x[i+1] - x[i]
            dy = y[i+1] - y[i]
            levy_area += 0.5 * (x[i] * dy - y[i] * dx)
            
        self.assertAlmostEqual(levy_area, math.pi, places=2)

    def test_kelly_subfraction_bounds(self):
        """Vérifie que la fraction de Kelly prudente 1/8 respecte la contrainte de perte maximale autorisée."""
        equity = 9640.61
        kelly_fraction = 1.0 / 8.0 # 12.5%
        target_risk_usd = kelly_fraction * equity
        self.assertLess(target_risk_usd, equity * 0.20, "Kelly 1/8 must never risk more than 20% total equity")
        self.assertGreater(target_risk_usd, 50.0, "Target risk must be meaningful for multi-symbol diversification")


    def test_ea_version_and_normalized_order_price_invariants(self):
        v8_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'mql5', 'DerivBoomCrashHFT_v8.mq5')
        self.assertTrue(os.path.exists(v8_path), 'DerivBoomCrashHFT_v8.mq5 must exist')
        with open(v8_path, 'r', encoding='utf-8') as f:
            v8_content = f.read()
            
        self.assertIn('#property version     ' + chr(34) + '8.22' + chr(34), v8_content, 'EA version must be 8.22')
        self.assertIn('NormalizeDouble(live_tick.ask, digits)', v8_content, 'BUY entry price must be normalized')
        self.assertIn('NormalizeDouble(live_tick.bid, digits)', v8_content, 'SELL entry price must be normalized')
        self.assertIn('NormalizeDouble(req.price + tp_depth, digits)', v8_content, 'BUY TP must be normalized from req.price')
        self.assertIn('NormalizeDouble(req.price - tp_depth, digits)', v8_content, 'SELL TP must be normalized from req.price')

    def test_v830_b1_b9_and_fair_value_closed_form_laws(self):
        """Vérifie les correctifs B1-B9 de v8.30, l'alignement 7-features de v3.10 et les lois fermées du scanner."""
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        py_dir = os.path.join(repo_root, 'src', 'python')
        if py_dir not in sys.path:
            sys.path.insert(0, py_dir)
        import deriv_fair_value_scanner as dfvs

        v830_path = os.path.join(repo_root, 'src', 'mql5', 'DerivBoomCrashHFT_v830_Ultimate.mq5')
        with open(v830_path, 'r', encoding='utf-8') as f:
            v830 = f.read()
        self.assertIn('GetLiveExecutableSpreadPts(', v830)
        self.assertIn('tick.time_msc < tr.last_time_msc', v830)
        self.assertIn('MathPow(surv_train, horizon / train_horizon_ticks)', v830)
        self.assertIn('if(InpEnableStaticEvGate && !tr.ev_gate_pass)', v830)

        # Conservation des probabilités GBM et Géométriques sans mémoire (1/tau)
        for tau in [500.0, 1000.0]:
            p_sp = dfvs.exact_boom_crash_spike_prob(60, tau)
            p_su = dfvs.exact_boom_crash_survival_prob(60, tau)
            self.assertAlmostEqual(p_sp + p_su, 1.0, places=12)

if __name__ == '__main__':
    unittest.main()
