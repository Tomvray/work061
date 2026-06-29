"""
USPTO Patent Pair Extractor
============================
Combines two data sources into (application_claims, cited_patent_claims) pairs:

  SOURCE A — Application claims:
    HUPD dataset: one JSON file per application, named {application_number}.json
    Key fields used: application_number, claims, filing_date, main_cpc_label

  SOURCE B — Cited patent claims:
    PostgreSQL: claims table, joined via citations + office_actions
    Join key: citations.app_id = application_number (HUPD)
              citations.parsed = claims.patent_id   (cited patent)

Pipeline:
  1. Query PostgreSQL for all (app_id, cited_id, rejection_type) triples
  2. For each unique app_id, load claims from HUPD JSON
  3. For each unique cited_id, pull aggregated claims from PostgreSQL
  4. Join everything, clean, split temporally, save JSONL

Usage:
    # From inside Docker network:
    python extract_from_db.py \
        --hupd_dir /data/hupd \
        --host db --port 5432 \
        --dbname patents_db --user postgres --password secret \
        --output_dir data/ --split --stats

    # With env vars for DB credentials:
    export PGHOST=db PGPORT=5432 PGDATABASE=patents_db
    export PGUSER=postgres PGPASSWORD=secret
    python extract_from_db.py --hupd_dir /data/hupd --output_dir data/ --split --stats

    # Quick test on a small subset:
    python extract_from_db.py --hupd_dir /data/hupd ... --limit 5000 --stats

    # Dry run (print SQL only, no DB or file access):
    python extract_from_db.py --hupd_dir /data/hupd ... --dry_run
"""

import argparse
import json
import logging
import os
from pathlib import Path

import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
from tqdm import tqdm

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
log = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# 1. POSTGRESQL CONNECTION
# ─────────────────────────────────────────────────────────────

def get_connection(host, port, dbname, user):
    conn = psycopg2.connect(
        host=host         or os.getenv("PGHOST",     "db"),
        port=port         or os.getenv("PGPORT",     5432),
        dbname=dbname     or os.getenv("PGDATABASE", "patents_db"),
        user=user         or os.getenv("PGUSER",     "postgres"),
        password="postgres"
    )
    log.info(f"Connected to {dbname} on {host}:{port}")
    return conn


# ─────────────────────────────────────────────────────────────
# 2. POSTGRESQL QUERIES
# ─────────────────────────────────────────────────────────────

# Pull every (app_id, cited_id, rejection_type) triple we care about.
# No claim aggregation here — application claims come from HUPD.
PAIRS_QUERY = """
SELECT
    c.app_id,
    c.parsed                                    AS cited_id,
    CASE
        WHEN oa.rejection_102 AND oa.rejection_103 THEN '102+103'
        WHEN oa.rejection_102                       THEN '102'
        ELSE                                              '103'
    END                                         AS rejection_type,
    oa.mail_dt::text                            AS mail_dt,
    oa.uspc_class,
    oa.uspc_subclass,
    oa.art_unit
FROM citations c
JOIN office_actions oa ON oa.app_id = c.app_id
WHERE (oa.rejection_102 = TRUE OR oa.rejection_103 = TRUE)
  AND c.citation_in_oa = TRUE
  AND c.parsed IS NOT NULL
  AND c.parsed != ''
GROUP BY
    c.app_id, c.parsed, oa.rejection_102, oa.rejection_103,
    oa.mail_dt, oa.uspc_class, oa.uspc_subclass, oa.art_unit
ORDER BY oa.mail_dt
{limit_clause};
"""

# Aggregate all claims for a batch of cited patent IDs in one query.
CITED_CLAIMS_QUERY = """
SELECT
    patent_id,
    string_agg(
        claim_number::text || '. ' || claim_text,
        ' '
        ORDER BY claim_number
    ) AS claims_text
FROM claims
WHERE patent_id = ANY(%(patent_ids)s)
GROUP BY patent_id;
"""

SANITY_QUERY = """
SELECT
    COUNT(DISTINCT c.app_id)                    AS n_applications,
    COUNT(DISTINCT c.parsed)                    AS n_cited_patents,
    COUNT(*)                                    AS n_pairs,
    SUM(oa.rejection_102::int)                  AS n_102,
    SUM(oa.rejection_103::int)                  AS n_103
FROM citations c
JOIN office_actions oa ON oa.app_id = c.app_id
WHERE (oa.rejection_102 = TRUE OR oa.rejection_103 = TRUE)
  AND c.citation_in_oa = TRUE
  AND c.parsed IS NOT NULL;
"""


