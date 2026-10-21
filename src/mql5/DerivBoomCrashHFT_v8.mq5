//+------------------------------------------------------------------+
//|                                        DerivBoomCrashHFT_v8.mq5 |
//|                    Copyright 2026, Direction Recherche Quant    |
//|                    https://github.com/Christ-yavn/bot-quant-    |
//+------------------------------------------------------------------+
//| PROTOCOLE GO / NO-GO QUALITE QUANTITATIVE (MANDAT SECTION 5) :  |
//| G0 : Backtest tick-a-tick multi-sessions, >= 300 trades,         |
//|      PF >= 1.5, E/trade > 0 sur >= 3 sessions distinctes.        |
//| G1 : Demo live 2 semaines lot min : >= 500 trades, PF >= 1.6,    |
//|      A_capture/A >= 0.90 (MESURE, pas estimation),               |
//|      rejets [Invalid stops] = 0, lift >= 1.4.                    |
//| G2 : Passage 1/8 Kelly seulement apres validation formelle G1.  |
//| G3 : +25% de risque par palier de 250 trades valides             |
//|      (lift >= 1.4, DD < 3%), sinon gel au palier courant.        |
//| Le verrou InpDemoAccountOnly reste ACTIF jusqu'a G1 inclus.      |
//|                                                                  |
//| v8.21 : FIX-1..FIX-10 de l'audit statique appliques :            |
//|  FIX-1  Curseur CopyTicks reel (plus de ticks perdus)            |
//|  FIX-2  Horloges coherentes + debit tick/s mesure pour l'age     |
//|  FIX-3  Urgence = flatten + gestion continue (entrees bloquees) |
//|  FIX-4  Capture ratio MESURE (PnL/MFE), pas de constante fixee   |
//|  FIX-5  Lift = Somme(spikes)/Somme(hazard de base a l'entree)    |
//|  FIX-6  Payoff conservateur : P(A>=TP)=exp(-TP/A_bar),           |
//|         derive payee = E[T|T<=M] = tau - M/(exp(M/tau)-1)        |
//|  FIX-7  Kelly calibre sur le SL serveur reel + marge slippage    |
//|  FIX-8  Symboles non calibres refuses (tous univers)            |
//|  FIX-9  Comptabilisation par position complete (deals OUT cumules)|
//|  FIX-10 Perte journaliere remise a zero chaque jour             |
//+------------------------------------------------------------------+
#property copyright   "Copyright 2026, Direction Recherche Quant"
#property link        "https://github.com/Christ-yavn/bot-quant-"
#property version     "8.22"
#property description "Deriv HFT Quant v8.22 - Spike Hunter Convexe (Positive Skew Engine)"
#property description "Inversion exacte de v7 : SELL sur Crash, BUY sur Boom (capture de spikes)."
#property description "v8.22 : elimine les rejets 10016, integrite des ticks, telemetrie honnete, Kelly aligne sur le SL reel."
#property strict

#resource "\\Files\\boom_crash_meta_brain.onnx" as uchar ExtColabOnnxBrain[]

#include <Trade\Trade.mqh>
CTrade trade;

//+------------------------------------------------------------------+
//| Enumerations                                                     |
//+------------------------------------------------------------------+
enum ENUM_SYMBOL_UNIVERSE
{
   UNIVERSE_AUDITED_TOP_LIFT     = 0, // 5 Symboles Audites Lift >= 1.4
   UNIVERSE_CALIBRATED_10        = 1, // 10 Symboles Calibres (avertissement lift bas pour 300/500/1000-boom)
   UNIVERSE_CURRENT_CHART_ONLY   = 2  // Graphique Actuel Uniquement (doit etre calibre)
};

enum ENUM_LOT_MODE
{
   LOT_MODE_MIN_BROKER           = 0,
   LOT_MODE_FIXED                = 1,
   LOT_MODE_FRACTIONAL_KELLY     = 2
};

//+------------------------------------------------------------------+
//| Inputs                                                           |
//+------------------------------------------------------------------+
input group "=== 1. Mode Inversion Convexe (Charlie Munger INVERT) ==="
input bool   InpPureConvexReversalMode      = true;   // [INVERT] Mode Inversion Miroir Pure v7 (Chasseur Convexe Actif)
input int    InpCycleEntryTicks             = 20;     // Cadence d'entree cyclique en derive calme (ticks)
input bool   InpEnforcePositivePayoff       = false;  // Exiger payoff mathematique theorique strict (>0)
input bool   InpUseColabOnnxBrain           = false;  // Utiliser cerveau ONNX (si disponible)
input bool   InpUseZeroCheatFeatures        = true;
input double InpThetaSpike                  = 0.05;   // Plancher de seuil P0 minimal
input double InpHazardLiftMultiplier         = 1.00;   // Multiplicateur vs base Poisson (1.00x)
input double InpMaxHawkesFast               = 2.50;

input group "=== 2. Univers & Filtres d'Entree ==="
input ENUM_SYMBOL_UNIVERSE InpSymbolUniverse = UNIVERSE_AUDITED_TOP_LIFT;
input bool   InpAutoOpenAuditedCharts        = true;  // Ouvrir les graphiques de l'univers
input int    InpCooldownPostSpike           = 15;
input double InpMaxSpreadDriftMult           = 80.0;
input int    InpMaxActiveSymbols            = 3;
input int    InpScannerTimerMs              = 50;
input int    InpMaxTicksPerScan             = 500;    // FIX-1 : max ticks traites par scan par symbole

input group "=== 3. Sortie Hybride : TP Dur Serveur + Watchdog + Stop Temporel ==="
input int    InpTimeStopTicks               = 60;     // M* strict (ticks broker reels)
input double InpTakeProfitRatio             = 0.8;    // k_TP * E[A]
input double InpEmergencySlMult             = 2.0;    // SL = 2.0 * L_max
input bool   InpEnableWatchdog              = true;
input double InpWatchdogFloorMinUsd         = 0.10;
input double InpWatchdogFloorSpikeRatio     = 0.30;

input group "=== 4. Kelly Convexe & Dimensionnement ==="
input ENUM_LOT_MODE InpLotMode              = LOT_MODE_MIN_BROKER;
input double InpFixedLot                    = 0.20;
input double InpKellyFraction               = 0.01;   // 1/8 Kelly (~1% equity)
input bool   InpUseUsdRiskCap               = false;
input double InpMaxRiskUsdPerTrade          = 2.50;
input double InpMaxKellyOverstepRatio       = 1.30;   // Refus si arrondi > 1.30x cible
input double InpSlippageBufferMult          = 1.25;   // FIX-7 : marge slippage sur le risque SL

input group "=== 5. Moniteur de Lift Roulant (Estimateur Honnête) ==="
input bool   InpEnableLiftMonitor           = true;
input int    InpLiftWindowTradesSymbol      = 200;
input int    InpLiftMinTradesSymbol         = 50;     // trades min avant 1ere evaluation
input double InpMinObservedLiftSymbol       = 1.30;
input int    InpLiftWindowTradesGlobal      = 500;
input int    InpLiftMinTradesGlobal         = 100;
input double InpMinObservedLiftGlobal       = 1.30;

input group "=== 6. Securite Globale & Coupe-Circuits ==="
input bool   InpDemoAccountOnly             = true;
input double InpDailyLossPct                = 2.0;    // FIX-10 : reset chaque jour
input double InpMaxDrawdownPct              = 10.0;
input ulong  InpMagicNumber                 = 20261020;
input bool   InpShowDashboard               = true;

//+------------------------------------------------------------------+
//| Structures                                                       |
//+------------------------------------------------------------------+
#define MAX_LIFT_WINDOW_SYMBOL 200
#define MAX_LIFT_WINDOW_GLOBAL 500
#define MAX_TRACKED_POS        64

struct SymbolTracker
{
   string   name;
   int      symbol_id;
   bool     is_boom;
   bool     is_calibrated;
   double   abs_drift_per_tick;
   double   mean_spike_pts;
   double   mean_tau_ticks;
   double   spike_threshold;
   double   real_spread_pts;
   double   breakeven_ticks;

   // FIX-1 : curseur de ticks reel
   long     last_time_msc;      // dernier time_msc CONSOMME (Unix ms broker)
   int      last_ms_consumed;   // nb de ticks deja consommes a ce time_msc
   long     first_time_msc;    // premier tick traite (mesure debit)
   double   ticks_per_sec;      // debit mesure (FIX-2)

   double   last_price;
   double   recent_prices[4];
   int      recent_prices_count;
   double   last_delta;
   double   last_spike_amp;
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
   bool     spike_watchdog_pending;   // FIX-5 : arme par detection tick, pas par commentaire
   bool     disabled_low_lift;

   // FIX-5 : estimateur honnete par symbole
   int      lift_spike_hist[MAX_LIFT_WINDOW_SYMBOL];
   double   lift_base_hist[MAX_LIFT_WINDOW_SYMBOL];
   int      lift_head;
   int      lift_count;
   int      lift_spikes_sum;
   double   lift_base_sum;
   double   current_observed_lift;
   string   calib_source;
};

struct PositionEntryTracker
{
   ulong    ticket;               // position id / ticket
   string   symbol;
   long     entry_tick;
   long     entry_time_msc;      // Unix ms broker (FIX-2)
   int      pos_type;
   double   volume;              // volume initial
   double   open_price;
   double   target_tp;
   double   emergency_sl;
   double   entry_p0;
   double   expected_payoff_pts;
   double   entry_base_hazard;   // FIX-5 : hazard de base au moment de l'entree
   bool     spike_observed;      // FIX-4/5 : spike reellement vu pendant la position
   double   mfe_usd;             // FIX-4 : Max Favorable Excursion (USD)
   double   closed_pnl;          // FIX-9 : PnL cumule des deals OUT
   double   closed_volume;
   string   last_exit_reason;
   bool     is_active;
};

