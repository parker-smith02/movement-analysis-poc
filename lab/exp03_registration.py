"""Test 2 (extension) — exp03: cross-camera-setup registration accuracy.

Question: when the phone comes off the tripod between attempts (the product
default — climbers rest minutes between burns), how accurately can two takes
be brought into one wall-fixed coordinate system, and which correction level
gets the cross-setup noise floor under the 2%-of-torso bar?

Methods compared on every pair of takes of the same scene:
  translation-1pt : shift by one clicked anchor's difference — what exp02
                    variant D does today (corrects translation only)
  similarity-2pt  : scale+rotation+translation fixed by two clicked holds —
                    the "two taps" product option (needs >=3 clicked points
                    so at least one is held out for evaluation)
  auto-similarity : estimateAffinePartial2D (RANSAC) on background feature
                    matches — zero taps
  auto-homography : findHomography (RANSAC) on background feature matches —
                    zero taps; the wall is PLANAR, so a homography maps
                    wall points between views exactly

Evaluation: residual |dy| (hip height is a y-measure; dx/d also recorded) at
clicked probe holds NOT used for fitting, split by pair class:
  same-setup : both takes from the untouched-tripod group (sf1) — measures
               click/feature noise, the floor of the method chain itself
  re-set     : any pair involving a tripod re-set (sr1) — the treatment

Hypothesis: translation-only leaves ~5-15 px y-error across re-sets (this is
the residual that shows up as exp02 run 3's 7 px / 3.2% floor); similarity
and the auto methods cut it to click-noise level (~2 px ~ 1% of the ~220 px
pos1 torso), which combined with the ~3 px pose/body-reproduction term
(exp02 variant B on clean takes) predicts a cross-setup floor of
sqrt(2^2 + 3.1^2) ~ 3.7 px ~ 1.7% torso — under the 2% bar.

Pass criterion (judgment call, stated up front): median |dy| at held-out
probe points over re-set pairs <= 2 px for at least one corrected method.

Inputs (no new filming needed):
  footage/exp02/registration_points.json     OPTIONAL, recommended: K>=3
      ordered holds per take via  uv run lab/pick_registration_points.py
  lab/results/exp02-noise-floor/run3-near-anchor/anchors-near.json
  lab/results/exp02-noise-floor/run2-toprow-anchor/anchors-toprow.json
      The two frozen exp02 anchor sets are 2 known hold correspondences per
      take, so translation-1pt and the auto methods are evaluable before any
      new clicking. similarity-2pt needs registration_points.json.
  lab/results/exp02-noise-floor/landmarks/    person mask for feature
      detection (the climber holds the same position in every take, so
      un-masked person features would contaminate the wall fit)

End-to-end check: the six takes all hold the same position (true hip delta
zero), so mapping every take's median hip/shoulder positions into one
reference take's coordinates via the fitted homographies and recomputing the
relative hip-height floor (per-take median form, df=5) measures the
CORRECTED cross-setup noise floor directly — including the climber's own
off-wall-plane parallax, which is real product error. Compared against the
uncorrected (translation-only, exp02 variant D) floor on the same six takes.

Outputs (lab/results/exp03-registration/): residuals.csv, summary.md,
plots/residuals.png, qa/ (feature-match and warp-difference images).
"""

from __future__ import annotations

import cmath
import itertools
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import cv2
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from pose_schema import N_LANDMARKS, landmarks_csv_path, read_landmarks

ROOT = Path(__file__).parent.parent
EXP02_DIR = ROOT / "footage" / "exp02"
EXP02_RESULTS = Path(__file__).parent / "results" / "exp02-noise-floor"
LANDMARKS_DIR = EXP02_RESULTS / "landmarks"
REG_POINTS_PATH = EXP02_DIR / "registration_points.json"
ANCHOR_SETS = {  # frozen exp02 clicks reused as known correspondences
    "hold_near": EXP02_RESULTS / "run3-near-anchor" / "anchors-near.json",
    "hold_top": EXP02_RESULTS / "run2-toprow-anchor" / "anchors-toprow.json",
}
RESULTS_DIR = Path(__file__).parent / "results" / "exp03-registration"

