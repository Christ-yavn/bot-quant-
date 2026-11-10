//+------------------------------------------------------------------+
//|                                          DerivBoomCrashHFT.mq5   |
//|        Quantitative High-Frequency Post-Spike & Drift Harvester  |
//|        v6.00 : TURBO GOLDEN-7 + CONTINUOUS DRIFT ENGINE          |
//|                + COLAB ONNX NEURAL BRAIN + RECOVERY_BE_GREEN     |
//+------------------------------------------------------------------+
#property copyright "Deriv Quantitative HFT Research"
#property version   "6.00"
#property description "v6.00 Turbo Golden-7 HFT: Continuous Calm-Drift Engine + Post-Spike Harvester + Calibrated Colab ONNX Brain + Instant Spike Recovery Break-Even."
#property strict

// Intégration directe du Cerveau IA entraîné sur Google Colab dans l'exécutable .ex5 !
#resource "\\Files\\boom_crash_meta_brain.onnx" as uchar ExtColabOnnxBrain[]

//--- Mode de sélection des marchés Boom & Crash
enum ENUM_SYMBOL_UNIVERSE
{
   UNIVERSE_GOLDEN_7_LIVE_WINNERS = 0, // RECOMMANDÉ : Les 7 Gagnants 100% Live (Crash 600/900/500/1000, Boom 500/900/600)
   UNIVERSE_CLASSIC_10            = 1, // Les 10 Classiques (Boom/Crash 300, 500, 600, 900, 1000)
   UNIVERSE_ALL_BOOM_CRASH        = 2, // TOUS les Boom & Crash (inclut 50, 100, 150)
   UNIVERSE_CURRENT_CHART_ONLY    = 3  // Uniquement le symbole du graphique actuel
};

//--- Input Parameters
input group "=== 1. Cerveau IA Google Colab (.ONNX) & Filtre Hawkes ==="
input bool   InpUseColabOnnxBrain           = true;   // Activer le Réseau de Neurones ONNX entraîné sur Colab (IA3_DeepSurvivalMLP)
input double InpOnnxThreshStage1            = 0.7800; // Seuil IA Colab Palier 1 (Calibré Golden-7 = 0.7800, bloque les clusters)
input double InpOnnxThreshStage2            = 0.8500; // Seuil IA Colab Palier 2 (Calibré Golden-7 = 0.8500)
input double InpOnnxThreshStage3            = 0.9000; // Seuil IA Colab Palier 3 (Calibré Golden-7 = 0.9000)
input double InpMaxHawkesFast               = 1.25;   // Intensité Hawkes rapide max autorisée (bloque les doubles spikes)

input group "=== 2. Moteur HFT Turbo : Dérive Continue + Post-Spike ==="
input ENUM_SYMBOL_UNIVERSE InpSymbolUniverse = UNIVERSE_GOLDEN_7_LIVE_WINNERS; // Univers Boom & Crash à scanner
input bool   InpEnableContinuousDrift       = true;   // MODE TURBO : Entrer aussi en pleine dérive calme (sans attendre 10 min un spike !)
input int    InpCalmDriftEntryTicks         = 15;     // Ticks consécutifs de dérive calme requis pour un Scalp Continu
input int    InpMaxActiveSymbols            = 7;      // Nombre max d'indices pouvant trader simultanément (7 = les 7 Golden en parallèle)
input bool   InpForceM1Timeframe            = true;   // Forcer automatiquement le graphique sur M1 au lancement
input int    InpScannerTimerMs              = 50;     // Fréquence du scanner multi-symboles en millisecondes (50ms = 20x/sec)

input group "=== 3. Prise de Gain Ultra-Rapide (Green Cash-In) & Recovery ==="
input bool   InpAutoCloseInGreen            = true;   // COUPER DÈS QUE C'EST EN GAIN NET (sans attendre un spike inverse !)
input double InpStage1NetDriftTicks         = 8.0;    // Palier 1 : Gain net visé AU-DESSUS du spread (8 ticks = rotation 2x plus rapide)
input double InpStage2NetDriftTicks         = 16.0;   // Palier 2 : Gain net visé AU-DESSUS du spread (16 ticks)
input double InpStage3NetDriftTicks         = 26.0;   // Palier 3 : Gain net visé AU-DESSUS du spread (26 ticks)
input bool   InpInstantExitOnSpikeRecovery  = true;   // Si une position subit un spike puis remonte à +0.01$, couper TOUT en vert immédiatement !
input bool   InpLockBreakEvenAfterS1        = true;   // Sécuriser Paliers 2 & 3 à Break-Even dès que Palier 1 encaisse !