struct ClosingTicketLock
{
   ulong    ticket;
   long     sent_msc;
};

//+------------------------------------------------------------------+
//| Variables Globales                                               |
//+------------------------------------------------------------------+
SymbolTracker g_trackers[];
int           g_num_trackers = 0;
long          g_onnx_handle  = INVALID_HANDLE;
bool          g_onnx_ready   = false;

double        g_initial_equity      = 0.0;   // reference drawdown session
double        g_day_start_equity     = 0.0;   // FIX-10
long          g_current_day          = 0;
double        g_peak_equity          = 0.0;
bool          g_emergency_stopped    = false;

PositionEntryTracker g_pos_tracker[MAX_TRACKED_POS];
ClosingTicketLock    g_closing_locks[32];
int                  g_closing_locks_count = 0;

// FIX-5 : fenetres globales honnetes (spike, hazard de base par trade)
int           g_glob_spike_hist[MAX_LIFT_WINDOW_GLOBAL];
double        g_glob_base_hist[MAX_LIFT_WINDOW_GLOBAL];
int           g_glob_head          = 0;
int           g_glob_count         = 0;
int           g_glob_spikes_sum    = 0;
double        g_glob_base_sum      = 0.0;
double        g_global_observed_lift = 0.0;  // 0 = non encore mesurable

long g_total_ticks_all=0, g_total_spikes_all=0, g_total_entries_all=0, g_total_ai_blocked=0;
long g_total_server_tp=0, g_total_watchdog_green=0, g_total_thesis_consumed=0;
long g_total_timestop_closed=0, g_total_max_risk_cut=0, g_total_orphan_flattens=0;
long g_total_finalized_trades=0;

string g_csv_log_filename = "v8_closed_positions.csv";

//+------------------------------------------------------------------+
//| Helpers calibrage / hazard                                       |
//+------------------------------------------------------------------+
double BaseHazardOf(const SymbolTracker &tr)
{
   return 1.0 - MathExp(-((double)InpTimeStopTicks) / MathMax(tr.mean_tau_ticks, 1.0));
}

double ThetaEffOf(const SymbolTracker &tr)
{
   return MathMax(InpThetaSpike, BaseHazardOf(tr) * InpHazardLiftMultiplier);
}

// FIX-8 : un symbole est calibre s'il figure dans la table forensique
bool IsCalibratedSymbol(const string sym)
{
   string s = sym; StringToLower(s);
   if(StringFind(s, "crash 600") >= 0) return true;
   if(StringFind(s, "crash 900") >= 0) return true;
   if(StringFind(s, "boom 900")  >= 0) return true;
   if(StringFind(s, "boom 600")  >= 0) return true;
   if(StringFind(s, "crash 1000")>= 0) return true;
   if(StringFind(s, "boom 1000") >= 0) return true;
   if(StringFind(s, "boom 500")  >= 0) return true;
   if(StringFind(s, "crash 500") >= 0) return true;
   if(StringFind(s, "boom 300")  >= 0) return true;
   if(StringFind(s, "crash 300") >= 0) return true;
   return false;
}

//+------------------------------------------------------------------+
//| Idempotence fermetures                                           |
//+------------------------------------------------------------------+
bool IsTicketClosingInFlight(ulong ticket)
{
   long now_msc = (long)GetTickCount64();
   for(int i = 0; i < g_closing_locks_count; i++)
      if(g_closing_locks[i].ticket == ticket)
      {
         if(now_msc - g_closing_locks[i].sent_msc < 2500) return true;
         g_closing_locks[i] = g_closing_locks[g_closing_locks_count - 1];
         g_closing_locks_count--;
         return false;
      }
   return false;
}

void MarkTicketClosingInFlight(ulong ticket)
{
   if(g_closing_locks_count < 32)
   {
      g_closing_locks[g_closing_locks_count].ticket = ticket;
      g_closing_locks[g_closing_locks_count].sent_msc = (long)GetTickCount64();
      g_closing_locks_count++;
   }
}

void ClearTicketClosingLock(ulong ticket)
{
   for(int i = 0; i < g_closing_locks_count; i++)
      if(g_closing_locks[i].ticket == ticket)
      {
         g_closing_locks[i] = g_closing_locks[g_closing_locks_count - 1];
         g_closing_locks_count--;
         return;
      }
}

//+------------------------------------------------------------------+
//| FIX-2 : Persistance coherente (horloge broker Unix ms)           |
//+------------------------------------------------------------------+
void SavePositionGlobalVariable(ulong ticket, long entry_msc_broker)
{
   GlobalVariableSet("V8_ENT_" + IntegerToString((long)ticket), (double)entry_msc_broker);
}

void DeletePositionGlobalVariable(ulong ticket)
{
   string gv = "V8_ENT_" + IntegerToString((long)ticket);
   if(GlobalVariableCheck(gv)) GlobalVariableDel(gv);
}

// Debit tick/s mesure, persiste pour la reconstruction d'age
void SaveTrackerRateGV(const SymbolTracker &tr)
{
   if(tr.ticks_per_sec > 0.01)
      GlobalVariableSet("V8_TPS_" + tr.name, tr.ticks_per_sec);
}

double LoadTrackerRateGV(const string sym)
{
   string gv = "V8_TPS_" + sym;
   if(GlobalVariableCheck(gv))
   {
      double v = GlobalVariableGet(gv);
      if(v > 0.01) return v;
   }
   return 0.0;
}

//+------------------------------------------------------------------+
//| Registre des positions                                           |
//+------------------------------------------------------------------+
void RegisterTrackedPosition(ulong ticket, const string sym, long current_tick, long entry_msc,
                             int ptype, double vol, double price, double tp, double sl,
                             double p0, double payoff, double base_hazard)
{
   for(int i = 0; i < MAX_TRACKED_POS; i++)
      if(!g_pos_tracker[i].is_active || g_pos_tracker[i].ticket == ticket)
      {
         g_pos_tracker[i].ticket              = ticket;
         g_pos_tracker[i].symbol              = sym;
         g_pos_tracker[i].entry_tick          = current_tick;
         g_pos_tracker[i].entry_time_msc      = entry_msc;
         g_pos_tracker[i].pos_type            = ptype;
         g_pos_tracker[i].volume              = vol;
         g_pos_tracker[i].open_price          = price;
         g_pos_tracker[i].target_tp           = tp;
         g_pos_tracker[i].emergency_sl        = sl;
         g_pos_tracker[i].entry_p0            = p0;
         g_pos_tracker[i].expected_payoff_pts = payoff;
         g_pos_tracker[i].entry_base_hazard   = base_hazard;
         g_pos_tracker[i].spike_observed      = false;
         g_pos_tracker[i].mfe_usd             = 0.0;
         g_pos_tracker[i].closed_pnl         = 0.0;
         g_pos_tracker[i].closed_volume      = 0.0;
         g_pos_tracker[i].last_exit_reason   = "";
         g_pos_tracker[i].is_active          = true;
         SavePositionGlobalVariable(ticket, entry_msc);
         return;
      }
}

int FindTrackedPositionIndex(ulong ticket)
{
   for(int i = 0; i < MAX_TRACKED_POS; i++)
      if(g_pos_tracker[i].is_active && g_pos_tracker[i].ticket == ticket)
         return i;
   return -1;
}

void UnregisterTrackedPosition(ulong ticket)
{
   int idx = FindTrackedPositionIndex(ticket);
   if(idx >= 0) g_pos_tracker[idx].is_active = false;
   ClearTicketClosingLock(ticket);
   DeletePositionGlobalVariable(ticket);
}

//+------------------------------------------------------------------+
//| Broker helpers                                                   |
//+------------------------------------------------------------------+
double GetBrokerMinStopDistancePts(const string sym)
{
   double pt        = SymbolInfoDouble(sym, SYMBOL_POINT);
   long   stops_lvl = SymbolInfoInteger(sym, SYMBOL_TRADE_STOPS_LEVEL);
   long   freeze    = SymbolInfoInteger(sym, SYMBOL_TRADE_FREEZE_LEVEL);
   return (double)(MathMax(stops_lvl, freeze) + 5) * pt;
}

ENUM_ORDER_TYPE_FILLING GetSupportedFillingMode(const string sym)
{
   uint filling = (uint)SymbolInfoInteger(sym, SYMBOL_FILLING_MODE);
   if((filling & SYMBOL_FILLING_IOC) != 0) return ORDER_FILLING_IOC;
   if((filling & SYMBOL_FILLING_FOK) != 0) return ORDER_FILLING_FOK;
   return ORDER_FILLING_RETURN;
}

//+------------------------------------------------------------------+
//| ONNX                                                             |
//+------------------------------------------------------------------+
bool InitColabOnnxBrain()
{
   g_onnx_ready  = false;
   g_onnx_handle = INVALID_HANDLE;
   if(!InpUseColabOnnxBrain) return false;

   g_onnx_handle = OnnxCreateFromBuffer(ExtColabOnnxBrain, ONNX_DEFAULT);
   if(g_onnx_handle == INVALID_HANDLE)
      g_onnx_handle = OnnxCreate("boom_crash_meta_brain.onnx", ONNX_DEFAULT);
   if(g_onnx_handle == INVALID_HANDLE)
   {
      PrintFormat("[v8.22] ONNX absent (code=%d) -> Moteur physique Poisson/Hawkes.", GetLastError());
      return false;
   }

   const long in_shape[]   = {1, 14};
   const long out_label[]  = {1};
   const long out_proba[]  = {1, 2};
   if(!OnnxSetInputShape(g_onnx_handle, 0, in_shape))
   {
      OnnxRelease(g_onnx_handle);
      g_onnx_handle = INVALID_HANDLE;
      return false;
   }
   OnnxSetOutputShape(g_onnx_handle, 0, out_label);
   OnnxSetOutputShape(g_onnx_handle, 1, out_proba);
   g_onnx_ready = true;
   Print("[v8.22] >>> CERVEAU ONNX v7 (14 features Hawkes) ACTIF <<<");
   return true;
}

