# -*- coding: utf-8 -*-
"""
Canonical N170 scrambler (color preserved correctly)
- Fully scrambled (alpha = 0.0)
- Uses ONE shared random phase field for R,G,B  -> avoids hue fringing
- After IFFT, per-channel HISTOGRAM MATCHING to the original channel
  (stronger than mean/std: matches the whole color distribution)
"""

import os, glob
import numpy as np
from PIL import Image, UnidentifiedImageError

# ---------- CONFIG ----------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IN_DIR   = os.path.join(BASE_DIR, "media")
OUT_DIR  = IN_DIR
ALPHA = 0.0          # canonical: fully scrambled
RANDOM_SEED = 1234   # lock set for reproducibility (set None to vary)
# ----------------------------

# ---------- HELPERS ----------
def is_image_ok(path):
    try:
        with Image.open(path) as im:
            im.verify()
        return True
    except Exception:
        return False

def load_rgb01(path):
    im = Image.open(path).convert("RGB")
    arr = np.asarray(im, dtype=np.float32) / 255.0  # H x W x 3
    return arr

def save_rgb01(path, arr):
    arr = np.clip(arr, 0.0, 1.0)
    Image.fromarray((arr * 255.0).astype(np.uint8), mode="RGB").save(path, quality=95)

def wrap_phase(ph):
    return (ph + np.pi) % (2*np.pi) - np.pi

def hist_match_channel(src, tmpl):
    """
    Histogram match 2D array src to 2D array tmpl (both float in [0,1]).
    Returns src' whose histogram follows tmpl.
    """
    s = src.ravel()
    t = tmpl.ravel()
    s_values, s_idx, s_counts = np.unique(s, return_inverse=True, return_counts=True)
    t_values, t_counts = np.unique(t, return_counts=True)
    s_quantiles = np.cumsum(s_counts).astype(np.float64) / s.size
    t_quantiles = np.cumsum(t_counts).astype(np.float64) / t.size
    # interpolate target values at source quantiles
    interp_t_values = np.interp(s_quantiles, t_quantiles, t_values)
    matched = interp_t_values[s_idx].reshape(src.shape)
    return matched.astype(np.float32)

def phase_scramble_color_shared(img01, alpha=0.0, rng=None):
    """
    Phase-scramble with a SINGLE random phase field shared across R,G,B.
    Per-channel amplitude preserved; phase fully randomized when alpha=0.
    """
    if rng is None:
        rng = np.random.default_rng()
    H, W, C = img01.shape
    assert C == 3

    # Build one random phase field (H x W)
    phi_rand = rng.uniform(-np.pi, np.pi, size=(H, W)).astype(np.float32)

    out = np.empty_like(img01)
    for c in range(3):
        x = img01[..., c]
        F = np.fft.fft2(x)
        A = np.abs(F).astype(np.float32)
        phi_orig = np.angle(F).astype(np.float32)

        # Mix with shared phi_rand (alpha=0 -> pure random)
        phi_mix = wrap_phase(alpha * phi_orig + (1.0 - alpha) * phi_rand)

        rec = np.fft.ifft2(A * np.exp(1j * phi_mix))
        out[..., c] = np.real(rec).astype(np.float32)

    # DO NOT min-max; we’ll histogram-match next
    return out
# ----------------------------

def batch(paths, label, rng):
    for p in paths:
        base = os.path.basename(p)
        stem, _ = os.path.splitext(base)
        try:
            x = load_rgb01(p)  # original in [0,1]
        except UnidentifiedImageError:
            print(f"[SKIP] {base} (unreadable)")
            continue
        except Exception as e:
            print(f"[SKIP] {base} ({e})")
            continue

        # 1) Shared-phase scramble (alpha=0.0 for canonical)
        x_scr = phase_scramble_color_shared(x, alpha=ALPHA, rng=rng)

        # 2) Per-channel histogram matching back to original channel
        x_s = np.empty_like(x_scr)
        for c in range(3):
            x_s[..., c] = hist_match_channel(x_scr[..., c], x[..., c])

        # 3) Clip and save
        x_s = np.clip(x_s, 0.0, 1.0)
        idx = stem.split('_')[-1]
        out_name = (f"scrambled_face_{idx}.jpg" if label == "face"
                    else f"scrambled_car_{idx}.jpg")
        save_rgb01(os.path.join(OUT_DIR, out_name), x_s)
        print(f"[OK] {base} -> {out_name} (alpha={ALPHA}, shared-phase + hist-match)")

# ---------- RUN ----------
if __name__ == "__main__":
    all_faces = sorted(glob.glob(os.path.join(IN_DIR, "face_*.jpg")))
    all_cars  = sorted(glob.glob(os.path.join(IN_DIR,  "car_*.jpg")))
    faces = [p for p in all_faces if is_image_ok(p)]
    cars  = [p for p in all_cars  if is_image_ok(p)]

#    skipped = (set(all_faces) - set(faces)) | (set(all_cars) - set(cars))
#    if skipped:
#        print("Skipped unreadable files:")
#        for b in sorted(skipped):
#            print("  -", os.path.basename(b))

    if not faces and not cars:
        raise SystemExit(f"No valid inputs in {IN_DIR}")

    print(f"Input: faces={len(faces)} cars={len(cars)}")
    print(f"Mode : alpha={ALPHA} (canonical), shared-phase across RGB + per-channel histogram matching")

    rng = np.random.default_rng(RANDOM_SEED) if RANDOM_SEED is not None else np.random.default_rng()
    batch(faces, "face", rng)
    batch(cars,  "car",  rng)

    print("\nDone.")
