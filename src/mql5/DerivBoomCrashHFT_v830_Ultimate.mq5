//+------------------------------------------------------------------+

//|                                       DerivBoomCrashHFT_v8.mq5   |

//|         Quantitative Convex Spike Harvester (v8.30 INVERT)       |

//|         MÉTHODOLOGIE CHARLIE MUNGER (INVERT) V7 -> V8 :          |

//|         1. Rétro-Inversion de Polarité (SELL Crash / BUY Boom)   |

//|         2. Stop Temporel Analytique Strict (M* = 60 Ticks)       |

//|         3. Correction des 3 Bugs de Paralysie v8.20 (ONNX [1,1], |

//|            Suppression du Verrou theta_eff, Payoff Convexe Réel) |

//|         4. Sonde Périodique Haute Fréquence (15-20 Ticks Calmes) |

//+------------------------------------------------------------------+

#property copyright "Deriv Quantitative HFT Research — Munger Convex Inversion"

#property link      "https://github.com/Christ-yavn/bot-quant-"

#property version   "8.30"

#property description "v8.30 Ultimate Convex Spike Harvester: Synthesis of Argon Dynamic ONNX + Fable Static EV Gate + Hawkes Cluster Re-entry + CopyTicks Cursor."

#property strict



#resource "\\Files\\boom_crash_meta_brain.onnx" as uchar ExtColabOnnxBrain[]



enum ENUM_SYMBOL_UNIVERSE

{

   UNIVERSE_GOLDEN_5_V8_CONVEX    = 0, // Les 5 Indices Cibles V8 (Crash 600/900/1000, Boom 600/900)

   UNIVERSE_GOLDEN_7_LIVE_WINNERS = 1, // Les 7 Indices Golden (Crash 600/900/500/1000, Boom 500/900/600)

   UNIVERSE_CLASSIC_10            = 2, // Les 10 Classiques (300, 500, 600, 900, 1000)

   UNIVERSE_CURRENT_CHART_ONLY    = 3  // Uniquement le symbole du graphique actuel

};



//--- Input Parameters

input group "=== 1. Cerveau IA ONNX v8.30 (Corrigé [1,1] & Sans Paralysie) ==="

input bool   InpUseColabOnnxBrain           = true;     // Activer le Réseau ONNX (Auto-détection [1,1] ou [1,2])

input bool   InpOnnxOutputsSurvivalProb     = true;     // true = ONNX prédit P(Survie Dérive) -> inversé en P(Spike)=1-P

input bool   InpUseZeroCheatFeatures        = true;     // true = 14 variables sans triche (excès Poisson/Hawkes)

input double InpThetaEffBaseMult            = 0.90;     // Multiplicateur theta_eff (0.90 * base_p0 : 0 blocage abusif !)

input bool   InpEnforcePositivePayoffLock   = false;    // Verrou d'espérance (false = évite la paralysie analytique)

input double InpMinExpectedPayoffUsd        = -0.05;    // Seuil de payoff convexe minimal toléré ($)



input group "=== 1b. Porte EV Statique & Curseur Ticks (Fable Core) ==="
input bool   InpEnableStaticEvGate          = true;     // Pre-qualification statique d'EV a l'initialisation (OnInit)
input double InpMinEvUsd                    = 0.01;     // EV nette minimale exigee par sonde (USD)
input bool   InpUseCopyTicksCursor          = true;     // Consommation reelle du flux par curseur CopyTicks + dedup intra-ms
input int    InpMaxTicksPerScan             = 500;      // Plafond de ticks traites par scan

input group "=== 2. Moteur d'Entrée Inversé (SELL Crash / BUY Boom) ==="

input ENUM_SYMBOL_UNIVERSE InpSymbolUniverse = UNIVERSE_GOLDEN_5_V8_CONVEX; // Univers d'indices à surveiller

input bool   InpEnablePeriodicSpikeProbe    = true;     // Sonde périodique en dérive calme (Capture les 82+ spikes/jour)

input int    InpCalmDriftEntryTicks         = 18;       // Ticks calmes requis avant d'entrer (15-20 ticks = cadence optimale)

input bool   InpEnableHawkesClusterEntry    = true;     // Entrer aussi sur réplique de cluster Hawkes post-spike

input int    InpClusterReentryTicks         = 6;        // Ticks calmes après un 1er spike pour tenter la réplique (Hawkes)

input double InpMinHawkesForCluster         = 0.85;     // Intensité Hawkes rapide min pour déclencher une réplique

input int    InpMaxActiveSymbols            = 3;        // Max indices en position simultanément

input int    InpScannerTimerMs              = 50;       // Fréquence du scanner HFT (50 ms = 20x/sec)



input group "=== 3. Stop Temporel Analytique Strict (M* = 60 Ticks) & Risque Borné ==="

input int    InpMaxHoldCalmTicks            = 60;       // Stop Temporel M* en ticks calmes sans spike (ex: 60 ticks)

input int    InpMaxHoldCalmSeconds          = 65;       // Stop Temporel de sécurité en secondes (65s max sans spike)

input double InpMaxLossUsdPerTrade          = 0.35;     // Coupe-circuit monétaire strict par sonde (-0.35$ max)

input double InpServerHardSlUsd             = 1.20;     // Stop-Loss catastrophique serveur ($ d'écart max anti-déconnexion)

input double InpLotsPerProbe                = 0.0;      // Lots par sonde (0.0 = lot min Deriv 0.20)

input int    InpCooldownAfterTimeStop       = 15;       // Pause courte après un Time-Stop (15 ticks = relance la sonde)

input int    InpCooldownAfterSpikeWin       = 18;       // Pause après encaissement d'un Spike gagnant (18 ticks)



input group "=== 4. Encaissement Convexe des Spikes (+3.50$ à +15.00$) ==="

input bool   InpInstantCashInOnSpike        = false;    // true = Ferme au 1er tick du spike | false = Trailing post-spike

input int    InpPostSpikeGraceTicks         = 3;        // Ticks de grâce après un spike pour capter un double spike

input double InpPostSpikeTrailRetraceRatio  = 0.08;     // Rétrocession max tolérée sur le gain du spike (8% du pic)

input double InpMinSpikeProfitUsd           = 0.10;     // Profit net minimal ($) pour valider la clôture sur spike



input group "=== 5. Sécurité & Conformité Microstructure Deriv ==="

input bool   InpDemoAccountOnly             = false;    // true = Bloque sur compte réel | false = Autorise Démo & Réel

input double InpMaxDrawdownPct              = 10.0;     // Coupe-circuit Drawdown Max (%)

input double InpDailyLossPct                = 4.0;      // Coupe-circuit Perte Journalière Max (%)

input double InpMaxSpreadDriftMult          = 125.0;    // Plafond de Spread Réel en multiples de dérive

input ulong  InpMagicNumber                 = 20261020; // Magic Number v8.30 Convex

input bool   InpUseAsyncOrders              = true;     // Utiliser OrderSendAsync() avec verrou anti-spam

input bool   InpShowDashboard               = true;     // Afficher le tableau de bord télémétrique



//--- Structure de suivi par symbole (Architecture Convexe V8)

struct SymbolTracker

{

   string   name;

   int      symbol_id;

   bool     is_boom;

   double   abs_drift_per_tick;

   double   mean_spike_pts;

   double   mean_tau_ticks;

   double   spike_threshold;

   double   real_spread_pts;

   double   breakeven_ticks;

   double   sl_pts;

   double   lot_per_stage;

   string   calib_source;



   double   last_price;

   double   recent_prices[4];

   int      recent_prices_count;

   double   last_delta;

   double   last_spike_amp;

   long     last_time_msc;

   long     last_order_sent_msc;



   long     tick_counter;

   long     calm_drift_ticks;

   long     spikes_detected;

   long     probes_triggered;

   long     ai_filtered_count;

   double   last_spike_prob_p0;

   double   last_theta_eff;

   double   last_expected_payoff_usd;

   double   last_hawkes_fast;

   long     cooldown_until_tick;

   long     spike_history_ticks[32];

   double   spike_history_amps[32];