//+------------------------------------------------------------------+
//| Inference P0(spike dans M* ticks)                                |
//+------------------------------------------------------------------+
double EvaluateColabOnnxSpikeProbability(SymbolTracker &tr, int &out_c60)
{
   double mean_sp  = MathMax(tr.mean_spike_pts, 1e-6);
   double mean_tau = MathMax(tr.mean_tau_ticks, 1.0);
   double drift    = MathMax(tr.abs_drift_per_tick, 1e-8);

   double tau1 = 1.0, tau2 = 1.0, tau3 = 1.0;
   int n = tr.spike_history_count;
   if(n >= 2) tau1 = (double)(tr.spike_history_ticks[n-1] - tr.spike_history_ticks[n-2]) / mean_tau;
   if(n >= 3) tau2 = (double)(tr.spike_history_ticks[n-2] - tr.spike_history_ticks[n-3]) / mean_tau;
   if(n >= 4) tau3 = (double)(tr.spike_history_ticks[n-3] - tr.spike_history_ticks[n-4]) / mean_tau;

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
   out_c60 = c60;

   double post3_vel = 1.0;
   if(tr.recent_prices_count >= 4)
   {
      double move3 = tr.is_boom ? (tr.recent_prices[0] - tr.recent_prices[3])
                                : (tr.recent_prices[3] - tr.recent_prices[0]);
      post3_vel = MathMax(-2.0, MathMin(2.5, move3 / (3.0 * drift)));
   }

   double be_ticks       = tr.real_spread_pts / drift;
   double spike_amp_norm = (tr.last_spike_amp > 0.0) ? (tr.last_spike_amp / mean_sp) : 1.0;

   // Repli physique exact (Poisson + boost Hawkes borne)
   if(!g_onnx_ready || g_onnx_handle == INVALID_HANDLE)
   {
      double base_p0 = 1.0 - MathExp(-((double)InpTimeStopTicks) / mean_tau);
      double p0 = base_p0 * (1.0 + 0.50 * MathMax(0.0, h_fast - 0.30));
      return MathMax(0.01, MathMin(0.85, p0));
   }

   float x[1][14];
   if(InpUseZeroCheatFeatures)
   {
      double e_h_fast = MathExp(-0.05*3.0)  + 1.0/(0.05*mean_tau);
      double e_h_med  = MathExp(-0.015*3.0) + 1.0/(0.015*mean_tau);
      double e_h_slow = MathExp(-0.003*3.0) + 1.0/(0.003*mean_tau);
      double hfe = h_fast - e_h_fast, hme = h_med - e_h_med, hse = h_slow - e_h_slow;
      double c60e  = (double)MathMax(1, c60)  - (1.0 + 60.0/mean_tau);
      double c300e = (double)MathMax(1, c300) - (1.0 + 300.0/mean_tau);

      x[0][0]  = (float)(tau1 / (tau2 + 0.10));
      x[0][1]  = (float)(hfe - hme);
      x[0][2]  = (float)spike_amp_norm;
      x[0][3]  = (float)tau1;
      x[0][4]  = (float)tau2;
      x[0][5]  = (float)tau3;
      x[0][6]  = (float)hfe;
      x[0][7]  = (float)hme;
      x[0][8]  = (float)hse;
      x[0][9]  = (float)c60e;
      x[0][10] = (float)c300e;
      x[0][11] = (float)post3_vel;
      x[0][12] = (float)(hme - hse);
      x[0][13] = (float)((spike_amp_norm - 1.0) * hfe);
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
      x[0][13] = (float)(be_ticks / mean_tau);
   }

   long out_label[1];
   float out_proba[1][2];
   if(!OnnxRun(g_onnx_handle, ONNX_NO_CONVERSION, x, out_label, out_proba))
      return 0.10;

   double p0 = 1.0 - (double)out_proba[0][1];
   return MathMax(0.01, MathMin(0.85, p0));
}

//+------------------------------------------------------------------+
//| FIX-7 : SL serveur reel + marge slippage (utilise par Kelly)     |
//+------------------------------------------------------------------+
double ComputeSlDistPts(const SymbolTracker &tr)
{
   double lmax_pts    = tr.abs_drift_per_tick * InpTimeStopTicks + tr.real_spread_pts;
   double min_stop    = GetBrokerMinStopDistancePts(tr.name);
   return MathMax(min_stop, InpEmergencySlMult * lmax_pts);
}

double ComputeConvexLotSize(SymbolTracker &tr, double sl_dist_pts)
{
   double vol_min  = SymbolInfoDouble(tr.name, SYMBOL_VOLUME_MIN);
   double vol_max  = SymbolInfoDouble(tr.name, SYMBOL_VOLUME_MAX);
   double vol_step = SymbolInfoDouble(tr.name, SYMBOL_VOLUME_STEP);
   if(vol_min  <= 0.0) vol_min  = 0.20;
   if(vol_step <= 0.0) vol_step = 0.01;

   if(InpLotMode == LOT_MODE_MIN_BROKER)
   {
      // Mode validation G1 : avertissement si le risque reel depasse la cible Kelly
      double tv = SymbolInfoDouble(tr.name, SYMBOL_TRADE_TICK_VALUE);
      double ts = SymbolInfoDouble(tr.name, SYMBOL_TRADE_TICK_SIZE);
      if(ts <= 0.0) ts = SymbolInfoDouble(tr.name, SYMBOL_POINT);
      if(tv > 0.0 && ts > 0.0)
      {
         double min_risk = (sl_dist_pts * InpSlippageBufferMult / ts) * tv * vol_min;
         double target   = InpKellyFraction * AccountInfoDouble(ACCOUNT_EQUITY);
         if(InpUseUsdRiskCap && InpMaxRiskUsdPerTrade > 0.0) target = MathMin(target, InpMaxRiskUsdPerTrade);
         if(min_risk > target)
            PrintFormat("[v8.22] AVERTISSEMENT %s : risque au lot min (%.2f USD) > cible Kelly (%.2f USD) -> mode validation G1.",
                        tr.name, min_risk, target);
      }
      return vol_min;
   }

   if(InpLotMode == LOT_MODE_FIXED)
   {
      double clamped = MathMax(vol_min, MathMin(vol_max, InpFixedLot));
      return MathFloor(clamped / vol_step + 1e-9) * vol_step;
   }

   // LOT_MODE_FRACTIONAL_KELLY -> base = SL serveur reel + marge slippage
   double equity          = AccountInfoDouble(ACCOUNT_EQUITY);
   double target_risk_usd = InpKellyFraction * equity;
   if(InpUseUsdRiskCap && InpMaxRiskUsdPerTrade > 0.0)
      target_risk_usd = MathMin(target_risk_usd, InpMaxRiskUsdPerTrade);

   double tick_val = SymbolInfoDouble(tr.name, SYMBOL_TRADE_TICK_VALUE);
   double tick_sz  = SymbolInfoDouble(tr.name, SYMBOL_TRADE_TICK_SIZE);
   if(tick_sz  <= 0.0) tick_sz  = SymbolInfoDouble(tr.name, SYMBOL_POINT);
   if(tick_val <= 0.0) tick_val = 1.0;

   double risk_pts_minlot = sl_dist_pts * InpSlippageBufferMult;
   double risk_usd_minlot = (risk_pts_minlot / tick_sz) * tick_val * vol_min;
   if(risk_usd_minlot <= 0.01) risk_usd_minlot = 0.25;

   // Si meme le lot MINIMUM depasse la cible -> REFUS (pas de clamp silencieux vers vol_min)
   if(risk_usd_minlot > InpMaxKellyOverstepRatio * target_risk_usd)
   {
      PrintFormat("[v8.22] REFUS KELLY %s : risque au lot min (%.2f USD) > %.2fx cible (%.2f USD).",
                  tr.name, risk_usd_minlot, InpMaxKellyOverstepRatio, target_risk_usd);
      return 0.0;
   }

   double raw_lot     = vol_min * (target_risk_usd / risk_usd_minlot);
   double stepped_lot = MathFloor(raw_lot / vol_step + 1e-9) * vol_step;
   if(stepped_lot < vol_min) stepped_lot = 0.0; // refus si sous le minimum

   double effective_risk = (stepped_lot / vol_min) * risk_usd_minlot;
   if(effective_risk > InpMaxKellyOverstepRatio * target_risk_usd)
   {
      PrintFormat("[v8.22] REFUS KELLY %s : risque effectif (%.2f USD) > %.2fx cible (%.2f USD).",
                  tr.name, effective_risk, InpMaxKellyOverstepRatio, target_risk_usd);
      return 0.0;
   }
   return MathMin(vol_max, stepped_lot);
}

