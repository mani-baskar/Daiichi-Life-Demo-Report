#!/usr/bin/env python3
"""Generate deterministic synthetic life-insurance demo data.

The output is designed for an Azure -> Fabric -> Power BI demonstration. It
contains no real customer data and must not be presented as Daiichi Life data.
"""

from __future__ import annotations

import argparse
import calendar
import json
import math
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd


TABLE_ORDER = [
    "DimDate",
    "DimCustomer",
    "DimProduct",
    "DimAgent",
    "FactPolicy",
    "LeadConversion",
]

LEAKAGE_COLUMNS = {
    "ConvertedFlag",
    "ConversionDate",
    "LostReason",
    "LeadStage",
    "ConversionProbability",
    "PredictedConvertedFlag",
    "PropensityBand",
    "ModelVersion",
    "ScoredAt",
}

MODEL_FEATURES = {
    "LeadSource",
    "DistributionChannel",
    "Region",
    "IncomeBandSGD",
    "ExistingCustomerFlag",
    "ProductInterest",
    "AgentKey",
    "EstimatedAnnualPremiumSGD",
    "ContactAttempts",
    "FirstResponseHours",
    "FollowUpCount",
    "DigitalEngagementScore",
    "NeedsAssessmentScore",
    "AppointmentCompletedFlag",
    "QuoteProvidedFlag",
    "DaysSinceLeadCreated",
}

GEOGRAPHY: dict[str, list[tuple[str, float, float, tuple[str, ...]]]] = {
    "Central": [
        ("Toa Payoh", 1.3343, 103.8563, ("31", "32")),
        ("Queenstown", 1.2942, 103.7861, ("14", "15")),
        ("Bukit Merah", 1.2819, 103.8239, ("09", "10")),
        ("Novena", 1.3201, 103.8439, ("30", "31")),
        ("Downtown Core", 1.2867, 103.8535, ("01", "02", "04")),
    ],
    "East": [
        ("Tampines", 1.3520, 103.9446, ("52", "53")),
        ("Bedok", 1.3236, 103.9273, ("46", "47")),
        ("Pasir Ris", 1.3730, 103.9493, ("51",)),
    ],
    "North": [
        ("Woodlands", 1.4382, 103.7890, ("73", "74")),
        ("Yishun", 1.4293, 103.8355, ("76", "77")),
        ("Sembawang", 1.4491, 103.8185, ("75",)),
    ],
    "North-East": [
        ("Punggol", 1.3984, 103.9072, ("82",)),
        ("Sengkang", 1.3868, 103.8914, ("54", "55")),
        ("Hougang", 1.3714, 103.8920, ("53",)),
    ],
    "West": [
        ("Jurong East", 1.3329, 103.7436, ("60",)),
        ("Jurong West", 1.3404, 103.7090, ("64",)),
        ("Clementi", 1.3151, 103.7650, ("12",)),
        ("Bukit Batok", 1.3496, 103.7490, ("65",)),
    ],
}

CHANNELS = ["Agency", "Bancassurance", "Digital", "Broker / IFA", "Direct"]
PRODUCT_FAMILIES = [
    "Term Life",
    "Whole Life",
    "Endowment / Savings",
    "Investment Linked",
    "Critical Illness",
    "Retirement / Annuity",
]


@dataclass(frozen=True)
class RunSettings:
    root: Path
    start_date: pd.Timestamp
    end_date: pd.Timestamp
    date_end: pd.Timestamp
    seed: int
    scale: str
    counts: dict[str, int]
    dirty_rate: float
    output_formats: tuple[str, ...]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--scale", choices=("small", "medium", "large"), default="small")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--end-date", type=str, default=None, help="Override demo end date (YYYY-MM-DD).")
    parser.add_argument("--output-root", type=Path, default=None, help="Project root containing data/ and validation/.")
    parser.add_argument("--no-parquet", action="store_true", help="Write CSV only.")
    return parser.parse_args()


def load_settings(args: argparse.Namespace) -> RunSettings:
    script_root = Path(__file__).resolve().parents[1]
    config_path = args.config or script_root / "config" / "demo_config.json"
    with config_path.open("r", encoding="utf-8") as handle:
        config = json.load(handle)

    root = (args.output_root or script_root).resolve()
    start = pd.Timestamp(config["start_date"]).normalize()
    end = pd.Timestamp(args.end_date or config["demo_end_date"]).normalize()
    if end <= start:
        raise ValueError("demo_end_date must be after start_date")

    counts = {key: int(value) for key, value in config["scales"][args.scale].items()}
    if counts["agents"] < len(CHANNELS):
        raise ValueError("Each scale needs at least one agent per distribution channel")
    if counts["policies"] < 12 or counts["leads"] < len(CHANNELS):
        raise ValueError("Scale is too small to guarantee required category coverage")

    formats = [str(value).lower() for value in config.get("output_formats", ["csv"])]
    if args.no_parquet:
        formats = [value for value in formats if value != "parquet"]
    if "csv" not in formats:
        formats.insert(0, "csv")

    buffer_days = int(config.get("date_dimension_end_buffer_days", 366))
    return RunSettings(
        root=root,
        start_date=start,
        end_date=end,
        date_end=end + pd.Timedelta(days=buffer_days),
        seed=int(args.seed if args.seed is not None else config["random_seed"]),
        scale=args.scale,
        counts=counts,
        dirty_rate=float(config.get("raw_dirty_rate", 0.01)),
        output_formats=tuple(dict.fromkeys(formats)),
    )


def sigmoid(values: np.ndarray | float) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.asarray(values, dtype=float)))


def date_key(values: pd.Series | pd.DatetimeIndex) -> pd.Series:
    return pd.Series(pd.to_datetime(values)).dt.strftime("%Y%m%d").astype("int32")


def iso_date(values: pd.Series | pd.DatetimeIndex) -> pd.Series:
    return pd.Series(pd.to_datetime(values)).dt.date


def sample_dates(
    rng: np.random.Generator,
    count: int,
    start: pd.Timestamp,
    end: pd.Timestamp,
    ensure_every_month: bool = True,
) -> pd.Series:
    months = pd.period_range(start=start, end=end, freq="M")
    month_numbers = months.month.to_numpy()
    seasonality = np.array([0.91, 0.94, 1.01, 0.98, 1.03, 1.08, 0.99, 1.00, 1.06, 1.10, 1.16, 1.24])
    trend = np.linspace(0.90, 1.16, len(months))
    weights = seasonality[month_numbers - 1] * trend
    weights = weights / weights.sum()

    guaranteed = np.arange(len(months)) if ensure_every_month and count >= len(months) else np.array([], dtype=int)
    sampled = rng.choice(len(months), size=count - len(guaranteed), p=weights)
    month_indices = np.concatenate([guaranteed, sampled])
    rng.shuffle(month_indices)

    results: list[pd.Timestamp] = []
    for month_index in month_indices:
        period = months[int(month_index)]
        month_start = max(pd.Timestamp(period.start_time).normalize(), start)
        month_end = min(pd.Timestamp(period.end_time).normalize(), end)
        span = max(0, (month_end - month_start).days)
        results.append(month_start + pd.Timedelta(days=int(rng.integers(0, span + 1))))
    return pd.Series(results, dtype="datetime64[ns]")


