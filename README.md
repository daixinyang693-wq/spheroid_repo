# Spheroid Analysis Pipeline

Automated quantification of spheroid morphology and perispheroid debris  
in brightfield microplate images.

---

## Overview

| | |
|---|---|
| **Image type** | Brightfield, single-channel (RGB TIFF or JPEG) |
| **Plate layout** | 7 columns × 6 rows (42 wells) |
| **Pixel size** | 2.27 µm/px |
| **Language** | Python 3.10+ |

### Pipeline summary

```
RGB image
  └─ Grayscale conversion (luminance weights)
      └─ Scale=8 thumbnail → black border removal → local threshold detection
          └─ 7×6 grid assignment (empty wells skipped)
              └─ Full-resolution ROI extraction per spheroid
                  ├─ Morphology: area, circularity, aspect ratio, solidity …
                  ├─ Band (160 px ≈ 363 µm): mean intensity on original image
                  └─ Debris: Band_Mean < 115 → HasDebris = 1
```

---

## Installation

```bash
git clone https://github.com/your-username/spheroid-analysis.git
cd spheroid-analysis
pip install -r requirements.txt
```

---

## Usage

### Run analysis

```bash
python src/spheroid_analysis.py \
    --input  /path/to/images \
    --output /path/to/results
```

With custom parameters:

```bash
python src/spheroid_analysis.py \
    --input            /path/to/images \
    --output           /path/to/results \
    --pixel_size       2.27 \
    --n_rows           6 \
    --n_cols           7 \
    --band_width       160 \
    --band_thresh      triangle \
    --debris_threshold 115
```

### Compare reference vs debris

```bash
python src/compare_debris.py \
    --reference results/clean_image_results.csv \
    --debris    results/debris_image_results.csv \
    --output    results/comparison.png \
    --threshold 115
```

---

## Output files

| File | Description |
|---|---|
| `<image>_results.csv` | Per-spheroid measurements (one row per spheroid) |
| `<image>_overlay.png` | Annotated overlay: detection + band regions |
| `ALL_results.csv` | Combined results across all images |
| `comparison.png` | Band_Mean distribution comparison (reference vs debris) |

### CSV columns

| Column | Unit | Description |
|---|---|---|
| `ImageName` | — | Source image filename |
| `Spheroid_ID` | — | Unique ID within image |
| `Grid_Row`, `Grid_Col` | — | Well position in plate grid |
| `Area_um2` | µm² | Spheroid area |
| `Perimeter_um` | µm | Spheroid perimeter |
| `Circularity` | 0–1 | 4π·area/perimeter² |
| `AspectRatio` | — | Major/minor axis ratio |
| `Roundness` | — | 1/AspectRatio |
| `Solidity` | 0–1 | Area/convex hull area |
| `Eccentricity` | 0–1 | Ellipse eccentricity |
| `MeanIntensity` | a.u. | Mean pixel intensity inside spheroid |
| `Band_Mean` | a.u. | Mean intensity in perispheroid band **(key debris metric)** |
| `Band_Std` | a.u. | Intensity standard deviation in band |
| `Band_SignalArea_um2` | µm² | Area of detected signal in band |
| `Band_Count` | — | Number of signal particles in band |
| `HasDebris` | 0/1 | 1 = debris detected |
| `DebrisScore` | a.u. | 115 − Band_Mean (positive = debris) |

---

## Debris classification

Band_Mean (mean pixel intensity within the 363-µm perispheroid band,  
measured on the original grayscale image) was the most discriminative metric  
for debris detection.

| | Reference (n=26) | Debris (n=35) |
|---|---|---|
| Band_Mean (median) | ~148 a.u. | ~82 a.u. |
| Band_Mean (range) | 130–160 | 60–110 |
| Sensitivity | — | **100%** (35/35) |
| Specificity | **96%** (25/26) | — |

Threshold: `Band_Mean < 115` → `HasDebris = 1`

---

## Algorithm parameters

| Parameter | Default | Description |
|---|---|---|
| `--pixel_size` | 2.27 | µm per pixel |
| `--n_rows` | 6 | Plate rows |
| `--n_cols` | 7 | Plate columns |
| `--band_width` | 160 | Band thickness in pixels (≈363 µm) |
| `--band_thresh` | triangle | Auto-threshold for band signal |
| `--debris_threshold` | 115 | Band_Mean cutoff for debris |

---

## Supported image formats

`.tif` `.tiff` `.png` `.jpg` `.jpeg`

---

## Citation

If you use this pipeline in your work, please cite:

```
[your citation here]
```

---

## License

MIT License — see `LICENSE` for details.
