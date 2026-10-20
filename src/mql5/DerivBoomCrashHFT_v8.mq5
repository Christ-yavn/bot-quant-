//+------------------------------------------------------------------+
//|                                        DerivBoomCrashHFT_v8.mq5 |
//|                             Copyright 2026, Direction Recherche Quant |
//|                                      https://github.com/Christ-yavn/bot-quant- |
//+------------------------------------------------------------------+
#property copyright   "Copyright 2026, Direction Recherche Quant"
#property link        "https://github.com/Christ-yavn/bot-quant-"
#property version     "8.00"
#property description "Deriv HFT Quant v8.00 - Spike Hunter Convexe (Positive Skew Alpha Engine)"
#property description "Architecture miroir de la v7.00 transformant l'esperance negative en alpha convexe."
#property description "Direction inverse : SELL sur Crash, BUY sur Boom (capture de spikes a payoff asymetrique)."
#property description "Stop temporel analytique strict M*=60 ticks, TP serveur dur 0.8*E[Amp], Watchdog OnTick."
#property strict

// Inclusion du modele ONNX Hawkes v7 sans triche compile comme ressource integree
#resource "\\Files\\boom_crash_meta_brain.onnx" as uchar ExtColabOnnxBrain[]

#include <Trade\Trade.mqh>
CTrade trade;

//+------------------------------------------------------------------+
//| Enumerations de Configuration                                    |
//+------------------------------------------------------------------+
enum ENUM_SYMBOL_UNIVERSE
{
   UNIVERSE_CONVEX_TOP_HARVEST   = 0, // Top Convexite (Crash 600, Crash 900, Boom 500, Boom 900, Boom 600, Crash 500, Crash 1000)
   UNIVERSE_ALL_10_BOOM_CRASH    = 1, // 10 Indices Complets (Boom 300-1000 & Crash 300-1000)
   UNIVERSE_CURRENT_CHART_ONLY   = 2  // Graphique Actuel Uniquement
};

enum ENUM_LOT_MODE
{
   LOT_MODE_MIN_BROKER           = 0, // Lot Minimum Broker (0.20 - Securite Maximale Validation)
   LOT_MODE_FIXED                = 1, // Lot Fixe Configure (InpFixedLot)
   LOT_MODE_FRACTIONAL_KELLY     = 2  // Dimensionnement Kelly Convexe 1/8 (~1% risque equity)
};

//+------------------------------------------------------------------+
//| Parametres d'Entree (Inputs) - Norme L99 / BEASTMODE             |
//+------------------------------------------------------------------+
input group "=== 1. Cerveau IA ONNX Hawkes & Signal Convexe ==="
input bool   InpUseColabOnnxBrain           = true;   // Activer le Reseau ONNX v7.00 (14 variables dynamiques sans triche)
input bool   InpUseZeroCheatFeatures        = true;   // true = Features normalisees sans fuite
input double InpThetaSpike                  = 0.15;   // Seuil P0 = P(spike dans M* ticks) [Lift Hazard 1.61x a 2.06x]
input bool   InpRequirePositiveExpectedPayoff = true; // Exiger E[Payoff] > 0 avant toute entree
input double InpMaxHawkesFast               = 1.50;   // Intensite Hawkes rapide max autorisee

input group "=== 2. Univers & Filtres d'Entree Inversee ==="
input ENUM_SYMBOL_UNIVERSE InpSymbolUniverse = UNIVERSE_CONVEX_TOP_HARVEST; // Univers d'indices
input int    InpCooldownPostSpike           = 15;     // Cooldown post-spike obligatoire (ticks anti-double-spike)
input double InpMaxSpreadDriftMult          = 80.0;   // Plafond de spread (multiples de derive)
input int    InpMaxActiveSymbols            = 3;      // Max positions simultanees
input int    InpScannerTimerMs              = 50;     // Frequence du scanner haute precision (ms)

input group "=== 3. Sortie Hybride : TP Dur Serveur + Watchdog + Stop Temporel ==="
input int    InpTimeStopTicks               = 60;     // M* Stop temporel analytique strict (ticks non-negociables)
input double InpTakeProfitRatio             = 0.8;    // Profondeur TP dur serveur = 0.8 * E[Amplitude]
input double InpEmergencySlMult             = 2.0;    // Multiplicateur SL d'urgence serveur (2.0 * L_max)
input bool   InpEnableWatchdog              = true;   // Watchdog OnTick (capture saut de tick ou coupe these consommee)
input double InpSpikeProfitFloor            = 0.50;   // Seuil profit USD pour valider SPIKE_CAUGHT_WATCHDOG vs THESIS_CONSUMED

input group "=== 4. Kelly Convexe & Dimensionnement ==="
input ENUM_LOT_MODE InpLotMode              = LOT_MODE_MIN_BROKER; // Mode de calcul des lots
input double InpFixedLot                    = 0.20;   // Lot fixe (si Mode = LOT_MODE_FIXED)
input double InpKellyFraction               = 0.01;   // Fraction de Kelly 1/8 (~1.0% equity par trade)
input double InpMaxRiskUsdPerTrade          = 2.50;   // Coupe-circuit USD absolu par trade