   int      spike_history_count;



   // Suivi de la position convexe ouverte

   int      open_positions;

   long     entry_tick_counter;

   long     entry_time_msc;

   int      spikes_while_open;

   long     last_open_spike_tick;

   double   peak_profit_usd;

   double   peak_favorable_pts;

   // Porte EV Statique a l'Init (Fable Core)
   bool     ev_gate_pass;
   double   ev_usd_est;
   double   loss_usd_est;
   double   gain_usd_est;

   // Curseur de Ticks & Debit Live (FIX-1 & FIX-2)
   int      last_ms_consumed;
   long     rate_window_start_msc;
   long     rate_window_start_tick;
   double   ticks_per_sec;

};



//--- Verrou d'idempotence asynchrone pour éviter les fermetures multiples du même ticket

struct ClosingTicketLock

{

   ulong    ticket;

   long     sent_msc;

};



SymbolTracker     g_trackers[];

int               g_num_trackers         = 0;

ClosingTicketLock g_closing_locks[64];

int               g_num_closing_locks    = 0;



long              g_onnx_handle          = INVALID_HANDLE;

bool              g_onnx_ready           = false;

int               g_onnx_output_count    = 0;

bool              g_onnx_scalar_1d       = false;

bool              g_emergency_stopped    = false;
long              g_current_day          = 0;
double            g_day_start_equity     = 0.0;



double            g_initial_equity       = 0.0;

double            g_peak_equity          = 0.0;

long              g_total_ticks_all      = 0;

long              g_total_spikes_all     = 0;

long              g_total_probes_all     = 0;

long              g_total_spikes_caught  = 0;

long              g_total_time_stops     = 0;

long              g_total_ai_blocked     = 0;



//+------------------------------------------------------------------+

//| Vérifie si un ticket est déjà en cours de fermeture asynchrone   |

//+------------------------------------------------------------------+

bool IsTicketClosingInFlight(ulong ticket)

{

   long now_msc = (long)GetTickCount64();

   for(int i = 0; i < g_num_closing_locks; i++)

   {

      if(g_closing_locks[i].ticket == ticket)

      {

         if(now_msc - g_closing_locks[i].sent_msc < 2500)

            return true;

         g_closing_locks[i].sent_msc = now_msc;

         return false;

      }

   }

   return false;

}



void MarkTicketClosingInFlight(ulong ticket)

{

   long now_msc = (long)GetTickCount64();

   for(int i = 0; i < g_num_closing_locks; i++)

   {

      if(g_closing_locks[i].ticket == ticket)

      {

         g_closing_locks[i].sent_msc = now_msc;

         return;

      }

   }

   if(g_num_closing_locks < 64)

   {

      g_closing_locks[g_num_closing_locks].ticket   = ticket;

      g_closing_locks[g_num_closing_locks].sent_msc = now_msc;

      g_num_closing_locks++;

   }

   else

   {

      for(int i = 0; i < 63; i++)

         g_closing_locks[i] = g_closing_locks[i+1];

      g_closing_locks[63].ticket   = ticket;

      g_closing_locks[63].sent_msc = now_msc;

   }

}



//+------------------------------------------------------------------+

//| Distance minimale réglementaire STOP_LEVEL / FREEZE_LEVEL (pts)  |

//+------------------------------------------------------------------+

double GetBrokerMinStopDistancePts(const string sym)

{

   double pt         = SymbolInfoDouble(sym, SYMBOL_POINT);

   long   stops_lvl  = SymbolInfoInteger(sym, SYMBOL_TRADE_STOPS_LEVEL);

   long   freeze_lvl = SymbolInfoInteger(sym, SYMBOL_TRADE_FREEZE_LEVEL);

   long   max_lvl    = MathMax(stops_lvl, freeze_lvl);

   return (double)(max_lvl + 6) * pt;

}



//+------------------------------------------------------------------+

//| Conversion Points -> Dollars ($) pour un volume donné            |

//+------------------------------------------------------------------+

double PointsToUsd(const string sym, double pts, double lot)

{

   double tick_val  = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_VALUE);

   double tick_size = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_SIZE);

   if(tick_val <= 0.0 || tick_size <= 0.0 || lot <= 0.0)

      return pts * lot;

   return pts * lot * (tick_val / tick_size);

}



//+------------------------------------------------------------------+

//| Calcule le Stop-Loss Serveur de sécurité catastrophique (pts)    |

//+------------------------------------------------------------------+

double ComputeCatastrophicServerSlPts(const string sym, double lot, double fallback_pts)

{

   double tick_val  = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_VALUE);

   double tick_size = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_SIZE);

   double min_dist  = GetBrokerMinStopDistancePts(sym);



   if(tick_val <= 0.0 || tick_size <= 0.0 || lot <= 0.0 || InpServerHardSlUsd <= 0.0)

      return MathMax(min_dist, fallback_pts);



   double usd_per_pt_per_lot = tick_val / tick_size;

   double max_pts_by_usd     = InpServerHardSlUsd / (lot * usd_per_pt_per_lot);

   return MathMax(min_dist, max_pts_by_usd);

}



//+------------------------------------------------------------------+

//| Initialisation du modèle ONNX avec Correctif Bug #1 (Code 5800)  |

//| Supporte dynamiquement la sortie scalaire [1,1] et le format     |

//| classifieur [1] + [1,2] sans jamais bloquer la session.          |

//+------------------------------------------------------------------+

bool InitColabOnnxBrain()

{

   g_onnx_ready        = false;

   g_onnx_handle       = INVALID_HANDLE;

   g_onnx_output_count = 0;

   g_onnx_scalar_1d    = false;



   if(!InpUseColabOnnxBrain)

      return false;



   g_onnx_handle = OnnxCreateFromBuffer(ExtColabOnnxBrain, ONNX_DEFAULT);

   if(g_onnx_handle == INVALID_HANDLE)

      g_onnx_handle = OnnxCreate("boom_crash_meta_brain.onnx", ONNX_DEFAULT);

   if(g_onnx_handle == INVALID_HANDLE)

   {

      PrintFormat("[DerivBoomCrashHFT v8.30] Fichier ONNX absent ou non chargé (err=%d) -> Mode Processus de Poisson + Hawkes Actif.", GetLastError());

      return false;

   }



   const long input_shape[] = {1, 14};

   if(!OnnxSetInputShape(g_onnx_handle, 0, input_shape))

   {

      PrintFormat("[DerivBoomCrashHFT v8.30] Erreur OnnxSetInputShape [1,14] (err=%d) -> Repli Poisson + Hawkes.", GetLastError());

      OnnxRelease(g_onnx_handle);

      g_onnx_handle = INVALID_HANDLE;

      return false;

   }



   g_onnx_output_count = (int)OnnxGetOutputCount(g_onnx_handle);



   if(g_onnx_output_count == 1)

   {

      // Correctif Bug #1 (Erreur MT5 5800) : Le modèle exporté a 1 seule sortie scalaire [1, 1]

      const long out_shape_2d[] = {1, 1};

      if(!OnnxSetOutputShape(g_onnx_handle, 0, out_shape_2d))

      {

         const long out_shape_1d[] = {1};

         if(!OnnxSetOutputShape(g_onnx_handle, 0, out_shape_1d))

         {

            PrintFormat("[DerivBoomCrashHFT v8.30] Erreur OnnxSetOutputShape [1,1] (err=%d) -> Repli Poisson.", GetLastError());

            OnnxRelease(g_onnx_handle);

            g_onnx_handle = INVALID_HANDLE;

            return false;

         }

         g_onnx_scalar_1d = true;

      }

      g_onnx_ready = true;

      Print("[DerivBoomCrashHFT v8.30] >>> CERVEAU ONNX SCALAIRE [1, 1] INITIALISÉ SANS ERREUR 5800 ! <<<");

      return true;

   }

   else if(g_onnx_output_count >= 2)

   {

      const long output_label[] = {1};

      const long output_proba[] = {1, 2};

      OnnxSetOutputShape(g_onnx_handle, 0, output_label);

      OnnxSetOutputShape(g_onnx_handle, 1, output_proba);

      g_onnx_ready = true;

      Print("[DerivBoomCrashHFT v8.30] >>> CERVEAU ONNX DUAL-OUTPUT [1, 2] INITIALISÉ ! <<<");

      return true;

   }



   OnnxRelease(g_onnx_handle);

   g_onnx_handle = INVALID_HANDLE;

   return false;

}



