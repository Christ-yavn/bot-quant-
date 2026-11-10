//+------------------------------------------------------------------+
//|                             Deriv_VolSqueeze_Breakout_EA_v3.mq5 |
//|        Quantitative Production Blueprint - Deriv Synthetic Audit |
//|   Target Universe: Omni-Basket 8-Assets & Champions 11 Familles  |
//|   Architectures  : S1 (Squeeze Breakout), S2 (Momentum), S3 (OU) |
//|   Features       : Retractable MQL5 UI (OnChartEvent)            |
//|                    Real-Time Telemetry Engine (Zero 0.00 bps)    |
//|                    Lookback Shift Bug Fix (rolling_std[1])       |
//|                    OrderCalcMargin Protection & Direction Filter |
//|                    Cold-Boot Freshness Guard + Hard Disaster SL  |
//|   Release        : v3.52 (Omni-Basket & Retractable UI L99 Prod - Direction Fix v3.52) |
//+------------------------------------------------------------------+
#property copyright "Quantitative Research & Algorithmic Systems (Audit-Hardened)"
#property link      "https://github.com/Christ-yavn/bot-quant-"
#property version   "3.52"
#property description "QuantPod v3.52 - Omni-Basket 8-Assets (S1/S2/S3), Retractable UI, Cold-Boot Guard & Hard Disaster SL"
#property strict

#include <Trade\Trade.mqh>
#include <Trade\PositionInfo.mqh>
#include <Trade\SymbolInfo.mqh>

//+------------------------------------------------------------------+
//| Strategy & Direction Enumerations                                |
//+------------------------------------------------------------------+
enum ENUM_STRATEGY_MODE
{
   STRAT_S1_VOL_SQUEEZE_BREAKOUT   = 0, // S1: Volatility Squeeze & Impulse Breakout
   STRAT_S2_MOMENTUM_CONTINUATION  = 1, // S2: Trend & Momentum Continuation
   STRAT_S3_OU_MEAN_REVERSION      = 2  // S3: Ornstein-Uhlenbeck Mean-Reversion
};

enum ENUM_DIRECTION_MODE
{
   DIR_BOTH       = 0, // Both BUY and SELL allowed
   DIR_LONG_ONLY  = 1, // Long / BUY only
   DIR_SHORT_ONLY = 2  // Short / SELL only
};

//--- Input Parameters: Signal & Strategy Modes
input group "=== 1. Strategy Engine & Impulse Parameters ==="
input ENUM_STRATEGY_MODE InpStrategyMode        = STRAT_S1_VOL_SQUEEZE_BREAKOUT; // Default Strategy Engine (S1, S2, S3)
input ENUM_DIRECTION_MODE InpDirectionMode      = DIR_BOTH;                      // Allowed Trade Direction (Both, Long, Short)
input ENUM_TIMEFRAMES   InpTimeframe            = PERIOD_H1;                     // Execution Timeframe (H1, M30, M15, H4, D1)
input int               InpVolLookback          = 20;                            // Rolling Volatility / Momentum Window (Bars, N=20)
input int               InpQuantileWindow       = 100;                           // Squeeze Percentile Lookback (Bars, M=100)
input double            InpSqueezeQuantile      = 0.30;                          // Bandwidth Squeeze Quantile (0.30 = 30th pct)
input double            InpBreakoutZScore       = 1.25;                          // Z-Score Threshold (1.25 for S1, 1.50 S2, 2.00 S3)
input int               InpMaxHoldBars          = 4;                             // Time-Stop Horizon (Bars on effective timeframe)
input int               InpMaxEntryDelaySec     = 300;                           // Cold-Boot Freshness Guard: Max Entry Delay (Sec, 300s=5m)

//--- Input Parameters: C2 Machine Learning ONNX Filter
input group "=== 2. C2 Machine Learning / ONNX Filter (7 Features) ==="
input bool              InpUseONNXFilter        = false;                         // Enable C2 ONNX GBDT Filter (Default: False - Pure Quant)
input string            InpONNXModelName        = "c2_vol_filter.onnx";          // ONNX Model File (Auto-selects v25/v75 model)
input double            InpMinWinProbability    = 0.42;                          // Min Predicted Win Probability (0.42 = 42%)

//--- Input Parameters: Excursion Guardrails & Dynamic Profit Lock
input group "=== 3. Excursion Guardrails, Dynamic Lock & Hard Disaster SL ==="
input bool              InpUseHardTPSL          = true;                          // Enable Hard Disaster Stop-Loss on Server (Default: True)
input int               InpATRPeriod            = 20;                            // ATR Period for Guardrails & Spread Ratio
input double            InpHardSL_ATR           = 2.50;                          // Hard Disaster Stop-Loss (Multiples of ATR20)
input double            InpHardTP_ATR           = 4.00;                          // Optional Hard Take-Profit Target (Multiples of ATR20)
input bool              InpUseTrailingLock      = true;                          // Enable Dynamic Profit Excursion Lock (Hardened v3.31/v3.52)
input double            InpLockTriggerATR       = 1.20;                          // Profit Lock Trigger (+1.20 ATR MFE)
input double            InpLockOffsetATR        = 0.20;                          // Locked Profit Buffer (+0.20 ATR above Entry / BE+)
input double            InpMaxSpreadToATR       = 0.050;                         // Max Allowed Spread / ATR Ratio (5.0% Ceiling)
input double            InpMaxSpreadBps         = 4.50;                          // Max Allowed Spread in Basis Points of Price

//--- Input Parameters: Risk Management & Multi-Asset Auto-Preset Matrix
input group "=== 4. Risk Management, Omni-Basket & UI ==="
input double            InpRiskPerSDPct         = 0.50;                          // Account Equity Risk (%) per 1-SD Move
input double            InpMaxDailyLossPct      = 3.00;                          // Daily Drawdown Circuit Breaker (% of Start-of-Day Equity)
input double            InpMaxLotCap            = 0.05;                          // Hard Cap on Position Volume (Default 0.05 lot on V25)
input ulong             InpMagicNumber          = 20261021;                      // Strategy Magic Number
input int               InpSlippagePoints       = 50;                            // Max Permissible Slippage (Points)
input bool              InpApplyV340TriActifsPreset = true;                      // Auto-Enforce Omni-Basket Preset Matrix (8 Elite Assets)
input bool              InpAllowV75Trading      = false;                         // Allow Entries on Volatility 75 (Default: False - Paused)

//--- Internal State & Architecture Variables
CTrade         ExtTrade;
CPositionInfo  ExtPosition;
CSymbolInfo    ExtSymbol;

int            ExtATRHandle         = INVALID_HANDLE;
long           ExtOnnxHandle        = INVALID_HANDLE;
datetime       ExtLastBarTime       = 0;
datetime       ExtCurrentDay        = 0;
double         ExtDayStartEq        = 0.0;
bool           ExtModelLoaded       = false;
string         ExtActiveModelFile   = "";

// Effective auto-configured parameters
string         ExtEffRole           = "ALPHA_KING_V25";
ENUM_TIMEFRAMES ExtEffTimeframe     = PERIOD_H1;
ENUM_STRATEGY_MODE ExtEffStrategyMode = STRAT_S1_VOL_SQUEEZE_BREAKOUT;
double         ExtEffSqueezeQ       = 0.30;
double         ExtEffBreakoutZ      = 1.25;
int            ExtEffMaxHoldBars    = 4;
double         ExtEffLotCap         = 0.05;
ulong          ExtEffMagic          = 20261021;
bool           ExtEffUseONNX        = false;
int            ExtEffSlippage       = 50;
bool           ExtIsSymbolPaused    = false;
double         ExtEffMinProb        = 0.42;

// Telemetry state (zero 0.00 bps values)
double         ExtLastRetBps        = 0.0; // v3.52: Signed breakout bar return in bps (Close[shift=1] - Close[shift=2])
double         ExtLastStd20         = 0.0;
double         ExtLastSqueezeQ      = 0.0;
double         ExtLastBreakoutZ     = 0.0;
double         ExtLastMomZ          = 0.0;
double         ExtLastSpreadBps     = 0.0;
double         ExtLastATR           = 0.0;
double         ExtLastOnnxProb      = 1.0;
long           ExtTotalSignals      = 0;
long           ExtTotalTrades       = 0;

