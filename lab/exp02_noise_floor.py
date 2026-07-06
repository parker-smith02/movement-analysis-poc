"""Test 2 — Metric noise floor and calibration.

Hypothesis: when the true hip-position delta is zero (same static position,
repeated takes), the measured between-take variation is small enough that
climbing-relevant differences (~5 cm / ~10% of torso length) clear it, and
the two pixel->cm calibration methods agree.

Pass criteria (judgment calls, stated up front):
  1. Between-take std of relative hip height (variant C, static-reset group)
     <= 2% of torso length. The product's minimum reportable difference is
     2 sigma; 2% keeps that at ~2 cm-equivalent for a typical adult torso.
  2. Person-height and hold-spacing calibrations agree within 5%.
Failing (1) on static-reset but passing on static-fixed = camera setup, not
pose, is the bottleneck -> filming guidance + relative units. Failing (2) ->
relative units only (already Parker's preference for morphology reasons).

Three hip-height variants per take (the comparison IS the abs-vs-rel decision):
  A  hips above frame bottom, px    — valid only within one camera setup
  B  hips above ankle midpoint, px  — wall-anchored (feet on same holds),
                                      survives camera re-sets; cm via calibration
  C  B / torso length               — camera- and morphology-relative

Inputs:
  footage/exp02/takes.csv          filename, group, notes
                                   groups: static-fixed | static-reset | movement
  footage/exp02/calibration.json   optional; see CAL_TEMPLATE below
  landmarks extracted via:
    uv run lab/extract_pose_mediapipe.py footage/exp02 --out lab/results/exp02-noise-floor/landmarks

Outputs (lab/results/exp02-noise-floor/): takes_summary.csv, noise_floor.csv,
summary.md, plots/.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import metrics
from pose_schema import (
    ANKLE_L,
    ANKLE_R,
    HIP_L,
    HIP_R,
    SHOULDER_L,
    SHOULDER_R,
    landmarks_csv_path,
    read_landmarks,
)

ROOT = Path(__file__).parent.parent
EXP02_DIR = ROOT / "footage" / "exp02"
TAKES_PATH = EXP02_DIR / "takes.csv"
CAL_PATH = EXP02_DIR / "calibration.json"
RESULTS_DIR = Path(__file__).parent / "results" / "exp02-noise-floor"
LANDMARKS_DIR = RESULTS_DIR / "landmarks"
PLOTS_DIR = RESULTS_DIR / "plots"

CONF = 0.5              # visibility threshold for usable frames
GROUPS = ("static-fixed", "static-reset", "movement")
TAKES_COLUMNS = ["filename", "group", "move_id", "notes"]
PASS_REL_STD_PCT = 2.0  # criterion 1: sigma_C (static-reset) as % of torso
PASS_CAL_AGREE_PCT = 5.0  # criterion 2

CAL_TEMPLATE = {
    "climber_height_cm": None,
    "person_extent": {"comment": "click head-top and floor with pick_points.py",
                      "clip": "", "frame": 0, "top_px": [0, 0], "bottom_px": [0, 0]},
    "hold_references": [
        {"label": "horizontal", "spacing_cm": None,
         "comment": "two roughly LEVEL holds at working-zone depth, "
                    "tape-measured center-to-center",
         "clip": "", "frame": 0, "a_px": [0, 0], "b_px": [0, 0]},
        {"label": "vertical", "spacing_cm": None,
         "comment": "OPTIONAL: two vertically-separated holds; tests whether "
                    "calibration is orientation-sensitive on the oblique wall",
         "clip": "", "frame": 0, "a_px": [0, 0], "b_px": [0, 0]},
    ],
}

FILMING_CHECKLIST = """
exp02 filming checklist (all clips into footage/exp02/, tripod; film at the
SAME camera angle the product will use — the noise floor is angle-dependent):
  static-fixed : hold the SAME easy, reproducible position, ~10 s per take,
                 3+ takes, do NOT touch the camera between takes.
  static-reset : same position, 3+ more takes, but fully re-set the tripod
                 between takes (move it, put it back roughly where it was).
  movement     : easy move(s) you can repeat identically, FEET ON THE SAME
                 footholds every take (variant B anchors to the ankles).
                 Either 1 move x 5+ takes, OR several moves x 3+ takes each —
                 tag each move's takes with the SAME move_id (move1, move2...);
                 repeatability is pooled within-move so different moves don't
                 pollute each other.
  calibration  : one clip standing straight next to the wall (full body,
                 head to floor visible); plus two holds roughly LEVEL with
                 each other at the working-zone depth, tape-measured
                 center-to-center. Optionally a second, vertically-separated
                 hold pair to test orientation sensitivity.
