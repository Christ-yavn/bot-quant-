//+------------------------------------------------------------------+
//|                               Deriv_VolSqueeze_Breakout_EA.mq5   |
//|        Quantitative Production Blueprint — Deriv Synthetic Audit |
//|   Target Symbols: Volatility 25 (1s) Index & Volatility 75 (1s)  |
//|   Timeframe: H1 (Hourly Close Execution, Non-Overlapping Hold)   |
//+------------------------------------------------------------------+
#property copyright "Quantitative Research & Algorithmic Systems"
#property link      "https://github.com/Christ-yavn/bot-quant-"
#property version   "2.00"
#property description "Phase 2 Quant EA - Volatility Compression & Impulse Breakout (H1)"
#property strict

#include <Trade\Trade.mqh>
#include <Trade\PositionInfo.mqh>
#include <Trade\SymbolInfo.mqh>

//--- Input Parameters: Signal & Regime Mechanics
input group "=== 1. Volatility Squeeze & Impulse Breakout Parameters ==="
input ENUM_TIMEFRAMES InpTimeframe          = PERIOD_H1;   // Execution Timeframe (Validated on H1)
input int             InpVolLookback        = 20;          // Rolling Volatility Window (Bars, N=20)
input int             InpQuantileWindow     = 100;         // Squeeze Percentile Lookback (Bars, M=100)
input double          InpSqueezeQuantile    = 0.25;        // Bandwidth Squeeze Quantile (0.25 = 25th pct, or 0.30)
input double          InpBreakoutZScore     = 1.50;        // Impulse Breakout Z-Score Threshold (1.50 or 1.25)
input int             InpMaxHoldBars        = 4;           // Non-Overlapping Time-Stop Horizon (H1 Bars = 4h)

//--- Input Parameters: Excursion Guardrails & Microstructure Filter
input group "=== 2. Excursion Guardrails & Spread Circuit Breaker ==="
input bool            InpUseHardTPSL        = false;       // Enable Hard ATR Stop-Loss / Take-Profit (Default: Pure 4h Time-Stop)
input int             InpATRPeriod          = 20;          // ATR Period for Hard Stops & Spread Ratio
input double          InpHardSL_ATR         = 2.00;        // Hard Disaster Stop-Loss (Multiples of ATR20)
input double          InpHardTP_ATR         = 3.50;        // Hard Take-Profit Target (Multiples of ATR20)
input double          InpMaxSpreadToATR     = 0.050;       // Max Allowed Spread / H1 ATR Ratio (5.0% Ceiling)
input double          InpMaxSpreadBps       = 4.50;        // Max Allowed Spread in Basis Points of Price

//--- Input Parameters: Dynamic Volatility-Parity Position Sizing
input group "=== 3. Risk Management & Volatility-Parity Sizing ==="
input double          InpRiskPerSDPct       = 0.50;        // Account Equity Risk (%) per 1-SD (4-Hour) Move
input double          InpMaxDailyLossPct    = 3.00;        // Daily Drawdown Circuit Breaker (% of Start-of-Day Equity)
input ulong           InpMagicNumber        = 20261021;    // Unique Strategy Magic Number (Phase 2)
input int             InpSlippagePoints     = 10;          // Max Permissible Slippage (Points)

//--- Global Objects & State Variables
CTrade         ExtTrade;
CPositionInfo  ExtPosition;
CSymbolInfo    ExtSymbol;

int            ExtATRHandle     = INVALID_HANDLE;
datetime       ExtLastBarTime   = 0;
datetime       ExtCurrentDay    = 0;
double         ExtDayStartEq    = 0.0;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
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
   
   PrintFormat("Deriv_VolSqueeze_Breakout_EA initialized on %s (%s). SqueezeQ=%.2f, BreakZ=%.2f, Hold=%d bars.",
               _Symbol, EnumToString(InpTimeframe), InpSqueezeQuantile, InpBreakoutZScore, InpMaxHoldBars);
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   if(ExtATRHandle != INVALID_HANDLE)
      IndicatorRelease(ExtATRHandle);
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
//| Check and Enforce Non-Overlapping Time-Stop Exit                 |
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
            else
            {
               has_open_position = true;
            }
         }
      }
   }
   return(has_open_position);
}

