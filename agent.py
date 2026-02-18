"""
Meta Campaigns Agent
====================
A Claude-powered agent that can manage and analyse your Meta (Facebook/Instagram)
ad campaigns via the Meta Marketing API.

Usage:
    python agent.py                  # interactive REPL
    python agent.py "list my active campaigns"
"""

import json
import os
import sys
from typing import Any

import anthropic
from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

import meta_tools

load_dotenv()

console = Console()

# ---------------------------------------------------------------------------
# Tool definitions (passed to Claude)
# ---------------------------------------------------------------------------

TOOLS: list[dict] = [
    {
        "name": "list_campaigns",
        "description": (
            "List all campaigns in the Meta ad account. "
            "Filter by status: ACTIVE, PAUSED, ARCHIVED, DELETED, or ALL."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "status_filter": {
                    "type": "string",
                    "enum": ["ACTIVE", "PAUSED", "ARCHIVED", "DELETED", "ALL"],
                    "description": "Campaign status to filter by. Defaults to ACTIVE.",
                    "default": "ACTIVE",
                }
            },
        },
    },
    {
        "name": "get_campaign",
        "description": "Get detailed information about a single campaign by its ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "campaign_id": {
                    "type": "string",
                    "description": "The campaign ID.",
                }
            },
            "required": ["campaign_id"],
        },
    },
    {
        "name": "create_campaign",
        "description": (
            "Create a new Meta ad campaign. "
            "Campaigns start PAUSED by default for safety. "
            "Either daily_budget OR lifetime_budget must be provided (in account currency cents)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Campaign name."},
                "objective": {
                    "type": "string",
                    "enum": [
                        "OUTCOME_AWARENESS",
                        "OUTCOME_TRAFFIC",
                        "OUTCOME_ENGAGEMENT",
                        "OUTCOME_LEADS",
                        "OUTCOME_APP_PROMOTION",
                        "OUTCOME_SALES",
                    ],
                    "description": "Campaign objective.",
                },
                "status": {
                    "type": "string",
                    "enum": ["ACTIVE", "PAUSED"],
                    "default": "PAUSED",
                    "description": "Initial status. Defaults to PAUSED.",
                },
                "daily_budget": {
                    "type": "integer",
                    "description": "Daily budget in account currency cents (e.g. 1000 = $10.00).",
                },
                "lifetime_budget": {
                    "type": "integer",
                    "description": "Lifetime budget in account currency cents.",
                },
                "start_time": {
                    "type": "string",
                    "description": "Start datetime in ISO 8601 format e.g. 2025-06-01T00:00:00.",
                },
                "stop_time": {
                    "type": "string",
                    "description": "Stop datetime in ISO 8601 format.",
                },
                "special_ad_categories": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Special ad categories e.g. CREDIT, EMPLOYMENT, HOUSING.",
                    "default": [],
                },
            },
            "required": ["name", "objective"],
        },
    },
    {
        "name": "update_campaign",
        "description": "Update fields on an existing campaign (name, status, budgets, stop time).",
        "input_schema": {
            "type": "object",
            "properties": {
                "campaign_id": {"type": "string", "description": "Campaign ID to update."},
                "name": {"type": "string", "description": "New campaign name."},
                "status": {
                    "type": "string",
                    "enum": ["ACTIVE", "PAUSED"],
                    "description": "New campaign status.",
                },
                "daily_budget": {
                    "type": "integer",
                    "description": "New daily budget in cents.",
                },
                "lifetime_budget": {
                    "type": "integer",
                    "description": "New lifetime budget in cents.",
                },
                "stop_time": {
                    "type": "string",
                    "description": "New stop time ISO 8601 string.",
                },
            },
            "required": ["campaign_id"],
        },
    },
    {
        "name": "pause_campaign",
        "description": "Pause an active campaign.",
        "input_schema": {
            "type": "object",
            "properties": {
                "campaign_id": {"type": "string", "description": "Campaign ID to pause."}
            },
            "required": ["campaign_id"],
        },
    },
    {
        "name": "resume_campaign",
        "description": "Resume (activate) a paused campaign.",
        "input_schema": {
            "type": "object",
            "properties": {
                "campaign_id": {"type": "string", "description": "Campaign ID to resume."}
            },
            "required": ["campaign_id"],
        },
    },
    {
        "name": "delete_campaign",
        "description": (
            "Permanently delete a campaign. This cannot be undone. "
            "Always confirm with the user before calling this."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "campaign_id": {"type": "string", "description": "Campaign ID to delete."}
            },
            "required": ["campaign_id"],
        },
    },
    {
        "name": "get_campaign_insights",
        "description": (
            "Get performance analytics for a specific campaign "
            "(impressions, clicks, CTR, spend, CPC, CPM, conversions, etc.)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "campaign_id": {"type": "string", "description": "Campaign ID."},
                "date_preset": {
                    "type": "string",
                    "enum": [
                        "today",
                        "yesterday",
                        "last_7d",
                        "last_30d",
                        "last_90d",
                        "this_month",
                        "last_month",
                        "last_year",
                    ],
                    "default": "last_7d",
                    "description": "Pre-defined date range. Ignored if start_date/end_date are set.",
                },
                "start_date": {
                    "type": "string",
                    "description": "Start date YYYY-MM-DD (overrides date_preset).",
                },
                "end_date": {
                    "type": "string",
                    "description": "End date YYYY-MM-DD (overrides date_preset).",
                },
                "breakdown": {
                    "type": "string",
                    "description": "Optional breakdown dimension: age, gender, country, placement.",
                },
            },
            "required": ["campaign_id"],
        },
    },
    {
        "name": "get_account_insights",
        "description": "Get account-level performance analytics across all campaigns.",
        "input_schema": {
            "type": "object",
            "properties": {
                "date_preset": {
                    "type": "string",
                    "enum": [
                        "today",
                        "yesterday",
                        "last_7d",
                        "last_30d",
                        "last_90d",
                        "this_month",
                        "last_month",
                        "last_year",
                    ],
                    "default": "last_7d",
                },
                "start_date": {"type": "string", "description": "Start date YYYY-MM-DD."},
                "end_date": {"type": "string", "description": "End date YYYY-MM-DD."},
            },
        },
    },
    {
        "name": "list_ad_sets",
        "description": "List all ad sets within a campaign.",
        "input_schema": {
            "type": "object",
            "properties": {
                "campaign_id": {"type": "string", "description": "Parent campaign ID."},
                "status_filter": {
                    "type": "string",
                    "enum": ["ACTIVE", "PAUSED", "ARCHIVED", "DELETED", "ALL"],
                    "default": "ALL",
                },
            },
            "required": ["campaign_id"],
        },
    },
    {
        "name": "list_ads",
        "description": "List all ads within an ad set.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ad_set_id": {"type": "string", "description": "Parent ad set ID."},
                "status_filter": {
                    "type": "string",
                    "enum": ["ACTIVE", "PAUSED", "ARCHIVED", "DELETED", "ALL"],
                    "default": "ALL",
                },
            },
            "required": ["ad_set_id"],
        },
    },
]

