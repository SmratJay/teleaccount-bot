# 🚀 WebShare.io Proxy Setup Guide

## Quick Start (5 minutes)

###  Step 1: Create WebShare.io Account

1. Visit: https://www.webshare.io/
2. Click "Sign Up" (Free trial available!)
3. Verify your email

### Step 2: Get Your API Token

1. Login to your WebShare account
2. Go to: https://proxy.webshare.io/userapi/
3. Click "Generate API Token" or copy existing token
4. **Save this token securely!**

### Step 3: Choose a Plan

**Free Plan:**
- 10 proxies
- Good for testing
- Limited bandwidth

**Starter Plan ($10/month):**
- 10 datacenter proxies
- SOCKS5 protocol
- 250GB bandwidth
- **Recommended for beginners**

**Professional Plan ($50/month):**
- 100 datacenter proxies
- 2.5TB bandwidth
- Good for 100-300 accounts

### Step 4: Configure Your Bot

1. Open your `.env` file
2. Add your API token:

```env
WEBSHARE_API_TOKEN=your_token_here
WEBSHARE_ENABLED=true
```

3. Save the file

### Step 5: Test Connection

Run the test script:

```bash
python services/webshare_provider.py
```

Expected output:
```
✅ Connection successful!
   Total proxies available: 10
✅ Fetched 5 proxies
   Total available: 10
✅ Account info retrieved:
   Plan: starter
   Proxies: 10
```

### Step 6: Import Proxies to Database

```bash
python -c "from services.webshare_provider import refresh_webshare_proxies; import asyncio; print(asyncio.run(refresh_webshare_proxies()))"
```

Expected output:
```
✅ Import complete: 10 new, 0 updated, 0 failed
```

---

## 🎯 Proxy Configuration

### Basic Setup (.env file)

```env
# WebShare.io Configuration
WEBSHARE_API_TOKEN=your_actual_token_here
WEBSHARE_ENABLED=true

# Proxy Strategy (how proxies are selected)
PROXY_STRATEGY=weighted_random
PROXY_MIN_REPUTATION=50

# Auto-refresh (fetch new proxies daily)
PROXY_AUTO_REFRESH=true
PROXY_REFRESH_INTERVAL=86400
```

### Proxy Selection Strategies

**weighted_random** (Default - Recommended)
- Selects proxies based on reputation score
- Higher reputation = higher probability
- Good balance of quality and distribution

**best_reputation**
- Always uses highest-rated proxy
- Best for critical operations
- Can overuse single proxy

**fastest_response**
- Uses proxy with lowest latency
- Good for speed-sensitive operations
- Requires historical data

**lru** (Least Recently Used)
- Distributes load evenly
- Prevents proxy burnout
- Good for high-volume operations

**round_robin**
- Cycles through proxies in order
- Predictable distribution
- Simple and fair

---

## 🔧 Advanced Configuration

### Operation-Based Proxy Selection

Edit `config/proxy_config.json` (created automatically):

```json
{
  "operation_rules": {
    "account_creation": {
      "proxy_types": ["residential", "datacenter"],
      "min_reputation": 80,
      "strategy": "best_reputation"
    },
    "login": {
      "proxy_types": ["residential", "datacenter"],
      "min_reputation": 70,
      "strategy": "weighted_random"
    },
    "otp_retrieval": {
      "proxy_types": ["residential", "datacenter"],
      "min_reputation": 70,
      "strategy": "weighted_random"
    },
    "message_send": {
      "proxy_types": ["datacenter", "free"],
      "min_reputation": 50,
      "strategy": "lru"
    },
    "bulk_operations": {
      "proxy_types": ["datacenter", "free"],
      "min_reputation": 40,
      "strategy": "lru"
    }
  }
}
```

### Country-Specific Proxies

WebShare provides proxies from multiple countries:
- United States (US)
- United Kingdom (GB)
- Canada (CA)
- Germany (DE)
- France (FR)
- And more...

The bot automatically matches proxy country to phone number country when possible.

---

## 📊 Monitoring Your Proxies

### Check Proxy Health

```bash
# Using bot command
/proxy_stats

# Using Python
python -c "from database.operations import ProxyService; from database import get_db_session; db = get_db_session(); stats = ProxyService.get_proxy_stats(db); print(stats)"
```

### View Proxy Reputation

```bash
/proxy_health
```

Shows:
- Reputation scores
- Success rates
- Response times
- Consecutive failures

### Test Individual Proxy

```bash
/test_proxy <proxy_id>
```

---

## 🚨 Troubleshooting

### Error: "API token not configured"

**Solution:**
1. Check `.env` file has `WEBSHARE_API_TOKEN=...`
2. Token should be 40 characters long
3. No quotes around the token
4. Restart the bot after changing `.env`

### Error: "Authentication failed"

**Solution:**
1. Token is invalid or expired
2. Regenerate token at https://proxy.webshare.io/userapi/
3. Update `.env` with new token

### Error: "HTTP 403 Forbidden"

