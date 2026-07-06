"""Test 1 — Pose quality on real climbing footage (go/no-go).

Hypothesis: MediaPipe PoseLandmarker (heavy) tracks hips and shoulders with
stable confidence on reasonably-filmed climbing clips.

Pass criterion (per CLAUDE.md): on clips tagged filming=good in
footage/manifest.csv, >=80% of frames have all four core keypoints
(L/R hip, L/R shoulder) at visibility >= 0.5. Failure only on filming=bad
clips is acceptable (validates filming guidance as a product feature).
Failure on filming=good clips = stop and rethink.

Reads landmark CSVs written by extract_pose_*.py (schema: pose_schema.py) —
never touches video or models. Metric functions are pure and NumPy-only so
they can be fixture-tested and ported to TypeScript later.

Usage:
    uv run lab/exp01_pose_quality.py

Outputs (lab/results/exp01-pose-quality/):
    summary.csv          one row per clip x model, all metrics + manifest tags
    summary.md           human-readable report, split by filming tag
    plots/<clip>_<model>_visibility.png
    plots/<clip>_<model>_jitter.png
summary.csv/.md and plots are derived data, regenerated from the landmark
CSVs on every run; the landmark CSVs themselves are never modified here.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from pose_schema import CORE_KEYPOINTS, LIMB_KEYPOINTS, read_landmarks

ROOT = Path(__file__).parent.parent
FOOTAGE_DIR = ROOT / "footage"
MANIFEST_PATH = FOOTAGE_DIR / "manifest.csv"
RESULTS_DIR = Path(__file__).parent / "results" / "exp01-pose-quality"
LANDMARKS_DIR = RESULTS_DIR / "landmarks"
PLOTS_DIR = RESULTS_DIR / "plots"

PASS_THRESHOLD = 0.5     # visibility threshold for the pass criterion
PASS_FRACTION = 0.80     # fraction of frames required
SENSITIVITY_THRESHOLDS = (0.3, 0.5, 0.7)
JITTER_WINDOW = 5        # frames, rolling-median baseline for jitter residual

MANIFEST_COLUMNS = ["filename", "angle", "lighting", "venue", "filming", "notes"]


# --------------------------------------------------------------------------
# Pure metric functions (candidates for the shared fixtures / TS port later)
# --------------------------------------------------------------------------

def detection_rate(detected: np.ndarray) -> float:
    """Fraction of frames where a pose was found. detected: 0/1 per frame."""
    return float(np.mean(detected)) if len(detected) else 0.0


def joint_confidence_rate(vis: np.ndarray, threshold: float) -> float:
    """Fraction of frames where ALL keypoints clear the visibility threshold.

    vis: (n_frames, n_keypoints) visibilities; NaN (undetected) counts as below.
    """
    if vis.size == 0:
        return 0.0
    with np.errstate(invalid="ignore"):
        all_ok = np.all(vis >= threshold, axis=1)
    return float(np.mean(all_ok))


def rolling_median(values: np.ndarray, window: int) -> np.ndarray:
    """Centered rolling median, NaN-tolerant, edges use available samples."""
    n = len(values)
    half = window // 2
    out = np.full(n, np.nan)
    for i in range(n):
        seg = values[max(0, i - half): min(n, i + half + 1)]
        if np.any(~np.isnan(seg)):
            out[i] = np.nanmedian(seg)
    return out


def jitter_rms(x: np.ndarray, y: np.ndarray, window: int = JITTER_WINDOW) -> float:
    """RMS of the residual between a 2D trajectory and its rolling median.

    Separates high-frequency tracking noise from real movement (which the
    rolling median follows). Units follow the inputs (pass pixels for px RMS).
    NaN frames (undetected) are excluded.
    """
    rx = x - rolling_median(x, window)
    ry = y - rolling_median(y, window)
    mag_sq = rx**2 + ry**2
    valid = ~np.isnan(mag_sq)
    if not np.any(valid):
        return float("nan")
    return float(np.sqrt(np.mean(mag_sq[valid])))


def longest_run_below(vis: np.ndarray, threshold: float) -> int:
    """Longest consecutive run of frames below threshold (NaN counts as below)."""
    with np.errstate(invalid="ignore"):
        below = ~(vis >= threshold)
    longest = current = 0
    for b in below:
        current = current + 1 if b else 0
        longest = max(longest, current)
    return int(longest)


# --------------------------------------------------------------------------
# Per-clip analysis
# --------------------------------------------------------------------------

def keypoint_vis_matrix(df: pd.DataFrame, keypoints: dict[str, int]) -> np.ndarray:
    return np.column_stack([df[f"lm{i:02d}_vis"].to_numpy() for i in keypoints.values()])


def analyze_clip(csv_path: Path) -> tuple[dict, pd.DataFrame, dict]:
    df, meta = read_landmarks(csv_path)
    width, height = meta["width"], meta["height"]

    core_vis = keypoint_vis_matrix(df, CORE_KEYPOINTS)
    row = {
        "clip": meta["filename"],
        "model": meta["model"],
        "frames": len(df),
        "fps": meta["fps"],
        "detection_rate": detection_rate(df["detected"].to_numpy()),
    }
    for th in SENSITIVITY_THRESHOLDS:
        row[f"core_conf_rate_{th}"] = joint_confidence_rate(core_vis, th)

    # Jitter in pixels, hips and shoulders separately (avg of L/R)
    for group, idxs in (("shoulder", (11, 12)), ("hip", (23, 24))):
        vals = []
        for i in idxs:
            x = df[f"lm{i:02d}_x"].to_numpy() * width
            y = df[f"lm{i:02d}_y"].to_numpy() * height
            vals.append(jitter_rms(x, y))
        row[f"jitter_{group}_px"] = float(np.nanmean(vals))
    # Normalized version (fraction of image height) for cross-clip comparison
    row["jitter_hip_norm"] = row["jitter_hip_px"] / height
    row["jitter_shoulder_norm"] = row["jitter_shoulder_px"] / height

    # Limb occlusion
    limb_stats = {}
    for name, i in LIMB_KEYPOINTS.items():
        vis = df[f"lm{i:02d}_vis"].to_numpy()
        with np.errstate(invalid="ignore"):
            lost_frac = float(np.mean(~(vis >= PASS_THRESHOLD)))
        limb_stats[name] = (lost_frac, longest_run_below(vis, PASS_THRESHOLD))
    worst = max(limb_stats.items(), key=lambda kv: kv[1][0])
    row["limb_loss_worst"] = worst[0]
    row["limb_loss_worst_frac"] = worst[1][0]
    row["limb_loss_worst_run"] = worst[1][1]
    row["limb_loss_mean_frac"] = float(np.mean([v[0] for v in limb_stats.values()]))

    row["passes"] = row[f"core_conf_rate_{PASS_THRESHOLD}"] >= PASS_FRACTION
    return row, df, meta


def plot_visibility(df: pd.DataFrame, meta: dict, model_tag: str) -> Path:
    fig, ax = plt.subplots(figsize=(12, 4))
    for name, i in CORE_KEYPOINTS.items():
        ax.plot(df["frame"], df[f"lm{i:02d}_vis"], label=name, linewidth=0.9)
    undetected = df["detected"] == 0
    if undetected.any():
        ax.fill_between(df["frame"], 0, 1, where=undetected,
                        color="red", alpha=0.15, label="no pose")
    ax.axhline(PASS_THRESHOLD, color="gray", linestyle="--", linewidth=0.8)
    ax.set(xlabel="frame", ylabel="visibility", ylim=(0, 1.02),
           title=f"{meta['filename']} — {meta['model']} — core keypoint visibility")
    ax.legend(loc="lower left", fontsize=8)
    out = PLOTS_DIR / f"{Path(meta['filename']).stem}_{model_tag}_visibility.png"
    fig.tight_layout()
    fig.savefig(out, dpi=110)
    plt.close(fig)
    return out


def plot_jitter(df: pd.DataFrame, meta: dict, model_tag: str) -> Path:
    width, height = meta["width"], meta["height"]
    fig, ax = plt.subplots(figsize=(12, 4))
    for name, i in CORE_KEYPOINTS.items():
        x = df[f"lm{i:02d}_x"].to_numpy() * width
        y = df[f"lm{i:02d}_y"].to_numpy() * height
        rx = x - rolling_median(x, JITTER_WINDOW)
        ry = y - rolling_median(y, JITTER_WINDOW)
        ax.plot(df["frame"], np.sqrt(rx**2 + ry**2), label=name, linewidth=0.9)
    ax.set(xlabel="frame", ylabel="residual (px)",
           title=f"{meta['filename']} — {meta['model']} — jitter residual "
                 f"(vs {JITTER_WINDOW}-frame rolling median)")
    ax.legend(loc="upper right", fontsize=8)
    out = PLOTS_DIR / f"{Path(meta['filename']).stem}_{model_tag}_jitter.png"
    fig.tight_layout()
    fig.savefig(out, dpi=110)
    plt.close(fig)
    return out


# --------------------------------------------------------------------------
# Cross-model comparison
# --------------------------------------------------------------------------

def model_disagreement_px(
    df_a: pd.DataFrame, df_b: pd.DataFrame, width: int, height: int,
    threshold: float = PASS_THRESHOLD,
) -> tuple[float, int]:
    """Median px distance between two models' core keypoints, and the number
    of frames compared (frames where both models are confident on that kp)."""
    dists = []
    n = min(len(df_a), len(df_b))
    for i in CORE_KEYPOINTS.values():
        ax = df_a[f"lm{i:02d}_x"].to_numpy()[:n] * width
        ay = df_a[f"lm{i:02d}_y"].to_numpy()[:n] * height
        bx = df_b[f"lm{i:02d}_x"].to_numpy()[:n] * width
        by = df_b[f"lm{i:02d}_y"].to_numpy()[:n] * height
        av = df_a[f"lm{i:02d}_vis"].to_numpy()[:n]
        bv = df_b[f"lm{i:02d}_vis"].to_numpy()[:n]
        with np.errstate(invalid="ignore"):
            both = (av >= threshold) & (bv >= threshold)
        if np.any(both):
            dists.append(np.hypot(ax[both] - bx[both], ay[both] - by[both]))
    if not dists:
        return float("nan"), 0
    all_d = np.concatenate(dists)
    return float(np.median(all_d)), int(len(all_d) // len(CORE_KEYPOINTS))


def compare_models(csvs: list[Path]) -> pd.DataFrame:
    """Pair up extractions of the same clip from different models."""
    by_clip: dict[str, dict[str, Path]] = {}
    for p in csvs:
        stem, tag = p.stem.rsplit("_", 1)
        by_clip.setdefault(stem, {})[tag] = p
    rows = []
    for stem, tags in sorted(by_clip.items()):
        if len(tags) < 2:
            continue
        (tag_a, path_a), (tag_b, path_b) = sorted(tags.items())[:2]
        df_a, meta = read_landmarks(path_a)
        df_b, _ = read_landmarks(path_b)
        med, n_frames = model_disagreement_px(df_a, df_b, meta["width"], meta["height"])
        rows.append({
            "clip": meta["filename"], "models": f"{tag_a} vs {tag_b}",
            "core_disagreement_median_px": med, "frames_compared": n_frames,
        })
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# Manifest + report
# --------------------------------------------------------------------------

def load_or_template_manifest(clip_names: list[str]) -> pd.DataFrame:
    if MANIFEST_PATH.exists():
        manifest = pd.read_csv(MANIFEST_PATH)
        for col in manifest.columns:  # tolerate stray whitespace in hand-edited CSV
            if manifest[col].dtype == object:
                manifest[col] = manifest[col].str.strip()
        known = {f.lower() for f in manifest["filename"].dropna()}
        missing = [c for c in clip_names if c.lower() not in known]
        if missing:
            new_rows = pd.DataFrame(
                [[name, "", "", "", "", ""] for name in missing],
                columns=MANIFEST_COLUMNS,
            )
            manifest = pd.concat([manifest, new_rows], ignore_index=True)
            manifest.to_csv(MANIFEST_PATH, index=False)
            print(f"added {len(missing)} new clip(s) to manifest.csv — "
                  f"fill in their tags: {missing}")
        return manifest
    template = pd.DataFrame(
        [[name, "", "", "", "", ""] for name in clip_names],
        columns=MANIFEST_COLUMNS,
    )
    template.to_csv(MANIFEST_PATH, index=False)
    print(f"created manifest template: {MANIFEST_PATH}")
    print("fill in: angle (steep = >30 deg overhung | vertical = <=30 deg), "
          "lighting (good|bad), venue (board|gym|outside), filming (good|bad)")
    return template


def md_table(df: pd.DataFrame, cols: list[str]) -> str:
    fmt = {c: (lambda v: f"{v:.3f}" if isinstance(v, float) else str(v)) for c in cols}
    header = "| " + " | ".join(cols) + " |"
    sep = "|" + "|".join("---" for _ in cols) + "|"
    lines = [header, sep]
    for _, r in df.iterrows():
        lines.append("| " + " | ".join(fmt[c](r[c]) for c in cols) + " |")
    return "\n".join(lines)


def write_report(summary: pd.DataFrame, comparison: pd.DataFrame) -> Path:
    n_clips = summary["clip"].nunique()
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    parts = [
        "# Test 1 — pose quality results",
        f"_Generated {ts} from {len(summary)} clip×model runs "
        f"({n_clips} clips)._",
        "",
        f"**Pass criterion:** ≥{PASS_FRACTION:.0%} of frames with all four core "
        f"keypoints (L/R hip, L/R shoulder) at visibility ≥ {PASS_THRESHOLD}, "
        "on clips tagged `filming=good`.",
        "",
    ]
    if n_clips < 30:
        parts += [
            f"> **SMOKE RUN — {n_clips} clip(s).** The go/no-go verdict requires "
            "the full 30–50 clip set; treat these numbers as pipeline validation "
            "only.",
            "",
        ]
    show_cols = ["clip", "model", "filming", "frames", "detection_rate",
                 "core_conf_rate_0.3", "core_conf_rate_0.5", "core_conf_rate_0.7",
                 "jitter_shoulder_px", "jitter_hip_px",
                 "limb_loss_worst", "limb_loss_worst_frac", "passes"]
    show_cols = [c for c in show_cols if c in summary.columns]
    for filming, group in summary.groupby(summary["filming"].fillna("untagged")):
        n_pass = int(group["passes"].sum())
        parts += [
            f"## filming = {filming or 'untagged'} "
            f"({n_pass}/{len(group)} clip-runs pass)",
            "",
            md_table(group, show_cols),
            "",
        ]
    if len(comparison):
        parts += [
            "## Cross-model agreement (core keypoints, both models confident)",
            "",
            md_table(comparison, list(comparison.columns)),
            "",
        ]
    good = summary[summary["filming"] == "good"]
    if len(good):
        all_pass = bool(good["passes"].all())
        verdict = ("all well-filmed clips PASS" if all_pass
                   else f"{int((~good['passes']).sum())} well-filmed clip-run(s) FAIL "
                        "— investigate before proceeding")
        parts += [f"## Verdict on well-filmed clips: {verdict}", ""]
    else:
        parts += ["## Verdict: no clips tagged filming=good yet — fill in "
                  "footage/manifest.csv and re-run.", ""]
    out = RESULTS_DIR / "summary.md"
    out.write_text("\n".join(parts), encoding="utf-8")
    return out


def main() -> int:
    csvs = sorted(LANDMARKS_DIR.glob("*.csv"))
    if not csvs:
        print(f"no landmark CSVs in {LANDMARKS_DIR} — run extract_pose_*.py first")
        return 1
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)

    rows = []
    for csv_path in csvs:
        model_tag = csv_path.stem.rsplit("_", 1)[-1]
        row, df, meta = analyze_clip(csv_path)
        plot_visibility(df, meta, model_tag)
        plot_jitter(df, meta, model_tag)
        rows.append(row)
        print(f"{row['clip']} [{model_tag}]  det={row['detection_rate']:.2f}  "
              f"core@0.5={row['core_conf_rate_0.5']:.2f}  "
              f"jitter hip/shoulder px={row['jitter_hip_px']:.1f}/"
              f"{row['jitter_shoulder_px']:.1f}  "
              f"{'PASS' if row['passes'] else 'FAIL'}")

    summary = pd.DataFrame(rows)
    manifest = load_or_template_manifest(sorted(summary["clip"].unique()))
    # case-insensitive filename join (.MOV vs .mov)
    manifest = manifest.assign(_key=manifest["filename"].str.lower()).drop(columns=["filename"])
    summary = (
        summary.assign(_key=summary["clip"].str.lower())
        .merge(manifest, on="_key", how="left")
        .drop(columns=["_key"])
    )
    summary.to_csv(RESULTS_DIR / "summary.csv", index=False)

    comparison = compare_models(csvs)
    if len(comparison):
        comparison.to_csv(RESULTS_DIR / "model_comparison.csv", index=False)
        for _, r in comparison.iterrows():
            print(f"{r['clip']}  {r['models']}: median core disagreement "
                  f"{r['core_disagreement_median_px']:.1f}px "
                  f"({r['frames_compared']} frames)")

    report = write_report(summary, comparison)
    print(f"\nwrote {RESULTS_DIR / 'summary.csv'}")
    print(f"wrote {report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
