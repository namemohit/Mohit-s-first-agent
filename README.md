# Meta Campaigns Agent

A Claude-powered AI agent that lets you manage and analyse your Meta (Facebook/Instagram)
ad campaigns using natural language.

## What it can do

| Capability | Examples |
|---|---|
| **List campaigns** | "Show me all active campaigns" |
| **Campaign details** | "Get info on campaign 123456789" |
| **Create campaigns** | "Create a traffic campaign called Summer Sale with a $50/day budget" |
| **Update campaigns** | "Increase the budget on campaign X to $100/day" |
| **Pause / Resume** | "Pause all campaigns" / "Resume the Summer Sale campaign" |
| **Delete campaigns** | "Delete the test campaign" (will confirm first) |
| **Performance insights** | "How did my campaigns perform last month?" |
| **Account analytics** | "Show me account-level stats for the last 7 days" |
| **Ad sets & Ads** | "List ad sets in campaign 123456789" |

## Setup

### 1. Clone & install dependencies

```bash
git clone <repo-url>
cd Mohit-s-first-agent
pip install -r requirements.txt
```

### 2. Configure credentials

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

| Variable | Where to get it |
|---|---|
| `META_ACCESS_TOKEN` | [Meta for Developers](https://developers.facebook.com/tools/explorer/) — generate a User Access Token with `ads_management` and `ads_read` permissions |
| `META_AD_ACCOUNT_ID` | Your ad account ID, format `act_XXXXXXXXX` — find it in [Business Manager](https://business.facebook.com/settings/ad-accounts) |
| `META_APP_ID` | Your Meta App ID from [developers.facebook.com/apps](https://developers.facebook.com/apps/) |
| `META_APP_SECRET` | Your Meta App Secret (same page as App ID) |
| `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com/) |

### 3. Run the agent

**Interactive mode (recommended):**
```bash
python agent.py
```

**Single query mode:**
```bash
python agent.py "show me my active campaigns"
python agent.py "how much did I spend last week?"
python agent.py "pause campaign 120210000000000"
```

## Example session

```
Meta Campaigns Agent
Powered by Claude + Meta Marketing API

You: show me all active campaigns

  → calling tool list_campaigns with {"status_filter": "ACTIVE"}

Agent:
Here are your active campaigns:

| ID | Name | Objective | Daily Budget | Status |
|---|---|---|---|---|
| 120210001234567 | Summer Sale | OUTCOME_TRAFFIC | $50.00 | ACTIVE |
| 120210009876543 | Brand Awareness Q2 | OUTCOME_AWARENESS | $30.00 | ACTIVE |

You: how did Summer Sale perform last 30 days?

  → calling tool get_campaign_insights with {"campaign_id": "120210001234567", "date_preset": "last_30d"}

Agent:
**Summer Sale — Last 30 Days**

- Impressions: 245,302
- Reach: 189,441
- Clicks: 3,821 (CTR: 1.56%)
- Spend: $1,420.55
- CPC: $0.37 | CPM: $5.79
```

## Project structure

```
Mohit-s-first-agent/
├── agent.py          # Claude agent loop + CLI
├── meta_tools.py     # Meta Marketing API tool implementations
├── requirements.txt  # Python dependencies
├── .env.example      # Credentials template
└── README.md
```

## Required Meta API permissions

Your access token needs these permissions:
- `ads_management` — to create/update/delete campaigns
- `ads_read` — to read campaigns and insights

For a System User token (production), set these in Business Manager → System Users.
