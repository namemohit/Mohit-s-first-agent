"""
Meta Marketing API tools for the campaigns agent.
Each function maps directly to a tool the Claude agent can call.
"""

import os
from typing import Any

from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.campaign import Campaign
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.ad import Ad
from facebook_business.adobjects.adsinsights import AdsInsights


def _init_api() -> str:
    """Initialise the Facebook Ads API and return the ad account ID."""
    access_token = os.environ["META_ACCESS_TOKEN"]
    app_id = os.environ.get("META_APP_ID", "")
    app_secret = os.environ.get("META_APP_SECRET", "")
    ad_account_id = os.environ["META_AD_ACCOUNT_ID"]

    FacebookAdsApi.init(app_id, app_secret, access_token)
    return ad_account_id


# ---------------------------------------------------------------------------
# Campaign tools
# ---------------------------------------------------------------------------

def list_campaigns(status_filter: str = "ACTIVE") -> list[dict]:
    """
    List campaigns in the ad account.

    Args:
        status_filter: One of ACTIVE, PAUSED, ARCHIVED, DELETED, ALL.

    Returns:
        List of campaign dicts with id, name, status, objective, daily_budget,
        lifetime_budget, start_time, stop_time.
    """
    ad_account_id = _init_api()
    account = AdAccount(ad_account_id)

    fields = [
        Campaign.Field.id,
        Campaign.Field.name,
        Campaign.Field.status,
        Campaign.Field.objective,
        Campaign.Field.daily_budget,
        Campaign.Field.lifetime_budget,
        Campaign.Field.start_time,
        Campaign.Field.stop_time,
    ]

    params: dict[str, Any] = {}
    if status_filter != "ALL":
        params["effective_status"] = [status_filter]

    campaigns = account.get_campaigns(fields=fields, params=params)
    return [dict(c) for c in campaigns]


def get_campaign(campaign_id: str) -> dict:
    """
    Get details of a single campaign.

    Args:
        campaign_id: The campaign ID.

    Returns:
        Campaign details dict.
    """
    _init_api()
    fields = [
        Campaign.Field.id,
        Campaign.Field.name,
        Campaign.Field.status,
        Campaign.Field.objective,
        Campaign.Field.daily_budget,
        Campaign.Field.lifetime_budget,
        Campaign.Field.start_time,
        Campaign.Field.stop_time,
        Campaign.Field.budget_remaining,
        Campaign.Field.spend_cap,
    ]
    campaign = Campaign(campaign_id)
    campaign.remote_read(fields=fields)
    return dict(campaign)


def create_campaign(
    name: str,
    objective: str,
    status: str = "PAUSED",
    daily_budget: int | None = None,
    lifetime_budget: int | None = None,
    start_time: str | None = None,
    stop_time: str | None = None,
    special_ad_categories: list[str] | None = None,
) -> dict:
    """
    Create a new campaign.

    Args:
        name: Campaign name.
        objective: One of OUTCOME_AWARENESS, OUTCOME_TRAFFIC, OUTCOME_ENGAGEMENT,
                   OUTCOME_LEADS, OUTCOME_APP_PROMOTION, OUTCOME_SALES.
        status: ACTIVE or PAUSED (default PAUSED for safety).
        daily_budget: Daily budget in account currency cents (e.g. 1000 = $10.00).
        lifetime_budget: Lifetime budget in account currency cents.
        start_time: ISO 8601 datetime string, e.g. "2025-01-01T00:00:00".
        stop_time: ISO 8601 datetime string.
        special_ad_categories: List of special ad category strings (e.g. ["CREDIT"]).

    Returns:
        Dict with the new campaign's id and name.
    """
    ad_account_id = _init_api()
    account = AdAccount(ad_account_id)

    params: dict[str, Any] = {
        Campaign.Field.name: name,
        Campaign.Field.objective: objective,
        Campaign.Field.status: status,
        Campaign.Field.special_ad_categories: special_ad_categories or [],
    }
    if daily_budget is not None:
        params[Campaign.Field.daily_budget] = daily_budget
    if lifetime_budget is not None:
        params[Campaign.Field.lifetime_budget] = lifetime_budget
    if start_time:
        params[Campaign.Field.start_time] = start_time
    if stop_time:
        params[Campaign.Field.stop_time] = stop_time

    campaign = account.create_campaign(fields=[Campaign.Field.id, Campaign.Field.name], params=params)
    return dict(campaign)