// Interactive retractable UI state
bool           ExtDashboardMinimized = false;
const string   UI_PREFIX            = "QP350_";

//+------------------------------------------------------------------+
//| Refresh effective parameters & Omni-Basket Auto-Preset Matrix    |
//+------------------------------------------------------------------+
void SyncEffectiveParameters()
{
   if(InpApplyV340TriActifsPreset)
   {
      ExtEffUseONNX  = false; // Pure deterministic signal across basket
      ExtEffSlippage = MathMax(50, InpSlippagePoints);

      if(StringFind(_Symbol, "25 (1s)") >= 0)
      {
         ExtEffRole         = "ALPHA_KING_V25";
         ExtEffTimeframe    = PERIOD_H1;
         ExtEffStrategyMode = STRAT_S1_VOL_SQUEEZE_BREAKOUT;
         ExtEffSqueezeQ     = 0.30;
         ExtEffBreakoutZ    = 1.25;
         ExtEffMaxHoldBars  = 4;
         ExtEffLotCap       = 0.050;
         ExtEffMagic        = 20261021;
         ExtIsSymbolPaused  = false;
      }
      else if(StringFind(_Symbol, "15 (1s)") >= 0)
      {
         ExtEffRole         = "STABILIZER_V15";
         ExtEffTimeframe    = PERIOD_M30;
         ExtEffStrategyMode = STRAT_S1_VOL_SQUEEZE_BREAKOUT;
         ExtEffSqueezeQ     = 0.30;
         ExtEffBreakoutZ    = 1.25;
         ExtEffMaxHoldBars  = 8;
         ExtEffLotCap       = 0.500;
         ExtEffMagic        = 20261015;
         ExtIsSymbolPaused  = false;
      }
      else if(StringFind(_Symbol, " 5 (1s)") >= 0 || StringFind(_Symbol, "Volatility 5 (1s)") >= 0 || (StringFind(_Symbol, "5 (1s)") >= 0 && StringFind(_Symbol, "15 (1s)") < 0 && StringFind(_Symbol, "25 (1s)") < 0 && StringFind(_Symbol, "75 (1s)") < 0))
      {
         ExtEffRole         = "HIGH_FREQ_V5";
         ExtEffTimeframe    = PERIOD_M30;
         ExtEffStrategyMode = STRAT_S1_VOL_SQUEEZE_BREAKOUT;
         ExtEffSqueezeQ     = 0.30;
         ExtEffBreakoutZ    = 1.25;
         ExtEffMaxHoldBars  = 8;
         ExtEffLotCap       = 0.200;
         ExtEffMagic        = 20261025;
         ExtIsSymbolPaused  = false;
      }
      else if(StringFind(_Symbol, "550") >= 0 || StringFind(_Symbol, "Crash 550") >= 0)
      {
         ExtEffRole         = "CHAMPION_VC550";
         ExtEffTimeframe    = PERIOD_H4;
         ExtEffStrategyMode = STRAT_S1_VOL_SQUEEZE_BREAKOUT;
         ExtEffSqueezeQ     = 0.30;
         ExtEffBreakoutZ    = 1.25;
         ExtEffMaxHoldBars  = 4;
         ExtEffLotCap       = 0.500;
         ExtEffMagic        = 20261550;
         ExtIsSymbolPaused  = false;
      }
      else if(StringFind(_Symbol, "1500 DOWN") >= 0 || StringFind(_Symbol, "DEX 1500 DOWN") >= 0)
      {
         ExtEffRole         = "DEX1500_ELITE";
         ExtEffTimeframe    = (_Period == PERIOD_M15 ? PERIOD_M15 : PERIOD_H1);
         ExtEffStrategyMode = STRAT_S1_VOL_SQUEEZE_BREAKOUT;
         ExtEffSqueezeQ     = 0.30;
         ExtEffBreakoutZ    = 1.25;
         ExtEffMaxHoldBars  = 4;
         ExtEffLotCap       = 0.200;
         ExtEffMagic        = 20261500;
         ExtIsSymbolPaused  = false;
      }
      else if(StringFind(_Symbol, "Range Break 200") >= 0 || StringFind(_Symbol, "Range 200") >= 0)
      {
         ExtEffRole         = "RANGE_MEANREV";
         ExtEffTimeframe    = (_Period == PERIOD_M15 ? PERIOD_M15 : PERIOD_H1);
         ExtEffStrategyMode = STRAT_S3_OU_MEAN_REVERSION;
         ExtEffSqueezeQ     = 0.30;
         ExtEffBreakoutZ    = 2.00;
         ExtEffMaxHoldBars  = 4;
         ExtEffLotCap       = 0.200;
         ExtEffMagic        = 20261200;
         ExtIsSymbolPaused  = false;
      }
      else if(StringFind(_Symbol, "Ladder") >= 0)
      {
         ExtEffRole         = "LADDER_MOM";
         ExtEffTimeframe    = PERIOD_H4;
         ExtEffStrategyMode = STRAT_S2_MOMENTUM_CONTINUATION;
         ExtEffSqueezeQ     = 0.30;
         ExtEffBreakoutZ    = 1.50;
         ExtEffMaxHoldBars  = 4;
         ExtEffLotCap       = 0.200;
         ExtEffMagic        = 20261400;
         ExtIsSymbolPaused  = false;
      }
      else if(StringFind(_Symbol, "Boom 300") >= 0)
      {
         ExtEffRole         = "BOOM300_SWING";
         ExtEffTimeframe    = PERIOD_D1;
         ExtEffStrategyMode = STRAT_S2_MOMENTUM_CONTINUATION;
         ExtEffSqueezeQ     = 0.30;
         ExtEffBreakoutZ    = 1.50;
         ExtEffMaxHoldBars  = 4;
         ExtEffLotCap       = 0.500;
         ExtEffMagic        = 20261300;
         ExtIsSymbolPaused  = false;
      }
      else if(StringFind(_Symbol, "Volatility 10 Index") >= 0 || (StringFind(_Symbol, "10 Index") >= 0 && StringFind(_Symbol, "1s") < 0))
      {
         ExtEffRole         = "V10_STD_ALPHA";
         ExtEffTimeframe    = PERIOD_H1;
         ExtEffStrategyMode = STRAT_S1_VOL_SQUEEZE_BREAKOUT;
         ExtEffSqueezeQ     = 0.30;
         ExtEffBreakoutZ    = 1.25;
         ExtEffMaxHoldBars  = 4;
         ExtEffLotCap       = 0.500;
         ExtEffMagic        = 20261010;
         ExtIsSymbolPaused  = false;
      }
      else
      {
         ExtEffRole         = "PAUSED_STANDBY";
         ExtEffTimeframe    = InpTimeframe;
         ExtEffStrategyMode = InpStrategyMode;
         ExtEffSqueezeQ     = InpSqueezeQuantile;
         ExtEffBreakoutZ    = InpBreakoutZScore;
         ExtEffMaxHoldBars  = InpMaxHoldBars;
         ExtEffLotCap       = 0.020;
         ExtEffMagic        = InpMagicNumber;
         ExtIsSymbolPaused  = true;
      }
   }
   else
   {
      ExtEffRole         = "MANUAL_CUSTOM";
      ExtEffTimeframe    = InpTimeframe;
      ExtEffStrategyMode = InpStrategyMode;
      ExtEffSqueezeQ     = InpSqueezeQuantile;
      ExtEffBreakoutZ    = InpBreakoutZScore;
      ExtEffMaxHoldBars  = InpMaxHoldBars;
      ExtEffLotCap       = InpMaxLotCap;
      ExtEffMagic        = InpMagicNumber;
      ExtEffUseONNX      = InpUseONNXFilter;
      ExtEffSlippage     = InpSlippagePoints;
      ExtIsSymbolPaused  = (StringFind(_Symbol, "75") >= 0 && !InpAllowV75Trading);
   }
}