def random_datetimes_between(
    rng: np.random.Generator, starts: pd.Series, end: pd.Timestamp
) -> pd.Series:
    starts_dt = pd.to_datetime(starts).reset_index(drop=True)
    max_seconds = ((end + pd.Timedelta(hours=23, minutes=59, seconds=59)) - starts_dt).dt.total_seconds()
    max_seconds = np.maximum(max_seconds.to_numpy(dtype=np.int64), 0)
    offsets = np.array([int(rng.integers(0, value + 1)) for value in max_seconds], dtype=np.int64)
    return starts_dt + pd.to_timedelta(offsets, unit="s")


def geography_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for region, areas in GEOGRAPHY.items():
        for planning_area, latitude, longitude, sectors in areas:
            rows.append(
                {
                    "Region": region,
                    "PlanningArea": planning_area,
                    "Latitude": latitude,
                    "Longitude": longitude,
                    "PostalSectors": sectors,
                }
            )
    return rows


def generate_dim_date(settings: RunSettings) -> pd.DataFrame:
    dates = pd.date_range(settings.start_date, settings.date_end, freq="D")
    frame = pd.DataFrame({"Date": dates})
    frame["DateKey"] = date_key(frame["Date"])
    frame["Year"] = frame["Date"].dt.year.astype("int16")
    frame["QuarterNumber"] = frame["Date"].dt.quarter.astype("int8")
    frame["Quarter"] = "Q" + frame["QuarterNumber"].astype(str)
    frame["MonthNumber"] = frame["Date"].dt.month.astype("int8")
    frame["MonthName"] = frame["Date"].dt.month_name()
    frame["YearMonth"] = frame["Date"].dt.strftime("%Y-%m")
    frame["WeekOfYear"] = frame["Date"].dt.isocalendar().week.astype("int16")
    frame["DayOfWeek"] = (frame["Date"].dt.dayofweek + 1).astype("int8")
    frame["DayName"] = frame["Date"].dt.day_name()
    frame["IsWeekend"] = frame["Date"].dt.dayofweek.ge(5).astype("int8")
    frame["IsMonthEnd"] = frame["Date"].dt.is_month_end.astype("int8")
    frame["IsQuarterEnd"] = frame["Date"].dt.is_quarter_end.astype("int8")
    frame["IsYearEnd"] = frame["Date"].dt.is_year_end.astype("int8")
    columns = [
        "DateKey", "Date", "Year", "Quarter", "QuarterNumber", "MonthNumber",
        "MonthName", "YearMonth", "WeekOfYear", "DayOfWeek", "DayName",
        "IsWeekend", "IsMonthEnd", "IsQuarterEnd", "IsYearEnd",
    ]
    frame["Date"] = iso_date(frame["Date"])
    return frame[columns]


def generate_dim_product() -> tuple[pd.DataFrame, dict[int, dict[str, Any]]]:
    definitions = [
        (1, "TL-A", "Secure Horizon Term", "Term Life", "Death", "Low", 18, 65, "SGD 300-1,800", "SGD 100k-1.5m", 0, 0, "2019-04-01", 0.0017, 100000, 1500000, (1, 2, 5, 10, 20)),
        (2, "TL-B", "Family Shield Term", "Term Life", "Death + TPD", "Standard", 18, 60, "SGD 450-2,400", "SGD 150k-1.2m", 0, 0, "2020-07-15", 0.0022, 150000, 1200000, (5, 10, 15, 20)),
        (3, "WL-A", "Lifetime Heritage", "Whole Life", "Death + TPD", "Standard", 18, 60, "SGD 1,800-9,000", "SGD 75k-750k", 0, 0, "2018-02-20", 0.0120, 75000, 750000, (20, 25, 30)),
        (4, "WL-B", "Legacy Plus", "Whole Life", "Death + CI", "Elevated", 21, 55, "SGD 2,400-12,000", "SGD 100k-800k", 0, 1, "2021-01-05", 0.0145, 100000, 800000, (20, 25, 30)),
        (5, "ES-A", "Future Builder Savings", "Endowment / Savings", "Savings + Death", "Low", 18, 65, "SGD 2,000-18,000", "SGD 50k-500k", 0, 0, "2017-09-01", 0.0200, 50000, 500000, (10, 15, 20)),
        (6, "ES-B", "Education Milestone", "Endowment / Savings", "Savings + Death", "Standard", 18, 55, "SGD 2,400-20,000", "SGD 60k-450k", 0, 0, "2022-03-18", 0.0220, 60000, 450000, (10, 15, 18)),
        (7, "IL-A", "Growth Navigator", "Investment Linked", "Death + Investment", "Elevated", 21, 65, "SGD 1,800-24,000", "SGD 100k-1m", 1, 0, "2020-11-09", 0.0090, 100000, 1000000, (10, 15, 20, 25)),
        (8, "IL-B", "Balanced Wealth Link", "Investment Linked", "Death + Investment", "Standard", 21, 60, "SGD 2,400-30,000", "SGD 150k-1.2m", 1, 0, "2023-05-12", 0.0100, 150000, 1200000, (10, 15, 20)),
        (9, "CI-A", "Critical Care Protect", "Critical Illness", "Critical Illness", "Elevated", 18, 60, "SGD 600-6,000", "SGD 50k-500k", 0, 1, "2019-08-22", 0.0065, 50000, 500000, (5, 10, 15, 20)),
        (10, "CI-B", "Early Stage Guard", "Critical Illness", "Early + Major CI", "Elevated", 18, 55, "SGD 900-7,500", "SGD 75k-400k", 0, 1, "2022-10-03", 0.0080, 75000, 400000, (5, 10, 15)),
        (11, "RA-A", "RetireIncome Select", "Retirement / Annuity", "Retirement Income", "Low", 35, 70, "SGD 3,600-36,000", "SGD 100k-1m", 0, 0, "2018-06-14", 0.0180, 100000, 1000000, (10, 15, 20)),
        (12, "RA-B", "Golden Years Annuity", "Retirement / Annuity", "Lifetime Income", "Standard", 40, 70, "SGD 4,800-48,000", "SGD 150k-1.2m", 0, 0, "2021-06-30", 0.0200, 150000, 1200000, (10, 15, 20)),
    ]
    columns = [
        "ProductKey", "ProductCode", "ProductName", "ProductFamily", "CoverageType",
        "RiskTier", "MinEntryAge", "MaxEntryAge", "TypicalPremiumBand",
        "TypicalSumAssuredBand", "InvestmentLinkedFlag", "CriticalIllnessFlag",
        "ProductLaunchDate", "PremiumRate", "MinSumAssured", "MaxSumAssured", "TermChoices",
    ]
    working = pd.DataFrame(definitions, columns=columns)
    working["ProductActiveFlag"] = 1
    internal = {
        int(row.ProductKey): {
            "premium_rate": float(row.PremiumRate),
            "sum_min": int(row.MinSumAssured),
            "sum_max": int(row.MaxSumAssured),
            "terms": tuple(int(value) for value in row.TermChoices),
        }
        for row in working.itertuples()
    }
    output = working.drop(columns=["PremiumRate", "MinSumAssured", "MaxSumAssured", "TermChoices"])
    output["ProductLaunchDate"] = pd.to_datetime(output["ProductLaunchDate"]).dt.date
    output = output[
        [
            "ProductKey", "ProductCode", "ProductName", "ProductFamily", "CoverageType",
            "RiskTier", "MinEntryAge", "MaxEntryAge", "TypicalPremiumBand",
            "TypicalSumAssuredBand", "InvestmentLinkedFlag", "CriticalIllnessFlag",
            "ProductActiveFlag", "ProductLaunchDate",
        ]
    ]
    return output, internal