//+------------------------------------------------------------------+
//| Calibration d'un tracker                                         |
//+------------------------------------------------------------------+
void InitAndCalibrateTracker(SymbolTracker &tr, const string sym)
{
   tr.name             = sym;
   tr.is_calibrated    = IsCalibratedSymbol(sym);
   string s            = sym;
   StringToLower(s);
   tr.is_boom          = (StringFind(s, "boom") >= 0);
   tr.symbol_id        = 0;
   tr.last_time_msc    = 0;
   tr.last_ms_consumed = 0;
   tr.first_time_msc   = 0;
   tr.ticks_per_sec    = LoadTrackerRateGV(sym);
   tr.recent_prices_count = 0;
   tr.last_price       = 0.0;
   tr.last_delta       = 0.0;
   tr.last_spike_amp   = 0.0;
   tr.last_order_sent_msc = 0;
   tr.tick_counter     = 0;
   tr.ticks_since_spike= 1000;
   tr.spikes_detected  = 0;
   tr.entries_triggered= 0;
   tr.ai_filtered_count= 0;
   tr.last_ai_p0       = 0.0;
   tr.last_hawkes_fast = 0.0;
   tr.cooldown_until_tick = 0;
   tr.spike_history_count = 0;
   tr.open_positions   = 0;
   tr.spike_watchdog_pending = false;
   tr.disabled_low_lift = false;
   tr.lift_head = 0; tr.lift_count = 0; tr.lift_spikes_sum = 0; tr.lift_base_sum = 0.0;
   tr.current_observed_lift = 0.0;
   tr.calib_source    = "TABLE_FORENSIC";
   for(int w = 0; w < MAX_LIFT_WINDOW_SYMBOL; w++) { tr.lift_spike_hist[w] = 0; tr.lift_base_hist[w] = 0.0; }
   for(int r = 0; r < 4; r++) tr.recent_prices[r] = 0.0;
   for(int k = 0; k < 32; k++) { tr.spike_history_ticks[k] = -100000; tr.spike_history_amps[k] = 0.0; }

   tr.abs_drift_per_tick = 0.01622;
   tr.mean_spike_pts     = 17.015;
   tr.mean_tau_ticks     = 1000.0;

   if(StringFind(s, "crash 600")  >= 0) { tr.symbol_id = 5; tr.abs_drift_per_tick = 0.03773; tr.mean_spike_pts = 22.904; tr.mean_tau_ticks = 571.5; }
   else if(StringFind(s, "crash 900") >= 0) { tr.symbol_id = 3; tr.abs_drift_per_tick = 0.01900; tr.mean_spike_pts = 17.314; tr.mean_tau_ticks = 907.3; }
   else if(StringFind(s, "boom 900")  >= 0) { tr.symbol_id = 2; tr.abs_drift_per_tick = 0.00972; tr.mean_spike_pts = 8.865;  tr.mean_tau_ticks = 911.4; }
   else if(StringFind(s, "boom 600")  >= 0) { tr.symbol_id = 4; tr.abs_drift_per_tick = 0.00894; tr.mean_spike_pts = 5.155;  tr.mean_tau_ticks = 586.5; }
   else if(StringFind(s, "crash 1000")>= 0) { tr.symbol_id = 1; tr.abs_drift_per_tick = 0.00636; tr.mean_spike_pts = 5.887;  tr.mean_tau_ticks = 961.0; }
   else if(StringFind(s, "boom 1000") >= 0) { tr.symbol_id = 0; tr.abs_drift_per_tick = 0.01551; tr.mean_spike_pts = 17.015; tr.mean_tau_ticks = 1066.6; }
   else if(StringFind(s, "boom 500")  >= 0) { tr.symbol_id = 6; tr.abs_drift_per_tick = 0.01128; tr.mean_spike_pts = 5.825;  tr.mean_tau_ticks = 486.9; }
   else if(StringFind(s, "crash 500") >= 0) { tr.symbol_id = 7; tr.abs_drift_per_tick = 0.00623; tr.mean_spike_pts = 2.991;  tr.mean_tau_ticks = 480.0; }
   else if(StringFind(s, "boom 300")  >= 0) { tr.symbol_id = 8; tr.abs_drift_per_tick = 0.00414; tr.mean_spike_pts = 1.324;  tr.mean_tau_ticks = 289.3; }
   else if(StringFind(s, "crash 300") >= 0) { tr.symbol_id = 9; tr.abs_drift_per_tick = 0.02080; tr.mean_spike_pts = 6.863;  tr.mean_tau_ticks = 297.3; }

   tr.last_spike_amp = tr.mean_spike_pts;

   // Calibration vivante 5K (seuils v7 stricts : 3.5x)
   MqlTick ticks[];
   int copied = CopyTicks(sym, ticks, COPY_TICKS_ALL, 0, 5000);
   if(copied > 200)
   {
      double sum_drift = 0.0; int cnt_drift = 0;
      for(int i = 1; i < copied; i++)
      {
         double p0 = (ticks[i-1].last > 0.0) ? ticks[i-1].last : 0.5*(ticks[i-1].bid + ticks[i-1].ask);
         double p1 = (ticks[i].last   > 0.0) ? ticks[i].last   : 0.5*(ticks[i].bid + ticks[i].ask);
         double d  = p1 - p0;
         if((tr.is_boom && d < 0.0) || (!tr.is_boom && d > 0.0)) { sum_drift += MathAbs(d); cnt_drift++; }
      }
      if(cnt_drift > 100)
      {
         double live_drift = sum_drift / cnt_drift;
         double sum_spike = 0.0; int cnt_spike = 0; int last_sp_i = 0;
         for(int i = 1; i < copied; i++)
         {
            double p0 = (ticks[i-1].last > 0.0) ? ticks[i-1].last : 0.5*(ticks[i-1].bid + ticks[i-1].ask);
            double p1 = (ticks[i].last   > 0.0) ? ticks[i].last   : 0.5*(ticks[i].bid + ticks[i].ask);
            double d  = p1 - p0;
            if((tr.is_boom && d > 3.5*live_drift) || (!tr.is_boom && d < -3.5*live_drift))
            {
               sum_spike += MathAbs(d); cnt_spike++; last_sp_i = i;
               tr.last_spike_amp = MathAbs(d);
               long rel_tick = (long)(i - copied);
               if(tr.spike_history_count < 32)
               { tr.spike_history_ticks[tr.spike_history_count] = rel_tick; tr.spike_history_amps[tr.spike_history_count] = MathAbs(d); tr.spike_history_count++; }
               else
               {
                  for(int m = 0; m < 31; m++) { tr.spike_history_ticks[m] = tr.spike_history_ticks[m+1]; tr.spike_history_amps[m] = tr.spike_history_amps[m+1]; }
                  tr.spike_history_ticks[31] = rel_tick; tr.spike_history_amps[31] = MathAbs(d);
               }
            }
         }
         tr.abs_drift_per_tick = live_drift;
         tr.ticks_since_spike  = (long)(copied - 1 - last_sp_i);
         if(cnt_spike >= 3) { tr.mean_spike_pts = sum_spike / cnt_spike; tr.calib_source = "LIVE_5K_V7_RESTORED"; }
      }
      for(int r = 0; r < 4; r++)
      {
         int idx = copied - 4 + r;
         tr.recent_prices[r] = (ticks[idx].last > 0.0) ? ticks[idx].last : 0.5*(ticks[idx].bid + ticks[idx].ask);
      }
      tr.recent_prices_count = 4;
      // Amorcage du debit mesure
      if(copied > 2)
      {
         tr.first_time_msc = ticks[copied-1].time_msc;
         if(tr.ticks_per_sec <= 0.01)
         {
            long span = ticks[copied-1].time_msc - ticks[0].time_msc;
            if(span > 1000)
               tr.ticks_per_sec = (double)(copied - 1) / ((double)span / 1000.0);
         }
      }
   }

   MqlTick live_t;
   if(SymbolInfoTick(sym, live_t) && live_t.ask > live_t.bid)
      tr.real_spread_pts = live_t.ask - live_t.bid;
   else
      tr.real_spread_pts = 60.0 * tr.abs_drift_per_tick;

   tr.breakeven_ticks = tr.real_spread_pts / MathMax(tr.abs_drift_per_tick, 1e-8);
   tr.spike_threshold = MathMax(3.5 * tr.abs_drift_per_tick, 0.25 * tr.mean_spike_pts); // BUG-7 : seuils v7

   int dummy = 0;
   tr.last_ai_p0 = EvaluateColabOnnxSpikeProbability(tr, dummy);

   double base_h = BaseHazardOf(tr);
   double th_eff = ThetaEffOf(tr);
   PrintFormat("[v8.22 CALIB] %s | calibre=%s | drift=%.5f | amp=%.3f | tau=%.1ft | base_h=%.2f%% | theta_eff=%.2f%% | TPS=%.2f | src=%s",
               tr.name, tr.is_calibrated ? "OUI" : "NON", tr.abs_drift_per_tick, tr.mean_spike_pts,
               tr.mean_tau_ticks, base_h*100.0, th_eff*100.0, tr.ticks_per_sec, tr.calib_source);
}

//+------------------------------------------------------------------+
//| Univers (FIX-8 : refus des symboles non calibres)                |
//+------------------------------------------------------------------+
bool AddSymbolToScanner(const string sym)
{
   for(int i = 0; i < g_num_trackers; i++)
      if(g_trackers[i].name == sym) return true;

   if(!IsCalibratedSymbol(sym))
   {
      PrintFormat("[v8.22] REFUS FIX-8 : %s n'est PAS dans la table de calibration forensique -> exclu.", sym);
      return false;
   }

   if(!SymbolSelect(sym, true)) return false;

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
      if(!AddSymbolToScanner(_Symbol))
      {
         Alert("[v8.22] ECHEC INIT : le symbole du graphique courant n'est pas calibre. Changez de graphique.");
      }
      return;
   }

   if(InpSymbolUniverse == UNIVERSE_AUDITED_TOP_LIFT)
   {
      string top5[] = { "Crash 600 Index", "Crash 900 Index", "Boom 900 Index", "Boom 600 Index", "Crash 1000 Index" };
      for(int i = 0; i < ArraySize(top5); i++) AddSymbolToScanner(top5[i]);
      return;
   }

   string calib10[] = {
      "Boom 1000 Index", "Crash 1000 Index", "Boom 900 Index", "Crash 900 Index",
      "Boom 600 Index", "Crash 600 Index", "Boom 500 Index", "Crash 500 Index",
      "Boom 300 Index", "Crash 300 Index"
   };
   for(int i = 0; i < ArraySize(calib10); i++) AddSymbolToScanner(calib10[i]);
}