//+------------------------------------------------------------------+

//| Évaluation de la probabilité de Spike dans la fenêtre M* = 60t   |

//| Corrigée des Bugs #2 (theta_eff) et #3 (expected_payoff)         |

//+------------------------------------------------------------------+

double EvaluateConvexSpikeProbability(SymbolTracker &tr, int &out_c60)

{

   double mean_sp  = MathMax(tr.mean_spike_pts, 1e-6);

   double mean_tau = MathMax(tr.mean_tau_ticks, 1.0);

   double drift    = MathMax(tr.abs_drift_per_tick, 1e-8);

   double horizon  = (double)MathMax(10, InpMaxHoldCalmTicks);



   // 1. Probabilité de base analytique de Poisson sur l'horizon M* = 60 ticks :

   //    p0_base = 1 - exp(-M* / tau)  (ex: Crash 600 -> 1 - exp(-60/571.5) = 9.97%)

   double base_p0 = 1.0 - MathExp(-horizon / mean_tau);



   double tau1 = 1.0, tau2 = 1.0, tau3 = 1.0;

   int n = tr.spike_history_count;

   if(n >= 2)

      tau1 = (double)(tr.spike_history_ticks[n-1] - tr.spike_history_ticks[n-2]) / mean_tau;

   if(n >= 3)

      tau2 = (double)(tr.spike_history_ticks[n-2] - tr.spike_history_ticks[n-3]) / mean_tau;

   if(n >= 4)

      tau3 = (double)(tr.spike_history_ticks[n-3] - tr.spike_history_ticks[n-4]) / mean_tau;



   double h_fast = 0.0, h_med = 0.0, h_slow = 0.0;

   int c60 = 0, c300 = 0;



   for(int i = 0; i < n; i++)

   {

      double lag = (double)(tr.tick_counter - tr.spike_history_ticks[i]);

      if(lag < 0.0) lag = 0.0;

      double amp_n = tr.spike_history_amps[i] / mean_sp;

      h_fast += amp_n * MathExp(-0.05  * lag);

      h_med  += amp_n * MathExp(-0.015 * lag);

      h_slow += amp_n * MathExp(-0.003 * lag);



      if(lag <= 60.0)  c60++;

      if(lag <= 300.0) c300++;

   }



   tr.last_hawkes_fast = h_fast;

   out_c60             = c60;



   // Facteur d'intensité combiné (Hawkes auto-excitant + maturation de dérive calme)

   double calm_maturity_boost = 1.0 + 0.15 * MathMin(2.0, (double)tr.calm_drift_ticks / mean_tau);

   double hawkes_boost        = 1.0 + 0.25 * MathMax(0.0, h_fast - 0.50);

   double phys_spike_p0       = 1.0 - MathExp(-(horizon / mean_tau) * calm_maturity_boost * hawkes_boost);

   phys_spike_p0              = MathMax(base_p0, MathMin(0.95, phys_spike_p0));



   // Correctif Bug #2 : theta_eff est inférieur ou égal à base_p0 (par défaut 0.90 * base_p0)

   // de sorte qu'en régime de Poisson normal, phys_spike_p0 >= theta_eff est TOUJOURS vrai !

   tr.last_theta_eff = InpThetaEffBaseMult * base_p0;



   double spike_prob = phys_spike_p0;



   if(g_onnx_ready && g_onnx_handle != INVALID_HANDLE)

   {

      double post3_vel = 1.0;

      if(tr.recent_prices_count >= 4)

      {

         double move3 = tr.is_boom ? (tr.recent_prices[0] - tr.recent_prices[3]) : (tr.recent_prices[3] - tr.recent_prices[0]);

         post3_vel = move3 / (3.0 * drift);

         post3_vel = MathMax(-2.0, MathMin(2.5, post3_vel));

      }



      double be_ticks       = tr.real_spread_pts / drift;

      double cost_ratio     = be_ticks / mean_tau;

      double spike_amp_norm = (tr.last_spike_amp > 0.0) ? (tr.last_spike_amp / mean_sp) : 1.0;



      float x[1][14];

      if(InpUseZeroCheatFeatures)

      {

         double e_h_fast   = MathExp(-0.05  * 3.0) + 1.0 / (0.05  * mean_tau);

         double e_h_med    = MathExp(-0.015 * 3.0) + 1.0 / (0.015 * mean_tau);

         double e_h_slow   = MathExp(-0.003 * 3.0) + 1.0 / (0.003 * mean_tau);

         double h_fast_exc = h_fast - e_h_fast;

         double h_med_exc  = h_med  - e_h_med;

         double h_slow_exc = h_slow - e_h_slow;

         double c60_exc    = (double)MathMax(1, c60)  - (1.0 + 60.0  / mean_tau);

         double c300_exc   = (double)MathMax(1, c300) - (1.0 + 300.0 / mean_tau);



         x[0][0]  = (float)(tau1 / (tau2 + 0.10));

         x[0][1]  = (float)(h_fast_exc - h_med_exc);

         x[0][2]  = (float)spike_amp_norm;

         x[0][3]  = (float)tau1;

         x[0][4]  = (float)tau2;

         x[0][5]  = (float)tau3;

         x[0][6]  = (float)h_fast_exc;

         x[0][7]  = (float)h_med_exc;

         x[0][8]  = (float)h_slow_exc;

         x[0][9]  = (float)c60_exc;

         x[0][10] = (float)c300_exc;

         x[0][11] = (float)post3_vel;

         x[0][12] = (float)(h_med_exc - h_slow_exc);

         x[0][13] = (float)((spike_amp_norm - 1.0) * h_fast_exc);

      }

      else

      {

         x[0][0]  = (float)tr.symbol_id;

         x[0][1]  = tr.is_boom ? 1.0f : 0.0f;

         x[0][2]  = (float)spike_amp_norm;

         x[0][3]  = (float)tau1;

         x[0][4]  = (float)tau2;

         x[0][5]  = (float)tau3;

         x[0][6]  = (float)h_fast;

         x[0][7]  = (float)h_med;

         x[0][8]  = (float)h_slow;

         x[0][9]  = (float)MathMax(1, c60);

         x[0][10] = (float)MathMax(1, c300);

         x[0][11] = (float)post3_vel;

         x[0][12] = (float)be_ticks;

         x[0][13] = (float)cost_ratio;

      }



      double raw_onnx = -1.0;

      if(g_onnx_output_count == 1)

      {

         if(g_onnx_scalar_1d)

         {

            float out_1d[1];

            if(OnnxRun(g_onnx_handle, ONNX_NO_CONVERSION, x, out_1d))

               raw_onnx = (double)out_1d[0];

         }

         else

         {

            float out_2d[1][1];

            if(OnnxRun(g_onnx_handle, ONNX_NO_CONVERSION, x, out_2d))

               raw_onnx = (double)out_2d[0][0];

         }

      }

      else if(g_onnx_output_count >= 2)

      {

         long  out_label[1];

         float out_proba[1][2];

         if(OnnxRun(g_onnx_handle, ONNX_NO_CONVERSION, x, out_label, out_proba))

            raw_onnx = (double)out_proba[0][1];

      }



      if(raw_onnx >= 0.0 && raw_onnx <= 1.0)

      {

         // Si le modèle ONNX sort P(Survie sans spike ~ 0.815), l'inversion donne P(Spike) = 1 - P(Survie)

         double onnx_spike_p = InpOnnxOutputsSurvivalProb ? (1.0 - raw_onnx) : raw_onnx;

         // Fusion Bayésienne prudente : ne jamais descendre sous la probabilité physique de Poisson

         spike_prob = MathMax(phys_spike_p0, 0.50 * phys_spike_p0 + 0.50 * onnx_spike_p);

      }

   }



   // Correctif Bug #3 : Équation d'espérance convexe réelle (en USD)

   // Gain moyen si Spike dans les M* ticks : E[Gain_USD] = PointsToUsd(mean_spike_pts - 0.5*horizon*drift - spread)

   // Perte bornée si Time-Stop à M* ticks  : E[Loss_USD] = min(InpMaxLossUsdPerTrade, PointsToUsd(horizon*drift))

   double net_spike_pts = MathMax(0.20 * mean_sp, mean_sp - 0.5 * horizon * drift - tr.real_spread_pts);

   double win_usd       = PointsToUsd(tr.name, net_spike_pts, tr.lot_per_stage);

   double loss_usd      = MathMin(InpMaxLossUsdPerTrade, PointsToUsd(tr.name, horizon * drift, tr.lot_per_stage));



   // Espérance mathématique par sonde : E[Payoff] = p0 * Win_USD - (1 - p0) * Loss_USD

   tr.last_expected_payoff_usd = spike_prob * win_usd - (1.0 - spike_prob) * loss_usd;

   tr.last_spike_prob_p0       = spike_prob;



   return spike_prob;

}



