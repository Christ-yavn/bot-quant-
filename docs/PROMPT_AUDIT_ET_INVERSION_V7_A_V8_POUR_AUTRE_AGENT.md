# PROMPT MAÎTRE D'AUDIT ET D'INVERSION CONVEXE (V7 -> V8) POUR AGENT QUANTITATIF EXTERNE

> [!IMPORTANT]
> **Ce document contient l'intégralité du cahier des charges, de la méthode INVERT de Charlie Munger, des données télémétriques et du code source v7 nécessaires pour faire auditer et corriger la stratégie par une autre intelligence artificielle.**

---

## 📋 PROMPT COMPLET À COPIER-COLLER DANS LE SECOND AGENT

```text
========================================================================================
MISSION : AUDIT FORENSIQUE, APPLICATION DU PRINCIPE D'INVERSION (CHARLIE MUNGER) ET
CONVERSION D'UNE STRATÉGIE HFT PERDANTE (V7) EN STRATÉGIE CONVEXE GAGNANTE (V8)
========================================================================================

CONTEXTE & RÉFÉRENTIEL DU PROJET :
- Dépôt Git : https://github.com/Christ-yavn/bot-quant-
- Broker : Deriv (Indices Synthétiques Boom & Crash)
- Unités d'exécution : M1 (Haute Fréquence HFT) sur Crash 600, Crash 900, Boom 900, Boom 600, Crash 1000.
- Historique de télémétrie réelle disponible : data_summaries/v7/v7_closed_positions.csv (1 242 trades).

----------------------------------------------------------------------------------------
SECTION 1 : CADRE MÉTHODOLOGIQUE OBLIGATOIRE (SKILL INVERT-THINKING - CHARLIE MUNGER)
----------------------------------------------------------------------------------------
Vous devez appliquer rigoureusement la méthodologie d'inversion intellectuelle suivante :

---
name: invert-thinking
description: >
  Résout le problème à l'envers selon la technique de Charlie Munger (Berkshire Hathaway). Au lieu
  de "Comment réussir ?", demande "Comment garantir l'échec ?". Les obstacles à l'échec sont les
  facteurs de succès. Produit des insights contre-intuitifs souvent invisibles par l'approche directe.
  Utiliser dès que l'utilisateur veut raisonner à l'envers, penser l'inversion, chercher comment
  échouer, ou appliquer la technique de Charlie Munger.
category: raisonnement
tags: [inversion, munger, contre-intuitif, anti-problème, succès-par-échec]
trigger: "INVERT"
position: avant
---

# INVERT — Pensée Inversée (Munger)

## Définition
Résout le problème à l'envers. Au lieu de chercher comment réussir, on cherche comment garantir l'échec. Les obstacles qu'on identifie à l'échec sont les facteurs de succès à sécuriser. Technique de Charlie Munger (Berkshire Hathaway).

## Mécanisme d'action

### Étape 1 — Inversion du problème
- Question originale : "Comment réussir X ?"
- Question inversée : "Comment garantir l'échec de X ?"

### Étape 2 — Génération de l'échec
Lister tous les moyens de garantir l'échec :
```
Pour garantir l'échec de X :
1. [action qui mène à l'échec]
2. [action qui mène à l'échec]
3. [action qui mène à l'échec]
...
```

### Étape 3 — Rétro-inversion
Pour chaque facteur d'échec, identifier l'anti-facteur :
```
1. Si [A] garantit l'échec → éviter [A] est un facteur de succès
2. Si [B] garantit l'échec → éviter [B] est un facteur de succès
```

### Étape 4 — Synthèse
Les facteurs de succès identifiés par inversion sont souvent différents de ceux qu'on aurait trouvés par approche directe. Ce sont souvent des facteurs défensifs (ce qu'il ne faut PAS faire) plutôt qu'offensifs (ce qu'il faut faire).

## Syntaxe d'utilisation
```
INVERT, [objectif à inverser]
```

## Combinaisons clés
- `INVERT` + `Red Team` → inversion + critique
- `INVERT` + `/blindspots` → inversion + angles morts
- `INVERT` + `OODA` → inversion dans chaque phase


----------------------------------------------------------------------------------------
SECTION 2 : LE CONSTAT FACTUEL DE L'ÉCHEC DE LA V7.00 (-406.14 USD)
----------------------------------------------------------------------------------------
Dans la version v7.00, le robot a exécuté 1 242 trades réels sur le compte MetaTrader 5 (32449166).
Voici le bilan télémétrique certifié :
- Total trades : 1 242 trades
- Win Rate brut : 85.91 % (1 067 trades gagnants, 175 trades perdants)
- PnL Net Total : -406.14 USD (Perte nette de capital !)
- Gain moyen par trade gagnant : +0.20 USD
- Perte moyenne par trade perdant : -3.54 USD (Ratio Perte/Gain défavorable de 17.7 contre 1 !)
- Cause racine : Concavité négative extrême (Negative Skewness). Le bot ramasse des centimes de dérive calme (BUY sur Crash, SELL sur Boom) mais se fait faucher par les spikes imprévisibles du processus de Poisson.

----------------------------------------------------------------------------------------
SECTION 3 : L'ÉCHEC DU PREMIER PROTOTYPE V8.20 (PARALYSIE TOTALE : 68 113 REJETS / 0 TRADE)
----------------------------------------------------------------------------------------
Un premier prototype v8.20 a été déployé pour inverser la logique, mais il a été victime d'une paralysie totale :
- Ticks réels analysés : 69 332
- Spikes réels observés sur le marché : 82
- Filtre IA Bloqué : 68 113 fois consécutives !
- Entrées déclenchées : 0 (zéro trade en 24h !)

L'audit forensique a révélé 3 bugs bloquants dans le code de décision de la v8.20 :
1. Bug ONNX (Code erreur 5800 dans MT5) : Le modèle boom_crash_meta_brain.onnx exporté a 1 seule sortie scalaire [1, 1], mais le code MQL5 déclarait une sortie [1, 2], causant un échec d'initialisation de session.
2. Le verrou theta_eff (Ligne 1270) : En repli physique Poisson, p0 = base_p0 = 9.97 % sur Crash 600. Mais le code exigeait p0 >= theta_eff = 1.40 * base_p0 = 13.95 %. Puisque 9.97 % < 13.95 % en tout temps calme, le bot bloque 100 % des ticks !
3. Le verrou expected_payoff (Ligne 1291) : La formule imposait que pour avoir expected_payoff > 0, p0 devait dépasser 46.0 %, ce qui est physiquement impossible sur un processus de Poisson où les spikes ont une probabilité naturelle de 6 % à 10 % en 60 secondes.

----------------------------------------------------------------------------------------
SECTION 4 : VOTRE CAHIER DES CHARGES POUR L'INVERSION DE STRATÉGIE
----------------------------------------------------------------------------------------
En vous basant sur le principe INVERT de Charlie Munger :
1. RÉTRO-INVERSION DE LA POLARITÉ :
   - Dans la v7 : Le bot achetait sur Crash et vendait sur Boom pour récolter la dérive.
   - Dans la nouvelle v8 inversée : Le bot doit faire STRICTEMENT L'INVERSE :
     * VENDRE (SELL) sur Crash pour attraper les chutes explosives de spikes !
     * ACHETER (BUY) sur Boom pour attraper les explosions haussières de spikes !
2. RÉTRO-INVERSION DE LA GESTION DU RISQUE :
   - Au lieu de subir des pertes illimitées sur les spikes, le risque est désormais STRICTEMENT BORNÉ à la dérive adverse par un Stop Temporel analytique strict à M* = 60 ticks (perte maximale unitaire de ~ -0.20 $ à -0.25 $).
   - Dès qu'un spike frappe dans les 60 secondes, la position passe en gain géant (+3.50 $ à +15.00 $).
3. SUPPRESSION DE LA PARALYSIE :
   - L'algorithme ne doit PAS se bloquer lui-même avec des filtres théoriques impossibles à franchir.
   - Les entrées doivent se déclencher à intervalles réguliers en dérive calme (tous les 15-20 ticks calmes sans spike) pour capturer les 82+ spikes par session.
   - Dans notre simulation Python de ce principe sur les 1 242 trades v7, le PnL s'est inversé de -406.14 $ à +340.73 $ de gain net !

----------------------------------------------------------------------------------------
SECTION 5 : CODE SOURCE COMPLET DE LA V7.00 D'ORIGINE (À INVERSER)
----------------------------------------------------------------------------------------
Voici le code source intégral de la v7.00 qui a généré les 1 242 trades :

```mql5
//+------------------------------------------------------------------+
//|                                       DerivBoomCrashHFT_v7.mq5   |
//|        Quantitative High-Frequency Drift Harvester (v7.00)       |
//|        4 CORRECTIFS MAJEURS :                                    |
//|        1. Amortissement du Spread sur Vague Longue + Trailing    |
//|        2. Zéro Rejet [Invalid stops] & Anti-Spam OrderSendAsync  |
//|        3. Stop-Loss Plafonné en Dollars ($) & Anti-2e-Spike      |
//|        4. Cerveau IA ONNX 14 Variables 100% Sans Triche          |
//+------------------------------------------------------------------+
#property copyright "Deriv Quantitative HFT Research"
#property version   "7.00"
#property description "v7.00 Zero-Cheat ONNX + Long-Wave Spread Amortization + Dollar-Capped Risk + Zero Invalid Stops."
#property strict

#resource "\\Files\\boom_crash_meta_brain.onnx" as uchar ExtColabOnnxBrain[]

enum ENUM_SYMBOL_UNIVERSE
{
   UNIVERSE_GOLDEN_7_LIVE_WINNERS = 0, // Les 7 Indices Golden (Crash 600/900/500/1000, Boom 500/900/600)
   UNIVERSE_CLASSIC_10            = 1, // Les 10 Classiques (300, 500, 600, 900, 1000)
   UNIVERSE_CURRENT_CHART_ONLY    = 2  // Uniquement le symbole du graphique actuel
};

//--- Input Parameters
input group "=== 1. Cerveau IA Google Colab (.ONNX v7.00 Sans Triche) ==="
input bool   InpUseColabOnnxBrain           = true;   // Activer le Réseau ONNX v7.00 (14 variables dynamiques sans triche)
input bool   InpUseZeroCheatFeatures        = true;   // true = Nouveau modèle v7 sans triche | false = Ancien modèle v6
input double InpOnnxThreshStage1            = 0.8155; // Seuil IA v7 Palier 1 (Médiane Q50 calibrée hors échantillon)
input double InpOnnxThreshStage2            = 0.8161; // Seuil IA v7 Palier 2 (Quantile Q70 calibré)
input double InpOnnxThreshStage3            = 0.8165; // Seuil IA v7 Palier 3 (Quantile Q85 calibré)
input double InpMaxHawkesFast               = 1.15;   // Intensité Hawkes rapide max autorisée

input group "=== 2. Moteur Vague Longue (Amortissement du Spread 1x par Cycle) ==="
input ENUM_SYMBOL_UNIVERSE InpSymbolUniverse = UNIVERSE_GOLDEN_7_LIVE_WINNERS; // Univers à surveiller
input bool   InpEnableContinuousDrift       = true;   // Entrer en dérive calme stabilisée
input bool   InpEnablePostSpikeImmediate    = false;  // Désactivé par défaut (évite d'entrer 2t après un spike)
input int    InpCalmDriftEntryTicks         = 25;     // Ticks calmes requis avant d'entrer (25t = dérive stabilisée)
input int    InpMaxActiveSymbols            = 3;      // Max indices en position simultanément (réduit le risque global)
input int    InpScannerTimerMs              = 50;     // Fréquence du scanner (50 ms = 20x/sec)

input group "=== 3. Cibles Longues & Trailing Stop Virtuel Progressif ==="
input bool   InpAutoCloseInGreen            = true;   // Fermeture automatique en gain net
input double InpStage1NetDriftTicks         = 60.0;   // Cible nette Palier 1 (+60 ticks nets : amortit le spread 1 seule fois !)
input double InpStage2NetDriftTicks         = 100.0;  // Cible nette Palier 2 (+100 ticks nets)
input double InpStage3NetDriftTicks         = 140.0;  // Cible nette Palier 3 (+140 ticks nets)
input bool   InpUseVirtualTrailing          = true;   // Activer le Trailing Stop virtuel en mémoire dès +15 ticks nets
input double InpTrailingActivateNetTicks    = 15.0;   // Activation du Trailing virtuel (+15 ticks nets au-dessus du spread)
input double InpTrailingStepBackTicks       = 6.0;    // Distance de suivi du Trailing virtuel (sécurise le gain acquis)

input group "=== 4. Plafond de Risque en Dollars ($) & Sauvetage Anti-Rafale ==="
input bool   InpInstantExitOnSpikeRecovery  = true;   // Si 1 spike subi remonte à +0.01$, sortir immédiatement en vert
input int    InpMaxSpikesInRecovery         = 1;      // Coupe immédiatement si un 2e spike frappe pendant RECOVERY !
input double InpMaxRiskUsdPerTrade          = 2.50;   // Perte MAX absolue en Dollars par trade (ex: 2.50$ max au lieu de -11.66$)
input double InpSlSpikeMultiple             = 2.5;    // Multiple max de spike pour le SL serveur
input double InpLotsPerStage                = 0.0;    // Lots par palier (0.0 = lot min Deriv 0.20)
input int    InpCooldownAfterWin            = 45;     // Pause après un gain (45 ticks = évite le sur-trading)
input int    InpCooldownAfterLoss           = 240;    // Pause après une perte (240 ticks = 4 minutes)

input group "=== 5. Sécurité & Conformité Microstructure Deriv ==="
input bool   InpDemoAccountOnly             = true;   // Verrou Compte Démo uniquement
input double InpMaxDrawdownPct              = 10.0;   // Coupe-circuit Drawdown Max (%)
input double InpDailyLossPct                = 4.0;    // Coupe-circuit Perte Journalière Max (%)
input double InpMaxSpreadDriftMult          = 115.0;  // Plafond de Spread Réel (115t = débloque Crash 600, Boom 600/900, Crash 1000)
input ulong  InpMagicNumber                 = 20261019;// Magic Number v7.00
input bool   InpUseAsyncOrders              = true;   // Utiliser OrderSendAsync() avec verrou anti-spam
input bool   InpShowDashboard               = true;   // Afficher le tableau de bord

//--- Structure de suivi par symbole
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
   long     bursts_triggered;
   long     ai_filtered_count;
   double   last_ai_prob;
   double   last_hawkes_fast;
   long     cooldown_until_tick;
   long     spike_history_ticks[32];
   double   spike_history_amps[32];
   int      spike_history_count;
   int      open_positions;
   int      spikes_while_open;
   double   peak_net_drift_ticks; // Pour le Trailing Stop virtuel progressif
};

//--- Verrou d'idempotence pour éviter d'envoyer 20 ordres de fermeture pour le même ticket
struct ClosingTicketLock
{
   ulong    ticket;
   long     sent_msc;
};

SymbolTracker     g_trackers[];
int               g_num_trackers       = 0;
ClosingTicketLock g_closing_locks[64];
int               g_num_closing_locks  = 0;

long              g_onnx_handle        = INVALID_HANDLE;
bool              g_onnx_ready         = false;
bool              g_emergency_stopped  = false;
double            g_initial_equity     = 0.0;
double            g_peak_equity        = 0.0;
long              g_total_ticks_all    = 0;
long              g_total_spikes_all   = 0;
long              g_total_bursts_all   = 0;
long              g_total_green_closed = 0;
long              g_total_recovery_be  = 0;
long              g_total_ai_blocked   = 0;

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
   double pt          = SymbolInfoDouble(sym, SYMBOL_POINT);
   long   stops_lvl   = SymbolInfoInteger(sym, SYMBOL_TRADE_STOPS_LEVEL);
   long   freeze_lvl  = SymbolInfoInteger(sym, SYMBOL_TRADE_FREEZE_LEVEL);
   long   max_lvl     = MathMax(stops_lvl, freeze_lvl);
   // Marge de sécurité de +4 points au-dessus du niveau minimum du broker
   return (double)(max_lvl + 4) * pt;
}

//+------------------------------------------------------------------+
//| Calcule la distance Stop-Loss plafonnée en Dollars ($)           |
//+------------------------------------------------------------------+
double ComputeDollarCappedSlPts(const string sym, double lot, double default_sl_pts)
{
   double tick_val  = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_VALUE);
   double tick_size = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_SIZE);
   double min_dist  = GetBrokerMinStopDistancePts(sym);

   if(tick_val <= 0.0 || tick_size <= 0.0 || lot <= 0.0 || InpMaxRiskUsdPerTrade <= 0.0)
      return MathMax(min_dist, default_sl_pts);

   double usd_per_pt_per_lot = tick_val / tick_size;
   double max_pts_by_usd     = InpMaxRiskUsdPerTrade / (lot * usd_per_pt_per_lot);
   double capped_sl          = MathMin(default_sl_pts, max_pts_by_usd);
   return MathMax(min_dist, capped_sl);
}