Then:
  1. fill footage/exp02/takes.csv  (filename, group, move_id, notes)
  2. uv run lab/extract_pose_mediapipe.py footage/exp02 --out lab/results/exp02-noise-floor/landmarks
  3. uv run lab/pick_points.py <calibration clip>   -> paste px coords into calibration.json
  4. uv run lab/exp02_noise_floor.py
"""


def frame_points(df: pd.DataFrame, idx: int, w: int, h: int) -> dict[str, metrics.Point]:
    def pt(i: int) -> metrics.Point:
        return (df[f"lm{i:02d}_x"].iat[idx] * w, df[f"lm{i:02d}_y"].iat[idx] * h)

    return {
        "l_sh": pt(SHOULDER_L), "r_sh": pt(SHOULDER_R),
        "l_hip": pt(HIP_L), "r_hip": pt(HIP_R),
        "l_ank": pt(ANKLE_L), "r_ank": pt(ANKLE_R),
    }


def analyze_take(csv_path: Path) -> dict:
    df, meta = read_landmarks(csv_path)
    w, h = meta["width"], meta["height"]

    core_ok = np.all(
        np.column_stack([df[f"lm{i:02d}_vis"].to_numpy()
                         for i in (SHOULDER_L, SHOULDER_R, HIP_L, HIP_R)]) >= CONF,
        axis=1,
    ) & (df["detected"].to_numpy() == 1)
    ankles_ok = core_ok & np.all(
        np.column_stack([df[f"lm{i:02d}_vis"].to_numpy()
                         for i in (ANKLE_L, ANKLE_R)]) >= CONF,
        axis=1,
    )

    a_vals, b_vals, c_vals, torso_vals = [], [], [], []
    for idx in range(len(df)):
        if not core_ok[idx]:
            continue
        p = frame_points(df, idx, w, h)
        torso = metrics.torso_length(p["l_sh"], p["r_sh"], p["l_hip"], p["r_hip"])
        torso_vals.append(torso)
        a_vals.append(metrics.hip_height(p["l_hip"], p["r_hip"], reference_y=h))
        if ankles_ok[idx]:
            ankle_mid_y = metrics.midpoint(p["l_ank"], p["r_ank"])[1]
            b = metrics.hip_height(p["l_hip"], p["r_hip"], reference_y=ankle_mid_y)
            b_vals.append(b)
            c_vals.append(metrics.relative_to(b, torso))

    return {
        "frames": len(df),
        "frames_core": int(core_ok.sum()),
        "frames_ankles": int(ankles_ok.sum()),
        "hipA_px": float(np.median(a_vals)) if a_vals else np.nan,
        "hipA_within_std": float(np.std(a_vals)) if a_vals else np.nan,
        "hipB_px": float(np.median(b_vals)) if b_vals else np.nan,
        "hipC_torso": float(np.median(c_vals)) if c_vals else np.nan,
        # peak (95th pct): the move-shaped quantity for movement takes —
        # a repeated identical move should reach the same highest hip point
        "hipB_peak_px": float(np.percentile(b_vals, 95)) if b_vals else np.nan,
        "hipC_peak_torso": float(np.percentile(c_vals, 95)) if c_vals else np.nan,
        "torso_px": float(np.median(torso_vals)) if torso_vals else np.nan,
        "_series": {"A": a_vals, "B": b_vals, "C": c_vals},
    }


def pooled_std(subgroups: list[np.ndarray]) -> tuple[float, int]:
    """Pool within-subgroup variances by degrees of freedom:
    sqrt( Σ(n_k-1)·s_k² / Σ(n_k-1) ). For movement takes grouped by move:
    each move contributes its own repeatability, so real move-to-move
    differences never enter the noise estimate. Returns (std, total_df).
    """
    num, df = 0.0, 0
    for vals in subgroups:
        vals = np.asarray(vals, float)
        vals = vals[~np.isnan(vals)]
        if len(vals) >= 2:
            num += (len(vals) - 1) * float(np.var(vals, ddof=1))
            df += len(vals) - 1
    if df == 0:
        return float("nan"), 0
    return float(np.sqrt(num / df)), df


def load_calibration() -> dict | None:
    """Return {methods: {name: cm_per_px}, pairwise_pct, max_disagreement_pct}.

    Supports the person-height method plus any number of labelled hold
    references (e.g. horizontal + vertical) so calibration consistency can be
    checked across orientations, not just person-vs-hold.
    """
    if not CAL_PATH.exists():
        return None
    cal = json.loads(CAL_PATH.read_text())
    methods: dict[str, float] = {}

    if cal.get("climber_height_cm"):
        pe = cal["person_extent"]
        px = metrics.distance(tuple(pe["top_px"]), tuple(pe["bottom_px"]))
        methods["person"] = metrics.cm_per_px(cal["climber_height_cm"], px)
    for ref in cal.get("hold_references", []):
        if ref.get("spacing_cm"):
            px = metrics.distance(tuple(ref["a_px"]), tuple(ref["b_px"]))
            methods[f"hold_{ref.get('label', '?')}"] = metrics.cm_per_px(
                ref["spacing_cm"], px)
    # legacy single-pair schema, still accepted
    if cal.get("hold_spacing_cm") and cal.get("hold_pair"):
        hp = cal["hold_pair"]
        px = metrics.distance(tuple(hp["a_px"]), tuple(hp["b_px"]))
        methods.setdefault("hold", metrics.cm_per_px(cal["hold_spacing_cm"], px))

    methods = {k: v for k, v in methods.items() if v == v}  # drop NaN
    if not methods:
        return None

    names = list(methods)
    pairwise = {
        f"{names[i]} vs {names[j]}":
            abs(methods[names[i]] - methods[names[j]])
            / ((methods[names[i]] + methods[names[j]]) / 2) * 100
        for i in range(len(names)) for j in range(i + 1, len(names))
    }
    return {
        "methods": methods,
        "pairwise_pct": pairwise,
        "max_disagreement_pct": max(pairwise.values()) if pairwise else None,
    }


def plot_takes(summary: pd.DataFrame, series: dict[str, dict], variant: str,
               label: str) -> None:
    fig, ax = plt.subplots(figsize=(11, 4.5))
    names, data, colors = [], [], []
    palette = {"static-fixed": "#2a9d8f", "static-reset": "#e76f51",
               "movement": "#457b9d"}
    for _, row in summary.sort_values(["group", "filename"]).iterrows():
        vals = series[row["filename"]][variant]
        if not vals:
            continue
        names.append(f"{row['filename']}\n[{row['group']}]")
        data.append(vals)
        colors.append(palette.get(row["group"], "gray"))
    if not data:
        plt.close(fig)
        return
    bp = ax.boxplot(data, tick_labels=names, showfliers=False, patch_artist=True)
    for patch, color in zip(bp["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.6)
    ax.set(ylabel=label, title=f"hip height variant {variant} per take")
    ax.tick_params(axis="x", labelsize=7)
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / f"takes_{variant}.png", dpi=110)
    plt.close(fig)


def main() -> int:
    if not TAKES_PATH.exists():
        EXP02_DIR.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(columns=TAKES_COLUMNS).to_csv(TAKES_PATH, index=False)
        if not CAL_PATH.exists():
            CAL_PATH.write_text(json.dumps(CAL_TEMPLATE, indent=2))
        print(f"created template {TAKES_PATH} and {CAL_PATH.name}")
        print(FILMING_CHECKLIST)
        return 1

    takes = pd.read_csv(TAKES_PATH)
    if takes.empty:
        print(f"{TAKES_PATH} is empty — film the takes first.")
        print(FILMING_CHECKLIST)
        return 1
    if "move_id" not in takes.columns:
        takes["move_id"] = ""
    takes["move_id"] = takes["move_id"].fillna("").astype(str).str.strip()
    bad_groups = set(takes["group"]) - set(GROUPS) - {"calibration"}
    if bad_groups:
        print(f"unknown group(s) in takes.csv: {bad_groups}; valid: {GROUPS}")
        return 1

    # movement takes must carry a move_id so repeatability pools within-move
    mv = takes[takes["group"] == "movement"]
    if len(mv) and (mv["move_id"] == "").any():
        missing_id = mv[mv["move_id"] == ""]["filename"].tolist()
        print(f"movement take(s) missing move_id: {missing_id}")
        print("tag every movement take with a move_id (move1, move2, ...).")
        return 1

    analysis_takes = takes[takes["group"].isin(GROUPS)]
    missing = [f for f in analysis_takes["filename"]
               if not landmarks_csv_path(LANDMARKS_DIR, EXP02_DIR / f,
                                         "mediapipe").exists()]
    if missing:
        print(f"missing landmarks for {len(missing)} take(s): {missing}")
        print("run: uv run lab/extract_pose_mediapipe.py footage/exp02 "
              "--out lab/results/exp02-noise-floor/landmarks")
        return 1

    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    rows, series = [], {}
    for _, t in analysis_takes.iterrows():
        csv_path = landmarks_csv_path(LANDMARKS_DIR, EXP02_DIR / t["filename"],
                                      "mediapipe")
        result = analyze_take(csv_path)
        series[t["filename"]] = result.pop("_series")
        rows.append({"filename": t["filename"], "group": t["group"],
                     "move_id": t["move_id"], **result})
        print(f"{t['filename']} [{t['group']}]  "
              f"hipA={result['hipA_px']:.0f}px  hipB={result['hipB_px']:.0f}px  "
              f"hipC={result['hipC_torso']:.3f}torso  "
              f"usable core/ankles: {result['frames_core']}/{result['frames_ankles']}"
              f" of {result['frames']}")

    summary = pd.DataFrame(rows)
    summary.to_csv(RESULTS_DIR / "takes_summary.csv", index=False)
    for variant, label in (("A", "px above frame bottom"),
                           ("B", "px above ankle midpoint"),
                           ("C", "fraction of torso length")):
        plot_takes(summary, series, variant, label)

    cal = load_calibration()
    scales = cal["methods"] if cal else {}

    def cm_columns(prefix: str, std_px: float) -> dict:
        return {f"{prefix}_cm_{name}": std_px * s for name, s in scales.items()}

    # --- static groups: between-take std of per-take median hip height,
    # pooled WITHIN position (move_id). static-fixed may hold several distinct
    # positions (pos1/pos2/...); the true delta is zero only within a position,
    # so pooling by move_id keeps real position differences out of the floor.
    # A single-position group (e.g. static-reset) collapses to a plain std. ---
    noise_rows = []
    for group in ("static-fixed", "static-reset"):
        g = summary[summary["group"] == group]
        if g.empty:
            continue
        by_pos = [sub for _, sub in g.groupby("move_id")]
        row: dict = {"group": group, "n_takes": len(g),
                     "n_positions": g["move_id"].nunique()}
        for col, name in (("hipA_px", "A_px"), ("hipB_px", "B_px"),
                          ("hipC_torso", "C_torso")):
            std, _ = pooled_std([sub[col].to_numpy() for sub in by_pos])
            row[f"std_{name}"] = std
        torso = float(g["torso_px"].median())
        row["std_C_pct_torso"] = row["std_C_torso"] * 100
        row["std_B_pct_torso"] = row["std_B_px"] / torso * 100 if torso else np.nan
        row.update(cm_columns("std_B", row["std_B_px"]))
        noise_rows.append(row)
    noise = pd.DataFrame(noise_rows)
    noise.to_csv(RESULTS_DIR / "noise_floor.csv", index=False)

    # --- movement: pooled WITHIN-move std of the peak (apex) hip height ---
    # each move's 3 takes give one repeatability estimate; pooling across moves
    # keeps real move-to-move differences out of the noise floor.
    mvt = summary[summary["group"] == "movement"]
    movement = None
    if not mvt.empty:
        by_move = [g for _, g in mvt.groupby("move_id")]
        mrow: dict = {"n_moves": mvt["move_id"].nunique(), "n_takes": len(mvt)}
        for col, name in (("hipB_peak_px", "Bpeak_px"),
                          ("hipC_peak_torso", "Cpeak_torso")):
            std, df = pooled_std([g[col].to_numpy() for g in by_move])
            mrow[f"std_{name}"] = std
            mrow[f"df_{name}"] = df
        torso = float(mvt["torso_px"].median())
        mrow["std_Bpeak_pct_torso"] = (mrow["std_Bpeak_px"] / torso * 100
                                       if torso else np.nan)
        mrow["std_Cpeak_pct_torso"] = mrow["std_Cpeak_torso"] * 100
        mrow.update(cm_columns("std_Bpeak", mrow["std_Bpeak_px"]))
        movement = pd.DataFrame([mrow])
        movement.to_csv(RESULTS_DIR / "movement_noise.csv", index=False)

    # ---- report ----
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    parts = [
        "# Test 2 — noise floor and calibration",
        f"_Generated {ts} from {len(summary)} takes._",
        "",
        "Between-take std (ddof=1) of per-take medians; the product's minimum",
        "honestly-reportable difference is **2×std**.",
        "",
        noise.to_string(index=False, float_format=lambda v: f"{v:.3f}"),
        "",
    ]
    if movement is not None:
        parts += [
            "## Movement repeatability (peak hip height, pooled within-move)",
            f"_{int(mrow['n_moves'])} move(s), {int(mrow['n_takes'])} takes, "
            f"pooled df={int(mrow.get('df_Bpeak_px', 0))}._",
            "",
            movement.to_string(index=False, float_format=lambda v: f"{v:.3f}"),
            "",
        ]

    if cal:
        parts += ["## Calibration (cm per px by method)",
                  json.dumps({k: round(v, 5)
                              for k, v in cal["methods"].items()}, indent=2)]
        if cal["pairwise_pct"]:
            parts += ["", "Pairwise disagreement:",
                      json.dumps({k: round(v, 2)
                                  for k, v in cal["pairwise_pct"].items()},
                                 indent=2)]
        agree = cal.get("max_disagreement_pct")
        if agree is not None:
            ok = agree <= PASS_CAL_AGREE_PCT
            parts += ["", f"**Criterion 2 (all methods agree "
                      f"≤{PASS_CAL_AGREE_PCT}%):** worst {agree:.1f}% → "
                      f"{'PASS' if ok else 'FAIL'}", ""]
        else:
            parts += ["", "_only one calibration method provided — agreement "
                      "not evaluable._", ""]
    else:
        parts += ["## Calibration", "_calibration.json not filled in — "
                  "criterion 2 not evaluated._", ""]

    reset = noise[noise["group"] == "static-reset"]
    fixed = noise[noise["group"] == "static-fixed"]
    crit1_pass = None
    if len(reset) and not np.isnan(reset["std_C_pct_torso"].iat[0]):
        v = reset["std_C_pct_torso"].iat[0]
        crit1_pass = v <= PASS_REL_STD_PCT
        parts += [f"**Criterion 1 (σ of relative hip height, static-reset, "
                  f"≤{PASS_REL_STD_PCT}% torso):** {v:.2f}% → "
                  f"{'PASS' if crit1_pass else 'FAIL'}", ""]
    else:
        parts += ["**Criterion 1:** not evaluable — need ≥2 static-reset takes "
                  "with usable ankle frames.", ""]

    # ---- minimum honestly reportable difference (2σ), per unit system ----
    parts += ["## Minimum honestly reportable difference (2σ)", ""]
    if len(fixed) and not np.isnan(fixed["std_A_px"].iat[0]):
        parts += [f"- Within one camera setup (variant A, static-fixed): "
                  f"**{2 * fixed['std_A_px'].iat[0]:.1f} px**"]
    if len(reset):
        r = reset.iloc[0]
        if not np.isnan(r["std_B_px"]):
            line = (f"- Across camera setups, wall-anchored (variant B, "
                    f"static-reset): **{2 * r['std_B_px']:.1f} px**")
            if scales:
                cms = [f"{2 * r['std_B_px'] * s:.2f} cm ({name})"
                       for name, s in scales.items()]
                line += " = " + " / ".join(cms)
            parts += [line]
        if not np.isnan(r["std_C_pct_torso"]):
            parts += [f"- Across camera setups, relative (variant C, "
                      f"static-reset): **{2 * r['std_C_pct_torso']:.2f}% of "
                      f"torso length**"]
    parts += [""]

    # ---- units decision input (the point of Test 2 per CLAUDE.md) ----
    cal_ok = bool(cal) and cal.get("max_disagreement_pct") is not None \
        and cal["max_disagreement_pct"] <= PASS_CAL_AGREE_PCT
    if crit1_pass is None:
        rec = "_Not enough data for a units recommendation yet._"
    elif cal_ok and crit1_pass:
        rec = ("Both worlds are open: calibration is consistent and the "
               "relative floor passes. Relative units remain the default "
               "(morphology-invariant, no calibration step in the product); "
               "absolute cm is available where a calibration reference exists.")
    elif crit1_pass:
        rec = ("Relative units only: the relative noise floor passes but "
               "calibration is missing or unreliable, so absolute cm claims "
               "are not honest yet.")
    else:
        rec = ("Neither unit system clears the bar — investigate the noise "
               "sources (ankle visibility? camera protocol?) before designing "
               "insight language.")
    parts += ["## Units decision (recommendation — final call is the developer's)",
              "", rec, ""]

    out = RESULTS_DIR / "summary.md"
    out.write_text("\n".join(parts), encoding="utf-8")
    print(f"\nwrote {RESULTS_DIR / 'takes_summary.csv'}")
    print(f"wrote {RESULTS_DIR / 'noise_floor.csv'}")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