ENUM_ORDER_TYPE_FILLING GetSupportedFillingMode(const string sym)

{

   uint filling = (uint)SymbolInfoInteger(sym, SYMBOL_FILLING_MODE);

   if((filling & SYMBOL_FILLING_FOK) != 0)

      return ORDER_FILLING_FOK;

   if((filling & SYMBOL_FILLING_IOC) != 0)

      return ORDER_FILLING_IOC;

   return ORDER_FILLING_RETURN;

}



//+------------------------------------------------------------------+

//| Calibration initiale sur 5 000 ticks                             |

//+------------------------------------------------------------------+

//+------------------------------------------------------------------+
//| Porte d'Esperance Mathematique Statique a l'Init (Fable Core)    |
//| Evaluee une seule fois par symbole au demarrage avec les vraies  |
//| valeurs de contrat MT5 (TICK_VALUE, TICK_SIZE, SPREAD live).     |
//+------------------------------------------------------------------+
void ComputeSymbolEvGate(SymbolTracker &tr, const string sym)
{
   double tick_val  = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_VALUE);
   double tick_size = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_SIZE);
   if(tick_size <= 0.0) tick_size = SymbolInfoDouble(sym, SYMBOL_POINT);
   if(tick_val <= 0.0)  tick_val  = 1.0;

   double lot = (tr.lot_per_stage > 0.0) ? tr.lot_per_stage : 0.20;
   double usd_per_pt = (tick_val / tick_size) * lot;
   double M          = (double)InpMaxHoldCalmTicks;
   double p0         = 1.0 - MathExp(-M / MathMax(tr.mean_tau_ticks, 1.0));

   double L_pts = M * tr.abs_drift_per_tick + tr.real_spread_pts;
   double G_pts = MathMax(0.0, tr.mean_spike_pts - tr.real_spread_pts);

   tr.loss_usd_est = L_pts * usd_per_pt;
   tr.gain_usd_est = G_pts * usd_per_pt;
   tr.ev_usd_est   = p0 * tr.gain_usd_est - (1.0 - p0) * tr.loss_usd_est;

   tr.ev_gate_pass = (!InpEnableStaticEvGate) || (tr.ev_usd_est >= InpMinEvUsd);

   PrintFormat("[DerivBoomCrashHFT v8.30 EV GATE] %s : p0(60t)=%.2f%% | Gain~+%.2f$ | Perte~-%.2f$ | EV=%.4f$ -> %s",
               tr.name, p0 * 100.0, tr.gain_usd_est, tr.loss_usd_est, tr.ev_usd_est,
               tr.ev_gate_pass ? "VALIDE (Trade Autorise)" : "REFUSE (EV Insuffisante)");
}

void InitAndCalibrateTracker(SymbolTracker &tr, const string sym)