def age_band(age: int) -> str:
    if age < 30:
        return "18-29"
    if age < 40:
        return "30-39"
    if age < 50:
        return "40-49"
    if age < 60:
        return "50-59"
    return "60+"


def generate_dim_customer(settings: RunSettings, rng: np.random.Generator) -> pd.DataFrame:
    count = settings.counts["customers"]
    ages = np.clip(np.rint(rng.normal(41, 13, count)), 18, 75).astype(int)
    income_bands = np.array(["Below 40k", "40k-79k", "80k-119k", "120k-199k", "200k+"])
    income = rng.choice(income_bands, count, p=[0.20, 0.34, 0.24, 0.15, 0.07])
    segment_map = {
        "Below 40k": "Emerging", "40k-79k": "Mass", "80k-119k": "Mass",
        "120k-199k": "Affluent", "200k+": "High Value",
    }
    geography = geography_rows()
    geo_weights = np.array([1.25 if row["Region"] == "Central" else 1.0 for row in geography], dtype=float)
    geo_weights /= geo_weights.sum()
    geo_index = rng.choice(len(geography), count, p=geo_weights)
    existing = rng.binomial(1, np.clip(0.20 + (ages - 18) * 0.009, 0.20, 0.68))
    since_start = pd.Timestamp("2012-01-01")
    customer_since = sample_dates(rng, count, since_start, settings.end_date, ensure_every_month=False)

    rows: list[dict[str, Any]] = []
    for index in range(count):
        geo = geography[int(geo_index[index])]
        band = str(income[index])
        segment = segment_map[band]
        if rng.random() < 0.08:
            segment = rng.choice(["Emerging", "Mass", "Affluent", "High Value"])
        marital_prob = min(0.84, max(0.12, (ages[index] - 18) / 48))
        marital = rng.choice(["Single", "Married", "Divorced", "Widowed"], p=[1 - marital_prob, marital_prob * 0.80, marital_prob * 0.13, marital_prob * 0.07])
        rows.append(
            {
                "CustomerKey": index + 1,
                "CustomerID": f"CUS{index + 1:07d}",
                "Age": int(ages[index]),
                "AgeBand": age_band(int(ages[index])),
                "Gender": rng.choice(["Female", "Male", "Non-binary", "Prefer not to say"], p=[0.49, 0.48, 0.01, 0.02]),
                "OccupationCategory": rng.choice(["Professional", "Manager", "Service", "Technical", "Self-employed", "Homemaker", "Retired", "Student"], p=[0.25, 0.15, 0.14, 0.14, 0.12, 0.07, 0.08, 0.05]),
                "IncomeBandSGD": band,
                "MaritalStatus": marital,
                "ExistingCustomerFlag": int(existing[index]),
                "CustomerSegment": segment,
                "Region": geo["Region"],
                "PlanningArea": geo["PlanningArea"],
                "PostalSector": rng.choice(geo["PostalSectors"]),
                "PlanningAreaLatitude": geo["Latitude"],
                "PlanningAreaLongitude": geo["Longitude"],
                "ConsentForMarketingFlag": int(rng.random() < (0.70 if existing[index] else 0.58)),
                "CustomerSinceDate": customer_since.iloc[index].date(),
            }
        )
    return pd.DataFrame(rows)


def generate_dim_agent(settings: RunSettings, rng: np.random.Generator) -> pd.DataFrame:
    count = settings.counts["agents"]
    channels = np.array(CHANNELS + list(rng.choice(CHANNELS, count - len(CHANNELS), p=[0.36, 0.24, 0.15, 0.13, 0.12])))
    rng.shuffle(channels)
    geography = geography_rows()
    syllables_a = ["Ari", "Ben", "Cara", "Dev", "Eli", "Far", "Gia", "Han", "Ira", "Jia", "Kai", "Lena", "Mira", "Nave", "Owen", "Priya", "Ravi", "Sora", "Tara", "Wei"]
    syllables_b = ["Tan", "Lim", "Ng", "Lee", "Koh", "Nair", "Das", "Wong", "Chen", "Yeo", "Goh", "Rao"]
    join_dates = sample_dates(rng, count, pd.Timestamp("2010-01-01"), settings.end_date - pd.Timedelta(days=30), ensure_every_month=False)
    rows: list[dict[str, Any]] = []
    for index, channel in enumerate(channels):
        geo = geography[int(rng.integers(0, len(geography)))]
        tenure = max(1, (settings.end_date.year - join_dates.iloc[index].year) * 12 + settings.end_date.month - join_dates.iloc[index].month)
        grade = "Premier" if tenure >= 84 and rng.random() < 0.58 else "Senior" if tenure >= 30 else "Associate"
        if channel == "Digital":
            name = f"Digital Team {index + 1:03d}"
            branch = "Virtual Service Hub"
        else:
            name = f"{rng.choice(syllables_a)} {rng.choice(syllables_b)}"
            branch = f"{geo['PlanningArea']} Advisory Centre"
        grade_target = {"Associate": 45000, "Senior": 80000, "Premier": 135000}[grade]
        channel_factor = {"Agency": 1.08, "Bancassurance": 1.18, "Digital": 1.35, "Broker / IFA": 1.12, "Direct": 0.92}[str(channel)]
        rows.append(
            {
                "AgentKey": index + 1,
                "AgentID": f"AGT{index + 1:05d}",
                "AgentName": name,
                "DistributionChannel": str(channel),
                "BranchName": branch,
                "Region": geo["Region"],
                "PlanningArea": geo["PlanningArea"],
                "BranchLatitude": geo["Latitude"],
                "BranchLongitude": geo["Longitude"],
                "AgentJoinDate": join_dates.iloc[index].date(),
                "AgentTenureMonths": int(tenure),
                "AgentGrade": grade,
                "MonthlyTargetSGD": round(grade_target * channel_factor * float(rng.lognormal(0, 0.12)), 2),
                "ActiveFlag": int(rng.random() < 0.93),
            }
        )
    return pd.DataFrame(rows)