# the six takes that view the same scene: sf1 = camera untouched (control),
# sr1 = tripod re-set between takes (treatment)
TAKES = ["sf1-1.MOV", "sf1-2.MOV", "sf1-3.MOV",
         "sr1-1.MOV", "sr1-2.MOV", "sr1-3.MOV"]
SAME_SETUP_GROUP = {"sf1-1.MOV", "sf1-2.MOV", "sf1-3.MOV"}

PASS_MEDIAN_DY_PX = 2.0     # criterion: re-set median |dy| at held-out probes
MIN_FIT_SEPARATION = 50.0   # px between the two points fixing a similarity
RANSAC_THRESH_PX = 3.0
LOWE_RATIO = 0.75
POSE_BODY_PX = 3.1          # exp02 variant B, clean static-reset takes
REF_TAKE = "sr1-1.MOV"      # common coordinate frame for the end-to-end floor
CONF = 0.5


# ---------------------------------------------------------------- clicked fits

def fit_translation(p: tuple, q: tuple):
    """Map A->B by the offset of one corresponding point."""
    tx, ty = q[0] - p[0], q[1] - p[1]
    return lambda pt: (pt[0] + tx, pt[1] + ty)


def fit_similarity_2pt(p1: tuple, p2: tuple, q1: tuple, q2: tuple):
    """Similarity (scale+rotation+translation) fixed exactly by 2 points."""
    zp = complex(p2[0] - p1[0], p2[1] - p1[1])
    if abs(zp) < 1e-9:
        return None
    s = complex(q2[0] - q1[0], q2[1] - q1[1]) / zp

    def apply(pt):
        z = complex(pt[0] - p1[0], pt[1] - p1[1]) * s
        return (q1[0] + z.real, q1[1] + z.imag)

    return apply


# ------------------------------------------------------------------- auto fits

def person_mask(take: str, w: int, h: int) -> np.ndarray:
    """255 everywhere except an expanded bbox around the pose landmarks."""
    mask = np.full((h, w), 255, np.uint8)
    csv_path = landmarks_csv_path(LANDMARKS_DIR, EXP02_DIR / take, "mediapipe")
    if not csv_path.exists():
        return mask
    df, _ = read_landmarks(csv_path)
    det = df[df["detected"] == 1]
    if det.empty:
        return mask
    row = det.iloc[0]
    xs = np.array([row[f"lm{i:02d}_x"] for i in range(N_LANDMARKS)]) * w
    ys = np.array([row[f"lm{i:02d}_y"] for i in range(N_LANDMARKS)]) * h
    xs, ys = xs[~np.isnan(xs)], ys[~np.isnan(ys)]
    if not len(xs):
        return mask
    pad_x = 0.25 * (xs.max() - xs.min()) + 20
    pad_y = 0.25 * (ys.max() - ys.min()) + 20
    x0, x1 = int(max(0, xs.min() - pad_x)), int(min(w, xs.max() + pad_x))
    y0, y1 = int(max(0, ys.min() - pad_y)), int(min(h, ys.max() + pad_y))
    mask[y0:y1, x0:x1] = 0
    return mask


def read_frame0(take: str) -> np.ndarray | None:
    cap = cv2.VideoCapture(str(EXP02_DIR / take))
    cap.set(cv2.CAP_PROP_ORIENTATION_AUTO, 1)
    ok, frame = cap.read()
    cap.release()
    return frame if ok else None


def make_detector():
    if hasattr(cv2, "SIFT_create"):
        return cv2.SIFT_create(), cv2.NORM_L2, "SIFT"
    return cv2.ORB_create(5000), cv2.NORM_HAMMING, "ORB"


def detect_features(frame: np.ndarray, mask: np.ndarray, detector):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return detector.detectAndCompute(gray, mask)