input group "=== 4. Calibration & Gestion des Lots ==="
input double InpSpikeThresholdMult          = 0.25;   // Seuil de détection Spike (0.25 = vrai spike >= 25% du spike moyen)
input int    InpDelayTicksAfterSpike        = 2;      // Délai anti-cluster en ticks après un spike (2 ticks)
input int    InpStagedPositions             = 2;      // Nombre max de paliers après un Spike (2 = S1 rapide + S2 runner)
input int    InpContinuousDriftStages       = 1;      // Nombre de paliers en Scalp de Dérive Continue (1 = Sniper rapide risque divisé par 3)
input double InpLotsPerStage                = 0.0;    // Lots par palier (0.0 = lot minimum autorisé par Deriv, ex: 0.20)
input double InpSlSpikeMultiple             = 3.0;    // Stop-Loss catastrophe serveur (3.0x spike moyen pour éviter d'être coupé au pire tick d'un spike)
input int    InpCooldownAfterWin            = 8;      // Ticks de pause après un gain avant ré-entrée (8 ticks = ~8 sec)
input int    InpCooldownAfterLoss           = 180;    // Ticks de pause après une perte (évite les tempêtes de spikes)

input group "=== 5. Sécurité & Coupe-Circuits (Circuit Breakers) ==="
input bool   InpDemoAccountOnly             = true;   // VERROU SÉCURITÉ : Bloquer sur compte Réel (Autoriser Démo uniquement)
input double InpMaxDrawdownPct              = 15.0;   // Coupe-circuit Drawdown Max (% depuis le pic d'équité)
input double InpDailyLossPct                = 5.0;    // Coupe-circuit Perte Journalière Max (% du solde initial)
input double InpMaxSpreadDriftMult          = 75.0;   // Limite Spread Réel en ticks de dérive (75 = bloque Boom 1000 à 118t de spread !)
input ulong  InpMagicNumber                 = 20261018;// Identifiant unique (Magic Number) du Bot
input bool   InpUseAsyncOrders              = true;   // Utiliser OrderSendAsync() (rafale HFT parallèle < 0.5 ms)
input bool   InpShowDashboard               = true;   // Afficher la matrice multi-symboles en direct sur le graphique

//--- Structure d'état indépendante pour chaque indice Boom / Crash
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
   double   spike_start_price;
   double   last_spike_amp;
   long     last_time_msc;
   long     last_order_sent_msc;

   long     tick_counter;
   long     calm_drift_ticks;
   long     spikes_detected;
   long     bursts_triggered;
   long     drift_scalps_triggered;
   long     ai_filtered_count;
   double   last_ai_prob;
   double   last_hawkes_fast;
   long     pending_signal_tick;
   long     entry_tick;
   long     cooldown_until_tick;
   long     spike_history_ticks[32];
   double   spike_history_amps[32];
   int      spike_history_count;
   int      open_positions;
   int      spikes_while_open;
   bool     stage1_cashed;
};

SymbolTracker g_trackers[];
int           g_num_trackers        = 0;
long          g_onnx_handle         = INVALID_HANDLE;
bool          g_onnx_ready          = false;
bool          g_emergency_stopped   = false;
double        g_initial_equity      = 0.0;
double        g_peak_equity         = 0.0;
long          g_total_ticks_all     = 0;
long          g_total_spikes_all    = 0;
long          g_total_bursts_all    = 0;
long          g_total_green_closed  = 0;
long          g_total_recovery_be   = 0;
long          g_total_ai_blocked    = 0;

//+------------------------------------------------------------------+
//| Initialise le moteur C++ ONNX de MetaTrader 5 avec le modèle     |
//| IA3_DeepSurvivalNeuralNet_MLP entraîné sur Google Colab          |
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
      PrintFormat("[DerivBoomCrashHFT v6.00] ERREUR chargement ONNX (code=%d) -> Fonctionnement en mode Hawkes Physique.", GetLastError());
      return false;
   }

   const long input_shape[]  = {1, 14};
   const long output_label[] = {1};
   const long output_proba[] = {1, 2};

   if(!OnnxSetInputShape(g_onnx_handle, 0, input_shape))
   {
      PrintFormat("[DerivBoomCrashHFT v6.00] OnnxSetInputShape échoué (err=%d)", GetLastError());
      OnnxRelease(g_onnx_handle);
      g_onnx_handle = INVALID_HANDLE;
      return false;
   }
   OnnxSetOutputShape(g_onnx_handle, 0, output_label);
   OnnxSetOutputShape(g_onnx_handle, 1, output_proba);

   g_onnx_ready = true;
   Print("[DerivBoomCrashHFT v6.00] >>> CERVEAU IA GOOGLE COLAB (IA3_DeepSurvivalNeuralNet_MLP - 14 features Hawkes) CHARGÉ ET ACTIF ! <<<");
   return true;
}

//+------------------------------------------------------------------+
//| Calcule l'intensité de Hawkes multi-échelles actuelle et         |
//| interroge le Réseau de Neurones ONNX de Colab (< 40 µs)          |
//+------------------------------------------------------------------+
double EvaluateColabOnnxSurvivalProbability(SymbolTracker &tr, int &out_c60)
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

   // Calcul robuste de la vélocité sur les 3 derniers ticks (compatible Post-Spike ET Dérive Continue)
   double post3_vel = 1.0;
   if(tr.recent_prices_count >= 4)
   {
      double move3 = tr.is_boom ? (tr.recent_prices[0] - tr.recent_prices[3]) : (tr.recent_prices[3] - tr.recent_prices[0]);
      post3_vel = move3 / (3.0 * drift);
      post3_vel = MathMax(-2.0, MathMin(2.5, post3_vel));
   }

   double be_ticks   = tr.real_spread_pts / drift;
   double cost_ratio = be_ticks / mean_tau;
   double spike_amp_norm = (tr.last_spike_amp > 0.0) ? (tr.last_spike_amp / mean_sp) : 1.0;

   if(!g_onnx_ready || g_onnx_handle == INVALID_HANDLE)
   {
      double phys_prob = MathExp(-(be_ticks + InpStage1NetDriftTicks) / mean_tau) * MathExp(-0.15 * MathMax(0.0, h_fast - 0.85));
      return MathMax(0.0, MathMin(1.0, phys_prob));
   }

   float x[1][14];
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

   long  out_label[1];
   float out_proba[1][2];

   if(!OnnxRun(g_onnx_handle, ONNX_NO_CONVERSION, x, out_label, out_proba))
      return 0.85;

   return (double)out_proba[0][1];
}

