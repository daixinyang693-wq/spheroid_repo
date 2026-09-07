# Algorithm Description

## Pipeline overview

```
Phase 1  Image loading
         RGB → float32 grayscale (Y = 0.299R + 0.587G + 0.114B)

Phase 2  Thumbnail generation
         Downsample × 1/8 for fast localisation

Phase 3  Valid region detection
         Scan row/column means → remove black borders (threshold = 60)

Phase 4  Candidate detection  [on thumbnail]
         Local adaptive threshold (block=51, offset=15)
         Filter: 200 < area < 3000 px²; circularity > 0.4

Phase 5  Grid assignment  [7 × 6]
         Best candidate per cell; empty wells skipped

Phase 6  Coordinate mapping
         thumbnail centroid × 8 → original image

Phase 7  Full-resolution segmentation
         Local adaptive threshold on ROI
         Fallback: global 20th-percentile threshold
         Minimum area: 9,530 px² (= 250 µm diameter at 2.27 µm/px)

Phase 8  Morphology measurement
         Area, perimeter, circularity, aspect ratio, solidity, eccentricity

Phase 9  Band generation
         BinaryDilation(mask, 160 iterations) − mask
         160 px × 2.27 µm/px ≈ 363 µm

Phase 10 Band intensity measurement
         original_image[band_mask]  — never on processed mask

Phase 11 Debris classification
         Band_Mean < 115 → HasDebris = 1
         Sensitivity 100%, Specificity 96% (n = 61 calibration wells)
```

## Key design decisions

**Dual-resolution strategy**  
Detection runs at 1/8 scale (speed). All measurements use the original image (accuracy).

**No forced grid assignment**  
Wells with no candidate are skipped rather than filled with a fallback centroid,
preventing spurious data from empty or ambiguous wells.

**Band intensity on original image**  
`roi[band_mask]` extracts raw pixel values via NumPy boolean indexing.
Measuring on a binary mask would return only 0 and 255, which is meaningless.

**Debris metric selection**  
Band_Mean was selected over Band_Count, Band_Std, and Band_SignalArea_um2
because it showed the largest separation (non-overlapping distributions)
between reference and debris-positive wells in the calibration dataset.