//+------------------------------------------------------------------+
//| Normalize price to exact broker Tick Size and Digits             |
//+------------------------------------------------------------------+
double NormalizePrice(const double price)
{
   double tick_size = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(tick_size > 0.0)
      return NormalizeDouble(MathRound(price / tick_size) * tick_size, _Digits);
   return NormalizeDouble(price, _Digits);
}

//+------------------------------------------------------------------+
//| Normalize probability threshold (handles both 0.42 and 42.0)     |
//+------------------------------------------------------------------+
double GetNormalizedMinWinProb()
{
   double p = InpMinWinProbability;
   if(p > 1.0)
      p = p / 100.0;
   return MathMax(0.05, MathMin(0.95, p));
}

//+------------------------------------------------------------------+
//| UI Helper: Create or Update Rectangle Object                     |
//+------------------------------------------------------------------+
void CreateRect(string name, int x, int y, int w, int h, color bg_col, color border_col = clrNONE)
{
   if(ObjectFind(0, name) < 0)
   {
      ObjectCreate(0, name, OBJ_RECTANGLE_LABEL, 0, 0, 0);
      ObjectSetInteger(0, name, OBJPROP_CORNER, CORNER_LEFT_UPPER);
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
      ObjectSetInteger(0, name, OBJPROP_BACK, false);
   }
   ObjectSetInteger(0, name, OBJPROP_XDISTANCE, x);
   ObjectSetInteger(0, name, OBJPROP_YDISTANCE, y);
   ObjectSetInteger(0, name, OBJPROP_XSIZE, w);
   ObjectSetInteger(0, name, OBJPROP_YSIZE, h);
   ObjectSetInteger(0, name, OBJPROP_BGCOLOR, bg_col);
   ObjectSetInteger(0, name, OBJPROP_BORDER_TYPE, BORDER_FLAT);
   ObjectSetInteger(0, name, OBJPROP_COLOR, (border_col != clrNONE ? border_col : bg_col));
}

//+------------------------------------------------------------------+
//| UI Helper: Create or Update Label Object                         |
//+------------------------------------------------------------------+
void CreateLabel(string name, int x, int y, string text, color col, int font_size = 8, string font_name = "Consolas")
{
   if(ObjectFind(0, name) < 0)
   {
      ObjectCreate(0, name, OBJ_LABEL, 0, 0, 0);
      ObjectSetInteger(0, name, OBJPROP_CORNER, CORNER_LEFT_UPPER);
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
      ObjectSetInteger(0, name, OBJPROP_BACK, false);
   }
   ObjectSetInteger(0, name, OBJPROP_XDISTANCE, x);
   ObjectSetInteger(0, name, OBJPROP_YDISTANCE, y);
   ObjectSetString(0, name, OBJPROP_TEXT, text);
   ObjectSetInteger(0, name, OBJPROP_COLOR, col);
   ObjectSetInteger(0, name, OBJPROP_FONTSIZE, font_size);
   ObjectSetString(0, name, OBJPROP_FONT, font_name);
}

//+------------------------------------------------------------------+
//| UI Helper: Create or Update Button Object                        |
//+------------------------------------------------------------------+
void CreateButton(string name, int x, int y, int w, int h, string text, color bg_col, color text_col, int font_size = 8, string font_name = "Consolas")
{
   if(ObjectFind(0, name) < 0)
   {
      ObjectCreate(0, name, OBJ_BUTTON, 0, 0, 0);
      ObjectSetInteger(0, name, OBJPROP_CORNER, CORNER_LEFT_UPPER);
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
      ObjectSetInteger(0, name, OBJPROP_BACK, false);
   }
   ObjectSetInteger(0, name, OBJPROP_XDISTANCE, x);
   ObjectSetInteger(0, name, OBJPROP_YDISTANCE, y);
   ObjectSetInteger(0, name, OBJPROP_XSIZE, w);
   ObjectSetInteger(0, name, OBJPROP_YSIZE, h);
   ObjectSetString(0, name, OBJPROP_TEXT, text);
   ObjectSetInteger(0, name, OBJPROP_BGCOLOR, bg_col);
   ObjectSetInteger(0, name, OBJPROP_COLOR, text_col);
   ObjectSetInteger(0, name, OBJPROP_FONTSIZE, font_size);
   ObjectSetString(0, name, OBJPROP_FONT, font_name);
   ObjectSetInteger(0, name, OBJPROP_STATE, false);
}

//+------------------------------------------------------------------+
//| Helper: Convert Strategy Enum to Clean Name                      |
//+------------------------------------------------------------------+
string StrategyToString(ENUM_STRATEGY_MODE mode)
{
   switch(mode)
   {
      case STRAT_S1_VOL_SQUEEZE_BREAKOUT:  return "S1: Squeeze Breakout";
      case STRAT_S2_MOMENTUM_CONTINUATION: return "S2: Momentum Follow";
      case STRAT_S3_OU_MEAN_REVERSION:     return "S3: Mean-Reversion";
   }
   return "UNKNOWN";
}

//+------------------------------------------------------------------+
//| Dedicated Market Telemetry Engine (BUG N°1 Correctif)            |
//| Computes real-time metrics at boot and while trades are active.  |
//+------------------------------------------------------------------+
bool UpdateMarketTelemetry()
{
   int needed_closes = InpQuantileWindow + InpVolLookback + 2;
   double closes[];
   ArraySetAsSeries(closes, true);
   int copied = CopyClose(_Symbol, ExtEffTimeframe, 1, needed_closes, closes);
   if(copied < needed_closes)
      return false;

   double r_bps[];
   ArrayResize(r_bps, InpQuantileWindow + InpVolLookback);
   for(int k = 0; k < InpQuantileWindow + InpVolLookback; k++)
      r_bps[k] = (closes[k] - closes[k+1]) / closes[k+1] * 10000.0;

   double rolling_std[];
   ArrayResize(rolling_std, InpQuantileWindow);
   for(int m = 0; m < InpQuantileWindow; m++)
   {
      double sum = 0.0;
      for(int j = 0; j < InpVolLookback; j++)
         sum += r_bps[m + j];
      double mean = sum / InpVolLookback;
      double sum_sq = 0.0;
      for(int j = 0; j < InpVolLookback; j++)
      {
         double diff = r_bps[m + j] - mean;
         sum_sq += diff * diff;
      }
      rolling_std[m] = MathSqrt(sum_sq / (InpVolLookback - 1));
   }

   double current_std20 = rolling_std[0];
   // BUG N°2 & BUG SUBTIL A FIX (v3.51): pre_breakout_std20 uses rolling_std[1] (volatility of 20 bars prior to breakout bar)
   double pre_breakout_std20 = (ArraySize(rolling_std) > 1) ? rolling_std[1] : rolling_std[0];

   // Quantile calculated strictly over pre-breakout history (excluding rolling_std[0] contaminated by breakout bar)
   int q_count = (InpQuantileWindow > 1) ? (InpQuantileWindow - 1) : 1;
   double sorted_std[];
   ArrayResize(sorted_std, q_count);
   for(int i = 0; i < q_count; i++)
      sorted_std[i] = rolling_std[i + 1];
   ArraySort(sorted_std);
   int q_index = (int)MathFloor(ExtEffSqueezeQ * (q_count - 1));
   if(q_index < 0) q_index = 0;
   if(q_index >= q_count) q_index = q_count - 1;
   double squeeze_threshold = sorted_std[q_index];

   double safe_std = (pre_breakout_std20 > 1e-9) ? pre_breakout_std20 : ((current_std20 > 1e-9) ? current_std20 : 1e-9);
   double breakout_z = MathAbs(r_bps[0]) / safe_std;

   // Momentum Z-Score calculation over InpVolLookback (20)
   double mom_sum = 0.0;
   for(int k = 0; k < InpVolLookback; k++)
      mom_sum += r_bps[k];
   double denom = safe_std * MathSqrt((double)InpVolLookback);
   double mom_z = (denom > 1e-9) ? (mom_sum / denom) : 0.0;

   // Microstructure Real Live Spread Filter & ATR
   ExtSymbol.Refresh();
   ExtSymbol.RefreshRates();
   MqlTick live_tick;
   bool has_tick = SymbolInfoTick(_Symbol, live_tick);
   double ask = has_tick ? live_tick.ask : ExtSymbol.Ask();
   double bid = has_tick ? live_tick.bid : ExtSymbol.Bid();
   double mid_price = (ask + bid) / 2.0;
   if(mid_price <= 0.0 && ArraySize(closes) > 0) mid_price = closes[0];
   double pt = (_Point > 0.0) ? _Point : 0.01;
   double spread_pts = (ask > bid && pt > 0.0) ? ((ask - bid) / pt) : (double)SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
   double spread_bps = (mid_price > 0.0) ? ((spread_pts * pt / mid_price) * 10000.0) : 0.0;

   double atr_vals[];
   ArraySetAsSeries(atr_vals, true);
   double atr_val = 0.0;
   if(CopyBuffer(ExtATRHandle, 0, 1, 1, atr_vals) > 0)
      atr_val = atr_vals[0];
   else if(mid_price > 0.0)
      atr_val = mid_price * 0.005;

   ExtLastRetBps    = r_bps[0];           // v3.52: Vrai rendement signé de la bougie de cassure (Close[1] - Close[2])
   ExtLastStd20     = pre_breakout_std20; // v3.51 Surgical Patch: Evaluates true pre-breakout volatility!
   ExtLastSqueezeQ  = squeeze_threshold;
   ExtLastBreakoutZ = breakout_z;
   ExtLastMomZ      = mom_z;
   ExtLastSpreadBps = spread_bps;
   ExtLastATR       = atr_val;

   return true;
}