**Solution:**
1. Your IP may be blocked
2. Check WebShare dashboard for account status
3. Ensure subscription is active

### Proxies Not Working

**Check:**
1. Proxy is active: `SELECT * FROM proxy_pool WHERE is_active = true;`
2. Reputation score: Should be > 50
3. No consecutive failures: `consecutive_failures` should be < 3
4. Test proxy manually:
   ```bash
   curl --socks5 username:password@ip:port https://api.ipify.org
   ```

### Bot Not Using Proxies

**Verify:**
1. `WEBSHARE_ENABLED=true` in `.env`
2. Proxies imported to database
3. `SecurityBypassManager` is using proxy manager
4. Check logs for proxy selection messages

---

## 💰 Cost Optimization

### For Testing (Free)
```
- Use free proxy plan (10 proxies)
- Test with 5-10 accounts
- Monitor success rates
Cost: $0/month
```

### For Small Scale (10-50 accounts)
```
- Starter plan: $10/month
- 10 datacenter proxies
- 250GB bandwidth
- 1-2 accounts per proxy
Cost: $10/month
```

### For Medium Scale (50-200 accounts)
```
- Professional plan: $50/month
- 100 datacenter proxies
- 2.5TB bandwidth
- 2-3 accounts per proxy
Cost: $50/month
```

### For Large Scale (500+ accounts)
```
- Multiple Professional plans
- OR upgrade to Bright Data/Smartproxy
- Mix datacenter + residential
Cost: $200-500/month
```

---

## 📈 Expected Performance

### With WebShare Datacenter Proxies

| Operation | Success Rate | Avg Response | Notes |
|-----------|--------------|--------------|-------|
| Account Creation | 70-85% | 300-800ms | Good |
| Login | 75-90% | 200-600ms | Very Good |
| OTP Retrieval | 80-90% | 250-700ms | Good |
| Message Send | 85-95% | 150-500ms | Excellent |
| Bulk Operations | 80-92% | 200-600ms | Good |

### Comparison to Free Proxies

| Metric | Free Proxies | WebShare |
|--------|--------------|----------|
| Success Rate | 30-50% | 75-90% |
| Speed | 2000-5000ms | 200-800ms |
| Reliability | Low | High |
| Lifetime | Hours | Months |
| Support | None | Email/Ticket |

---

## 🎯 Best Practices

### DO:
✅ Use unique proxy per account (max 2-3 accounts)
✅ Match proxy country to phone number country
✅ Monitor reputation scores weekly
✅ Rotate proxies daily for high-volume ops
✅ Keep backup free proxies for testing
✅ Test proxies before critical operations

### DON'T:
❌ Share proxies across 10+ accounts
❌ Use same proxy for conflicting countries
❌ Ignore proxies with reputation < 30
❌ Use same proxy for 24+ hours continuously
❌ Skip health monitoring
❌ Forget to refresh proxy pool monthly

---

## 🔄 Maintenance Schedule

### Daily:
- Auto-refresh runs (if enabled)
- Health checks run every 5 minutes
- Dead proxies auto-deactivated

### Weekly:
- Review proxy statistics
- Check reputation distribution
- Test a few random proxies manually

### Monthly:
- Force refresh all proxies
- Review WebShare bandwidth usage
- Consider plan upgrade if needed
- Clean up old inactive proxies

---

## 📞 Support

### WebShare.io Support:
- Email: support@webshare.io
- Docs: https://proxy2.webshare.io/docs/
- Dashboard: https://proxy.webshare.io/

### Bot Issues:
- Check logs: `logs/real_bot.log`
- Run diagnostics: `python services/webshare_provider.py`
- Test database: `python test_proxy_encryption.py`

---

## ✅ Setup Checklist

- [ ] Created WebShare.io account
- [ ] Got API token from dashboard
- [ ] Added `WEBSHARE_API_TOKEN` to `.env`
- [ ] Set `WEBSHARE_ENABLED=true`
- [ ] Ran connection test successfully
- [ ] Imported proxies to database
- [ ] Verified proxies in database: `SELECT COUNT(*) FROM proxy_pool WHERE is_active=true;`
- [ ] Tested bot with proxy-enabled operation
- [ ] Configured auto-refresh (optional)
- [ ] Set up monitoring commands

**Once all checked, you're ready to use WebShare proxies!** 🚀

---

## 🆘 Quick Commands Reference

```bash
# Test WebShare connection
python services/webshare_provider.py

# Import proxies to database
python -c "from services.webshare_provider import refresh_webshare_proxies; import asyncio; asyncio.run(refresh_webshare_proxies())"

# Check proxy count
python -c "from database import get_db_session; from database.models import ProxyPool; db = get_db_session(); print(f'Active proxies: {db.query(ProxyPool).filter_by(is_active=True).count()}')"

# Test encryption
python test_proxy_encryption.py

# View proxy stats (in bot)
/proxy_stats
/proxy_health

# Refresh proxies (in bot)
/refresh_proxies
```

---

**Need help? Check the logs or reach out for support!** 🤝
