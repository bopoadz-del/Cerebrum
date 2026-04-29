#!/usr/bin/env python3
"""
ViaBTC Electricity Cost Calculator
Tracks mining profit vs electricity cost
"""

import requests
import hmac
import hashlib
import time
import json
from urllib.parse import urlencode
from datetime import datetime, timedelta
from collections import defaultdict

# ViaBTC Credentials
API_KEY = "57c66210d1442a6615833b1e470a7cdd"
API_SECRET = "f67e6fc9f46555e60f1720643aa1065973ee22248d767f53856a771313f77cab"
SUB_ACCOUNT = "Cymahmoud101"
COIN = "BTC"
BASE_URL = "https://pool.viabtc.com"

# User settings
ELECTRICITY_RATE = 0.06  # $0.06 per kWh


def signed_request(endpoint, extra_params=None):
    args = {'tonce': int(time.time() * 1000)}
    if extra_params:
        args.update(extra_params)
    qs = urlencode(args)
    sig = hmac.new(API_SECRET.encode('utf-8'), qs.encode('utf-8'), hashlib.sha256).hexdigest()
    headers = {'X-API-KEY': API_KEY, 'X-SIGNATURE': sig}
    url = f"{BASE_URL}/res/openapi/v1/{endpoint}?{qs}"
    r = requests.get(url, headers=headers, timeout=15)
    return r.json()


def fetch_all_pages(endpoint, params):
    all_data = []
    page = 1
    while True:
        params['pageno'] = page
        result = signed_request(endpoint, params)
        if result.get('code') != 0:
            break
        data = result.get('data', {})
        items = data.get('data', [])
        all_data.extend(items)
        if not data.get('has_next', False):
            break
        page += 1
        if page > 20:
            break
    return all_data


def get_btc_price():
    """Get current BTC price in USD"""
    try:
        r = requests.get('https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd', timeout=10)
        return r.json()['bitcoin']['usd']
    except:
        return 95000  # Fallback price


def calculate_monthly(kwh_used, month=None):
    """
    Calculate mining economics for a given month
    
    Args:
        kwh_used: Total kWh consumed for the month
        month: Month to analyze (e.g., '2026-04'). None = current month
    """
    btc_price = get_btc_price()
    
    # Fetch ViaBTC data for the month
    profit_data = fetch_all_pages('profit/history', {'coin': COIN, 'sub_name': SUB_ACCOUNT})
    hashrate_data = fetch_all_pages('hashrate/history', {'coin': COIN})
    
    # Filter to requested month
    if month:
        profit_data = [p for p in profit_data if p['date'].startswith(month)]
        hashrate_data = [h for h in hashrate_data if h['date'].startswith(month)]
    
    days_with_data = len(profit_data)
    total_btc = sum(float(p.get('total_profit', 0)) for p in profit_data)
    
    # Electricity cost
    electricity_cost = kwh_used * ELECTRICITY_RATE
    
    # Revenue
    revenue = total_btc * btc_price
    
    # Profit/Loss
    profit = revenue - electricity_cost
    profit_margin = (profit / revenue * 100) if revenue > 0 else 0
    
    # Efficiency
    kwh_per_btc = kwh_used / total_btc if total_btc > 0 else 0
    cost_per_btc = kwh_per_btc * ELECTRICITY_RATE
    
    # Avg daily
    avg_daily_btc = total_btc / days_with_data if days_with_data > 0 else 0
    avg_daily_kwh = kwh_used / 30  # Assuming 30-day month for projection
    
    return {
        'month': month or datetime.now().strftime('%Y-%m'),
        'days_data': days_with_data,
        'btc_price': btc_price,
        'total_btc': total_btc,
        'kwh_used': kwh_used,
        'electricity_cost': electricity_cost,
        'revenue_usd': revenue,
        'profit_usd': profit,
        'profit_margin': profit_margin,
        'kwh_per_btc': kwh_per_btc,
        'cost_per_btc': cost_per_btc,
        'avg_daily_btc': avg_daily_btc,
        'avg_daily_kwh': avg_daily_kwh,
    }


def format_report(calc):
    lines = []
    lines.append("=" * 70)
    lines.append(f"⚡ MINING ECONOMICS REPORT — {calc['month']}")
    lines.append(f"Electricity Rate: ${ELECTRICITY_RATE}/kWh | BTC Price: ${calc['btc_price']:,.0f}")
    lines.append("=" * 70)
    lines.append("")
    lines.append(f"📊 PRODUCTION")
    lines.append(f"  Days with data:     {calc['days_data']}")
    lines.append(f"  Total BTC mined:    {calc['total_btc']:.8f} BTC")
    lines.append(f"  Avg daily:          {calc['avg_daily_btc']:.8f} BTC/day")
    lines.append("")
    lines.append(f"⚡ ELECTRICITY")
    lines.append(f"  kWh used:           {calc['kwh_used']:,.0f} kWh")
    lines.append(f"  Cost:               ${calc['electricity_cost']:,.2f}")
    lines.append(f"  Avg daily usage:    {calc['avg_daily_kwh']:,.0f} kWh/day")
    lines.append(f"  Efficiency:         {calc['kwh_per_btc']:,.0f} kWh per BTC")
    lines.append(f"  Cost per BTC:       ${calc['cost_per_btc']:,.2f}")
    lines.append("")
    lines.append(f"💰 ECONOMICS")
    lines.append(f"  Revenue:            ${calc['revenue_usd']:,.2f}")
    lines.append(f"  Electricity Cost:   ${calc['electricity_cost']:,.2f}")
    if calc['profit_usd'] >= 0:
        lines.append(f"  PROFIT:             ${calc['profit_usd']:,.2f} ✅")
    else:
        lines.append(f"  LOSS:               ${calc['profit_usd']:,.2f} ❌")
    lines.append(f"  Margin:             {calc['profit_margin']:.1f}%")
    lines.append("")
    lines.append("=" * 70)
    return '\n'.join(lines)


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python viabtc_electricity.py <kWh_used> [YYYY-MM]")
        print("  kWh_used  = Your electricity meter reading for the month")
        print("  YYYY-MM   = Month to analyze (default: current month)")
        print("")
        print("Example: python viabtc_electricity.py 45000 2026-04")
        print("  → Analyzes April 2026 with 45,000 kWh consumed")
        sys.exit(1)
    
    kwh = float(sys.argv[1])
    month = sys.argv[2] if len(sys.argv) > 2 else None
    
    print(f"Fetching ViaBTC data for {month or 'current month'}...")
    result = calculate_monthly(kwh, month)
    
    report = format_report(result)
    print(report)
    
    # Save
    path = f"/tmp/viabtc_economics_{result['month']}.txt"
    with open(path, 'w') as f:
        f.write(report)
    print(f"📄 Saved: {path}")