//+------------------------------------------------------------------+
//| Initialisation du modèle ONNX                                    |
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
      PrintFormat("[DerivBoomCrashHFT v7.00] ERREUR chargement ONNX (code=%d) -> Mode Filtre Physique.", GetLastError());
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
   Print("[DerivBoomCrashHFT v7.00] >>> CERVEAU IA ONNX v7.00 (14 VARIABLES DYNAMIQUES SANS TRICHE) ACTIF ! <<<");
   return true;
}

//+------------------------------------------------------------------+
//| Évaluation du Cerveau ONNX v7.00 (100% Sans Triche)              |
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

   if(!g_onnx_ready || g_onnx_handle == INVALID_HANDLE)
   {
      double phys_prob = MathExp(-(be_ticks + InpStage1NetDriftTicks) / mean_tau) * MathExp(-0.15 * MathMax(0.0, h_fast - 0.85));
      return MathMax(0.0, MathMin(1.0, phys_prob));
   }

   float x[1][14];
   if(InpUseZeroCheatFeatures)
   {
      // Transformation v7.00 Sans Triche : Excès normalisés par rapport au processus de Poisson du symbole
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
      return 0.8155;

   return (double)out_proba[0][1];
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
   tr.calm_drift_ticks      = 0;
   tr.spikes_detected       = 0;
   tr.bursts_triggered      = 0;
   tr.ai_filtered_count     = 0;
   tr.last_ai_prob          = 0.0;
   tr.last_hawkes_fast      = 0.0;
   tr.cooldown_until_tick   = 0;
   tr.spike_history_count   = 0;
   tr.open_positions        = 0;
   tr.spikes_while_open     = 0;
   tr.peak_net_drift_ticks  = 0.0;

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
   tr.calib_source       = "TABLE_V7";

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
            tr.calib_source   = "LIVE_5K_V7";
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
   tr.sl_pts          = ComputeDollarCappedSlPts(sym, tr.lot_per_stage, InpSlSpikeMultiple * tr.mean_spike_pts);

   int dummy_c60 = 0;
   tr.last_ai_prob = EvaluateColabOnnxSurvivalProbability(tr, dummy_c60);
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
      Alert("[DerivBoomCrashHFT v7.00] VERROU SÉCURITÉ : Compte Réel détecté ! Exécution bloquée.");
      return(INIT_FAILED);
   }

   InitColabOnnxBrain();
   BuildSymbolUniverse();

   g_initial_equity = AccountInfoDouble(ACCOUNT_EQUITY);
   g_peak_equity    = g_initial_equity;

   EventSetMillisecondTimer(MathMax(25, InpScannerTimerMs));
   PrintFormat("[DerivBoomCrashHFT v7.00] Prêt sur %d indices | ONNX Sans Triche=%s | RisqueMax=%.2f$/trade | Cible1=+%.0ft",
               g_num_trackers, g_onnx_ready ? "ACTIF" : "PHYSIQUE", InpMaxRiskUsdPerTrade, InpStage1NetDriftTicks);
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
//| Fermeture idempotente (1 seul ordre envoyé par ticket !)         |
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
//| Gestion des positions ouvertes :                                 |
//| 1) Coupe-circuit en Dollars ($) et anti-2e-spike en RECOVERY     |
//| 2) Sortie verte post-spike (RECOVERY_BE_GREEN dès +0.01$)        |
//| 3) Trailing Stop virtuel progressif & Cible longue GREEN_CASH_IN |
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

      string psym              = PositionGetString(POSITION_SYMBOL);
      double profit_usd        = PositionGetDouble(POSITION_PROFIT) + PositionGetDouble(POSITION_SWAP);
      double open_price        = PositionGetDouble(POSITION_PRICE_OPEN);
      double cur_price         = PositionGetDouble(POSITION_PRICE_CURRENT);
      double volume            = PositionGetDouble(POSITION_VOLUME);
      ENUM_POSITION_TYPE ptype = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
      string comment           = PositionGetString(POSITION_COMMENT);

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
      double net_pts_gain          = (ptype == POSITION_TYPE_BUY) ? (cur_price - open_price) : (open_price - cur_price);
      double net_drift_ticks_gained = net_pts_gain / MathMax(tr.abs_drift_per_tick, 1e-8);

      if(net_drift_ticks_gained > g_trackers[tr_idx].peak_net_drift_ticks)
         g_trackers[tr_idx].peak_net_drift_ticks = net_drift_ticks_gained;

      // --- 1. PLAFOND MONÉTAIRE ABSOLU EN DOLLARS ET ANTI-2e-SPIKE EN RECOVERY ---
      if(InpMaxRiskUsdPerTrade > 0.0 && profit_usd <= -InpMaxRiskUsdPerTrade)
      {
         if(CloseSinglePositionTicket(ticket, psym, ptype, volume, "MAX_USD_RISK_CUT"))
         {
            PrintFormat("[DerivBoomCrashHFT v7.00] COUPE-CIRCUIT RISQUE MAX (%.2f USD) sur %s -> Perte plafonnée !", profit_usd, psym);
            g_trackers[tr_idx].cooldown_until_tick = g_trackers[tr_idx].tick_counter + InpCooldownAfterLoss;
            continue;
         }
      }

      if(tr.spikes_while_open > InpMaxSpikesInRecovery)
      {
         if(CloseSinglePositionTicket(ticket, psym, ptype, volume, "RECOVERY_2ND_SPIKE_CUT"))
         {
            PrintFormat("[DerivBoomCrashHFT v7.00] COUPE ANTI-RAFALE (Spike #%d) sur %s (%.2f USD) -> Évite -11$ !",
                        tr.spikes_while_open, psym, profit_usd);
            g_trackers[tr_idx].cooldown_until_tick = g_trackers[tr_idx].tick_counter + InpCooldownAfterLoss;
            continue;
         }
      }

      // --- 2. SAUVETAGE POST-SPIKE EN VERT DÈS +0.01$ ---
      if(InpInstantExitOnSpikeRecovery && tr.spikes_while_open > 0 && profit_usd >= 0.01)
      {
         if(CloseSinglePositionTicket(ticket, psym, ptype, volume, "RECOVERY_BE_GREEN"))
         {
            g_total_green_closed++;
            g_total_recovery_be++;
            PrintFormat("[DerivBoomCrashHFT v7.00] >>> SAUVETAGE POST-SPIKE EN VERT sur %s : +%.2f USD <<<", psym, profit_usd);
            g_trackers[tr_idx].cooldown_until_tick = g_trackers[tr_idx].tick_counter + InpCooldownAfterWin;
            continue;
         }
      }

      // --- 3. TRAILING STOP VIRTUEL PROGRESSIF (SÉCURISE LE GAIN DÈS +15 TICKS NETS) ---
      if(InpUseVirtualTrailing && tr.spikes_while_open == 0 && profit_usd > 0.0 &&
         g_trackers[tr_idx].peak_net_drift_ticks >= InpTrailingActivateNetTicks)
      {
         double trail_floor = g_trackers[tr_idx].peak_net_drift_ticks - InpTrailingStepBackTicks;
         if(net_drift_ticks_gained <= trail_floor && net_drift_ticks_gained >= 5.0)
         {
            if(CloseSinglePositionTicket(ticket, psym, ptype, volume, "TRAILING_GREEN_LOCK"))
            {
               g_total_green_closed++;
               PrintFormat("[DerivBoomCrashHFT v7.00] $$$ TRAILING LOCK sur %s : +%.2f USD (+%.1f ticks nets, pic=%.1ft) $$$",
                           psym, profit_usd, net_drift_ticks_gained, g_trackers[tr_idx].peak_net_drift_ticks);
               g_trackers[tr_idx].cooldown_until_tick = g_trackers[tr_idx].tick_counter + InpCooldownAfterWin;
               continue;
            }
         }
      }

      // --- 4. CIBLE DE VAGUE LONGUE (GREEN_CASH_IN : +60 / +100 / +140 TICKS NETS) ---
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
            PrintFormat("[DerivBoomCrashHFT v7.00] $$$ VAGUE LONGUE ENCAISSÉE sur %s (%s) : +%.2f USD (+%.1f ticks nets) $$$",
                        psym, comment, profit_usd, net_drift_ticks_gained);
            g_trackers[tr_idx].cooldown_until_tick = g_trackers[tr_idx].tick_counter + InpCooldownAfterWin;
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
         g_trackers[i].spikes_while_open    = 0;
         g_trackers[i].peak_net_drift_ticks = 0.0;
      }
   }
   return active_symbols;
}

