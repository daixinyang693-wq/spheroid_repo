"""
================================================================================
Spheroid Analysis Pipeline
================================================================================
Automated quantification of spheroid morphology and perispheroid debris
in brightfield microplate images.

Imaging setup : Brightfield, single-channel, RGB TIFF or JPEG
Plate layout  : 7 columns x 6 rows (42 wells)
Pixel size    : 2.27 µm/px

Dependencies
------------
    pip install -r requirements.txt

Usage
-----
    python src/spheroid_analysis.py --input /path/to/images --output /path/to/results
    python src/spheroid_analysis.py --help
================================================================================
"""

import argparse
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

import numpy as np
import pandas as pd
import tifffile
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from pathlib import Path
from scipy.ndimage import binary_dilation
from skimage.filters import threshold_local, threshold_triangle, threshold_yen
from skimage.measure import regionprops, label
from skimage.morphology import remove_small_objects, remove_small_holes
from skimage.transform import resize


# ==============================================================================
# DEFAULT PARAMETERS
# ==============================================================================
DEFAULTS = {
    "pixel_size":         2.27,
    "n_cols":             7,
    "n_rows":             6,
    "band_width":         160,
    "band_thresh_method": "triangle",
    "debris_threshold":   115,
    "detect_scale":       8,
    "min_spheroid_area":  9530,
}


# ==============================================================================
# CLI
# ==============================================================================
def parse_args():
    p = argparse.ArgumentParser(
        description="Automated spheroid morphology and debris analysis."
    )
    p.add_argument("--input",   required=True,  help="Input folder containing images")
    p.add_argument("--output",  required=True,  help="Output folder for results")
    p.add_argument("--pixel_size",    type=float, default=DEFAULTS["pixel_size"],
                   help=f"Pixel size in µm/px (default: {DEFAULTS['pixel_size']})")
    p.add_argument("--n_cols",        type=int,   default=DEFAULTS["n_cols"],
                   help=f"Number of plate columns (default: {DEFAULTS['n_cols']})")
    p.add_argument("--n_rows",        type=int,   default=DEFAULTS["n_rows"],
                   help=f"Number of plate rows (default: {DEFAULTS['n_rows']})")
    p.add_argument("--band_width",    type=int,   default=DEFAULTS["band_width"],
                   help=f"Band width in original-image pixels (default: {DEFAULTS['band_width']})")
    p.add_argument("--band_thresh",   default=DEFAULTS["band_thresh_method"],
                   choices=["triangle", "yen"],
                   help="Auto-threshold method for band signal detection")
    p.add_argument("--debris_threshold", type=float, default=DEFAULTS["debris_threshold"],
                   help=f"Band_Mean below this → debris (default: {DEFAULTS['debris_threshold']})")
    return p.parse_args()


# ==============================================================================
# SECTION 1  IMAGE LOADING
# ==============================================================================

def load_image(img_path: Path) -> np.ndarray:
    """Load image as 2-D float32 grayscale array (supports TIFF and JPEG/PNG)."""
    suffix = img_path.suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png"}:
        from PIL import Image as PILImage
        img = np.array(PILImage.open(str(img_path)))
    else:
        img = tifffile.imread(str(img_path))

    img = np.squeeze(img)
    if img.ndim == 3:
        return (0.299 * img[:, :, 0] +
                0.587 * img[:, :, 1] +
                0.114 * img[:, :, 2]).astype(np.float32)
    return img.astype(np.float32)


