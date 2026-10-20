//+------------------------------------------------------------------+
//|                                        DerivBoomCrashHFT_v8.mq5 |
//|                             Copyright 2026, Direction Recherche Quant |
//|                                      https://github.com/Christ-yavn/bot-quant- |
//+------------------------------------------------------------------+
//| PROTOCOLE GO / NO-GO QUALITÉ QUANTITATIVE (MANDAT SECTION 5) :   |
//| G0 : Backtest tick-à-tick multi-sessions, >= 300 trades,         |
//|      PF >= 1.5, E/trade > 0 sur >= 3 sessions distinctes.        |
//| G1 : Démo live 2 semaines lot min : >= 500 trades, PF >= 1.6,    |
//|      A_capturé/A >= 0.90, rejets [Invalid stops] = 0, lift >= 1.4|
//| G2 : Passage 1/8 Kelly seulement après validation formelle de G1.|
//| G3 : +25% de risque par palier de 250 trades validés             |
//|      (lift >= 1.4, DD < 3%), sinon gel au palier courant.        |
//| Le verrou InpDemoAccountOnly reste ACTIF jusqu'à G1 inclus.      |
//+------------------------------------------------------------------+
#property copyright   "Copyright 2026, Direction Recherche Quant"
#property link        "https://github.com/Christ-yavn/bot-quant-"
#property version     "8.10"
#property description "Deriv HFT Quant v8.10 - Spike Hunter Convexe (Positive Skew Engine)"
#property description "Inversion exacte de v7 : SELL sur Crash, BUY sur Boom pour capture de spikes asymetriques."
#property description "Conforme a 100% au Mandat V8-REVERSE-CONVEXITY-001-CODAGE (BUG-1 a BUG-8 resolus)."
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
   UNIVERSE_AUDITED_TOP_LIFT     = 0, // 5 Symboles Audites Lift >= 1.4 (Crash 600, Crash 900, Boom 900, Boom 600, Crash 1000)
   UNIVERSE_ALL_BOOM_CRASH       = 1, // Tous indices Boom & Crash
   UNIVERSE_CURRENT_CHART_ONLY   = 2  // Graphique Actuel Uniquement
};

enum ENUM_LOT_MODE
{
   LOT_MODE_MIN_BROKER           = 0, // Lot Minimum Broker (0.20 - Mode Validation Demo G1)
   LOT_MODE_FIXED                = 1, // Lot Fixe Configure (InpFixedLot)
   LOT_MODE_FRACTIONAL_KELLY     = 2  // Dimensionnement Kelly Convexe 1/8 (~1% risque equity)
};

//+------------------------------------------------------------------+
//| Parametres d'Entree (Inputs) - Norme L99 / Mandat Strict         |
//+------------------------------------------------------------------+
input group "=== 1. Cerveau IA ONNX Hawkes & Signal Convexe ==="
input bool   InpUseColabOnnxBrain           = true;   // Activer le Reseau ONNX v7.00 (14 variables dynamiques sans triche)
input bool   InpUseZeroCheatFeatures        = true;   // true = Features normalisees sans fuite
input double InpThetaSpike                  = 0.10;   // Plancher de seuil P0_spike minimal (defaut 0.10 = 10%)
input double InpHazardLiftMultiplier        = 1.40;   // Multiplicateur minimal de lift sur base Poisson (1.40x)
input double InpMaxHawkesFast               = 1.50;   // Intensite Hawkes rapide max autorisee (1.50)

input group "=== 2. Univers & Filtres d'Entree Inversee ==="
input ENUM_SYMBOL_UNIVERSE InpSymbolUniverse = UNIVERSE_AUDITED_TOP_LIFT; // Univers d'indices (5 audites lift >= 1.4 par defaut)
input bool   InpAutoOpenAuditedCharts       = true;   // Ouvrir automatiquement tous les graphiques de l'univers dans MT5
input int    InpCooldownPostSpike           = 15;     // Cooldown post-spike obligatoire (15 ticks anti-double-spike)
input double InpMaxSpreadDriftMult          = 80.0;   // Plafond de spread (80 multiples de derive)
input int    InpMaxActiveSymbols            = 3;      // Max positions simultanees (3)
input int    InpScannerTimerMs              = 50;     // Frequence du scanner haute precision (ms)

input group "=== 3. Sortie Hybride : TP Dur Serveur + Watchdog + Stop Temporel ==="
input int    InpTimeStopTicks               = 60;     // M* Stop temporel analytique strict (60 ticks non-negociables)
input double InpTakeProfitRatio             = 0.8;    // Profondeur TP dur serveur = 0.8 * E[Amplitude]
input double InpEmergencySlMult             = 2.0;    // Multiplicateur SL d'urgence serveur (2.0 * L_max)
input bool   InpEnableWatchdog              = true;   // Watchdog OnTick persistant (BUG-5)
input double InpWatchdogFloorMinUsd         = 0.10;   // Plancher minimal absolu USD du watchdog (0.10 USD)
input double InpWatchdogFloorSpikeRatio     = 0.30;   // Ratio d'amplitude attendue pour plancher dynamique (0.30)

input group "=== 4. Kelly Convexe & Dimensionnement ==="
input ENUM_LOT_MODE InpLotMode              = LOT_MODE_MIN_BROKER; // Mode de calcul des lots (defaut min lot 0.20 pour G1)
input double InpFixedLot                    = 0.20;   // Lot fixe (si Mode = LOT_MODE_FIXED)
input double InpKellyFraction               = 0.01;   // Fraction de Kelly 1/8 (~1.0% equity par trade)
input bool   InpUseUsdRiskCap               = false;  // Activer le plafond USD absolu (BUG-1, defaut false)
input double InpMaxRiskUsdPerTrade          = 2.50;   // Plafond de perte USD par trade (si InpUseUsdRiskCap=true)
input double InpMaxKellyOverstepRatio       = 1.30;   // Refuser le trade si lot arrondi depasse 1.30x le risque cible