{

   tr.name                     = sym;

   string s                    = sym;

   StringToLower(s);

   tr.is_boom                  = (StringFind(s, "boom") >= 0);

   tr.symbol_id                = 0;

   tr.last_price               = 0.0;

   tr.recent_prices_count      = 0;

   tr.last_delta               = 0.0;

   tr.last_spike_amp           = 0.0;

   tr.last_time_msc            = 0;

   tr.last_order_sent_msc      = 0;

   tr.tick_counter             = 0;

   tr.calm_drift_ticks         = 0;

   tr.spikes_detected          = 0;

   tr.probes_triggered         = 0;

   tr.ai_filtered_count        = 0;

   tr.last_spike_prob_p0       = 0.0;

   tr.last_theta_eff           = 0.0;

   tr.last_expected_payoff_usd = 0.0;

   tr.last_hawkes_fast         = 0.0;

   tr.cooldown_until_tick      = 0;

   tr.spike_history_count      = 0;



   tr.open_positions           = 0;

   tr.entry_tick_counter       = 0;

   tr.entry_time_msc           = 0;

   tr.spikes_while_open        = 0;

   tr.last_open_spike_tick     = 0;

   tr.peak_profit_usd          = -1e9;

   tr.peak_favorable_pts       = 0.0;



   for(int r = 0; r < 4; r++)

      tr.recent_prices[r] = 0.0;



   for(int k = 0; k < 32; k++)

   {

      tr.spike_history_ticks[k] = -100000;

      tr.spike_history_amps[k]  = 0.0;

   }



   double vol_min  = SymbolInfoDouble(sym, SYMBOL_VOLUME_MIN);

   double vol_max  = SymbolInfoDouble(sym, SYMBOL_VOLUME_MAX);

   double vol_step = SymbolInfoDouble(sym, SYMBOL_VOLUME_STEP);

   if(vol_min <= 0.0)  vol_min  = 0.20;

   if(vol_step <= 0.0) vol_step = 0.01;



   if(InpLotsPerProbe <= 0.0)

      tr.lot_per_stage = vol_min;

   else

   {

      double clamped = MathMax(vol_min, MathMin(vol_max, InpLotsPerProbe));

      tr.lot_per_stage = MathFloor(clamped / vol_step + 1e-9) * vol_step;

   }



   tr.abs_drift_per_tick = 0.01622;

   tr.mean_spike_pts     = 17.015;

   tr.mean_tau_ticks     = 1000.0;

   tr.calib_source       = "TABLE_V8";



   if(StringFind(s, "boom 1000") >= 0)       { tr.symbol_id = 0; tr.abs_drift_per_tick = 0.01551; tr.mean_spike_pts = 17.015; tr.mean_tau_ticks = 1066.6; }

   else if(StringFind(s, "crash 1000") >= 0) { tr.symbol_id = 1; tr.abs_drift_per_tick = 0.00636; tr.mean_spike_pts = 5.887;  tr.mean_tau_ticks = 961.0;  }

   else if(StringFind(s, "boom 900") >= 0)   { tr.symbol_id = 2; tr.abs_drift_per_tick = 0.00972; tr.mean_spike_pts = 8.865;  tr.mean_tau_ticks = 911.4;  }

   else if(StringFind(s, "crash 900") >= 0)  { tr.symbol_id = 3; tr.abs_drift_per_tick = 0.01900; tr.mean_spike_pts = 17.314; tr.mean_tau_ticks = 907.3;  }

   else if(StringFind(s, "boom 600") >= 0)   { tr.symbol_id = 4; tr.abs_drift_per_tick = 0.00894; tr.mean_spike_pts = 5.155;  tr.mean_tau_ticks = 586.5;  }

   else if(StringFind(s, "crash 600") >= 0)  { tr.symbol_id = 5; tr.abs_drift_per_tick = 0.03773; tr.mean_spike_pts = 22.904; tr.mean_tau_ticks = 571.5;  }

   else if(StringFind(s, "boom 500") >= 0)   { tr.symbol_id = 6; tr.abs_drift_per_tick = 0.01128; tr.mean_spike_pts = 5.825;  tr.mean_tau_ticks = 486.9;  }

   else if(StringFind(s, "crash 500") >= 0)  { tr.symbol_id = 7; tr.abs_drift_per_tick = 0.00623; tr.mean_spike_pts = 2.991;  tr.mean_tau_ticks = 480.0;  }

   else if(StringFind(s, "boom 300") >= 0)   { tr.symbol_id = 8; tr.abs_drift_per_tick = 0.00414; tr.mean_spike_pts = 1.324;  tr.mean_tau_ticks = 289.3;  }

   else if(StringFind(s, "crash 300") >= 0)  { tr.symbol_id = 9; tr.abs_drift_per_tick = 0.02080; tr.mean_spike_pts = 6.863;  tr.mean_tau_ticks = 297.3;  }



   tr.last_spike_amp = tr.mean_spike_pts;



   MqlTick ticks[];

   int copied = CopyTicks(sym, ticks, COPY_TICKS_ALL, 0, 5000);

   if(copied > 200)

   {

      double sum_drift = 0.0;

      int    cnt_drift = 0;

      for(int i = 1; i < copied; i++)

      {

         double p0 = (ticks[i-1].last > 0.0) ? ticks[i-1].last : 0.5 * (ticks[i-1].bid + ticks[i-1].ask);

         double p1 = (ticks[i].last > 0.0)   ? ticks[i].last   : 0.5 * (ticks[i].bid + ticks[i].ask);

         double d  = p1 - p0;

         if((tr.is_boom && d < 0.0) || (!tr.is_boom && d > 0.0))

         {

            sum_drift += MathAbs(d);

            cnt_drift++;

         }

      }

      if(cnt_drift > 100)

      {

         double live_drift = sum_drift / cnt_drift;

         double sum_spike  = 0.0;

         int    cnt_spike  = 0;

         int    last_sp_i  = 0;

         for(int i = 1; i < copied; i++)

         {

            double p0 = (ticks[i-1].last > 0.0) ? ticks[i-1].last : 0.5 * (ticks[i-1].bid + ticks[i-1].ask);

            double p1 = (ticks[i].last > 0.0)   ? ticks[i].last   : 0.5 * (ticks[i].bid + ticks[i].ask);

            double d  = p1 - p0;

            if((tr.is_boom && d > 3.5 * live_drift) || (!tr.is_boom && d < -3.5 * live_drift))

            {

               sum_spike += MathAbs(d);

               cnt_spike++;

               last_sp_i = i;

               tr.last_spike_amp = MathAbs(d);



               long rel_tick = (long)(i - copied);

               if(tr.spike_history_count < 32)

               {

                  tr.spike_history_ticks[tr.spike_history_count] = rel_tick;

                  tr.spike_history_amps[tr.spike_history_count]  = MathAbs(d);

                  tr.spike_history_count++;

               }

               else

               {

                  for(int m = 0; m < 31; m++)

                  {

                     tr.spike_history_ticks[m] = tr.spike_history_ticks[m+1];

                     tr.spike_history_amps[m]  = tr.spike_history_amps[m+1];

                  }

                  tr.spike_history_ticks[31] = rel_tick;

                  tr.spike_history_amps[31]  = MathAbs(d);

               }

            }

         }

         tr.abs_drift_per_tick = live_drift;

         tr.calm_drift_ticks   = (long)(copied - 1 - last_sp_i);

         if(cnt_spike >= 3)

         {

            tr.mean_spike_pts = sum_spike / cnt_spike;

            tr.calib_source   = "LIVE_5K_V8";

         }

      }

      for(int r = 0; r < 4; r++)

      {

         int idx = copied - 4 + r;

         tr.recent_prices[r] = (ticks[idx].last > 0.0) ? ticks[idx].last : 0.5 * (ticks[idx].bid + ticks[idx].ask);

      }

      tr.recent_prices_count = 4;

   }



   MqlTick live_t;

   if(SymbolInfoTick(sym, live_t) && live_t.ask > live_t.bid)

      tr.real_spread_pts = live_t.ask - live_t.bid;

   else

      tr.real_spread_pts = 20.0 * tr.abs_drift_per_tick;



   tr.breakeven_ticks = tr.real_spread_pts / MathMax(tr.abs_drift_per_tick, 1e-8);

   tr.spike_threshold = MathMax(3.5 * tr.abs_drift_per_tick, 0.25 * tr.mean_spike_pts);

   tr.last_ms_consumed       = 0;
   tr.rate_window_start_msc  = 0;
   tr.rate_window_start_tick = 0;
   tr.ticks_per_sec          = 0.0;

   ComputeSymbolEvGate(tr, sym);

   tr.sl_pts          = ComputeCatastrophicServerSlPts(sym, tr.lot_per_stage, 180.0 * tr.abs_drift_per_tick);



   int dummy_c60 = 0;

   EvaluateConvexSpikeProbability(tr, dummy_c60);

}



bool AddSymbolToScanner(const string sym)

{

   for(int i = 0; i < g_num_trackers; i++)

      if(g_trackers[i].name == sym)

         return true;



   if(!SymbolSelect(sym, true))

      return false;



   MqlTick t;

   SymbolInfoTick(sym, t);



   ArrayResize(g_trackers, g_num_trackers + 1);

   InitAndCalibrateTracker(g_trackers[g_num_trackers], sym);

   g_num_trackers++;

   return true;

}



void BuildSymbolUniverse()

{

   ArrayResize(g_trackers, 0);

   g_num_trackers = 0;



   if(InpSymbolUniverse == UNIVERSE_CURRENT_CHART_ONLY)

   {

      AddSymbolToScanner(_Symbol);

      return;

   }



   if(InpSymbolUniverse == UNIVERSE_GOLDEN_5_V8_CONVEX)

   {

      string golden5[] = {

         "Crash 600 Index",

         "Crash 900 Index",

         "Boom 900 Index",

         "Boom 600 Index",

         "Crash 1000 Index"

      };

      for(int i = 0; i < ArraySize(golden5); i++)

         AddSymbolToScanner(golden5[i]);

      return;

   }



   if(InpSymbolUniverse == UNIVERSE_GOLDEN_7_LIVE_WINNERS)

   {

      string golden7[] = {

         "Crash 600 Index",

         "Boom 500 Index",

         "Crash 900 Index",

         "Boom 900 Index",

         "Boom 600 Index",

         "Crash 500 Index",

         "Crash 1000 Index"

      };

      for(int i = 0; i < ArraySize(golden7); i++)

         AddSymbolToScanner(golden7[i]);

      return;

   }



   string classic10[] = {

      "Boom 1000 Index", "Crash 1000 Index",

      "Boom 900 Index",  "Crash 900 Index",

      "Boom 600 Index",  "Crash 600 Index",

      "Boom 500 Index",  "Crash 500 Index",

      "Boom 300 Index",  "Crash 300 Index"

   };

   for(int i = 0; i < ArraySize(classic10); i++)

      AddSymbolToScanner(classic10[i]);

}



int OnInit()

{

   long trade_mode = AccountInfoInteger(ACCOUNT_TRADE_MODE);

   if(InpDemoAccountOnly && trade_mode == ACCOUNT_TRADE_MODE_REAL)

   {

      Alert("[DerivBoomCrashHFT v8.30] VERROU SÉCURITÉ : Compte Réel détecté (InpDemoAccountOnly=true).");

      return(INIT_FAILED);

   }



   InitColabOnnxBrain();

   BuildSymbolUniverse();



   g_initial_equity = AccountInfoDouble(ACCOUNT_EQUITY);

   g_peak_equity    = g_initial_equity;



   EventSetMillisecondTimer(MathMax(25, InpScannerTimerMs));

   PrintFormat("[DerivBoomCrashHFT v8.30 INVERT] Prêt sur %d indices | Polarité=CONVEXE (SELL Crash / BUY Boom) | TimeStop M*=%dt | MaxLoss=%.2f$ | ONNX=%s",

               g_num_trackers, InpMaxHoldCalmTicks, InpMaxLossUsdPerTrade, g_onnx_ready ? "ACTIF [1,1]" : "POISSON_HAWKES");

   return(INIT_SUCCEEDED);

}



void OnDeinit(const int reason)