//+------------------------------------------------------------------+
//| FIX-3 : fermeture totale d'urgence                               |
//+------------------------------------------------------------------+
void CloseAllBotPositions(const string reason)
{
   int total = PositionsTotal();
   for(int p = total - 1; p >= 0; p--)
   {
      ulong ticket = PositionGetTicket(p);
      if(ticket == 0) continue;
      if((ulong)PositionGetInteger(POSITION_MAGIC) != InpMagicNumber) continue;
      string   psym = PositionGetString(POSITION_SYMBOL);
      double   vol  = PositionGetDouble(POSITION_VOLUME);
      ENUM_POSITION_TYPE pt = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
      CloseSinglePositionTicket(ticket, psym, pt, vol, reason);
   }
}

//+------------------------------------------------------------------+
//| Fermeture idempotente                                            |
//+------------------------------------------------------------------+
bool CloseSinglePositionTicket(ulong ticket, const string sym, ENUM_POSITION_TYPE ptype, double volume, const string reason)
{
   if(IsTicketClosingInFlight(ticket)) return false;

   MqlTick tick;
   if(!SymbolInfoTick(sym, tick)) return false;

   MqlTradeRequest req; MqlTradeResult res;
   ZeroMemory(req); ZeroMemory(res);
   req.action       = TRADE_ACTION_DEAL;
   req.position     = ticket;
   req.symbol       = sym;
   req.volume       = volume;
   req.magic        = InpMagicNumber;
   req.deviation    = 50;
   req.type_filling = GetSupportedFillingMode(sym);
   req.comment      = reason;
   if(ptype == POSITION_TYPE_BUY) { req.type = ORDER_TYPE_SELL; req.price = tick.bid; }
   else                           { req.type = ORDER_TYPE_BUY;  req.price = tick.ask; }

   MarkTicketClosingInFlight(ticket);
   bool sent = OrderSend(req, res);
   if(sent && res.retcode == TRADE_RETCODE_DONE)
   {
      UnregisterTrackedPosition(ticket);
      return true;
   }
   PrintFormat("[v8.22] Echec fermeture %d (%s) : retcode=%d err=%d", ticket, reason, res.retcode, GetLastError());
   return false;
}

//+------------------------------------------------------------------+
//| FIX-4/5/9 : finalisation d'une position COMPLETE                 |
//+------------------------------------------------------------------+
void FinalizeClosedPosition(int pos_idx)
{
   PositionEntryTracker pos = g_pos_tracker[pos_idx]; // copie pour log apres unregister

   // Capture ratio MESURE : PnL realise / MFE (clamp 1.5, valeur honnete)
   double cap_ratio = 0.0;
   if(pos.closed_pnl > 0.0 && pos.mfe_usd > 0.01)
      cap_ratio = MathMin(1.5, pos.closed_pnl / pos.mfe_usd);

   // Spike capture = evenement reel : spike vu dans le flux de ticks PENDANT la position,
   // OU TP serveur encaisse (preuve directe d'un saut au-dela du TP).
   bool is_tp_exit  = (StringFind(pos.last_exit_reason, "tp") >= 0 && pos.closed_pnl > 0.0);
   bool is_capture  = (pos.spike_observed || is_tp_exit);

   UpdateLiftFinalized(pos.symbol, is_capture, pos.entry_base_hazard);

   g_total_finalized_trades++;
   LogTradeToCsv(pos.symbol, (pos.pos_type == POSITION_TYPE_BUY) ? "BUY" : "SELL",
                 pos.volume, pos.entry_p0, pos.expected_payoff_pts,
                 pos.last_exit_reason, pos.closed_pnl, cap_ratio, pos.mfe_usd, is_capture,
                 pos.entry_base_hazard);

   PrintFormat("[v8.22] POSITION FINALISEE %d %s | PnL=%+.2f USD | Sortie=%s | Capture=%.3f | MFE=%.2f | SpikeVu=%s",
               pos.ticket, pos.symbol, pos.closed_pnl, pos.last_exit_reason, cap_ratio,
               pos.mfe_usd, is_capture ? "OUI" : "NON");

   UnregisterTrackedPosition(pos.ticket);
}

//+------------------------------------------------------------------+
//| FIX-5 : Moniteur de lift honnete (ratio de Poisson)              |
//| lift = Somme(spike captures) / Somme(hazard de base a l'entree)  |
//+------------------------------------------------------------------+
void UpdateLiftFinalized(const string sym, bool is_capture, double base_hazard_at_entry)
{
   if(!InpEnableLiftMonitor) return;
   if(base_hazard_at_entry <= 1e-6) base_hazard_at_entry = 1e-6;

   // --- Par symbole ---
   for(int i = 0; i < g_num_trackers; i++)
   {
      if(g_trackers[i].name != sym) continue;

      if(g_trackers[i].lift_count >= InpLiftWindowTradesSymbol)
      {
         g_trackers[i].lift_spikes_sum -= g_trackers[i].lift_spike_hist[g_trackers[i].lift_head];
         g_trackers[i].lift_base_sum   -= g_trackers[i].lift_base_hist[g_trackers[i].lift_head];
      }
      else g_trackers[i].lift_count++;

      g_trackers[i].lift_spike_hist[g_trackers[i].lift_head] = is_capture ? 1 : 0;
      g_trackers[i].lift_base_hist[g_trackers[i].lift_head]  = base_hazard_at_entry;
      g_trackers[i].lift_head = (g_trackers[i].lift_head + 1) % InpLiftWindowTradesSymbol;
      if(is_capture) g_trackers[i].lift_spikes_sum++;
      g_trackers[i].lift_base_sum += base_hazard_at_entry;

      if(g_trackers[i].lift_count >= InpLiftMinTradesSymbol && g_trackers[i].lift_base_sum > 1e-6)
      {
         g_trackers[i].current_observed_lift = (double)g_trackers[i].lift_spikes_sum / g_trackers[i].lift_base_sum;
         if(g_trackers[i].lift_count >= InpLiftWindowTradesSymbol &&
            g_trackers[i].current_observed_lift < InpMinObservedLiftSymbol &&
            !g_trackers[i].disabled_low_lift)
         {
            g_trackers[i].disabled_low_lift = true;
            Alert(StringFormat("[v8.22] LIFT BAS : %s DESACTIVE (lift=%.2fx < %.2fx sur %d trades).",
                               sym, g_trackers[i].current_observed_lift, InpMinObservedLiftSymbol, g_trackers[i].lift_count));
         }
      }
      break;
   }

   // --- Global ---
   if(g_glob_count >= InpLiftWindowTradesGlobal)
   {
      g_glob_spikes_sum -= g_glob_spike_hist[g_glob_head];
      g_glob_base_sum   -= g_glob_base_hist[g_glob_head];
   }
   else g_glob_count++;

   g_glob_spike_hist[g_glob_head] = is_capture ? 1 : 0;
   g_glob_base_hist[g_glob_head] = base_hazard_at_entry;
   g_glob_head = (g_glob_head + 1) % InpLiftWindowTradesGlobal;
   if(is_capture) g_glob_spikes_sum++;
   g_glob_base_sum += base_hazard_at_entry;

   if(g_glob_count >= InpLiftMinTradesGlobal && g_glob_base_sum > 1e-6)
   {
      g_global_observed_lift = (double)g_glob_spikes_sum / g_glob_base_sum;
      if(g_glob_count >= InpLiftWindowTradesGlobal &&
         g_global_observed_lift < InpMinObservedLiftGlobal && !g_emergency_stopped)
      {
         g_emergency_stopped = true;
         CloseAllBotPositions("MODEL_DRIFT_FLATTEN");
         Alert(StringFormat("[v8.22] !!! ARRET TOTAL : DERIVE DU MODELE (lift global=%.2fx < %.2fx sur %d trades) !!!",
                            g_global_observed_lift, InpMinObservedLiftGlobal, g_glob_count));
      }
   }
}

//+------------------------------------------------------------------+
//| Journalisation CSV                                               |
//+------------------------------------------------------------------+
void LogTradeToCsv(const string sym, const string dir, double vol, double p0, double exp_payoff,
                  const string reason, double pnl, double cap_ratio, double mfe_usd, bool spike,
                  double base_hazard)
{
   int h = FileOpen(g_csv_log_filename, FILE_READ|FILE_WRITE|FILE_CSV|FILE_COMMON, ",");
   if(h == INVALID_HANDLE) h = FileOpen(g_csv_log_filename, FILE_READ|FILE_WRITE|FILE_CSV, ",");
   if(h == INVALID_HANDLE) return;

   if(FileSize(h) == 0)
      FileWrite(h, "timestamp_utc","symbol","direction","volume","p0_entry","expected_payoff_pts",
                "exit_reason","pnl_usd","capture_ratio_measured","mfe_usd","spike_observed","base_hazard_entry");

   FileSeek(h, 0, SEEK_END);
   FileWrite(h, TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS), sym, dir, DoubleToString(vol, 2),
             DoubleToString(p0, 4), DoubleToString(exp_payoff, 2), reason, DoubleToString(pnl, 2),
             DoubleToString(cap_ratio, 3), DoubleToString(mfe_usd, 2), spike ? 1 : 0,
             DoubleToString(base_hazard, 4));
   FileClose(h);
}

