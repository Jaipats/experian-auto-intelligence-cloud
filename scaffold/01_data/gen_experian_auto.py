# =============================================================================
# Experian Automotive synthetic demo data generator
# Tier 1 + UC write (Polars + NumPy + Mimesis -> Databricks Connect serverless)
# Target: experian_agent_demo_catalog.auto
#   1. gold_vio_market    ~6,000 rows   (Vehicles in Operation / market stats)
#   2. gold_autocheck_vin ~20,000 rows  (AutoCheck vehicle history per VIN)
#   3. gold_lending       ~30,000 rows  (Automotive credit & lending)
# Shared pools: makes/models/model_years, ~40 zips w/ state+region -> join keys
# Seed = 42
# =============================================================================
import numpy as np
import polars as pl
import string
from databricks.connect import DatabricksSession

import os
PROFILE = os.environ.get("DBX_PROFILE", "sp-contoso")
CATALOG = "experian_agent_demo_catalog"
SCHEMA = "auto"

rng = np.random.default_rng(42)

# ---------------------------------------------------------------------------
# SHARED POOLS (guarantee join-key overlap across all 3 tables)
# ---------------------------------------------------------------------------
# 18 real make/model pairs with a canonical body_style + fuel_type + trims
MODELS = [
    # make,        model,        body_style, fuel_type, [trims]
    ("Toyota",     "RAV4",       "SUV",    "Gas",    ["LE", "XLE", "Limited", "TRD"]),
    ("Toyota",     "Camry",      "Sedan",  "Gas",    ["LE", "SE", "XSE", "XLE"]),
    ("Honda",      "CR-V",       "SUV",    "Gas",    ["LX", "EX", "EX-L", "Touring"]),
    ("Honda",      "Civic",      "Sedan",  "Gas",    ["LX", "Sport", "EX", "Touring"]),
    ("Ford",       "F-150",      "Truck",  "Gas",    ["XL", "XLT", "Lariat", "Platinum"]),
    ("Ford",       "Explorer",   "SUV",    "Gas",    ["Base", "XLT", "Limited", "ST"]),
    ("Chevrolet",  "Silverado",  "Truck",  "Gas",    ["WT", "LT", "RST", "High Country"]),
    ("Chevrolet",  "Equinox",    "SUV",    "Gas",    ["LS", "LT", "RS", "Premier"]),
    ("Tesla",      "Model 3",    "Sedan",  "EV",     ["Standard", "Long Range", "Performance"]),
    ("Tesla",      "Model Y",    "SUV",    "EV",     ["Long Range", "Performance"]),
    ("Nissan",     "Rogue",      "SUV",    "Gas",    ["S", "SV", "SL", "Platinum"]),
    ("Nissan",     "Altima",     "Sedan",  "Gas",    ["S", "SV", "SR", "SL"]),
    ("Jeep",       "Grand Cherokee", "SUV", "Gas",   ["Laredo", "Limited", "Overland", "Summit"]),
    ("Ram",        "1500",       "Truck",  "Gas",    ["Tradesman", "Big Horn", "Laramie", "Limited"]),
    ("Hyundai",    "Tucson",     "SUV",    "Hybrid", ["SE", "SEL", "Limited"]),
    ("Subaru",     "Outback",    "SUV",    "Gas",    ["Base", "Premium", "Limited", "Touring"]),
    ("Toyota",     "Sienna",     "Van",    "Hybrid", ["LE", "XLE", "Limited", "Platinum"]),
    ("Ford",       "F-250",      "Truck",  "Diesel", ["XL", "XLT", "Lariat", "King Ranch"]),
]
N_MODELS = len(MODELS)
MAKES  = [m[0] for m in MODELS]
MODLS  = [m[1] for m in MODELS]
BODY   = [m[2] for m in MODELS]
FUEL   = [m[3] for m in MODELS]
TRIMS  = [m[4] for m in MODELS]

MODEL_YEARS = list(range(2015, 2026))  # 2015-2025