input group "=== 5. Securite Globale & Coupe-Circuits ==="
input bool   InpDemoAccountOnly             = true;   // Verrou compte Demo
input double InpDailyLossPct                = 2.0;    // Coupe-circuit Perte Journaliere Max (-2%)
input double InpMaxDrawdownPct              = 10.0;   // Coupe-circuit Drawdown Max (-10%)
input ulong  InpMagicNumber                 = 20261020;// Magic Number v8.00 Spike Hunter
input bool   InpShowDashboard               = true;   // Afficher tableau de bord live

//+------------------------------------------------------------------+
//| Structures de Donnees & Microstructure                           |
//+------------------------------------------------------------------+
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
   long     ticks_since_spike;
   long     spikes_detected;
   long     entries_triggered;
   long     ai_filtered_count;
   double   last_ai_p0;
   double   last_hawkes_fast;
   long     cooldown_until_tick;

   long     spike_history_ticks[32];
   double   spike_history_amps[32];
   int      spike_history_count;

   int      open_positions;
};

struct PositionEntryTracker
{
   ulong    ticket;
   string   symbol;
   long     entry_tick;
   long     entry_time_msc;
   int      pos_type;
   double   volume;
   double   open_price;
   double   target_tp;
   double   emergency_sl;
   bool     is_active;
};

#define MAX_TRACKED_POS 64
PositionEntryTracker g_pos_tracker[MAX_TRACKED_POS];

struct ClosingTicketLock
{
   ulong    ticket;
   long     sent_msc;
};
ClosingTicketLock g_closing_locks[32];
int               g_closing_locks_count = 0;

//+------------------------------------------------------------------+
//| Variables Globales                                               |
//+------------------------------------------------------------------+
SymbolTracker  g_trackers[];
int            g_num_trackers = 0;
long           g_onnx_handle  = INVALID_HANDLE;
bool           g_onnx_ready   = false;

double         g_initial_equity       = 0.0;
double         g_peak_equity          = 0.0;
bool           g_emergency_stopped    = false;

long           g_total_ticks_all      = 0;
long           g_total_spikes_all     = 0;
long           g_total_entries_all    = 0;
long           g_total_ai_blocked     = 0;

long           g_total_server_tp      = 0;
long           g_total_watchdog_green = 0;
long           g_total_thesis_consumed= 0;
long           g_total_timestop_closed= 0;
long           g_total_max_risk_cut   = 0;
long           g_total_emergency_sl   = 0;

//+------------------------------------------------------------------+
//| Fonctions Utilitaires & Securite de Fermeture                     |
//+------------------------------------------------------------------+
bool IsTicketClosingInFlight(ulong ticket)
{
   long now_msc = (long)GetTickCount64();
   for(int i = 0; i < g_closing_locks_count; i++)
   {
      if(g_closing_locks[i].ticket == ticket)
      {
         if(now_msc - g_closing_locks[i].sent_msc < 2500)
            return true;
         g_closing_locks[i] = g_closing_locks[g_closing_locks_count - 1];
         g_closing_locks_count--;
         return false;
      }
   }
   return false;
}

void MarkTicketClosingInFlight(ulong ticket)
{
   if(g_closing_locks_count < 32)
   {
      g_closing_locks[g_closing_locks_count].ticket   = ticket;
      g_closing_locks[g_closing_locks_count].sent_msc = (long)GetTickCount64();
      g_closing_locks_count++;
   }
}

void ClearTicketClosingLock(ulong ticket)
{
   for(int i = 0; i < g_closing_locks_count; i++)
   {
      if(g_closing_locks[i].ticket == ticket)
      {
         g_closing_locks[i] = g_closing_locks[g_closing_locks_count - 1];
         g_closing_locks_count--;
         return;
      }
   }
}

//+------------------------------------------------------------------+
//| Registre de Suivi des Positions en Memoire (0 ms)                |
//+------------------------------------------------------------------+
void RegisterTrackedPosition(ulong ticket, const string sym, long current_tick, long time_msc, int ptype, double vol, double price, double tp, double sl)
{
   for(int i = 0; i < MAX_TRACKED_POS; i++)
   {
      if(!g_pos_tracker[i].is_active || g_pos_tracker[i].ticket == ticket)
      {
         g_pos_tracker[i].ticket         = ticket;
         g_pos_tracker[i].symbol         = sym;
         g_pos_tracker[i].entry_tick     = current_tick;
         g_pos_tracker[i].entry_time_msc = time_msc;
         g_pos_tracker[i].pos_type       = ptype;
         g_pos_tracker[i].volume         = vol;
         g_pos_tracker[i].open_price     = price;
         g_pos_tracker[i].target_tp      = tp;
         g_pos_tracker[i].emergency_sl   = sl;
         g_pos_tracker[i].is_active      = true;
         return;
      }
   }
}