def match_features(desA, desB, norm) -> list:
    matcher = cv2.BFMatcher(norm)
    knn = matcher.knnMatch(desA, desB, k=2)
    return [m for m, n in (p for p in knn if len(p) == 2)
            if m.distance < LOWE_RATIO * n.distance]


def auto_transforms(kpA, kpB, matches) -> dict:
    """Fit similarity and homography from matched features; return mappers."""
    out = {}
    if len(matches) < 8:
        return out
    src = np.float32([kpA[m.queryIdx].pt for m in matches]).reshape(-1, 1, 2)
    dst = np.float32([kpB[m.trainIdx].pt for m in matches]).reshape(-1, 1, 2)

    M, inl = cv2.estimateAffinePartial2D(src, dst, method=cv2.RANSAC,
                                         ransacReprojThreshold=RANSAC_THRESH_PX)
    if M is not None:
        out["auto-similarity"] = {
            "apply": lambda pt, M=M: tuple(
                (M @ np.array([pt[0], pt[1], 1.0]))[:2]),
            "n_inliers": int(inl.sum()) if inl is not None else 0,
        }
    H, inl = cv2.findHomography(src, dst, cv2.RANSAC, RANSAC_THRESH_PX)
    if H is not None:
        out["auto-homography"] = {
            "apply": lambda pt, H=H: tuple(cv2.perspectiveTransform(
                np.float32([[pt]]), H)[0, 0]),
            "n_inliers": int(inl.sum()) if inl is not None else 0,
            "H": H,
        }
    out["n_matches"] = len(matches)
    return out


# ------------------------------------------------------- end-to-end hip floor

def take_body_medians(take: str) -> tuple[tuple, tuple] | None:
    """Median hip-center and shoulder-center px over core-usable frames."""
    csv_path = landmarks_csv_path(LANDMARKS_DIR, EXP02_DIR / take, "mediapipe")
    if not csv_path.exists():
        return None
    df, meta = read_landmarks(csv_path)
    w, h = meta["width"], meta["height"]
    ok = df["detected"] == 1
    for i in (11, 12, 23, 24):  # shoulders, hips
        ok &= df[f"lm{i:02d}_vis"] >= CONF
    d = df[ok]
    if d.empty:
        return None
    hip = (float(((d["lm23_x"] + d["lm24_x"]) / 2 * w).median()),
           float(((d["lm23_y"] + d["lm24_y"]) / 2 * h).median()))
    sh = (float(((d["lm11_x"] + d["lm12_x"]) / 2 * w).median()),
          float(((d["lm11_y"] + d["lm12_y"]) / 2 * h).median()))
    return hip, sh


def map_pt(H: np.ndarray | None, pt: tuple) -> tuple:
    if H is None:
        return pt
    return tuple(cv2.perspectiveTransform(np.float32([[pt]]), H)[0, 0])


def end_to_end_floor(homs: dict, near_anchor: dict) -> dict | None:
    """Corrected vs uncorrected relative hip-height floor over the 6 takes."""
    anchor_ref_y = near_anchor[REF_TAKE][1]
    corrected, uncorrected = [], []
    for t in TAKES:
        body = take_body_medians(t)
        if body is None or t not in near_anchor:
            return None
        hip, sh = body
        # uncorrected = exp02 variant D: own-take anchor, own-take scale
        d_own = near_anchor[t][1] - hip[1]
        torso_own = float(np.hypot(sh[0] - hip[0], sh[1] - hip[1]))
        uncorrected.append(d_own / torso_own)
        # corrected: map body into the reference take's wall coordinates
        if t == REF_TAKE:
            H = None
        elif (t, REF_TAKE) in homs:
            H = homs[(t, REF_TAKE)]
        elif (REF_TAKE, t) in homs:
            H = np.linalg.inv(homs[(REF_TAKE, t)])
        else:
            return None
        hip_r, sh_r = map_pt(H, hip), map_pt(H, sh)
        d_ref = anchor_ref_y - hip_r[1]
        torso_ref = float(np.hypot(sh_r[0] - hip_r[0], sh_r[1] - hip_r[1]))
        corrected.append(d_ref / torso_ref)
    return {
        "n": len(TAKES),
        "std_uncorrected_pct": float(np.std(uncorrected, ddof=1)) * 100,
        "std_corrected_pct": float(np.std(corrected, ddof=1)) * 100,
        "uncorrected": uncorrected,
        "corrected": corrected,
    }