def choose_products(rng: np.random.Generator, count: int) -> np.ndarray:
    weights = np.array([0.13, 0.09, 0.10, 0.07, 0.10, 0.07, 0.10, 0.06, 0.09, 0.06, 0.07, 0.06])
    forced = np.arange(1, 13, dtype=int)
    chosen = np.concatenate([forced, rng.choice(np.arange(1, 13), count - len(forced), p=weights)])
    rng.shuffle(chosen)
    return chosen


def choose_agents_by_channel(
    rng: np.random.Generator, agents: pd.DataFrame, channels: np.ndarray
) -> np.ndarray:
    result = np.empty(len(channels), dtype=int)
    for channel in CHANNELS:
        candidate_keys = agents.loc[agents["DistributionChannel"].eq(channel), "AgentKey"].to_numpy(dtype=int)
        positions = np.flatnonzero(channels == channel)
        result[positions] = rng.choice(candidate_keys, len(positions))
    return result


def generate_fact_policy(
    settings: RunSettings,
    rng: np.random.Generator,
    customers: pd.DataFrame,
    products: pd.DataFrame,
    product_rules: dict[int, dict[str, Any]],
    agents: pd.DataFrame,
) -> pd.DataFrame:
    count = settings.counts["policies"]
    product_keys = choose_products(rng, count)
    customer_keys = np.empty(count, dtype=int)
    customer_age = customers.set_index("CustomerKey")["Age"]
    for key in range(1, 13):
        product = products.loc[products["ProductKey"].eq(key)].iloc[0]
        eligible = customers.loc[
            customers["Age"].between(int(product["MinEntryAge"]), int(product["MaxEntryAge"])), "CustomerKey"
        ].to_numpy(dtype=int)
        positions = np.flatnonzero(product_keys == key)
        customer_keys[positions] = rng.choice(eligible, len(positions))

    channel_weights = {
        "Term Life": [0.30, 0.18, 0.27, 0.10, 0.15],
        "Whole Life": [0.40, 0.27, 0.08, 0.17, 0.08],
        "Endowment / Savings": [0.29, 0.39, 0.08, 0.13, 0.11],
        "Investment Linked": [0.34, 0.18, 0.16, 0.24, 0.08],
        "Critical Illness": [0.35, 0.21, 0.18, 0.14, 0.12],
        "Retirement / Annuity": [0.31, 0.38, 0.06, 0.18, 0.07],
    }
    product_family = products.set_index("ProductKey").loc[product_keys, "ProductFamily"].to_numpy()
    acquisition_channels = np.array([rng.choice(CHANNELS, p=channel_weights[str(family)]) for family in product_family])
    for index, channel in enumerate(CHANNELS):
        acquisition_channels[index] = channel
    agent_keys = choose_agents_by_channel(rng, agents, acquisition_channels)

    application_dates = sample_dates(rng, count, settings.start_date, settings.end_date)
    raw_delays = np.clip(np.rint(rng.gamma(shape=2.2, scale=4.2, size=count)), 0, 45).astype(int)
    available_days = (settings.end_date - application_dates).dt.days.to_numpy(dtype=int)
    issue_delays = np.minimum(raw_delays, available_days)
    issue_dates = application_dates + pd.to_timedelta(issue_delays, unit="D")
    renewal_dates = issue_dates + pd.to_timedelta(365, unit="D")

    ages = customer_age.loc[customer_keys].to_numpy(dtype=int)
    underwriting_score = (ages - 18) / 57 + rng.normal(0, 0.22, count)
    risk_bands = np.where(underwriting_score > 0.72, "Elevated", np.where(underwriting_score < 0.28, "Low", "Standard"))
    decisions = np.where(risk_bands == "Elevated", "Approved with Loading", "Approved")

    sum_assured = np.empty(count, dtype=float)
    terms = np.empty(count, dtype=int)
    premium_rates = np.empty(count, dtype=float)
    for key, rules in product_rules.items():
        positions = np.flatnonzero(product_keys == key)
        logs = rng.uniform(math.log(rules["sum_min"]), math.log(rules["sum_max"]), len(positions))
        sum_assured[positions] = np.round(np.exp(logs) / 1000) * 1000
        terms[positions] = rng.choice(rules["terms"], len(positions))
        premium_rates[positions] = rules["premium_rate"]

    age_factor = np.clip(0.78 + ages * 0.012, 0.88, 1.72)
    risk_factor = np.select([risk_bands == "Low", risk_bands == "Elevated"], [0.88, 1.32], default=1.0)
    channel_factor = pd.Series(acquisition_channels).map({"Agency": 1.04, "Bancassurance": 0.97, "Digital": 0.90, "Broker / IFA": 1.02, "Direct": 0.94}).to_numpy()
    annual_premium = sum_assured * premium_rates * age_factor * risk_factor * channel_factor * rng.lognormal(0, 0.24, count)
    annual_premium = np.round(np.clip(annual_premium, 240, 52000), 2)

    maturity_dates = issue_dates + pd.to_timedelta(np.rint(terms * 365.25).astype(int), unit="D")
    status = np.full(count, "Active", dtype=object)
    matured_candidates = maturity_dates.le(settings.end_date).to_numpy()
    status[matured_candidates] = "Matured"
    non_matured = np.flatnonzero(~matured_candidates)
    tenure_years = ((settings.end_date - issue_dates).dt.days.to_numpy() / 365.25)
    lapse_probability = np.clip(0.04 + tenure_years * 0.025 + (risk_bands == "Elevated") * 0.025, 0.03, 0.22)
    random_status = rng.random(count)
    status[(random_status < 0.035) & ~matured_candidates] = "Cancelled"
    status[(random_status >= 0.035) & (random_status < 0.035 + lapse_probability) & ~matured_candidates] = "Lapsed"
    status[(random_status >= 0.035 + lapse_probability) & (random_status < 0.035 + lapse_probability + 0.035) & ~matured_candidates] = "Claimed"
    if len(non_matured) >= 4:
        for forced_status, position in zip(["Active", "Lapsed", "Claimed", "Cancelled"], non_matured[:4]):
            status[position] = forced_status
    same_day_claims = (status == "Claimed") & issue_dates.ge(settings.end_date).to_numpy()
    status[same_day_claims] = "Active"
    if not np.any(status == "Claimed"):
        claimable = np.flatnonzero((~matured_candidates) & issue_dates.lt(settings.end_date).to_numpy())
        if len(claimable):
            status[claimable[0]] = "Claimed"

    renewal_due = np.where(renewal_dates.le(settings.end_date), annual_premium, 0.0)
    renewal_probability = np.select(
        [status == "Active", status == "Claimed", status == "Matured"],
        [0.90, 0.80, 0.88],
        default=0.0,
    )
    renewal_paid_flag = ((rng.random(count) < renewal_probability) & (renewal_due > 0)).astype(int)
    renewal_paid_flag[np.isin(status, ["Lapsed", "Cancelled"])] = 0
    renewal_paid = np.round(renewal_due * renewal_paid_flag, 2)

    claim_count = np.zeros(count, dtype=int)
    claim_paid = np.zeros(count, dtype=float)
    claim_status = np.full(count, "None", dtype=object)
    claim_dates = pd.Series(pd.NaT, index=np.arange(count), dtype="datetime64[ns]")
    claimed_positions = np.flatnonzero(status == "Claimed")
    if len(claimed_positions):
        claim_count[claimed_positions] = rng.choice([1, 2], len(claimed_positions), p=[0.94, 0.06])
        claim_paid[claimed_positions] = np.round(sum_assured[claimed_positions] * rng.uniform(0.08, 0.88, len(claimed_positions)), 2)
        claim_status[claimed_positions] = "Paid"
        for position in claimed_positions:
            days_available = max(0, (settings.end_date - issue_dates.iloc[position]).days)
            claim_dates.iloc[position] = issue_dates.iloc[position] + pd.Timedelta(days=int(rng.integers(1, days_available + 1)))

    payment_frequency = rng.choice(["Monthly", "Quarterly", "Half-yearly", "Annual"], count, p=[0.57, 0.17, 0.07, 0.19])
    monthly_equivalent = np.round(annual_premium / 12, 2)
    last_modified = random_datetimes_between(rng, issue_dates, settings.end_date)

    frame = pd.DataFrame(
        {
            "PolicyKey": np.arange(1, count + 1, dtype=int),
            "PolicyID": [f"POL{value:09d}" for value in range(1, count + 1)],
            "CustomerKey": customer_keys,
            "ProductKey": product_keys,
            "AgentKey": agent_keys,
            "ApplicationDateKey": date_key(application_dates).to_numpy(),
            "IssueDateKey": date_key(issue_dates).to_numpy(),
            "RenewalDateKey": date_key(renewal_dates).to_numpy(),
            "ApplicationDate": application_dates.dt.date,
            "IssueDate": issue_dates.dt.date,
            "RenewalDate": renewal_dates.dt.date,
            "PolicyStatus": status,
            "PaymentFrequency": payment_frequency,
            "UnderwritingDecision": decisions,
            "UnderwritingRiskBand": risk_bands,
            "DaysToIssue": issue_delays,
            "AnnualPremiumSGD": annual_premium,
            "MonthlyEquivalentPremiumSGD": monthly_equivalent,
            "SumAssuredSGD": sum_assured.astype(int),
            "RenewalPremiumDueSGD": np.round(renewal_due, 2),
            "RenewalPremiumPaidSGD": renewal_paid,
            "RenewalPaidFlag": renewal_paid_flag,
            "LapseFlag": (status == "Lapsed").astype(int),
            "ClaimCount": claim_count,
            "ClaimPaidAmountSGD": claim_paid,
            "ClaimStatus": claim_status,
            "ClaimDate": claim_dates.dt.date,
            "PolicyTermYears": terms,
            "AcquisitionChannel": acquisition_channels,
            "LastModifiedDateTime": last_modified,
        }
    )
    return frame


