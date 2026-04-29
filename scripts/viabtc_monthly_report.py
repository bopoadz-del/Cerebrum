#!/usr/bin/env python3
"""
ViaBTC Monthly Mining Report
Fetches daily records for electricity consumption tracking
"""

import requests
import hmac
import hashlib
import time
import json
from urllib.parse import urlencode
from datetime import datetime, timedelta
from collections import defaultdict

# Credentials
API_KEY = "57c66210d1442a6615833b1e470a7cdd"
API_SECRET = "f67e6fc9f46555e60f1720643aa1065973ee22248d767f53856a771313f77cab"
SUB_ACCOUNT = "Cymahmoud101"
COIN = "BTC"
BASE_URL = "https://pool.viabtc.com"


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
    """Fetch all pages of paginated data"""
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
        if page > 20:  # Safety limit
            break
    return all_data


def get_daily_records():
    """Fetch all daily hashrate and profit records"""
    hashrate = fetch_all_pages('hashrate/history', {'coin': COIN})
    profit = fetch_all_pages('profit/history', {'coin': COIN, 'sub_name': SUB_ACCOUNT})
    return hashrate, profit


def format_report(hashrate_data, profit_data):
    """Format monthly report for electricity tracking"""
    # Merge by date
    by_date = {}
    
    for h in hashrate_data:
        date = h['date']
        by_date[date] = {
            'hashrate': float(h.get('hashrate', 0)) / 1e12,  # Convert to TH/s
            'reject_rate': float(h.get('reject_rate', 0)) * 100,
            'pps': 0, 'pplns': 0, 'solo': 0, 'total_btc': 0
        }
    
    for p in profit_data:
        date = p['date']
        if date not in by_date:
            by_date[date] = {'hashrate': 0, 'reject_rate': 0, 'pps': 0, 'pplns': 0, 'solo': 0, 'total_btc': 0}
        by_date[date]['pps'] = float(p.get('pps_profit', 0))
        by_date[date]['pplns'] = float(p.get('pplns_profit', 0))
        by_date[date]['solo'] = float(p.get('solo_profit', 0))
        by_date[date]['total_btc'] = float(p.get('total_profit', 0))
    
    # Group by month
    by_month = defaultdict(list)
    for date in sorted(by_date.keys()):
        month_key = date[:7]  # "2026-04"
        by_month[month_key].append({
            'date': date,
            **by_date[date]
        })
    
    lines = []
    lines.append("=" * 80)
    lines.append("VIA BTC MONTHLY MINING REPORT")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("=" * 80)
    
    for month in sorted(by_month.keys(), reverse=True):
        days = by_month[month]
        total_btc = sum(d['total_btc'] for d in days)
        avg_hashrate = sum(d['hashrate'] for d in days) / len(days) if days else 0
        avg_reject = sum(d['reject_rate'] for d in days) / len(days) if days else 0
        
        lines.append(f"\n{'─' * 80}")
        lines.append(f"📅 {month}  |  {len(days)} days of data")
        lines.append(f"{'─' * 80}")
        lines.append(f"  Total Mined:      {total_btc:.8f} BTC")
        lines.append(f"  Avg Hashrate:      {avg_hashrate:.2f} TH/s")
        lines.append(f"  Avg Reject Rate:   {avg_reject:.2f}%")
        lines.append(f"")
        lines.append(f"  Daily Breakdown:")
        lines.append(f"  {'Date':12s} {'Hashrate':>12s} {'BTC':>12s} {'Reject%':>8s}")
        lines.append(f"  {'-'*12} {'-'*12} {'-'*12} {'-'*8}")
        
        for d in reversed(days):  # Most recent first
            lines.append(f"  {d['date']:12s} {d['hashrate']:>10.2f}  {d['total_btc']:>10.8f}  {d['reject_rate']:>6.2f}")
    
    return '\n'.join(lines)


if __name__ == '__main__':
    print("Fetching daily records from ViaBTC...")
    hashrate, profit = get_daily_records()
    
    report = format_report(hashrate, profit)
    print(report)
    
    # Save to file
    report_path = f"/tmp/viabtc_monthly_report_{datetime.now().strftime('%Y%m%d')}.txt"
    with open(report_path, 'w') as f:
        f.write(report)
    print(f"\n📄 Report saved: {report_path}")
    
    # Also save raw JSON for further analysis
    raw_path = f"/tmp/viabtc_raw_{datetime.now().strftime('%Y%m%d')}.json"
    with open(raw_path, 'w') as f:
        json.dump({'hashrate_history': hashrate, 'profit_history': profit}, f, indent=2)
    print(f"📊 Raw data saved: {raw_path}")