{

   EventKillTimer();

   if(g_onnx_handle != INVALID_HANDLE)

   {

      OnnxRelease(g_onnx_handle);

      g_onnx_handle = INVALID_HANDLE;

   }

   if(InpShowDashboard)

      Comment("");

}



//+------------------------------------------------------------------+

//| Fermeture idempotente d'une position (1 seul envoi par ticket)   |

//+------------------------------------------------------------------+

bool CloseSinglePositionTicket(ulong ticket, const string sym, ENUM_POSITION_TYPE ptype, double volume, const string reason)

{

   if(IsTicketClosingInFlight(ticket))

      return false;



   MqlTick tick;

   if(!SymbolInfoTick(sym, tick))

      return false;



   MqlTradeRequest req;

   MqlTradeResult  res;

   ZeroMemory(req);

   ZeroMemory(res);



   req.action       = TRADE_ACTION_DEAL;

   req.position     = ticket;

   req.symbol       = sym;

   req.volume       = volume;

   req.magic        = InpMagicNumber;

   req.deviation    = 50;

   req.type_filling = GetSupportedFillingMode(sym);

   req.comment      = reason;



   if(ptype == POSITION_TYPE_BUY)

   {

      req.type  = ORDER_TYPE_SELL;

      req.price = tick.bid;

   }

   else

   {

      req.type  = ORDER_TYPE_BUY;

      req.price = tick.ask;

   }



   MarkTicketClosingInFlight(ticket);

   if(InpUseAsyncOrders)

      return OrderSendAsync(req, res);

   return OrderSend(req, res);

}



//+------------------------------------------------------------------+

//| Gestion Convexe des Positions Ouvertes (V8.30 INVERT) :          |

//| 1) Encaissement Explosif de Spike (+3.50$ à +15.00$)             |

//| 2) Stop Temporel Analytique Strict à M* = 60 Ticks (~ -0.20$)    |

//| 3) Coupe-circuit Monétaire Strict (InpMaxLossUsdPerTrade)        |

//+------------------------------------------------------------------+

int ManageConvexPositions()

{

   for(int i = 0; i < g_num_trackers; i++)

      g_trackers[i].open_positions = 0;



   long now_msc = (long)GetTickCount64();

   int  total   = PositionsTotal();



   for(int p = total - 1; p >= 0; p--)

   {

      ulong ticket = PositionGetTicket(p);

      if(ticket == 0) continue;

      if((ulong)PositionGetInteger(POSITION_MAGIC) != InpMagicNumber) continue;



      string psym              = PositionGetString(POSITION_SYMBOL);

      double profit_usd        = PositionGetDouble(POSITION_PROFIT) + PositionGetDouble(POSITION_SWAP);

      double open_price        = PositionGetDouble(POSITION_PRICE_OPEN);

      double cur_price         = PositionGetDouble(POSITION_PRICE_CURRENT);

      double volume            = PositionGetDouble(POSITION_VOLUME);

      long   pos_time_msc      = PositionGetInteger(POSITION_TIME_MSC);

      ENUM_POSITION_TYPE ptype = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);



      int tr_idx = -1;

      for(int i = 0; i < g_num_trackers; i++)

      {

         if(g_trackers[i].name == psym)

         {

            tr_idx = i;

            break;

         }

      }

      if(tr_idx < 0) continue;



      g_trackers[tr_idx].open_positions++;

      SymbolTracker tr = g_trackers[tr_idx];



      // En polarité inversée V8 : BUY sur Boom (gagne si cur_price > open_price), SELL sur Crash (gagne si open_price > cur_price)

      double favorable_pts = (ptype == POSITION_TYPE_BUY) ? (cur_price - open_price) : (open_price - cur_price);



      if(profit_usd > g_trackers[tr_idx].peak_profit_usd)

         g_trackers[tr_idx].peak_profit_usd = profit_usd;

      if(favorable_pts > g_trackers[tr_idx].peak_favorable_pts)

         g_trackers[tr_idx].peak_favorable_pts = favorable_pts;



      // Détection directe d'un spike favorable par excursion de prix (sécurité même si le tick a sauté)

      if(favorable_pts >= 0.80 * tr.spike_threshold && g_trackers[tr_idx].spikes_while_open == 0)

      {

         g_trackers[tr_idx].spikes_while_open    = 1;

         g_trackers[tr_idx].last_open_spike_tick = tr.tick_counter;

      }



      // --- 1. ENCAISSEMENT CONVEXE D'UN SPIKE CAPTURÉ (+3.50$ à +15.00$) ---

      if(g_trackers[tr_idx].spikes_while_open > 0 && profit_usd >= InpMinSpikeProfitUsd)

      {

         long ticks_since_spike = tr.tick_counter - g_trackers[tr_idx].last_open_spike_tick;

         bool retrace_triggered = (g_trackers[tr_idx].peak_profit_usd > InpMinSpikeProfitUsd &&

                                   profit_usd <= g_trackers[tr_idx].peak_profit_usd * (1.0 - InpPostSpikeTrailRetraceRatio));



         if(InpInstantCashInOnSpike || ticks_since_spike >= InpPostSpikeGraceTicks || retrace_triggered)

         {

            if(CloseSinglePositionTicket(ticket, psym, ptype, volume, "V8_SPIKE_JACKPOT"))

            {

               g_total_spikes_caught++;

               PrintFormat("[DerivBoomCrashHFT v8.30] $$$ SPIKE CONVEXE ENCAISSÉ sur %s : +%.2f USD (Pic=+%.2f$ | GainPts=+%.2f pts | Spikes=%d) $$$",

                           psym, profit_usd, g_trackers[tr_idx].peak_profit_usd, favorable_pts, g_trackers[tr_idx].spikes_while_open);

               g_trackers[tr_idx].cooldown_until_tick = g_trackers[tr_idx].tick_counter + InpCooldownAfterSpikeWin;

               continue;

            }

         }

      }



      // --- 2. STOP TEMPOREL ANALYTIQUE STRICT (M* = 60 TICKS SANS SPIKE) ---

      long ticks_held   = (tr.entry_tick_counter > 0) ? (tr.tick_counter - tr.entry_tick_counter) : 0;

      long elapsed_sec  = (pos_time_msc > 0 && now_msc > pos_time_msc) ? ((now_msc - pos_time_msc) / 1000) : 0;

      bool m60_expired  = (ticks_held >= InpMaxHoldCalmTicks) ||

                          (InpMaxHoldCalmSeconds > 0 && elapsed_sec >= InpMaxHoldCalmSeconds);



      if(g_trackers[tr_idx].spikes_while_open == 0 && m60_expired)

      {

         if(CloseSinglePositionTicket(ticket, psym, ptype, volume, "V8_TIME_STOP_M60"))

         {

            g_total_time_stops++;

            PrintFormat("[DerivBoomCrashHFT v8.30] STOP TEMPOREL M*=%dt sur %s : %.2f USD (Dérive bornée après %d ticks / %ds)",

                        InpMaxHoldCalmTicks, psym, profit_usd, (int)ticks_held, (int)elapsed_sec);

            g_trackers[tr_idx].cooldown_until_tick = g_trackers[tr_idx].tick_counter + InpCooldownAfterTimeStop;

            continue;

         }

      }



      // --- 3. PLAFOND MONÉTAIRE STRICT PAR SONDE (-0.35$ MAX) ---

      if(InpMaxLossUsdPerTrade > 0.0 && g_trackers[tr_idx].spikes_while_open == 0 && profit_usd <= -InpMaxLossUsdPerTrade)

      {

         if(CloseSinglePositionTicket(ticket, psym, ptype, volume, "V8_MAX_USD_PROBE_CUT"))

         {

            g_total_time_stops++;

            PrintFormat("[DerivBoomCrashHFT v8.30] COUPE-CIRCUIT MONÉTAIRE SONDE (%.2f USD <= -%.2f$) sur %s",

                        profit_usd, InpMaxLossUsdPerTrade, psym);

            g_trackers[tr_idx].cooldown_until_tick = g_trackers[tr_idx].tick_counter + InpCooldownAfterTimeStop;

            continue;

         }

      }

   }



   int active_symbols = 0;

   for(int i = 0; i < g_num_trackers; i++)

   {

      if(g_trackers[i].open_positions > 0)

         active_symbols++;

      else

      {

         g_trackers[i].spikes_while_open  = 0;

         g_trackers[i].peak_profit_usd    = -1e9;

         g_trackers[i].peak_favorable_pts = 0.0;

      }

   }

   return active_symbols;

}