//+------------------------------------------------------------------+
//| Gestion des positions ouvertes (toujours activee, meme urgence)  |
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
         if(g_trackers[i].name == psym) { tr_idx = i; break; }
      if(tr_idx < 0) continue;

      g_trackers[tr_idx].open_positions++;

      // FIX-4 : MFE maj a chaque passage
      int pos_idx = FindTrackedPositionIndex(ticket);
      if(pos_idx >= 0 && profit_usd > g_pos_tracker[pos_idx].mfe_usd)
         g_pos_tracker[pos_idx].mfe_usd = profit_usd;

      // FIX-2 : reconstitution coherente (horloge broker) apres redemarrage
      if(pos_idx < 0)
      {
         string gv = "V8_ENT_" + IntegerToString((long)ticket);
         if(GlobalVariableCheck(gv))
         {
            MqlTick now_t;
            long now_msc = (SymbolInfoTick(psym, now_t)) ? now_t.time_msc : 0;
            long entry_msc = (long)GlobalVariableGet(gv);
            double tps = LoadTrackerRateGV(psym);

            if(now_msc > entry_msc && entry_msc > 0 && tps > 0.01)
            {
               double age_ticks = ((double)(now_msc - entry_msc) / 1000.0) * tps;
               long recon_entry = g_trackers[tr_idx].tick_counter - (long)age_ticks;
               RegisterTrackedPosition(ticket, psym, recon_entry, entry_msc, (int)ptype, volume,
                                       open_price, 0.0, 0.0, 0.10, 0.0, BaseHazardOf(g_trackers[tr_idx]));
               pos_idx = FindTrackedPositionIndex(ticket);
               PrintFormat("[v8.22] Position %d RECONSTITUEE : age~%.0f ticks (tps=%.2f mesure).", ticket, age_ticks, tps);
            }
            else
            {
               // Debit inconnu : age NON FIABLE -> aplatissement conservateur
               if(CloseSinglePositionTicket(ticket, psym, ptype, volume, "ORPHAN_FLATTEN"))
               {
                  g_total_orphan_flattens++;
                  PrintFormat("[v8.22] ORPHELIN %d APLATI : debit tick/s inconnu, age non reconstituable.", ticket);
                  continue;
               }
            }
         }
         else
         {
            if(CloseSinglePositionTicket(ticket, psym, ptype, volume, "ORPHAN_FLATTEN"))
            {
               g_total_orphan_flattens++;
               PrintFormat("[v8.22] ORPHELIN %d APLATI : aucune trace d'entree persistee.", ticket);
               continue;
            }
         }
      }

      long age_ticks = (pos_idx >= 0) ? (g_trackers[tr_idx].tick_counter - g_pos_tracker[pos_idx].entry_tick) : 0;

      // --- WATCHDOG PERSISTANT (arme uniquement par detection reelle de spike) ---
      if(InpEnableWatchdog && g_trackers[tr_idx].spike_watchdog_pending)
      {
         double tick_val = SymbolInfoDouble(psym, SYMBOL_TRADE_TICK_VALUE);
         double tick_sz  = SymbolInfoDouble(psym, SYMBOL_TRADE_TICK_SIZE);
         if(tick_sz  <= 0.0) tick_sz  = SymbolInfoDouble(psym, SYMBOL_POINT);
         if(tick_val <= 0.0) tick_val = 1.0;

         double exp_spike_usd = (InpTakeProfitRatio * g_trackers[tr_idx].mean_spike_pts / tick_sz) * tick_val * volume;
         double floor_usd     = MathMax(InpWatchdogFloorMinUsd, InpWatchdogFloorSpikeRatio * exp_spike_usd);

         if(profit_usd >= floor_usd)
         {
            if(CloseSinglePositionTicket(ticket, psym, ptype, volume, "SPIKE_CAUGHT_WATCHDOG"))
            {
               g_total_watchdog_green++;
               g_trackers[tr_idx].cooldown_until_tick = g_trackers[tr_idx].tick_counter + InpCooldownPostSpike;
               continue;
            }
         }
         else
         {
            if(CloseSinglePositionTicket(ticket, psym, ptype, volume, "THESIS_CONSUMED_CUT"))
            {
               g_total_thesis_consumed++;
               g_trackers[tr_idx].cooldown_until_tick = g_trackers[tr_idx].tick_counter + InpCooldownPostSpike;
               continue;
            }
         }
      }

      // --- STOP TEMPOREL STRICT (en ticks reels) ---
      if(age_ticks >= InpTimeStopTicks)
      {
         if(CloseSinglePositionTicket(ticket, psym, ptype, volume, "TIME_STOP_EXPIRED"))
         {
            g_total_timestop_closed++;
            continue;
         }
      }

      // --- COUPE USD (optionnelle) ---
      if(InpUseUsdRiskCap && InpMaxRiskUsdPerTrade > 0.0 && profit_usd <= -InpMaxRiskUsdPerTrade)
      {
         if(CloseSinglePositionTicket(ticket, psym, ptype, volume, "MAX_USD_RISK_CUT"))
         {
            g_total_max_risk_cut++;
            g_trackers[tr_idx].cooldown_until_tick = g_trackers[tr_idx].tick_counter + 60;
            continue;
         }
      }
   }

   // FIX-5 : desarmement du watchdog quand plus aucune position ouverte sur le symbole
   int active_count = 0;
   for(int i = 0; i < g_num_trackers; i++)
   {
      if(g_trackers[i].open_positions > 0) active_count++;
      else g_trackers[i].spike_watchdog_pending = false;
   }
   return active_count;
}

//+------------------------------------------------------------------+
//| Entree convexe inversee (TP dur server-side des l'entree)        |
//+------------------------------------------------------------------+
bool OpenConvexSpikePosition(SymbolTracker &tr, const MqlTick &tick, double p0_spike, double expected_payoff)
{
   if(tr.open_positions > 0 || (tick.time_msc - tr.last_order_sent_msc) < 3000) return false;
   if(!(bool)TerminalInfoInteger(TERMINAL_TRADE_ALLOWED) || !(bool)MQLInfoInteger(MQL_TRADE_ALLOWED)) return false;

   // Fresh tick acquisition directly from broker
   MqlTick live_tick;
   if(!SymbolInfoTick(tr.name, live_tick) || live_tick.ask <= 0.0 || live_tick.bid <= 0.0)
      live_tick = tick;

   double spread = live_tick.ask - live_tick.bid;
   tr.real_spread_pts = spread;
   tr.breakeven_ticks = spread / MathMax(tr.abs_drift_per_tick, 1e-8);
   if(tr.breakeven_ticks > InpMaxSpreadDriftMult) return false;

   double sl_dist_pts = ComputeSlDistPts(tr);
   double lot = ComputeConvexLotSize(tr, sl_dist_pts);
   if(lot <= 0.0) return false;

   tr.last_order_sent_msc = live_tick.time_msc;
   int    digits     = (int)SymbolInfoInteger(tr.name, SYMBOL_DIGITS);
   double min_stop    = GetBrokerMinStopDistancePts(tr.name);
   double tp_depth    = MathMax(min_stop, InpTakeProfitRatio * tr.mean_spike_pts);
   double sl_depth    = MathMax(min_stop, sl_dist_pts);

   MqlTradeRequest req; MqlTradeResult res;
   ZeroMemory(req); ZeroMemory(res);
   req.action       = TRADE_ACTION_DEAL;
   req.symbol       = tr.name;
   req.volume       = lot;
   req.magic        = InpMagicNumber;
   req.deviation    = 50;
   req.type_filling = GetSupportedFillingMode(tr.name);
   req.comment      = "V8_SPK_HUNT";

   // INVERSION : Boom=BUY (spike hausse = gain) | Crash=SELL (spike baisse = gain)
   // Guaranteed stop distances relative to entry price and opposite quote
   if(tr.is_boom)
   {
      req.type  = ORDER_TYPE_BUY;
      req.price = NormalizeDouble(live_tick.ask, digits);
      req.tp    = NormalizeDouble(req.price + tp_depth, digits);
      req.sl    = NormalizeDouble(live_tick.bid - sl_depth, digits);
   }
   else
   {
      req.type  = ORDER_TYPE_SELL;
      req.price = NormalizeDouble(live_tick.bid, digits);
      req.tp    = NormalizeDouble(req.price - tp_depth, digits);
      req.sl    = NormalizeDouble(live_tick.ask + sl_depth, digits);
   }

   bool sent = OrderSend(req, res);
   if(sent && res.retcode == TRADE_RETCODE_DONE)
   {
      ulong ticket = res.order;
      if(ticket == 0) ticket = res.deal;
      RegisterTrackedPosition(ticket, tr.name, tr.tick_counter, live_tick.time_msc, (int)req.type,
                              lot, req.price, req.tp, req.sl, p0_spike, expected_payoff, BaseHazardOf(tr));
      tr.entries_triggered++;
      tr.open_positions++;
      g_total_entries_all++;
      PrintFormat("[v8.22] >>> ENTREE %s %s %.2f lots | P0=%.2f%% | E[Payoff]=%+.2f pts | TP=%.5f | SL=%.5f <<<",
                  tr.name, tr.is_boom ? "BUY" : "SELL", lot, p0_spike*100.0, expected_payoff, req.tp, req.sl);
      return true;
   }

   tr.cooldown_until_tick = tr.tick_counter + 15;
   PrintFormat("[v8.22] REJET ORDRE %s (code=%d : %s) [Price=%.5f TP=%.5f SL=%.5f MinStop=%.5f Bid=%.5f Ask=%.5f]",
               tr.name, res.retcode, res.comment, req.price, req.tp, req.sl, min_stop, live_tick.bid, live_tick.ask);
   return false;
}