//+------------------------------------------------------------------+
//| Render Real-Time Graphical Dashboard on Chart (v3.52 Retractable)|
//+------------------------------------------------------------------+
void RenderVolSqueezeDashboard()
{
   bool term_ok = (bool)TerminalInfoInteger(TERMINAL_TRADE_ALLOWED);
   bool mql_ok  = (bool)MQLInfoInteger(MQL_TRADE_ALLOWED);

   // Active position lookup on current symbol
   bool has_pos = false;
   string pos_dir = "";
   double pos_vol = 0.0;
   double pos_pnl = 0.0;
   int pos_bars = 0;
   string pos_lock_str = "ATTENTE";

   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(!ExtPosition.SelectByIndex(i)) continue;
      if(ExtPosition.Symbol() != _Symbol) continue;

      ulong magic = ExtPosition.Magic();
      bool magic_matches = (magic == ExtEffMagic || magic == InpMagicNumber || magic == 20261021 || magic == 20261022);
      if(!magic_matches) continue;

      has_pos = true;
      pos_dir = (ExtPosition.PositionType() == POSITION_TYPE_BUY) ? "BUY" : "SELL";
      pos_vol = ExtPosition.Volume();
      pos_pnl = ExtPosition.Profit();
      datetime pos_time = (datetime)ExtPosition.Time();
      pos_bars = iBarShift(_Symbol, ExtEffTimeframe, pos_time, false);

      // BUG SUBTIL B FIX (v3.51): Accurately detect if SL has been trailed past entry price
      double cur_sl = ExtPosition.StopLoss();
      double open_px = ExtPosition.PriceOpen();
      bool is_profit_locked = false;
      if(ExtPosition.PositionType() == POSITION_TYPE_BUY)
         is_profit_locked = (cur_sl > open_px);
      else
         is_profit_locked = (cur_sl > 0.0 && cur_sl < open_px);

      pos_lock_str = is_profit_locked ? "VERROUILLÉ (+0.20 ATR)" : "ARMÉ (Seuil +1.20 ATR)";
      break;
   }

   int panel_x = 12;
   int panel_y = 26;
   int panel_w = 440;

   // 1. Minimized Mode (Height 32 px)
   if(ExtDashboardMinimized)
   {
      CreateRect(UI_PREFIX + "BG", panel_x, panel_y, panel_w, 32, C'15,23,42', C'56,189,248');
      CreateButton(UI_PREFIX + "BTN_MINIMIZE", panel_x + panel_w - 102, panel_y + 5, 96, 22,
                   "[ + AGRANDIR ]", C'51,65,85', clrWhite, 8);

      bool sqz_now = (ExtLastStd20 > 0.0 && ExtLastStd20 <= ExtLastSqueezeQ);
      string min_sum = StringFormat("⚡ QP v3.52 [%s] | Sqz:%s | Z:%.2f | PnL: %+.2f USD",
                                    ExtEffRole, (sqz_now ? "OUI" : "NON"), ExtLastBreakoutZ, pos_pnl);
      CreateLabel(UI_PREFIX + "LBL_MIN_SUM", panel_x + 10, panel_y + 8, min_sum, clrSkyBlue, 8, "Consolas");

      // Delete detailed labels if present
      for(int k = 1; k <= 10; k++)
         ObjectDelete(0, UI_PREFIX + "LBL_SEC_" + IntegerToString(k));
      ObjectDelete(0, UI_PREFIX + "HDR");
      ObjectDelete(0, UI_PREFIX + "LBL_HDR");
      ObjectDelete(0, UI_PREFIX + "SEP_1");
      ObjectDelete(0, UI_PREFIX + "SEP_2");
      ObjectDelete(0, UI_PREFIX + "SEP_3");

      ChartRedraw(0);
      return;
   }

   // 2. Expanded Mode (Height 285 px)
   ObjectDelete(0, UI_PREFIX + "LBL_MIN_SUM");

   CreateRect(UI_PREFIX + "BG", panel_x, panel_y, panel_w, 285, C'15,23,42', C'56,189,248');
   CreateRect(UI_PREFIX + "HDR", panel_x, panel_y, panel_w, 28, C'30,41,59', clrNONE);

   string hdr_text = StringFormat("⚡ QUANT-POD v3.52 ELITE — [%s]", ExtEffRole);
   CreateLabel(UI_PREFIX + "LBL_HDR", panel_x + 10, panel_y + 6, hdr_text, clrGold, 9, "Consolas");

   CreateButton(UI_PREFIX + "BTN_MINIMIZE", panel_x + panel_w - 102, panel_y + 3, 96, 22,
                "[ — RÉDUIRE ]", C'51,65,85', clrWhite, 8);

   // Fine horizontal dividers
   CreateRect(UI_PREFIX + "SEP_1", panel_x + 8, panel_y + 102, panel_w - 16, 1, C'51,65,85');
   CreateRect(UI_PREFIX + "SEP_2", panel_x + 8, panel_y + 182, panel_w - 16, 1, C'51,65,85');

   // Section 1: Identité & Statut
   string status_str = "BLOQUÉ (Algo OFF)";
   color status_col = clrTomato;
   if(ExtIsSymbolPaused)
   {
      status_str = "PAUSE PROTECTION (Hors Panier)";
      status_col = clrOrange;
   }
   else if(term_ok && mql_ok)
   {
      status_str = "ACTIF & OPÉRATIONNEL";
      status_col = clrSpringGreen;
   }

   string l1 = StringFormat("Actif & Unité  : %s | TF: %s | Horizon: %d barres",
                            _Symbol, EnumToString(ExtEffTimeframe), ExtEffMaxHoldBars);
   CreateLabel(UI_PREFIX + "LBL_SEC_1", panel_x + 10, panel_y + 36, l1, clrWhite, 8);

   string l2 = StringFormat("Statut & Mode  : %s | Strat: %s",
                            status_str, StrategyToString(ExtEffStrategyMode));
   CreateLabel(UI_PREFIX + "LBL_SEC_2", panel_x + 10, panel_y + 54, l2, status_col, 8);

   string dir_str = (InpDirectionMode == DIR_BOTH) ? "BOTH" : (InpDirectionMode == DIR_LONG_ONLY ? "LONG_ONLY" : "SHORT_ONLY");
   string l3 = StringFormat("Magic & Filtres: Magic=%I64u | Dir=%s | Slippage=%d pts",
                            ExtEffMagic, dir_str, ExtEffSlippage);
   CreateLabel(UI_PREFIX + "LBL_SEC_3", panel_x + 10, panel_y + 72, l3, clrLightSteelBlue, 8);

   // Section 2: Radar Mathématique Temps Réel
   bool sqz_active = (ExtLastStd20 > 0.0 && ExtLastStd20 <= ExtLastSqueezeQ);
   string sqz_badge = sqz_active ? "[ SQUEEZE ACTIF ! ]" : "[ VOL NORMALE ]";
   color sqz_col = sqz_active ? clrAqua : clrSilver;
   string l4 = StringFormat("Compression S1 : std20 = %.2f bps vs Q%.0f = %.2f bps -> %s",
                            ExtLastStd20, ExtEffSqueezeQ * 100.0, ExtLastSqueezeQ, sqz_badge);
   CreateLabel(UI_PREFIX + "LBL_SEC_4", panel_x + 10, panel_y + 112, l4, sqz_col, 8);

   bool brk_active = (ExtLastBreakoutZ >= ExtEffBreakoutZ);
   string l5 = StringFormat("Signal Cassure : Impulse Z = %.2f (Seuil %.2f) | Mom20 Z = %+.2f",
                            ExtLastBreakoutZ, ExtEffBreakoutZ, ExtLastMomZ);
   CreateLabel(UI_PREFIX + "LBL_SEC_5", panel_x + 10, panel_y + 132, l5, (brk_active ? clrSpringGreen : clrWhite), 8);

   double pt = (_Point > 0.0) ? _Point : 0.01;
   double atr_pts = (pt > 0.0 && ExtLastATR > 0.0) ? (ExtLastATR / pt) : 100.0;
   double spread_pts = (ExtLastSpreadBps * (_Symbol != "" ? SymbolInfoDouble(_Symbol, SYMBOL_BID) : 1.0) / 10000.0) / pt;
   double spread_to_atr = (atr_pts > 0.0) ? (spread_pts / atr_pts) : 0.0;
   bool spread_ok = (ExtLastSpreadBps <= InpMaxSpreadBps && spread_to_atr <= InpMaxSpreadToATR);
   string l6 = StringFormat("Microstructure : Spread = %.2f bps / %.2f bps (%.1f%% ATR)",
                            ExtLastSpreadBps, InpMaxSpreadBps, spread_to_atr * 100.0);
   CreateLabel(UI_PREFIX + "LBL_SEC_6", panel_x + 10, panel_y + 152, l6, (spread_ok ? clrSpringGreen : clrTomato), 8);

   // Section 3: Position en Direct & Sécurités Serveur
   if(has_pos)
   {
      string l7 = StringFormat("POSITION ACTIVE: %s %.3f lot | Barres: %d/%d | Lock: %s | PnL: %+.2f USD",
                               pos_dir, pos_vol, pos_bars, ExtEffMaxHoldBars, pos_lock_str, pos_pnl);
      CreateLabel(UI_PREFIX + "LBL_SEC_7", panel_x + 10, panel_y + 192, l7, (pos_pnl >= 0.0 ? clrGold : clrCoral), 8);
   }
   else
   {
      string l7 = StringFormat("Position Active: AUCUNE (Scan en cours) | Signaux=%I64d | Trades=%I64d",
                               ExtTotalSignals, ExtTotalTrades);
      CreateLabel(UI_PREFIX + "LBL_SEC_7", panel_x + 10, panel_y + 192, l7, clrSilver, 8);
   }

   string l8 = StringFormat("Gardes Risque  : HardSL=%.1f ATR | Lock=+%.1f->+%.1f ATR | LotMax=%.3f",
                            InpHardSL_ATR, InpLockTriggerATR, InpLockOffsetATR, ExtEffLotCap);
   CreateLabel(UI_PREFIX + "LBL_SEC_8", panel_x + 10, panel_y + 212, l8, clrLightSteelBlue, 8);

   string l9 = StringFormat("Sécurités      : ColdBoot=%ds max delay | Risque=%.2f%% par 1-SD",
                            InpMaxEntryDelaySec, InpRiskPerSDPct);
   CreateLabel(UI_PREFIX + "LBL_SEC_9", panel_x + 10, panel_y + 232, l9, clrSkyBlue, 8);

   string onnx_status = (ExtEffUseONNX && ExtModelLoaded) ? "ONNX ACTIVE" : "PURE_S1_S2_S3";
   string l10 = StringFormat("Serveur & Mode : Deriv-Demo | Mode %s | Telemetry Live 0.00bps FIX", onnx_status);
   CreateLabel(UI_PREFIX + "LBL_SEC_10", panel_x + 10, panel_y + 252, l10, clrDarkGray, 8);

   ChartRedraw(0);
}