int FindTrackedPositionIndex(ulong ticket)
{
   for(int i = 0; i < MAX_TRACKED_POS; i++)
   {
      if(g_pos_tracker[i].is_active && g_pos_tracker[i].ticket == ticket)
         return i;
   }
   return -1;
}

void UnregisterTrackedPosition(ulong ticket)
{
   int idx = FindTrackedPositionIndex(ticket);
   if(idx >= 0)
      g_pos_tracker[idx].is_active = false;
   ClearTicketClosingLock(ticket);
}

//+------------------------------------------------------------------+
//| Distance Minimale Requise par le Broker Deriv                    |
//+------------------------------------------------------------------+
double GetBrokerMinStopDistancePts(const string sym)
{
   double pt         = SymbolInfoDouble(sym, SYMBOL_POINT);
   long   stops_lvl  = SymbolInfoInteger(sym, SYMBOL_TRADE_STOPS_LEVEL);
   long   freeze_lvl = SymbolInfoInteger(sym, SYMBOL_TRADE_FREEZE_LEVEL);
   long   max_lvl    = MathMax(stops_lvl, freeze_lvl);
   return (double)(max_lvl + 4) * pt;
}

//+------------------------------------------------------------------+
//| Mode de Remplissage Supporte (FOK, IOC, RETURN)                  |
//+------------------------------------------------------------------+
ENUM_ORDER_TYPE_FILLING GetSupportedFillingMode(const string sym)
{
   uint filling = (uint)SymbolInfoInteger(sym, SYMBOL_FILLING_MODE);
   if((filling & ORDER_FILLING_IOC) != 0)
      return ORDER_FILLING_IOC;
   if((filling & ORDER_FILLING_FOK) != 0)
      return ORDER_FILLING_FOK;
   return ORDER_FILLING_RETURN;
}

//+------------------------------------------------------------------+
//| Initialisation du Cerveau ONNX v7.00                             |
//+------------------------------------------------------------------+
bool InitColabOnnxBrain()
{
   g_onnx_ready  = false;
   g_onnx_handle = INVALID_HANDLE;

   if(!InpUseColabOnnxBrain)
      return false;

   g_onnx_handle = OnnxCreateFromBuffer(ExtColabOnnxBrain, ONNX_DEFAULT);
   if(g_onnx_handle == INVALID_HANDLE)
      g_onnx_handle = OnnxCreate("boom_crash_meta_brain.onnx", ONNX_DEFAULT);

   if(g_onnx_handle == INVALID_HANDLE)
   {
      PrintFormat("[DerivBoomCrashHFT v8.00] ERREUR chargement ONNX (code=%d) -> Repli modele physique.", GetLastError());
      return false;
   }

   const long input_shape[]  = {1, 14};
   const long output_label[] = {1};
   const long output_proba[] = {1, 2};

   if(!OnnxSetInputShape(g_onnx_handle, 0, input_shape))
   {
      OnnxRelease(g_onnx_handle);
      g_onnx_handle = INVALID_HANDLE;
      return false;
   }
   OnnxSetOutputShape(g_onnx_handle, 0, output_label);
   OnnxSetOutputShape(g_onnx_handle, 1, output_proba);

   g_onnx_ready = true;
   Print("[DerivBoomCrashHFT v8.00] >>> CERVEAU IA ONNX v8.00 INITIALISE AVEC SUCCES (14 FEATURES HAWKES) <<<");
   return true;
}

//+------------------------------------------------------------------+
//| Inference ONNX : Probabilite de Spike P0 = P(spike dans M* ticks)|
//+------------------------------------------------------------------+
double EvaluateColabOnnxSpikeProbability(SymbolTracker &tr, int &out_c60)
{
   double mean_sp  = MathMax(tr.mean_spike_pts, 1e-6);
   double mean_tau = MathMax(tr.mean_tau_ticks, 1.0);
   double drift    = MathMax(tr.abs_drift_per_tick, 1e-8);

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

   // Repli analytique physique si ONNX non charge
   if(!g_onnx_ready || g_onnx_handle == INVALID_HANDLE)
   {
      double base_p0 = 1.0 - MathExp(-((double)InpTimeStopTicks) / mean_tau);
      double hawkes_boost = 1.0 + 0.35 * MathMax(0.0, h_fast - 0.50);
      return MathMax(0.01, MathMin(0.50, base_p0 * hawkes_boost));
   }

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

   long  out_label[1];
   float out_proba[1][2];

   if(!OnnxRun(g_onnx_handle, ONNX_NO_CONVERSION, x, out_label, out_proba))
      return 0.15;

   // En v7, out_proba[0][1] etait P(survie sans spike dans 60 ticks)
   // En v8, P0 = P(spike dans 60 ticks) = 1.0 - P_survie
   double p_survie = (double)out_proba[0][1];
   double p0_spike = 1.0 - p_survie;
   return MathMax(0.0, MathMin(1.0, p0_spike));
}

