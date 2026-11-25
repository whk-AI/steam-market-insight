"""Train the A0 12-month high-review classifier.

Strict rules:
- label: reviews_12m >= 1000, from monthly histogram buckets;
- features: release-time only (main genre, genres, free/paid, year);
- split by release year: train 2015-2021, validation 2022, test 2023-2025;
- no random split, no review/rating/price/discount as features.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    precision_recall_curve,
    roc_auc_score,
)

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "data" / "ml" / "train_sample.csv"
LABELS = ROOT / "data" / "ml" / "labels.csv"
OUT = ROOT / "data" / "ml"
OUT.mkdir(parents=True, exist_ok=True)
SEED = 42
TOP_GENRES = 15


def make_matrix(df: pd.DataFrame, main_levels: list[str], genre_levels: list[str]):
    cols: list[np.ndarray] = []
    names: list[str] = []
    for level in main_levels:
        cols.append((df["main_genre"] == level).to_numpy(dtype=float))
        names.append(f"main={level}")
    for level in genre_levels:
        cols.append(
            df["genres"].fillna("").map(lambda s, g=level: int(g in str(s).split(","))).to_numpy(dtype=float)
        )
        names.append(f"genre={level}")
    cols.append(df["is_free"].to_numpy(dtype=float))
    names.append("is_free")
    cols.append(df["year"].to_numpy(dtype=float))
    names.append("year")
    return np.column_stack(cols), names


def fit_scaler(X: np.ndarray, numeric_idx: list[int]):
    means = X.mean(axis=0)
    stds = X.std(axis=0)
    stds[stds == 0] = 1.0
    Xs = X.copy()
    Xs[:, numeric_idx] = (Xs[:, numeric_idx] - means[numeric_idx]) / stds[numeric_idx]
    return Xs, means, stds


def bootstrap_ci(y: np.ndarray, p: np.ndarray, n: int = 400) -> list[float]:
    rng = np.random.default_rng(SEED)
    vals = []
    for _ in range(n):
        idx = rng.integers(0, len(y), len(y))
        if y[idx].sum() == 0:
            continue
        vals.append(average_precision_score(y[idx], p[idx]))
    if not vals:
        return [float("nan"), float("nan")]
    return [float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))]


def metrics(y: np.ndarray, p: np.ndarray) -> dict:
    pr = float(average_precision_score(y, p)) if y.sum() else float("nan")
    roc = float(roc_auc_score(y, p)) if y.sum() and y.sum() < len(y) else float("nan")
    brier = float(brier_score_loss(y, p))
    k = max(1, int(len(y) * 0.1))
    top = np.argsort(-p)[:k]
    return {
        "n": int(len(y)),
        "positives": int(y.sum()),
        "base_rate": float(y.mean()),
        "pr_auc": pr,
        "roc_auc": roc,
        "brier": brier,
        "top10_hit": float(y[top].mean()),
        "pr_auc_ci": bootstrap_ci(y, p),
    }


def main() -> None:
    sample = pd.read_csv(SAMPLE)
    sample["release_date"] = pd.to_datetime(sample["release_date"], errors="coerce")
    labels = pd.read_csv(LABELS)
    df = sample.merge(labels, on="appid", how="left")
    before = len(df)
    df = df[df["status"] == "ok"].copy()
    df["reviews_12m"] = pd.to_numeric(df["reviews_12m"], errors="coerce")
    df = df[df["reviews_12m"].notna()].copy()
    # months_seen counts months that actually have reviews, not calendar
    # coverage: a zero-review month is omitted from the histogram. Judge the
    # window by release date instead, otherwise quiet games look "incomplete".
    cutoff = pd.Timestamp.now().normalize() - pd.DateOffset(years=1)
    df = df[df["release_date"].notna() & (df["release_date"] <= cutoff)].copy()
    df["label"] = (df["reviews_12m"] >= 1000).astype(int)
    df["split"] = np.select(
        [df["year"].between(2015, 2021), df["year"].eq(2022), df["year"].between(2023, 2025)],
        ["train", "val", "test"],
        default="excluded",
    )
    df = df[df["split"] != "excluded"].reset_index(drop=True)

    main_levels = [str(x) for x in df["main_genre"].value_counts().index]
    genre_counts: dict[str, int] = {}
    for s in df["genres"].fillna(""):
        for g in str(s).split(","):
            g = g.strip()
            if g:
                genre_counts[g] = genre_counts.get(g, 0) + 1
    genre_levels = [g for g, _ in sorted(genre_counts.items(), key=lambda kv: -kv[1])[:TOP_GENRES]]

    X, names = make_matrix(df, main_levels, genre_levels)
    numeric_idx = [names.index("is_free"), names.index("year")]
    X, means, stds = fit_scaler(X, numeric_idx)
    y = df["label"].to_numpy()
    tr = (df["split"] == "train").to_numpy()
    va = (df["split"] == "val").to_numpy()
    te = (df["split"] == "test").to_numpy()

    log = LogisticRegression(C=1.0, max_iter=3000, solver="lbfgs", random_state=SEED)
    log.fit(X[tr], y[tr])
    p_log_va = log.predict_proba(X[va])[:, 1]
    p_log_te = log.predict_proba(X[te])[:, 1]

    hist = HistGradientBoostingClassifier(
        max_iter=250,
        learning_rate=0.06,
        max_leaf_nodes=15,
        l2_regularization=1.0,
        random_state=SEED,
    )
    hist.fit(X[tr], y[tr])
    p_hist_va = hist.predict_proba(X[va])[:, 1]
    p_hist_te = hist.predict_proba(X[te])[:, 1]

    # Validation threshold that maximises F1, then frozen for test/page.
    prec, rec, thr = precision_recall_curve(y[va], p_log_va)
    f1 = 2 * prec[:-1] * rec[:-1] / np.clip(prec[:-1] + rec[:-1], 1e-9, None)
    threshold = float(thr[int(np.nanargmax(f1))]) if len(thr) else 0.5

    m_log_va = metrics(y[va], p_log_va)
    m_log_te = metrics(y[te], p_log_te)
    m_hist_va = metrics(y[va], p_hist_va)
    m_hist_te = metrics(y[te], p_hist_te)
    use_hist = (m_hist_va["pr_auc"] - m_log_va["pr_auc"] >= 0.03) and (
        m_hist_va["brier"] <= m_log_va["brier"] + 0.02
    )
    selected = "histgb" if use_hist else "logistic"
    selected_te = m_hist_te if use_hist else m_log_te

    # Calibration table for the page (logistic proxy, deciles on test).
    bins = np.quantile(p_log_te, np.linspace(0, 1, 11))
    bins[0] -= 1e-9
    bins[-1] += 1e-9
    calib = []
    for i in range(10):
        mask = (p_log_te >= bins[i]) & (p_log_te < bins[i + 1])
        if mask.sum() == 0:
            continue
        calib.append(
            {
                "bin": i + 1,
                "pred": float(p_log_te[mask].mean()),
                "actual": float(y[te][mask].mean()),
                "n": int(mask.sum()),
            }
        )

    coef = log.coef_[0]
    features = []
    for name, c in zip(names, coef):
        if name == "is_free":
            kind, value = "numeric", None
        elif name == "year":
            kind, value = "numeric", None
        elif name.startswith("main="):
            kind, value = "main_genre", name.split("=", 1)[1]
        else:
            kind, value = "genre", name.split("=", 1)[1]
        features.append(
            {
                "name": name,
                "kind": kind,
                "value": value,
                "coef": float(c),
                "scaled": name in ("is_free", "year"),
                "mean": float(means[names.index(name)]),
                "std": float(stds[names.index(name)]),
            }
        )

    model = {
        "version": "a0-v1",
        "trained_at": pd.Timestamp.now("UTC").isoformat(),
        "label": "reviews_12m >= 1000",
        "window": "first 12 calendar months from release month",
        "split": {"train": "2015-2021", "val": "2022", "test": "2023-2025"},
        "selected": selected,
        "page_model": "logistic",
        "threshold": threshold,
        "base_rate_train": float(y[tr].mean()),
        "base_rate_test": float(y[te].mean()),
        "features": features,
        "intercept": float(log.intercept_[0]),
        "metrics": {
            "logistic_val": m_log_va,
            "logistic_test": m_log_te,
            "histgb_val": m_hist_va,
            "histgb_test": m_hist_te,
            "selected_test": selected_te,
            "logistic_threshold_val": threshold,
        },
        "calibration": calib,
        "coverage": {
            "sample": int(before),
            "labeled_ok": int(len(df)),
            "coverage": float(len(df) / before) if before else 0,
            "positives": int(y.sum()),
            "positive_rate": float(y.mean()),
        },
        "note": "Page inference uses the logistic proxy (exportable offline); tree model is offline-only if selected.",
    }
    (OUT / "model.json").write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")

    df["p_logistic"] = np.nan
    df.loc[va, "p_logistic"] = p_log_va
    df.loc[te, "p_logistic"] = p_log_te
    df.to_csv(OUT / "model_dataset.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(
        [
            {"split": "val", "model": "logistic", **m_log_va},
            {"split": "test", "model": "logistic", **m_log_te},
            {"split": "val", "model": "histgb", **m_hist_va},
            {"split": "test", "model": "histgb", **m_hist_te},
        ]
    ).to_csv(OUT / "metrics.csv", index=False, encoding="utf-8-sig")

    print(json.dumps({k: model[k] for k in ("selected", "threshold", "base_rate_train", "coverage", "metrics")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
