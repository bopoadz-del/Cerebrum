"""
ViaBTC Mining Pool Integration
Real-time miner monitoring and status checks.
"""

import time
import hmac
import hashlib
import json
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

import httpx

from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger(__name__)


@dataclass
class MinerStatus:
    """Individual miner status."""
    worker_id: str
    status: str  # "active", "inactive", "dead"
    hash_rate: float  # TH/s
    accept_count: int
    reject_count: int
    last_share_time: Optional[datetime]
    uptime_minutes: int


@dataclass
class MiningStatus:
    """Overall mining account status."""
    account_id: str
    coin: str
    total_workers: int
    active_workers: int
    inactive_workers: int
    dead_workers: int
    total_hash_rate: float  # TH/s
    miners: List[MinerStatus]
    updated_at: datetime


class ViaBTCClient:
    """
    ViaBTC Mining Pool API Client
    
    API Documentation: https://www.viabtc.com/support/api_doc
    """
    
    BASE_URL = "https://pool.viabtc.com/res/openapi/v1"
    
    def __init__(self, api_key: str, api_secret: str = ""):
        self.api_key = api_key
        self.api_secret = api_secret
        self.client = httpx.Client(
            timeout=30.0,
            follow_redirects=True,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "Cerebrum-Miner-Monitor/1.0"
            }
        )
    
    def _generate_signature(self, query_string: str) -> str:
        """Generate HMAC-SHA256 signature for API requests."""
        if not self.api_secret:
            return ""
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None, signed: bool = False) -> Dict:
        """Make authenticated request to ViaBTC API."""
        url = f"{self.BASE_URL}{endpoint}"
        params = params or {}
        
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Cerebrum-Miner-Monitor/1.0",
            "X-API-KEY": self.api_key
        }
        
        if signed and self.api_secret:
            # For signed endpoints, use tonce parameter
            params['tonce'] = int(time.time() * 1000)
            query_string = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
            headers['X-SIGNATURE'] = self._generate_signature(query_string)
        
        try:
            response = self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            # Debug: log the raw response
            logger.info(f"ViaBTC raw response: {data}")
            return data
        except httpx.HTTPError as e:
            logger.error(f"ViaBTC API error: {e}")
            raise
    
    def get_mining_status(self, coin: str = "BTC") -> MiningStatus:
        """
        Get mining status for a specific coin.
        Uses /hashrate endpoint which returns active/unactive worker counts.
        """
        try:
            # ViaBTC API v1: /hashrate endpoint returns summary data
            response = self._make_request("/hashrate", {"coin": coin}, signed=False)
            
            if response.get("code") != 0:
                error_msg = response.get("message", "Unknown error")
                logger.error(f"ViaBTC API error: {error_msg}")
                raise Exception(f"ViaBTC API error: {error_msg}")
            
            data = response.get("data", {})
            active = int(data.get("active_workers", 0))
            inactive = int(data.get("unactive_workers", 0))
            total = active + inactive
            
            # Convert hashrate from H/s to TH/s
            hash_10min = float(data.get("hashrate_10min", 0)) / 1e12
            
            # Try to get subaccount list for more details (signed endpoint)
            miners = []
            try:
                sub_resp = self._make_request("/account/sub", {}, signed=True)
                if sub_resp.get("code") == 0:
                    sub_data = sub_resp.get("data", {})
                    # Note: Individual worker details not available in public API v1
                    # We create summary miners from subaccount data if available
                    sub_list = sub_data.get("data", [])
                    for sub in sub_list:
                        miners.append(MinerStatus(
                            worker_id=sub.get("name", "unknown"),
                            status="active" if active > 0 else "unknown",
                            hash_rate=hash_10min / max(len(sub_list), 1),
                            accept_count=0,
                            reject_count=0,
                            last_share_time=None,
                            uptime_minutes=0
                        ))
            except Exception as e:
                logger.warning(f"Could not fetch subaccount details: {e}")
            
            # If no subaccount data, create a single summary entry
            if not miners:
                miners.append(MinerStatus(
                    worker_id=f"{coin}_workers",
                    status="active" if active > 0 else "unknown",
                    hash_rate=hash_10min,
                    accept_count=0,
                    reject_count=0,
                    last_share_time=None,
                    uptime_minutes=0
                ))
            
            return MiningStatus(
                account_id=self.api_key[:8] + "...",
                coin=coin,
                total_workers=total,
                active_workers=active,
                inactive_workers=inactive,
                dead_workers=0,
                total_hash_rate=hash_10min,
                miners=miners,
                updated_at=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Failed to get mining status: {e}")
            raise
    
    def get_profit(self, coin: str = "BTC", days: int = 1) -> Dict:
        """Get mining profit statistics."""
        try:
            response = self._make_request("/profit", {
                "coin": coin,
                "days": days
            })
            
            if response.get("code") != 0:
                return {"error": response.get("message", "Unknown error")}
            
            return response.get("data", {})
            
        except Exception as e:
            logger.error(f"Failed to get profit: {e}")
            return {"error": str(e)}
    
    def get_hashrate_history(self, coin: str = "BTC", duration: str = "24h") -> Dict:
        """Get hashrate history for charting."""
        try:
            response = self._make_request("/hashrate/history", {
                "coin": coin,
                "duration": duration
            })
            
            if response.get("code") != 0:
                return {"error": response.get("message", "Unknown error")}
            
            return response.get("data", {})
            
        except Exception as e:
            logger.error(f"Failed to get hashrate history: {e}")
            return {"error": str(e)}
    
    def check_all_coins(self) -> Dict[str, MiningStatus]:
        """Check mining status for all supported coins."""
        coins = ["BTC", "BCH", "BSV", "LTC", "ETH", "ETC", "ZEC", "DASH", "XMR"]
        results = {}
        
        for coin in coins:
            try:
                status = self.get_mining_status(coin)
                if status.total_workers > 0:
                    results[coin] = status
            except Exception as e:
                logger.warning(f"Failed to check {coin}: {e}")
        
        return results


# Singleton instance
_viabtc_client = None

def get_viabtc_client() -> ViaBTCClient:
    """Get or create ViaBTC client singleton."""
    global _viabtc_client
    if _viabtc_client is None:
        # API credentials loaded from environment or settings
        api_key = getattr(settings, 'VIABTC_API_KEY', None) or "3fe4de232925307307611c973225eddb"
        api_secret = getattr(settings, 'VIABTC_API_SECRET', None) or "231c5f2b7f68d50b23204b6f6300ff3f0ad342fbcbf36076b4831bd733b9753c"
        _viabtc_client = ViaBTCClient(api_key, api_secret)
    return _viabtc_client


async def check_miner_status() -> Dict:
    """
    Convenience function to check all miner status.
    Returns formatted dict for display/logging.
    """
    client = get_viabtc_client()
    
    try:
        # Check all coins
        all_status = client.check_all_coins()
        
        if not all_status:
            return {
                "status": "error",
                "message": "No active mining found for any coin",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # Format results
        summary = []
        for coin, status in all_status.items():
            summary.append({
                "coin": coin,
                "total_workers": status.total_workers,
                "active": status.active_workers,
                "inactive": status.inactive_workers,
                "dead": status.dead_workers,
                "hash_rate_th": round(status.total_hash_rate, 2),
                "miners": [
                    {
                        "id": m.worker_id,
                        "status": m.status,
                        "hash_rate_th": round(m.hash_rate, 2),
                        "accept": m.accept_count,
                        "reject": m.reject_count
                    }
                    for m in status.miners
                ]
            })
        
        return {
            "status": "success",
            "data": summary,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Miner status check failed: {e}")
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }
