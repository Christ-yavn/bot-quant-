//+------------------------------------------------------------------+
//|                          Deriv_VolSqueeze_Breakout_EA_v3.mq5      |
//|   PH2-C1 Sentinel-validated production build (Gate 4 -> Gate 5)   |
//|   C1 PASS : Volatility 25 (1s) Index, H1, q=0.30, z=1.25, hold=4  |
//|   C1 FAIL : Volatility 75 (1s) Index  -> blocked by symbol guard  |
//|   C2 gate : ONNX filter AUC 0.554 (UNVALIDATED) -> OFF by default |
//+------------------------------------------------------------------+
#property copyright "Quantitative Research & Algorithmic Systems"
#property version   "3.00"
#property strict

#include <Trade\Trade.mqh>
#include <Trade\PositionInfo.mqh>
#include <Trade\SymbolInfo.mqh>

//--- Input Parameters: Signal & Regime Mechanics (C1-validated defaults)
input group "=== 1. Volatility Squeeze & Impulse Breakout (C1-validated) ==="
input ENUM_TIMEFRAMES InpTimeframe          = PERIOD_H1;  // Execution Timeframe (validated H1)
input int             InpVolLookback        = 20;         // Rolling Volatility Window
input int             InpQuantileWindow     = 100;        // Squeeze Percentile Lookback
input double          InpSqueezeQuantile    = 0.30;       // C1 robust grid cell (t=+3.29)
input double          InpBreakoutZScore     = 1.25;       // C1 robust grid cell (t=+3.29)
input int             InpMaxHoldBars        = 4;          // Non-Overlapping Time-Stop (4h)

input group "=== 2. Excursion Guardrails & Spread Circuit Breaker ==="
input bool            InpUseHardTPSL        = false;       // Hard ATR Stops (default: pure 4h time-stop)
input int             InpATRPeriod          = 20;
input double          InpHardSL_ATR         = 2.00;
input double          InpHardTP_ATR         = 3.50;
input double          InpMaxSpreadToATR     = 0.050;       // Max Spread/H1-ATR ratio (5.0%)
input double          InpMaxSpreadBps       = 4.50;        // Max spread in bps

input group "=== 3. Risk Management & Volatility-Parity Sizing ==="
input double          InpRiskPerSDPct       = 0.50;        // Equity risk (%) per 1-SD 4h move
input double          InpMaxDailyLossPct    = 3.00;        // Daily drawdown circuit breaker
input ulong           InpMagicNumber        = 20261021;    // v3 magic number
input int             InpSlippagePoints     = 10;

input group "=== 4. PH2-C1 Sentinel Deployment Guards ==="
input string          InpAllowedSymbolPrefix = "Volatility 25 (1s)"; // ONLY C1-validated symbol
input bool            InpUseOnnxFilter       = false;      // C2 gate: AUC 0.554 unvalidated -> keep OFF
input string          InpOnnxModelFile       = "c2_vol_filter.onnx";  // in MQL5\Files\
input double          InpOnnxProbThreshold   = 0.55;       // Min P(win) to allow entry when gate ON

//--- Global Objects & State
CTrade         ExtTrade;
CPositionInfo  ExtPosition;
CSymbolInfo    ExtSymbol;

int            ExtATRHandle     = INVALID_HANDLE;
datetime       ExtLastBarTime   = 0;
datetime       ExtCurrentDay    = 0;
double         ExtDayStartEq    = 0.0;
long           ExtOnnxHandle    = INVALID_HANDLE;