def make_thumbnail(img_full: np.ndarray, scale: int) -> np.ndarray:
    """Downsample and normalise to uint8 for fast localisation."""
    h, w = img_full.shape
    small = resize(img_full, (h // scale, w // scale),
                   preserve_range=True, anti_aliasing=True).astype(np.float32)
    mn, mx = small.min(), small.max()
    return ((small - mn) / (mx - mn + 1e-8) * 255).astype(np.uint8)


# ==============================================================================
# SECTION 2  VALID REGION DETECTION
# ==============================================================================

def detect_valid_region(img_u8: np.ndarray) -> tuple:
    """Remove black borders by scanning row/column mean intensities."""
    row_mean = img_u8.mean(axis=1)
    col_mean = img_u8.mean(axis=0)
    H, W = img_u8.shape
    T = 60

    y_start = next((i for i in range(H)           if row_mean[i] > T), 0)
    y_end   = next((i for i in range(H-1, -1, -1) if row_mean[i] > T), H-1)
    x_start = next((i for i in range(W)           if col_mean[i] > T), 0)
    x_end   = next((i for i in range(W-1, -1, -1) if col_mean[i] > T), W-1)

    y_start = min(y_start + 5, H)
    x_start = min(x_start + 5, W)
    x_end   = max(x_end   - 5, 0)
    y_end   = max(y_end   - 5, 0)

    print(f"    Valid region: x={x_start}–{x_end}, y={y_start}–{y_end}")
    return y_start, y_end, x_start, x_end


# ==============================================================================
# SECTION 3  SPHEROID LOCALISATION  (thumbnail)
# ==============================================================================

def detect_candidates(img_u8, y_start, y_end, x_start, x_end) -> list:
    """Detect dark candidate spheroids via local adaptive thresholding."""
    valid = img_u8[y_start:y_end, x_start:x_end]
    dark  = valid < threshold_local(valid, block_size=51, offset=15)
    dark  = remove_small_objects(dark, min_size=100)
    dark  = remove_small_holes(dark, area_threshold=200)

    candidates = []
    for p in regionprops(label(dark)):
        area = p.area
        circ = (4 * np.pi * area / p.perimeter ** 2) if p.perimeter > 0 else 0
        if 200 < area < 3000 and circ > 0.4:
            candidates.append({
                "cx": x_start + p.centroid[1],
                "cy": y_start + p.centroid[0],
                "area": area,
            })
    return candidates


def assign_grid(candidates, y_start, y_end, x_start, x_end,
                n_rows, n_cols) -> tuple:
    """Assign candidates to a regular grid; skip empty wells (no fallback)."""
    cell_w = (x_end - x_start) / n_cols
    cell_h = (y_end - y_start) / n_rows
    detections, sid = [], 0

    for row in range(n_rows):
        for col in range(n_cols):
            sid += 1
            gx1 = x_start + col * cell_w;       gx2 = gx1 + cell_w
            gy1 = y_start + row * cell_h;        gy2 = gy1 + cell_h

            in_cell = [c for c in candidates
                       if gx1 <= c["cx"] < gx2 and gy1 <= c["cy"] < gy2]
            if not in_cell:
                print(f"    [{row+1},{col+1}] no candidate — skipped")
                continue

            best = max(in_cell, key=lambda c: c["area"])
            detections.append({"id": sid, "row": row+1, "col": col+1,
                                "cx_small": best["cx"], "cy_small": best["cy"]})

    return detections, cell_w, cell_h


# ==============================================================================
# SECTION 4  FULL-RESOLUTION MEASUREMENT
# ==============================================================================

def extract_roi(img_full, cx, cy, hw, hh) -> tuple:
    """Crop a full-resolution ROI centred on the detected spheroid."""
    H, W = img_full.shape
    y1, y2 = max(0, int(cy-hh)), min(H, int(cy+hh))
    x1, x2 = max(0, int(cx-hw)), min(W, int(cx+hw))
    return img_full[y1:y2, x1:x2], y1, x1


def segment_spheroid(roi: np.ndarray, min_size: int) -> np.ndarray:
    """
    Segment the spheroid at full resolution.
    Primary: local adaptive threshold.
    Fallback: global 20th-percentile threshold.
    """
    mn, mx   = roi.min(), roi.max()
    norm     = ((roi - mn) / (mx - mn + 1e-8) * 255).astype(np.uint8)
    block    = min(norm.shape[0], norm.shape[1], 201)
    block    = block if block % 2 else block - 1
    block    = max(block, 11)

    dark = norm < threshold_local(norm, block_size=block, offset=15)
    dark = remove_small_objects(dark, min_size=min_size)
    dark = remove_small_holes(dark, area_threshold=2000)
    props = regionprops(label(dark))

    if not props:                                       # fallback
        dark  = norm < np.percentile(norm, 20)
        dark  = remove_small_objects(dark, min_size=min_size)
        props = regionprops(label(dark))

    if not props:
        return np.zeros(roi.shape, dtype=bool)

    best = max(props, key=lambda p: p.area)
    return label(dark) == best.label


def measure_morphology(mask, roi, pixel_size) -> dict:
    """Morphological descriptors in physical units."""
    props = regionprops(mask.astype(int), intensity_image=roi)
    if not props:
        return {}
    p    = props[0]
    a    = p.area
    per  = p.perimeter
    circ = (4 * np.pi * a / per ** 2) if per > 0 else 0
    mn   = p.axis_minor_length
    ar   = (p.axis_major_length / mn) if mn > 0 else np.nan
    return {
        "Area_um2":      round(a * pixel_size ** 2, 2),
        "Perimeter_um":  round(per * pixel_size, 2),
        "Circularity":   round(circ, 4),
        "AspectRatio":   round(ar, 4)     if not np.isnan(ar) else np.nan,
        "Roundness":     round(1/ar, 4)   if (not np.isnan(ar) and ar) else np.nan,
        "Solidity":      round(p.solidity, 4),
        "Eccentricity":  round(p.eccentricity, 4),
        "MeanIntensity": round(float(p.intensity_mean), 4),
        "IntDen":        round(float(p.intensity_mean * a), 2),
    }


# ==============================================================================
# SECTION 5  PERISPHEROID BAND ANALYSIS
# ==============================================================================

def generate_band(mask, band_width) -> tuple:
    """Band = BinaryDilation(mask, iterations=band_width) AND NOT mask."""
    inner = mask.astype(bool)
    outer = binary_dilation(inner, iterations=band_width)
    return inner, outer & ~inner


def measure_band_intensity(roi, band) -> dict:
    """
    Sample band intensities from the ORIGINAL image via boolean indexing.
    Never measure on a mask image.
    """
    px = roi[band]
    if px.size == 0:
        return {"Band_Mean": np.nan, "Band_Std": np.nan,
                "Band_Min":  np.nan, "Band_Max": np.nan}
    return {
        "Band_Mean": round(float(px.mean()), 4),
        "Band_Std":  round(float(px.std()),  4),
        "Band_Min":  round(float(px.min()),  4),
        "Band_Max":  round(float(px.max()),  4),
    }


def detect_band_signal(roi, band, method, pixel_size) -> dict:
    """Count and quantify dark signal particles within the band."""
    px = roi[band]
    if px.size == 0:
        return {"Band_SignalArea_um2": 0, "Band_Count": 0, "Band_ThreshVal": np.nan}

    fn = {"triangle": threshold_triangle, "yen": threshold_yen}.get(
        method, threshold_triangle)
    try:
        tv = fn(px)
    except Exception:
        tv = px.mean()

    sig   = remove_small_objects((roi < tv) & band, min_size=50)
    n_p   = len(regionprops(label(sig)))
    return {
        "Band_SignalArea_um2": round(sig.sum() * pixel_size ** 2, 4),
        "Band_Count":          n_p,
        "Band_ThreshVal":      round(float(tv), 4),
    }


# ==============================================================================
# SECTION 6  DEBRIS CLASSIFICATION
# ==============================================================================

def classify_debris(band_mean: float, threshold: float) -> tuple:
    """
    Classify well as debris-positive if Band_Mean < threshold.
    Threshold = 115 a.u. (sensitivity 100%, specificity 96%, n=61 wells).
    """
    has_debris   = int(band_mean < threshold)
    debris_score = round(threshold - band_mean, 2)
    return has_debris, debris_score


# ==============================================================================
# SECTION 7  OVERLAY
# ==============================================================================

def save_overlay(img_u8, detections, x_start, y_start, x_end, y_end,
                 band_width, scale, output_path, title):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 10), facecolor="#0d1117")
    fig.suptitle(title, color="white", fontsize=13)
    colors = plt.cm.tab20.colors

    for ax, ttl in zip([ax1, ax2], ["Spheroid detection", "Perispheroid band"]):
        ax.imshow(img_u8, cmap="gray"); ax.axis("off")
        ax.set_title(ttl, color="#58a6ff", fontsize=11)
        ax.add_patch(plt.Rectangle((x_start, y_start), x_end-x_start, y_end-y_start,
                                   lw=1.5, edgecolor="lime", facecolor="none", alpha=0.5))

    for det in detections:
        sid = det["id"]; c = colors[(sid-1) % 20]
        cx_s, cy_s = det["cx_small"], det["cy_small"]
        for ax in [ax1, ax2]:
            ax.plot(cx_s, cy_s, "+", color=c, markersize=12, markeredgewidth=2)
            ax.text(cx_s+2, cy_s-2, str(sid), color="white", fontsize=6, fontweight="bold")
        ax2.add_patch(plt.Circle((cx_s, cy_s), band_width/scale,
                                 color=c, fill=False, lw=1.5, alpha=0.8))

    plt.tight_layout()
    plt.savefig(str(output_path), dpi=150, bbox_inches="tight", facecolor="#0d1117")
    plt.close(fig)