//+------------------------------------------------------------------+

//| Ouverture d'une Sonde Convexe Inversée (SELL Crash / BUY Boom)   |

//+------------------------------------------------------------------+

bool OpenConvexSpikeProbe(SymbolTracker &tr, const MqlTick &tick, bool is_cluster_probe)

{

   if(tr.open_positions > 0 || (tick.time_msc - tr.last_order_sent_msc) < 3500)

      return false;



   if(!(bool)TerminalInfoInteger(TERMINAL_TRADE_ALLOWED) || !(bool)MQLInfoInteger(MQL_TRADE_ALLOWED))

      return false;



   double spread = tick.ask - tick.bid;

   tr.real_spread_pts = spread;

   tr.breakeven_ticks = spread / MathMax(tr.abs_drift_per_tick, 1e-8);



   if(tr.breakeven_ticks > InpMaxSpreadDriftMult)

      return false;



   int c60 = 0;

   double spike_p0 = EvaluateConvexSpikeProbability(tr, c60);



   // Correctif Bug #2 : Comparaison non-bloquante (spike_p0 >= theta_eff où theta_eff = 0.90 * base_p0)

   if(spike_p0 < tr.last_theta_eff)

   {

      tr.ai_filtered_count++;

      g_total_ai_blocked++;

      return false;

   }



   // Correctif Bug #3 : Le verrou d'espérance est désactivé par défaut ou calibré sur le vrai payoff convexe

   if(InpEnforcePositivePayoffLock && tr.last_expected_payoff_usd < InpMinExpectedPayoffUsd)

   {

      tr.ai_filtered_count++;

      g_total_ai_blocked++;

      return false;

   }



   // Verrouille l'horodatage avant l'envoi pour éviter tout spam serveur

   tr.last_order_sent_msc = tick.time_msc;



   int digits = (int)SymbolInfoInteger(tr.name, SYMBOL_DIGITS);

   ENUM_ORDER_TYPE_FILLING fill_mode = GetSupportedFillingMode(tr.name);

   double server_sl_pts = ComputeCatastrophicServerSlPts(tr.name, tr.lot_per_stage, 180.0 * tr.abs_drift_per_tick);

   tr.sl_pts = server_sl_pts;



   MqlTradeRequest req;

   MqlTradeResult  res;

   ZeroMemory(req);

   ZeroMemory(res);



   req.action       = TRADE_ACTION_DEAL;

   req.symbol       = tr.name;

   req.volume       = tr.lot_per_stage;

   req.magic        = InpMagicNumber;

   req.deviation    = 50;

   req.type_filling = fill_mode;

   req.comment      = is_cluster_probe ? "V8_CONVEX_HAWKES" : "V8_CONVEX_PROBE";

   req.tp           = 0.0; // Aucun TP serveur qui briderait l'amplitude d'un méga-spike



   // =========================================================================

   // RÉTRO-INVERSION STRICTE DE LA POLARITÉ (CHARLIE MUNGER INVERT) :

   // - Sur BOOM  : ACHETER (ORDER_TYPE_BUY) pour capter les explosions haussières !

   // - Sur CRASH : VENDRE (ORDER_TYPE_SELL) pour capter les chutes de spikes !

   // =========================================================================

   if(tr.is_boom)

   {

      req.type  = ORDER_TYPE_BUY;

      req.price = tick.ask;

      req.sl    = (server_sl_pts > 0.0) ? NormalizeDouble(tick.bid - server_sl_pts, digits) : 0.0;

   }

   else

   {

      req.type  = ORDER_TYPE_SELL;

      req.price = tick.bid;

      req.sl    = (server_sl_pts > 0.0) ? NormalizeDouble(tick.ask + server_sl_pts, digits) : 0.0;

   }



   bool sent = false;

   if(InpUseAsyncOrders)

      sent = OrderSendAsync(req, res);

   else

      sent = OrderSend(req, res);



   if(sent)

   {

      tr.entry_tick_counter   = tr.tick_counter;

      tr.entry_time_msc       = (long)GetTickCount64();

      tr.spikes_while_open    = 0;

      tr.last_open_spike_tick = 0;

      tr.peak_profit_usd      = -1e9;

      tr.peak_favorable_pts   = 0.0;

      tr.probes_triggered++;

      tr.open_positions++;

      g_total_probes_all++;



      PrintFormat("[DerivBoomCrashHFT v8.30] >>> SONDE CONVEXE %s LANCÉE sur %s (%.2f lot | p0=%.2f%% >= theta=%.2f%% | E[Payoff]=%+.2f$ | Hawkes=%.2f | TimeStop=%dt) <<<",

                  tr.is_boom ? "BUY_BOOM" : "SELL_CRASH",

                  tr.name, tr.lot_per_stage,

                  spike_p0 * 100.0, tr.last_theta_eff * 100.0,

                  tr.last_expected_payoff_usd, tr.last_hawkes_fast, InpMaxHoldCalmTicks);

      return true;

   }

   else

   {

      tr.cooldown_until_tick = tr.tick_counter + 10;

   }

   return false;

}



//+------------------------------------------------------------------+

//| Traitement tick par tick d'un indice                             |

//+------------------------------------------------------------------+

void ProcessSingleTick(SymbolTracker &tr, const MqlTick &tick, int &active_symbols_count)
{
   if(tick.bid <= 0.0 || tick.time_msc <= tr.last_time_msc)
      return;

   tr.last_time_msc   = tick.time_msc;
   tr.real_spread_pts = tick.ask - tick.bid;
   tr.breakeven_ticks = tr.real_spread_pts / MathMax(tr.abs_drift_per_tick, 1e-8);
   tr.tick_counter++;
   g_total_ticks_all++;

   // Mesure glissante du debit tick/s (fenetre 30s)
   if(tr.rate_window_start_msc <= 0)
   {
      tr.rate_window_start_msc  = tick.time_msc;
      tr.rate_window_start_tick = tr.tick_counter;
   }
   else if(tick.time_msc - tr.rate_window_start_msc >= 30000)
   {
      double span_sec = (double)(tick.time_msc - tr.rate_window_start_msc) / 1000.0;
      if(span_sec > 0.0)
         tr.ticks_per_sec = (double)(tr.tick_counter - tr.rate_window_start_tick) / span_sec;
      tr.rate_window_start_msc  = tick.time_msc;
      tr.rate_window_start_tick = tr.tick_counter;
   }

   double price = (tick.last > 0.0) ? tick.last : 0.5 * (tick.bid + tick.ask);

   if(tr.recent_prices_count < 4)
   {
      tr.recent_prices[tr.recent_prices_count] = price;
      tr.recent_prices_count++;
   }
   else
   {
      tr.recent_prices[0] = tr.recent_prices[1];
      tr.recent_prices[1] = tr.recent_prices[2];
      tr.recent_prices[2] = tr.recent_prices[3];
      tr.recent_prices[3] = price;
   }

   if(tr.last_price <= 0.0)
   {
      tr.last_price = price;
      return;
   }

   double delta  = price - tr.last_price;
   tr.last_price = price;
   tr.last_delta = delta;

   bool is_spike = tr.is_boom ? (delta >= tr.spike_threshold) : (delta <= -tr.spike_threshold);
   if(is_spike)
   {
      tr.spikes_detected++;
      g_total_spikes_all++;
      tr.last_spike_amp   = MathAbs(delta);
      tr.calm_drift_ticks = 0;

      if(tr.spike_history_count < 32)
      {
         tr.spike_history_ticks[tr.spike_history_count] = tr.tick_counter;
         tr.spike_history_amps[tr.spike_history_count]  = MathAbs(delta);
         tr.spike_history_count++;
      }
      else
      {
         for(int m = 0; m < 31; m++)
         {
            tr.spike_history_ticks[m] = tr.spike_history_ticks[m+1];
            tr.spike_history_amps[m]  = tr.spike_history_amps[m+1];
         }
         tr.spike_history_ticks[31] = tr.tick_counter;
         tr.spike_history_amps[31]  = MathAbs(delta);
      }

      if(tr.open_positions > 0)
      {
         tr.spikes_while_open++;
         tr.last_open_spike_tick = tr.tick_counter;
         PrintFormat("[DerivBoomCrashHFT v8.30] >>> SPIKE CAPTURE EN PLEIN VOL (#%d, Amp=%.2f pts) sur %s ! <<<",
                     tr.spikes_while_open, MathAbs(delta), tr.name);
      }
   }
   else
   {
      bool is_calm_drift = tr.is_boom ? (delta <= 0.0) : (delta >= 0.0);
      if(is_calm_drift)
         tr.calm_drift_ticks++;
   }

   if(tr.open_positions > 0)
      return;

   // Priorite de re-entree Hawkes : permet d'enjamber le cooldown classique si l'excitation est forte
   bool can_hawkes_reenter = (InpEnableHawkesClusterEntry &&
                              tr.spikes_detected > 0 &&
                              tr.calm_drift_ticks >= InpClusterReentryTicks &&
                              tr.calm_drift_ticks < InpCalmDriftEntryTicks &&
                              tr.last_hawkes_fast >= InpMinHawkesForCluster);

   if(tr.tick_counter < tr.cooldown_until_tick && !can_hawkes_reenter)
      return;

   if(active_symbols_count >= InpMaxActiveSymbols)
      return;

   // Mode 1 : Replique rapide sur Cluster de Hawkes (ex: 6 ticks calmes apres un spike)
   if(can_hawkes_reenter)
   {
      if(OpenConvexSpikeProbe(tr, tick, true))
      {
         active_symbols_count++;
         return;
      }
   }

   // Mode 2 : Sonde periodique standard tous les 15-20 ticks calmes sans spike
   if(InpEnablePeriodicSpikeProbe && tr.calm_drift_ticks >= InpCalmDriftEntryTicks)
   {
      if(OpenConvexSpikeProbe(tr, tick, false))
      {
         active_symbols_count++;
         return;
      }
   }
}