//+------------------------------------------------------------------+
//| Expert initialization                                            |
//+------------------------------------------------------------------+
int OnInit()
{
   //--- SENTINEL GUARD: only the C1-validated symbol may trade
   if(StringFind(_Symbol, InpAllowedSymbolPrefix) < 0)
   {
      PrintFormat("SENTINEL GUARD: '%s' is NOT C1-validated (V75 1s FAILED Gate 4). Only '%s' is authorized. EA halted.",
                  _Symbol, InpAllowedSymbolPrefix);
      return(INIT_FAILED);
   }
   if(!ExtSymbol.Name(_Symbol))
   {
      Print("ERROR: Failed to initialize symbol info for ", _Symbol);
      return(INIT_FAILED);
   }
   ExtTrade.SetExpertMagicNumber(InpMagicNumber);
   ExtTrade.SetDeviationInPoints(InpSlippagePoints);
   ExtTrade.SetTypeFillingBySymbol(_Symbol);

   ExtATRHandle = iATR(_Symbol, InpTimeframe, InpATRPeriod);
   if(ExtATRHandle == INVALID_HANDLE)
   {
      Print("ERROR: Failed to create iATR handle.");
      return(INIT_FAILED);
   }
   ExtDayStartEq = AccountInfoDouble(ACCOUNT_EQUITY);
   ExtCurrentDay = iTime(_Symbol, PERIOD_D1, 0);

   //--- optional C2 ONNX gate (fail-open, logged)
   if(InpUseOnnxFilter)
   {
      ExtOnnxHandle = OnnxCreate(InpOnnxModelFile, ONNX_DEFAULT);
      if(ExtOnnxHandle == INVALID_HANDLE)
      {
         PrintFormat("WARNING: ONNX '%s' failed to load (err %d). Gate fails OPEN (EA trades as v2.00 logic).",
                     InpOnnxModelFile, GetLastError());
      }
      else
      {
         // FEATURE VECTOR (1x6): [z_impulse, squeeze_ratio, spread_bps, spread_to_atr, hour_sin, hour_cos]
         // !!! ORDER MUST MATCH THE C2 TRAINER EXACTLY. C2 not validated (AUC 0.554): keep gate OFF.
         const long input_shape[] = {1, 6};
         if(!OnnxSetInputShape(ExtOnnxHandle, 0, input_shape))
            Print("WARNING: OnnxSetInputShape failed (err ", GetLastError(), "). Gate fails open.");
      }
   }
   PrintFormat("Deriv_VolSqueeze_Breakout_EA v3.00 (C1 Sentinel build) on %s. q=%.2f, z=%.2f, hold=%d bars. ONNX gate=%s.",
               _Symbol, InpSqueezeQuantile, InpBreakoutZScore, InpMaxHoldBars, InpUseOnnxFilter ? "ON" : "OFF");
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization                                          |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   if(ExtATRHandle != INVALID_HANDLE)
      IndicatorRelease(ExtATRHandle);
   if(ExtOnnxHandle != INVALID_HANDLE)
      OnnxRelease(ExtOnnxHandle);
}

//+------------------------------------------------------------------+
//| Compute Sample Standard Deviation of an Array Slice              |
//+------------------------------------------------------------------+
double CalcSampleStd(const double &arr[], int start_idx, int count)
{
   if(count <= 1) return(0.0);
   double sum = 0.0;
   for(int i = 0; i < count; i++)
      sum += arr[start_idx + i];
   double mean = sum / count;
   double sq_sum = 0.0;
   for(int i = 0; i < count; i++)
   {
      double diff = arr[start_idx + i] - mean;
      sq_sum += diff * diff;
   }
   return(MathSqrt(sq_sum / (count - 1)));
}

//+------------------------------------------------------------------+
//| Compute Empirical Quantile of a Rolling Volatility Array         |
//+------------------------------------------------------------------+
double CalcQuantile(const double &vals[], int count, double q)
{
   if(count <= 0) return(0.0);
   double sorted[];
   ArrayResize(sorted, count);
   ArrayCopy(sorted, vals, 0, 0, count);
   ArraySort(sorted);
   double pos = q * (count - 1);
   int lo = (int)MathFloor(pos);
   int hi = (int)MathCeil(pos);
   if(lo == hi) return(sorted[lo]);
   double weight = pos - lo;
   return(sorted[lo] * (1.0 - weight) + sorted[hi] * weight);
}

//+------------------------------------------------------------------+
//| Check and Enforce Non-Overlapping Time-Stop Exit                |
//+------------------------------------------------------------------+
bool ManageOpenPositions(datetime current_bar_time)
{
   bool has_open_position = false;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(ExtPosition.SelectByIndex(i))
      {
         if(ExtPosition.Symbol() == _Symbol && ExtPosition.Magic() == InpMagicNumber)
         {
            datetime open_time = ExtPosition.Time();
            int bars_elapsed = iBarShift(_Symbol, InpTimeframe, open_time, false);
            if(bars_elapsed >= InpMaxHoldBars)
            {
               ulong ticket = ExtPosition.Ticket();
               PrintFormat("Time-Stop Reached (%d bars >= %d). Closing Ticket #%I64u at Market.",
                           bars_elapsed, InpMaxHoldBars, ticket);
               ExtTrade.PositionClose(ticket);
            }
            else has_open_position = true;
         }
      }
   }
   return(has_open_position);
}

