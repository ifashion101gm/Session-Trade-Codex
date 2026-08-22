import MetaTrader5 as mt5
import json
from pathlib import Path
from datetime import datetime

def generate_report():
    if not mt5.initialize(login=1144985, password="***REMOVED_CREDENTIAL***", server="VTMarkets-Demo"):
        print(f"Failed to initialize MT5, error code: {mt5.last_error()}")
        return

    account = mt5.account_info()
    if account is None:
        print("Failed to get account info.")
        mt5.shutdown()
        return

    positions = mt5.positions_get()
    orders = mt5.orders_get()
    
    # Check outputs for recent analysis
    outputs_dir = Path("outputs")
    recent_analysis = []
    if outputs_dir.exists():
        date_folders = sorted([d for d in outputs_dir.iterdir() if d.is_dir()], reverse=True)
        if date_folders:
            for folder in sorted([d for d in date_folders[0].iterdir() if d.is_dir()], reverse=True):
                analysis_file = folder / "analysis.json"
                if analysis_file.exists():
                    try:
                        with open(analysis_file, 'r') as f:
                            data = json.load(f)
                            recent_analysis.append(data)
                    except Exception:
                        pass

    md_content = f"""# MT5 Active Status Report
*Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*

## 🏦 Account Overview
- **Balance:** {account.balance:,.2f} {account.currency}
- **Equity:** {account.equity:,.2f} {account.currency}
- **Free Margin:** {account.margin_free:,.2f} {account.currency}
- **Floating P/L:** {account.profit:,.2f} {account.currency}
- **Algorithmic Trading:** {"✅ ENABLED" if account.trade_allowed else "❌ DISABLED"}

## 📊 Active Strategies (Open Positions)
"""
    if positions:
        md_content += "| Ticket | Symbol | Type | Volume | Entry | SL | TP | Profit | Strategy (Comment) | Magic |\n"
        md_content += "|---|---|---|---|---|---|---|---|---|---|\n"
        for p in positions:
            p_type = "BUY" if p.type == 0 else "SELL"
            md_content += f"| {p.ticket} | {p.symbol} | {p_type} | {p.volume} | {p.price_open} | {p.sl} | {p.tp} | {p.profit} | {p.comment} | {p.magic} |\n"
    else:
        md_content += "*No active positions currently open.*\n"

    md_content += "\n## ⏳ Pending Orders (Limits/Stops)\n"
    if orders:
        md_content += "| Ticket | Symbol | Type | Volume | Setup Price | SL | TP | Strategy (Comment) | Magic |\n"
        md_content += "|---|---|---|---|---|---|---|---|---|\n"
        # Order types: 2=Buy Limit, 3=Sell Limit, 4=Buy Stop, 5=Sell Stop, etc.
        type_map = {2: 'BUY LIMIT', 3: 'SELL LIMIT', 4: 'BUY STOP', 5: 'SELL STOP', 6: 'BUY STOP LIMIT', 7: 'SELL STOP LIMIT'}
        for o in orders:
            o_type = type_map.get(o.type, f"TYPE {o.type}")
            md_content += f"| {o.ticket} | {o.symbol} | {o_type} | {o.volume_initial} | {o.price_open} | {o.sl} | {o.tp} | {o.comment} | {o.magic} |\n"
    else:
        md_content += "*No pending orders currently placed.*\n"

    md_content += "\n## 📁 Recent Analysis Outputs (Today)\n"
    if recent_analysis:
        for run in recent_analysis[:5]:
            md_content += f"- **{run.get('timestamp', 'N/A')}**: {run.get('symbol', 'N/A')} - `{run.get('status', 'N/A')}` (Strategy: {run.get('strategy_id', 'N/A')})\n"
    else:
        md_content += "*No analysis runs found for today.*\n"

    with open("ACTIVE_STATUS.md", "w", encoding="utf-8") as f:
        f.write(md_content)
        
    print("✅ Status report generated: ACTIVE_STATUS.md")
    mt5.shutdown()

if __name__ == "__main__":
    generate_report()