//+------------------------------------------------------------------+
//| Consommation Multi-Ticks par Curseur CopyTicks (Fable FIX-1)     |
//+------------------------------------------------------------------+
void ProcessSymbolTick(SymbolTracker &tr, int &active_symbols_count)
{
   if(!InpUseCopyTicksCursor)
   {
      MqlTick tick;
      if(!SymbolInfoTick(tr.name, tick))
         return;
      ProcessSingleTick(tr, tick, active_symbols_count);
      return;
   }

   // Amorce du curseur
   if(tr.last_time_msc <= 0)
   {
      MqlTick t0;
      if(!SymbolInfoTick(tr.name, t0) || t0.time_msc <= 0)
         return;
      tr.last_time_msc    = t0.time_msc;
      tr.last_ms_consumed = 1;
      tr.last_price       = (t0.last > 0.0) ? t0.last : 0.5 * (t0.bid + t0.ask);
      return;
   }

   MqlTick arr[];
   int copied = CopyTicks(tr.name, arr, COPY_TICKS_ALL, (ulong)tr.last_time_msc, InpMaxTicksPerScan);
   if(copied <= 0)
   {
      MqlTick fallback_tick;
      if(SymbolInfoTick(tr.name, fallback_tick) && fallback_tick.time_msc > tr.last_time_msc)
         ProcessSingleTick(tr, fallback_tick, active_symbols_count);
      return;
   }

   int start = 0;
   while(start < copied && arr[start].time_msc == tr.last_time_msc && start < tr.last_ms_consumed)
      start++;

   for(int k = start; k < copied; k++)
   {
      if(arr[k].time_msc > tr.last_time_msc)
      {
         tr.last_time_msc    = arr[k].time_msc;
         tr.last_ms_consumed = 1;
      }
      else if(arr[k].time_msc == tr.last_time_msc)
      {
         tr.last_ms_consumed++;
      }
      else
         continue;

      ProcessSingleTick(tr, arr[k], active_symbols_count);
   }
}


//+------------------------------------------------------------------+
//| Affichage du Tableau de Bord Telemetrique V8.30                  |
//+------------------------------------------------------------------+
void RenderConvexDashboard(double eq, double dd_pct, int active_symbols_count)

{

   if(!InpShowDashboard)

      return;



   string dash = StringFormat(

      "=================================================================\n"

      " DERIV BOOM & CRASH HFT v8.30 — MUNGER CONVEX SPIKE HARVESTER\n"

      "=================================================================\n"

      " Polarité   : INVERSION CONVEXE (SELL Crash | BUY Boom)\n"

      " Cerveau IA : %s | Time-Stop M* = %d ticks | MaxLoss = -%.2f$\n"

      " Equity     : %.2f USD (Initial: %.2f$ | DD: %.2f%% | Actifs: %d/%d)\n"

      " Télémétrie : Ticks=%I64d | SpikesMarché=%I64d | Sondes=%I64d | SpikesCapturés=%I64d | TimeStops=%I64d | Bloqués=%I64d\n"

      "-----------------------------------------------------------------\n",

      g_onnx_ready ? "ONNX [1,1] ACTIF" : "POISSON + HAWKES",

      InpMaxHoldCalmTicks, InpMaxLossUsdPerTrade,

      eq, g_initial_equity, dd_pct, active_symbols_count, InpMaxActiveSymbols,

      g_total_ticks_all, g_total_spikes_all, g_total_probes_all,

      g_total_spikes_caught, g_total_time_stops, g_total_ai_blocked

   );



   for(int i = 0; i < g_num_trackers; i++)

   {

      SymbolTracker tr = g_trackers[i];

      dash += StringFormat(

         " %-16s | %s | Calm=%3I64dt | p0=%5.2f%% (th=%4.2f%%) | H_fast=%4.2f | E[Payoff]=%+5.2f$ | Sondes=%I64d | Spikes=%I64d\n",

         tr.name,

         tr.is_boom ? "BUY_BOOM " : "SELL_CRSH",

         tr.calm_drift_ticks,

         tr.last_spike_prob_p0 * 100.0,

         tr.last_theta_eff * 100.0,

         tr.last_hawkes_fast,

         tr.last_expected_payoff_usd,

         tr.probes_triggered,

         tr.spikes_detected

      );

   }

   Comment(dash);

}



//+------------------------------------------------------------------+

//| Boucle Principale Multi-Symboles (50 ms)                         |

//+------------------------------------------------------------------+

void ScanAllBoomCrashSymbols()

{

   if(g_emergency_stopped)

      return;



   double eq = AccountInfoDouble(ACCOUNT_EQUITY);

   if(eq > g_peak_equity)

      g_peak_equity = eq;



   double dd_pct         = (g_peak_equity > 0.0) ? ((g_peak_equity - eq) / g_peak_equity) * 100.0 : 0.0;

   double daily_loss_pct = (g_initial_equity > 0.0) ? ((g_initial_equity - eq) / g_initial_equity) * 100.0 : 0.0;



   int active_symbols_count = ManageConvexPositions();



   if(dd_pct >= InpMaxDrawdownPct || daily_loss_pct >= InpDailyLossPct)

   {

      g_emergency_stopped = true;

      Alert(StringFormat("[DerivBoomCrashHFT v8.30] ARRÊT D'URGENCE (DD=%.2f%%, PerteJour=%.2f%%)", dd_pct, daily_loss_pct));

      return;

   }



   for(int i = 0; i < g_num_trackers; i++)

      ProcessSymbolTick(g_trackers[i], active_symbols_count);



   RenderConvexDashboard(eq, dd_pct, active_symbols_count);

}



void OnTick()  { ScanAllBoomCrashSymbols(); }

void OnTimer() { ScanAllBoomCrashSymbols(); }

//+------------------------------------------------------------------+