def update_campaign(
    campaign_id: str,
    name: str | None = None,
    status: str | None = None,
    daily_budget: int | None = None,
    lifetime_budget: int | None = None,
    stop_time: str | None = None,
) -> dict:
    """
    Update an existing campaign.

    Args:
        campaign_id: The campaign ID to update.
        name: New campaign name (optional).
        status: New status – ACTIVE or PAUSED (optional).
        daily_budget: New daily budget in cents (optional).
        lifetime_budget: New lifetime budget in cents (optional).
        stop_time: New stop time ISO 8601 string (optional).

    Returns:
        Dict with success flag and campaign_id.
    """
    _init_api()
    campaign = Campaign(campaign_id)

    params: dict[str, Any] = {}
    if name is not None:
        params[Campaign.Field.name] = name
    if status is not None:
        params[Campaign.Field.status] = status
    if daily_budget is not None:
        params[Campaign.Field.daily_budget] = daily_budget
    if lifetime_budget is not None:
        params[Campaign.Field.lifetime_budget] = lifetime_budget
    if stop_time is not None:
        params[Campaign.Field.stop_time] = stop_time

    if not params:
        return {"success": False, "error": "No fields provided to update."}

    campaign.remote_update(params=params)
    return {"success": True, "campaign_id": campaign_id}


def pause_campaign(campaign_id: str) -> dict:
    """
    Pause a running campaign.

    Args:
        campaign_id: The campaign ID to pause.

    Returns:
        Dict with success flag.
    """
    return update_campaign(campaign_id, status="PAUSED")


def resume_campaign(campaign_id: str) -> dict:
    """
    Resume (activate) a paused campaign.

    Args:
        campaign_id: The campaign ID to activate.

    Returns:
        Dict with success flag.
    """
    return update_campaign(campaign_id, status="ACTIVE")


def delete_campaign(campaign_id: str) -> dict:
    """
    Delete a campaign.

    Args:
        campaign_id: The campaign ID to delete.

    Returns:
        Dict with success flag.
    """
    _init_api()
    campaign = Campaign(campaign_id)
    campaign.remote_delete()
    return {"success": True, "campaign_id": campaign_id}


# ---------------------------------------------------------------------------
# Insights / analytics tools
# ---------------------------------------------------------------------------

def get_campaign_insights(
    campaign_id: str,
    date_preset: str = "last_7d",
    start_date: str | None = None,
    end_date: str | None = None,
    breakdown: str | None = None,
) -> list[dict]:
    """
    Get performance insights for a campaign.

    Args:
        campaign_id: The campaign ID.
        date_preset: One of today, yesterday, last_7d, last_30d, last_90d,
                     this_month, last_month, last_year. Ignored if start_date/end_date set.
        start_date: Start date YYYY-MM-DD (optional, overrides date_preset).
        end_date: End date YYYY-MM-DD (optional, overrides date_preset).
        breakdown: Optional breakdown dimension e.g. age, gender, country, placement.

    Returns:
        List of insight row dicts.
    """
    _init_api()
    campaign = Campaign(campaign_id)

    fields = [
        AdsInsights.Field.campaign_id,
        AdsInsights.Field.campaign_name,
        AdsInsights.Field.impressions,
        AdsInsights.Field.reach,
        AdsInsights.Field.clicks,
        AdsInsights.Field.ctr,
        AdsInsights.Field.spend,
        AdsInsights.Field.cpm,
        AdsInsights.Field.cpc,
        AdsInsights.Field.actions,
        AdsInsights.Field.cost_per_action_type,
        AdsInsights.Field.frequency,
        AdsInsights.Field.date_start,
        AdsInsights.Field.date_stop,
    ]

    params: dict[str, Any] = {"level": "campaign"}

    if start_date and end_date:
        params["time_range"] = {"since": start_date, "until": end_date}
    else:
        params["date_preset"] = date_preset

    if breakdown:
        params["breakdowns"] = [breakdown]

    insights = campaign.get_insights(fields=fields, params=params)
    return [dict(row) for row in insights]