//+------------------------------------------------------------------+
//| Chart Event Handler: Interactive Retractable Dashboard           |
//+------------------------------------------------------------------+
void OnChartEvent(const int id, const long &lparam, const double &dparam, const string &sparam)
{
   if(id == CHARTEVENT_OBJECT_CLICK && sparam == UI_PREFIX + "BTN_MINIMIZE")
   {
      ExtDashboardMinimized = !ExtDashboardMinimized;
      ObjectSetInteger(0, UI_PREFIX + "BTN_MINIMIZE", OBJPROP_STATE, false);
      RenderVolSqueezeDashboard();
      ChartRedraw(0);
   }
}

//+------------------------------------------------------------------+
//| Expert Initialization Function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
   Comment(""); // Clear ASCII comment overlay permanently

   if(!ExtSymbol.Name(_Symbol))
   {
      PrintFormat("[v3.52 ERROR] Symbol %s could not be initialized.", _Symbol);
      return INIT_FAILED;
   }
   ExtSymbol.Refresh();
   ExtSymbol.RefreshRates();

   SyncEffectiveParameters();

   ExtTrade.SetExpertMagicNumber(ExtEffMagic);
   ExtTrade.SetDeviationInPoints(ExtEffSlippage);

   // Dynamic Filling Mode Adaptation
   uint filling = (uint)SymbolInfoInteger(_Symbol, SYMBOL_FILLING_MODE);
   if((filling & SYMBOL_FILLING_IOC) != 0)
      ExtTrade.SetTypeFilling(ORDER_FILLING_IOC);
   else if((filling & SYMBOL_FILLING_FOK) != 0)
      ExtTrade.SetTypeFilling(ORDER_FILLING_FOK);
   else
      ExtTrade.SetTypeFilling(ORDER_FILLING_RETURN);

   // Initialize ATR Indicator on Effective Timeframe
   ExtATRHandle = iATR(_Symbol, ExtEffTimeframe, InpATRPeriod);
   if(ExtATRHandle == INVALID_HANDLE)
   {
      PrintFormat("[v3.52 ERROR] Failed to create ATR(%d) handle on %s. Error = %d", InpATRPeriod, EnumToString(ExtEffTimeframe), GetLastError());
      return INIT_FAILED;
   }

   // Cold-Boot Freshness Guard: Initialize LastBarTime to CURRENT forming bar
   ExtLastBarTime = iTime(_Symbol, ExtEffTimeframe, 0);

   // Initialize C2 ONNX Model only if effectively enabled
   ExtEffMinProb = GetNormalizedMinWinProb();
   ExtActiveModelFile = InpONNXModelName;
   ExtModelLoaded = false;
   if(ExtEffUseONNX)
   {
      string preferred_model = InpONNXModelName;
      if(preferred_model == "c2_vol_filter.onnx" || preferred_model == "AUTO" || preferred_model == "")
      {
         if(StringFind(_Symbol, "25 (1s)") >= 0)
            preferred_model = "c2_vol_filter_v25.onnx";
         else if(StringFind(_Symbol, "75 (1s)") >= 0)
            preferred_model = "c2_vol_filter_v75.onnx";
      }

      ExtOnnxHandle = OnnxCreate(preferred_model, ONNX_DEFAULT);
      if(ExtOnnxHandle == INVALID_HANDLE && preferred_model != InpONNXModelName)
      {
         ExtOnnxHandle = OnnxCreate(InpONNXModelName, ONNX_DEFAULT);
         if(ExtOnnxHandle != INVALID_HANDLE)
            preferred_model = InpONNXModelName;
      }

      if(ExtOnnxHandle != INVALID_HANDLE)
      {
         const long in_shape[] = {1, 7};
         const long out_shape_0[] = {1};
         const long out_shape_1[] = {1, 2};
         OnnxSetInputShape(ExtOnnxHandle, 0, in_shape);
         OnnxSetOutputShape(ExtOnnxHandle, 0, out_shape_0);
         OnnxSetOutputShape(ExtOnnxHandle, 1, out_shape_1);
         ExtModelLoaded = true;
         ExtActiveModelFile = preferred_model;
         PrintFormat("[v3.52 ONNX] Model '%s' loaded (P_min=%.1f%%).", ExtActiveModelFile, ExtEffMinProb * 100.0);
      }
   }

   ExtDayStartEq = AccountInfoDouble(ACCOUNT_EQUITY);
   ExtCurrentDay = iTime(_Symbol, PERIOD_D1, 0);

   // BUG N°1 FIX: Run Telemetry and Render Dashboard IMMEDIATELY on boot (at millisecond 0)
   UpdateMarketTelemetry();
   RenderVolSqueezeDashboard();

   bool term_ok = (bool)TerminalInfoInteger(TERMINAL_TRADE_ALLOWED);
   bool mql_ok  = (bool)MQLInfoInteger(MQL_TRADE_ALLOWED);
   PrintFormat("[v3.52 INIT SUCCESS] %s | Role=%s | Status=%s | TF=%s | Strat=%s | Hold=%db | Magic=%I64u | SqueezeQ=%.2f | BreakoutZ=%.2f | HardSL=%s | LotCap=%.3f | ColdBootGuard=%ds | TradeAllowed=(Term:%s, MQL:%s)",
               _Symbol, ExtEffRole, ExtIsSymbolPaused ? "PAUSED_STANDBY" : "ACTIVE",
               EnumToString(ExtEffTimeframe), StrategyToString(ExtEffStrategyMode), ExtEffMaxHoldBars,
               ExtEffMagic, ExtEffSqueezeQ, ExtEffBreakoutZ,
               InpUseHardTPSL ? StringFormat("%.2f_ATR", InpHardSL_ATR) : "OFF",
               ExtEffLotCap, InpMaxEntryDelaySec,
               term_ok ? "YES" : "NO", mql_ok ? "YES" : "NO");

   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert Deinitialization Function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   if(ExtATRHandle != INVALID_HANDLE)
   {
      IndicatorRelease(ExtATRHandle);
      ExtATRHandle = INVALID_HANDLE;
   }
   if(ExtOnnxHandle != INVALID_HANDLE)
   {
      OnnxRelease(ExtOnnxHandle);
      ExtOnnxHandle = INVALID_HANDLE;
   }

   // Cleanup all MQL5 Dashboard Graphical Objects
   ObjectsDeleteAll(0, UI_PREFIX);
   Comment("");
   ChartRedraw(0);

   PrintFormat("[v3.52 DEINIT] Shutdown clean on %s. Reason = %d", _Symbol, reason);
}