# Map tool names to their implementation functions
TOOL_FUNCTIONS: dict[str, Any] = {
    "list_campaigns": meta_tools.list_campaigns,
    "get_campaign": meta_tools.get_campaign,
    "create_campaign": meta_tools.create_campaign,
    "update_campaign": meta_tools.update_campaign,
    "pause_campaign": meta_tools.pause_campaign,
    "resume_campaign": meta_tools.resume_campaign,
    "delete_campaign": meta_tools.delete_campaign,
    "get_campaign_insights": meta_tools.get_campaign_insights,
    "get_account_insights": meta_tools.get_account_insights,
    "list_ad_sets": meta_tools.list_ad_sets,
    "list_ads": meta_tools.list_ads,
}

SYSTEM_PROMPT = """You are an expert Meta (Facebook/Instagram) advertising agent.
You help users manage and optimise their Meta ad campaigns using the available tools.

Guidelines:
- Always be helpful and concise.
- When listing campaigns or insights, format the output clearly (use tables in markdown when useful).
- Before deleting anything, confirm the action with the user.
- When creating campaigns, set status to PAUSED unless the user explicitly asks to launch immediately.
- Budgets are always in the ad account's currency, in the smallest unit (cents for USD).
  Clarify this with the user if they don't specify.
- If a tool call fails, explain the error clearly and suggest what the user can do.
- Never make up campaign IDs — always fetch real data first.
"""