def generate_leads(
    settings: RunSettings,
    rng: np.random.Generator,
    products: pd.DataFrame,
    product_rules: dict[int, dict[str, Any]],
    agents: pd.DataFrame,
) -> pd.DataFrame:
    count = settings.counts["leads"]
    product_keys = choose_products(rng, count)
    product_lookup = products.set_index("ProductKey")
    product_names = product_lookup.loc[product_keys, "ProductName"].to_numpy()
    family = product_lookup.loc[product_keys, "ProductFamily"].to_numpy()

    channel_weights = [0.31, 0.24, 0.19, 0.12, 0.14]
    channels = np.array(CHANNELS + list(rng.choice(CHANNELS, count - len(CHANNELS), p=channel_weights)))
    rng.shuffle(channels)
    agent_keys = choose_agents_by_channel(rng, agents, channels)
    agent_lookup = agents.set_index("AgentKey")
    agent_tenure = agent_lookup.loc[agent_keys, "AgentTenureMonths"].to_numpy(dtype=float)
    region = agent_lookup.loc[agent_keys, "Region"].to_numpy()
    planning_area = agent_lookup.loc[agent_keys, "PlanningArea"].to_numpy()

    created = sample_dates(rng, count, settings.start_date, settings.end_date)
    days_since = (settings.end_date - created).dt.days.to_numpy(dtype=int)
    recent_factor = np.clip(1 - days_since / 120, 0, 1)
    open_probability = np.clip(0.08 + 0.70 * recent_factor, 0.08, 0.76)
    is_open = rng.random(count) < open_probability

    income_bands = np.array(["Below 40k", "40k-79k", "80k-119k", "120k-199k", "200k+"])
    income = rng.choice(income_bands, count, p=[0.19, 0.35, 0.25, 0.14, 0.07])
    income_mid = pd.Series(income).map({"Below 40k": 32000, "40k-79k": 60000, "80k-119k": 100000, "120k-199k": 155000, "200k+": 250000}).to_numpy(dtype=float)
    existing = rng.binomial(1, 0.37, count)
    age_bands = rng.choice(["18-29", "30-39", "40-49", "50-59", "60+"], count, p=[0.18, 0.29, 0.26, 0.18, 0.09])

    sources = np.empty(count, dtype=object)
    for index in range(count):
        if existing[index] and rng.random() < 0.34:
            sources[index] = "Existing Customer Cross-sell"
        else:
            sources[index] = rng.choice(["Website", "Referral", "Branch", "Bancassurance", "Campaign", "Agent Prospecting"], p=[0.23, 0.18, 0.16, 0.17, 0.13, 0.13])

    estimated_premium = np.empty(count, dtype=float)
    for key, rules in product_rules.items():
        positions = np.flatnonzero(product_keys == key)
        typical_sum = math.sqrt(rules["sum_min"] * rules["sum_max"])
        estimated_premium[positions] = typical_sum * rules["premium_rate"] * rng.lognormal(0, 0.36, len(positions))
    estimated_premium = np.round(np.clip(estimated_premium, 240, 50000), 2)

    digital_base = rng.beta(2.2, 2.0, count) * 100
    digital_base += np.where(np.isin(sources, ["Website", "Campaign"]), 13, -3)
    digital_score = np.clip(np.rint(digital_base), 0, 100).astype(int)
    needs_score = np.clip(np.rint(rng.beta(2.4, 1.9, count) * 100 + existing * 6), 0, 100).astype(int)
    response_base = rng.lognormal(mean=2.1, sigma=0.85, size=count)
    response_base *= np.where(channels == "Digital", 0.55, 1.0)
    response_base *= np.where(sources == "Referral", 0.78, 1.0)
    first_response = np.round(np.clip(response_base, 0.2, 168), 1)
    contact_attempts = np.clip(rng.poisson(2.5, count), 0, 12).astype(int)
    followups = np.clip(contact_attempts - 1 + rng.integers(-1, 2, count), 0, 10).astype(int)

    appointment_logit = -1.25 + needs_score / 48 + existing * 0.30 - np.log1p(first_response) * 0.18 + np.isin(sources, ["Referral", "Existing Customer Cross-sell"]) * 0.40
    appointment = (rng.random(count) < sigmoid(appointment_logit)).astype(int)
    quote_logit = -1.35 + appointment * 1.85 + needs_score / 75 + digital_score / 160
    quote = (rng.random(count) < sigmoid(quote_logit)).astype(int)

    affordability = estimated_premium / income_mid
    healthy_followup = ((followups >= 1) & (followups <= 4)).astype(int)
    too_many_followups = (followups >= 7).astype(int)
    source_bonus = np.isin(sources, ["Referral", "Existing Customer Cross-sell"]).astype(int)
    slow_response = (first_response > 36).astype(int)
    fast_response = (first_response <= 6).astype(int)
    aging_penalty = np.clip((days_since - 30) / 120, 0, 1)
    tenure_effect = np.clip((agent_tenure - 24) / 120, -0.25, 0.45)
    latent_logit = (
        -2.80
        + existing * 0.48
        + appointment * 1.10
        + quote * 1.20
        + (needs_score - 50) / 42
        + (digital_score - 50) / 95
        + fast_response * 0.48
        - slow_response * 0.60
        + healthy_followup * 0.34
        - too_many_followups * 0.62
        + source_bonus * 0.58
        + tenure_effect
        - np.clip((affordability - 0.10) * 5.2, 0, 1.1)
        - aging_penalty * 0.35
        + rng.normal(0, 0.65, count)
    )
    conversion_probability = sigmoid(latent_logit)
    converted = (rng.random(count) < conversion_probability).astype(int)
    converted[is_open] = 0

    lead_stage = np.full(count, "Lost", dtype=object)
    lead_stage[(~is_open) & (converted == 1)] = "Won"
    open_positions = np.flatnonzero(is_open)
    for position in open_positions:
        if quote[position] and followups[position] >= 2:
            lead_stage[position] = "Application"
        elif quote[position]:
            lead_stage[position] = "Quote"
        elif appointment[position]:
            lead_stage[position] = "Appointment"
        elif needs_score[position] >= 58:
            lead_stage[position] = "Qualified"
        elif contact_attempts[position] >= 1:
            lead_stage[position] = "Contacted"
        else:
            lead_stage[position] = "New"

    conversion_dates = pd.Series(pd.NaT, index=np.arange(count), dtype="datetime64[ns]")
    won_positions = np.flatnonzero((~is_open) & (converted == 1))
    for position in won_positions:
        available = max(0, (settings.end_date - created.iloc[position]).days)
        delay = min(int(rng.integers(1, 61)), available)
        conversion_dates.iloc[position] = created.iloc[position] + pd.Timedelta(days=delay)

    lost_reason = np.full(count, None, dtype=object)
    lost_positions = np.flatnonzero((~is_open) & (converted == 0))
    lost_reason[lost_positions] = rng.choice(
        ["No response", "Price concern", "Needs changed", "Competitor selected", "Not eligible", "Timing deferred"],
        len(lost_positions),
        p=[0.25, 0.22, 0.15, 0.14, 0.09, 0.15],
    )
    target = pd.Series(converted, dtype="Int64")
    target.loc[is_open] = pd.NA
    last_modified = random_datetimes_between(rng, created, settings.end_date)

    return pd.DataFrame(
        {
            "LeadID": [f"LEAD{value:09d}" for value in range(1, count + 1)],
            "LeadCreatedDate": created.dt.date,
            "LeadCreatedDateKey": date_key(created).to_numpy(),
            "ProductKey": product_keys,
            "AgentKey": agent_keys,
            "LeadSource": sources,
            "DistributionChannel": channels,
            "Region": region,
            "PlanningArea": planning_area,
            "AgeBand": age_bands,
            "IncomeBandSGD": income,
            "ExistingCustomerFlag": existing,
            "ProductInterest": product_names,
            "EstimatedAnnualPremiumSGD": estimated_premium,
            "ContactAttempts": contact_attempts,
            "FirstResponseHours": first_response,
            "FollowUpCount": followups,
            "DigitalEngagementScore": digital_score,
            "NeedsAssessmentScore": needs_score,
            "AppointmentCompletedFlag": appointment,
            "QuoteProvidedFlag": quote,
            "DaysSinceLeadCreated": days_since,
            "LeadStage": lead_stage,
            "ConvertedFlag": target,
            "ConversionDate": conversion_dates.dt.date,
            "LostReason": lost_reason,
            "ConversionProbability": pd.Series([pd.NA] * count, dtype="Float64"),
            "PredictedConvertedFlag": pd.Series([pd.NA] * count, dtype="Int64"),
            "PropensityBand": pd.Series([None] * count, dtype="object"),
            "ModelVersion": pd.Series([None] * count, dtype="object"),
            "ScoredAt": pd.Series([pd.NaT] * count, dtype="datetime64[ns]"),
            "LastModifiedDateTime": last_modified,
        }
    )


