# Cerebrum Deployment Tracking

> Central log for all Cerebrum deployments. Update after each deploy with test results.

---

## Deploy Log

### Deploy #2
| Field | Value |
|-------|-------|
| **Commit Hash** | `7bcaaf44` |
| **Description** | Fixed critical agent bugs |
| **Deploy Time** | 2026-04-01 00:30:00+08:00 |
| **Status** | Live |
| **Tests Run** | TBD |
| **Issues Found** | TBD |
| **Fix Commits Applied** | None (initial deploy) |

**Test Results:**
```
[ ] Health endpoint check
[ ] Agent status (14 layers)
[ ] Layer navigation
[ ] Chat routing
[ ] File uploads
[ ] WebSocket
[ ] Voice health
```

---

### Deploy #1
| Field | Value |
|-------|-------|
| **Commit Hash** | `54b98ec` |
| **Description** | Graceful transcription error |
| **Deploy Time** | TBD |
| **Status** | Building |
| **Tests Run** | TBD |
| **Issues Found** | TBD |
| **Fix Commits Applied** | None (initial deploy) |

**Test Results:**
```
[ ] Health endpoint check
[ ] Agent status (14 layers)
[ ] Layer navigation
[ ] Chat routing
[ ] File uploads
[ ] WebSocket
[ ] Voice health
```

---

## Quick Reference

### Status Values
- `Building` - Deploy in progress
- `Live` - Deploy successful, serving traffic
- `Failed` - Deploy failed, rolled back or needs fix

### Update Template
```markdown
### Deploy #{N}
| Field | Value |
|-------|-------|
| **Commit Hash** | `{HASH}` |
| **Description** | {description} |
| **Deploy Time** | {ISO8601 timestamp} |
| **Status** | {Building/Live/Failed} |
| **Tests Run** | {test commands/results} |
| **Issues Found** | {list or "None"} |
| **Fix Commits Applied** | {list or "None"} |

**Test Results:**
[Copy from GREEN_CHECKLIST.md]
```

---

*Last updated: 2026-04-01*