# ---------------------------------------------------------------------------
# Agent loop
# ---------------------------------------------------------------------------

def run_tool(name: str, inputs: dict) -> str:
    """Execute a tool and return its JSON-serialised result (or error string)."""
    func = TOOL_FUNCTIONS.get(name)
    if func is None:
        return json.dumps({"error": f"Unknown tool: {name}"})
    try:
        result = func(**inputs)
        return json.dumps(result, default=str, indent=2)
    except Exception as exc:  # noqa: BLE001
        return json.dumps({"error": str(exc)})


def run_agent(user_message: str, history: list[dict] | None = None) -> str:
    """
    Run one full agent turn (with tool calls) and return the final text response.

    Args:
        user_message: The user's natural-language request.
        history: Prior conversation turns (list of message dicts).

    Returns:
        The agent's final text response.
    """
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    messages: list[dict] = list(history or [])
    messages.append({"role": "user", "content": user_message})

    while True:
        response = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        # Collect text for display
        text_parts: list[str] = []
        tool_uses: list[dict] = []

        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_uses.append(block)

        # If the model is done (no more tool calls), return the final answer
        if response.stop_reason == "end_turn" or not tool_uses:
            return "\n".join(text_parts)

        # Otherwise, execute the tool calls and loop
        # Add assistant's response to history
        messages.append({"role": "assistant", "content": response.content})

        # Build tool results
        tool_results = []
        for tool_use in tool_uses:
            console.print(
                f"[dim]  → calling tool [bold]{tool_use.name}[/bold] "
                f"with {json.dumps(tool_use.input)}[/dim]"
            )
            result_str = run_tool(tool_use.name, tool_use.input)
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": result_str,
                }
            )

        messages.append({"role": "user", "content": tool_results})


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    console.print(
        Panel.fit(
            "[bold blue]Meta Campaigns Agent[/bold blue]\n"
            "[dim]Powered by Claude + Meta Marketing API[/dim]\n"
            "Type [bold]exit[/bold] or [bold]quit[/bold] to stop.",
            border_style="blue",
        )
    )

    # Check required env vars
    missing = [v for v in ("META_ACCESS_TOKEN", "META_AD_ACCOUNT_ID", "ANTHROPIC_API_KEY") if not os.environ.get(v)]
    if missing:
        console.print(
            f"[red]Error:[/red] Missing environment variables: {', '.join(missing)}\n"
            "Copy [bold].env.example[/bold] to [bold].env[/bold] and fill in your credentials."
        )
        sys.exit(1)

    # If a message was passed as CLI argument, run once and exit
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        console.print(f"\n[bold]You:[/bold] {query}\n")
        answer = run_agent(query)
        console.print(Markdown(answer))
        return

    # Interactive REPL
    history: list[dict] = []
    while True:
        try:
            user_input = console.input("\n[bold green]You:[/bold green] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Goodbye![/dim]")
            break

        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit", "q"}:
            console.print("[dim]Goodbye![/dim]")
            break

        console.print()
        answer = run_agent(user_input, history)

        # Update history for multi-turn conversation
        history.append({"role": "user", "content": user_input})
        history.append({"role": "assistant", "content": answer})

        console.print("[bold blue]Agent:[/bold blue]")
        console.print(Markdown(answer))


if __name__ == "__main__":
    main()