input group "=== 5. Moniteur de Lift Roulant & Surveillance Derive ==="
input bool   InpEnableLiftMonitor           = true;   // Activer le moniteur de lift roulant (Mandat Section 2.F)
input int    InpLiftWindowTradesSymbol      = 200;    // Fenetre glissante par symbole (200 trades)
input double InpMinObservedLiftSymbol       = 1.30;   // Lift minimal par symbole avant desactivation (1.30x)
input int    InpLiftWindowTradesGlobal      = 500;    // Fenetre glissante globale (500 trades)
input double InpMinObservedLiftGlobal       = 1.30;   // Lift minimal global avant arret d'urgence (1.30x)

input group "=== 6. Securite Globale & Coupe-Circuits ==="
input bool   InpDemoAccountOnly             = true;   // Verrou Compte Demo obligatoire
input double InpDailyLossPct                = 2.0;    // Coupe-circuit Perte Journaliere Max (-2.0%)
input double InpMaxDrawdownPct              = 10.0;   // Coupe-circuit Drawdown Max (-10.0%)
input ulong  InpMagicNumber                 = 20261020;// Magic Number v8.10 Spike Hunter
input bool   InpShowDashboard               = true;   // Afficher tableau de bord live

//+------------------------------------------------------------------+
//| Structures de Donnees & Microstructure                           |
//+------------------------------------------------------------------+
#define MAX_LIFT_WINDOW_SYMBOL 200
#define MAX_LIFT_WINDOW_GLOBAL 500

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
   bool     spike_watchdog_pending; // BUG-5: Watchdog persistant armé lors d'un spike en position ouverte
   bool     disabled_low_lift;      // Désactivé si lift roulant < 1.30

   // Fenêtre glissante locale pour moniteur de lift (200 trades)
   int      lift_history[MAX_LIFT_WINDOW_SYMBOL];
   int      lift_head;
   int      lift_count;
   int      lift_spikes_captured;
   double   current_observed_lift;
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
   double   entry_p0;
   double   expected_payoff_pts;
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

// Fenêtre glissante globale pour surveillance de dérive modèle (500 trades)
int  g_global_lift_history[MAX_LIFT_WINDOW_GLOBAL];
int  g_global_lift_head            = 0;
int  g_global_lift_count           = 0;
int  g_global_lift_spikes_captured = 0;
double g_global_observed_lift      = 1.61;

//+------------------------------------------------------------------+
//| Variables Globales d'Etat                                        |
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
long           g_total_orphan_flattens= 0;

string         g_csv_log_filename     = "v8_closed_positions.csv";

//+------------------------------------------------------------------+
//| Idempotence des Fermetures d'Ordres (Verrou 2500 ms)             |
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
//| BUG-3 : Registre Persistant du Stop Temporel (GlobalVariables)   |
//+------------------------------------------------------------------+
void SavePositionGlobalVariable(ulong ticket, long time_msc)
{
   string gv_name = "V8_ENT_" + IntegerToString((long)ticket);
   GlobalVariableSet(gv_name, (double)time_msc);
}

void DeletePositionGlobalVariable(ulong ticket)
{
   string gv_name = "V8_ENT_" + IntegerToString((long)ticket);
   if(GlobalVariableCheck(gv_name))
      GlobalVariableDel(gv_name);
}

void RegisterTrackedPosition(ulong ticket, const string sym, long current_tick, long time_msc, int ptype, double vol, double price, double tp, double sl, double p0, double payoff)
{
   for(int i = 0; i < MAX_TRACKED_POS; i++)
   {
      if(!g_pos_tracker[i].is_active || g_pos_tracker[i].ticket == ticket)
      {
         g_pos_tracker[i].ticket              = ticket;
         g_pos_tracker[i].symbol              = sym;
         g_pos_tracker[i].entry_tick          = current_tick;
         g_pos_tracker[i].entry_time_msc      = time_msc;
         g_pos_tracker[i].pos_type            = ptype;
         g_pos_tracker[i].volume              = vol;
         g_pos_tracker[i].open_price          = price;
         g_pos_tracker[i].target_tp           = tp;
         g_pos_tracker[i].emergency_sl        = sl;
         g_pos_tracker[i].entry_p0            = p0;
         g_pos_tracker[i].expected_payoff_pts = payoff;
         g_pos_tracker[i].is_active           = true;

         SavePositionGlobalVariable(ticket, time_msc);
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
   DeletePositionGlobalVariable(ticket);
}

//+------------------------------------------------------------------+
//| Fermeture d'urgence ou d'alpha d'une position unique             |
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
   else
   {
      PrintFormat("[DerivBoomCrashHFT v8.10] Echec fermeture ticket %d (%s) : retcode=%d err=%d",
                  ticket, reason, res.retcode, GetLastError());
   }
   return false;
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
      PrintFormat("[DerivBoomCrashHFT v8.10] Information ONNX (code=%d) -> Activation Moteur Physique Exact (Markov/Poisson).", GetLastError());
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
   Print("[DerivBoomCrashHFT v8.10] >>> CERVEAU IA ONNX v8.10 INITIALISE AVEC SUCCES (14 FEATURES HAWKES) <<<");
   return true;
}

//+------------------------------------------------------------------+
//| Inférence ONNX & Moteur Physique (Mandat Section 2.A)            |
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

   // Formule de repli physique exacte (Poisson avec boost Hawkes borne [0.01, 0.85])
   if(!g_onnx_ready || g_onnx_handle == INVALID_HANDLE)
   {
      double base_p0 = 1.0 - MathExp(-((double)InpTimeStopTicks) / mean_tau);
      double p0 = base_p0 * (1.0 + 0.50 * MathMax(0.0, h_fast - 0.30));
      return MathMax(0.01, MathMin(0.85, p0));
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
      return 0.10;

   double p_survie = (double)out_proba[0][1];
   double p0_spike = 1.0 - p_survie;
   return MathMax(0.01, MathMin(0.85, p0_spike));
}

//+------------------------------------------------------------------+
//| BUG-1 & Mandat 2.D : Calcul de Lot Kelly Sans Division par Step  |
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

   // Mode LOT_MODE_FRACTIONAL_KELLY :
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   double target_risk_usd = InpKellyFraction * equity; // 1% de l'équité

   // Résolution conflit de plafonds (BUG-1) : n'applique InpMaxRiskUsdPerTrade que si activé
   if(InpUseUsdRiskCap && InpMaxRiskUsdPerTrade > 0.0)
      target_risk_usd = MathMin(target_risk_usd, InpMaxRiskUsdPerTrade);

   double tick_val = SymbolInfoDouble(tr.name, SYMBOL_TRADE_TICK_VALUE);
   double tick_sz  = SymbolInfoDouble(tr.name, SYMBOL_TRADE_TICK_SIZE);
   if(tick_sz <= 0.0)  tick_sz  = SymbolInfoDouble(tr.name, SYMBOL_POINT);
   if(tick_val <= 0.0) tick_val = 1.0;

   // L_max = d * M* + S (en points)
   double lmax_pts = tr.abs_drift_per_tick * InpTimeStopTicks + tr.real_spread_pts;
   // Risque USD au lot minimum : (lmax_pts / tick_size) * tick_value * vol_min (PAS de division par vol_step !)
   double risk_usd_minlot = (lmax_pts / tick_sz) * tick_val * vol_min;
   if(risk_usd_minlot <= 0.01) risk_usd_minlot = 0.25;

   double raw_lot = vol_min * (target_risk_usd / risk_usd_minlot);
   double stepped_lot = MathFloor(raw_lot / vol_step + 1e-9) * vol_step;

   // Si l'arrondi dépasse 1.30x le risque cible, REFUSER le trade
   double effective_risk_usd = (stepped_lot / vol_min) * risk_usd_minlot;
   if(effective_risk_usd > InpMaxKellyOverstepRatio * target_risk_usd)
   {
      PrintFormat("[DerivBoomCrashHFT v8.10] REFUS KELLY : Risque effectif (%.2f USD) > %.2fx cible (%.2f USD) sur %s",
                  effective_risk_usd, InpMaxKellyOverstepRatio, target_risk_usd, tr.name);
      return 0.0;
   }

   return MathMax(vol_min, MathMin(vol_max, stepped_lot));
}

