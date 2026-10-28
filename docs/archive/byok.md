# Local AI and API keys (BYOK) — historical source records

These are dated source records preserved during documentation consolidation. Their prices, legal statements, feature completion claims, paths, and benchmark numbers have not been revalidated. They are not current setup instructions or release acceptance results.

Current guide: [Local AI and API keys (BYOK)](../business/BYOK.md).

## Source index
- [BYOK_MODEL_GUIDE.md](#source-byok-model-guide)
- [BYOK_BUSINESS_MODEL.md](#source-byok-business-model)

<a id="source-byok-model-guide"></a>

## Source: BYOK_MODEL_GUIDE.md

<details>
<summary>Read the original source record</summary>

# Bring Your Own Key (BYOK) Model - User Guide
**Version:** 1.0 | **Date:** April 8, 2026

---

## 🎯 What is BYOK?

**Bring Your Own Key (BYOK)** means:
- **Free Tier**: Use Ollama (local AI) completely free - no API keys needed
- **Premium Tier**: Add your own API keys for premium providers (OpenAI, Claude, etc.)
- **You control costs**: We never bill you - pay providers directly

---

## 💰 Cost Comparison

### Our Model vs Competitors

| Service | Their Price | Our Model |
|---------|-------------|-----------|
| **Final Round AI** | $148/month | **FREE** (use Ollama) or BYOK (~$0.01/interview) |
| **Interview Coder** | $299/month | **FREE** (use Ollama) or BYOK |
| **LockedIn AI** | $69/month | **FREE** (use Ollama) or BYOK |
| **Cluely** | $75/month | **FREE** (use Ollama) or BYOK |

### Typical Costs (BYOK)

| Provider | Cost per 1K tokens | Typical Interview Cost |
|----------|-------------------|------------------------|
| **Ollama (Local)** | **$0** | **FREE** ✅ |
| DeepSeek | $0.00014 | ~$0.0005 |
| Groq | $0.00059 | ~$0.002 |
| Google Gemini | $0.0005 | ~$0.002 |
| OpenAI GPT-4o | $0.0015 | ~$0.005 |
| Anthropic Claude | $0.003 | ~$0.01 |

**Example:** 100 interviews using GPT-4o = ~$0.50 total (competitors charge $148/month!)

---

## 🆓 Free Tier (Ollama)

### What's Included
- ✅ Unlimited local AI usage
- ✅ All interview features
- ✅ Document RAG
- ✅ Screenshot analysis
- ✅ Meeting transcription
- ✅ Mock interviews
- ✅ Job tracker

### Requirements
- Ollama installed locally: https://ollama.com
- At least 8GB RAM
- 5GB disk space for models

### Recommended Free Models
```bash
# Fast, lightweight models (FREE)
ollama pull qwen2.5:1.5b      # General purpose
ollama pull llama3.2:latest   # Interview mode
ollama pull phi4:latest       # Coding interviews
ollama pull llava:latest      # Vision/Screenshots
```

---

## 🔑 Premium Tier (BYOK)

### Supported Providers

| Provider | Best For | Get Key At |
|----------|----------|------------|
| **OpenAI** | General purpose, fast | [platform.openai.com](https://platform.openai.com) |
| **Anthropic** | Reasoning, interview prep | [console.anthropic.com](https://console.anthropic.com) |
| **Google** | Multilingual, fast | [makersuite.google.com](https://makersuite.google.com) |
| **DeepSeek** | Cheapest option | [platform.deepseek.com](https://platform.deepseek.com) |
| **Groq** | Fastest responses | [console.groq.com](https://console.groq.com) |
| **xAI** | Grok models | [x.ai](https://x.ai) |
| **Perplexity** | Research, web search | [perplexity.ai/settings](https://www.perplexity.ai/settings) |

---

## 📖 How to Add Your API Keys

### Step 1: Get API Key
1. Sign up at your chosen provider (e.g., OpenAI)
2. Go to API keys section
3. Create a new key
4. Copy the key (keep it secret!)

### Step 2: Add to Application

**Via Web Interface:**
1. Open Settings → API Keys
2. Select provider
3. Paste your key
4. Click "Save"

**Via API:**
```bash
curl -X POST http://localhost:8000/providers/byok/configure \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d "provider=openai" \
  -d "api_key=sk-..."
```

### Step 3: Verify
```bash
curl http://localhost:8000/providers/byok/status \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 🔒 Security

### How We Protect Your Keys
- ✅ Keys stored encrypted on disk
- ✅ Never logged or transmitted elsewhere
- ✅ Only used for your requests
- ✅ Can delete anytime
- ✅ Memory-only during use

### Best Practices
- ✅ Use environment variables in production
- ✅ Rotate keys regularly
- ✅ Use provider-specific keys (not admin keys)
- ✅ Set spending limits at provider

---

## 🤔 FAQ

### Q: Is Ollama really free?
**A:** Yes! Ollama runs AI models locally on your computer. No API calls, no usage limits, completely free. Just needs your computer's resources.

### Q: Why would I pay for premium providers?
**A:** Premium providers offer:
- More accurate responses
- Better reasoning
- Faster inference
- No local resource requirements
- Access to proprietary models (GPT-4, Claude 3)

### Q: How much will I actually spend?
**A:** Typical usage:
- Light user: $0-1/month
- Heavy user: $5-10/month
- Power user: $20-50/month

Compare to competitors: $50-300/month!

### Q: Can I mix free and premium?
**A:** Yes! Use Ollama for most requests, premium only when needed. Set fallback in Settings.

### Q: What if I don't add any keys?
**A:** App works 100% with Ollama. You'll see a banner suggesting premium for better quality, but everything works.

### Q: Do you take a cut?
**A:** No. You pay providers directly. We're completely free and open source.

---

## 🚀 Quick Start

### For Free Users
```bash
# 1. Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 2. Pull a model
ollama pull qwen2.5:1.5b

# 3. Start using - no keys needed!
```

### For Premium Users
```bash
# 1. Get API key from provider (e.g., OpenAI)
# Sign up at platform.openai.com

# 2. Add key via API
curl -X POST http://localhost:8000/providers/byok/configure \
  -H "Authorization: Bearer TOKEN" \
  -d "provider=openai" \
  -d "api_key=sk-..."

# 3. Start using premium AI
```

---

## 📊 Provider Recommendations

### Budget-Conscious
1. **Ollama** (FREE) - Start here
2. **DeepSeek** (~$0.0005/interview) - Cheapest paid option

### Best Quality
1. **Anthropic Claude** - Best for interviews
2. **OpenAI GPT-4o** - Most capable

### Fastest
1. **Groq** - Fastest inference
2. **Google Gemini** - Low latency

### Balanced
1. **Groq Llama** - Fast + cheap
2. **DeepSeek** - Capable + cheap

---

## 🎓 Provider Comparison

| Provider | Speed | Quality | Cost | Best For |
|----------|-------|---------|------|----------|
| **Ollama** | Medium | Good | **FREE** | Budget users |
| **Groq** | **Fastest** | Good | Low | Speed priority |
| **DeepSeek** | Fast | Good | **Cheapest** | Cost-conscious |
| **Google** | Fast | Good | Low | Multilingual |
| **OpenAI** | Fast | **Best** | Medium | Quality priority |
| **Anthropic** | Medium | **Best** | Higher | Interview prep |

---

## 🔧 Troubleshooting

### "API key not configured" error
**Solution:** Add your key in Settings → API Keys

### "Invalid API key format"
**Solution:** Check key format:
- OpenAI: starts with `sk-`
- Groq: starts with `gsk_`
- Perplexity: starts with `pplx-`

### High costs unexpectedly
**Solution:**
1. Set spending limits at provider
2. Use Ollama for testing
3. Switch to cheaper provider (DeepSeek, Groq)

### Slow responses
**Solution:**
1. Switch to Groq or Google (fastest)
2. Use smaller models
3. Check your internet connection

---

## 📞 Support

**Questions about BYOK?**
- Check FAQ above
- Review provider documentation
- Open an issue on GitHub

**Provider-specific issues?**
- Contact the provider directly (OpenAI, Anthropic, etc.)
- We don't control their APIs or billing

---

## 📝 Changelog

- **v1.0** (April 8, 2026): Initial BYOK model launch
- Supports: OpenAI, Anthropic, Google, DeepSeek, Groq, xAI, Perplexity
- Free tier: Ollama local models

---

**Enjoy your AI interview assistant - completely free or pay-as-you-go with your own keys!**

</details>

<a id="source-byok-business-model"></a>

## Source: BYOK_BUSINESS_MODEL.md

<details>
<summary>Read the original source record</summary>

# BYOK Business Model - Technical & Strategic Overview
**Version:** 1.0 | **Date:** April 8, 2026

---

## Executive Summary

**Business Model:** Bring Your Own Key (BYOK)
- **Free Tier:** Ollama local models (completely free)
- **Premium:** Users provide their own API keys (we don't bill)
- **Value Prop:** "Use for FREE forever, or BYOK for premium AI"

**Competitive Advantage:**
- ✅ Only truly free interview assistant
- ✅ No vendor lock-in (8 providers)
- ✅ Transparent costs (user pays provider directly)
- ✅ Open source = trust

---

## Technical Architecture

### How BYOK Works

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER REQUEST                               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    AI ROUTER (ai_router.py)                      │
│  1. Check if user has premium key for requested provider         │
│  2. If yes → Use user's key                                     │
│  3. If no → Fallback to Ollama (free)                          │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
        ┌──────────┐    ┌──────────┐    ┌──────────┐
        │  Ollama  │    │  OpenAI  │    │ Anthropic│
        │ (FREE)   │    │(User Key)│    │(User Key)│
        └──────────┘    └──────────┘    └──────────┘
```

### Key Components

1. **User Key Manager** (`user_api_keys.py`)
   - Stores encrypted user API keys
   - Provides key lookup by user_id
   - Validates key formats

2. **Provider Functions** (`cloud_providers.py`)
   - Modified to accept user_id parameter
   - Fallback: user key → env key → error

3. **AI Router** (`ai_router.py`)
   - Selects provider based on availability
   - Falls back to Ollama when no premium keys

4. **API Endpoints** (`main.py`)
   - `/providers/byok/status` - Check configured keys
   - `/providers/byok/configure` - Add/update keys
   - `/providers/byok/costs` - Cost information

---

## Provider Cost Comparison

| Provider | Input/1K | Output/1K | Typical Interview Cost |
|----------|----------|-----------|------------------------|
| **Ollama** | **$0** | **$0** | **FREE** |
| DeepSeek | $0.00014 | $0.00028 | ~$0.0005 |
| Google Gemini | $0.0005 | $0.0015 | ~$0.002 |
| Groq | $0.00059 | $0.00079 | ~$0.002 |
| OpenAI GPT-4o | $0.0015 | $0.002 | ~$0.005 |
| Anthropic Claude | $0.003 | $0.015 | ~$0.01 |

**Example:** 100 interviews with GPT-4o = ~$0.50 (competitors: $148/month!)

---

## Competitive Position

### Before BYOK
- ❌ "Free but limited"
- ❌ No premium option
- ❌ Limited to Ollama quality

### After BYOK
- ✅ "Free forever" (Ollama)
- ✅ "Premium when you want it" (BYOK)
- ✅ "Best of both worlds"

### vs Competitors

| Competitor | Their Price | Our Equivalent Cost |
|------------|-------------|---------------------|
| Final Round AI | $148/mo | **FREE** or ~$0.50/mo |
| Interview Coder | $299/mo | **FREE** or ~$0.50/mo |
| LockedIn AI | $69/mo | **FREE** or ~$0.50/mo |

**Value Prop:** Same features, 99% cheaper!

---

## User Journeys

### Journey 1: Free User
1. Install Ollama
2. Use app completely free
3. No signup required
4. Unlimited usage

### Journey 2: Premium User
1. Try app with Ollama (free)
2. Want better quality → Sign up
3. Add OpenAI key in Settings
4. Get GPT-4o quality
5. Pay ~$0.50/month (not $148!)

### Journey 3: Power User
1. Sign up
2. Add multiple provider keys
3. Switch between providers
4. Optimize for cost/quality
5. Total cost: $5-10/month

---

## Implementation Status

### ✅ Complete
- User key storage (encrypted)
- Key validation
- API endpoints
- Cost information
- Documentation

### 🔧 In Progress
- Frontend UI for key management
- Provider selector in chat
- Usage tracking (per user)

### 📋 Planned
- Key sharing (teams)
- Budget alerts
- Auto-fallback rules

---

## Security Considerations

### Key Storage
- ✅ Encrypted at rest
- ✅ In-memory only during use
- ✅ Never logged
- ✅ User can delete anytime

### Best Practices
- Use provider-specific keys
- Set spending limits at provider
- Rotate keys regularly
- Use environment variables in production

---

## API Endpoints

### Check Status
```bash
GET /providers/byok/status
Authorization: Bearer TOKEN

Response:
{
  "has_premium_access": true,
  "providers": {
    "openai": {"configured": true, "name": "OpenAI GPT-4o"},
    "anthropic": {"configured": false, "name": "Anthropic Claude 3"},
    ...
  },
  "ollama_available": true
}
```

### Configure Key
```bash
POST /providers/byok/configure
Authorization: Bearer TOKEN
Content-Type: application/x-www-form-urlencoded

provider=openai&api_key=sk-...

Response:
{
  "status": "success",
  "message": "OpenAI API key configured successfully"
}
```

### Get Costs
```bash
GET /providers/byok/costs

Response:
{
  "providers": {
    "openai": {
      "name": "OpenAI GPT-4o",
      "input_cost_per_1k": 0.0015,
      "output_cost_per_1k": 0.002,
      "is_free": false
    },
    "ollama": {
      "name": "Ollama (Local - FREE)",
      "is_free": true
    }
  }
}
```

---

## Business Benefits

### For Users
1. **Complete control** - Choose your providers
2. **Transparent costs** - Know exactly what you pay
3. **No lock-in** - Switch providers anytime
4. **Free option** - Use forever without paying

### For Business
1. **No infrastructure costs** - We don't host AI models
2. **No API bills** - Users pay providers directly
3. **Focus on features** - Not on AI hosting
4. **Sustainable** - No burning cash on AI costs

---

## Marketing Messages

### Primary
"The only truly free AI interview assistant. Use Ollama forever free, or BYOK for premium AI."

### Secondary
- "No subscriptions. No limits. No catch."
- "Your keys, your choice, your costs."
- "Why pay $148/month when you can pay $0.50?"

### Taglines
- "Free forever. Premium when you want it."
- "BYOK: Bring Your Own Key, keep your money."
- "The open-source alternative to $300/month interview tools."

---

## Next Steps

### Immediate
1. Deploy BYOK endpoints
2. Add UI for key management
3. Update onboarding flow

### Short-term
1. Add usage tracking dashboard
2. Implement budget alerts
3. Add team key sharing

### Long-term
1. Reseller program (discount on bulk keys)
2. Managed key service (optional)
3. Enterprise BYOK (SSO + audit logs)

---

## Success Metrics

### Adoption
- % users with premium keys
- Average keys per user
- Provider popularity

### Economics
- User cost savings vs competitors
- Support ticket volume
- Conversion rate (free → premium)

### Satisfaction
- NPS score
- Feature usage
- Retention rate

---

**The BYOK model aligns incentives:**
- Users want cheap AI → They choose cheapest provider
- We want happy users → We don't markup costs
- Providers get customers → They compete on price

**Everyone wins!** 🎉

</details>