//+------------------------------------------------------------------+
//| Compute Volatility-Normalized Lot Size                           |
//+------------------------------------------------------------------+
double CalcVolatilityParityLots(double entry_price, double std1_bps)
{
   // Expected 4-hour standard deviation in bps = std1_bps * sqrt(InpMaxHoldBars)
   double hold_std_bps = std1_bps * MathSqrt((double)InpMaxHoldBars);
   if(hold_std_bps <= 0.0001 || entry_price <= 0.0)
      return(ExtSymbol.LotsMin());
      
   double move_price_1sd = entry_price * (hold_std_bps / 10000.0);
   double tick_size      = ExtSymbol.TickSize();
   double tick_value     = ExtSymbol.TickValue();
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
   //--- 1. Update Daily Drawdown Circuit Breaker
   datetime today = iTime(_Symbol, PERIOD_D1, 0);
   if(today != ExtCurrentDay && today != 0)
   {
      ExtCurrentDay = today;
      ExtDayStartEq = AccountInfoDouble(ACCOUNT_EQUITY);
   }
   
   double current_eq = AccountInfoDouble(ACCOUNT_EQUITY);
   if(ExtDayStartEq > 0.0 && ((ExtDayStartEq - current_eq) / ExtDayStartEq) * 100.0 >= InpMaxDailyLossPct)
   {
      return; // Daily loss limit breached; halt new entries until next UTC day
   }

   //--- 2. Execute Strictly on New Completed H1 Bar
   datetime bar_time = iTime(_Symbol, InpTimeframe, 0);
   if(bar_time == ExtLastBarTime || bar_time == 0)
      return;
      
   //--- 3. Check Non-Overlapping Position State & Enforce 4-Hour Time-Stop
   bool is_positioned = ManageOpenPositions(bar_time);
   if(is_positioned)
   {
      ExtLastBarTime = bar_time;
      return; // Strictly non-overlapping: never stack concurrent positions
   }
   
   //--- 4. Fetch Historical Close Prices for Volatility Squeeze & Impulse Calculation
   // Need InpQuantileWindow + InpVolLookback + 2 completed bars (starting at shift=1)
   int needed_closes = InpQuantileWindow + InpVolLookback + 2;
   double closes[];
   ArraySetAsSeries(closes, true);
   int copied = CopyClose(_Symbol, InpTimeframe, 1, needed_closes, closes);
   if(copied < needed_closes)
      return;
      
   //--- 5. Compute 1-Bar Returns in Basis Points (r_bps[k] = (close[k] - close[k+1]) / close[k+1] * 10000)
   int n_rets = needed_closes - 1;
   double rets_bps[];
   ArrayResize(rets_bps, n_rets);
   for(int k = 0; k < n_rets; k++)
   {
      if(closes[k + 1] <= 0.0) return;
      rets_bps[k] = ((closes[k] - closes[k + 1]) / closes[k + 1]) * 10000.0;
   }
   
   //--- 6. Compute Rolling 20-Bar Return StdDev Across Last 100 Bars (m = 0 .. InpQuantileWindow - 1)
   double rolling_std[];
   ArrayResize(rolling_std, InpQuantileWindow);
   for(int m = 0; m < InpQuantileWindow; m++)
   {
      rolling_std[m] = CalcSampleStd(rets_bps, m, InpVolLookback);
   }
   
   double current_std20 = rolling_std[0];     // Most recent completed bar's 20-bar volatility
   double current_r1    = rets_bps[0];        // Most recent completed bar's 1-bar return (bps)
   if(current_std20 <= 0.0)
   {
      ExtLastBarTime = bar_time;
      return;
   }
   
   double q_threshold = CalcQuantile(rolling_std, InpQuantileWindow, InpSqueezeQuantile);
   
   //--- 7. Evaluate Squeeze Regime + Impulse Breakout Conditions
   bool is_squeeze    = (current_std20 <= q_threshold);
   bool long_signal   = is_squeeze && (current_r1 >=  InpBreakoutZScore * current_std20);
   bool short_signal  = is_squeeze && (current_r1 <= -InpBreakoutZScore * current_std20);
   
   if(!long_signal && !short_signal)
   {
      ExtLastBarTime = bar_time;
      return;
   }
   
   //--- 8. Verify Live Microstructure & Spread-to-ATR Circuit Breaker
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
      PrintFormat("Spread Filter Blocked Entry on %s: Spread/ATR=%.2f%% (Max %.2f%%), Spread=%.2f bps (Max %.2f bps).",
                  _Symbol, spread_to_atr * 100.0, InpMaxSpreadToATR * 100.0, spread_bps, InpMaxSpreadBps);
      ExtLastBarTime = bar_time;
      return;
   }
   
   //--- 9. Calculate Volatility-Parity Position Size & Execute Trade
   double lots = CalcVolatilityParityLots(mid_price, current_std20);
   int digits = ExtSymbol.Digits();
   
   if(long_signal)
   {
      double sl = InpUseHardTPSL ? NormalizeDouble(ask - InpHardSL_ATR * current_atr, digits) : 0.0;
      double tp = InpUseHardTPSL ? NormalizeDouble(ask + InpHardTP_ATR * current_atr, digits) : 0.0;
      string comment = StringFormat("VSB_L_z%.2f_q%.2f", current_r1 / current_std20, InpSqueezeQuantile);
      if(ExtTrade.Buy(lots, _Symbol, ask, sl, tp, comment))
      {
         PrintFormat("LONG Executed on %s: Lots=%.2f, Ask=%.2f, r1=%.2f bps, std20=%.2f bps (<= q%.0f=%.2f bps), Spr=%.2f bps",
                     _Symbol, lots, ask, current_r1, current_std20, InpSqueezeQuantile*100, q_threshold, spread_bps);
      }
   }
   else if(short_signal)
   {
      double sl = InpUseHardTPSL ? NormalizeDouble(bid + InpHardSL_ATR * current_atr, digits) : 0.0;
      double tp = InpUseHardTPSL ? NormalizeDouble(bid - InpHardTP_ATR * current_atr, digits) : 0.0;
      string comment = StringFormat("VSB_S_z%.2f_q%.2f", current_r1 / current_std20, InpSqueezeQuantile);
      if(ExtTrade.Sell(lots, _Symbol, bid, sl, tp, comment))
      {
         PrintFormat("SHORT Executed on %s: Lots=%.2f, Bid=%.2f, r1=%.2f bps, std20=%.2f bps (<= q%.0f=%.2f bps), Spr=%.2f bps",
                     _Symbol, lots, bid, current_r1, current_std20, InpSqueezeQuantile*100, q_threshold, spread_bps);
      }
   }
   
   ExtLastBarTime = bar_time;
}