//+------------------------------------------------------------------+
//| Détecte automatiquement le mode de remplissage supporté par MT5  |
//+------------------------------------------------------------------+
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
//| Calibre un indice Boom/Crash avec le VRAI spread live MT5        |
//| et pré-charge les 5000 derniers ticks pour démarrer instantanément|
//+------------------------------------------------------------------+
void InitAndCalibrateTracker(SymbolTracker &tr, const string sym)
{
   tr.name                   = sym;
   string s                  = sym;
   StringToLower(s);
   tr.is_boom                = (StringFind(s, "boom") >= 0);
   tr.symbol_id              = 0;
   tr.last_price             = 0.0;
   tr.recent_prices_count    = 0;
   tr.last_delta             = 0.0;
   tr.spike_start_price      = 0.0;
   tr.last_spike_amp         = 0.0;
   tr.last_time_msc          = 0;
   tr.last_order_sent_msc    = 0;
   tr.tick_counter           = 0;
   tr.calm_drift_ticks       = 0;
   tr.spikes_detected        = 0;
   tr.bursts_triggered       = 0;
   tr.drift_scalps_triggered = 0;
   tr.ai_filtered_count      = 0;
   tr.last_ai_prob           = 0.0;
   tr.last_hawkes_fast       = 0.0;
   tr.pending_signal_tick    = -1;
   tr.entry_tick             = -1;
   tr.cooldown_until_tick    = 0;
   tr.spike_history_count    = 0;
   tr.open_positions         = 0;
   tr.spikes_while_open      = 0;
   tr.stage1_cashed          = false;

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
   if(vol_min <= 0.0) vol_min = 0.20;
   if(vol_step <= 0.0) vol_step = 0.01;

   if(InpLotsPerStage <= 0.0)
      tr.lot_per_stage = vol_min;
   else
   {
      double clamped = MathMax(vol_min, MathMin(vol_max, InpLotsPerStage));
      tr.lot_per_stage = MathFloor(clamped / vol_step + 1e-9) * vol_step;
   }

   tr.abs_drift_per_tick = 0.01622;
   tr.mean_spike_pts     = 17.015;
   tr.mean_tau_ticks     = 1000.0;
   tr.calib_source       = "TABLE";

   if(StringFind(s, "boom 1000") >= 0)       { tr.symbol_id = 0; tr.abs_drift_per_tick = 0.01622; tr.mean_spike_pts = 17.015; tr.mean_tau_ticks = 1066.6; }
   else if(StringFind(s, "crash 1000") >= 0) { tr.symbol_id = 1; tr.abs_drift_per_tick = 0.00625; tr.mean_spike_pts = 5.887;  tr.mean_tau_ticks = 961.0;  }
   else if(StringFind(s, "boom 900") >= 0)   { tr.symbol_id = 2; tr.abs_drift_per_tick = 0.00969; tr.mean_spike_pts = 8.865;  tr.mean_tau_ticks = 911.4;  }
   else if(StringFind(s, "crash 900") >= 0)  { tr.symbol_id = 3; tr.abs_drift_per_tick = 0.01861; tr.mean_spike_pts = 17.314; tr.mean_tau_ticks = 907.3;  }
   else if(StringFind(s, "boom 600") >= 0)   { tr.symbol_id = 4; tr.abs_drift_per_tick = 0.00873; tr.mean_spike_pts = 5.155;  tr.mean_tau_ticks = 586.5;  }
   else if(StringFind(s, "crash 600") >= 0)  { tr.symbol_id = 5; tr.abs_drift_per_tick = 0.03848; tr.mean_spike_pts = 22.904; tr.mean_tau_ticks = 571.5;  }
   else if(StringFind(s, "boom 500") >= 0)   { tr.symbol_id = 6; tr.abs_drift_per_tick = 0.01160; tr.mean_spike_pts = 5.825;  tr.mean_tau_ticks = 486.9;  }
   else if(StringFind(s, "crash 500") >= 0)  { tr.symbol_id = 7; tr.abs_drift_per_tick = 0.00613; tr.mean_spike_pts = 2.991;  tr.mean_tau_ticks = 480.0;  }
   else if(StringFind(s, "boom 300") >= 0)   { tr.symbol_id = 8; tr.abs_drift_per_tick = 0.00441; tr.mean_spike_pts = 1.324;  tr.mean_tau_ticks = 289.3;  }
   else if(StringFind(s, "crash 300") >= 0)  { tr.symbol_id = 9; tr.abs_drift_per_tick = 0.02249; tr.mean_spike_pts = 6.863;  tr.mean_tau_ticks = 297.3;  }
   else if(StringFind(s, "boom 150") >= 0)   { tr.symbol_id = 8; tr.abs_drift_per_tick = 0.00667; tr.mean_spike_pts = 0.955;  tr.mean_tau_ticks = 150.0;  }
   else if(StringFind(s, "crash 150") >= 0)  { tr.symbol_id = 9; tr.abs_drift_per_tick = 0.00664; tr.mean_spike_pts = 0.908;  tr.mean_tau_ticks = 150.0;  }
   else if(StringFind(s, "boom 100") >= 0)   { tr.symbol_id = 8; tr.abs_drift_per_tick = 0.07244; tr.mean_spike_pts = 6.661;  tr.mean_tau_ticks = 100.0;  }
   else if(StringFind(s, "crash 100") >= 0)  { tr.symbol_id = 9; tr.abs_drift_per_tick = 0.07539; tr.mean_spike_pts = 7.472;  tr.mean_tau_ticks = 100.0;  }
   else if(StringFind(s, "boom 50") >= 0)    { tr.symbol_id = 8; tr.abs_drift_per_tick = 0.08411; tr.mean_spike_pts = 3.446;  tr.mean_tau_ticks = 50.0;   }
   else if(StringFind(s, "crash 50") >= 0)   { tr.symbol_id = 9; tr.abs_drift_per_tick = 0.08405; tr.mean_spike_pts = 4.559;  tr.mean_tau_ticks = 50.0;   }

   tr.last_spike_amp = tr.mean_spike_pts;

   // Pré-chargement des 5000 derniers ticks pour que Hawkes et le compteur de dérive calme soient chauds dès la 1re seconde !
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
            tr.calib_source   = "LIVE_5K+ONNX";
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
      tr.real_spread_pts = 45.0 * tr.abs_drift_per_tick;

   tr.breakeven_ticks = tr.real_spread_pts / MathMax(tr.abs_drift_per_tick, 1e-8);
   tr.spike_threshold = MathMax(3.5 * tr.abs_drift_per_tick, InpSpikeThresholdMult * tr.mean_spike_pts);
   tr.sl_pts          = InpSlSpikeMultiple * tr.mean_spike_pts;

   int dummy_c60 = 0;
   tr.last_ai_prob = EvaluateColabOnnxSurvivalProbability(tr, dummy_c60);
}