//+------------------------------------------------------------------+
//| Initialisation et Calibration d'un SymbolTracker (BUG-6 & BUG-7) |
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
   tr.spike_watchdog_pending= false;
   tr.disabled_low_lift     = false;

   // Initialisation moniteur de lift
   tr.lift_head             = 0;
   tr.lift_count            = 0;
   tr.lift_spikes_captured  = 0;
   tr.current_observed_lift = 1.61;
   for(int w = 0; w < MAX_LIFT_WINDOW_SYMBOL; w++)
      tr.lift_history[w] = 0;

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
   tr.calib_source       = "MANDAT_TABLE_SECTION_1.6";

   // Table de calibration STRICTEMENT conforme au Mandat BUG-6
   if(StringFind(s, "crash 600") >= 0)       { tr.symbol_id = 5; tr.abs_drift_per_tick = 0.03773; tr.mean_spike_pts = 22.904; tr.mean_tau_ticks = 571.5; }
   else if(StringFind(s, "crash 900") >= 0)  { tr.symbol_id = 3; tr.abs_drift_per_tick = 0.01900; tr.mean_spike_pts = 17.314; tr.mean_tau_ticks = 907.3; }
   else if(StringFind(s, "boom 900") >= 0)   { tr.symbol_id = 2; tr.abs_drift_per_tick = 0.00972; tr.mean_spike_pts = 8.865;  tr.mean_tau_ticks = 911.4; }
   else if(StringFind(s, "boom 600") >= 0)   { tr.symbol_id = 4; tr.abs_drift_per_tick = 0.00894; tr.mean_spike_pts = 5.155;  tr.mean_tau_ticks = 586.5; }
   else if(StringFind(s, "crash 1000") >= 0) { tr.symbol_id = 1; tr.abs_drift_per_tick = 0.00636; tr.mean_spike_pts = 5.887;  tr.mean_tau_ticks = 961.0; }
   else if(StringFind(s, "boom 1000") >= 0)  { tr.symbol_id = 0; tr.abs_drift_per_tick = 0.01551; tr.mean_spike_pts = 17.015; tr.mean_tau_ticks = 1066.6; }
   else if(StringFind(s, "boom 500") >= 0)   { tr.symbol_id = 6; tr.abs_drift_per_tick = 0.01128; tr.mean_spike_pts = 5.825;  tr.mean_tau_ticks = 486.9; }
   else if(StringFind(s, "crash 500") >= 0)  { tr.symbol_id = 7; tr.abs_drift_per_tick = 0.00623; tr.mean_spike_pts = 2.991;  tr.mean_tau_ticks = 480.0; }
   else if(StringFind(s, "boom 300") >= 0)   { tr.symbol_id = 8; tr.abs_drift_per_tick = 0.00414; tr.mean_spike_pts = 1.324;  tr.mean_tau_ticks = 289.3; }
   else if(StringFind(s, "crash 300") >= 0)  { tr.symbol_id = 9; tr.abs_drift_per_tick = 0.02080; tr.mean_spike_pts = 6.863;  tr.mean_tau_ticks = 297.3; }

   tr.last_spike_amp = tr.mean_spike_pts;

   // Calibration vivante à partir des 5 000 ticks du broker
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
            // BUG-7 : Seuil de spike 5K strictement conforme v7 : |delta| > 3.5 * live_drift
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
            tr.calib_source   = "LIVE_5K_V7_RESTORED";
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

   // BUG-7 : Seuil runtime STRICTEMENT conforme v7 : max(3.5 * drift, 0.25 * mean_spike_pts)
   tr.spike_threshold = MathMax(3.5 * tr.abs_drift_per_tick, 0.25 * tr.mean_spike_pts);

   int dummy_c60 = 0;
   tr.last_ai_p0 = EvaluateColabOnnxSpikeProbability(tr, dummy_c60);

   // Mandat Section 4 : Trace d'initialisation obligatoire par symbole
   double base_h = 1.0 - MathExp(-((double)InpTimeStopTicks) / MathMax(tr.mean_tau_ticks, 1.0));
   double th_eff = MathMax(InpThetaSpike, base_h * InpHazardLiftMultiplier);
   double e_win  = MathMax(0.0, InpTakeProfitRatio * tr.mean_spike_pts - tr.real_spread_pts);
   double e_loss = tr.abs_drift_per_tick * InpTimeStopTicks + tr.real_spread_pts;
   double e_pay  = th_eff * e_win - (1.0 - th_eff) * e_loss;

   PrintFormat("[DerivBoomCrashHFT v8.10 CALIB] %s | drift=%.5f | amp=%.3f | tau=%.1ft | base_h=%.2f%% | theta_eff=%.2f%% | E[Payoff@theta]=%+.3f pts",
               tr.name, tr.abs_drift_per_tick, tr.mean_spike_pts, tr.mean_tau_ticks,
               base_h * 100.0, th_eff * 100.0, e_pay);
}