//+------------------------------------------------------------------+
//| Calcul du Dimensionnement de Lot (Kelly Convexe)                 |
//+------------------------------------------------------------------+
double ComputeConvexLotSize(SymbolTracker &tr)
{
   double vol_min  = SymbolInfoDouble(tr.name, SYMBOL_VOLUME_MIN);
   double vol_max  = SymbolInfoDouble(tr.name, SYMBOL_VOLUME_MAX);
   double vol_step = SymbolInfoDouble(tr.name, SYMBOL_VOLUME_STEP);
   if(vol_min <= 0.0)  vol_min  = 0.20;
   if(vol_step <= 0.0) vol_step = 0.01;

   if(InpLotMode == LOT_MODE_MIN_BROKER)
      return vol_min;

   if(InpLotMode == LOT_MODE_FIXED)
   {
      double clamped = MathMax(vol_min, MathMin(vol_max, InpFixedLot));
      return MathFloor(clamped / vol_step + 1e-9) * vol_step;
   }

   // Mode Kelly Convexe 1/8 :
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   double target_risk_usd = MathMin(InpMaxRiskUsdPerTrade, InpKellyFraction * equity);

   double tick_val = SymbolInfoDouble(tr.name, SYMBOL_TRADE_TICK_VALUE);
   double tick_sz  = SymbolInfoDouble(tr.name, SYMBOL_TRADE_TICK_SIZE);
   if(tick_sz <= 0.0)  tick_sz  = SymbolInfoDouble(tr.name, SYMBOL_POINT);
   if(tick_val <= 0.0) tick_val = 1.0;

   double lmax_pts = tr.abs_drift_per_tick * InpTimeStopTicks + tr.real_spread_pts;
   double lmax_usd_minlot = (lmax_pts / tick_sz) * tick_val * (vol_min / MathMax(vol_step, 0.01));
   if(lmax_usd_minlot <= 0.05) lmax_usd_minlot = 0.25;

   double raw_lot = vol_min * (target_risk_usd / lmax_usd_minlot);
   double clamped = MathMax(vol_min, MathMin(vol_max, raw_lot));
   return MathFloor(clamped / vol_step + 1e-9) * vol_step;
}

//+------------------------------------------------------------------+
//| Initialisation et Calibration d'un SymbolTracker                 |
//+------------------------------------------------------------------+
void InitAndCalibrateTracker(SymbolTracker &tr, const string sym)
{
   tr.name                  = sym;
   string s                 = sym;
   StringToLower(s);
   tr.is_boom               = (StringFind(s, "boom") >= 0);
   tr.symbol_id             = 0;
   tr.last_price            = 0.0;
   tr.recent_prices_count   = 0;
   tr.last_delta            = 0.0;
   tr.last_spike_amp        = 0.0;
   tr.last_time_msc         = 0;
   tr.last_order_sent_msc   = 0;
   tr.tick_counter          = 0;
   tr.ticks_since_spike     = 1000;
   tr.spikes_detected       = 0;
   tr.entries_triggered     = 0;
   tr.ai_filtered_count     = 0;
   tr.last_ai_p0            = 0.0;
   tr.last_hawkes_fast      = 0.0;
   tr.cooldown_until_tick   = 0;
   tr.spike_history_count   = 0;
   tr.open_positions        = 0;

   for(int r = 0; r < 4; r++)
      tr.recent_prices[r] = 0.0;

   for(int k = 0; k < 32; k++)
   {
      tr.spike_history_ticks[k] = -100000;
      tr.spike_history_amps[k]  = 0.0;
   }

   tr.lot_per_stage      = ComputeConvexLotSize(tr);
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
         tr.ticks_since_spike  = (long)(copied - 1 - last_sp_i);
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
      tr.real_spread_pts = 60.0 * tr.abs_drift_per_tick;

   tr.breakeven_ticks = tr.real_spread_pts / MathMax(tr.abs_drift_per_tick, 1e-8);
   tr.spike_threshold = MathMax(3.5 * tr.abs_drift_per_tick, 0.25 * tr.mean_spike_pts);

   int dummy_c60 = 0;
   tr.last_ai_p0 = EvaluateColabOnnxSpikeProbability(tr, dummy_c60);
}

