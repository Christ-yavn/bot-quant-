import os

file_path = os.path.abspath('src/mql5/Deriv_VolSqueeze_Breakout_EA_v3.mq5')
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update versions
content = content.replace('Release        : v3.50 (Omni-Basket & Retractable UI L99 Prod)', 'Release        : v3.51 (Omni-Basket & Retractable UI L99 Prod - Surgical Patch v3.51)')
content = content.replace('#property version   "3.50"', '#property version   "3.51"')
content = content.replace('QuantPod v3.50 - Omni-Basket 8-Assets', 'QuantPod v3.51 - Omni-Basket 8-Assets')
content = content.replace('TrailingLock      = true;                          // Enable Dynamic Profit Excursion Lock (Hardened v3.31/v3.50)', 'TrailingLock      = true;                          // Enable Dynamic Profit Excursion Lock (Hardened v3.31/v3.51)')
content = content.replace('//| Render Real-Time Graphical Dashboard on Chart (v3.50 Retractable)|', '//| Render Real-Time Graphical Dashboard on Chart (v3.51 Retractable)|')
content = content.replace('⚡ QP v3.50 [', '⚡ QP v3.51 [')
content = content.replace('⚡ QUANT-POD v3.50 ELITE — [', '⚡ QUANT-POD v3.51 ELITE — [')
content = content.replace('//| Position Management & Strict Time-Stop Engine (v3.50)            |', '//| Position Management & Strict Time-Stop Engine (v3.51)            |')
content = content.replace('[v3.50 ', '[v3.51 ')

# 2. Patch Bug Subtil A in UpdateMarketTelemetry
old_telemetry_block = """   double current_std20 = rolling_std[0];
   // BUG N°2 FIX: pre_breakout_std20 uses rolling_std[1] (volatility of 20 bars prior to breakout bar)
   double pre_breakout_std20 = (ArraySize(rolling_std) > 1) ? rolling_std[1] : rolling_std[0];

   double sorted_std[];
   ArrayCopy(sorted_std, rolling_std);
   ArraySort(sorted_std);
   int q_index = (int)MathFloor(ExtEffSqueezeQ * (InpQuantileWindow - 1));
   if(q_index < 0) q_index = 0;
   if(q_index >= InpQuantileWindow) q_index = InpQuantileWindow - 1;
   double squeeze_threshold = sorted_std[q_index];

   double breakout_z = (pre_breakout_std20 > 1e-6) ? (MathAbs(r_bps[0]) / pre_breakout_std20) : 0.0;

   // Momentum Z-Score calculation over InpVolLookback (20)
   double mom_sum = 0.0;
   for(int k = 0; k < InpVolLookback; k++)
      mom_sum += r_bps[k];
   double denom = current_std20 * MathSqrt((double)InpVolLookback);
   double mom_z = (denom > 1e-6) ? (mom_sum / denom) : 0.0;"""

new_telemetry_block = """   double current_std20 = rolling_std[0];
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
   double mom_z = (denom > 1e-9) ? (mom_sum / denom) : 0.0;"""

assert old_telemetry_block in content, "old_telemetry_block not found in file!"
content = content.replace(old_telemetry_block, new_telemetry_block)

# 3. Patch ExtLastStd20 assignment
old_assign = """   ExtLastStd20     = current_std20;
   ExtLastSqueezeQ  = squeeze_threshold;"""

new_assign = """   ExtLastStd20     = pre_breakout_std20; // v3.51 Surgical Patch: Evaluates true pre-breakout volatility!
   ExtLastSqueezeQ  = squeeze_threshold;"""

assert old_assign in content, "old_assign not found in file!"
content = content.replace(old_assign, new_assign)

# 4. Patch Bug Subtil B in RenderVolSqueezeDashboard
old_lock = """      pos_bars = iBarShift(_Symbol, ExtEffTimeframe, pos_time, false);
      pos_lock_str = (ExtPosition.StopLoss() > 0.0) ? "VERROUILLÉ" : "ACTIF (Shift=1)";"""

new_lock = """      pos_bars = iBarShift(_Symbol, ExtEffTimeframe, pos_time, false);

      // BUG SUBTIL B FIX (v3.51): Accurately detect if SL has been trailed past entry price
      double cur_sl = ExtPosition.StopLoss();
      double open_px = ExtPosition.PriceOpen();
      bool is_profit_locked = false;
      if(ExtPosition.PositionType() == POSITION_TYPE_BUY)
         is_profit_locked = (cur_sl > open_px);
      else
         is_profit_locked = (cur_sl > 0.0 && cur_sl < open_px);

      pos_lock_str = is_profit_locked ? "VERROUILLÉ (+0.20 ATR)" : "ARMÉ (Seuil +1.20 ATR)";"""

assert old_lock in content, "old_lock not found in file!"
content = content.replace(old_lock, new_lock)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Successfully applied v3.51 surgical patches!")
