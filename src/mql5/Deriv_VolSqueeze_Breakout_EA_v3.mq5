//+------------------------------------------------------------------+
//|                             Deriv_VolSqueeze_Breakout_EA_v3.mq5 |
//|        Quantitative Production Blueprint - Deriv Synthetic Audit |
//|   Target Symbol: Volatility 25 (1s) Index (Sentinel C1 Certified)|
//|   Timeframe: H1 (Hourly Close Execution, 4h Non-Overlapping Hold)|
//|   Features : Real Spread Reader + C2 Machine Learning ONNX Filter |
//+------------------------------------------------------------------+
#property copyright "Quantitative Research & Algorithmic Systems"
#property link      "https://github.com/Christ-yavn/bot-quant-"
#property version   "3.00"
#property description "Phase 2 Quant EA v3.00 - Volatility Compression & C2 ONNX Filter (H1)"
#property strict

#include <Trade\Trade.mqh>
#include <Trade\PositionInfo.mqh>
#include <Trade\SymbolInfo.mqh>

//--- Input Parameters: Signal & Regime Mechanics
input group "=== 1. Volatility Squeeze & Impulse Breakout Parameters ==="
input ENUM_TIMEFRAMES InpTimeframe          = PERIOD_H1;   // Execution Timeframe (H1)
input int             InpVolLookback        = 20;          // Rolling Volatility Window (Bars, N=20)
input int             InpQuantileWindow     = 100;         // Squeeze Percentile Lookback (Bars, M=100)
input double          InpSqueezeQuantile    = 0.25;        // Bandwidth Squeeze Quantile (0.25 = 25th pct)
input double          InpBreakoutZScore     = 1.50;        // Impulse Breakout Z-Score Threshold (1.50)
input int             InpMaxHoldBars        = 4;           // Non-Overlapping Time-Stop Horizon (4 H1 Bars = 4h)

//--- Input Parameters: C2 Machine Learning ONNX Filter
input group "=== 2. C2 Machine Learning / ONNX Filter ==="
input bool            InpUseONNXFilter      = true;        // Enable C2 ONNX Neural / GBDT Filter
input string          InpONNXModelName      = "c2_vol_filter.onnx"; // ONNX Model File (in MQL5\Files)
input double          InpMinWinProbability  = 0.50;        // Min Predicted Win Probability to Enter (0.50 = 50%)

//--- Input Parameters: Excursion Guardrails & Real Spread Filter
input group "=== 3. Excursion Guardrails & Dynamic Spread Filter ==="
input bool            InpUseHardTPSL        = false;       // Enable Hard ATR Stop-Loss / Take-Profit (Default: Pure 4h Time-Stop)
input int             InpATRPeriod          = 20;          // ATR Period for Hard Stops & Spread Ratio
input double          InpHardSL_ATR         = 2.00;        // Hard Disaster Stop-Loss (Multiples of ATR20)
input double          InpHardTP_ATR         = 3.50;        // Hard Take-Profit Target (Multiples of ATR20)
input double          InpMaxSpreadToATR     = 0.050;       // Max Allowed Spread / H1 ATR Ratio (5.0% Ceiling)
input double          InpMaxSpreadBps       = 4.50;        // Max Allowed Spread in Basis Points of Price

//--- Input Parameters: Dynamic Volatility-Parity Position Sizing
input group "=== 4. Risk Management & Volatility-Parity Sizing ==="
input double          InpRiskPerSDPct       = 0.50;        // Account Equity Risk (%) per 1-SD (4-Hour) Move
input double          InpMaxDailyLossPct    = 3.00;        // Daily Drawdown Circuit Breaker (% of Start-of-Day Equity)
input ulong           InpMagicNumber        = 20261022;    // Strategy Magic Number (v3.00)
input int             InpSlippagePoints     = 10;          // Max Permissible Slippage (Points)

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