//+------------------------------------------------------------------+
//| ONNX C2 Filter: returns true if the trade is allowed by the gate |
//| (fail-open policy: if the model cannot run, the trade proceeds)  |
//+------------------------------------------------------------------+
bool OnnxFilterAllows(double z_impulse, double squeeze_ratio, double spread_bps,
                      double spread_to_atr, datetime bar_time)
{
   if(!InpUseOnnxFilter || ExtOnnxHandle == INVALID_HANDLE)
      return(true);                                  // gate OFF or unloadable -> pure v2 logic

   const long output_shape[] = {1, 1};
   if(!OnnxSetOutputShape(ExtOnnxHandle, 0, output_shape))
   {
      Print("WARNING: OnnxSetOutputShape failed (err ", GetLastError(), "). Gate fails open.");
      return(true);
   }

   double hour_ang = 2.0 * M_PI * (double)TimeHour(bar_time) / 24.0;
   double features[6];
   features[0] = z_impulse;                    // |r1| / std20 (signed z)
   features[1] = squeeze_ratio;               // std20 / q_threshold (<= 1.0 in squeeze)
   features[2] = spread_bps;                  // live spread in bps
   features[3] = spread_to_atr;                // spread / ATR20
   features[4] = MathSin(hour_ang);            // hour cyclical sin
   features[5] = MathCos(hour_ang);            // hour cyclical cos

   float input_data[1][6];
   for(int j = 0; j < 6; j++) input_data[0][j] = (float)features[j];
   float output_data[1][1];
   ArrayInitialize(output_data, 0.0f);

   if(!OnnxRun(ExtOnnxHandle, ONNX_NO_CONVERSION, input_data, output_data))
   {
      Print("WARNING: OnnxRun failed (err ", GetLastError(), "). Gate fails open.");
      return(true);
   }

   double p_win = (double)output_data[0][0];
   PrintFormat("C2 Gate: z=%.3f squeeze_ratio=%.3f spr=%.2fbps atr=%.4f -> P(win)=%.4f (thr=%.2f)",
               z_impulse, squeeze_ratio, spread_bps, spread_to_atr, p_win, InpOnnxProbThreshold);
   return(p_win >= InpOnnxProbThreshold);
}