//+------------------------------------------------------------------+
//| Calculate Skewness of array                                      |
//+------------------------------------------------------------------+
double CalcSkewness(const double &arr[], int n, double mean, double std)
{
   if(n < 3 || std <= 1e-8) return 0.0;
   double sum = 0.0;
   for(int i = 0; i < n; i++)
   {
      double diff = (arr[i] - mean) / std;
      sum += diff * diff * diff;
   }
   return sum / n;
}

//+------------------------------------------------------------------+
//| Calculate Pearson Kurtosis of array                              |
//+------------------------------------------------------------------+
double CalcKurtosis(const double &arr[], int n, double mean, double std)
{
   if(n < 4 || std <= 1e-8) return 0.0;
   double sum = 0.0;
   for(int i = 0; i < n; i++)
   {
      double diff = (arr[i] - mean) / std;
      sum += diff * diff * diff * diff;
   }
   return sum / n;
}

//+------------------------------------------------------------------+
//| Calculate Levy Area proxy on normalized price trajectory         |
//+------------------------------------------------------------------+
double CalcLevyArea(const double &p_norm[], int n)
{
   if(n < 2) return 0.0;
   double area = 0.0;
   double dt = 1.0 / (double)(n - 1);
   for(int k = 0; k < n - 1; k++)
   {
      double t_k = k * dt;
      double dp = p_norm[k+1] - p_norm[k];
      area += (t_k * dp - p_norm[k] * dt);
   }
   return area;
}

//+------------------------------------------------------------------+
//| Inference function for C2 ONNX Model                             |
//+------------------------------------------------------------------+
bool EvaluateONNXFilter(double vol_ratio, double impulse_z, double direction,
                        double levy_area, double spread_to_atr, double skew20, double kurt20,
                        double &out_prob)
{
   if(!ExtEffUseONNX || !ExtModelLoaded || ExtOnnxHandle == INVALID_HANDLE)
   {
      out_prob = 1.0;
      return true;
   }

   float in_features[7];
   in_features[0] = (float)vol_ratio;
   in_features[1] = (float)impulse_z;
   in_features[2] = (float)direction;
   in_features[3] = (float)levy_area;
   in_features[4] = (float)spread_to_atr;
   in_features[5] = (float)skew20;
   in_features[6] = (float)kurt20;

   long out_label[1];
   float out_probs[2];

   ResetLastError();
   if(!OnnxRun(ExtOnnxHandle, ONNX_NO_CONVERSION, in_features, out_label, out_probs))
   {
      PrintFormat("[v3.52 ONNX RUN ERROR] Code = %d. Rejecting trade on inference failure.", GetLastError());
      out_prob = 0.0;
      return false;
   }

   out_prob = (double)out_probs[1];
   ExtEffMinProb = GetNormalizedMinWinProb();
   return (out_prob >= ExtEffMinProb);
}