//+------------------------------------------------------------------+
//| Univers de Surveillance (Strict BUG-6)                           |
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

   if(InpSymbolUniverse == UNIVERSE_AUDITED_TOP_LIFT)
   {
      // BUG-6 : Exactement les 5 symboles audités avec lift >= 1.40 (aucun intrus)
      string audited_top5[] = {
         "Crash 600 Index",   // Lift 2.06x
         "Crash 900 Index",   // Lift 2.00x
         "Boom 900 Index",    // Lift 1.85x
         "Boom 600 Index",    // Lift 1.78x
         "Crash 1000 Index"   // Lift 1.45x
      };
      for(int i = 0; i < ArraySize(audited_top5); i++)
         AddSymbolToScanner(audited_top5[i]);
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
//| BUG-3 & 2.B : Gestion des Positions & Sorties Strictes           |
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

      // BUG-3 : Reconstitution persistance et gestion des orphelins
      int pos_idx = FindTrackedPositionIndex(ticket);
      if(pos_idx < 0)
      {
         string gv_name = "V8_ENT_" + IntegerToString((long)ticket);
         if(GlobalVariableCheck(gv_name))
         {
            long entry_msc = (long)GlobalVariableGet(gv_name);
            long elapsed_sec = MathMax(0, (long)(GetTickCount64() - entry_msc) / 1000);
            long reconstructed_entry_tick = tr.tick_counter - elapsed_sec; // débit 1 tick/sec
            RegisterTrackedPosition(ticket, psym, reconstructed_entry_tick, entry_msc, (int)ptype, volume, open_price, 0.0, 0.0, 0.10, 0.0);
            pos_idx = FindTrackedPositionIndex(ticket);
            PrintFormat("[DerivBoomCrashHFT v8.10] Position %d RECONSTITUEE depuis GlobalVariable (Age=%d ticks)", ticket, elapsed_sec);
         }
         else
         {
            // Position orpheline sans variable globale trouvée : fermer immédiatement
            if(CloseSinglePositionTicket(ticket, psym, ptype, volume, "ORPHAN_FLATTEN"))
            {
               g_total_orphan_flattens++;
               PrintFormat("[DerivBoomCrashHFT v8.10] !!! POSITION ORPHELINE %d FERMEE (ORPHAN_FLATTEN) -> Age inconnu !!!", ticket);
               continue;
            }
         }
      }

      long age_ticks = (pos_idx >= 0) ? (tr.tick_counter - g_pos_tracker[pos_idx].entry_tick) : 0;

      // 1 & 2 : TP et SL d'urgence sont placés côté serveur dès l'entrée (Mandat Section 2.B.1 & 2.B.2)

      // 3 : WATCHDOG ON-TICK PERSISTANT (BUG-5 & BUG-8)
      if(InpEnableWatchdog && tr.spike_watchdog_pending)
      {
         double tick_val = SymbolInfoDouble(psym, SYMBOL_TRADE_TICK_VALUE);
         double tick_sz  = SymbolInfoDouble(psym, SYMBOL_TRADE_TICK_SIZE);
         if(tick_sz <= 0.0)  tick_sz  = SymbolInfoDouble(psym, SYMBOL_POINT);
         if(tick_val <= 0.0) tick_val = 1.0;

         // BUG-8 : Plancher dynamique = max(0.10, 0.30 * E[USD du spike])
         double exp_spike_usd = (InpTakeProfitRatio * tr.mean_spike_pts / tick_sz) * tick_val * volume;
         double floor_usd     = MathMax(InpWatchdogFloorMinUsd, InpWatchdogFloorSpikeRatio * exp_spike_usd);

         if(profit_usd >= floor_usd)
         {
            if(CloseSinglePositionTicket(ticket, psym, ptype, volume, "SPIKE_CAUGHT_WATCHDOG"))
            {
               g_total_watchdog_green++;
               PrintFormat("[DerivBoomCrashHFT v8.10] $$$ WATCHDOG EN VERT sur %s : +%.2f USD (Plancher=%.2f USD | Age=%d ticks) $$$",
                           psym, profit_usd, floor_usd, age_ticks);
               g_trackers[tr_idx].cooldown_until_tick = g_trackers[tr_idx].tick_counter + InpCooldownPostSpike;
               continue;
            }
         }
         else
         {
            if(CloseSinglePositionTicket(ticket, psym, ptype, volume, "THESIS_CONSUMED_CUT"))
            {
               g_total_thesis_consumed++;
               PrintFormat("[DerivBoomCrashHFT v8.10] --- THESE DE SPIKE CONSOMMEE sur %s (PnL=%.2f USD < Plancher=%.2f USD) -> Cut immediat ---",
                           psym, profit_usd, floor_usd);
               g_trackers[tr_idx].cooldown_until_tick = g_trackers[tr_idx].tick_counter + InpCooldownPostSpike;
               continue;
            }
         }
      }

      // 4 : STOP TEMPOREL ANALYTIQUE STRICT M* = 60 TICKS (Mandat Section 2.B.4)
      if(age_ticks >= InpTimeStopTicks)
      {
         if(CloseSinglePositionTicket(ticket, psym, ptype, volume, "TIME_STOP_EXPIRED"))
         {
            g_total_timestop_closed++;
            PrintFormat("[DerivBoomCrashHFT v8.10] <<< STOP TEMPOREL STRICT EXPIRE sur %s : %.2f USD (M*=%d ticks) >>>",
                        psym, profit_usd, InpTimeStopTicks);
            continue;
         }
      }

      // 5 : COUPE-CIRCUIT USD ABSOLU (si active explicitement)
      if(InpUseUsdRiskCap && InpMaxRiskUsdPerTrade > 0.0 && profit_usd <= -InpMaxRiskUsdPerTrade)
      {
         if(CloseSinglePositionTicket(ticket, psym, ptype, volume, "MAX_USD_RISK_CUT"))
         {
            g_total_max_risk_cut++;
            PrintFormat("[DerivBoomCrashHFT v8.10] !!! PLAFOND RISQUE MAX USD (%.2f USD) sur %s -> Coupure d'urgence !!!",
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
//| BUG-2 & Mandat Section 2.C : Entrée Convexe Inversée             |
//+------------------------------------------------------------------+
bool OpenConvexSpikePosition(SymbolTracker &tr, const MqlTick &tick, double p0_spike, double expected_payoff)
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

   double lot = ComputeConvexLotSize(tr);
   if(lot <= 0.0)
      return false; // Refus Kelly Overstep

   tr.last_order_sent_msc = tick.time_msc;
   int digits = (int)SymbolInfoInteger(tr.name, SYMBOL_DIGITS);
   ENUM_ORDER_TYPE_FILLING fill_mode = GetSupportedFillingMode(tr.name);
   double min_stop_pts = GetBrokerMinStopDistancePts(tr.name);

   // Profondeur du TP serveur dur : k_TP * mean_spike_pts
   double tp_depth_pts = MathMax(min_stop_pts, InpTakeProfitRatio * tr.mean_spike_pts);
   // SL d'urgence serveur = 2.0 * L_max
   double lmax_pts     = tr.abs_drift_per_tick * InpTimeStopTicks + tr.real_spread_pts;
   double sl_dist_pts  = MathMax(min_stop_pts, InpEmergencySlMult * lmax_pts);

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

   // INVERSION DU SENS (COEUR DU MANDAT) :
   // - Boom  : Spike = hausse -> Entrée BUY  AVANT le spike. TP se déclenche sur BID (BUG-2 : bid + tp_depth).
   // - Crash : Spike = baisse -> Entrée SELL AVANT le spike. TP se déclenche sur ASK (BUG-2 : ask - tp_depth).
   if(tr.is_boom)
   {
      req.type  = ORDER_TYPE_BUY;
      req.price = tick.ask;
      req.tp    = NormalizeDouble(tick.bid + tp_depth_pts, digits); // BUG-2 CORRIGE : TP BUY declenche sur BID
      req.sl    = NormalizeDouble(tick.bid - sl_dist_pts,  digits);
   }
   else
   {
      req.type  = ORDER_TYPE_SELL;
      req.price = tick.bid;
      req.tp    = NormalizeDouble(tick.ask - tp_depth_pts, digits); // BUG-2 CORRIGE : TP SELL declenche sur ASK
      req.sl    = NormalizeDouble(tick.ask + sl_dist_pts,  digits);
   }

   bool sent = OrderSend(req, res);
   if(sent && res.retcode == TRADE_RETCODE_DONE)
   {
      ulong ticket = res.order;
      if(ticket == 0) ticket = res.deal;

      RegisterTrackedPosition(ticket, tr.name, tr.tick_counter, tick.time_msc, (int)req.type, lot, req.price, req.tp, req.sl, p0_spike, expected_payoff);

      tr.entries_triggered++;
      tr.open_positions++;
      g_total_entries_all++;

      PrintFormat("[DerivBoomCrashHFT v8.10] >>> ENTREE CONVEXE LANCEE sur %s (%s %.2f lots | P0=%.2f%% | E[Payoff]=+%.2f pts | TP=%.2f | SL=%.2f) <<<",
                  tr.name, tr.is_boom ? "BUY" : "SELL", lot, p0_spike * 100.0, expected_payoff, req.tp, req.sl);
      return true;
   }
   else
   {
      tr.cooldown_until_tick = tr.tick_counter + 15;
      PrintFormat("[DerivBoomCrashHFT v8.10] REJET ORDRE sur %s (code=%d : %s)",
                  tr.name, res.retcode, res.comment);
   }
   return false;
}

//+------------------------------------------------------------------+
//| Traitement Tick par Tick (Mandat Section 2.C : Ordre Strict)     |
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

   // BUG-7 : Détection spike rigoureusement conforme v7
   bool is_spike = tr.is_boom ? (delta >= tr.spike_threshold) : (delta <= -tr.spike_threshold);
   if(is_spike)
   {
      tr.spikes_detected++;
      g_total_spikes_all++;
      tr.last_spike_amp      = MathAbs(delta);
      tr.ticks_since_spike   = 0;

      // BUG-5 : Armement du watchdog persistant si position ouverte
      if(tr.open_positions > 0)
         tr.spike_watchdog_pending = true;

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

   // --- FILTRES D'ENTREE SEQUENTIELS (MANDAT SECTION 2.C) ---
   // 1. Pas de position ouverte + cooldown ordre >= 3000 ms
   if(tr.open_positions > 0 || (tick.time_msc - tr.last_order_sent_msc) < 3000)
      return;

   // Symbole desactivé par le moniteur de lift (Mandat Section 2.F)
   if(tr.disabled_low_lift)
      return;

   if(tr.tick_counter < tr.cooldown_until_tick)
      return;

   // 2. breakeven_ticks <= InpMaxSpreadDriftMult (80)
   if(tr.breakeven_ticks > InpMaxSpreadDriftMult)
      return;

   // 3. ticks_depuis_dernier_spike >= InpCooldownPostSpike (15)
   if(tr.ticks_since_spike < InpCooldownPostSpike)
      return;

   // 4. positions actives < InpMaxActiveSymbols (3)
   if(active_symbols_count >= InpMaxActiveSymbols)
      return;

   int c60 = 0;
   double p0_spike = EvaluateColabOnnxSpikeProbability(tr, c60);
   tr.last_ai_p0   = p0_spike;

   // 5. hawkes_fast <= InpMaxHawkesFast (1.50)
   if(tr.last_hawkes_fast > InpMaxHawkesFast)
   {
      tr.ai_filtered_count++;
      g_total_ai_blocked++;
      return;
   }

   // 6. BUG-4 : Seuil effectif theta_eff = max(InpThetaSpike, base_hazard * 1.40) (PAS DE "OU" LOGIQUE)
   double base_hazard = 1.0 - MathExp(-((double)InpTimeStopTicks) / MathMax(tr.mean_tau_ticks, 1.0));
   double theta_eff   = MathMax(InpThetaSpike, base_hazard * InpHazardLiftMultiplier);

   // BUG-2 : Expected Win Pts soustrayant le spread
   double expected_win_pts  = MathMax(0.0, InpTakeProfitRatio * tr.mean_spike_pts - tr.real_spread_pts);
   double expected_loss_pts = tr.abs_drift_per_tick * InpTimeStopTicks + tr.real_spread_pts;
   double expected_payoff   = p0_spike * expected_win_pts - (1.0 - p0_spike) * expected_loss_pts;

   // Entrée STRICTEMENT conditionnée : (P0 >= theta_eff) ET (E[Payoff] > 0)
   if(p0_spike >= theta_eff && expected_payoff > 0.0)
   {
      if(OpenConvexSpikePosition(tr, tick, p0_spike, expected_payoff))
         active_symbols_count++;
   }
}

//+------------------------------------------------------------------+
//| Scanner Global Exécute sur OnTick et OnTimer                     |
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
      Alert(StringFormat("[DerivBoomCrashHFT v8.10] ARRET D'URGENCE DECLENCHE (DD=%.2f%%, PerteJour=%.2f%%)", dd_pct, daily_loss_pct));
      return;
   }

   for(int i = 0; i < g_num_trackers; i++)
      ProcessSymbolTick(g_trackers[i], active_symbols_count);

   if(InpShowDashboard)
      UpdateDashboard(dd_pct, daily_loss_pct);
}

//+------------------------------------------------------------------+
//| Dashboard Graphique Multi-Lignes Haut de Gamme                   |
//+------------------------------------------------------------------+
void UpdateDashboard(double dd_pct, double daily_loss_pct)
{
   string bg_name = "V8_DASH_BG";
   if(ObjectFind(0, bg_name) < 0)
   {
      ObjectCreate(0, bg_name, OBJ_RECTANGLE_LABEL, 0, 0, 0);
      ObjectSetInteger(0, bg_name, OBJPROP_XDISTANCE, 20);
      ObjectSetInteger(0, bg_name, OBJPROP_YDISTANCE, 20);
      ObjectSetInteger(0, bg_name, OBJPROP_XSIZE, 460);
      ObjectSetInteger(0, bg_name, OBJPROP_YSIZE, 265);
      ObjectSetInteger(0, bg_name, OBJPROP_BGCOLOR, C'15,23,42');
      ObjectSetInteger(0, bg_name, OBJPROP_BORDER_COLOR, C'56,189,248');
      ObjectSetInteger(0, bg_name, OBJPROP_CORNER, CORNER_LEFT_UPPER);
   }

   double cur_eq  = AccountInfoDouble(ACCOUNT_EQUITY);
   double pnl_tot = cur_eq - g_initial_equity;

   string lines[13];
   color  clrs[13];

   lines[0] = "=== DERIV HFT QUANT v8.10 (SPIKE HUNTER CONVEX) ===";
   clrs[0]  = C'56,189,248'; // Cyan

   lines[1] = StringFormat("Statut : ACTIF (Convexe) | Ticks Scannes: %d", g_total_ticks_all);
   clrs[1]  = C'74,222,128'; // SpringGreen

   lines[2] = StringFormat("Equite: %.2f USD | PnL Session: %+.2f USD", cur_eq, pnl_tot);
   clrs[2]  = (pnl_tot >= 0.0) ? C'250,204,21' : C'248,113,113'; // Gold ou Rouge

   lines[3] = StringFormat("Drawdown Pic: %.2f%% | Perte Journaliere: %.2f%%", dd_pct, daily_loss_pct);
   clrs[3]  = clrWhite;

   lines[4] = "--------------------------------------------------------";
   clrs[4]  = C'100,116,139'; // Slate gris

   lines[5] = StringFormat("Positions Lancees : %d (En cours : %d)", g_total_entries_all, PositionsTotal());
   clrs[5]  = clrWhite;

   lines[6] = StringFormat("Sorties TP Dur Serveur (0 ms) : %d deals", g_total_server_tp);
   clrs[6]  = C'52,211,153'; // Vert Emeraude

   lines[7] = StringFormat("Sorties Watchdog En Vert      : %d deals", g_total_watchdog_green);
   clrs[7]  = C'52,211,153'; // Vert Emeraude

   lines[8] = StringFormat("Sorties These Consommee       : %d cuts", g_total_thesis_consumed);
   clrs[8]  = C'251,146,60'; // Orange clair

   lines[9] = StringFormat("Sorties Stop Temporel (M*=%dt) : %d cuts", InpTimeStopTicks, g_total_timestop_closed);
   clrs[9]  = C'56,189,248'; // Sky blue

   lines[10]= StringFormat("Sorties Risque USD / Orphelins: %d / %d", g_total_max_risk_cut, g_total_orphan_flattens);
   clrs[10] = C'239,68,68';  // Rouge tomate

   lines[11]= StringFormat("Lift Roulant Global (500 tr)  : %.2fx (Min: %.2fx)", g_global_observed_lift, InpMinObservedLiftGlobal);
   clrs[11] = (g_global_observed_lift >= 1.30) ? C'74,222,128' : C'239,68,68';

   lines[12]= StringFormat("Univers Audite : %d symboles | Seuil Lift: >=%.2fx", g_num_trackers, InpHazardLiftMultiplier);
   clrs[12] = C'56,189,248'; // Cyan

   for(int i = 0; i < 13; i++)
   {
      string lbl_name = StringFormat("V8_DASH_L%d", i);
      if(ObjectFind(0, lbl_name) < 0)
      {
         ObjectCreate(0, lbl_name, OBJ_LABEL, 0, 0, 0);
         ObjectSetInteger(0, lbl_name, OBJPROP_XDISTANCE, 30);
         ObjectSetInteger(0, lbl_name, OBJPROP_YDISTANCE, 28 + i * 17);
         ObjectSetString(0, lbl_name, OBJPROP_FONT, "Consolas");
         ObjectSetInteger(0, lbl_name, OBJPROP_FONTSIZE, 9);
         ObjectSetInteger(0, lbl_name, OBJPROP_CORNER, CORNER_LEFT_UPPER);
      }
      ObjectSetInteger(0, lbl_name, OBJPROP_COLOR, clrs[i]);
      ObjectSetString(0, lbl_name, OBJPROP_TEXT, lines[i]);
   }

   string comment_txt = "";
   for(int j = 0; j < 13; j++)
      comment_txt += lines[j] + "\n";
   Comment(comment_txt);
}

//+------------------------------------------------------------------+
//| Journalisation CSV des Trades (Mandat Section 4)                 |
//+------------------------------------------------------------------+
void LogTradeToCsv(const string sym, const string dir, double vol, double p0, double exp_payoff, const string reason, double pnl, double capture_ratio)
{
   int file_handle = FileOpen(g_csv_log_filename, FILE_READ|FILE_WRITE|FILE_CSV|FILE_COMMON, ",");
   if(file_handle == INVALID_HANDLE)
      file_handle = FileOpen(g_csv_log_filename, FILE_READ|FILE_WRITE|FILE_CSV, ",");

   if(file_handle != INVALID_HANDLE)
   {
      if(FileSize(file_handle) == 0)
         FileWrite(file_handle, "timestamp_utc", "symbol", "direction", "volume", "p0_entry", "expected_payoff_pts", "exit_reason", "pnl_usd", "capture_ratio");

      FileSeek(file_handle, 0, SEEK_END);
      FileWrite(file_handle, TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS), sym, dir, DoubleToString(vol, 2),
                DoubleToString(p0, 4), DoubleToString(exp_payoff, 2), reason, DoubleToString(pnl, 2), DoubleToString(capture_ratio, 3));
      FileClose(file_handle);
   }
}