# ==============================================================================
# SECTION 8  PER-IMAGE PROCESSING
# ==============================================================================

def process_image(img_path: Path, output_dir: Path, params: dict) -> pd.DataFrame:
    print(f"\n{'='*60}\nImage: {img_path.name}")

    img_full = load_image(img_path)
    print(f"    Full resolution: {img_full.shape[0]} × {img_full.shape[1]} px")

    scale  = params["detect_scale"]
    img_u8 = make_thumbnail(img_full, scale)

    y_start, y_end, x_start, x_end = detect_valid_region(img_u8)
    candidates = detect_candidates(img_u8, y_start, y_end, x_start, x_end)
    print(f"    Candidates: {len(candidates)}")

    detections, cell_w_s, cell_h_s = assign_grid(
        candidates, y_start, y_end, x_start, x_end,
        params["n_rows"], params["n_cols"])
    print(f"    Detected: {len(detections)} / {params['n_rows']*params['n_cols']}")

    if not detections:
        print("    No spheroids — skipped.")
        return pd.DataFrame()

    roi_hw = int(cell_w_s * scale * 0.50)
    roi_hh = int(cell_h_s * scale * 0.45)
    rows   = []

    for det in detections:
        sid     = det["id"]
        cx_full = det["cx_small"] * scale
        cy_full = det["cy_small"] * scale

        roi, _, _ = extract_roi(img_full, cx_full, cy_full, roi_hw, roi_hh)
        mask      = segment_spheroid(roi, params["min_spheroid_area"])
        morph     = measure_morphology(mask, roi, params["pixel_size"])
        _, band   = generate_band(mask, params["band_width"])
        band_int  = measure_band_intensity(roi, band)
        band_sig  = detect_band_signal(roi, band, params["band_thresh_method"],
                                       params["pixel_size"])

        bm = band_int.get("Band_Mean", 999)
        has_debris, debris_score = classify_debris(bm, params["debris_threshold"])

        rows.append({
            "ImageName":       img_path.name,
            "Spheroid_ID":     sid,
            "Grid_Row":        det["row"],
            "Grid_Col":        det["col"],
            "cx_orig_px":      round(cx_full, 1),
            "cy_orig_px":      round(cy_full, 1),
            **morph,
            **band_int,
            **band_sig,
            "HasDebris":       has_debris,
            "DebrisScore":     debris_score,
            "BandWidth_px":    params["band_width"],
            "BandThreshMethod":params["band_thresh_method"],
            "PixelSize_um_px": params["pixel_size"],
        })

        print(f"    [{det['row']},{det['col']}] ID={sid:2d}  "
              f"Area={morph.get('Area_um2','N/A')} µm²  "
              f"Circ={morph.get('Circularity','N/A')}  "
              f"Band_Mean={bm}  "
              f"Debris={'YES' if has_debris else 'no'}")

    df       = pd.DataFrame(rows)
    csv_path = output_dir / f"{img_path.stem}_results.csv"
    df.to_csv(csv_path, index=False)
    print(f"\n    CSV  → {csv_path.name}")

    save_overlay(img_u8, detections, x_start, y_start, x_end, y_end,
                 params["band_width"], params["detect_scale"],
                 output_dir / f"{img_path.stem}_overlay.png", img_path.name)
    print(f"    PNG  → {img_path.stem}_overlay.png")

    return df


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    args       = parse_args()
    input_dir  = Path(args.input)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    params = {
        "pixel_size":         args.pixel_size,
        "n_rows":             args.n_rows,
        "n_cols":             args.n_cols,
        "band_width":         args.band_width,
        "band_thresh_method": args.band_thresh,
        "debris_threshold":   args.debris_threshold,
        "detect_scale":       DEFAULTS["detect_scale"],
        "min_spheroid_area":  DEFAULTS["min_spheroid_area"],
    }

    SUPPORTED = {".tif", ".tiff", ".png", ".jpg", ".jpeg"}
    images    = [f for f in sorted(input_dir.iterdir())
                 if f.suffix.lower() in SUPPORTED]

    if not images:
        raise FileNotFoundError(f"No supported images in: {input_dir}")

    print(f"\nSpheroid Analysis Pipeline")
    print(f"  Input   : {input_dir}")
    print(f"  Output  : {output_dir}")
    print(f"  Images  : {len(images)}")
    print(f"  Scale   : detection 1/{params['detect_scale']} | measurement full resolution")
    print(f"  Debris  : Band_Mean < {params['debris_threshold']}")

    all_results = []
    for img_path in images:
        try:
            df = process_image(img_path, output_dir, params)
            if not df.empty:
                all_results.append(df)
        except Exception as exc:
            import traceback
            print(f"\n  [ERROR] {img_path.name}: {exc}")
            traceback.print_exc()

    if all_results:
        combined      = pd.concat(all_results, ignore_index=True)
        combined_path = output_dir / "ALL_results.csv"
        combined.to_csv(combined_path, index=False)
        print(f"\n{'='*60}")
        print(f"Complete. Total spheroids: {len(combined)}")
        print(f"Debris-positive wells: {combined['HasDebris'].sum()}")
        print(f"Combined CSV: {combined_path}")
        print(f"{'='*60}\n")
        print(combined[["ImageName","Spheroid_ID","Grid_Row","Grid_Col",
                         "Area_um2","Circularity","Band_Mean",
                         "Band_Count","HasDebris"]].to_string(index=False))
    else:
        print("\nNo results produced.")


if __name__ == "__main__":
    main()