def run_sanity_check(conn):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(SANITY_QUERY)
        r = dict(cur.fetchone())
    log.info(
        f"DB sanity — "
        f"apps: {r['n_applications']:,} | "
        f"cited patents: {r['n_cited_patents']:,} | "
        f"pairs: {r['n_pairs']:,} | "
        f"§102 OAs: {r['n_102']:,} | "
        f"§103 OAs: {r['n_103']:,}"
    )


def fetch_pairs_from_db(conn, limit=None) -> pd.DataFrame:
    """Fetch (app_id, cited_id, rejection_type, ...) triples from PostgreSQL."""
    limit_clause = f"LIMIT {limit}" if limit else ""
    query = PAIRS_QUERY.format(limit_clause=limit_clause)
    log.info("Fetching pairs from PostgreSQL...")
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query)
        rows = [dict(r) for r in cur.fetchall()]
    df = pd.DataFrame(rows)
    log.info(f"  → {len(df):,} (app_id, cited_id) pairs from DB")
    return df


def fetch_cited_claims_from_db(conn, cited_ids: list[str]) -> dict[str, str]:
    """
    Batch-fetch aggregated claims for all cited patent IDs in one query.
    Returns {patent_id: claims_text}.
    """
    log.info(f"Fetching claims for {len(cited_ids):,} cited patents from PostgreSQL...")
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(CITED_CLAIMS_QUERY, {"patent_ids": cited_ids})
        rows = cur.fetchall()
    result = {r["patent_id"]: r["claims_text"] for r in rows}
    found = len(result)
    log.info(
        f"  → Claims found: {found:,} / {len(cited_ids):,} "
        f"({found / max(len(cited_ids), 1) * 100:.1f}% coverage)"
    )
    return result


# ─────────────────────────────────────────────────────────────
# 3. HUPD JSON LOADING
# ─────────────────────────────────────────────────────────────

def build_hupd_index(hupd_dir: str) -> dict[str, Path]:
    """
    Walk the HUPD directory recursively and build:
        application_number (str) → Path to .json file

    Supports both flat and year-nested layouts:
        hupd/14421830.json
        hupd/2018/14421830.json
    """
    log.info(f"Indexing HUPD directory: {hupd_dir}")
    index = {}
    for p in Path(hupd_dir).rglob("*.json"):
        index[p.stem] = p          # stem = filename without .json = application_number
    log.info(f"  → Indexed {len(index):,} HUPD application files")
    return index


def load_hupd_metadata(app_id: str, hupd_index: dict[str, Path]) -> dict | None:
    """
    Load claims + metadata for one application from its HUPD JSON file.
    Returns None if the file is missing, unreadable, or claims are empty.
    """
    path = hupd_index.get(str(app_id))
    if path is None:
        return None
    try:
        with open(path, "r") as f:
            rec = json.load(f)
        claims = rec.get("claims", "")
        if not isinstance(claims, str) or len(claims) < 50:
            return None
        return {
            "app_id":         str(rec.get("application_number", app_id)),
            "app_claims":     claims,
            "filing_date":    rec.get("filing_date", ""),
            "main_cpc_label": rec.get("main_cpc_label", ""),
        }
    except (json.JSONDecodeError, OSError):
        return None


def batch_load_hupd(
    app_ids: list[str],
    hupd_index: dict[str, Path],
) -> dict[str, dict]:
    """
    Load HUPD metadata for all unique app_ids.
    Returns {app_id: {app_claims, filing_date, main_cpc_label}}.
    """
    log.info(f"Loading HUPD claims for {len(app_ids):,} unique applications...")
    result, missing = {}, 0
    for app_id in tqdm(app_ids, desc="Loading HUPD files"):
        meta = load_hupd_metadata(str(app_id), hupd_index)
        if meta:
            result[str(app_id)] = meta
        else:
            missing += 1
    log.info(
        f"  → HUPD loaded: {len(result):,} / {len(app_ids):,} "
        f"({missing:,} missing or empty)"
    )
    return result


# ─────────────────────────────────────────────────────────────
# 4. JOIN + CLEAN
# ─────────────────────────────────────────────────────────────