//+------------------------------------------------------------------+
//| Moniteur de Lift Roulant (Mandat Section 2.F)                    |
//+------------------------------------------------------------------+
void UpdateRollingLiftMonitor(const string sym, bool is_spike_capture)
{
   if(!InpEnableLiftMonitor)
      return;

   // 1. Mise à jour locale par symbole (200 trades)
   for(int i = 0; i < g_num_trackers; i++)
   {
      if(g_trackers[i].name == sym)
      {
         int prev = g_trackers[i].lift_history[g_trackers[i].lift_head];
         g_trackers[i].lift_history[g_trackers[i].lift_head] = is_spike_capture ? 1 : 0;
         g_trackers[i].lift_head = (g_trackers[i].lift_head + 1) % InpLiftWindowTradesSymbol;

         if(g_trackers[i].lift_count < InpLiftWindowTradesSymbol)
            g_trackers[i].lift_count++;
         else
            g_trackers[i].lift_spikes_captured -= prev;

         if(is_spike_capture)
            g_trackers[i].lift_spikes_captured++;

         if(g_trackers[i].lift_count >= 50) // commence dès 50 trades
         {
            double obs_rate = (double)g_trackers[i].lift_spikes_captured / (double)g_trackers[i].lift_count;
            double base_rate = 1.0 - MathExp(-((double)InpTimeStopTicks) / MathMax(g_trackers[i].mean_tau_ticks, 1.0));
            g_trackers[i].current_observed_lift = obs_rate / MathMax(base_rate, 1e-4);

            if(g_trackers[i].lift_count >= InpLiftWindowTradesSymbol && g_trackers[i].current_observed_lift < InpMinObservedLiftSymbol)
            {
               g_trackers[i].disabled_low_lift = true;
               Alert(StringFormat("[DerivBoomCrashHFT v8.10] ALERTE LIFT BAS : %s desactive (Lift=%.2fx < %.2fx sur %d trades)",
                                  sym, g_trackers[i].current_observed_lift, InpMinObservedLiftSymbol, g_trackers[i].lift_count));
            }
         }
         break;
      }
   }

   // 2. Mise à jour globale (500 trades)
   int g_prev = g_global_lift_history[g_global_lift_head];
   g_global_lift_history[g_global_lift_head] = is_spike_capture ? 1 : 0;
   g_global_lift_head = (g_global_lift_head + 1) % InpLiftWindowTradesGlobal;

   if(g_global_lift_count < InpLiftWindowTradesGlobal)
      g_global_lift_count++;
   else
      g_global_lift_spikes_captured -= g_prev;

   if(is_spike_capture)
      g_global_lift_spikes_captured++;

   if(g_global_lift_count >= 100)
   {
      double g_obs_rate = (double)g_global_lift_spikes_captured / (double)g_global_lift_count;
      double g_base_rate = 0.088; // moyenne pondérée base Poisson sur le portefeuille
      g_global_observed_lift = g_obs_rate / g_base_rate;

      if(g_global_lift_count >= InpLiftWindowTradesGlobal && g_global_observed_lift < InpMinObservedLiftGlobal)
      {
         g_emergency_stopped = true;
         Alert(StringFormat("[DerivBoomCrashHFT v8.10] !!! ARRET D'URGENCE TOTAL : DERIVE DU MODELE (Lift global=%.2fx < %.2fx sur 500 trades) !!!",
                            g_global_observed_lift, InpMinObservedLiftGlobal));
      }
   }
}