//+------------------------------------------------------------------+
//| Compute Volatility-Parity Lot Size                               |
//+------------------------------------------------------------------+
double CalcVolatilityParityLots(double entry_price, double std1_bps)
{
   double hold_std_bps = std1_bps * MathSqrt((double)InpMaxHoldBars);
   if(hold_std_bps <= 0.0001 || entry_price <= 0.0)
      return(ExtSymbol.LotsMin());
   double move_price_1sd = entry_price * (hold_std_bps / 10000.0);
   double tick_size  = ExtSymbol.TickSize();
   double tick_value = ExtSymbol.TickValue();
   if(tick_size <= 0.0 || tick_value <= 0.0)
      return(ExtSymbol.LotsMin());
   double loss_per_lot_1sd = (move_price_1sd / tick_size) * tick_value;
   if(loss_per_lot_1sd <= 0.0)
      return(ExtSymbol.LotsMin());
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   double risk_dollars = equity * (InpRiskPerSDPct / 100.0);
   double raw_lots = risk_dollars / loss_per_lot_1sd;
   double step = ExtSymbol.LotsStep();
   double min_lot = ExtSymbol.LotsMin();
   double max_lot = ExtSymbol.LotsMax();
   double lots = MathFloor(raw_lots / step) * step;
   if(lots < min_lot) lots = min_lot;
   if(lots > max_lot) lots = max_lot;
   return(NormalizeDouble(lots, 2));
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
   //--- 1. Daily drawdown circuit breaker
   datetime today = iTime(_Symbol, PERIOD_D1, 0);
   if(today != ExtCurrentDay && today != 0)
   {
      ExtCurrentDay = today;
      ExtDayStartEq = AccountInfoDouble(ACCOUNT_EQUITY);
   }
   double current_eq = AccountInfoDouble(ACCOUNT_EQUITY);
   if(ExtDayStartEq > 0.0 && ((ExtDayStartEq - current_eq) / ExtDayStartEq) * 100.0 >= InpMaxDailyLossPct)
      return;

   //--- 2. Strictly on new completed H1 bar
   datetime bar_time = iTime(_Symbol, InpTimeframe, 0);
   if(bar_time == ExtLastBarTime || bar_time == 0)
      return;

   //--- 3. Non-overlapping position state & time-stop enforcement
   bool is_positioned = ManageOpenPositions(bar_time);
   if(is_positioned)
   {
      ExtLastBarTime = bar_time;
      return;
   }

   //--- 4. Fetch historical closes
   int needed_closes = InpQuantileWindow + InpVolLookback + 2;
   double closes[];
   ArraySetAsSeries(closes, true);
   int copied = CopyClose(_Symbol, InpTimeframe, 1, needed_closes, closes);
   if(copied < needed_closes)
      return;

   //--- 5. 1-bar returns in bps
   int n_rets = needed_closes - 1;
   double rets_bps[];
   ArrayResize(rets_bps, n_rets);
   for(int k = 0; k < n_rets; k++)
   {
      if(closes[k + 1] <= 0.0) return;
      rets_bps[k] = ((closes[k] - closes[k + 1]) / closes[k + 1]) * 10000.0;
   }

   //--- 6. Rolling 20-bar std across the last 100 bars
   double rolling_std[];
   ArrayResize(rolling_std, InpQuantileWindow);
   for(int m = 0; m < InpQuantileWindow; m++)
      rolling_std[m] = CalcSampleStd(rets_bps, m, InpVolLookback);
   double current_std20 = rolling_std[0];
   double current_r1    = rets_bps[0];
   if(current_std20 <= 0.0)
   {
      ExtLastBarTime = bar_time;
      return;
   }
   double q_threshold = CalcQuantile(rolling_std, InpQuantileWindow, InpSqueezeQuantile);

   //--- 7. Squeeze + impulse evaluation
   bool is_squeeze   = (current_std20 <= q_threshold);
   bool long_signal   = is_squeeze && (current_r1 >=  InpBreakoutZScore * current_std20);
   bool short_signal  = is_squeeze && (current_r1 <= -InpBreakoutZScore * current_std20);
   if(!long_signal && !short_signal)
   {
      ExtLastBarTime = bar_time;
      return;
   }

   //--- 8. Live spread circuit breaker
   if(!ExtSymbol.RefreshRates())
      return;
   double ask = ExtSymbol.Ask();
   double bid = ExtSymbol.Bid();
   double spread_price = ask - bid;
   double mid_price = 0.5 * (ask + bid);
   double spread_bps = (mid_price > 0.0) ? (spread_price / mid_price) * 10000.0 : 999.0;
   double atr_buf[];
   ArraySetAsSeries(atr_buf, true);
   if(CopyBuffer(ExtATRHandle, 0, 1, 1, atr_buf) < 1 || atr_buf[0] <= 0.0)
      return;
   double current_atr = atr_buf[0];
   double spread_to_atr = spread_price / current_atr;
   if(spread_to_atr > InpMaxSpreadToATR || spread_bps > InpMaxSpreadBps)
   {
      PrintFormat("Spread Filter Blocked Entry: Spread/ATR=%.2f%% (Max %.2f%%), Spread=%.2f bps (Max %.2f bps).",
                  spread_to_atr * 100.0, InpMaxSpreadToATR * 100.0, spread_bps, InpMaxSpreadBps);
      ExtLastBarTime = bar_time;
      return;
   }

   //--- 9. C2 ONNX gate (fail-open; disabled by default: AUC 0.554 OOS)
   double z_impulse     = current_r1 / current_std20;
   double squeeze_ratio = (q_threshold > 0.0) ? current_std20 / q_threshold : 1.0;
   if(!OnnxFilterAllows(z_impulse, squeeze_ratio, spread_bps, spread_to_atr, bar_time))
   {
      PrintFormat("C2 Gate blocked entry (z=%.3f, squeeze_ratio=%.3f).", z_impulse, squeeze_ratio);
      ExtLastBarTime = bar_time;
      return;
   }

   //--- 10. Volatility-parity sizing & execution
   double lots = CalcVolatilityParityLots(mid_price, current_std20);
   int digits = ExtSymbol.Digits();
   if(long_signal)
   {
      double sl = InpUseHardTPSL ? NormalizeDouble(ask - InpHardSL_ATR * current_atr, digits) : 0.0;
      double tp = InpUseHardTPSL ? NormalizeDouble(ask + InpHardTP_ATR * current_atr, digits) : 0.0;
      string comment = StringFormat("V3_L_z%.2f_q%.2f", z_impulse, InpSqueezeQuantile);
      if(ExtTrade.Buy(lots, _Symbol, ask, sl, tp, comment))
         PrintFormat("LONG Executed: Lots=%.2f, Ask=%.2f, z=%.3f, std20=%.2f bps, squeeze_ratio=%.3f, Spr=%.2f bps",
                     lots, ask, z_impulse, current_std20, squeeze_ratio, spread_bps);
   }
   else
   {
      double sl = InpUseHardTPSL ? NormalizeDouble(bid + InpHardSL_ATR * current_atr, digits) : 0.0;
      double tp = InpUseHardTPSL ? NormalizeDouble(bid - InpHardTP_ATR * current_atr, digits) : 0.0;
      string comment = StringFormat("V3_S_z%.2f_q%.2f", z_impulse, InpSqueezeQuantile);
      if(ExtTrade.Sell(lots, _Symbol, bid, sl, tp, comment))
         PrintFormat("SHORT Executed: Lots=%.2f, Bid=%.2f, z=%.3f, std20=%.2f bps, squeeze_ratio=%.3f, Spr=%.2f bps",
                     lots, bid, z_impulse, current_std20, squeeze_ratio, spread_bps);
   }
   ExtLastBarTime = bar_time;
}
//+------------------------------------------------------------------+