//+------------------------------------------------------------------+
//| Gestion de l'Univers des Symboles                                |
//+------------------------------------------------------------------+
bool AddSymbolToScanner(const string sym)
{
   for(int i = 0; i < g_num_trackers; i++)
      if(g_trackers[i].name == sym)
         return true;

   if(!SymbolSelect(sym, true))
      return false;

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

   if(InpSymbolUniverse == UNIVERSE_CONVEX_TOP_HARVEST)
   {
      string top_harvest[] = {
         "Crash 600 Index",
         "Crash 900 Index",
         "Boom 500 Index",
         "Boom 900 Index",
         "Boom 600 Index",
         "Crash 500 Index",
         "Crash 1000 Index"
      };
      for(int i = 0; i < ArraySize(top_harvest); i++)
         AddSymbolToScanner(top_harvest[i]);
      return;
   }

   string all10[] = {
      "Boom 1000 Index", "Crash 1000 Index",
      "Boom 900 Index",  "Crash 900 Index",
      "Boom 600 Index",  "Crash 600 Index",
      "Boom 500 Index",  "Crash 500 Index",
      "Boom 300 Index",  "Crash 300 Index"
   };
   for(int i = 0; i < ArraySize(all10); i++)
      AddSymbolToScanner(all10[i]);
}

//+------------------------------------------------------------------+
//| Dashboard Graphique Simple                                       |
//+------------------------------------------------------------------+
void UpdateDashboard(double dd_pct, double daily_loss_pct)
{
   string name = "V8_DASH_BG";
   if(ObjectFind(0, name) < 0)
   {
      ObjectCreate(0, name, OBJ_RECTANGLE_LABEL, 0, 0, 0);
      ObjectSetInteger(0, name, OBJPROP_XDISTANCE, 20);
      ObjectSetInteger(0, name, OBJPROP_YDISTANCE, 20);
      ObjectSetInteger(0, name, OBJPROP_XSIZE, 420);
      ObjectSetInteger(0, name, OBJPROP_YSIZE, 240);
      ObjectSetInteger(0, name, OBJPROP_BGCOLOR, C'15,23,42');
      ObjectSetInteger(0, name, OBJPROP_BORDER_COLOR, C'56,189,248');
      ObjectSetInteger(0, name, OBJPROP_CORNER, CORNER_LEFT_UPPER);
   }

   string label_name = "V8_DASH_TXT";
   if(ObjectFind(0, label_name) < 0)
   {
      ObjectCreate(0, label_name, OBJ_LABEL, 0, 0, 0);
      ObjectSetInteger(0, label_name, OBJPROP_XDISTANCE, 30);
      ObjectSetInteger(0, label_name, OBJPROP_YDISTANCE, 25);
      ObjectSetInteger(0, label_name, OBJPROP_COLOR, clrWhite);
      ObjectSetInteger(0, label_name, OBJPROP_FONTSIZE, 9);
      ObjectSetString(0, label_name, OBJPROP_FONT, "Consolas");
      ObjectSetInteger(0, label_name, OBJPROP_CORNER, CORNER_LEFT_UPPER);
   }

   double cur_eq  = AccountInfoDouble(ACCOUNT_EQUITY);
   double pnl_tot = cur_eq - g_initial_equity;

   string txt = StringFormat(
      "=== DERIV HFT QUANT v8.00 (SPIKE HUNTER CONVEXE) ===\n"
      "Statut : ACTIF (Alpha Positif Convexe) | Ticks: %d\n"
      "Equite : %.2f USD | PnL Session : %+.2f USD\n"
      "Drawdown Pic : %.2f%% | Perte Journaliere : %.2f%%\n"
      "--------------------------------------------------\n"
      "Positions Lancees : %d (Actives: %d)\n"
      "Sorties TP Serveur Dur : %d\n"
      "Sorties Watchdog Vert  : %d\n"
      "Sorties These Consommee: %d\n"
      "Sorties Stop Temporel  : %d (M*=%d ticks)\n"
      "Sorties Risque USD Cut : %d\n"
      "Filtres IA / Hawkes    : %d bloquages\n"
      "--------------------------------------------------\n"
      "Modele : ONNX v7 Sans Triche | Seuil Theta: %.2f",
      g_total_ticks_all, cur_eq, pnl_tot, dd_pct, daily_loss_pct,
      g_total_entries_all, PositionsTotal(),
      g_total_server_tp, g_total_watchdog_green, g_total_thesis_consumed,
      g_total_timestop_closed, InpTimeStopTicks, g_total_max_risk_cut,
      g_total_ai_blocked, InpThetaSpike
   );

   ObjectSetString(0, label_name, OBJPROP_TEXT, txt);
}