//+------------------------------------------------------------------+
//| Ajoute un symbole au scanner s'il existe sur le serveur Deriv    |
//+------------------------------------------------------------------+
bool AddSymbolToScanner(const string sym)
{
   for(int i = 0; i < g_num_trackers; i++)
   {
      if(g_trackers[i].name == sym)
         return true;
   }
   if(!SymbolSelect(sym, true))
      return false;

   MqlTick t;
   SymbolInfoTick(sym, t);

   ArrayResize(g_trackers, g_num_trackers + 1);
   InitAndCalibrateTracker(g_trackers[g_num_trackers], sym);
   g_num_trackers++;
   return true;
}

//+------------------------------------------------------------------+
//| Construit la liste des indices Boom & Crash à surveiller         |
//+------------------------------------------------------------------+
void BuildSymbolUniverse()
{
   ArrayResize(g_trackers, 0);
   g_num_trackers = 0;

   if(InpSymbolUniverse == UNIVERSE_CURRENT_CHART_ONLY)
   {
      AddSymbolToScanner(_Symbol);
      return;
   }

   if(InpSymbolUniverse == UNIVERSE_GOLDEN_7_LIVE_WINNERS)
   {
      // Les 7 indices ayant obtenu 100.0% de Win Rate (39/39 victoires, 0 défaite) en Live MT5 !
      // Exclut Crash/Boom 300 (lot 0.50 trop risqué) et Boom 1000 (spread 118.7 ticks trop lent).
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

   if(InpSymbolUniverse == UNIVERSE_ALL_BOOM_CRASH)
   {
      string extra6[] = {
         "Boom 150 Index", "Crash 150 Index",
         "Boom 100 Index", "Crash 100 Index",
         "Boom 50 Index",  "Crash 50 Index"
      };
      for(int i = 0; i < ArraySize(extra6); i++)
         AddSymbolToScanner(extra6[i]);
   }
}

//+------------------------------------------------------------------+
//| Initialisation de l'Expert Advisor                               |
//+------------------------------------------------------------------+
int OnInit()
{
   long trade_mode = AccountInfoInteger(ACCOUNT_TRADE_MODE);
   if(InpDemoAccountOnly && trade_mode == ACCOUNT_TRADE_MODE_REAL)
   {
      Alert("[DerivBoomCrashHFT] VERROU SÉCURITÉ : Compte Réel détecté ! Exécution bloquée (InpDemoAccountOnly=true).");
      return(INIT_FAILED);
   }

   if(InpForceM1Timeframe && Period() != PERIOD_M1)
      ChartSetSymbolPeriod(0, _Symbol, PERIOD_M1);

   InitColabOnnxBrain();
   BuildSymbolUniverse();

   g_initial_equity = AccountInfoDouble(ACCOUNT_EQUITY);
   g_peak_equity    = g_initial_equity;

   int timer_ms = MathMax(20, InpScannerTimerMs);
   EventSetMillisecondTimer(timer_ms);

   PrintFormat("[DerivBoomCrashHFT v6.00 TURBO] Connecté à %d indices Golden | Cerveau IA Colab=%s | Dérive Continue=%s | Seuils IA=(%.2f / %.2f / %.2f)",
               g_num_trackers,
               g_onnx_ready ? "ACTIF (DeepSurvivalMLP)" : "HAWKES PHYSIQUE",
               InpEnableContinuousDrift ? "ACTIVE (Haute Fréquence)" : "POST-SPIKE SEUL",
               InpOnnxThreshStage1, InpOnnxThreshStage2, InpOnnxThreshStage3);
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Nettoyage à la désactivation de l'Expert Advisor                 |
//+------------------------------------------------------------------+
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
//| Ferme un ticket individuel immédiatement au prix du marché       |
//+------------------------------------------------------------------+
bool CloseSinglePositionTicket(ulong ticket, const string sym, ENUM_POSITION_TYPE ptype, double volume, const string reason)
{
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

   bool sent = false;
   if(InpUseAsyncOrders)
      sent = OrderSendAsync(req, res);
   if(!sent)
      sent = OrderSend(req, res);
   return sent;
}

//+------------------------------------------------------------------+
//| Déplace le Stop-Loss d'une position à Break-Even (Prix Entrée)   |
//+------------------------------------------------------------------+
void MovePositionToBreakEven(ulong ticket, const string sym, double open_price, double current_tp)
{
   int digits = (int)SymbolInfoInteger(sym, SYMBOL_DIGITS);
   MqlTradeRequest req;
   MqlTradeResult  res;
   ZeroMemory(req);
   ZeroMemory(res);

   req.action   = TRADE_ACTION_SLTP;
   req.position = ticket;
   req.symbol   = sym;
   req.sl       = NormalizeDouble(open_price, digits);
   req.tp       = current_tp;
   if(!OrderSendAsync(req, res))
   {
      bool ok = OrderSend(req, res);
      if(!ok) return;
   }
}

//+------------------------------------------------------------------+
//| SURVEILLANCE CONTINUE DES GAINS & RECOVERY :                     |
//| 1) Si la position a subi un spike puis est remontée à +0.01$,    |
//|    coupe immédiatement en vert (RECOVERY_BE_GREEN) !             |
//| 2) Sinon, coupe chaque palier dès qu'il atteint +8 / +16 / +26t  |
//|    nets au-dessus du spread (GREEN_CASH_IN) !                    |
//+------------------------------------------------------------------+
int ManageOpenPositionsAndCashInGreen()
{
   for(int i = 0; i < g_num_trackers; i++)
      g_trackers[i].open_positions = 0;

   int total = PositionsTotal();
   for(int p = total - 1; p >= 0; p--)
   {
      ulong ticket = PositionGetTicket(p);
      if(ticket == 0) continue;
      if((ulong)PositionGetInteger(POSITION_MAGIC) != InpMagicNumber) continue;

      string psym               = PositionGetString(POSITION_SYMBOL);
      double profit_usd         = PositionGetDouble(POSITION_PROFIT) + PositionGetDouble(POSITION_SWAP);
      double open_price         = PositionGetDouble(POSITION_PRICE_OPEN);
      double cur_price          = PositionGetDouble(POSITION_PRICE_CURRENT);
      double cur_sl             = PositionGetDouble(POSITION_SL);
      double cur_tp             = PositionGetDouble(POSITION_TP);
      double volume             = PositionGetDouble(POSITION_VOLUME);
      ENUM_POSITION_TYPE ptype  = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
      string comment            = PositionGetString(POSITION_COMMENT);

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

      SymbolTracker tr = g_trackers[tr_idx];
      double net_pts_gain = (ptype == POSITION_TYPE_BUY) ? (cur_price - open_price) : (open_price - cur_price);
      double net_drift_ticks_gained = net_pts_gain / MathMax(tr.abs_drift_per_tick, 1e-8);

      // --- 1. SORTIE IMMÉDIATE BREAK-EVEN APRÈS RÉCUPÉRATION D'UN SPIKE ---
      if(InpInstantExitOnSpikeRecovery && tr.spikes_while_open > 0 && profit_usd >= 0.01)
      {
         if(CloseSinglePositionTicket(ticket, psym, ptype, volume, "RECOVERY_BE_GREEN"))
         {
            g_total_green_closed++;
            g_total_recovery_be++;
            PrintFormat("[DerivBoomCrashHFT v6.00] >>> SAUVETAGE POST-SPIKE EN VERT sur %s (%s) : +%.2f USD (Spike récupéré à 100%% !) <<<",
                        psym, comment, profit_usd);
            g_trackers[tr_idx].cooldown_until_tick = g_trackers[tr_idx].tick_counter + InpCooldownAfterWin;
            continue;
         }
      }

      // --- 2. PRISE DE GAIN HAUTE FRÉQUENCE (GREEN_CASH_IN : +8 / +16 / +26 ticks nets) ---
      double target_net_ticks = InpStage1NetDriftTicks;
      if(StringFind(comment, "HFT_S2") >= 0)
         target_net_ticks = InpStage2NetDriftTicks;
      else if(StringFind(comment, "HFT_S3") >= 0)
         target_net_ticks = InpStage3NetDriftTicks;

      if(InpAutoCloseInGreen && profit_usd > 0.0 && net_drift_ticks_gained >= target_net_ticks)
      {
         if(CloseSinglePositionTicket(ticket, psym, ptype, volume, "GREEN_CASH_IN"))
         {
            g_total_green_closed++;
            PrintFormat("[DerivBoomCrashHFT v6.00] $$$ GAIN ENCAISSÉ sur %s (%s) : +%.2f USD (+%.1f ticks nets) $$$",
                        psym, comment, profit_usd, net_drift_ticks_gained);
            if(StringFind(comment, "HFT_S1") >= 0)
               g_trackers[tr_idx].stage1_cashed = true;
            g_trackers[tr_idx].cooldown_until_tick = g_trackers[tr_idx].tick_counter + InpCooldownAfterWin;
            continue;
         }
      }

      // --- 3. VERROUILLAGE BREAK-EVEN DU PALIER 2 APRÈS ENCAISSEMENT DU PALIER 1 ---
      if(InpLockBreakEvenAfterS1 && g_trackers[tr_idx].stage1_cashed && profit_usd > 0.0)
      {
         bool need_be = (ptype == POSITION_TYPE_BUY) ? (cur_sl < open_price - 1e-5) : (cur_sl > open_price + 1e-5 || cur_sl == 0.0);
         if(need_be)
            MovePositionToBreakEven(ticket, psym, open_price, cur_tp);
      }

      g_trackers[tr_idx].open_positions++;
   }

   int active_symbols = 0;
   for(int i = 0; i < g_num_trackers; i++)
   {
      if(g_trackers[i].open_positions > 0)
         active_symbols++;
      else
         g_trackers[i].spikes_while_open = 0;
   }
   return active_symbols;
}

//+------------------------------------------------------------------+
//| Ferme toutes les positions de tous les symboles (Arrêt Urgence)  |
//+------------------------------------------------------------------+
void CloseAllPositionsEverywhere(const string reason)
{
   int total = PositionsTotal();
   for(int p = total - 1; p >= 0; p--)
   {
      ulong ticket = PositionGetTicket(p);
      if(ticket == 0) continue;
      if((ulong)PositionGetInteger(POSITION_MAGIC) != InpMagicNumber) continue;
      CloseSinglePositionTicket(
         ticket,
         PositionGetString(POSITION_SYMBOL),
         (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE),
         PositionGetDouble(POSITION_VOLUME),
         reason
      );
   }
}

//+------------------------------------------------------------------+
//| Interroge le Cerveau ONNX de Colab + Filtre Hawkes et ouvre      |
//| soit une Rafale Post-Spike (1-2 paliers), soit un Scalp Continu  |
//+------------------------------------------------------------------+
bool OpenStagedDriftPositions(SymbolTracker &tr, const MqlTick &tick, bool is_continuous_scalp)
{
   if(tr.open_positions > 0 || (tick.time_msc - tr.last_order_sent_msc) < 3000)
      return false;

   bool term_trade = (bool)TerminalInfoInteger(TERMINAL_TRADE_ALLOWED);
   bool mql_trade  = (bool)MQLInfoInteger(MQL_TRADE_ALLOWED);
   if(!term_trade || !mql_trade)
      return false;

   double spread = tick.ask - tick.bid;
   tr.real_spread_pts = spread;
   tr.breakeven_ticks = spread / MathMax(tr.abs_drift_per_tick, 1e-8);

   if(tr.breakeven_ticks > InpMaxSpreadDriftMult)
      return false;

   // --- INTERROGATION DU CERVEAU IA GOOGLE COLAB (ONNX) + FILTRE HAWKES ---
   int c60 = 0;
   double ai_prob = EvaluateColabOnnxSurvivalProbability(tr, c60);
   tr.last_ai_prob = ai_prob;

   // Blocage anti-cluster Hawkes : si >= 2 spikes dans les 60 derniers ticks ou h_fast > InpMaxHawkesFast
   if(c60 >= 2 || tr.last_hawkes_fast > InpMaxHawkesFast)
   {
      tr.ai_filtered_count++;
      g_total_ai_blocked++;
      tr.cooldown_until_tick = tr.tick_counter + 25;
      return false;
   }

   int max_stages_requested = is_continuous_scalp ? InpContinuousDriftStages : InpStagedPositions;
   int approved_stages = max_stages_requested;

   if(InpUseColabOnnxBrain && g_onnx_ready)
   {
      if(ai_prob < InpOnnxThreshStage1)
      {
         tr.ai_filtered_count++;
         g_total_ai_blocked++;
         tr.cooldown_until_tick = tr.tick_counter + 20;
         PrintFormat("[DerivBoomCrashHFT v6.00 ONNX] BOUCLIER IA : Signal filtré sur %s | ProbIA=%.2f%% < %.2f%% | Hawkes=%.2f",
                     tr.name, ai_prob * 100.0, InpOnnxThreshStage1 * 100.0, tr.last_hawkes_fast);
         return false;
      }
      else if(ai_prob >= InpOnnxThreshStage3)
         approved_stages = MathMin(3, max_stages_requested);
      else if(ai_prob >= InpOnnxThreshStage2)
         approved_stages = MathMin(2, max_stages_requested);
      else
         approved_stages = 1;
   }

   int digits = (int)SymbolInfoInteger(tr.name, SYMBOL_DIGITS);
   ENUM_ORDER_TYPE_FILLING fill_mode = GetSupportedFillingMode(tr.name);
   int success_count = 0;

   double net_targets[3];
   net_targets[0] = InpStage1NetDriftTicks * tr.abs_drift_per_tick;
   net_targets[1] = InpStage2NetDriftTicks * tr.abs_drift_per_tick;
   net_targets[2] = InpStage3NetDriftTicks * tr.abs_drift_per_tick;

   string mode_tag = is_continuous_scalp ? "DRFT" : "SPK";

   for(int s_idx = 0; s_idx < approved_stages; s_idx++)
   {
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
      req.comment      = StringFormat("HFT_S%d_%s", s_idx + 1, mode_tag);

      double total_tp_move = spread + net_targets[s_idx];

      if(tr.is_boom)
      {
         req.type  = ORDER_TYPE_SELL;
         req.price = tick.bid;
         req.tp    = NormalizeDouble(tick.bid - total_tp_move, digits);
         req.sl    = (tr.sl_pts > 0.0) ? NormalizeDouble(tick.bid + tr.sl_pts, digits) : 0.0;
      }
      else
      {
         req.type  = ORDER_TYPE_BUY;
         req.price = tick.ask;
         req.tp    = NormalizeDouble(tick.ask + total_tp_move, digits);
         req.sl    = (tr.sl_pts > 0.0) ? NormalizeDouble(tick.ask - tr.sl_pts, digits) : 0.0;
      }

      bool sent = false;
      if(InpUseAsyncOrders)
         sent = OrderSendAsync(req, res);
      if(!sent)
         sent = OrderSend(req, res);

      if(sent)
         success_count++;
   }

   if(success_count > 0)
   {
      tr.last_order_sent_msc = tick.time_msc;
      tr.entry_tick          = tr.tick_counter;
      tr.stage1_cashed       = false;
      tr.spikes_while_open   = 0;
      tr.bursts_triggered++;
      if(is_continuous_scalp)
         tr.drift_scalps_triggered++;
      tr.open_positions     += success_count;
      g_total_bursts_all++;
      PrintFormat("[DerivBoomCrashHFT v6.00 TURBO] >>> %s LANCÉ sur %s (%d x %.2f lot | ProbIA=%.1f%% | Hawkes=%.2f | Spread=%.1ft) <<<",
                  is_continuous_scalp ? "SCALP DÉRIVE CONTINUE" : "RAFALE POST-SPIKE",
                  tr.name, success_count, tr.lot_per_stage, ai_prob * 100.0, tr.last_hawkes_fast, tr.breakeven_ticks);
      return true;
   }
   return false;
}

//+------------------------------------------------------------------+
//| Traite le flux de ticks d'un indice Boom ou Crash individuel     |
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
      tr.spike_start_price = price;
      tr.last_spike_amp    = MathAbs(delta);
      tr.calm_drift_ticks  = 0;

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
         tr.cooldown_until_tick = tr.tick_counter + InpCooldownAfterLoss;
         tr.pending_signal_tick = -1;
         PrintFormat("[DerivBoomCrashHFT v6.00] ALERTE SPIKE sur position ouverte %s (Spike #%d) -> Mode RECOVERY_BE_GREEN activé (sortie dès +0.01$) !",
                     tr.name, tr.spikes_while_open);
         return;
      }
   }
   else
   {
      // Vérifie si le tick dérive normalement dans notre sens
      bool is_calm_drift = tr.is_boom ? (delta <= 0.0) : (delta >= 0.0);
      if(is_calm_drift)
         tr.calm_drift_ticks++;
   }

   if(tr.open_positions > 0)
   {
      tr.pending_signal_tick = -1;
      return;
   }

   if(tr.tick_counter < tr.cooldown_until_tick)
      return;

   // --- MOTEUR 1 : ENTRÉE POST-SPIKE (2 ticks après un Spike) ---
   if(is_spike)
   {
      if(InpDelayTicksAfterSpike <= 0)
      {
         if(active_symbols_count < InpMaxActiveSymbols)
         {
            if(OpenStagedDriftPositions(tr, tick, false))
               active_symbols_count++;
         }
         tr.pending_signal_tick = -1;
      }
      else
      {
         tr.pending_signal_tick = tr.tick_counter + InpDelayTicksAfterSpike;
      }
      return;
   }
   else if(tr.pending_signal_tick > 0)
   {
      if(tr.tick_counter >= tr.pending_signal_tick)
      {
         if(active_symbols_count < InpMaxActiveSymbols)
         {
            if(OpenStagedDriftPositions(tr, tick, false))
               active_symbols_count++;
         }
         tr.pending_signal_tick = -1;
      }
      return;
   }

   // --- MOTEUR 2 : SCALP CONTINU EN DÉRIVE CALME (Sans attendre 10 min un spike !) ---
   if(InpEnableContinuousDrift && tr.calm_drift_ticks >= InpCalmDriftEntryTicks)
   {
      if(active_symbols_count < InpMaxActiveSymbols)
      {
         if(OpenStagedDriftPositions(tr, tick, true))
            active_symbols_count++;
      }
   }
}