//+------------------------------------------------------------------+
//| Traitement des Transactions & Telemetrie (OnTradeTransaction)     |
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
            double volume  = HistoryDealGetDouble(deal_ticket, DEAL_VOLUME);
            long   type    = HistoryDealGetInteger(deal_ticket, DEAL_TYPE);
            string dir_str = (type == DEAL_TYPE_SELL) ? "BUY_CLOSED" : "SELL_CLOSED";

            // Récupère métadonnées enregistrées
            double p0 = 0.10, exp_pay = 0.0;
            int pos_idx = FindTrackedPositionIndex(pos_id);
            if(pos_idx >= 0)
            {
               p0      = g_pos_tracker[pos_idx].entry_p0;
               exp_pay = g_pos_tracker[pos_idx].expected_payoff_pts;
            }

            // BUG-5 : Désarmement du watchdog persistant sur confirmation du deal OUT
            for(int i = 0; i < g_num_trackers; i++)
            {
               if(g_trackers[i].name == psym)
               {
                  g_trackers[i].spike_watchdog_pending = false;
                  break;
               }
            }

            UnregisterTrackedPosition(pos_id);

            bool is_spike = false;
            double cap_ratio = 0.0;

            if(StringFind(comment, "tp") >= 0)
            {
               g_total_server_tp++;
               is_spike = true;
               cap_ratio = 1.0; // Hard server TP = capture 100% dans le tick
               PrintFormat("[DerivBoomCrashHFT v8.10] $$$ HARD SERVER TP EXECUTE ! Deal=%d | Pos=%d | Profit=+%.2f USD $$$",
                           deal_ticket, pos_id, profit);
            }
            else if(StringFind(comment, "SPIKE_CAUGHT") >= 0)
            {
               is_spike = true;
               cap_ratio = 0.95; // Watchdog OnTick
            }

            UpdateRollingLiftMonitor(psym, is_spike);
            LogTradeToCsv(psym, dir_str, volume, p0, exp_pay, comment, profit, cap_ratio);
         }
      }
   }
}