//+------------------------------------------------------------------+
//| Initialisation du Bot EA v8.00                                   |
//+------------------------------------------------------------------+
int OnInit()
{
   if(InpDemoAccountOnly && AccountInfoInteger(ACCOUNT_TRADE_MODE) != ACCOUNT_TRADE_MODE_DEMO)
   {
      Alert("[DerivBoomCrashHFT v8.00] SECURITE : Ce bot ne peut fonctionner QUE sur compte DEMO !");
      return INIT_FAILED;
   }

   trade.SetExpertMagicNumber(InpMagicNumber);
   trade.SetDeviationInPoints(50);

   g_initial_equity    = AccountInfoDouble(ACCOUNT_EQUITY);
   g_peak_equity       = g_initial_equity;
   g_emergency_stopped = false;

   for(int i = 0; i < MAX_TRACKED_POS; i++)
      g_pos_tracker[i].is_active = false;

   Print("========================================================================");
   PrintFormat("[DerivBoomCrashHFT v8.00] DEMARRAGE MOTEUR SPIKE HUNTER CONVEXE (Equite: %.2f USD)", g_initial_equity);
   PrintFormat("[DerivBoomCrashHFT v8.00] Parametres Cles: Seuil Theta=%.2f | M*=%d ticks | TP=%.1fx E[A] | Kelly=%.2f%%",
               InpThetaSpike, InpTimeStopTicks, InpTakeProfitRatio, InpKellyFraction * 100.0);

   InitColabOnnxBrain();
   BuildSymbolUniverse();

   EventSetMillisecondTimer(InpScannerTimerMs);
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Desinitialisation du Bot EA v8.00                                |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   EventKillTimer();
   if(g_onnx_handle != INVALID_HANDLE)
   {
      OnnxRelease(g_onnx_handle);
      g_onnx_handle = INVALID_HANDLE;
   }
   ObjectsDeleteAll(0, "V8_DASH_");
   PrintFormat("[DerivBoomCrashHFT v8.00] ARRETE (Raison: %d) | Total Trades: %d | Server TPs: %d | Watchdogs: %d | Time-Stops: %d",
               reason, g_total_entries_all, g_total_server_tp, g_total_watchdog_green, g_total_timestop_closed);
}

//+------------------------------------------------------------------+
//| Fermeture d'un Ticket Unique avec Raison Tracee                  |
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
   bool sent = OrderSend(req, res);
   if(sent && res.retcode == TRADE_RETCODE_DONE)
   {
      UnregisterTrackedPosition(ticket);
      return true;
   }
   return false;
}

//+------------------------------------------------------------------+
//| Gestion des Positions Ouvertes v8.00                             |
//| 1) Watchdog Spike OnTick (0 ms)                                  |
//| 2) Stop Temporel Analytique Strict M* = 60 ticks                 |
//| 3) Coupe-circuit risque USD absolu                               |
//+------------------------------------------------------------------+
int ManageOpenPositionsAndExitSpikes()
{
   for(int i = 0; i < g_num_trackers; i++)
      g_trackers[i].open_positions = 0;

   int total = PositionsTotal();
   for(int p = total - 1; p >= 0; p--)
   {
      ulong ticket = PositionGetTicket(p);
      if(ticket == 0) continue;
      if((ulong)PositionGetInteger(POSITION_MAGIC) != InpMagicNumber) continue;

      string psym              = PositionGetString(POSITION_SYMBOL);
      double profit_usd        = PositionGetDouble(POSITION_PROFIT) + PositionGetDouble(POSITION_SWAP);
      double open_price        = PositionGetDouble(POSITION_PRICE_OPEN);
      double volume            = PositionGetDouble(POSITION_VOLUME);
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

      int pos_idx = FindTrackedPositionIndex(ticket);
      if(pos_idx < 0)
      {
         RegisterTrackedPosition(ticket, psym, tr.tick_counter, (long)GetTickCount64(), (int)ptype, volume, open_price, 0.0, 0.0);
         pos_idx = FindTrackedPositionIndex(ticket);
      }

      long age_ticks = (pos_idx >= 0) ? (tr.tick_counter - g_pos_tracker[pos_idx].entry_tick) : 0;

      // --- EXIT 1 : WATCHDOG SPIKE ON-TICK ---
      if(InpEnableWatchdog && tr.ticks_since_spike == 0)
      {
         if(profit_usd >= InpSpikeProfitFloor)
         {
            if(CloseSinglePositionTicket(ticket, psym, ptype, volume, "SPIKE_CAUGHT_WATCHDOG"))
            {
               g_total_watchdog_green++;
               PrintFormat("[DerivBoomCrashHFT v8.00] $$$ SPIKE CAPTURE PAR WATCHDOG sur %s : +%.2f USD (age=%d ticks) $$$",
                           psym, profit_usd, age_ticks);
               g_trackers[tr_idx].cooldown_until_tick = g_trackers[tr_idx].tick_counter + InpCooldownPostSpike;
               continue;
            }
         }
         else
         {
            if(CloseSinglePositionTicket(ticket, psym, ptype, volume, "THESIS_CONSUMED_CUT"))
            {
               g_total_thesis_consumed++;
               PrintFormat("[DerivBoomCrashHFT v8.00] --- THESE DE SPIKE CONSOMMEE sur %s (PnL=%.2f USD) -> Sortie immediate ---",
                           psym, profit_usd);
               g_trackers[tr_idx].cooldown_until_tick = g_trackers[tr_idx].tick_counter + InpCooldownPostSpike;
               continue;
            }
         }
      }

      // --- EXIT 2 : STOP TEMPOREL ANALYTIQUE STRICT M* = 60 TICKS ---
      if(age_ticks >= InpTimeStopTicks)
      {
         if(CloseSinglePositionTicket(ticket, psym, ptype, volume, "TIME_STOP_EXPIRED"))
         {
            g_total_timestop_closed++;
            PrintFormat("[DerivBoomCrashHFT v8.00] <<< STOP TEMPOREL STRICT EXPIRE sur %s : %.2f USD (atteint M*=%d ticks) >>>",
                        psym, profit_usd, InpTimeStopTicks);
            continue;
         }
      }

      // --- EXIT 3 : COUPE-CIRCUIT RISQUE USD ABSOLU ---
      if(InpMaxRiskUsdPerTrade > 0.0 && profit_usd <= -InpMaxRiskUsdPerTrade)
      {
         if(CloseSinglePositionTicket(ticket, psym, ptype, volume, "MAX_USD_RISK_CUT"))
         {
            g_total_max_risk_cut++;
            PrintFormat("[DerivBoomCrashHFT v8.00] !!! PLAFOND RISQUE MAX USD (%.2f USD) sur %s -> Coupure d'urgence !!!",
                        profit_usd, psym);
            g_trackers[tr_idx].cooldown_until_tick = g_trackers[tr_idx].tick_counter + 60;
            continue;
         }
      }
   }

   int active_count = 0;
   for(int i = 0; i < g_num_trackers; i++)
      if(g_trackers[i].open_positions > 0)
         active_count++;

   return active_count;
}

