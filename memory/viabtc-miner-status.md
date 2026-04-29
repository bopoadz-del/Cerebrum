# ViaBTC Miner Status Log

## 2026-04-23 19:39 (Asia/Shanghai)

**Status:** ✅ CONNECTED — API working perfectly

**What was wrong before:**
1. Using `www.viabtc.com` instead of `pool.viabtc.com`
2. Signature was sent as query param (`sign=`) instead of header (`X-SIGNATURE`)
3. Missing `tonce` parameter (needs millisecond timestamp)
4. Secret key was incomplete (39 chars instead of 64)

**Correct auth method:**
- Headers: `X-API-KEY` + `X-SIGNATURE` 
- Sign: HMAC-SHA256 of `urlencode(params)` using secret as string key
- Must include `tonce=int(time.time()*1000)` in params

**Working Endpoints:**
| Endpoint | Auth | Data |
|----------|------|------|
| `/hashrate` | Unsigned (X-API-KEY only) | Worker count, hashrate |
| `/profit` | Signed | Total earnings, PPS/PPLNS breakdown |
| `/account/sub` | Signed | Sub-account list |
| `/account` | Unsigned | Account info |

**Not Available:**
- Individual worker names/status — ViaBTC OpenAPI v1 doesn't expose per-worker details
- Need web dashboard or newer API for individual miner diagnostics

**Current Status:**
- **Workers:** 19 active, 0 inactive
- **Hashrate:** ~4.5 PH/s (10min avg), ~4.6 PH/s (1h), ~4.5 PH/s (24h)
- **Total Profit:** 0.22846879 BTC
  - PPS: 0.22712443 BTC
  - PPLNS: 0.00134436 BTC
  - Solo: 0 BTC

**Files:**
- Monitor script: `scripts/viabtc_monitor.py`
- Credentials: `.env.viabtc`

---

## 2026-04-24 13:08 (Asia/Shanghai)

**Status:** ✅ ALL SYSTEMS GREEN

**Worker Status:**
- **Online:** 19 miners
- **Offline:** 0 miners
- **Total Offline Hours:** 0

**Hashrate:**
- 10min avg: 4477.33 TH/s (~4.48 PH/s)
- 1h avg: 4525.49 TH/s (~4.53 PH/s)
- 24h avg: 4505.27 TH/s (~4.51 PH/s)

**Profit (cumulative):**
- Total: 0.22992248 BTC
- PPS: 0.22856324 BTC
- PPLNS: 0.00135924 BTC
- Solo: 0 BTC

**Alert:** 🟢 None — all miners operational

---

## 2026-04-25 13:03 (Asia/Shanghai)

**Status:** ✅ ALL SYSTEMS GREEN

**Worker Status:**
- **Online:** 19 miners
- **Offline:** 0 miners
- **Total Offline Hours:** 0

**Hashrate:**
- 10min avg: 4537.38 TH/s (~4.54 PH/s)
- 1h avg: 4550.51 TH/s (~4.55 PH/s)
- 24h avg: 4524.49 TH/s (~4.52 PH/s)

**Profit (cumulative):**
- Total: 0.23197618 BTC
- PPS: 0.23060752 BTC
- PPLNS: 0.00136866 BTC
- Solo: 0 BTC

**24h Change:** +0.00205370 BTC (+$208 approx)

**Alert:** 🟢 None — all miners operational

---

**Next Steps:**
- Set up cron to run monitor script daily/hourly
- Consider building a dashboard or alert system
- If per-worker monitoring needed, investigate ViaBTC's newer API or web scraping approach

---

## 2026-04-26 13:04 (Asia/Shanghai)

**Status:** ✅ ALL SYSTEMS GREEN

**Worker Status:**
- **Online:** 19 miners
- **Offline:** 0 miners
- **Total Offline Hours:** 0

**Hashrate:**
- 10min avg: 4552.39 TH/s (~4.55 PH/s)
- 1h avg: 4530.50 TH/s (~4.53 PH/s)
- 24h avg: 4511.13 TH/s (~4.51 PH/s)

**Profit (cumulative):**
- Total: 0.23402405 BTC
- PPS: 0.23264656 BTC
- PPLNS: 0.00137749 BTC
- Solo: 0 BTC

**24h Change:** +0.00204787 BTC (+$207 approx)

**Alert:** 🟢 None — all miners operational

---

## 2026-04-28 13:01 (Asia/Shanghai)

**Status:** ✅ ALL SYSTEMS GREEN

**Worker Status:**
- **Online:** 19 miners
- **Offline:** 0 miners
- **Total Offline Hours:** 0

**Hashrate:**
- 10min avg: 4244.64 TH/s (~4.24 PH/s)
- 1h avg: 4378.50 TH/s (~4.38 PH/s)
- 24h avg: 4518.74 TH/s (~4.52 PH/s)

**Profit (cumulative):**
- Total: 0.2381269 BTC
- PPS: 0.23672922 BTC
- PPLNS: 0.00139768 BTC
- Solo: 0 BTC

**24h Change:** +0.00205035 BTC (+$195 approx)

**Alert:** 🟢 None — all miners operational

---

## 2026-04-29 13:04 (Asia/Shanghai)

**Status:** ✅ ALL SYSTEMS GREEN

**Worker Status:**
- **Online:** 19 miners
- **Offline:** 0 miners
- **Total Offline Hours:** 0

**Hashrate:**
- 10min avg: 4728.78 TH/s (~4.73 PH/s)
- 1h avg: 4510.79 TH/s (~4.51 PH/s)
- 24h avg: 4525.70 TH/s (~4.53 PH/s)

**Profit (cumulative):**
- Total: 0.24018401 BTC
- PPS: 0.23877449 BTC
- PPLNS: 0.00140952 BTC
- Solo: 0 BTC

**24h Change:** +0.00205711 BTC (+$208 approx)

**Alert:** 🟢 None — all miners operational