//+------------------------------------------------------------------+
//| Expert Initialization Function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
   if(!ExtSymbol.Name(_Symbol))
   {
      PrintFormat("[v3.00 ERROR] Symbol %s could not be initialized.", _Symbol);
      return INIT_FAILED;
   }
   ExtSymbol.Refresh();
   
   //--- Validate Symbol: Volatility 25 (1s) Index is the Certified Asset
   if(StringFind(_Symbol, "Volatility 25 (1s)") < 0 && StringFind(_Symbol, "25 (1s)") < 0)
   {
      PrintFormat("[v3.00 WARNING] %s was NOT validated in Phase 2 Sentinel C1. Certified asset is 'Volatility 25 (1s) Index'.", _Symbol);
   }

   ExtTrade.SetExpertMagicNumber(InpMagicNumber);
   ExtTrade.SetDeviationInPoints(InpSlippagePoints);
   ExtTrade.SetTypeFilling(ORDER_FILLING_FOK);

   //--- Initialize ATR Indicator
   ExtATRHandle = iATR(_Symbol, InpTimeframe, InpATRPeriod);
   if(ExtATRHandle == INVALID_HANDLE)
   {
      PrintFormat("[v3.00 ERROR] Failed to create ATR(%d) handle. Error = %d", InpATRPeriod, GetLastError());
      return INIT_FAILED;
   }

   //--- Initialize C2 ONNX Model if enabled
   if(InpUseONNXFilter)
   {
      ExtOnnxHandle = OnnxCreate(InpONNXModelName, ONNX_DEFAULT);
      if(ExtOnnxHandle != INVALID_HANDLE)
      {
         const long in_shape[] = {1, 7};
         if(!OnnxSetInputShape(ExtOnnxHandle, 0, in_shape))
         {
            PrintFormat("[v3.00 ONNX WARNING] OnnxSetInputShape failed. Code=%d", GetLastError());
         }
         else
         {
            ExtModelLoaded = true;
            PrintFormat("[v3.00 ONNX] Model '%s' successfully loaded and ready for inference.", InpONNXModelName);
         }
      }
      else
      {
         PrintFormat("[v3.00 ONNX NOTICE] Model '%s' not loaded (Code=%d). Operating in Pure S1 Quant mode.", InpONNXModelName, GetLastError());
         ExtModelLoaded = false;
      }
   }

   ExtDayStartEq = AccountInfoDouble(ACCOUNT_EQUITY);
   ExtCurrentDay = iTime(_Symbol, PERIOD_D1, 0);

   PrintFormat("[v3.00 INIT SUCCESS] %s | TF=%s | VolLookback=%d | SqueezeQ=%.2f | BreakoutZ=%.2f | Hold=%dh | ONNX=%s",
               _Symbol, EnumToString(InpTimeframe), InpVolLookback, InpSqueezeQuantile, InpBreakoutZScore, InpMaxHoldBars,
               (ExtModelLoaded ? "ACTIVE" : "BYPASS"));

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
   PrintFormat("[v3.00 DEINIT] Shutdown clean. Reason = %d", reason);
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
//| Calculate Kurtosis of array                                      |
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
                        double levy_area, double spread_atr, double skew20, double kurt20,
                        double &out_prob)
{
   if(!ExtModelLoaded || ExtOnnxHandle == INVALID_HANDLE)
   {
      out_prob = 1.0;
      return true; // Bypass filter if model not active
   }
   
   float in_features[7];
   in_features[0] = (float)vol_ratio;
   in_features[1] = (float)impulse_z;
   in_features[2] = (float)direction;
   in_features[3] = (float)levy_area;
   in_features[4] = (float)spread_atr;
   in_features[5] = (float)skew20;
   in_features[6] = (float)kurt20;
   
   long out_label[1];
   float out_probs[2];
   
   ResetLastError();
   if(!OnnxRun(ExtOnnxHandle, ONNX_NO_CONVERSION, in_features, out_label, out_probs))
   {
      PrintFormat("[v3.00 ONNX RUN ERROR] Code = %d. Bypassing filter.", GetLastError());
      out_prob = 1.0;
      return true;
   }
   
   out_prob = (double)out_probs[1]; // Probability of win (Class 1)
   return (out_prob >= InpMinWinProbability);
}

//+------------------------------------------------------------------+
//| Position Management & Strict 4-Hour Time-Stop Engine             |
//+------------------------------------------------------------------+
bool ManageOpenPositions(datetime current_bar_time)
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(ExtPosition.SelectByIndex(i))
      {
         if(ExtPosition.Symbol() == _Symbol && ExtPosition.Magic() == InpMagicNumber)
         {
            datetime open_time = (datetime)ExtPosition.Time();
            int bars_elapsed = iBarShift(_Symbol, InpTimeframe, open_time, false);
            
            // Exit immediately if 4 or more H1 bars have elapsed
            if(bars_elapsed >= InpMaxHoldBars)
            {
               double exit_price = (ExtPosition.PositionType() == POSITION_TYPE_BUY) ? 
                                   ExtSymbol.Bid() : ExtSymbol.Ask();
               PrintFormat("[v3.00 TIME-STOP EXIT] Ticket #%I64u | Bars Held = %d/%d | OpenPrice=%.2f | ExitPrice=%.2f | PnL=%.2f USD",
                           ExtPosition.Ticket(), bars_elapsed, InpMaxHoldBars, ExtPosition.PriceOpen(), exit_price, ExtPosition.Profit());
               ExtTrade.PositionClose(ExtPosition.Ticket());
               return false;
            }
            return true;
         }
      }
   }
   return false;
}

//+------------------------------------------------------------------+
//| Dynamic Volatility-Parity Position Sizing Engine                 |
//+------------------------------------------------------------------+
double CalculateVolParityLot(double std20_bps, double current_price)
{
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   double risk_cash = equity * (InpRiskPerSDPct / 100.0);
   
   double four_hour_sd_pts = (std20_bps / 10000.0) * current_price * 2.0; // 2 * 1-hour SD = 4-hour SD
   if(four_hour_sd_pts <= 0.0) four_hour_sd_pts = current_price * 0.001;

   double tick_size  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   double tick_value = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   if(tick_size <= 0.0) tick_size = _Point;
   if(tick_value <= 0.0) tick_value = 1.0;

   double dollar_loss_per_lot = (four_hour_sd_pts / tick_size) * tick_value;
   if(dollar_loss_per_lot <= 0.0) return SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);

   double raw_lot = risk_cash / dollar_loss_per_lot;
   double min_lot  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double max_lot  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double lot_step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);

   double rounded_lot = MathFloor(raw_lot / lot_step) * lot_step;
   if(rounded_lot < min_lot) rounded_lot = min_lot;
   if(rounded_lot > max_lot) rounded_lot = max_lot;

   return rounded_lot;
}

//+------------------------------------------------------------------+
//| Expert Tick Function                                             |
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
      return; // Daily loss limit breached (-3.00%)
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
      return;
   }
   
   //--- 4. Fetch Historical Close Prices
   int needed_closes = InpQuantileWindow + InpVolLookback + 2;
   double closes[];
   ArraySetAsSeries(closes, true);
   int copied = CopyClose(_Symbol, InpTimeframe, 1, needed_closes, closes);
   if(copied < needed_closes)
      return;
      
   //--- 5. Compute 1-Bar Returns in Basis Points
   double r_bps[];
   ArrayResize(r_bps, InpQuantileWindow + InpVolLookback);
   for(int k = 0; k < InpQuantileWindow + InpVolLookback; k++)
   {
      r_bps[k] = (closes[k] - closes[k+1]) / closes[k+1] * 10000.0;
   }
   
   //--- 6. Compute Rolling Standard Deviations
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
   
   double current_std20 = rolling_std[0]; // Squeeze candidate
   
   //--- 7. Compute Quantile Cutoff Threshold
   double sorted_std[];
   ArrayCopy(sorted_std, rolling_std);
   ArraySort(sorted_std);
   int q_index = (int)MathFloor(InpSqueezeQuantile * (InpQuantileWindow - 1));
   if(q_index < 0) q_index = 0;
   if(q_index >= InpQuantileWindow) q_index = InpQuantileWindow - 1;
   double squeeze_threshold = sorted_std[q_index];
   
   //--- 8. Evaluate Squeeze Compression Condition
   if(current_std20 > squeeze_threshold || current_std20 <= 1e-6)
   {
      ExtLastBarTime = bar_time;
      return;
   }
   
   //--- 9. Evaluate Impulse Breakout Condition
   double impulse_return_bps = r_bps[0];
   double breakout_z = MathAbs(impulse_return_bps) / current_std20;
   if(breakout_z < InpBreakoutZScore)
   {
      ExtLastBarTime = bar_time;
      return;
   }
   
   //--- 10. Check Microstructure Real Spread Filter
   ExtSymbol.Refresh();
   double spread_pts = (double)SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
   double ask = ExtSymbol.Ask();
   double bid = ExtSymbol.Bid();
   double mid_price = (ask + bid) / 2.0;
   double spread_bps = (spread_pts * _Point / mid_price) * 10000.0;
   
   double atr_vals[];
   ArraySetAsSeries(atr_vals, true);
   CopyBuffer(ExtATRHandle, 0, 1, 1, atr_vals);
   double atr_pts = atr_vals[0] / _Point;
   
   double spread_to_atr = (atr_pts > 0.0) ? (spread_pts / atr_pts) : 1.0;
   if(spread_to_atr > InpMaxSpreadToATR || spread_bps > InpMaxSpreadBps)
   {
      PrintFormat("[v3.00 SPREAD REJECT] Spread=%.2f bps (%.1f%% of ATR) exceeds threshold (%.2f bps / %.1f%% ATR)",
                  spread_bps, spread_to_atr * 100.0, InpMaxSpreadBps, InpMaxSpreadToATR * 100.0);
      ExtLastBarTime = bar_time;
      return;
   }
   
   //--- 11. Compute C2 ONNX Features & Execute Inference
   double direction = (impulse_return_bps > 0.0) ? 1.0 : -1.0;
   double vol_ratio = current_std20 / (squeeze_threshold + 1e-8);
   
   // Compute normalized price path & Levy Area
   double p_win[];
   ArrayResize(p_win, InpVolLookback);
   double p_sum = 0.0;
   for(int k = 0; k < InpVolLookback; k++)
   {
      p_win[k] = closes[InpVolLookback - 1 - k]; // Chronological order
      p_sum += p_win[k];
   }
   double p_mean = p_sum / InpVolLookback;
   double p_sq = 0.0;
   for(int k = 0; k < InpVolLookback; k++)
      p_sq += (p_win[k] - p_mean) * (p_win[k] - p_mean);
   double p_std = MathSqrt(p_sq / InpVolLookback);
   if(p_std <= 1e-8) p_std = 1.0;
   
   double p_norm[];
   ArrayResize(p_norm, InpVolLookback);
   for(int k = 0; k < InpVolLookback; k++)
      p_norm[k] = (p_win[k] - p_mean) / p_std;
      
   double levy_area = CalcLevyArea(p_norm, InpVolLookback);
   
   // Compute return skewness and kurtosis
   double ret_sub[];
   ArrayResize(ret_sub, InpVolLookback);
   double r_sum = 0.0;
   for(int k = 0; k < InpVolLookback; k++)
   {
      ret_sub[k] = r_bps[InpVolLookback - 1 - k];
      r_sum += ret_sub[k];
   }
   double r_mean = r_sum / InpVolLookback;
   double skew20 = CalcSkewness(ret_sub, InpVolLookback, r_mean, current_std20);
   double kurt20 = CalcKurtosis(ret_sub, InpVolLookback, r_mean, current_std20);
   double spread_atr_ratio = (atr_pts > 0.0) ? (spread_pts / (atr_pts * 100.0 + 1e-8)) : 0.01;
   
   double out_prob = 1.0;
   if(InpUseONNXFilter && ExtModelLoaded)
   {
      bool pass_filter = EvaluateONNXFilter(vol_ratio, breakout_z, direction,
                                            levy_area, spread_atr_ratio, skew20, kurt20,
                                            out_prob);
      if(!pass_filter)
      {
         PrintFormat("[v3.00 ONNX FILTER REJECT] S1 Triggered but C2 P(Win)=%.2f%% < %.2f%% minimum. Trade Filtered Out!",
                     out_prob * 100.0, InpMinWinProbability * 100.0);
         ExtLastBarTime = bar_time;
         return;
      }
   }
   
   //--- 12. Execute S1 Trade with Dynamic Vol-Parity Sizing
   double lot = CalculateVolParityLot(current_std20, mid_price);
   
   double sl = 0.0;
   double tp = 0.0;
   if(InpUseHardTPSL && atr_vals[0] > 0.0)
   {
      if(direction > 0.0)
      {
         sl = ask - InpHardSL_ATR * atr_vals[0];
         tp = ask + InpHardTP_ATR * atr_vals[0];
      }
      else
      {
         sl = bid + InpHardSL_ATR * atr_vals[0];
         tp = bid - InpHardTP_ATR * atr_vals[0];
      }
   }

   string comment = StringFormat("v3_S1_%s_P%.0f", (direction > 0.0 ? "BUY" : "SEL"), out_prob * 100.0);
   bool success = false;
   if(direction > 0.0)
      success = ExtTrade.Buy(lot, _Symbol, ask, sl, tp, comment);
   else
      success = ExtTrade.Sell(lot, _Symbol, bid, sl, tp, comment);

   if(success)
   {
      PrintFormat("[v3.00 ENTRY EXECUTED] %s %s %.2f lots | Close=%.2f | std20=%.2f bps | Z=%.2f | P(Win)=%.2f%% | Ticket=#%I64u",
                  (direction > 0.0 ? "BUY" : "SELL"), _Symbol, lot, closes[0], current_std20, breakout_z, out_prob * 100.0, ExtTrade.ResultOrder());
   }
   else
   {
      PrintFormat("[v3.00 EXECUTION FAILED] Error = %d", GetLastError());
   }

   ExtLastBarTime = bar_time;
}