//+------------------------------------------------------------------+
//| Ouverture de Position Convexe Spike Hunter (Direction Inverse)   |
//+------------------------------------------------------------------+
bool OpenConvexSpikePosition(SymbolTracker &tr, const MqlTick &tick, double p0_spike)
{
   if(tr.open_positions > 0 || (tick.time_msc - tr.last_order_sent_msc) < 3000)
      return false;

   if(!(bool)TerminalInfoInteger(TERMINAL_TRADE_ALLOWED) || !(bool)MQLInfoInteger(MQL_TRADE_ALLOWED))
      return false;

   double spread = tick.ask - tick.bid;
   tr.real_spread_pts = spread;
   tr.breakeven_ticks = spread / MathMax(tr.abs_drift_per_tick, 1e-8);

   if(tr.breakeven_ticks > InpMaxSpreadDriftMult)
      return false;

   double expected_win_pts  = InpTakeProfitRatio * tr.mean_spike_pts;
   double expected_loss_pts = tr.abs_drift_per_tick * InpTimeStopTicks + tr.real_spread_pts;
   double expected_payoff   = p0_spike * expected_win_pts - (1.0 - p0_spike) * expected_loss_pts;

   if(InpRequirePositiveExpectedPayoff && expected_payoff <= 0.0)
   {
      tr.ai_filtered_count++;
      g_total_ai_blocked++;
      return false;
   }

   tr.last_order_sent_msc = tick.time_msc;
   int digits = (int)SymbolInfoInteger(tr.name, SYMBOL_DIGITS);
   ENUM_ORDER_TYPE_FILLING fill_mode = GetSupportedFillingMode(tr.name);

   double lot = ComputeConvexLotSize(tr);
   double min_stop_pts = GetBrokerMinStopDistancePts(tr.name);

   double tp_depth_pts = MathMax(min_stop_pts, InpTakeProfitRatio * tr.mean_spike_pts);
   double sl_dist_pts  = MathMax(min_stop_pts, InpEmergencySlMult * expected_loss_pts);

   MqlTradeRequest req;
   MqlTradeResult  res;
   ZeroMemory(req);
   ZeroMemory(res);

   req.action       = TRADE_ACTION_DEAL;
   req.symbol       = tr.name;
   req.volume       = lot;
   req.magic        = InpMagicNumber;
   req.deviation    = 50;
   req.type_filling = fill_mode;
   req.comment      = "V8_SPK_HUNT";

   if(tr.is_boom)
   {
      req.type  = ORDER_TYPE_BUY;
      req.price = tick.ask;
      req.tp    = NormalizeDouble(tick.ask + tp_depth_pts, digits);
      req.sl    = NormalizeDouble(tick.bid - sl_dist_pts,  digits);
   }
   else
   {
      req.type  = ORDER_TYPE_SELL;
      req.price = tick.bid;
      req.tp    = NormalizeDouble(tick.bid - tp_depth_pts, digits);
      req.sl    = NormalizeDouble(tick.ask + sl_dist_pts,  digits);
   }

   bool sent = OrderSend(req, res);
   if(sent && res.retcode == TRADE_RETCODE_DONE)
   {
      ulong ticket = res.order;
      if(ticket == 0) ticket = res.deal;

      RegisterTrackedPosition(ticket, tr.name, tr.tick_counter, tick.time_msc, (int)req.type, lot, req.price, req.tp, req.sl);

      tr.entries_triggered++;
      tr.open_positions++;
      g_total_entries_all++;

      PrintFormat("[DerivBoomCrashHFT v8.00] >>> ENTREE CONVEXE LANCEE sur %s (%s %.2f lots | P0_Spike=%.2f%% | E[Payoff]=+%.2f pts | TP=%.2f | SL=%.2f) <<<",
                  tr.name, tr.is_boom ? "BUY" : "SELL", lot, p0_spike * 100.0, expected_payoff, req.tp, req.sl);
      return true;
   }
   else
   {
      tr.cooldown_until_tick = tr.tick_counter + 15;
      PrintFormat("[DerivBoomCrashHFT v8.00] AVERTISSEMENT : Rejet ordre sur %s (code=%d : %s)",
                  tr.name, res.retcode, res.comment);
   }
   return false;
}