//+------------------------------------------------------------------+
//| FIX-1 : Traitement d'UN tick reel du flux                        |
//+------------------------------------------------------------------+
void ProcessSingleTick(SymbolTracker &tr, const MqlTick &tick, int &active_symbols_count)
{
   // Mise a jour microstructure
   tr.real_spread_pts = tick.ask - tick.bid;
   tr.breakeven_ticks = tr.real_spread_pts / MathMax(tr.abs_drift_per_tick, 1e-8);
   tr.tick_counter++;
   g_total_ticks_all++;

   double price = (tick.last > 0.0) ? tick.last : 0.5 * (tick.bid + tick.ask);

   if(tr.recent_prices_count < 4) { tr.recent_prices[tr.recent_prices_count] = price; tr.recent_prices_count++; }
   else { tr.recent_prices[0]=tr.recent_prices[1]; tr.recent_prices[1]=tr.recent_prices[2];
          tr.recent_prices[2]=tr.recent_prices[3]; tr.recent_prices[3]=price; }

   if(tr.last_price <= 0.0) { tr.last_price = price; return; }

   double delta = price - tr.last_price;
   tr.last_price = price;
   tr.last_delta = delta;

   // Mesure du debit (FIX-2) : sauvegarde periodique
   if(tr.first_time_msc <= 0) tr.first_time_msc = tick.time_msc;
   else if((tr.tick_counter % 500) == 0)
   {
      double span_sec = (double)(tick.time_msc - tr.first_time_msc) / 1000.0;
      if(span_sec > 30.0)
      {
         tr.ticks_per_sec = (double)tr.tick_counter / span_sec;
         SaveTrackerRateGV(tr);
      }
   }

   // Detection spike (seuils v7 stricts)
   bool is_spike = tr.is_boom ? (delta >= tr.spike_threshold) : (delta <= -tr.spike_threshold);
   if(is_spike)
   {
      tr.spikes_detected++;
      g_total_spikes_all++;
      tr.last_spike_amp    = MathAbs(delta);
      tr.ticks_since_spike = 0;

      if(tr.open_positions > 0)
      {
         tr.spike_watchdog_pending = true;   // FIX-5 : arme par EVENEMENT reel
         for(int i = 0; i < MAX_TRACKED_POS; i++)
            if(g_pos_tracker[i].is_active && g_pos_tracker[i].symbol == tr.name)
               g_pos_tracker[i].spike_observed = true;
      }

      if(tr.spike_history_count < 32)
      { tr.spike_history_ticks[tr.spike_history_count] = tr.tick_counter; tr.spike_history_amps[tr.spike_history_count] = MathAbs(delta); tr.spike_history_count++; }
      else
      {
         for(int m = 0; m < 31; m++) { tr.spike_history_ticks[m] = tr.spike_history_ticks[m+1]; tr.spike_history_amps[m] = tr.spike_history_amps[m+1]; }
         tr.spike_history_ticks[31] = tr.tick_counter; tr.spike_history_amps[31] = MathAbs(delta);
      }
   }
   else
      tr.ticks_since_spike++;

   // ================= FILTRES D'ENTREE SEQUENTIELS =================
   if(g_emergency_stopped) return;                                   // FIX-3 : entrees bloquees
   if(tr.open_positions > 0 || (tick.time_msc - tr.last_order_sent_msc) < 3000) return;
   if(tr.disabled_low_lift) return;
   if(tr.tick_counter < tr.cooldown_until_tick) return;
   if(tr.breakeven_ticks > InpMaxSpreadDriftMult) return;
   if(tr.ticks_since_spike < InpCooldownPostSpike) return;
   if(active_symbols_count >= InpMaxActiveSymbols) return;

   // ================= MODE D'ENTREE CONVEXE V8.22 (CHARLIE MUNGER INVERT) =================
   if(InpPureConvexReversalMode)
   {
      // Inversion Pure Miroir v7 : Entree cyclique a contre-derive des que le cooldown post-spike est ecoule
      if(tr.ticks_since_spike >= InpCooldownPostSpike && (tr.tick_counter % InpCycleEntryTicks == 0))
      {
         double p0_hazard  = BaseHazardOf(tr);
         double payoff_est = p0_hazard * tr.mean_spike_pts - (1.0 - p0_hazard) * (tr.abs_drift_per_tick * InpTimeStopTicks + tr.real_spread_pts);
         if(OpenConvexSpikePosition(tr, tick, p0_hazard, payoff_est))
            active_symbols_count++;
         return;
      }
      return;
   }

   // ---------------- MODE 2 : FILTRE PROBABILISTE AVANCE ----------------
   int c60 = 0;
   double p0 = EvaluateColabOnnxSpikeProbability(tr, c60);
   tr.last_ai_p0 = p0;

   if(tr.last_hawkes_fast > InpMaxHawkesFast)
   { tr.ai_filtered_count++; g_total_ai_blocked++; return; }

   double theta_eff = ThetaEffOf(tr);
   if(p0 < theta_eff) { tr.ai_filtered_count++; g_total_ai_blocked++; return; }

   double A_bar     = MathMax(tr.mean_spike_pts, 1e-6);
   double tp_depth  = InpTakeProfitRatio * A_bar;
   double p_reach   = MathExp(-tp_depth / A_bar);
   double p_eff     = p0 * p_reach;

   double M   = (double)InpTimeStopTicks;
   double tau = MathMax(tr.mean_tau_ticks, 1.0);
   double e_wait_spike = tau - M / (MathExp(M / tau) - 1.0);
   if(e_wait_spike < 0.0 || e_wait_spike > M || !MathIsValidNumber(e_wait_spike)) e_wait_spike = M;
   double avg_adverse_ticks = p0 * e_wait_spike + (1.0 - p0) * M;

   double expected_win_pts  = tp_depth - tr.real_spread_pts;
   double expected_loss_pts = tr.abs_drift_per_tick * avg_adverse_ticks + tr.real_spread_pts;
   double expected_payoff   = p_eff * expected_win_pts - (1.0 - p_eff) * expected_loss_pts;

   if(InpEnforcePositivePayoff && expected_payoff <= 0.0)
   { tr.ai_filtered_count++; g_total_ai_blocked++; return; }

   if(OpenConvexSpikePosition(tr, tick, p0, expected_payoff))
      active_symbols_count++;
}

//+------------------------------------------------------------------+
//| FIX-1 : Consommation REELLE du flux de ticks (curseur + dedupe)  |
//+------------------------------------------------------------------+
void ProcessSymbolTick(SymbolTracker &tr, int &active_symbols_count)
{
   if(tr.last_time_msc <= 0)
   {
      // Amorcage : dernier etat connu, sans rejouer l'historique
      MqlTick t0;
      if(!SymbolInfoTick(tr.name, t0)) return;
      if(t0.time_msc <= 0) return;
      tr.last_time_msc    = t0.time_msc;
      tr.last_ms_consumed = 1;
      tr.last_price       = (t0.last > 0.0) ? t0.last : 0.5*(t0.bid + t0.ask);
      return;
   }

   MqlTick arr[];
   int copied = CopyTicks(tr.name, arr, COPY_TICKS_ALL, tr.last_time_msc, InpMaxTicksPerScan);
   if(copied <= 0) return;

   int start = 0;
   // Sauter les ticks deja consommes portant le meme time_msc que le curseur
   while(start < copied && arr[start].time_msc == tr.last_time_msc && start < tr.last_ms_consumed)
      start++;

   for(int k = start; k < copied; k++)
   {
      if(arr[k].time_msc > tr.last_time_msc)
      { tr.last_time_msc = arr[k].time_msc; tr.last_ms_consumed = 1; }
      else if(arr[k].time_msc == tr.last_time_msc)
         tr.last_ms_consumed++;
      else
         continue; // tick anterieur (anomalie) : ignorer

      ProcessSingleTick(tr, arr[k], active_symbols_count);
   }
}

//+------------------------------------------------------------------+
//| Ouverture auto des graphiques (conservee)                        |
//+------------------------------------------------------------------+
void OpenUniverseChartsIfClosed()
{
   for(int i = 0; i < g_num_trackers; i++)
   {
      string sym = g_trackers[i].name;
      SymbolSelect(sym, true);

      bool already_open = false;
      long c_id = ChartFirst();
      while(c_id >= 0)
      {
         if(ChartSymbol(c_id) == sym) { already_open = true; break; }
         c_id = ChartNext(c_id);
      }
      if(!already_open)
      {
         long new_cid = ChartOpen(sym, PERIOD_M1);
         if(new_cid > 0)
            PrintFormat("[v8.22] Graphique M1 ouvert pour %s (Chart ID: %I64d)", sym, new_cid);
         else
            PrintFormat("[v8.22] Impossible d'ouvrir le graphique %s (Erreur: %d)", sym, GetLastError());
      }
   }
}

//+------------------------------------------------------------------+
//| Scanner global                                                  |
//+------------------------------------------------------------------+
void ScanAllBoomCrashSymbols()
{
   double eq = AccountInfoDouble(ACCOUNT_EQUITY);
   if(eq > g_peak_equity) g_peak_equity = eq;

   // FIX-10 : reset journalier (jour UTC)
   long day = (long)(TimeCurrent() / 86400);
   if(day != g_current_day)
   {
      g_current_day      = day;
      g_day_start_equity = eq;
      PrintFormat("[v8.22] NOUVEAU JOUR UTC : base perte journaliere reinitialisee a %.2f USD.", eq);
   }

   double dd_pct    = (g_peak_equity > 0.0)      ? ((g_peak_equity - eq) / g_peak_equity) * 100.0 : 0.0;
   double day_start = (g_day_start_equity > 0.0) ? g_day_start_equity : g_initial_equity;
   double daily_pct = (day_start > 0.0)          ? ((day_start - eq) / day_start) * 100.0 : 0.0;

   // FIX-3 : la gestion des positions TOUJOURS active (meme apres arret d'urgence)
   int active_symbols_count = ManageOpenPositionsAndExitSpikes();

   if(!g_emergency_stopped && (dd_pct >= InpMaxDrawdownPct || daily_pct >= InpDailyLossPct))
   {
      g_emergency_stopped = true;
      CloseAllBotPositions("EMERGENCY_FLATTEN");
      Alert(StringFormat("[v8.22] ARRET D'URGENCE (DD=%.2f%%, PerteJour=%.2f%%) -> positions aplaties, entrees bloquees.",
                         dd_pct, daily_pct));
   }

   // Entrees : bloquees si arret d'urgence
   if(!g_emergency_stopped)
      for(int i = 0; i < g_num_trackers; i++)
         ProcessSymbolTick(g_trackers[i], active_symbols_count);

   if(InpShowDashboard)
      UpdateDashboard(dd_pct, daily_pct);
}

