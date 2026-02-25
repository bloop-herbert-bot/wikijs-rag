# Auto-Reindexing Setup Guide

Automatically sync Wiki.js content to ChromaDB on a schedule.

## Prerequisites

- Working `rag_indexer.py` (tested and functional)
- `.env` file configured with Wiki.js credentials
- Python venv with all dependencies installed

## Quick Setup

### 1. Test the Sync Script

```bash
cd ~/.openclaw/workspace-githerbert/wikijs-rag
./sync_wikijs.sh
```

Expected output:
```
=========================================
Wiki.js RAG Sync Started: ...
=========================================
🔧 Activating virtual environment...
📥 Fetching Wiki.js pages via GraphQL...
✅ Found 61 pages
...
✅ Reindexing successful!
📊 Stats: "total_chunks":1288
=========================================
```

### 2. System Cron (Option A)

**Edit crontab:**
```bash
crontab -e
```

**Add line:**
```cron
# Wiki.js RAG auto-reindex (daily at 2 AM)
0 2 * * * /home/openclaw/.openclaw/workspace-githerbert/wikijs-rag/sync_wikijs.sh >> /tmp/rag_reindex.log 2>&1
```

**Verify:**
```bash
crontab -l
```

### 3. OpenClaw Cron (Option B - Recommended)

**Add via OpenClaw cron tool:**

```bash
openclaw cron add \
  --name "Wiki.js RAG Daily Sync" \
  --schedule "0 2 * * *" \
  --command "/home/openclaw/.openclaw/workspace-githerbert/wikijs-rag/sync_wikijs.sh"
```

Or programmatically:

```javascript
// In OpenClaw agent session:
cron({
  action: "add",
  job: {
    name: "Wiki.js RAG Daily Sync",
    schedule: {
      kind: "cron",
      expr: "0 2 * * *",  // Daily at 2 AM
      tz: "Europe/Vienna"
    },
    payload: {
      kind: "systemEvent",
      text: "Running Wiki.js RAG reindex..."
    },
    sessionTarget: "isolated",
    enabled: true
  }
})
```

**List cron jobs:**
```bash
openclaw cron list
```

### 4. Manual Trigger

Run immediately:
```bash
./sync_wikijs.sh
```

Or via OpenClaw:
```bash
openclaw cron run <job-id>
```

## Configuration

### Schedule Options

**Daily at 2 AM:**
```cron
0 2 * * *
```

**Every 6 hours:**
```cron
0 */6 * * *
```

**Weekly on Sunday at 3 AM:**
```cron
0 3 * * 0
```

**Custom schedule:**
Use [crontab.guru](https://crontab.guru/) to build expressions.

### Logging

**Default log location:**
```bash
tail -f /tmp/rag_reindex.log
```

**Custom log location:**
```bash
# In crontab:
0 2 * * * /path/to/sync_wikijs.sh >> /var/log/wikijs-rag-sync.log 2>&1
```

**Rotate logs (optional):**
```bash
# /etc/logrotate.d/wikijs-rag
/tmp/rag_reindex.log {
    daily
    rotate 7
    compress
    missingok
    notifempty
}
```

## Monitoring

### Check Last Run

```bash
tail -20 /tmp/rag_reindex.log
```

### Verify Index Stats

```bash
curl -s http://localhost:8765/stats | jq .
```

Expected output:
```json
{
  "collection": "wikijs",
  "total_chunks": 1288,
  "unique_pages": 59,
  "storage": "./chromadb"
}
```

### Email Notifications (Optional)

**Install mailutils:**
```bash
sudo apt install mailutils
```

**Modify sync script:**
```bash
# At end of sync_wikijs.sh:
if [ $? -eq 0 ]; then
    echo "✅ Reindexing successful!" | mail -s "Wiki.js RAG Sync OK" admin@example.com
else
    echo "❌ Reindexing failed!" | mail -s "Wiki.js RAG Sync FAILED" admin@example.com
fi
```

## Troubleshooting

### Cron Not Running

**Check cron service:**
```bash
sudo systemctl status cron
```

**Check user permissions:**
```bash
ls -l /var/spool/cron/crontabs/$(whoami)
```

**Check logs:**
```bash
grep CRON /var/log/syslog
```

### Script Fails in Cron

**Test with full environment:**
```bash
env -i bash -c 'cd /path/to/wikijs-rag && ./sync_wikijs.sh'
```

**Common issues:**
- Missing `PATH` in cron environment
- `.env` file not found (use absolute paths)
- venv activation fails (check paths)

**Fix:**
Add to top of sync_wikijs.sh:
```bash
export PATH=/usr/local/bin:/usr/bin:/bin
```

### API Not Restarting

If API runs as systemd service:

**Uncomment in sync_wikijs.sh:**
```bash
if systemctl is-active --quiet wikijs-rag; then
    sudo systemctl restart wikijs-rag
fi
```

**Grant sudo permissions (optional):**
```bash
sudo visudo
# Add:
openclaw ALL=(ALL) NOPASSWD: /bin/systemctl restart wikijs-rag
```

## Advanced: Incremental Updates

**Future enhancement:** Only reindex changed pages.

**Query modified pages:**
```graphql
query {
  pages {
    list(filter: {updatedAfter: "2026-02-24T00:00:00Z"}) {
      id
      path
      title
      updatedAt
    }
  }
}
```

**Track last sync:**
```bash
echo $(date -Iseconds) > .last_sync
```

**Use in indexer:**
```python
with open('.last_sync', 'r') as f:
    last_sync = f.read().strip()
# Fetch only pages updated after last_sync
```

## Best Practices

1. **Test manually first** - Don't schedule until verified
2. **Monitor logs regularly** - Check for failures
3. **Keep backups** - ChromaDB can be backed up: `tar -czf chromadb-backup.tar.gz chromadb/`
4. **Schedule during low-traffic** - Reindexing can take 2-5 minutes
5. **Use absolute paths** - Cron runs in minimal environment

## Summary

**Recommended setup:**
- ✅ Use OpenClaw cron (integrated, monitored)
- ✅ Daily at 2 AM (low traffic time)
- ✅ Log to `/tmp/rag_reindex.log`
- ✅ Monitor via `curl http://localhost:8765/stats`

**One-liner setup:**
```bash
chmod +x sync_wikijs.sh && \
./sync_wikijs.sh && \
echo "0 2 * * * $(pwd)/sync_wikijs.sh >> /tmp/rag_reindex.log 2>&1" | crontab -
```

Done! 🎉