//+------------------------------------------------------------------+
//| Traitement Tick par Tick d'un Indice                             |
//+------------------------------------------------------------------+
void ProcessSymbolTick(SymbolTracker &tr, int &active_symbols_count)
{
   MqlTick tick;
   if(!SymbolInfoTick(tr.name, tick))
      return;

   if(tick.bid <= 0.0 || tick.time_msc <= tr.last_time_msc)
      return;

   tr.last_time_msc   = tick.time_msc;
   tr.real_spread_pts = tick.ask - tick.bid;
   tr.breakeven_ticks = tr.real_spread_pts / MathMax(tr.abs_drift_per_tick, 1e-8);
   tr.tick_counter++;
   g_total_ticks_all++;

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
      tr.last_spike_amp      = MathAbs(delta);
      tr.ticks_since_spike   = 0;

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
   }
   else
   {
      tr.ticks_since_spike++;
   }

   if(tr.open_positions > 0)
      return;

   if(tr.tick_counter < tr.cooldown_until_tick)
      return;

   if(tr.ticks_since_spike < InpCooldownPostSpike)
      return;

   if(active_symbols_count >= InpMaxActiveSymbols)
      return;

   int c60 = 0;
   double p0_spike = EvaluateColabOnnxSpikeProbability(tr, c60);
   tr.last_ai_p0   = p0_spike;

   if(tr.last_hawkes_fast > InpMaxHawkesFast)
   {
      tr.ai_filtered_count++;
      g_total_ai_blocked++;
      return;
   }

   if(p0_spike >= InpThetaSpike)
   {
      if(OpenConvexSpikePosition(tr, tick, p0_spike))
         active_symbols_count++;
   }
}

//+------------------------------------------------------------------+
//| Scanner Global Execute sur OnTick et OnTimer                     |
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

   int active_symbols_count = ManageOpenPositionsAndExitSpikes();

   if(dd_pct >= InpMaxDrawdownPct || daily_loss_pct >= InpDailyLossPct)
   {
      g_emergency_stopped = true;
      Alert(StringFormat("[DerivBoomCrashHFT v8.00] ARRET D'URGENCE DECLENCHE (DD=%.2f%%, PerteJour=%.2f%%)", dd_pct, daily_loss_pct));
      return;
   }

   for(int i = 0; i < g_num_trackers; i++)
      ProcessSymbolTick(g_trackers[i], active_symbols_count);

   if(InpShowDashboard)
      UpdateDashboard(dd_pct, daily_loss_pct);
}

//+------------------------------------------------------------------+
//| Traitement des Transactions (Telemetry Server TP & Deal Closes)  |
//+------------------------------------------------------------------+
void OnTradeTransaction(const MqlTradeTransaction &trans,
                        const MqlTradeRequest &request,
                        const MqlTradeResult &result)
{
   if(trans.type == TRADE_TRANSACTION_DEAL_ADD)
   {
      ulong deal_ticket = trans.deal;
      if(deal_ticket > 0 && HistoryDealSelect(deal_ticket))
      {
         long deal_entry = HistoryDealGetInteger(deal_ticket, DEAL_ENTRY);
         if(deal_entry == DEAL_ENTRY_OUT)
         {
            ulong pos_id = HistoryDealGetInteger(deal_ticket, DEAL_POSITION_ID);
            UnregisterTrackedPosition(pos_id);

            string comment = HistoryDealGetString(deal_ticket, DEAL_COMMENT);
            double profit  = HistoryDealGetDouble(deal_ticket, DEAL_PROFIT);
            if(StringFind(comment, "tp") >= 0)
            {
               g_total_server_tp++;
               PrintFormat("[DerivBoomCrashHFT v8.00] $$$ HARD SERVER TP EXECUTE ! Deal=%d | Pos=%d | Profit=+%.2f USD $$$",
                           deal_ticket, pos_id, profit);
            }
         }
      }
   }
}

//+------------------------------------------------------------------+
//| Evenements Tick et Timer                                         |
//+------------------------------------------------------------------+
void OnTick()  { ScanAllBoomCrashSymbols(); }
void OnTimer() { ScanAllBoomCrashSymbols(); }
//+------------------------------------------------------------------+