def get_account_insights(
    date_preset: str = "last_7d",
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict]:
    """
    Get account-level performance insights.

    Args:
        date_preset: One of today, yesterday, last_7d, last_30d, last_90d,
                     this_month, last_month, last_year.
        start_date: Start date YYYY-MM-DD (optional, overrides date_preset).
        end_date: End date YYYY-MM-DD (optional, overrides date_preset).

    Returns:
        List of insight row dicts.
    """
    ad_account_id = _init_api()
    account = AdAccount(ad_account_id)

    fields = [
        AdsInsights.Field.impressions,
        AdsInsights.Field.reach,
        AdsInsights.Field.clicks,
        AdsInsights.Field.ctr,
        AdsInsights.Field.spend,
        AdsInsights.Field.cpm,
        AdsInsights.Field.cpc,
        AdsInsights.Field.actions,
        AdsInsights.Field.date_start,
        AdsInsights.Field.date_stop,
    ]

    params: dict[str, Any] = {"level": "account"}
    if start_date and end_date:
        params["time_range"] = {"since": start_date, "until": end_date}
    else:
        params["date_preset"] = date_preset

    insights = account.get_insights(fields=fields, params=params)
    return [dict(row) for row in insights]


# ---------------------------------------------------------------------------
# Ad Set tools
# ---------------------------------------------------------------------------

def list_ad_sets(campaign_id: str, status_filter: str = "ALL") -> list[dict]:
    """
    List ad sets within a campaign.

    Args:
        campaign_id: The parent campaign ID.
        status_filter: ACTIVE, PAUSED, ARCHIVED, DELETED, or ALL.

    Returns:
        List of ad set dicts.
    """
    _init_api()
    campaign = Campaign(campaign_id)

    fields = [
        AdSet.Field.id,
        AdSet.Field.name,
        AdSet.Field.status,
        AdSet.Field.daily_budget,
        AdSet.Field.lifetime_budget,
        AdSet.Field.targeting,
        AdSet.Field.optimization_goal,
        AdSet.Field.billing_event,
        AdSet.Field.bid_amount,
        AdSet.Field.start_time,
        AdSet.Field.end_time,
    ]

    params: dict[str, Any] = {}
    if status_filter != "ALL":
        params["effective_status"] = [status_filter]

    ad_sets = campaign.get_ad_sets(fields=fields, params=params)
    return [dict(a) for a in ad_sets]


def list_ads(ad_set_id: str, status_filter: str = "ALL") -> list[dict]:
    """
    List ads within an ad set.

    Args:
        ad_set_id: The parent ad set ID.
        status_filter: ACTIVE, PAUSED, ARCHIVED, DELETED, or ALL.

    Returns:
        List of ad dicts.
    """
    _init_api()
    ad_set = AdSet(ad_set_id)

    fields = [
        Ad.Field.id,
        Ad.Field.name,
        Ad.Field.status,
        Ad.Field.creative,
        Ad.Field.adset_id,
        Ad.Field.campaign_id,
    ]

    params: dict[str, Any] = {}
    if status_filter != "ALL":
        params["effective_status"] = [status_filter]

    ads = ad_set.get_ads(fields=fields, params=params)
    return [dict(a) for a in ads]
