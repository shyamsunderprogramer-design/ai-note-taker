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