//+------------------------------------------------------------------+
//| Ouverture d'une position Vague Longue (0 Rejet [Invalid stops])  |
//+------------------------------------------------------------------+
bool OpenStagedDriftPositions(SymbolTracker &tr, const MqlTick &tick, bool is_continuous_scalp)
{
   if(tr.open_positions > 0 || (tick.time_msc - tr.last_order_sent_msc) < 5000)
      return false;

   if(!(bool)TerminalInfoInteger(TERMINAL_TRADE_ALLOWED) || !(bool)MQLInfoInteger(MQL_TRADE_ALLOWED))
      return false;

   double spread = tick.ask - tick.bid;
   tr.real_spread_pts = spread;
   tr.breakeven_ticks = spread / MathMax(tr.abs_drift_per_tick, 1e-8);

   if(tr.breakeven_ticks > InpMaxSpreadDriftMult)
      return false;

   int c60 = 0;
   double ai_prob = EvaluateColabOnnxSurvivalProbability(tr, c60);
   tr.last_ai_prob = ai_prob;

   if(c60 >= 2 || tr.last_hawkes_fast > InpMaxHawkesFast)
   {
      tr.ai_filtered_count++;
      g_total_ai_blocked++;
      tr.cooldown_until_tick = tr.tick_counter + 30;
      return false;
   }

   if(InpUseColabOnnxBrain && g_onnx_ready && ai_prob < InpOnnxThreshStage1)
   {
      tr.ai_filtered_count++;
      g_total_ai_blocked++;
      tr.cooldown_until_tick = tr.tick_counter + 20;
      PrintFormat("[DerivBoomCrashHFT v7.00 ONNX] BOUCLIER IA ACTIF : Signal filtré sur %s | ProbIA=%.2f%% < %.2f%% | Hawkes=%.2f",
                  tr.name, ai_prob * 100.0, InpOnnxThreshStage1 * 100.0, tr.last_hawkes_fast);
      return false;
   }

   // Verrouille immédiatement l'horodatage AVANT l'envoi pour interdire tout flood en cas de rejet serveur
   tr.last_order_sent_msc = tick.time_msc;

   int digits = (int)SymbolInfoInteger(tr.name, SYMBOL_DIGITS);
   ENUM_ORDER_TYPE_FILLING fill_mode = GetSupportedFillingMode(tr.name);
   double safe_sl_pts = ComputeDollarCappedSlPts(tr.name, tr.lot_per_stage, InpSlSpikeMultiple * tr.mean_spike_pts);
   tr.sl_pts = safe_sl_pts;

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
   req.comment      = is_continuous_scalp ? "HFT_S1_DRFT_V7" : "HFT_S1_SPK_V7";

   // CORRECTIF CRITIQUE : req.tp = 0.0 (aucun TP serveur proche qui viole SYMBOL_TRADE_STOPS_LEVEL !)
   // La sortie en gain est gérée à 100% par ManageOpenPositionsAndCashInGreen() à 50 ms.
   req.tp = 0.0;

   if(tr.is_boom)
   {
      req.type  = ORDER_TYPE_SELL;
      req.price = tick.bid;
      req.sl    = (safe_sl_pts > 0.0) ? NormalizeDouble(tick.ask + safe_sl_pts, digits) : 0.0;
   }
   else
   {
      req.type  = ORDER_TYPE_BUY;
      req.price = tick.ask;
      req.sl    = (safe_sl_pts > 0.0) ? NormalizeDouble(tick.bid - safe_sl_pts, digits) : 0.0;
   }

   bool sent = false;
   if(InpUseAsyncOrders)
      sent = OrderSendAsync(req, res);
   else
      sent = OrderSend(req, res);

   if(sent)
   {
      tr.spikes_while_open   = 0;
      tr.peak_net_drift_ticks = 0.0;
      tr.bursts_triggered++;
      tr.open_positions++;
      g_total_bursts_all++;
      PrintFormat("[DerivBoomCrashHFT v7.00] >>> POSITION VAGUE LONGUE LANCÉE sur %s (%.2f lot | ProbIA=%.2f%% | Spread=%.1ft | SL=%.2f pts) <<<",
                  tr.name, tr.lot_per_stage, ai_prob * 100.0, tr.breakeven_ticks, safe_sl_pts);
      return true;
   }
   else
   {
      // En cas de rejet, pause de 15 ticks pour ne jamais spammer le serveur Deriv
      tr.cooldown_until_tick = tr.tick_counter + 15;
   }
   return false;
}