def build_pairs(
    pairs_df: pd.DataFrame,
    hupd_data: dict[str, dict],
    cited_claims: dict[str, str],
) -> pd.DataFrame:
    """
    Join the three data sources into one flat DataFrame.
    Rows where either side is missing are dropped.
    """
    log.info("Joining data sources...")
    records = []
    for _, row in pairs_df.iterrows():
        app_id   = str(row["app_id"])
        cited_id = str(row["cited_id"])

        app_meta  = hupd_data.get(app_id)
        cited_txt = cited_claims.get(cited_id)

        if app_meta is None or cited_txt is None:
            continue

        records.append({
            "app_id":         app_id,
            "app_claims":     app_meta["app_claims"],
            "cited_id":       cited_id,
            "cited_claims":   cited_txt,
            "rejection_type": row["rejection_type"],
            # Prefer HUPD filing_date (application date) over mail_dt (OA date)
            "filing_date":    app_meta.get("filing_date") or row.get("mail_dt", ""),
            "main_cpc_label": app_meta.get("main_cpc_label", ""),
            "uspc_class":     row.get("uspc_class", ""),
            "uspc_subclass":  row.get("uspc_subclass", ""),
        })

    df = pd.DataFrame(records)
    log.info(
        f"  → Complete pairs: {len(df):,} "
        f"(dropped {len(pairs_df) - len(df):,} incomplete)"
    )
    return df


def clean_and_expand(df: pd.DataFrame) -> pd.DataFrame:
    """
    Split '102+103' rows into two rows (one per rejection type),
    then deduplicate on (app_id, cited_id, rejection_type).
    """
    n = len(df)
    df_102 = df[df["rejection_type"].isin(["102", "102+103"])].copy()
    df_102["rejection_type"] = "102"
    df_103 = df[df["rejection_type"].isin(["103", "102+103"])].copy()
    df_103["rejection_type"] = "103"

    df = pd.concat([df_102, df_103], ignore_index=True)
    df = df.drop_duplicates(subset=["app_id", "cited_id", "rejection_type"])

    log.info(
        f"After expand & dedup: {n:,} → {len(df):,} | "
        f"§102: {(df['rejection_type'] == '102').sum():,} | "
        f"§103: {(df['rejection_type'] == '103').sum():,}"
    )
    return df


# ─────────────────────────────────────────────────────────────
# 5. STATS
# ─────────────────────────────────────────────────────────────

def compute_stats(df: pd.DataFrame):
    log.info("── Word count statistics ───────────────────────────────────")
    for col, label in [
        ("app_claims",   "Application claims  (HUPD)"),
        ("cited_claims", "Cited patent claims (PostgreSQL)"),
    ]:
        wc = df[col].str.split().str.len()
        log.info(
            f"  {label}:\n"
            f"    mean={wc.mean():.0f} | median={wc.median():.0f} | "
            f"p90={wc.quantile(0.90):.0f} | p95={wc.quantile(0.95):.0f} | "
            f"p99={wc.quantile(0.99):.0f} | max={wc.max():.0f}"
        )
    log.info("────────────────────────────────────────────────────────────")
    log.info("Tip: set --max_seq_length ≥ p95 × 1.4 tokens in pipeline.py")


# ─────────────────────────────────────────────────────────────
# 6. TEMPORAL SPLIT
# ─────────────────────────────────────────────────────────────