# 40 shared zip codes with state + DMA region (real-ish geography)
GEO = [
    ("10001", "NY", "New York",        "Northeast"),
    ("10453", "NY", "New York",        "Northeast"),
    ("11201", "NY", "New York",        "Northeast"),
    ("07030", "NJ", "New York",        "Northeast"),
    ("02108", "MA", "Boston",          "Northeast"),
    ("02139", "MA", "Boston",          "Northeast"),
    ("19103", "PA", "Philadelphia",    "Northeast"),
    ("15213", "PA", "Pittsburgh",      "Northeast"),
    ("20001", "DC", "Washington DC",   "Southeast"),
    ("30303", "GA", "Atlanta",         "Southeast"),
    ("30329", "GA", "Atlanta",         "Southeast"),
    ("33101", "FL", "Miami",           "Southeast"),
    ("33602", "FL", "Tampa",           "Southeast"),
    ("32801", "FL", "Orlando",         "Southeast"),
    ("28202", "NC", "Charlotte",       "Southeast"),
    ("37203", "TN", "Nashville",       "Southeast"),
    ("60601", "IL", "Chicago",         "Midwest"),
    ("60614", "IL", "Chicago",         "Midwest"),
    ("48201", "MI", "Detroit",         "Midwest"),
    ("44113", "OH", "Cleveland",       "Midwest"),
    ("43215", "OH", "Columbus",        "Midwest"),
    ("55401", "MN", "Minneapolis",     "Midwest"),
    ("53202", "WI", "Milwaukee",       "Midwest"),
    ("63101", "MO", "St. Louis",       "Midwest"),
    ("75201", "TX", "Dallas",          "Southwest"),
    ("77002", "TX", "Houston",         "Southwest"),
    ("78701", "TX", "Austin",          "Southwest"),
    ("85004", "AZ", "Phoenix",         "Southwest"),
    ("87102", "NM", "Albuquerque",     "Southwest"),
    ("89101", "NV", "Las Vegas",       "Southwest"),
    ("80202", "CO", "Denver",          "Mountain"),
    ("84101", "UT", "Salt Lake City",  "Mountain"),
    ("83702", "ID", "Boise",           "Mountain"),
    ("90012", "CA", "Los Angeles",     "West"),
    ("90210", "CA", "Los Angeles",     "West"),
    ("94103", "CA", "San Francisco",   "West"),
    ("95814", "CA", "Sacramento",      "West"),
    ("98101", "WA", "Seattle",         "West"),
    ("97201", "OR", "Portland",        "West"),
    ("85281", "AZ", "Phoenix",         "West"),
]
N_GEO   = len(GEO)
ZIPS    = [g[0] for g in GEO]
STATES  = [g[1] for g in GEO]
DMAS    = [g[2] for g in GEO]
REGIONS = [g[3] for g in GEO]

def sample_geo(n):
    idx = rng.integers(0, N_GEO, size=n)
    return idx, (np.array(ZIPS)[idx], np.array(STATES)[idx],
                 np.array(DMAS)[idx], np.array(REGIONS)[idx])

def sample_models(n):
    idx = rng.integers(0, N_MODELS, size=n)
    trims = np.array([rng.choice(TRIMS[i]) for i in idx])
    return idx, (np.array(MAKES)[idx], np.array(MODLS)[idx],
                 np.array(BODY)[idx], np.array(FUEL)[idx], trims)

# ===========================================================================
# 1. gold_vio_market  (grid: model x geo x recent snapshot months)
# ===========================================================================
SNAP_MONTHS = ["2025-01-01", "2025-02-01", "2025-03-01", "2025-04-01",
               "2025-05-01", "2025-06-01"]