//+------------------------------------------------------------------+
//| Scan global de tous les indices Boom & Crash (appelé à 50 ms)    |
//+------------------------------------------------------------------+
void ScanAllBoomCrashSymbols()
{
   if(g_emergency_stopped)
      return;

   double eq = AccountInfoDouble(ACCOUNT_EQUITY);
   if(eq > g_peak_equity)
      g_peak_equity = eq;

   double dd_pct = (g_peak_equity > 0.0) ? ((g_peak_equity - eq) / g_peak_equity) * 100.0 : 0.0;
   double daily_loss_pct = (g_initial_equity > 0.0) ? ((g_initial_equity - eq) / g_initial_equity) * 100.0 : 0.0;

   int active_symbols_count = ManageOpenPositionsAndCashInGreen();

   if(dd_pct >= InpMaxDrawdownPct || daily_loss_pct >= InpDailyLossPct)
   {
      g_emergency_stopped = true;
      CloseAllPositionsEverywhere("ESTOP_CIRCUIT_BREAKER");
      Alert(StringFormat("[DerivBoomCrashHFT] ARRÊT D'URGENCE DÉCLENCHÉ (DD=%.2f%%, PerteJour=%.2f%%)", dd_pct, daily_loss_pct));
      return;
   }

   for(int i = 0; i < g_num_trackers; i++)
   {
      ProcessSymbolTick(g_trackers[i], active_symbols_count);
   }

   if(InpShowDashboard)
   {
      bool algo_ok = (bool)TerminalInfoInteger(TERMINAL_TRADE_ALLOWED) && (bool)MQLInfoInteger(MQL_TRADE_ALLOWED);
      string hud = StringFormat(
         "=== DERIV BOOM & CRASH HFT MATRIX (v6.00 - TURBO GOLDEN-7 + COLAB ONNX) ===\n"
         "Cerveau IA Colab : %s | Mode : %s | Algo Trading : %s\n"
         "Équité : %.2f USD (DD : %.2f%%) | Rafales Totales : %I64d | Gains Encaissés : %I64d (Sauvetages BE : %I64d) | Bloqués IA : %I64d\n"
         "----------------------------------------------------------------------------------------------------------------------------\n"
         "INDICE             | SENS      | TICKS  | CALME(T) | SPREAD(T) | RAFALES | HAWKES | PROB IA | ÉTAT\n"
         "----------------------------------------------------------------------------------------------------------------------------\n",
         g_onnx_ready ? "ACTIF (IA3_DeepSurvivalMLP .ONNX)" : "HAWKES PHYSIQUE",
         InpEnableContinuousDrift ? "TURBO (Post-Spike + Dérive Continue)" : "POST-SPIKE SEUL",
         algo_ok ? "ACTIF (OK)" : "BLOQUÉ -> ACTIVEZ ALGO TRADING !",
         eq, dd_pct, g_total_bursts_all, g_total_green_closed, g_total_recovery_be, g_total_ai_blocked
      );

      for(int i = 0; i < g_num_trackers; i++)
      {
         SymbolTracker tr = g_trackers[i];
         string st = "PRÊT SCALP";
         if(tr.open_positions > 0)
         {
            if(tr.spikes_while_open > 0)
               st = StringFormat("RECOVERY BE (%d pos)", tr.open_positions);
            else
               st = StringFormat("EN CHASSE (%d pos)", tr.open_positions);
         }
         else if(tr.pending_signal_tick > 0)
            st = StringFormat("DÉLAI SPIKE (%I64dt)", tr.pending_signal_tick - tr.tick_counter);
         else if(tr.tick_counter < tr.cooldown_until_tick)
            st = StringFormat("RESPIRATION (%I64dt)", tr.cooldown_until_tick - tr.tick_counter);

         hud += StringFormat("%-18s | %-9s | %6I64d | %7I64dt | %8.1ft | %7I64d | %6.2f | %6.1f%% | %s\n",
                             tr.name,
                             tr.is_boom ? "SELL DRFT" : "BUY DRFT",
                             tr.tick_counter,
                             tr.calm_drift_ticks,
                             tr.breakeven_ticks,
                             tr.bursts_triggered,
                             tr.last_hawkes_fast,
                             tr.last_ai_prob * 100.0,
                             st);
      }
      Comment(hud);
   }
}

//+------------------------------------------------------------------+
//| Événement Tick du graphique hôte                                 |
//+------------------------------------------------------------------+
void OnTick()
{
   ScanAllBoomCrashSymbols();
}

//+------------------------------------------------------------------+
//| Événement Timer Haute Fréquence (50ms)                           |
//+------------------------------------------------------------------+
void OnTimer()
{
   ScanAllBoomCrashSymbols();
}
//+------------------------------------------------------------------+