def temporal_split(
    df: pd.DataFrame,
    train_cutoff: str,
    val_cutoff: str,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Split by filing_date from HUPD (application date — more accurate than mail_dt).
    Rows with unparseable dates are dropped with a warning.

      train : filing_date < train_cutoff
      val   : train_cutoff <= filing_date < val_cutoff
      test  : filing_date >= val_cutoff
    """
    df["filing_date"] = pd.to_datetime(df["filing_date"], errors="coerce")
    n_bad = df["filing_date"].isna().sum()
    if n_bad:
        log.warning(f"Dropping {n_bad:,} rows with unparseable filing_date")
    df = df.dropna(subset=["filing_date"])

    t1 = pd.Timestamp(train_cutoff)
    t2 = pd.Timestamp(val_cutoff)

    train = df[df["filing_date"] < t1].copy()
    val   = df[(df["filing_date"] >= t1) & (df["filing_date"] < t2)].copy()
    test  = df[df["filing_date"] >= t2].copy()

    total = len(df)
    for name, split in [("Train", train), ("Val", val), ("Test", test)]:
        if len(split) == 0:
            log.warning(f"{name} split is empty — adjust --train_cutoff / --val_cutoff")
            continue
        log.info(
            f"  {name}: {len(split):,} ({len(split)/total*100:.1f}%) | "
            f"§102={(split['rejection_type'] == '102').sum():,} | "
            f"§103={(split['rejection_type'] == '103').sum():,} | "
            f"{split['filing_date'].min().date()} → {split['filing_date'].max().date()}"
        )
    return train, val, test


# ─────────────────────────────────────────────────────────────
# 7. SAVE
# ─────────────────────────────────────────────────────────────

OUTPUT_COLS = [
    "app_id", "app_claims",
    "cited_id", "cited_claims",
    "rejection_type", "filing_date",
    "main_cpc_label", "uspc_class", "uspc_subclass",
]

def save_jsonl(df: pd.DataFrame, path: str):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    cols = [c for c in OUTPUT_COLS if c in df.columns]
    with open(path, "w") as f:
        for rec in df[cols].to_dict(orient="records"):
            if isinstance(rec.get("filing_date"), pd.Timestamp):
                rec["filing_date"] = rec["filing_date"].strftime("%Y-%m-%d")
            f.write(json.dumps(rec) + "\n")
    log.info(f"Saved {len(df):,} records → {path}")


# ─────────────────────────────────────────────────────────────
# 8. MAIN
# ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Extract patent pairs from HUPD JSON files + PostgreSQL"
    )

    # HUPD
    parser.add_argument("--hupd_dir", required=True,
                        help="Root dir of HUPD JSON files (searched recursively)")

    # PostgreSQL
    parser.add_argument("--host",     default=None, help="DB host (or set $PGHOST)")
    parser.add_argument("--port",     default=None, type=int)
    parser.add_argument("--dbname",   default=None)
    parser.add_argument("--user",     default=None)
    parser.add_argument("--password", default=None)

    # Extraction
    parser.add_argument("--limit",   default=None, type=int,
                        help="Limit DB rows for quick testing")
    parser.add_argument("--dry_run", action="store_true",
                        help="Print SQL and exit without executing")

    # Output
    parser.add_argument("--output_dir",   default="data")
    parser.add_argument("--split",        action="store_true",
                        help="Produce train/val/test JSONL splits")
    parser.add_argument("--train_cutoff", default="2020-01-01")
    parser.add_argument("--val_cutoff",   default="2022-01-01")
    parser.add_argument("--stats",        action="store_true",
                        help="Print word count statistics")

    args = parser.parse_args()

    if args.dry_run:
        print("── PAIRS QUERY ──────────────────────────────────────────")
        print(PAIRS_QUERY.format(limit_clause=""))
        print("\n── CITED CLAIMS QUERY ───────────────────────────────────")
        print(CITED_CLAIMS_QUERY)
        return

    # ── Step 1: DB connection + sanity check ─────────────────────────
    conn = get_connection(
        args.host, args.port, args.dbname, args.user
    )
    try:
        run_sanity_check(conn)

        # ── Step 2: fetch (app_id, cited_id, rejection_type) ─────────
        pairs_df = fetch_pairs_from_db(conn, limit=args.limit)
        if pairs_df.empty:
            log.error("No pairs returned from DB.")
            return

        # ── Step 3: batch-fetch cited patent claims from DB ───────────
        unique_cited = pairs_df["cited_id"].unique().tolist()
        cited_claims = fetch_cited_claims_from_db(conn, unique_cited)

    finally:
        conn.close()
        log.info("DB connection closed.")

    # ── Step 4: index HUPD + load application claims ─────────────────
    hupd_index   = build_hupd_index(args.hupd_dir)
    unique_apps  = pairs_df["app_id"].unique().tolist()
    hupd_data    = batch_load_hupd(unique_apps, hupd_index)

    # ── Step 5: join ──────────────────────────────────────────────────
    df = build_pairs(pairs_df, hupd_data, cited_claims)
    if df.empty:
        log.error(
            "No complete pairs after joining. "
            "Check HUPD coverage and that cited patent IDs match claims.patent_id."
        )
        return

    # ── Step 6: clean + expand 102+103 ───────────────────────────────
    df = clean_and_expand(df)

    # ── Step 7: stats ─────────────────────────────────────────────────
    if args.stats:
        compute_stats(df)

    # ── Step 8: save ──────────────────────────────────────────────────
    save_jsonl(df, f"{args.output_dir}/pairs_all.jsonl")

    if args.split:
        log.info(
            f"Temporal split: train < {args.train_cutoff} | "
            f"val < {args.val_cutoff} | test ≥ {args.val_cutoff}"
        )
        train, val, test = temporal_split(df, args.train_cutoff, args.val_cutoff)
        save_jsonl(train, f"{args.output_dir}/pairs_train.jsonl")
        save_jsonl(val,   f"{args.output_dir}/pairs_val.jsonl")
        save_jsonl(test,  f"{args.output_dir}/pairs_test.jsonl")


if __name__ == "__main__":
    main()