vio_rows = []
vio_id = 500000
for si, snap in enumerate(SNAP_MONTHS):
    for mi in range(N_MODELS):
        # each model appears in a random subset of ~20 metros per month
        geo_pick = rng.choice(N_GEO, size=20, replace=False)
        for gi in geo_pick:
            # two recent model years per model-geo-month cell
            for my in rng.choice(MODEL_YEARS, size=2, replace=False):
                my = int(my)
                base = {"SUV": 4200, "Sedan": 3100, "Truck": 3800,
                        "EV": 1500, "Van": 900}[BODY[mi]]
                reg = int(max(50, rng.normal(base, base * 0.35)))
                vio = int(reg * rng.uniform(3.5, 6.0))  # cumulative in-operation
                days_turn = int(np.clip(rng.normal(
                    {"EV": 34, "Truck": 55, "SUV": 45, "Sedan": 60, "Van": 70}[BODY[mi]],
                    12), 8, 140))
                vio_rows.append((
                    vio_id, MAKES[mi], MODLS[mi], rng.choice(TRIMS[mi]), my,
                    BODY[mi], FUEL[mi], ZIPS[gi], DMAS[gi], STATES[gi],
                    reg, vio, days_turn, snap))
                vio_id += 1

vio = pl.DataFrame(vio_rows, schema=[
    "vio_id", "make", "model", "trim", "model_year", "body_style", "fuel_type",
    "zip_code", "dma_region", "state", "registration_count", "vio_count",
    "avg_days_to_turn", "snapshot_month"], orient="row")
# market_share_pct: share of registrations within (state, snapshot_month)
vio = vio.with_columns([
    (pl.col("registration_count") /
     pl.col("registration_count").sum().over(["state", "snapshot_month"]) * 100
     ).round(2).alias("market_share_pct"),
    pl.col("snapshot_month").str.to_date().alias("snapshot_month"),
])
vio = vio.select([
    "vio_id", "make", "model", "trim", "model_year", "body_style", "fuel_type",
    "zip_code", "dma_region", "state", "registration_count", "vio_count",
    "market_share_pct", "avg_days_to_turn", "snapshot_month"])
print(f"gold_vio_market: {vio.height:,} rows")

# ===========================================================================
# 2. gold_autocheck_vin  (~20,000 rows)  VIN-level history
# ===========================================================================
N_VIN = 20_000
_, (v_make, v_model, v_body, v_fuel, v_trim) = sample_models(N_VIN)
_, (z_zip, z_state, z_dma, z_region) = sample_geo(N_VIN)
v_year = rng.integers(2015, 2026, size=N_VIN)
age = 2026 - v_year
mileage = np.clip((age * rng.normal(12500, 3500, N_VIN)).astype(int) +
                  rng.integers(0, 8000, N_VIN), 500, 260000)
owner_count = np.clip(rng.poisson(np.clip(age * 0.35, 0.4, None)) + 1, 1, 6)
accident_count = rng.poisson(np.clip(age * 0.18, 0.1, None))
accident_count = np.clip(accident_count, 0, 5)
title_brand = rng.choice(["Clean", "Salvage", "Rebuilt", "Flood"],
                         size=N_VIN, p=[0.90, 0.04, 0.04, 0.02])