def add_raw_layer_issues(
    tables: dict[str, pd.DataFrame], rng: np.random.Generator, dirty_rate: float
) -> tuple[dict[str, pd.DataFrame], dict[str, int]]:
    raw = {name: frame.copy(deep=True) for name, frame in tables.items()}
    counts: dict[str, int] = {}

    def dirty(table: str, column: str, mode: str) -> None:
        frame = raw[table]
        affected = max(1, int(round(len(frame) * dirty_rate))) if len(frame) else 0
        indices = rng.choice(frame.index.to_numpy(), size=min(affected, len(frame)), replace=False)
        if mode == "missing":
            frame.loc[indices, column] = None
        elif mode == "space":
            frame.loc[indices, column] = frame.loc[indices, column].astype(str) + " "
        else:
            raise ValueError(mode)
        counts[f"{table}.{column}.{mode}"] = len(indices)

    dirty("DimCustomer", "OccupationCategory", "missing")
    dirty("DimCustomer", "PlanningArea", "space")
    dirty("DimProduct", "TypicalPremiumBand", "space")
    dirty("DimAgent", "BranchName", "missing")
    dirty("DimAgent", "AgentName", "space")
    dirty("FactPolicy", "PaymentFrequency", "missing")
    dirty("FactPolicy", "AcquisitionChannel", "space")
    dirty("LeadConversion", "LeadSource", "space")
    dirty("LeadConversion", "FirstResponseHours", "missing")
    return raw, counts


