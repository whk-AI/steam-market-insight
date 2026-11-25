"""Build the fixed A0 training sample.

Population: 2015-01-01 .. 2025-11-19 releases (12-month window completed
before the snapshot). Sampling is stratified by release year so that the
training set is not dominated by the 2024-2025 boom.

No outcome fields (reviews, rating, price, discount) are used as features.
The only feature columns here are known at release time.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
INP = ROOT / "data" / "market" / "market_full.csv"
OUT = ROOT / "data" / "ml" / "train_sample.csv"
META = ROOT / "data" / "ml" / "sample_meta.json"
N = 5000
SEED = 42
LO = pd.Timestamp("2015-01-01")
HI = pd.Timestamp("2025-11-19")


def main() -> None:
    df = pd.read_csv(INP)
    df["release_date"] = pd.to_datetime(df["release_date"], errors="coerce")
    df = df[
        (df["release_date"] >= LO)
        & (df["release_date"] <= HI)
        & (df["year"].between(2015, 2025))
    ].copy()
    df = df.dropna(subset=["release_date", "appid", "main_genre"])
    df["appid"] = df["appid"].astype("int64")
    # 修复清洗数据里残留的编码脏值：主类型只保留十个已知大类，其余归入“其他”；
    # genres 只保留 ASCII 标签，丢掉「δ֪」这类乱码 token，避免它进入 one-hot。
    known_main = {
        "Action", "Adventure", "Casual", "Indie", "Massively Multiplayer",
        "Racing", "RPG", "Simulation", "Sports", "Strategy", "Free To Play",
    }
    df["main_genre"] = df["main_genre"].where(df["main_genre"].isin(known_main), "其他")

    def clean_genres(value: object) -> str:
        tokens = []
        for token in str(value or "").split(","):
            token = token.strip()
            if not token:
                continue
            try:
                token.encode("ascii")
            except UnicodeEncodeError:
                # “未知”是清洗数据里的合法空类，保留；其他非 ASCII 脏 token 丢掉。
                if token not in {"未知", "其他"}:
                    continue
            if token.lower() in {"unknown", "none", "nan"}:
                continue
            tokens.append(token)
        return ",".join(tokens)

    df["genres"] = df["genres"].map(clean_genres)
    df = df.drop_duplicates("appid").sort_values(["year", "appid"]).reset_index(drop=True)

    # Proportional allocation by release year, then a random sample inside
    # each year. This keeps the boom years from crowding out earlier cohorts.
    counts = df["year"].value_counts().sort_index()
    raw = counts / counts.sum() * N
    alloc = raw.round().astype(int)
    diff = N - int(alloc.sum())
    if diff:
        order = raw.sub(alloc).sort_values(ascending=False).index[: abs(diff)]
        alloc.loc[order] += 1 if diff > 0 else -1

    parts = []
    for year, n in alloc.items():
        pool = df[df["year"] == year]
        n = min(int(n), len(pool))
        parts.append(pool.sample(n=n, random_state=SEED + int(year)))
    sample = pd.concat(parts).sort_values(["year", "appid"]).reset_index(drop=True)

    # Keep only release-time columns plus identifiers. Price is deliberately
    # absent: the archive price is a snapshot, not launch price.
    cols = [
        "appid",
        "name",
        "year",
        "release_date",
        "main_genre",
        "genres",
        "is_free",
    ]
    sample = sample[cols].copy()
    sample["release_date"] = sample["release_date"].dt.strftime("%Y-%m-%d")
    sample["is_free"] = sample["is_free"].astype(int)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    sample.to_csv(OUT, index=False, encoding="utf-8-sig")

    meta = {
        "population": int(len(df)),
        "sample": int(len(sample)),
        "seed": SEED,
        "window": "2015-01-01..2025-11-19",
        "strata": "release year",
        "years": {int(k): int(v) for k, v in sample["year"].value_counts().sort_index().items()},
        "genres": {str(k): int(v) for k, v in sample["main_genre"].value_counts().items()},
        "free": int(sample["is_free"].sum()),
        "note": "Features exclude price/discount/reviews/rating; all are snapshots or post-release outcomes.",
    }
    META.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