odo_rollback = (rng.random(N_VIN) < 0.015).astype(int)
auction_count = np.clip(rng.poisson(0.5, N_VIN) + (owner_count - 1) // 2, 0, 6)

# VIN: 17 chars, no I/O/Q
vin_chars = np.array(list("ABCDEFGHJKLMNPRSTUVWXYZ0123456789"))
vins = ["".join(rng.choice(vin_chars, size=17)) for _ in range(N_VIN)]

# accs_score (0-100): high = desirable/clean condition
score = np.full(N_VIN, 92.0)
score -= accident_count * 7.5
score -= (owner_count - 1) * 3.0
score -= np.clip((mileage - 60000) / 60000, 0, None) * 12
brand_pen = np.select(
    [title_brand == "Salvage", title_brand == "Flood", title_brand == "Rebuilt"],
    [45, 40, 30], default=0)
score -= brand_pen
score -= odo_rollback * 25
score += rng.normal(0, 4, N_VIN)
accs_score = np.clip(score, 1, 100).round().astype(int)

# last_reported_date within last ~18 months
lr_start = np.datetime64("2024-12-01")
lr_span = (np.datetime64("2026-06-30") - lr_start).astype(int)
last_reported = lr_start + rng.integers(0, lr_span + 1, N_VIN).astype("timedelta64[D]")

autocheck = pl.DataFrame({
    "vin": vins,
    "make": v_make, "model": v_model, "trim": v_trim, "model_year": v_year,
    "mileage": mileage, "owner_count": owner_count,
    "accident_count": accident_count, "title_brand": title_brand,
    "odometer_rollback_flag": odo_rollback, "auction_count": auction_count,
    "accs_score": accs_score,
    "last_reported_date": last_reported,
    "garaged_zip": z_zip, "garaged_state": z_state,
})
print(f"gold_autocheck_vin: {autocheck.height:,} rows")

# ===========================================================================
# 3. gold_lending  (~30,000 rows)  loan-level credit
# ===========================================================================
N_LOAN = 30_000
LENDERS = [
    ("Toyota Financial Services", "Captive"),
    ("Ford Motor Credit",         "Captive"),
    ("GM Financial",              "Captive"),
    ("Ally Financial",            "Bank"),
    ("Chase Auto",                "Bank"),
    ("Capital One Auto",          "Bank"),
    ("Wells Fargo Auto",          "Bank"),
    ("Bank of America",           "Bank"),
    ("Navy Federal Credit Union", "Credit Union"),
    ("PenFed Credit Union",       "Credit Union"),
    ("Carvana / Bridgecrest",     "Fintech"),
    ("Upstart Auto",              "Fintech"),
]
L_NAME = [l[0] for l in LENDERS]
L_TYPE = [l[1] for l in LENDERS]
l_idx = rng.integers(0, len(LENDERS), size=N_LOAN)
lender_name = np.array(L_NAME)[l_idx]
lender_type = np.array(L_TYPE)[l_idx]

_, (ln_make, ln_model, ln_body, ln_fuel, ln_trim) = sample_models(N_LOAN)
_, (ln_zip, ln_state, ln_dma, ln_region) = sample_geo(N_LOAN)
ln_year = rng.integers(2015, 2026, size=N_LOAN)

credit_tier = rng.choice(
    ["Super Prime", "Prime", "Near Prime", "Subprime"],
    size=N_LOAN, p=[0.28, 0.37, 0.22, 0.13])
new_used = np.where(ln_year >= 2024,
                    rng.choice(["New", "Used"], N_LOAN, p=[0.65, 0.35]),
                    rng.choice(["New", "Used"], N_LOAN, p=[0.10, 0.90]))

# APR by credit tier (annual %)
apr_mean = np.select(
    [credit_tier == "Super Prime", credit_tier == "Prime",
     credit_tier == "Near Prime", credit_tier == "Subprime"],
    [4.5, 7.0, 11.5, 18.5])
apr = np.round(np.clip(rng.normal(apr_mean, 1.3), 1.9, 29.9), 2)
# used cars carry slightly higher apr
apr = np.round(np.where(new_used == "Used", apr + rng.uniform(0.5, 2.0, N_LOAN), apr), 2)
apr = np.clip(apr, 1.9, 32.0)

term_months = rng.choice([36, 48, 60, 72, 84], size=N_LOAN,
                         p=[0.10, 0.18, 0.34, 0.28, 0.10])
body_price = np.select(
    [ln_body == "Truck", ln_body == "SUV", ln_body == "Van",
     ln_body == "EV", ln_body == "Sedan"],
    [52000, 42000, 40000, 51000, 30000]).astype(float)
new_factor = np.where(new_used == "New", 1.0, 0.62)
orig_amount = np.round(np.clip(
    rng.normal(body_price * new_factor, body_price * 0.14), 8000, 120000), 2)

ltv_mean = np.select(
    [credit_tier == "Super Prime", credit_tier == "Prime",
     credit_tier == "Near Prime", credit_tier == "Subprime"],
    [82, 92, 104, 116]).astype(float)
ltv_pct = np.round(np.clip(rng.normal(ltv_mean, 8), 55, 145), 1)

# monthly payment (standard amortization)
r = apr / 100 / 12
monthly_payment = np.round(
    orig_amount * r * (1 + r) ** term_months / ((1 + r) ** term_months - 1), 2)

# delinquency & default probability rise with tier + apr
delq_base = np.select(
    [credit_tier == "Super Prime", credit_tier == "Prime",
     credit_tier == "Near Prime", credit_tier == "Subprime"],
    [0.010, 0.030, 0.085, 0.190])
delinquency_30d = (rng.random(N_LOAN) < delq_base).astype(int)
def_base = np.select(
    [credit_tier == "Super Prime", credit_tier == "Prime",
     credit_tier == "Near Prime", credit_tier == "Subprime"],
    [0.003, 0.010, 0.035, 0.095])
# defaults only among (or elevated by) delinquency
default_flag = ((rng.random(N_LOAN) < def_base) &
                ((delinquency_30d == 1) | (rng.random(N_LOAN) < 0.3))).astype(int)

# orig_month over trailing ~2 years
om_start = np.datetime64("2023-07", "M")
om_span = (np.datetime64("2025-06", "M") - om_start).astype(int)
orig_month = (om_start + rng.integers(0, om_span + 1, N_LOAN).astype("timedelta64[M]")
              ).astype("datetime64[D]")

lending = pl.DataFrame({
    "loan_id": np.arange(9_000_000, 9_000_000 + N_LOAN),
    "lender_name": lender_name, "lender_type": lender_type,
    "make": ln_make, "model": ln_model, "model_year": ln_year,
    "region": ln_region, "state": ln_state,
    "orig_month": orig_month, "orig_amount": orig_amount, "apr": apr,
    "term_months": term_months, "credit_tier": credit_tier, "ltv_pct": ltv_pct,
    "monthly_payment": monthly_payment,
    "delinquency_30d_flag": delinquency_30d, "default_flag": default_flag,
    "new_used": new_used,
})
print(f"gold_lending: {lending.height:,} rows")

# ===========================================================================
# WRITE TO UNITY CATALOG
# ===========================================================================
spark = DatabricksSession.builder.profile(PROFILE).serverless().getOrCreate()
try:
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA}")
except Exception as e:
    print(f"NOTE: could not CREATE SCHEMA ({e}); assuming it already exists")

