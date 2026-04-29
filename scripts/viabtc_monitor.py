#!/usr/bin/env python3
"""
ViaBTC Mining Pool Monitor
Fetches hashrate and profit data for Cymahmoud101 sub-account
"""

import requests
import hmac
import hashlib
import time
import json
from urllib.parse import urlencode

# Credentials
API_KEY = "57c66210d1442a6615833b1e470a7cdd"
API_SECRET = "f67e6fc9f46555e60f1720643aa1065973ee22248d767f53856a771313f77cab"
SUB_ACCOUNT = "Cymahmoud101"
COIN = "BTC"
BASE_URL = "https://pool.viabtc.com"


def signed_request(endpoint, extra_params=None):
    """Make a signed request to ViaBTC API"""
    args = {'tonce': int(time.time() * 1000)}
    if extra_params:
        args.update(extra_params)
    
    query_string = urlencode(args)
    signature = hmac.new(
        API_SECRET.encode('utf-8'),
        query_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    headers = {
        'X-API-KEY': API_KEY,
        'X-SIGNATURE': signature
    }
    
    url = f"{BASE_URL}/res/openapi/v1/{endpoint}?{query_string}"
    response = requests.get(url, headers=headers, timeout=15)
    return response.json()


def unsigned_request(endpoint, params=None):
    """Make an unsigned request (just needs API key)"""
    headers = {'X-API-KEY': API_KEY}
    url = f"{BASE_URL}/res/openapi/v1/{endpoint}"
    response = requests.get(url, params=params, headers=headers, timeout=15)
    return response.json()


def get_status():
    """Get complete mining status"""
    # Hashrate (unsigned)
    hashrate = unsigned_request('hashrate', {'coin': COIN})
    
    # Profit (signed)
    profit = signed_request('profit', {'coin': COIN, 'sub_name': SUB_ACCOUNT})
    
    return {
        'hashrate': hashrate,
        'profit': profit,
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
    }


def format_status(data):
    """Format status for display"""
    hr = data['hashrate'].get('data', {})
    pr = data['profit'].get('data', {})
    
    # Convert hashrate from internal units to TH/s
    # ViaBTC returns raw hash values, need to divide appropriately
    hashrate_10min = int(hr.get('hashrate_10min', 0)) / 1e12
    hashrate_1h = int(hr.get('hashrate_1hour', 0)) / 1e12
    hashrate_24h = int(hr.get('hashrate_24hour', 0)) / 1e12
    
    lines = [
        f"📊 ViaBTC Mining Status - {data['timestamp']}",
        f"",
        f"Workers: {hr.get('active_workers', '?')} active, {hr.get('unactive_workers', '?')} inactive",
        f"Hashrate: {hashrate_10min:.2f} TH/s (10min) | {hashrate_1h:.2f} TH/s (1h) | {hashrate_24h:.2f} TH/s (24h)",
        f"",
        f"💰 Profit:",
        f"  Total: {pr.get('total_profit', '0')} BTC",
        f"  PPS:   {pr.get('pps_profit', '0')} BTC",
        f"  PPLNS: {pr.get('pplns_profit', '0')} BTC",
    ]
    
    return '\n'.join(lines)


if __name__ == '__main__':
    status = get_status()
    print(format_status(status))
    
    # Also save to file
    with open('/tmp/viabtc_status.json', 'w') as f:
        json.dump(status, f, indent=2)