//+------------------------------------------------------------------+
//| Traitement tick par tick d'un indice                             |
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
         tr.cooldown_until_tick = tr.tick_counter + InpCooldownAfterLoss;
         PrintFormat("[DerivBoomCrashHFT v7.00] ALERTE SPIKE #%d sur position ouverte %s (Max autorisé=%d)",
                     tr.spikes_while_open, tr.name, InpMaxSpikesInRecovery);
         return;
      }
   }
   else
   {
      bool is_calm_drift = tr.is_boom ? (delta <= 0.0) : (delta >= 0.0);
      if(is_calm_drift)
         tr.calm_drift_ticks++;
   }

   if(tr.open_positions > 0 || tr.tick_counter < tr.cooldown_until_tick)
      return;

   if(InpEnableContinuousDrift && tr.calm_drift_ticks >= InpCalmDriftEntryTicks)
   {
      if(active_symbols_count < InpMaxActiveSymbols)
      {
         if(OpenStagedDriftPositions(tr, tick, true))
            active_symbols_count++;
      }
   }
}

void ScanAllBoomCrashSymbols()
{
   if(g_emergency_stopped)
      return;

   double eq = AccountInfoDouble(ACCOUNT_EQUITY);
   if(eq > g_peak_equity)
      g_peak_equity = eq;

   double dd_pct         = (g_peak_equity > 0.0) ? ((g_peak_equity - eq) / g_peak_equity) * 100.0 : 0.0;
   double daily_loss_pct = (g_initial_equity > 0.0) ? ((g_initial_equity - eq) / g_initial_equity) * 100.0 : 0.0;

   int active_symbols_count = ManageOpenPositionsAndCashInGreen();

   if(dd_pct >= InpMaxDrawdownPct || daily_loss_pct >= InpDailyLossPct)
   {
      g_emergency_stopped = true;
      Alert(StringFormat("[DerivBoomCrashHFT v7.00] ARRÊT D'URGENCE (DD=%.2f%%, PerteJour=%.2f%%)", dd_pct, daily_loss_pct));
      return;
   }

   for(int i = 0; i < g_num_trackers; i++)
      ProcessSymbolTick(g_trackers[i], active_symbols_count);
}

void OnTick()  { ScanAllBoomCrashSymbols(); }
void OnTimer() { ScanAllBoomCrashSymbols(); }
//+------------------------------------------------------------------+

```

----------------------------------------------------------------------------------------
LIVRABLE DEMANDÉ :
1. Audit critique des causes de l'échec de la v7 et de la paralysie de la v8.
2. Architecture précise de la stratégie inverse v8 corrigée.
3. Code source MQL5 complet, propre, compilable sans warning ni erreur, prêt pour production immédiate.
========================================================================================
```