# ------------------------------------------------------------- correspondences

def load_points() -> dict[str, dict[str, tuple]]:
    """Return {point_name: {take: (x, y)}} from all available click sources."""
    points: dict[str, dict[str, tuple]] = {}
    for name, path in ANCHOR_SETS.items():
        if not path.exists():
            continue
        anchors = json.loads(path.read_text())["anchors"]
        points[name] = {t: tuple(anchors[t]["px"]) for t in TAKES
                        if anchors.get(t)}
    if REG_POINTS_PATH.exists():
        reg = json.loads(REG_POINTS_PATH.read_text())
        for take, pts in reg.get("takes", {}).items():
            if take not in TAKES:
                continue
            for i, xy in enumerate(pts):
                points.setdefault(f"reg{i + 1:02d}", {})[take] = tuple(xy)
    return points


# ------------------------------------------------------------------------ main

def main() -> int:
    missing = [t for t in TAKES if not (EXP02_DIR / t).exists()]
    if missing:
        print(f"missing clips: {missing}")
        return 1
    points = load_points()
    if not points:
        print("no clicked correspondences found — need the exp02 anchor "
              "snapshots or registration_points.json")
        return 1
    n_named = {n: len(d) for n, d in points.items()}
    print(f"correspondences: { {n: f'{k}/{len(TAKES)} takes' for n, k in n_named.items()} }")

    (RESULTS_DIR / "plots").mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "qa").mkdir(parents=True, exist_ok=True)

    # features once per take
    detector, norm, det_name = make_detector()
    frames, feats = {}, {}
    for t in TAKES:
        frame = read_frame0(t)
        if frame is None:
            print(f"cannot read {t}")
            return 1
        h, w = frame.shape[:2]
        kp, des = detect_features(frame, person_mask(t, w, h), detector)
        frames[t], feats[t] = frame, (kp, des)
        print(f"{t}: {len(kp)} {det_name} features (person masked)")

    rows, pair_meta, homs = [], [], {}
    for a, b in itertools.combinations(TAKES, 2):
        pair_class = ("same-setup" if a in SAME_SETUP_GROUP
                      and b in SAME_SETUP_GROUP else "re-set")
        common = {n: (d[a], d[b]) for n, d in points.items()
                  if a in d and b in d}

        def record(method: str, apply, fit_names: set[str]) -> None:
            for name, (pa, pb) in common.items():
                if name in fit_names:
                    continue
                px, py = apply(pa)
                rows.append({"take_a": a, "take_b": b, "class": pair_class,
                             "method": method, "eval_point": name,
                             "dx": px - pb[0], "dy": py - pb[1],
                             "d": float(np.hypot(px - pb[0], py - pb[1]))})

        # clicked: translation on each single point, evaluated on the others
        for name, (pa, pb) in common.items():
            record("translation-1pt", fit_translation(pa, pb), {name})
        # clicked: similarity on each sufficiently-separated pair of points
        for (n1, (p1, q1)), (n2, (p2, q2)) in itertools.combinations(
                common.items(), 2):
            if np.hypot(p2[0] - p1[0], p2[1] - p1[1]) < MIN_FIT_SEPARATION:
                continue
            fit = fit_similarity_2pt(p1, p2, q1, q2)
            if fit:
                record("similarity-2pt", fit, {n1, n2})

        # automatic, from background features (clicked points all held out)
        kpA, desA = feats[a]
        kpB, desB = feats[b]
        matches = (match_features(desA, desB, norm)
                   if desA is not None and desB is not None else [])
        auto = auto_transforms(kpA, kpB, matches)
        if "auto-homography" in auto:
            homs[(a, b)] = auto["auto-homography"]["H"]
        for method in ("auto-similarity", "auto-homography"):
            if method in auto:
                record(method, auto[method]["apply"], set())
        pair_meta.append({"take_a": a, "take_b": b, "class": pair_class,
                          "n_matches": auto.get("n_matches", 0),
                          "inl_sim": auto.get("auto-similarity", {}).get("n_inliers", 0),
                          "inl_hom": auto.get("auto-homography", {}).get("n_inliers", 0)})

        # QA images for the most-displaced re-set pair
        if (a, b) == ("sr1-1.MOV", "sr1-3.MOV") and "auto-homography" in auto:
            good = matches[:80]
            vis = cv2.drawMatches(frames[a], kpA, frames[b], kpB, good, None,
                                  flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS)
            cv2.imwrite(str(RESULTS_DIR / "qa" / "matches_sr1-1_sr1-3.png"),
                        cv2.resize(vis, None, fx=0.4, fy=0.4))
            hA, wA = frames[b].shape[:2]
            warped = cv2.warpPerspective(frames[a], auto["auto-homography"]["H"],
                                         (wA, hA))
            diff = cv2.absdiff(warped, frames[b])
            cv2.imwrite(str(RESULTS_DIR / "qa" / "warpdiff_sr1-1_sr1-3.png"),
                        cv2.resize(diff, None, fx=0.4, fy=0.4))

    res = pd.DataFrame(rows)
    res.to_csv(RESULTS_DIR / "residuals.csv", index=False)
    meta = pd.DataFrame(pair_meta)

    agg = (res.assign(abs_dy=res.dy.abs())
           .groupby(["method", "class"])["abs_dy"]
           .agg(n="count", median="median",
                p95=lambda v: float(np.percentile(v, 95)), max="max")
           .reset_index())

    # torso scale for % context (median over these six takes, exp02 run 3)
    torso = 220.0
    ts_path = EXP02_RESULTS / "takes_summary.csv"
    if ts_path.exists():
        ts = pd.read_csv(ts_path)
        v = ts[ts.filename.isin(TAKES)]["torso_px"].median()
        if v == v:
            torso = float(v)

    # plot: |dy| by method, colored by pair class
    fig, ax = plt.subplots(figsize=(9, 4.5))
    methods = [m for m in ("translation-1pt", "similarity-2pt",
                           "auto-similarity", "auto-homography")
               if m in set(res.method)]
    colors = {"same-setup": "#2a9d8f", "re-set": "#e76f51"}
    for i, m in enumerate(methods):
        for j, cls in enumerate(("same-setup", "re-set")):
            v = res[(res.method == m) & (res["class"] == cls)].dy.abs()
            if v.empty:
                continue
            x = i + (j - 0.5) * 0.3 + np.random.default_rng(0).uniform(
                -0.06, 0.06, len(v))
            ax.scatter(x, v, s=18, alpha=0.65, color=colors[cls],
                       label=cls if i == 0 else None)
            ax.hlines(v.median(), i + (j - 0.5) * 0.3 - 0.12,
                      i + (j - 0.5) * 0.3 + 0.12, color=colors[cls], lw=2)
    ax.axhline(PASS_MEDIAN_DY_PX, ls="--", c="gray", lw=1,
               label=f"pass bar ({PASS_MEDIAN_DY_PX:.0f} px)")
    ax.set(xticks=range(len(methods)), xticklabels=methods,
           ylabel="|dy| at held-out probe holds (px)",
           title="cross-take registration residual by method")
    ax.legend()
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "plots" / "residuals.png", dpi=110)
    plt.close(fig)

    # ---- report ----
    ts_now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    reset_meds = {m: agg[(agg.method == m) & (agg["class"] == "re-set")]
                  ["median"].squeeze()
                  for m in methods
                  if not agg[(agg.method == m) & (agg["class"] == "re-set")].empty}
    corrected = {m: v for m, v in reset_meds.items() if m != "translation-1pt"}
    best = min(corrected, key=corrected.get) if corrected else None
    passed = best is not None and corrected[best] <= PASS_MEDIAN_DY_PX

    parts = [
        "# exp03 — cross-setup registration accuracy",
        f"_Generated {ts_now}. {det_name} features, person-masked; "
        f"{len(points)} clicked correspondence(s): {sorted(points)}. "
        f"Torso scale: {torso:.0f} px._",
        "",
        "|dy| at held-out clicked probe holds, px:",
        "",
        agg.to_string(index=False, float_format=lambda v: f"{v:.2f}"),
        "",
        "Auto-method match/inlier counts per pair:",
        "",
        meta.to_string(index=False),
        "",
    ]
    if reset_meds:
        parts += ["## Re-set pairs, medians (the product's default regime)", ""]
        for m in methods:
            if m in reset_meds:
                v = reset_meds[m]
                parts += [f"- {m}: **{v:.2f} px** = {v / torso * 100:.2f}% torso"]
        parts += [""]
    if best:
        combined = float(np.hypot(corrected[best], POSE_BODY_PX))
        parts += [
            f"**Pass criterion (median |dy|, re-set pairs, ≤"
            f"{PASS_MEDIAN_DY_PX:.0f} px for a corrected method):** best is "
            f"{best} at {corrected[best]:.2f} px → "
            f"{'PASS' if passed else 'FAIL'}",
            "",
            f"Predicted cross-setup hip-height floor with {best}: "
            f"sqrt({corrected[best]:.2f}² registration + {POSE_BODY_PX}² "
            f"pose/body) = **{combined:.2f} px ≈ "
            f"{combined / torso * 100:.2f}% torso** "
            f"(2σ ≈ {2 * combined / torso * 100:.2f}%) vs the 2% bar. "
            "Prediction only — confirm by re-running the exp02 noise floor "
            "with this correction applied.",
            "",
        ]
    if "similarity-2pt" not in set(res.method):
        parts += ["_similarity-2pt not evaluable: needs ≥3 clicked points "
                  "per take → run `uv run lab/pick_registration_points.py`._",
                  ""]

    # ---- end-to-end: recompute the exp02 relative hip floor, corrected ----
    e2e = (end_to_end_floor(homs, points.get("hold_near", {}))
           if "hold_near" in points else None)
    if e2e:
        parts += [
            "## End-to-end: relative hip-height floor over all six takes "
            f"(same position, true delta zero, df={e2e['n'] - 1})",
            "",
            f"- uncorrected (exp02 variant D, per-take near anchor): "
            f"std **{e2e['std_uncorrected_pct']:.2f}% torso** "
            f"(2σ {2 * e2e['std_uncorrected_pct']:.2f}%)",
            f"- homography-corrected (all takes in {REF_TAKE} coordinates, "
            f"zero taps): std **{e2e['std_corrected_pct']:.2f}% torso** "
            f"(2σ {2 * e2e['std_corrected_pct']:.2f}%)",
            "",
            f"vs the 2% criterion-1 bar. Includes the climber's off-plane "
            "parallax (real product error). Per-take values (D/torso): "
            f"uncorrected {['%.3f' % v for v in e2e['uncorrected']]}, "
            f"corrected {['%.3f' % v for v in e2e['corrected']]}.",
            "",
        ]

    out = RESULTS_DIR / "summary.md"
    out.write_text("\n".join(parts), encoding="utf-8")
    print(f"\nwrote {RESULTS_DIR / 'residuals.csv'}")
    print(f"wrote {out}")
    print("\n" + agg.to_string(index=False,
                               float_format=lambda v: f"{v:.2f}"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