//+------------------------------------------------------------------+
//| Position Management & Strict Time-Stop Engine (v3.52)            |
//| Preserves and manages current, basket & legacy tickets           |
//+------------------------------------------------------------------+
bool ManageOpenPositions()
{
   ExtSymbol.RefreshRates();
   double pt = (_Point > 0.0) ? _Point : 0.01;
   long stops_pts  = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
   long freeze_pts = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_FREEZE_LEVEL);
   double freeze_dist = (double)freeze_pts * pt;
   double min_dist    = (double)MathMax(stops_pts, freeze_pts) * pt + pt;

   double atr_vals[];
   ArraySetAsSeries(atr_vals, true);
   double closed_atr = 0.0;
   if(CopyBuffer(ExtATRHandle, 0, 1, 1, atr_vals) > 0)
      closed_atr = atr_vals[0];

   static datetime s_last_modify_fail_time = 0;
   bool has_open_pos = false;

   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(!ExtPosition.SelectByIndex(i))
         continue;
      if(ExtPosition.Symbol() != _Symbol)
         continue;

      ulong pos_magic = ExtPosition.Magic();
      bool magic_matches = (pos_magic == ExtEffMagic || pos_magic == InpMagicNumber);
      // Legacy compatibility: manage any active trade on V25 opened under 20261021 or 20261022
      if(StringFind(_Symbol, "25 (1s)") >= 0 && (pos_magic == 20261021 || pos_magic == 20261022))
         magic_matches = true;

      if(!magic_matches)
         continue;

      ulong    ticket       = ExtPosition.Ticket();
      datetime open_time    = (datetime)ExtPosition.Time();
      int      bars_elapsed = iBarShift(_Symbol, ExtEffTimeframe, open_time, false);
      ENUM_POSITION_TYPE pos_type = ExtPosition.PositionType();
      MqlTick  live_tick;
      bool     got_tick     = SymbolInfoTick(_Symbol, live_tick);
      double   cur_bid      = got_tick ? live_tick.bid : ExtSymbol.Bid();
      double   cur_ask      = got_tick ? live_tick.ask : ExtSymbol.Ask();
      double   current_sl   = ExtPosition.StopLoss();
      double   current_tp   = ExtPosition.TakeProfit();

      //--- 1. Strict Time-Stop Exit Horizon FIRST
      if(bars_elapsed >= ExtEffMaxHoldBars)
      {
         double exit_price = (pos_type == POSITION_TYPE_BUY) ? cur_bid : cur_ask;
         bool frozen = false;
         if(freeze_dist > 0.0)
         {
            if(current_sl > 0.0 && MathAbs(exit_price - current_sl) <= freeze_dist) frozen = true;
            if(current_tp > 0.0 && MathAbs(current_tp - exit_price) <= freeze_dist) frozen = true;
         }

         if(!frozen && ExtTrade.PositionClose(ticket))
         {
            PrintFormat("[v3.52 TIME-STOP EXIT] %s Ticket #%I64u | Bars Held = %d/%d (%s) | Open=%s | Exit=%s | PnL=%.2f USD",
                        _Symbol, ticket, bars_elapsed, ExtEffMaxHoldBars, EnumToString(ExtEffTimeframe),
                        DoubleToString(ExtPosition.PriceOpen(), _Digits),
                        DoubleToString(exit_price, _Digits),
                        ExtPosition.Profit());
            continue;
         }
         else
         {
            has_open_pos = true;
            continue;
         }
      }

      has_open_pos = true;

      //--- 2. Dynamic Profit Excursion Lock (shift=1 ATR + NormalizePrice + Cooldown)
      if(InpUseTrailingLock && closed_atr > 0.0 && (TimeCurrent() - s_last_modify_fail_time) >= 10)
      {
         double open_price   = ExtPosition.PriceOpen();
         double lock_trigger = InpLockTriggerATR * closed_atr;
         double lock_offset  = InpLockOffsetATR * closed_atr;

         if(pos_type == POSITION_TYPE_BUY && cur_bid > 0.0)
         {
            double mfe = cur_bid - open_price;
            double target_sl = NormalizePrice(open_price + lock_offset);
            bool sl_improves = (current_sl <= 0.0) || ((target_sl - current_sl) > 0.5 * pt);
            bool stops_ok    = ((cur_bid - target_sl) >= min_dist) &&
                               (current_sl <= 0.0 || MathAbs(cur_bid - current_sl) > freeze_dist) &&
                               (current_tp <= 0.0 || (current_tp - cur_bid) >= min_dist);

            if(mfe >= lock_trigger && sl_improves && stops_ok)
            {
               if(ExtTrade.PositionModify(ticket, target_sl, current_tp))
               {
                  PrintFormat("[v3.52 PROFIT LOCK] %s Ticket #%I64u BUY | SL locked at %s (+%.2f ATR)",
                              _Symbol, ticket, DoubleToString(target_sl, _Digits), InpLockOffsetATR);
               }
               else
               {
                  s_last_modify_fail_time = TimeCurrent();
               }
            }
         }
         else if(pos_type == POSITION_TYPE_SELL && cur_ask > 0.0)
         {
            double mfe = open_price - cur_ask;
            double target_sl = NormalizePrice(open_price - lock_offset);
            bool sl_improves = (current_sl <= 0.0) || ((current_sl - target_sl) > 0.5 * pt);
            bool stops_ok    = ((target_sl - cur_ask) >= min_dist) &&
                               (current_sl <= 0.0 || MathAbs(current_sl - cur_ask) > freeze_dist) &&
                               (current_tp <= 0.0 || (cur_ask - current_tp) >= min_dist);

            if(mfe >= lock_trigger && sl_improves && stops_ok)
            {
               if(ExtTrade.PositionModify(ticket, target_sl, current_tp))
               {
                  PrintFormat("[v3.52 PROFIT LOCK] %s Ticket #%I64u SELL | SL locked at %s (+%.2f ATR)",
                              _Symbol, ticket, DoubleToString(target_sl, _Digits), InpLockOffsetATR);
               }
               else
               {
                  s_last_modify_fail_time = TimeCurrent();
               }
            }
         }
      }
   }
   return has_open_pos;
}

//+------------------------------------------------------------------+
//| Dynamic Volatility-Parity Position Sizing Engine                 |
//| BUG N°3 FIX: Free Margin verification with OrderCalcMargin       |
//+------------------------------------------------------------------+
double CalculateVolParityLot(double std20_bps, double current_price)
{
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   double risk_cash = equity * (InpRiskPerSDPct / 100.0);

   double horizon_sqrt = MathSqrt((double)MathMax(1, ExtEffMaxHoldBars));
   double horizon_sd_pts = (std20_bps / 10000.0) * current_price * horizon_sqrt;
   if(horizon_sd_pts <= 0.0) horizon_sd_pts = current_price * 0.001;

   double tick_size  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   double tick_value = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   if(tick_size <= 0.0) tick_size = _Point;
   if(tick_value <= 0.0) tick_value = 1.0;

   double dollar_loss_per_lot = (horizon_sd_pts / tick_size) * tick_value;
   if(dollar_loss_per_lot <= 0.0) return SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);

   double raw_lot = risk_cash / dollar_loss_per_lot;
   double min_lot  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double max_lot  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double lot_step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);

   double rounded_lot = MathFloor((raw_lot / lot_step) + 1e-8) * lot_step;
   if(rounded_lot < min_lot) rounded_lot = min_lot;
   if(rounded_lot > max_lot) rounded_lot = max_lot;

   // Enforce strict asset-specific lot cap
   if(ExtEffLotCap > 0.0 && rounded_lot > ExtEffLotCap)
      rounded_lot = ExtEffLotCap;

   // BUG N°3 FIX: Margin check via OrderCalcMargin (capping if margin_required > 25% free margin)
   double margin_required = 0.0;
   if(OrderCalcMargin(ORDER_TYPE_BUY, _Symbol, rounded_lot, current_price, margin_required))
   {
      double free_margin = AccountInfoDouble(ACCOUNT_MARGIN_FREE);
      double max_margin_allowed = free_margin * 0.25;
      if(margin_required > max_margin_allowed && margin_required > 0.0)
      {
         double factor = max_margin_allowed / margin_required;
         rounded_lot = MathFloor((rounded_lot * factor / lot_step) + 1e-8) * lot_step;
         if(rounded_lot < min_lot) rounded_lot = min_lot;
      }
   }

   return rounded_lot;
}