def build_validation_results(
    settings: RunSettings, tables: dict[str, pd.DataFrame]
) -> list[dict[str, Any]]:
    dates = tables["DimDate"]
    customers = tables["DimCustomer"]
    products = tables["DimProduct"]
    agents = tables["DimAgent"]
    policies = tables["FactPolicy"]
    leads = tables["LeadConversion"]
    results: list[dict[str, Any]] = []

    def add(check: str, observed: Any, expected: str, passed: bool, details: str) -> None:
        results.append({"Check": check, "Observed": observed, "Expected": expected, "Status": "PASS" if passed else "FAIL", "Details": details})

    pk_specs = {
        "DimDate": "DateKey", "DimCustomer": "CustomerKey", "DimProduct": "ProductKey",
        "DimAgent": "AgentKey", "FactPolicy": "PolicyKey", "LeadConversion": "LeadID",
    }
    duplicate_count = sum(int(tables[name][column].duplicated().sum()) for name, column in pk_specs.items())
    duplicate_count += int(policies["PolicyID"].duplicated().sum())
    add("Primary key duplicates", duplicate_count, "0", duplicate_count == 0, "Includes PolicyID uniqueness.")

    valid_dates = set(dates["DateKey"].astype(int))
    orphan_count = 0
    for column, valid in [
        ("CustomerKey", set(customers["CustomerKey"])),
        ("ProductKey", set(products["ProductKey"])),
        ("AgentKey", set(agents["AgentKey"])),
        ("ApplicationDateKey", valid_dates),
        ("IssueDateKey", valid_dates),
        ("RenewalDateKey", valid_dates),
    ]:
        orphan_count += int((~policies[column].isin(valid)).sum())
    for column, valid in [("ProductKey", set(products["ProductKey"])), ("AgentKey", set(agents["AgentKey"])), ("LeadCreatedDateKey", valid_dates)]:
        orphan_count += int((~leads[column].isin(valid)).sum())
    add("Orphan foreign keys", orphan_count, "0", orphan_count == 0, "Policy and lead dimension/date keys checked.")

    app = pd.to_datetime(policies["ApplicationDate"])
    issue = pd.to_datetime(policies["IssueDate"])
    renewal = pd.to_datetime(policies["RenewalDate"])
    conversion = pd.to_datetime(leads["ConversionDate"])
    lead_created = pd.to_datetime(leads["LeadCreatedDate"])
    claim_date = pd.to_datetime(policies["ClaimDate"])
    invalid_dates = int((issue < app).sum() + (renewal <= issue).sum() + ((conversion.notna()) & (conversion < lead_created)).sum() + ((claim_date.notna()) & (claim_date <= issue)).sum())
    add("Invalid date sequence", invalid_dates, "0", invalid_dates == 0, "Issue, renewal, conversion and claim sequences checked.")

    age_check = policies[["CustomerKey", "ProductKey"]].merge(customers[["CustomerKey", "Age"]], on="CustomerKey").merge(products[["ProductKey", "MinEntryAge", "MaxEntryAge"]], on="ProductKey")
    invalid_age = int((~age_check["Age"].between(age_check["MinEntryAge"], age_check["MaxEntryAge"])).sum())
    add("Invalid age/product eligibility", invalid_age, "0", invalid_age == 0, "Customer age checked against product entry ages.")

    nonpositive = int((policies["AnnualPremiumSGD"] <= 0).sum() + (policies["SumAssuredSGD"] <= 0).sum())
    add("Non-positive premium or sum assured", nonpositive, "0", nonpositive == 0, "Core monetary values must be positive.")

    invalid_claim = int(((policies["ClaimPaidAmountSGD"] < 0) | (policies["ClaimPaidAmountSGD"] > policies["SumAssuredSGD"])).sum())
    add("Invalid claim amount", invalid_claim, "0", invalid_claim == 0, "Paid claims cannot be negative or exceed sum assured.")

    valid_geo = {(region, area) for region, areas in GEOGRAPHY.items() for area, *_ in areas}
    invalid_geo = sum((region, area) not in valid_geo for region, area in customers[["Region", "PlanningArea"]].itertuples(index=False, name=None))
    invalid_geo += sum((region, area) not in valid_geo for region, area in agents[["Region", "PlanningArea"]].itertuples(index=False, name=None))
    invalid_geo += sum((region, area) not in valid_geo for region, area in leads[["Region", "PlanningArea"]].itertuples(index=False, name=None))
    add("Geography mapping", invalid_geo, "0 invalid pairs", invalid_geo == 0, "Singapore region/planning-area pairs checked.")

    maturity = issue + pd.to_timedelta(np.rint(policies["PolicyTermYears"] * 365.25).astype(int), unit="D")
    invalid_status = int(((policies["PolicyStatus"] == "Matured") & (maturity > settings.end_date)).sum())
    invalid_status += int(((policies["PolicyStatus"] == "Lapsed") & (policies["RenewalPaidFlag"] == 1)).sum())
    invalid_status += int(((policies["PolicyStatus"] == "Claimed") & ((policies["ClaimCount"] <= 0) | (policies["ClaimStatus"] == "None"))).sum())
    invalid_status += int((policies["LapseFlag"] != policies["PolicyStatus"].eq("Lapsed").astype(int)).sum())
    add("Policy status logic", invalid_status, "0", invalid_status == 0, "Maturity, lapse, claim and flag logic checked.")

    historical = leads.loc[leads["ConvertedFlag"].notna(), "ConvertedFlag"].astype(int)
    conversion_rate = float(historical.mean()) if len(historical) else float("nan")
    balanced = bool(0.15 <= conversion_rate <= 0.65)
    add("ML target balance", f"{conversion_rate:.2%}", "15%-65% converted", balanced, f"Historical completed leads: {len(historical):,}.")

    leakage_overlap = sorted(MODEL_FEATURES.intersection(LEAKAGE_COLUMNS))
    add("Leakage fields excluded", len(leakage_overlap), "0 leakage features", not leakage_overlap, ", ".join(leakage_overlap) if leakage_overlap else "Explicit allow-list excludes outcomes and model outputs.")

    expected_months = set(pd.period_range(settings.start_date, settings.end_date, freq="M").astype(str))
    policy_months = set(pd.to_datetime(policies["ApplicationDate"]).dt.to_period("M").astype(str))
    lead_months = set(pd.to_datetime(leads["LeadCreatedDate"]).dt.to_period("M").astype(str))
    missing_months = sorted((expected_months - policy_months) | (expected_months - lead_months))
    add("Every month represented", len(missing_months), "0 missing months", not missing_months, ", ".join(missing_months) if missing_months else "Policy applications and leads cover the full demo period.")

    represented_families = set(products["ProductFamily"]) & set(product_lookup for product_lookup in products.set_index("ProductKey").loc[policies["ProductKey"], "ProductFamily"])
    missing_families = sorted(set(PRODUCT_FAMILIES) - represented_families)
    missing_channels = sorted(set(CHANNELS) - set(policies["AcquisitionChannel"]) | set(CHANNELS) - set(leads["DistributionChannel"]))
    coverage_missing = len(missing_families) + len(missing_channels)
    add("Product family and channel coverage", coverage_missing, "All required categories", coverage_missing == 0, f"Missing families: {missing_families or 'none'}; missing channels: {missing_channels or 'none'}.")

    map_missing = int(customers[["PlanningAreaLatitude", "PlanningAreaLongitude"]].isna().sum().sum() + agents[["BranchLatitude", "BranchLongitude"]].isna().sum().sum())
    map_out_of_range = int((~customers["PlanningAreaLatitude"].between(1.20, 1.48)).sum() + (~customers["PlanningAreaLongitude"].between(103.60, 104.05)).sum())
    map_out_of_range += int((~agents["BranchLatitude"].between(1.20, 1.48)).sum() + (~agents["BranchLongitude"].between(103.60, 104.05)).sum())
    add("Map fields available", map_missing + map_out_of_range, "0 missing/out-of-range", map_missing + map_out_of_range == 0, "Planning-area and branch centroids checked.")

    currency_columns = {
        "DimAgent": ["MonthlyTargetSGD"],
        "FactPolicy": ["AnnualPremiumSGD", "MonthlyEquivalentPremiumSGD", "SumAssuredSGD", "RenewalPremiumDueSGD", "RenewalPremiumPaidSGD", "ClaimPaidAmountSGD"],
        "LeadConversion": ["EstimatedAnnualPremiumSGD"],
    }
    nonnumeric = 0
    for table_name, columns in currency_columns.items():
        nonnumeric += sum(not pd.api.types.is_numeric_dtype(tables[table_name][column]) for column in columns)
    add("Currency fields numeric", nonnumeric, "0 non-numeric columns", nonnumeric == 0, "All SGD measure columns checked by dtype.")

    last_modified_missing = int(policies["LastModifiedDateTime"].isna().sum() + leads["LastModifiedDateTime"].isna().sum())
    add("Incremental-load timestamps", last_modified_missing, "0 missing", last_modified_missing == 0, "FactPolicy and LeadConversion include LastModifiedDateTime.")

    return results


