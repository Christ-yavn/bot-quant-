"""
MONITOR DUAL BOTS: Real-Time Performance & Accounting Engine
Track 1: DerivBoomCrashHFT (v8.20) - Magic 20261020 / Boom & Crash
Track 2: Deriv_VolSqueeze_Breakout_EA (v3.00 ONNX) - Magic 20261022 / Volatility 25 (1s)
"""
import MetaTrader5 as mt5
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

def generate_report():
    if not mt5.initialize():
        print("Erreur : Impossible d'initialiser MetaTrader 5.")
        return

    acc = mt5.account_info()
    if not acc:
        print("Erreur : Impossible de lire les informations du compte.")
        mt5.shutdown()
        return

    print("=" * 78)
    print(f"RAPPORT INSTITUTIONNEL D'EXÉCUTION EN DIRECT - COMPTE {acc.login}")
    print(f"Date/Heure : {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')} | Solde : {acc.balance:.2f} USD | Équité : {acc.equity:.2f} USD")
    print("=" * 78)

    # 1. Open Positions
    open_pos = mt5.positions_get()
    print("\n--- POSITIONS ACTUELLEMENT OUVERTES ---")
    if open_pos and len(open_pos) > 0:
        pos_df = pd.DataFrame(list(open_pos), columns=open_pos[0]._asdict().keys())
        for _, p in pos_df.iterrows():
            bot_tag = "Track 1 (Boom/Crash v8)" if p['magic'] in [20261019, 20261020] else ("Track 2 (Vol 25 ONNX v3)" if p['magic'] == 20261022 else f"Autre ({p['magic']})")
            t_type = "BUY" if p['type'] == 0 else "SELL"
            print(f"Ticket #{p['ticket']} | {bot_tag} | {p['symbol']} | {t_type} {p['volume']:.2f} lots | Prix: {p['price_open']:.2f} | PnL: {p['profit']:+.2f} USD | Comment: {p['comment']}")
    else:
        print("Aucune position ouverte en ce moment.")

    # 2. Closed Deals since yesterday
    from_date = datetime.now() - timedelta(days=2)
    to_date = datetime.now() + timedelta(days=1)
    deals = mt5.history_deals_get(from_date, to_date)
    mt5.shutdown()

    if not deals or len(deals) == 0:
        print("\nAucun trade clôturé au cours des dernières 48 heures.")
        return

    df = pd.DataFrame(list(deals), columns=deals[0]._asdict().keys())
    # Filter only exit deals (entry == 1 means deal OUT)
    trade_deals = df[(df['entry'] == 1) & (df['profit'] != 0.0)]
    
    # Classify by Bot
    def classify_bot(row):
        m = row['magic']
        s = str(row['symbol'])
        if m == 20261022 or 'Volatility 25' in s or 'Volatility 75' in s:
            return "Track 2 : Volatility Squeeze v3.00 (ONNX)"
        elif m in [20261019, 20261020] or 'Boom' in s or 'Crash' in s:
            return "Track 1 : Boom/Crash HFT v8.20 (Convexité)"
        else:
            return f"Non répertorié (Magic {m})"

    if len(trade_deals) > 0:
        trade_deals = trade_deals.copy()
        trade_deals['Bot'] = trade_deals.apply(classify_bot, axis=1)

        print("\n--- PERFORMANCE DÉTAILLÉE PAR BOT ---")
        for bot_name, group in trade_deals.groupby('Bot'):
            total_trades = len(group)
            wins = len(group[group['profit'] > 0])
            losses = len(group[group['profit'] < 0])
            win_rate = (wins / total_trades) * 100.0 if total_trades > 0 else 0.0
            tot_pnl = group['profit'].sum()
            gross_win = group[group['profit'] > 0]['profit'].sum()
            gross_loss = abs(group[group['profit'] < 0]['profit'].sum())
            pf = (gross_win / gross_loss) if gross_loss > 0 else (99.0 if gross_win > 0 else 0.0)
            
            print(f"\n[{bot_name}]")
            print(f"  * Total Trades      : {total_trades}")
            print(f"  * Win Rate          : {win_rate:.1f}% ({wins} G / {losses} P)")
            print(f"  * PnL Total         : {tot_pnl:+.2f} USD")
            print(f"  * Profit Factor     : {pf:.2f}")
            print(f"  * Gain Moyen/Trade  : {tot_pnl/total_trades:+.2f} USD")
            
            print("  * Décomposition par Symbole :")
            for sym, s_grp in group.groupby('symbol'):
                s_tot = len(s_grp)
                s_pnl = s_grp['profit'].sum()
                s_win = len(s_grp[s_grp['profit'] > 0])
                print(f"      - {sym:20s}: {s_tot:3d} trades | PnL = {s_pnl:+7.2f} USD | WR = {(s_win/s_tot)*100:5.1f}%")
    else:
        print("\nAucun deal de clôture trouvé dans l'intervalle.")

if __name__ == "__main__":
    generate_report()