# table-level and column-level COMMENTs (for downstream Genie space)
TABLE_COMMENTS = {
    "gold_vio_market": "Experian Velocity Vehicles-in-Operation (VIO) market statistics. One row per make/model/model_year/ZIP/snapshot_month, giving new-vehicle registration counts, cumulative vehicles-in-operation, local market share, and inventory turn speed. Join keys: make/model/model_year, state/dma_region, zip_code.",
    "gold_autocheck_vin": "Experian AutoCheck vehicle-history records, one row per VIN. Captures ownership, accident, title-brand, odometer and auction history plus an AutoCheck-style condition/desirability score (accs_score). Join keys: make/model/model_year, garaged_state, garaged_zip.",
    "gold_lending": "Experian automotive credit & lending loan-level dataset. One row per originated auto loan with lender, credit tier, APR, term, LTV, payment and delinquency/default performance. Join keys: make/model/model_year, state/region.",
}
COLUMN_COMMENTS = {
    "gold_vio_market": {
        "vio_id": "Surrogate primary key for the VIO market record.",
        "make": "Vehicle manufacturer (shared make pool; joins to autocheck/lending).",
        "model": "Vehicle model name (shared model pool).",
        "trim": "Trim level of the model.",
        "model_year": "Model year, 2015-2025.",
        "body_style": "Body style: SUV, Sedan, Truck, EV, or Van.",
        "fuel_type": "Fuel/powertrain type: Gas, Hybrid, EV, or Diesel.",
        "zip_code": "5-digit garaging/registration ZIP (shared 40-ZIP pool).",
        "dma_region": "Designated Market Area / metro for the ZIP.",
        "state": "US state abbreviation.",
        "registration_count": "New vehicle registrations for this cell in the snapshot month.",
        "vio_count": "Cumulative vehicles in operation (on-road units) for this cell.",
        "market_share_pct": "Registration share (%) within the state for the snapshot month.",
        "avg_days_to_turn": "Average dealer days-to-turn (inventory velocity) in days.",
        "snapshot_month": "First-of-month date the statistics were snapshotted.",
    },
    "gold_autocheck_vin": {
        "vin": "Synthetic 17-character Vehicle Identification Number (no I/O/Q).",
        "make": "Vehicle manufacturer (shared make pool).",
        "model": "Vehicle model name (shared model pool).",
        "trim": "Trim level of the model.",
        "model_year": "Model year, 2015-2025.",
        "mileage": "Last reported odometer reading in miles.",
        "owner_count": "Number of distinct owners on record (1-6).",
        "accident_count": "Number of reported accidents (0-5).",
        "title_brand": "Title brand: Clean, Salvage, Rebuilt, or Flood.",
        "odometer_rollback_flag": "1 if a suspected odometer rollback was detected, else 0.",
        "auction_count": "Number of times the vehicle passed through auction.",
        "accs_score": "AutoCheck-style condition/desirability score 0-100; higher is better. Decreases with accidents, owners, mileage, adverse title brands and odometer rollback.",
        "last_reported_date": "Date of the most recent history event on the VIN.",
        "garaged_zip": "5-digit ZIP where the vehicle is garaged (shared ZIP pool).",
        "garaged_state": "US state where the vehicle is garaged.",
    },
    "gold_lending": {
        "loan_id": "Surrogate primary key for the auto loan.",
        "lender_name": "Originating lender (12-lender pool across banks, captives, credit unions, fintechs).",
        "lender_type": "Lender category: Bank, Captive, Credit Union, or Fintech.",
        "make": "Financed vehicle manufacturer (shared make pool).",
        "model": "Financed vehicle model (shared model pool).",
        "model_year": "Vehicle model year, 2015-2025.",
        "region": "US macro region of the borrower (shared region pool).",
        "state": "US state of the borrower.",
        "orig_month": "Loan origination month (first-of-month date).",
        "orig_amount": "Original financed amount in USD.",
        "apr": "Annual percentage rate (%). Rises with lower credit tier and used vehicles.",
        "term_months": "Loan term in months (36-84).",
        "credit_tier": "Borrower credit tier: Super Prime, Prime, Near Prime, or Subprime.",
        "ltv_pct": "Loan-to-value ratio (%). Higher for lower credit tiers.",
        "monthly_payment": "Scheduled monthly payment in USD (amortized).",
        "delinquency_30d_flag": "1 if the loan has ever been 30+ days delinquent, else 0. Rises with lower credit tier.",
        "default_flag": "1 if the loan has defaulted/charged off, else 0. Rises with lower credit tier.",
        "new_used": "Whether the financed vehicle is New or Used.",
    },
}

def write(df, name):
    sdf = spark.createDataFrame(df.to_pandas())
    (sdf.write.format("delta").mode("overwrite")
        .option("overwriteSchema", "true")
        .saveAsTable(f"{CATALOG}.{SCHEMA}.{name}"))
    fq = f"{CATALOG}.{SCHEMA}.{name}"
    tc = TABLE_COMMENTS[name].replace("'", "\\'")
    spark.sql(f"COMMENT ON TABLE {fq} IS '{tc}'")
    for col, cc in COLUMN_COMMENTS[name].items():
        cc = cc.replace("'", "\\'")
        spark.sql(f"ALTER TABLE {fq} ALTER COLUMN {col} COMMENT '{cc}'")
    n = spark.table(fq).count()
    print(f"  wrote {fq}: {n:,} rows (+ comments)")

write(vio, "gold_vio_market")
write(autocheck, "gold_autocheck_vin")
write(lending, "gold_lending")
print("DONE")
spark.stop()
