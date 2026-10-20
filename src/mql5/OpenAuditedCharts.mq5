//+------------------------------------------------------------------+
//|                                           OpenAuditedCharts.mq5 |
//|                             Copyright 2026, Direction Recherche Quant |
//|                                      https://github.com/Christ-yavn/bot-quant- |
//+------------------------------------------------------------------+
#property copyright   "Copyright 2026, Direction Recherche Quant"
#property link        "https://github.com/Christ-yavn/bot-quant-"
#property version     "1.00"
#property description "Ouvre automatiquement les 5 graphiques audites v8.10 Spike Hunter"
#property script_show_inputs false

void OnStart()
{
   string audited_symbols[] = {
      "Crash 600 Index",
      "Crash 900 Index",
      "Boom 900 Index",
      "Boom 600 Index",
      "Crash 1000 Index"
   };

   Print("========================================================================");
   Print("[OpenAuditedCharts] Ouverture des graphiques audites v8.10 en cours...");

   for(int i = 0; i < ArraySize(audited_symbols); i++)
   {
      string sym = audited_symbols[i];
      SymbolSelect(sym, true);

      bool already_open = false;
      long cid = ChartFirst();
      while(cid >= 0)
      {
         if(ChartSymbol(cid) == sym)
         {
            already_open = true;
            break;
         }
         cid = ChartNext(cid);
      }

      if(!already_open)
      {
         long new_cid = ChartOpen(sym, PERIOD_M1);
         if(new_cid > 0)
            PrintFormat("[OpenAuditedCharts] +++ Graphique M1 ouvert avec succes pour %s (Chart ID: %I64d) +++", sym, new_cid);
         else
            PrintFormat("[OpenAuditedCharts] --- Echec ouverture %s (Code: %d) ---", sym, GetLastError());
      }
      else
      {
         PrintFormat("[OpenAuditedCharts] === Graphique %s deja ouvert dans le terminal ===", sym);
      }
   }
   Print("[OpenAuditedCharts] Termine. Tous les graphiques audites sont prets.");
}