//+------------------------------------------------------------------+
//| Dashboard                                                       |
//+------------------------------------------------------------------+
void UpdateDashboard(double dd_pct, double daily_pct)
{
   string bg = "V8_DASH_BG";
   if(ObjectFind(0, bg) < 0)
   {
      ObjectCreate(0, bg, OBJ_RECTANGLE_LABEL, 0, 0, 0);
      ObjectSetInteger(0, bg, OBJPROP_XDISTANCE, 20);
      ObjectSetInteger(0, bg, OBJPROP_YDISTANCE, 20);
      ObjectSetInteger(0, bg, OBJPROP_XSIZE, 470);
      ObjectSetInteger(0, bg, OBJPROP_YSIZE, 285);
      ObjectSetInteger(0, bg, OBJPROP_BGCOLOR, C'15,23,42');
      ObjectSetInteger(0, bg, OBJPROP_BORDER_COLOR, C'56,189,248');
      ObjectSetInteger(0, bg, OBJPROP_CORNER, CORNER_LEFT_UPPER);
   }

   double cur_eq  = AccountInfoDouble(ACCOUNT_EQUITY);
   double pnl_tot = cur_eq - g_initial_equity;

   string lines[14];
   color  clrs[14];

   lines[0] = "=== DERIV HFT QUANT v8.22 (SPIKE HUNTER CONVEX INVERT) ==="; clrs[0] = C'56,189,248';
   lines[1] = StringFormat("%s | Ticks reels: %d", g_emergency_stopped ? "STATUT : ARRET D'URGENCE" : "Statut : ACTIF", g_total_ticks_all);
   clrs[1] = g_emergency_stopped ? C'248,113,113' : C'74,222,128';
   lines[2] = StringFormat("Equite: %.2f | PnL session: %+.2f", cur_eq, pnl_tot);
   clrs[2] = (pnl_tot >= 0.0) ? C'250,204,21' : C'248,113,113';

   lines[3] = StringFormat("Drawdown: %.2f%% (Max: %.1f%%) | Perte Jour: %.2f%% (Max: %.1f%%)",
                           dd_pct, InpMaxDrawdownPct, daily_pct, InpDailyLossPct);
   clrs[3] = (dd_pct > 3.0 || daily_pct > 1.5) ? C'248,113,113' : C'148,163,184';

   lines[4] = StringFormat("Positions Ouvertes: %d | Symboles Surveilles: %d",
                           PositionsTotal(), g_num_trackers);
   clrs[4] = C'226,232,240';

   lines[5] = StringFormat("Spikes Detectes: %d | Entrees Declenchees: %d",
                           g_total_spikes_all, g_total_entries_all);
   clrs[5] = C'226,232,240';

   lines[6] = StringFormat("Trades Finalises: %d | Filtre IA Bloque: %d",
                           g_total_finalized_trades, g_total_ai_blocked);
   clrs[6] = C'148,163,184';

   lines[7] = StringFormat("Server TP: %d | Watchdog Vert: %d | Time-Stops: %d",
                           g_total_server_tp, g_total_watchdog_green, g_total_timestop_closed);
   clrs[7] = C'74,222,128';

   lines[8] = StringFormat("Lift Global Roulant: %.2fx (Min Requis: %.2fx | Trades: %d)",
                           g_global_observed_lift, InpMinObservedLiftGlobal, g_glob_count);
   clrs[8] = (g_global_observed_lift >= InpMinObservedLiftGlobal) ? C'74,222,128' : C'250,204,21';

   lines[9] = StringFormat("Orphelins Aplaties: %d | Max USD Cuts: %d",
                           g_total_orphan_flattens, g_total_max_risk_cut);
   clrs[9] = C'148,163,184';

   lines[10] = "--------------------------------------------------------";
   clrs[10] = C'71,85,105';

   lines[11] = "Paires: Crash 600, Crash 900, Boom 900, Boom 600, Crash 1000";
   clrs[11] = C'203,213,225';

   lines[12] = "M* = 60 ticks broker | Stop Temporel & Watchdog Actifs";
   clrs[12] = C'148,163,184';

   lines[13] = "Mode: Validation G1 (Lot Min 0.20) | Log: v8_closed_positions.csv";
   clrs[13] = C'56,189,248';

   for(int i = 0; i < 14; i++)
   {
      string lbl = "V8_DASH_L" + IntegerToString(i);
      if(ObjectFind(0, lbl) < 0)
      {
         ObjectCreate(0, lbl, OBJ_LABEL, 0, 0, 0);
         ObjectSetInteger(0, lbl, OBJPROP_XDISTANCE, 30);
         ObjectSetInteger(0, lbl, OBJPROP_YDISTANCE, 30 + i * 18);
         ObjectSetInteger(0, lbl, OBJPROP_CORNER, CORNER_LEFT_UPPER);
         ObjectSetString(0, lbl, OBJPROP_FONT, "Lucida Console");
         ObjectSetInteger(0, lbl, OBJPROP_FONTSIZE, 8);
      }
      ObjectSetString(0, lbl, OBJPROP_TEXT, lines[i]);
      ObjectSetInteger(0, lbl, OBJPROP_COLOR, clrs[i]);
   }
   ChartRedraw(0);
}

//+------------------------------------------------------------------+
//| FIX-9 : Suivi transactionnel et deals OUT                        |
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
            ulong pos_id   = HistoryDealGetInteger(deal_ticket, DEAL_POSITION_ID);
            string psym    = HistoryDealGetString(deal_ticket, DEAL_SYMBOL);
            string comment = HistoryDealGetString(deal_ticket, DEAL_COMMENT);
            double profit  = HistoryDealGetDouble(deal_ticket, DEAL_PROFIT);
            double swap    = HistoryDealGetDouble(deal_ticket, DEAL_SWAP);
            double volume  = HistoryDealGetDouble(deal_ticket, DEAL_VOLUME);

            if(StringFind(comment, "tp") >= 0)
               g_total_server_tp++;

            int pos_idx = FindTrackedPositionIndex(pos_id);
            if(pos_idx >= 0)
            {
               g_pos_tracker[pos_idx].closed_pnl    += (profit + swap);
               g_pos_tracker[pos_idx].closed_volume += volume;
               g_pos_tracker[pos_idx].last_exit_reason = comment;

               // Position completement fermee (volume restant nul ou disparue de PositionsTotal)
               if(!PositionSelectByTicket(pos_id) || g_pos_tracker[pos_idx].closed_volume >= g_pos_tracker[pos_idx].volume - 1e-5)
               {
                  FinalizeClosedPosition(pos_idx);
               }
            }
            else
            {
               // Deal orphelin ou deja dereference
               bool is_tp = (StringFind(comment, "tp") >= 0);
               LogTradeToCsv(psym, "OUT", volume, 0.10, 0.0, comment, profit + swap, 0.0, 0.0, is_tp, 0.06);
            }
         }
      }
   }
}

//+------------------------------------------------------------------+
//| Initialisation du Bot EA v8.22                                   |
//+------------------------------------------------------------------+
int OnInit()
{
   if(InpDemoAccountOnly && AccountInfoInteger(ACCOUNT_TRADE_MODE) != ACCOUNT_TRADE_MODE_DEMO)
   {
      Alert("[v8.22] SECURITE : Ce bot ne peut fonctionner QUE sur compte DEMO !");
      return INIT_FAILED;
   }

   trade.SetExpertMagicNumber(InpMagicNumber);
   trade.SetDeviationInPoints(50);

   g_initial_equity    = AccountInfoDouble(ACCOUNT_EQUITY);
   g_peak_equity       = g_initial_equity;
   g_day_start_equity  = g_initial_equity;
   g_current_day       = (long)(TimeCurrent() / 86400);
   g_emergency_stopped = false;

   for(int i = 0; i < MAX_TRACKED_POS; i++)
      g_pos_tracker[i].is_active = false;

   for(int w = 0; w < MAX_LIFT_WINDOW_GLOBAL; w++)
   {
      g_glob_spike_hist[w] = 0;
      g_glob_base_hist[w]  = 0.0;
   }

   Print("========================================================================");
   PrintFormat("[v8.22] DEMARRAGE MOTEUR SPIKE HUNTER CONVEXE (Equite: %.2f USD)", g_initial_equity);
   PrintFormat("[v8.22] FIX-1..FIX-10 Appliques | M*=%d ticks | TP=%.1fx E[A] | Kelly=%.2f%% | LiftRequis=%.2fx",
               InpTimeStopTicks, InpTakeProfitRatio, InpKellyFraction * 100.0, InpHazardLiftMultiplier);

   InitColabOnnxBrain();
   BuildSymbolUniverse();

   if(InpAutoOpenAuditedCharts)
      OpenUniverseChartsIfClosed();

   PrintFormat("[v8.22] Univers pret : %d symboles actifs sous surveillance directe.", g_num_trackers);

   EventSetMillisecondTimer(InpScannerTimerMs);
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Desinitialisation                                                |
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
   Comment("");
   PrintFormat("[v8.22] ARRETE (Raison: %d) | Total Trades Finalises: %d | Total Ticks: %d | Spikes: %d",
               reason, g_total_finalized_trades, g_total_ticks_all, g_total_spikes_all);
}

//+------------------------------------------------------------------+
//| Evenements Tick et Timer                                         |
//+------------------------------------------------------------------+
void OnTick()  { ScanAllBoomCrashSymbols(); }
void OnTimer() { ScanAllBoomCrashSymbols(); }