//+------------------------------------------------------------------+
//| Expert Tick Function                                             |
//| Enforces Correct Lifecycle: Telemetry -> Position -> Breaker     |
//+------------------------------------------------------------------+
void OnTick()
{
   SyncEffectiveParameters();
   datetime bar_time = iTime(_Symbol, ExtEffTimeframe, 0);

   //--- 1. Manage Existing Open Positions at EVERY TICK
   bool is_positioned = ManageOpenPositions();

   //--- 2. BUG N°1 FIX: Throttled Telemetry & Dashboard Refresh (Every 500 ms)
   // Called BEFORE bar_time and is_positioned returns so telemetry refreshes continuously!
   static ulong s_last_telemetry_tick = 0;
   ulong current_tick = GetTickCount64();
   if(current_tick - s_last_telemetry_tick >= 500)
   {
      UpdateMarketTelemetry();
      RenderVolSqueezeDashboard();
      s_last_telemetry_tick = current_tick;
   }

   //--- 3. Daily Drawdown Circuit Breaker
   datetime today = iTime(_Symbol, PERIOD_D1, 0);
   if(today != ExtCurrentDay && today != 0)
   {
      ExtCurrentDay = today;
      ExtDayStartEq = AccountInfoDouble(ACCOUNT_EQUITY);
   }

   double current_eq = AccountInfoDouble(ACCOUNT_EQUITY);
   if(ExtDayStartEq > 0.0 && ((ExtDayStartEq - current_eq) / ExtDayStartEq) * 100.0 >= InpMaxDailyLossPct)
      return;

   //--- 4. Bar Lifecycle Guards for NEW Entries
   if(bar_time == ExtLastBarTime || bar_time == 0)
      return;

   // Cold-Boot Freshness Guard (300 sec max delay)
   if(TimeCurrent() - bar_time > InpMaxEntryDelaySec)
   {
      PrintFormat("[v3.52 COLD-BOOT GUARD] %s bar_time=%s is %d sec old (> %d sec max delay). Waiting for next fresh bar close.",
                  _Symbol, TimeToString(bar_time, TIME_DATE|TIME_SECONDS),
                  (int)(TimeCurrent() - bar_time), InpMaxEntryDelaySec);
      ExtLastBarTime = bar_time;
      return;
   }

   if(is_positioned)
   {
      ExtLastBarTime = bar_time;
      return;
   }

   if(ExtIsSymbolPaused)
   {
      ExtLastBarTime = bar_time;
      return;
   }

   // Ensure Fresh Indicator Telemetry on Bar Close
   if(!UpdateMarketTelemetry())
   {
      ExtLastBarTime = bar_time;
      return;
   }

   //--- 5. Evaluate Multi-Engine Strategy Signals (S1 / S2 / S3)
   bool is_signal = false;
   double direction = 0.0;

   // v3.52 CRITICAL FIX: Use true signed breakout return from UpdateMarketTelemetry() (No inverted AsSeries bug)
   double r_bps_last = ExtLastRetBps;

   if(ExtEffStrategyMode == STRAT_S1_VOL_SQUEEZE_BREAKOUT)
   {
      // S1: Squeeze Breakout (uses pre_breakout_std20 at shift=1)
      bool is_squeezed = (ExtLastStd20 <= ExtLastSqueezeQ);
      bool is_breakout = (ExtLastBreakoutZ >= ExtEffBreakoutZ);
      if(is_squeezed && is_breakout)
      {
         is_signal = true;
         direction = (r_bps_last > 0.0) ? 1.0 : -1.0;
      }
   }
   else if(ExtEffStrategyMode == STRAT_S2_MOMENTUM_CONTINUATION)
   {
      // S2: Trend & Momentum Continuation
      if(MathAbs(ExtLastMomZ) >= ExtEffBreakoutZ)
      {
         is_signal = true;
         direction = (ExtLastMomZ > 0.0) ? 1.0 : -1.0;
      }
   }
   else if(ExtEffStrategyMode == STRAT_S3_OU_MEAN_REVERSION)
   {
      // S3: Ornstein-Uhlenbeck Mean-Reversion (Contrarian)
      if(MathAbs(ExtLastMomZ) >= ExtEffBreakoutZ)
      {
         is_signal = true;
         direction = (ExtLastMomZ > 0.0) ? -1.0 : 1.0; // Contrarian direction!
      }
   }

   if(!is_signal || direction == 0.0)
   {
      ExtLastBarTime = bar_time;
      return;
   }

   //--- 6. BUG N°4 FIX: Direction Mode Filter (Asymmetric Swaps Protection)
   if(direction > 0.0 && InpDirectionMode == DIR_SHORT_ONLY)
   {
      PrintFormat("[v3.52 DIRECTION BLOCKED] %s BUY signal rejected (InpDirectionMode == DIR_SHORT_ONLY).", _Symbol);
      ExtLastBarTime = bar_time;
      return;
   }
   if(direction < 0.0 && InpDirectionMode == DIR_LONG_ONLY)
   {
      PrintFormat("[v3.52 DIRECTION BLOCKED] %s SELL signal rejected (InpDirectionMode == DIR_LONG_ONLY).", _Symbol);
      ExtLastBarTime = bar_time;
      return;
   }

   ExtTotalSignals++;

   // Microstructure Real Spread Filter
   ExtSymbol.Refresh();
   ExtSymbol.RefreshRates();
   MqlTick live_tick;
   bool has_tick = SymbolInfoTick(_Symbol, live_tick);
   double ask = has_tick ? live_tick.ask : ExtSymbol.Ask();
   double bid = has_tick ? live_tick.bid : ExtSymbol.Bid();
   double mid_price = (ask + bid) / 2.0;
   double pt = (_Point > 0.0) ? _Point : 0.01;
   double spread_pts = (ask > bid && pt > 0.0) ? ((ask - bid) / pt) : (double)SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
   double atr_pts = (pt > 0.0 && ExtLastATR > 0.0) ? (ExtLastATR / pt) : 100.0;
   double spread_to_atr = (atr_pts > 0.0) ? (spread_pts / (atr_pts + 1e-8)) : 1.0;

   if(spread_to_atr > InpMaxSpreadToATR || ExtLastSpreadBps > InpMaxSpreadBps)
   {
      PrintFormat("[v3.52 SPREAD REJECT] %s Spread=%.2f bps (%.1f%% of ATR) exceeds threshold (%.2f bps / %.1f%% ATR)",
                  _Symbol, ExtLastSpreadBps, spread_to_atr * 100.0, InpMaxSpreadBps, InpMaxSpreadToATR * 100.0);
      ExtLastBarTime = bar_time;
      return;
   }

   // Optional ONNX Filter (if effectively enabled)
   if(ExtEffUseONNX && ExtModelLoaded)
   {
      double out_prob = 1.0;
      double vol_ratio = (ExtLastSqueezeQ > 0.0) ? (ExtLastStd20 / ExtLastSqueezeQ) : 1.0;
      bool pass_onnx = EvaluateONNXFilter(vol_ratio, ExtLastBreakoutZ, direction,
                                          0.0, spread_to_atr, 0.0, 0.0, out_prob);
      if(!pass_onnx)
      {
         PrintFormat("[v3.52 ONNX REJECT] %s Signal rejected by ML (P=%.1f%% < %.1f%%)",
                     _Symbol, out_prob * 100.0, ExtEffMinProb * 100.0);
         ExtLastBarTime = bar_time;
         return;
      }
   }

   //--- 7. Execute Order with Dynamic Vol-Parity Sizing & Hard Normalized SL/TP
   ExtTrade.SetExpertMagicNumber(ExtEffMagic);
   ExtTrade.SetDeviationInPoints(ExtEffSlippage);
   double lot = CalculateVolParityLot(ExtLastStd20, mid_price);

   double sl = 0.0;
   double tp = 0.0;
   if(InpUseHardTPSL && ExtLastATR > 0.0)
   {
      long stops_level = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
      long freeze_level = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_FREEZE_LEVEL);
      double min_dist = (double)MathMax(stops_level, freeze_level) * pt + pt;

      if(direction > 0.0)
      {
         if(InpHardSL_ATR > 0.0) sl = NormalizePrice(MathMin(ask - (InpHardSL_ATR * ExtLastATR), bid - min_dist));
         if(InpHardTP_ATR > 0.0) tp = NormalizePrice(MathMax(ask + (InpHardTP_ATR * ExtLastATR), ask + min_dist));
      }
      else
      {
         if(InpHardSL_ATR > 0.0) sl = NormalizePrice(MathMax(bid + (InpHardSL_ATR * ExtLastATR), ask + min_dist));
         if(InpHardTP_ATR > 0.0) tp = NormalizePrice(MathMin(bid - (InpHardTP_ATR * ExtLastATR), bid - min_dist));
      }
   }

   string comment = StringFormat("v350_%s_%s", ExtEffRole, (direction > 0.0 ? "BUY" : "SEL"));

   bool success = false;
   if(direction > 0.0)
      success = ExtTrade.Buy(lot, _Symbol, ask, sl, tp, comment);
   else
      success = ExtTrade.Sell(lot, _Symbol, bid, sl, tp, comment);

   if(success)
   {
      ExtTotalTrades++;
      RenderVolSqueezeDashboard();
      PrintFormat("[v3.52 ENTRY EXECUTED] %s %s %.3f lots (%s) | Strat=%s | std20=%.2f bps | Z=%.2f | MomZ=%+.2f | SL=%s | TP=%s | Ticket=#%I64u",
                  (direction > 0.0 ? "BUY" : "SELL"), _Symbol, lot, ExtEffRole,
                  StrategyToString(ExtEffStrategyMode), ExtLastStd20, ExtLastBreakoutZ, ExtLastMomZ,
                  DoubleToString(sl, _Digits), DoubleToString(tp, _Digits),
                  ExtTrade.ResultOrder());
   }
   else
   {
      PrintFormat("[v3.52 EXECUTION FAILED] %s | Error = %d | Retcode = %u", _Symbol, GetLastError(), ExtTrade.ResultRetcode());
   }

   ExtLastBarTime = bar_time;
}
//+------------------------------------------------------------------+