def write_tables(
    settings: RunSettings,
    curated: dict[str, pd.DataFrame],
    raw: dict[str, pd.DataFrame],
) -> dict[str, list[str]]:
    outputs: dict[str, list[str]] = {"csv": [], "parquet": [], "skipped": []}
    for layer, tables in [("raw", raw), ("curated", curated)]:
        output_dir = settings.root / "data" / layer
        output_dir.mkdir(parents=True, exist_ok=True)
        for table_name in TABLE_ORDER:
            frame = tables[table_name]
            if "csv" in settings.output_formats:
                path = output_dir / f"{table_name}.csv"
                frame.to_csv(path, index=False, encoding="utf-8", date_format="%Y-%m-%d %H:%M:%S")
                outputs["csv"].append(str(path.relative_to(settings.root)))
            if "parquet" in settings.output_formats:
                path = output_dir / f"{table_name}.parquet"
                try:
                    frame.to_parquet(path, index=False)
                    outputs["parquet"].append(str(path.relative_to(settings.root)))
                except (ImportError, ModuleNotFoundError) as exc:
                    outputs["skipped"].append(f"{path.name}: {exc.__class__.__name__}")
    return outputs


def write_validation_reports(
    settings: RunSettings,
    results: list[dict[str, Any]],
    tables: dict[str, pd.DataFrame],
    raw_issue_counts: dict[str, int],
    output_manifest: dict[str, list[str]],
) -> None:
    validation_dir = settings.root / "validation"
    validation_dir.mkdir(parents=True, exist_ok=True)
    summary = pd.DataFrame(results)
    summary.to_csv(validation_dir / "validation_summary.csv", index=False, encoding="utf-8")

    failed = summary.loc[summary["Status"].eq("FAIL")]
    historical = tables["LeadConversion"].loc[tables["LeadConversion"]["ConvertedFlag"].notna(), "ConvertedFlag"].astype(int)
    report_lines = [
        "# Data Quality Report",
        "",
        f"Generated: {datetime.now().isoformat(timespec='seconds')}",
        f"Scale: `{settings.scale}`",
        f"Random seed: `{settings.seed}`",
        f"Business date range: `{settings.start_date.date()}` to `{settings.end_date.date()}`",
        f"DimDate range: `{settings.start_date.date()}` to `{settings.date_end.date()}` (includes renewal-key buffer)",
        "",
        "> All records are synthetic. They do not represent Daiichi Life customers or business performance.",
        "",
        "## Outcome",
        "",
        f"**{'PASS' if failed.empty else 'FAIL'}** - {len(summary) - len(failed)} of {len(summary)} mandatory checks passed.",
        "",
        "## Curated row counts",
        "",
        "| Table | Rows |",
        "| --- | ---: |",
    ]
    report_lines.extend(f"| {name} | {len(tables[name]):,} |" for name in TABLE_ORDER)
    report_lines.extend([
        "",
        "## ML target",
        "",
        f"Historical completed leads: {len(historical):,}",
        f"Converted share: {historical.mean():.2%}",
        "Open leads keep the outcome fields blank and are intended for scoring.",
        "",
        "## Validation checks",
        "",
        "| Check | Observed | Expected | Status |",
        "| --- | ---: | --- | --- |",
    ])
    for row in results:
        report_lines.append(f"| {row['Check']} | {row['Observed']} | {row['Expected']} | {row['Status']} |")
    report_lines.extend([
        "",
        "## Raw-layer quality simulation",
        "",
        "Controlled issues exist only in non-key raw fields. The curated tables retain their clean values.",
        "",
        "| Raw field issue | Rows |",
        "| --- | ---: |",
    ])
    report_lines.extend(f"| {name} | {count:,} |" for name, count in sorted(raw_issue_counts.items()))
    report_lines.extend([
        "",
        "## Output formats",
        "",
        f"CSV files: {len(output_manifest['csv'])}",
        f"Parquet files: {len(output_manifest['parquet'])}",
    ])
    if output_manifest["skipped"]:
        report_lines.append(f"Parquet skips: {', '.join(output_manifest['skipped'])}")
    report_lines.append("")
    (validation_dir / "data_quality_report.md").write_text("\n".join(report_lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    settings = load_settings(args)
    rng = np.random.default_rng(settings.seed)

    products, product_rules = generate_dim_product()
    customers = generate_dim_customer(settings, rng)
    agents = generate_dim_agent(settings, rng)
    tables = {
        "DimDate": generate_dim_date(settings),
        "DimCustomer": customers,
        "DimProduct": products,
        "DimAgent": agents,
        "FactPolicy": generate_fact_policy(settings, rng, customers, products, product_rules, agents),
        "LeadConversion": generate_leads(settings, rng, products, product_rules, agents),
    }
    raw_tables, raw_issue_counts = add_raw_layer_issues(tables, rng, settings.dirty_rate)
    validation_results = build_validation_results(settings, tables)
    output_manifest = write_tables(settings, tables, raw_tables)
    write_validation_reports(settings, validation_results, tables, raw_issue_counts, output_manifest)

    failures = [row for row in validation_results if row["Status"] == "FAIL"]
    if failures:
        print("Validation failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure['Check']}: {failure['Details']}", file=sys.stderr)
        return 1

    print(f"Generated {settings.scale} dataset with seed {settings.seed}.")
    for name in TABLE_ORDER:
        print(f"  {name}: {len(tables[name]):,} curated rows")
    print(f"Validation: {len(validation_results)}/{len(validation_results)} checks passed")
    print(f"CSV files: {len(output_manifest['csv'])}; Parquet files: {len(output_manifest['parquet'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
