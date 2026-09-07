# Leica SP8 Imaging Parameter Guide

Tkinter desktop tool for supporting Leica SP8 confocal microscopy parameter
selection, batch-to-batch consistency, and live-cell imaging decision making.

## Purpose

This tool is designed as an imaging-parameter checklist and decision aid. It
helps users keep acquisition settings consistent between experimental batches
and makes key trade-offs visible before imaging.

It does not control the microscope directly. Instead, it helps record, compare,
and reason about settings that affect reproducibility, signal quality,
phototoxicity, and multi-channel acquisition.

## Main Use Cases

- Keep imaging parameters consistent between experimental batches.
- Select objective, wavelength, pixel size, and pinhole settings.
- Evaluate detector choice for live-cell or fixed-sample imaging.
- Balance scan speed, line averaging, laser power, and acquisition interval.
- Assess multi-channel spectral crosstalk risk.
- Support reproducible reporting of microscopy acquisition conditions.

## Features

### 1. Objective Selection

Calculates optical reference values from objective NA and wavelength:

- Lateral resolution
- Axial resolution
- Recommended Nyquist pixel size

The tool also provides a target pixel size table across common SP8 objectives
and laser/emission wavelengths.

### 2. Pinhole Guidance

Estimates physical pinhole diameter from:

- Airy Units
- Wavelength
- Objective magnification
- Numerical aperture

It gives practical guidance for standard 1 AU imaging and warns when the
pinhole setting may cause severe signal loss or weak optical sectioning.

### 3. Detector Selection

Compares HyD and PMT detector use cases.

General guidance:

- HyD is preferred for live-cell imaging and weak signal.
- PMT may be useful for strong fixed-sample signals where dynamic range matters.

### 4. Scan Parameter Assessment

Evaluates:

- Scan speed
- Line averaging
- Laser power
- Time-lapse interval

It calculates relative SNR gain compared with a 1000 Hz / 1x averaging
reference condition and highlights phototoxicity-related risks.

### 5. Multi-Channel Crosstalk Assessment

Allows selection of 1-4 fluorophores and estimates qualitative crosstalk risk
from excitation and emission peak separation.

It provides guidance on whether simultaneous or sequential acquisition is more
appropriate.

## Requirements

- Python 3.7+
- Tkinter

Tkinter is included with most standard Python installations. No additional pip
packages are required.

## Run

```bash
python src/sp8_tool_v2_10.py
```

## Recommended Workflow

1. Open the tool before imaging.
2. Select the intended objective, wavelength, format, detector, scan speed,
   laser power, line averaging, and time interval.
3. Use the guidance panels to check phototoxicity and reproducibility risks.
4. Record the final settings in the experiment notebook or batch metadata.
5. Reuse the same settings for later batches when quantitative comparison is
   required.

## Notes

The tool provides decision support based on simplified optical formulas and
qualitative microscopy guidance. Final microscope settings should still be
validated empirically with controls, especially for live-cell imaging and
multi-channel experiments.
