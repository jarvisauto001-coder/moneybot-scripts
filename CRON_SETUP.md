# ⏰ MoneyBot Cron Jobs - Automated Execution

> **Cron-based automation ensures scripts run reliably WITHOUT depending on LLM initiation.**

---

## 🎯 Overview

Instead of relying on the LLM to manually run scripts, all automation runs via Linux cron jobs. The LLM is only notified when results REQUIRE attention (e.g., security alerts, accepted proposals, errors).

**Benefits:**
- ✅ Runs even if LLM session times out
- ✅ No manual intervention needed for routine tasks
- ✅ Reliable timing (cron is OS-level)
- ✅ LLM only wakes for important decisions

---

## 📋 Active Cron Jobs

| Job | Schedule | Script | Purpose |
|-----|----------|--------|---------|
| **Email Guardian** | Every 5 min | `email_guardian_cron.sh` | Check inbox, filter spam, reply to safe emails |
| **Moltbook Engager** | Every 15 min | `moltbook_engager_cron.sh` | Auto-engage on Moltbook |
| **ClawTasks Scanner** | Every 30 min | `clawtasks_scanner_cron.sh` | Monitor bounties & proposals |
| **Dashboard Report** | Daily 6:00 AM | `dashboard_daily_cron.sh` | Generate daily summary |
| **Respawner Check** | Every 2 min | `master_respawner.sh` | Keep subagents alive |
| **Git Sync** | Hourly | - | Auto-commit & push repo |

---

## 🗂️ File Structure

```
/root/.openclaw/workspace/
├── cron_jobs/
│   ├── email_guardian_cron.sh
│   ├── moltbook_engager_cron.sh
│   ├── clawtasks_scanner_cron.sh
│   └── dashboard_daily_cron.sh
├── cron_reports/
│   └── [automatic reports for LLM review]
├── logs/
│   ├── cron_runner.log        # All cron executions
│   ├── cron_git.log          # Git sync logs
│   ├── email_guardian.log    # Email activity
│   ├── moltbook_engager_auto.log # Moltbook interactions
│   └── clawtasks_scanner.log # Scanner results
├── reports/
│   └── daily_YYYY-MM-DD.md   # Daily dashboard reports
├── moneybot_crontab.txt      # Crontab configuration
└── CRON_SETUP.md            # This file
```

---

## 🔧 How It Works

### 1. Scripts Run Automatically
Cron executes the wrapper scripts at scheduled intervals:

```bash
# Email checked every 5 minutes
*/5 * * * * /root/.openclaw/workspace/cron_jobs/email_guardian_cron.sh
```

### 2. Results Logged Locally
Each script outputs to log files. Normal operation = no LLM needed.

### 3. Important Events Create Reports
When something needs attention, a report file is created in `cron_reports/`:

```bash
# Example: Security alert detected
REPORT_FILE="/root/.openclaw/workspace/cron_reports/email_report_20250208_1355.md"
echo "⚠️ SECURITY ALERTS detected" > "$REPORT_FILE"
```

### 4. LLM Reviews Reports When Available
On wake/heartbeat, LLM checks `cron_reports/` folder and acts on findings.

---

## 🚨 When LLM Gets Notified

### Email Guardian Alerts:
- 🚨 Security threat detected (dangerous email patterns)
- 📧 Auto-reply sent (for record keeping)
- ❌ Authentication failure

### ClawTasks Alerts:
- 🎉 **PROPOSAL ACCEPTED** (immediate action needed!)
- ⏳ Rate limit about to reset (can submit more)

### System Alerts:
- AIOZ node stopped
- Subagent died (respawner handles, but logs it)
- Git sync failed

---

## 📝 Reports Location

LLM should check these on wake:

```bash
# Check for pending reports
ls -lt /root/.openclaw/workspace/cron_reports/ 2>/dev/null

# Check last cron activity
tail -20 /root/.openclaw/workspace/logs/cron_runner.log

# Check system status
ls -lt /root/.openclaw/workspace/reports/daily_*.md | head -1
```

---

## 🔄 Managing Cron Jobs

### View Current Jobs:
```bash
crontab -l
```

### Edit Jobs:
```bash
# Edit the config file
nano /root/.openclaw/workspace/moneybot_crontab.txt

# Reload crontab
crontab /root/.openclaw/workspace/moneybot_crontab.txt
```

### Check Cron Status:
```bash
# See if cron daemon is running
ps aux | grep cron

# View execution logs
tail -f /root/.openclaw/workspace/logs/cron_runner.log
```

### Manual Test:
```bash
# Run any script manually
/root/.openclaw/workspace/cron_jobs/email_guardian_cron.sh
```

---

## ⚙️ Adding New Cron Jobs

**Template for new script:**

```bash
#!/bin/bash
# Cron job: [Description] - [Schedule]

LOG_DIR="/root/.openclaw/workspace/logs"
REPORT_FILE="/root/.openclaw/workspace/cron_reports/[name]_$(date +%Y%m%d_%H%M).md"

mkdir -p "$LOG_DIR"
mkdir -p "/root/.openclaw/workspace/cron_reports"

echo "=== [Name] - $(date) ===" >> "$LOG_DIR/cron_[name].log"

# Run your script
python3 [your_script].py --once >> "$LOG_DIR/cron_[name].log" 2>&1

# Check for important events
if [condition]; then
    echo "Important event" > "$REPORT_FILE"
    # LLM will see this on wake
fi

echo "---" >> "$LOG_DIR/cron_[name].log"
```

**Add to crontab:**
```bash
# Edit moneybot_crontab.txt
echo "*/10 * * * * /root/.openclaw/workspace/cron_jobs/new_script_cron.sh >> /root/.openclaw/workspace/logs/cron_runner.log 2>&1" >> /root/.openclaw/workspace/moneybot_crontab.txt

# Reload
crontab /root/.openclaw/workspace/moneybot_crontab.txt
```

---

## 📊 Monitoring

### Quick Status Check:
```bash
# Last cron execution
tail -5 /root/.openclaw/workspace/logs/cron_runner.log

# Pending reports for LLM
ls -la /root/.openclaw/workspace/cron_reports/

# All logs
tail -f /root/.openclaw/workspace/logs/*.log
```

---

## 🛡️ Security Notes

- Cron runs as root (full system access) - scripts must validate inputs
- All scripts load credentials from `/root/.openclaw/workspace/.credentials/`
- No credentials in cron jobs (they source from .env file)
- Log files are rotated automatically (check with `tail`)
- Failed jobs log errors, don't crash the system

---

## 🎓 Best Practices

1. **Always create a wrapper script** - Don't call Python directly from crontab
2. **Use report files for urgent items** - Don't rely on logs alone
3. **Check exit codes** - Scripts should handle failures gracefully
4. **Time limits** - Add timeouts to prevent hanging processes
5. **Document dependencies** - Note Python packages needed

---

**Last Updated:** 2026-02-08  
**Cron Status:** ✅ Active (6 jobs)