//+------------------------------------------------------------------+
//| Initialisation du Bot EA v8.10                                   |
//+------------------------------------------------------------------+
//+------------------------------------------------------------------+
//| Ouverture automatique des graphiques de l'univers surveille     |
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
         if(ChartSymbol(c_id) == sym)
         {
            already_open = true;
            break;
         }
         c_id = ChartNext(c_id);
      }

      if(!already_open)
      {
         long new_cid = ChartOpen(sym, PERIOD_M1);
         if(new_cid > 0)
         {
            PrintFormat("[DerivBoomCrashHFT v8.10] Graphique M1 ouvert avec succes pour %s (Chart ID: %I64d)", sym, new_cid);
         }
         else
         {
            PrintFormat("[DerivBoomCrashHFT v8.10] Impossible d'ouvrir le graphique pour %s (Erreur: %d)", sym, GetLastError());
         }
      }
      else
      {
         PrintFormat("[DerivBoomCrashHFT v8.10] Graphique %s deja ouvert dans le terminal.", sym);
      }
   }
}

int OnInit()
{
   if(InpDemoAccountOnly && AccountInfoInteger(ACCOUNT_TRADE_MODE) != ACCOUNT_TRADE_MODE_DEMO)
   {
      Alert("[DerivBoomCrashHFT v8.10] SECURITE : Ce bot ne peut fonctionner QUE sur compte DEMO !");
      return INIT_FAILED;
   }

   trade.SetExpertMagicNumber(InpMagicNumber);
   trade.SetDeviationInPoints(50);

   g_initial_equity    = AccountInfoDouble(ACCOUNT_EQUITY);
   g_peak_equity       = g_initial_equity;
   g_emergency_stopped = false;

   for(int i = 0; i < MAX_TRACKED_POS; i++)
      g_pos_tracker[i].is_active = false;

   for(int w = 0; w < MAX_LIFT_WINDOW_GLOBAL; w++)
      g_global_lift_history[w] = 0;

   Print("========================================================================");
   PrintFormat("[DerivBoomCrashHFT v8.10] DEMARRAGE MOTEUR SPIKE HUNTER CONVEXE (Equite: %.2f USD)", g_initial_equity);
   PrintFormat("[DerivBoomCrashHFT v8.10] Parametres Cles: M*=%d ticks | TP=%.1fx E[A] | Kelly=%.2f%% | LiftRequis=%.2fx",
               InpTimeStopTicks, InpTakeProfitRatio, InpKellyFraction * 100.0, InpHazardLiftMultiplier);

   InitColabOnnxBrain();
   BuildSymbolUniverse();
   if(InpAutoOpenAuditedCharts)
      OpenUniverseChartsIfClosed();

   PrintFormat("[DerivBoomCrashHFT v8.10] Univers pret : %d symboles audites sous surveillance directe.", g_num_trackers);

   EventSetMillisecondTimer(InpScannerTimerMs);
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Desinitialisation du Bot EA v8.10                                |
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
   PrintFormat("[DerivBoomCrashHFT v8.10] ARRETE (Raison: %d) | Total Trades: %d | Server TPs: %d | Watchdogs: %d | Time-Stops: %d",
               reason, g_total_entries_all, g_total_server_tp, g_total_watchdog_green, g_total_timestop_closed);
}

//+------------------------------------------------------------------+
//| Evenements Tick et Timer                                         |
//+------------------------------------------------------------------+
void OnTick()  { ScanAllBoomCrashSymbols(); }
void OnTimer() { ScanAllBoomCrashSymbols(); }
//+------------------------------------------------------------------+
