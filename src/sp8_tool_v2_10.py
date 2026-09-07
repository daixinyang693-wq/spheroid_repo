"""
Leica SP8 Confocal Microscopy Parameter Selection Tool
Live cell imaging — five-step workflow
Requires: Python 3.7+ (tkinter included in standard library)

System configuration:
  Objectives: 10x/0.40 DRY, 20x/0.70 DRY, 40x/0.75 DRY, 40x/1.25 OIL, 63x/1.40 OIL
  Formats: as listed in LAS X
  Scan speeds: 10, 100, 200, 400, 700, 1000, 1400 Hz
  Pixel Size, Pixel Dwell Time, Frame Rate, Optical Section: read directly from LAS X
"""

import tkinter as tk
from tkinter import ttk
import math

# ── COLOURS ──────────────────────────────────────────────────────────────────
BG       = "#f5f5f5"
WHITE    = "#ffffff"
CARD_BG  = "#ffffff"
CARD_BD  = "#e0e0e0"
MET_BG   = "#f0f4ff"
TEXT_PRI = "#1a1a1a"
TEXT_SEC = "#555555"
TEXT_MUT = "#888888"
OK_BG    = "#e8f5e9"; OK_FG    = "#2e7d32"
WARN_BG  = "#fff3e0"; WARN_FG  = "#e65100"
BAD_BG   = "#ffebee"; BAD_FG   = "#c62828"
INFO_BG  = "#e8eaff"; INFO_FG  = "#3344aa"
BORDER   = "#dddddd"

# ── DATA ─────────────────────────────────────────────────────────────────────
OBJECTIVES = [
    {"label": "HC PL APO CS  10× / NA 0.40  DRY",      "mag": 10,  "na": 0.40, "imm": "dry"},
    {"label": "HC PL APO CS  20× / NA 0.70  DRY",      "mag": 20,  "na": 0.70, "imm": "dry"},
    {"label": "HCX APO U-V-I 40× / NA 0.75  DRY",      "mag": 40,  "na": 0.75, "imm": "dry"},
    {"label": "HCX PL APO CS 40× / NA 1.25  OIL PH3",  "mag": 40,  "na": 1.25, "imm": "oil"},
    {"label": "HCX PL APO CS 63× / NA 1.40  OIL",      "mag": 63,  "na": 1.40, "imm": "oil"},
]

WAVELENGTHS = [
    {"label": "405 nm  (DAPI / BFP)",      "nm": 405},
    {"label": "488 nm  (GFP / Alexa 488)", "nm": 488},
    {"label": "514 nm  (YFP)",             "nm": 514},
    {"label": "561 nm  (mCherry / TRITC)", "nm": 561},
    {"label": "633 nm  (Cy5 / AF647)",     "nm": 633},
]

FORMATS = [
    "16 × 16", "64 × 64", "128 × 128", "256 × 256",
    "512 × 32", "512 × 64", "512 × 512",
    "1024 × 256", "1024 × 512", "1024 × 1024",
    "2048 × 2048", "4096 × 4096", "8192 × 8192",
]

SCAN_SPEEDS = [10, 100, 200, 400, 700, 1000, 1400]  # Hz

FLUORS = [
    {"name": "DAPI",         "ex": 405, "em": 461},
    {"name": "BFP",          "ex": 405, "em": 440},
    {"name": "mTurquoise2",  "ex": 434, "em": 474},
    {"name": "GFP",          "ex": 488, "em": 507},
    {"name": "Alexa 488",    "ex": 488, "em": 519},
    {"name": "YFP",          "ex": 514, "em": 527},
    {"name": "mVenus",       "ex": 514, "em": 528},
    {"name": "TRITC",        "ex": 561, "em": 572},
    {"name": "TagRFP",       "ex": 555, "em": 584},
    {"name": "mCherry",      "ex": 561, "em": 610},
    {"name": "Cy5 / AF647",  "ex": 633, "em": 668},
    {"name": "Alexa 647",    "ex": 633, "em": 668},
]
FLUOR_NAMES = [f["name"] for f in FLUORS]

# ── REUSABLE WIDGETS ─────────────────────────────────────────────────────────
class Card(tk.Frame):
    def __init__(self, parent, border_color=CARD_BD, **kw):
        super().__init__(parent, bg=CARD_BG, bd=0,
                         highlightthickness=1, highlightbackground=border_color, **kw)

class MetricCard(tk.Frame):
    def __init__(self, parent, label, **kw):
        super().__init__(parent, bg=MET_BG, bd=0, padx=12, pady=10, **kw)
        tk.Label(self, text=label, bg=MET_BG, fg=TEXT_MUT,
                 font=("Arial", 9)).pack(anchor="w")
        self._val = tk.Label(self, text="—", bg=MET_BG, fg=TEXT_PRI,
                             font=("Arial", 15, "bold"))
        self._val.pack(anchor="w")
    def set(self, text):
        self._val.config(text=text)

class RRow(tk.Frame):
    """Label + right-aligned value with a hairline separator below."""
    def __init__(self, parent, label, **kw):
        super().__init__(parent, bg=CARD_BG, **kw)
        tk.Label(self, text=label, bg=CARD_BG, fg=TEXT_SEC,
                 font=("Arial", 10), anchor="w").pack(side="left")
        self._v = tk.Label(self, text="—", bg=CARD_BG, fg=TEXT_PRI,
                           font=("Arial", 10, "bold"), anchor="e")
        self._v.pack(side="right")
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x", side="bottom")
    def set(self, text, color=TEXT_PRI):
        self._v.config(text=text, fg=color)

class SecTitle(tk.Label):
    def __init__(self, parent, text, **kw):
        super().__init__(parent, text=text.upper(), bg=BG, fg=TEXT_MUT,
                         font=("Arial", 9, "bold"), **kw)

class Tip(tk.Label):
    def __init__(self, parent, wrap=580, **kw):
        super().__init__(parent, bg=CARD_BG, fg=TEXT_SEC,
                         font=("Arial", 10), wraplength=wrap,
                         justify="left", anchor="w", **kw)

class Badge(tk.Label):
    def __init__(self, parent, **kw):
        super().__init__(parent, font=("Arial", 9, "bold"), padx=6, pady=2, **kw)
    def ok(self, t):   self.config(text=t, bg=OK_BG,   fg=OK_FG)
    def warn(self, t): self.config(text=t, bg=WARN_BG,  fg=WARN_FG)
    def bad(self, t):  self.config(text=t, bg=BAD_BG,   fg=BAD_FG)
    def info(self, t): self.config(text=t, bg=INFO_BG,  fg=INFO_FG)


# ── MAIN APP ─────────────────────────────────────────────────────────────────
class SP8Tool(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Leica SP8 — Imaging Parameter Guide")
        self.geometry("700x860")
        self.configure(bg=BG)
        self.resizable(True, True)
        self._build_header()
        self._build_nav()
        self._build_panels()
        self._show(0)
        self.calc_obj()
        self.calc_scan()
        self.build_channels()

    # ── HEADER ───────────────────────────────────────────────────────────────
    def _build_header(self):
        f = tk.Frame(self, bg=BG)
        f.pack(fill="x", padx=20, pady=(18, 0))
        tk.Label(f, text="Leica SP8 — Confocal Imaging Parameter Guide",
                 bg=BG, fg=TEXT_PRI, font=("Arial", 15, "bold")).pack(anchor="w")
        tk.Label(f, text="Live cell imaging · Five-step workflow",
                 bg=BG, fg=TEXT_MUT, font=("Arial", 10)).pack(anchor="w")

    # ── NAV ──────────────────────────────────────────────────────────────────
    def _build_nav(self):
        nav = tk.Frame(self, bg=WHITE, bd=0,
                       highlightthickness=1, highlightbackground=BORDER)
        nav.pack(fill="x", padx=20, pady=12)
        labels = ["01  Objective", "02  Pinhole", "03  Detector",
                  "04  Scan params", "05  Multi-channel"]
        self._nav_btns = []
        for i, lbl in enumerate(labels):
            b = tk.Button(nav, text=lbl, font=("Arial", 10), bd=0,
                          padx=6, pady=8, cursor="hand2",
                          command=lambda i=i: self._show(i))
            b.grid(row=0, column=i, sticky="nsew")
            nav.columnconfigure(i, weight=1)
            self._nav_btns.append(b)
        self._cur = 0

    def _show(self, idx):
        self._cur = idx
        for i, b in enumerate(self._nav_btns):
            if i == idx:
                b.config(bg=MET_BG, fg=TEXT_PRI, font=("Arial", 10, "bold"))
            else:
                b.config(bg=WHITE, fg=TEXT_MUT, font=("Arial", 10))
        for i, p in enumerate(self._panels):
            if i == idx:
                p.pack(fill="both", expand=True, padx=20, pady=(0, 20))
                if i == 1: self.calc_pinhole()
                if i == 2: self.calc_det()
                if i == 3: self.calc_scan()
                if i == 4: self.build_channels()
            else:
                p.pack_forget()

    # ── SCROLL WRAPPER ───────────────────────────────────────────────────────
    def _make_scroll(self):
        outer = tk.Frame(self, bg=BG)
        canvas = tk.Canvas(outer, bg=BG, bd=0, highlightthickness=0)
        sb = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        inner = tk.Frame(canvas, bg=BG)
        win = canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda e: canvas.configure(
            scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(win, width=e.width))
        canvas.bind_all("<MouseWheel>",
                        lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
        return outer, inner

    # ── ALL PANELS ───────────────────────────────────────────────────────────
    def _build_panels(self):
        self._panels = []
        for build in [self._p0, self._p1, self._p2, self._p3, self._p4]:
            outer, inner = self._make_scroll()
            build(inner)
            self._panels.append(outer)

    # ════════════════════════════════════════════════════════════════════════
    # STEP 1 — OBJECTIVE
    # ════════════════════════════════════════════════════════════════════════
    def _p0(self, f):
        SecTitle(f, "Objective lens selection").pack(anchor="w", pady=(8, 6))

        row = tk.Frame(f, bg=BG)
        row.pack(fill="x", pady=(0, 8))
        row.columnconfigure(0, weight=1); row.columnconfigure(1, weight=1)

        # Feature size slider
        lf = tk.Frame(row, bg=BG)
        lf.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        tk.Label(lf, text="Cell / feature size (µm)", bg=BG, fg=TEXT_SEC,
                 font=("Arial", 10)).pack(anchor="w")
        sr = tk.Frame(lf, bg=BG); sr.pack(fill="x")
        self.feat = tk.DoubleVar(value=15)
        tk.Scale(sr, from_=0.5, to=100, resolution=0.5, variable=self.feat,
                 orient="horizontal", bg=BG, highlightthickness=0,
                 troughcolor=MET_BG, showvalue=False,
                 command=lambda e: self.calc_obj()).pack(side="left", fill="x", expand=True)
        self._feat_lbl = tk.Label(sr, text="15.0 µm", bg=BG, fg=TEXT_PRI,
                                  font=("Arial", 10, "bold"), width=9)
        self._feat_lbl.pack(side="right")

        # Wavelength
        rf = tk.Frame(row, bg=BG)
        rf.grid(row=0, column=1, sticky="ew", padx=(6, 0))
        tk.Label(rf, text="Emission wavelength", bg=BG, fg=TEXT_SEC,
                 font=("Arial", 10)).pack(anchor="w")
        self.wl_var = tk.StringVar(value=WAVELENGTHS[0]["label"])
        cb = ttk.Combobox(rf, textvariable=self.wl_var, state="readonly",
                          values=[w["label"] for w in WAVELENGTHS], font=("Arial", 10))
        cb.pack(fill="x")
        cb.bind("<<ComboboxSelected>>", lambda e: self.calc_obj())

        # Objective
        tk.Label(f, text="Objective lens", bg=BG, fg=TEXT_SEC,
                 font=("Arial", 10)).pack(anchor="w", pady=(4, 2))
        self.obj_var = tk.StringVar(value=OBJECTIVES[4]["label"])
        cb2 = ttk.Combobox(f, textvariable=self.obj_var, state="readonly",
                            values=[o["label"] for o in OBJECTIVES], font=("Arial", 10))
        cb2.pack(fill="x")
        cb2.bind("<<ComboboxSelected>>", lambda e: self.calc_obj())

        # Format selector
        tk.Label(f, text="Image format  (record for reproducibility)", bg=BG,
                 fg=TEXT_SEC, font=("Arial", 10)).pack(anchor="w", pady=(4, 2))
        self.fmt = tk.StringVar(value="512 × 512")
        cb3 = ttk.Combobox(f, textvariable=self.fmt, state="readonly",
                            values=FORMATS, font=("Arial", 10))
        cb3.pack(fill="x")

        # Metrics — only optically derived values
        mg = tk.Frame(f, bg=BG); mg.pack(fill="x", pady=(12, 4))
        for i in range(3): mg.columnconfigure(i, weight=1)
        self.m_resxy = MetricCard(mg, "Lateral resolution  d_xy = 0.37λ/NA")
        self.m_resz  = MetricCard(mg, "Axial resolution  d_z = 1.77λn/NA²")
        self.m_recpx = MetricCard(mg, "Target pixel size  p = d_xy / 2.5  (Nyquist)")
        for i, m in enumerate([self.m_resxy, self.m_resz, self.m_recpx]):
            m.grid(row=0, column=i, padx=4, pady=4, sticky="nsew")

        # Pixel size table for all objectives
        tk.Frame(f, bg=BORDER, height=1).pack(fill="x", pady=(8, 4))
        tk.Label(f, text="TARGET PIXEL SIZE BY OBJECTIVE & WAVELENGTH  —  adjust Format and Zoom Factor in LAS X until Pixel Size reads this value",
                 bg=BG, fg=TEXT_MUT, font=("Arial", 9, "bold")).pack(anchor="w", pady=(0, 4))
        self._px_table = tk.Frame(f, bg=BG)
        self._px_table.pack(fill="x", pady=(0, 8))
        self._build_px_table()

        # Immersion note
        card = Card(f); card.pack(fill="x", pady=4)
        self._obj_tip = Tip(card)
        self._obj_tip.pack(padx=10, pady=10, fill="x")

    def _build_px_table(self):
        for w in self._px_table.winfo_children():
            w.destroy()
        hdrs = ["Objective", "NA"] + [f"{wl['nm']} nm" for wl in WAVELENGTHS]
        cols = len(hdrs)
        for c in range(cols):
            self._px_table.columnconfigure(c, weight=1)
        for c, h in enumerate(hdrs):
            tk.Label(self._px_table, text=h, bg=MET_BG, fg=TEXT_MUT,
                     font=("Arial", 9, "bold"), relief="flat",
                     padx=6, pady=4).grid(row=0, column=c, sticky="nsew", padx=1, pady=1)
        for r, obj in enumerate(OBJECTIVES, start=1):
            short = obj["label"].split("  ")[0].replace("HC PL APO CS ", "").replace("HCX PL APO CS ", "").replace("HCX APO U-V-I ", "")
            tk.Label(self._px_table, text=short, bg=WHITE, fg=TEXT_PRI,
                     font=("Arial", 9), padx=6, pady=3, anchor="w").grid(
                         row=r, column=0, sticky="nsew", padx=1, pady=1)
            tk.Label(self._px_table, text=str(obj["na"]), bg=WHITE, fg=TEXT_SEC,
                     font=("Arial", 9), padx=6, pady=3).grid(
                         row=r, column=1, sticky="nsew", padx=1, pady=1)
            for c, wl in enumerate(WAVELENGTHS, start=2):
                dxy = 0.37 * wl["nm"] / obj["na"]
                px  = dxy / 2.5
                tk.Label(self._px_table, text=f"{px:.0f} nm", bg=WHITE, fg=TEXT_PRI,
                         font=("Arial", 9, "bold"), padx=6, pady=3).grid(
                             row=r, column=c, sticky="nsew", padx=1, pady=1)

    def calc_obj(self):
        feat = self.feat.get()
        self._feat_lbl.config(text=f"{feat:.1f} µm")
        wl_idx = [w["label"] for w in WAVELENGTHS].index(self.wl_var.get())
        wl_nm  = WAVELENGTHS[wl_idx]["nm"]
        wl     = wl_nm / 1000  # µm
        obj_idx = [o["label"] for o in OBJECTIVES].index(self.obj_var.get())
        obj = OBJECTIVES[obj_idx]
        na, imm = obj["na"], obj["imm"]
        n = 1.515 if imm == "oil" else 1.0

        dxy  = 0.37 * wl / na
        dz   = 1.77 * wl * n / na**2
        recpx = dxy / 2.5

        self.m_resxy.set(f"{dxy*1000:.0f} nm")
        self.m_resz.set(f"{dz*1000:.0f} nm")
        self.m_recpx.set(f"{recpx*1000:.0f} nm  →  adjust via Format & Zoom")

        tips = []
        if imm == "dry" and na >= 0.70:
            tips.append("Dry objective with NA ≥ 0.70: refractive index mismatch between "
                        "air and aqueous medium introduces spherical aberration that degrades "
                        "resolution and SNR at depth. Consider water- or oil-immersion objective "
                        "for live cell imaging (Diel et al., Nat Protoc 2020).")
        px_across = feat / recpx  # both in µm
        tips = []
        if imm == "dry" and na >= 0.70:
            tips.append("Dry objective with NA ≥ 0.70: refractive index mismatch between "
                        "air and aqueous medium introduces spherical aberration that degrades "
                        "resolution and SNR at depth. Consider water- or oil-immersion objective "
                        "for live cell imaging (Diel et al., Nat Protoc 2020).")
        if not tips:
            tips.append(f"d_xy = 0.37 × {wl_nm} / {na} = {dxy*1000:.0f} nm.  "
                        f"d_z = 1.77 × {wl_nm} × {n} / {na}² = {dz*1000:.0f} nm.  "
                        f"Target pixel size = {dxy*1000:.0f} / 2.5 = {recpx*1000:.0f} nm.  "
                        f"Adjust Format and Zoom Factor in LAS X until Pixel Size reads ~{recpx*1000:.0f} nm.")
        self._obj_tip.config(text="  ".join(tips))

    # ════════════════════════════════════════════════════════════════════════
    # STEP 2 — PINHOLE
    # ════════════════════════════════════════════════════════════════════════
    def _p1(self, f):
        SecTitle(f, "Pinhole setting").pack(anchor="w", pady=(8, 6))

        row = tk.Frame(f, bg=BG); row.pack(fill="x", pady=(0, 8))
        row.columnconfigure(0, weight=1); row.columnconfigure(1, weight=1)

        lf = tk.Frame(row, bg=BG)
        lf.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        tk.Label(lf, text="Pinhole size (Airy Units)", bg=BG, fg=TEXT_SEC,
                 font=("Arial", 10)).pack(anchor="w")
        sr = tk.Frame(lf, bg=BG); sr.pack(fill="x")
        self.au = tk.DoubleVar(value=1.0)
        tk.Scale(sr, from_=0.5, to=3.0, resolution=0.1, variable=self.au,
                 orient="horizontal", bg=BG, highlightthickness=0,
                 troughcolor=MET_BG, showvalue=False,
                 command=lambda e: self.calc_pinhole()).pack(
                     side="left", fill="x", expand=True)
        self._au_lbl = tk.Label(sr, text="1.0 AU", bg=BG, fg=TEXT_PRI,
                                font=("Arial", 10, "bold"), width=8)
        self._au_lbl.pack(side="right")

        rf = tk.Frame(row, bg=BG)
        rf.grid(row=0, column=1, sticky="ew", padx=(6, 0))
        tk.Label(rf, text="Optical Section thickness", bg=BG, fg=TEXT_SEC,
                 font=("Arial", 10)).pack(anchor="w")
        tk.Label(rf, text="Read directly from LAS X › Optical Section",
                 bg=BG, fg=TEXT_MUT, font=("Arial", 10), wraplength=260,
                 justify="left").pack(anchor="w", pady=(4, 0))

        # Metrics — only pinhole diameter (physical); FWHM read from LAS X
        mg = tk.Frame(f, bg=BG); mg.pack(fill="x", pady=(0, 8))
        mg.columnconfigure(0, weight=1); mg.columnconfigure(1, weight=1)
        self.m_phum  = MetricCard(mg, "Physical pinhole diameter  d = 1.22λ·M/NA · AU")
        self.m_phau  = MetricCard(mg, "Setting in LAS X")
        self.m_phum.grid(row=0, column=0, padx=4, pady=4, sticky="nsew")
        self.m_phau.grid(row=0, column=1, padx=4, pady=4, sticky="nsew")

        card = Card(f); card.pack(fill="x", pady=4)
        self._ph_status = RRow(card, "Pinhole status")
        self._ph_status.pack(fill="x", padx=10, pady=(8, 0))
        self._ph_bg     = RRow(card, "Background rejection")
        self._ph_bg.pack(fill="x", padx=10)
        self._ph_use    = RRow(card, "Recommended use")
        self._ph_use.pack(fill="x", padx=10, pady=(0, 8))

        tk.Label(f,
                 text=("Formula: 1 AU = 1.22 λ × M_obj / NA  (physical diameter at pinhole plane).  "
                       "Optical section thickness (FWHM) is displayed directly in LAS X — "
                       "read from the Optical Section field after setting AU.  "
                       "Reference: Pawley (2006), Chapter 8; Wilson (1990)."),
                 bg=BG, fg=TEXT_MUT, font=("Arial", 9), wraplength=580,
                 justify="left").pack(anchor="w", pady=6)

    def calc_pinhole(self):
        au = self.au.get()
        self._au_lbl.config(text=f"{au:.1f} AU")
        wl_idx  = [w["label"] for w in WAVELENGTHS].index(self.wl_var.get())
        wl_nm   = WAVELENGTHS[wl_idx]["nm"]
        obj_idx = [o["label"] for o in OBJECTIVES].index(self.obj_var.get())
        obj = OBJECTIVES[obj_idx]
        ph_um = 1.22 * wl_nm * obj["mag"] / obj["na"] * au
        self.m_phum.set(f"{ph_um:.0f} µm")
        self.m_phau.set(f"Pinhole = {au:.1f} AU")

        if au < 0.7:
            s, bg, use, col = ("< 1 AU", "Maximum", "Not recommended for live cell — severe signal loss", WARN_FG)
        elif au <= 1.1:
            s, bg, use, col = ("1 AU  ✓  standard", "Optimal",
                               "Standard for live cell imaging (Pawley, 2006)", OK_FG)
        elif au <= 1.5:
            s, bg, use, col = ("1.0–1.5 AU", "Good",
                               "Acceptable for weak-signal specimens; marginal axial resolution loss", INFO_FG)
        elif au <= 2.0:
            s, bg, use, col = ("1.5–2.0 AU", "Moderate",
                               "Increased background; use only if signal is very weak", WARN_FG)
        else:
            s, bg, use, col = ("> 2 AU", "Poor",
                               "Approaches wide-field; confocal optical sectioning largely lost", BAD_FG)

        self._ph_status.set(s, col)
        self._ph_bg.set(bg)
        self._ph_use.set(use)

    # ════════════════════════════════════════════════════════════════════════
    # STEP 3 — DETECTOR
    # ════════════════════════════════════════════════════════════════════════
    def _p2(self, f):
        SecTitle(f, "Detector selection").pack(anchor="w", pady=(8, 6))

        row = tk.Frame(f, bg=BG); row.pack(fill="x", pady=(0, 8))
        row.columnconfigure(0, weight=1); row.columnconfigure(1, weight=1)

        lf = tk.Frame(row, bg=BG)
        lf.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        tk.Label(lf, text="Signal intensity", bg=BG, fg=TEXT_SEC,
                 font=("Arial", 10)).pack(anchor="w")
        self.sig = tk.StringVar(value="mid")
        for v, t in [("low",  "Weak  (low-expression / sparse labelling)"),
                     ("mid",  "Moderate  (standard fluorescent protein)"),
                     ("high", "Strong  (high expression / fixed sample)")]:
            tk.Radiobutton(lf, text=t, variable=self.sig, value=v,
                           bg=BG, fg=TEXT_SEC, font=("Arial", 10),
                           command=self.calc_det).pack(anchor="w")

        rf = tk.Frame(row, bg=BG)
        rf.grid(row=0, column=1, sticky="ew", padx=(6, 0))
        tk.Label(rf, text="Experiment type", bg=BG, fg=TEXT_SEC,
                 font=("Arial", 10)).pack(anchor="w")
        self.exp = tk.StringVar(value="live")
        for v, t in [("live",  "Live cell imaging"),
                     ("fixed", "Fixed sample")]:
            tk.Radiobutton(rf, text=t, variable=self.exp, value=v,
                           bg=BG, fg=TEXT_SEC, font=("Arial", 10),
                           command=self.calc_det).pack(anchor="w")

        # SNR formula — displayed for reference, not calculated
        fc = Card(f, border_color="#c8d0ff"); fc.pack(fill="x", pady=(4, 8))
        tk.Label(fc, text="SNR = (S · QE) / √(S · QE + B · QE + σ_d²)",
                 bg=CARD_BG, fg=TEXT_PRI, font=("Courier", 11)).pack(
                     anchor="w", padx=10, pady=(8, 2))
        tk.Label(fc, text=("S = signal photons per pixel,  B = background photons per pixel,  "
                           "QE = quantum efficiency,  σ_d = dark noise (e⁻ RMS).  "
                           "Formula displayed for reference; S and B are read from your images "
                           "(Pawley, 2006; Art, 2006)."),
                 bg=CARD_BG, fg=TEXT_MUT, font=("Arial", 9),
                 wraplength=560, justify="left").pack(anchor="w", padx=10, pady=(0, 8))

        dr = tk.Frame(f, bg=BG); dr.pack(fill="x", pady=4)
        dr.columnconfigure(0, weight=1); dr.columnconfigure(1, weight=1)

        self._hyd_card = Card(dr)
        self._hyd_card.grid(row=0, column=0, padx=(0, 4), sticky="nsew")
        tk.Label(self._hyd_card, text="HyD  (hybrid detector)", bg=CARD_BG,
                 fg=TEXT_PRI, font=("Arial", 11, "bold")).pack(anchor="w", padx=10, pady=(8, 4))
        for lbl, val in [("Peak QE",       "~45%  @ 488–561 nm"),
                         ("Dark current",  "< 0.1 cps"),
                         ("Dynamic range", "Moderate"),
                         ("Noise regime",  "Shot-noise limited  (F ≈ 1)")]:
            r = tk.Frame(self._hyd_card, bg=CARD_BG); r.pack(fill="x", padx=10)
            tk.Label(r, text=lbl, bg=CARD_BG, fg=TEXT_SEC, font=("Arial", 10)).pack(side="left")
            tk.Label(r, text=val, bg=CARD_BG, fg=TEXT_PRI,
                     font=("Arial", 10, "bold")).pack(side="right")
            tk.Frame(r, bg=BORDER, height=1).pack(fill="x", side="bottom")
        tk.Label(self._hyd_card, text="Source: Leica Microsystems (2019)",
                 bg=CARD_BG, fg=TEXT_MUT, font=("Arial", 8)).pack(anchor="w", padx=10)
        self._hyd_tip = Tip(self._hyd_card)
        self._hyd_tip.pack(padx=10, pady=(4, 10), fill="x")

        self._pmt_card = Card(dr)
        self._pmt_card.grid(row=0, column=1, padx=(4, 0), sticky="nsew")
        tk.Label(self._pmt_card, text="PMT  (photomultiplier)", bg=CARD_BG,
                 fg=TEXT_PRI, font=("Arial", 11, "bold")).pack(anchor="w", padx=10, pady=(8, 4))
        for lbl, val in [("Peak QE",       "~20–25%"),
                         ("Dark current",  "Low"),
                         ("Dynamic range", "Wide"),
                         ("Noise regime",  "Multiplicative noise  (F > 1)")]:
            r = tk.Frame(self._pmt_card, bg=CARD_BG); r.pack(fill="x", padx=10)
            tk.Label(r, text=lbl, bg=CARD_BG, fg=TEXT_SEC, font=("Arial", 10)).pack(side="left")
            tk.Label(r, text=val, bg=CARD_BG, fg=TEXT_PRI,
                     font=("Arial", 10, "bold")).pack(side="right")
            tk.Frame(r, bg=BORDER, height=1).pack(fill="x", side="bottom")
        tk.Label(self._pmt_card, text="Source: Leica Microsystems (2019)",
                 bg=CARD_BG, fg=TEXT_MUT, font=("Arial", 8)).pack(anchor="w", padx=10)
        self._pmt_tip = Tip(self._pmt_card)
        self._pmt_tip.pack(padx=10, pady=(4, 10), fill="x")

        rc = Card(f, border_color="#6677cc"); rc.pack(fill="x", pady=4)
        hr = tk.Frame(rc, bg=CARD_BG); hr.pack(fill="x", padx=10, pady=(8, 4))
        tk.Label(hr, text="Recommendation", bg=CARD_BG, fg=TEXT_PRI,
                 font=("Arial", 11, "bold")).pack(side="left")
        self._det_badge = Badge(rc, bg=INFO_BG, fg=INFO_FG)
        self._det_badge.pack(anchor="w", padx=10)
        self._det_tip = Tip(rc)
        self._det_tip.pack(padx=10, pady=(4, 10), fill="x")

    def calc_det(self):
        sig = self.sig.get()
        exp = self.exp.get()

        hyd_rec = exp == "live" or sig == "low"
        pmt_rec = sig == "high" and exp == "fixed"
        self._hyd_card.config(highlightbackground=OK_FG if hyd_rec else CARD_BD)
        self._pmt_card.config(highlightbackground=OK_FG if pmt_rec else CARD_BD)

        hyd_tips = {
            "live":  ("Higher QE (~45% vs ~20–25%) means equivalent SNR is achievable "
                      "at lower laser power, reducing phototoxic insult. "
                      "Near-zero dark current (<0.1 cps) is advantageous for weak live-cell signals. "
                      "(Icha et al., BioEssays 2017; Leica Microsystems, 2019)"),
            "fixed": ("Suitable for weak-to-moderate fixed samples. "
                      "Higher QE than PMT allows lower laser power for equivalent SNR. "
                      "(Leica Microsystems, 2019)"),
        }
        pmt_tips = {
            "live":  ("Lower QE (~20–25%) requires higher laser power for equivalent SNR, "
                      "increasing phototoxic risk (Icha et al., BioEssays 2017). "
                      "Use only when signal is strong enough that HyD gain would saturate."),
            "fixed": ("Wide dynamic range suits bright immunostained fixed samples where "
                      "HyD may saturate. (Leica Microsystems, 2019)"),
        }
        rec = {
            "live":  ("Use HyD. Higher QE (~45%) allows equivalent SNR at lower laser power, "
                      "directly reducing phototoxicity. SNR ≈ √(S · QE): higher QE means "
                      "fewer photons — and less laser power — needed for the same SNR "
                      "(Icha et al., BioEssays 2017; Pawley, 2006)."),
            "fixed": ("Weak-to-moderate signal: use HyD (higher QE, better SNR at low laser). "
                      "Strong signal: use PMT (wider dynamic range, avoids HyD saturation). "
                      "Record detector type, gain, and laser power; hold constant across sessions "
                      "for quantitative comparisons (Waters, J Cell Biol 2009)."),
        }
        badges = {"live": "HyD preferred", "fixed": "Signal-dependent"}

        self._hyd_tip.config(text=hyd_tips[exp])
        self._pmt_tip.config(text=pmt_tips[exp])
        self._det_tip.config(text=rec[exp])
        self._det_badge.info(badges[exp])

    # ════════════════════════════════════════════════════════════════════════
    # STEP 4 — SCAN PARAMETERS
    # ════════════════════════════════════════════════════════════════════════
    def _p3(self, f):
        SecTitle(f, "Scanning parameters").pack(anchor="w", pady=(8, 6))

        # LAS X read-directly notice
        notice = Card(f, border_color="#c8d0ff"); notice.pack(fill="x", pady=(0, 10))
        tk.Label(notice,
                 text=("Pixel Dwell Time and Frame Rate are displayed directly in LAS X — "
                       "read and record those values. "
                       "This panel calculates only the relative SNR gain between parameter combinations, "
                       "and provides evidence-based guidance on scan speed vs line averaging trade-offs."),
                 bg=CARD_BG, fg=TEXT_SEC, font=("Arial", 10),
                 wraplength=560, justify="left").pack(padx=10, pady=8)

        row = tk.Frame(f, bg=BG); row.pack(fill="x", pady=(0, 8))
        row.columnconfigure(0, weight=1); row.columnconfigure(1, weight=1)

        # Scan speed
        lf = tk.Frame(row, bg=BG)
        lf.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        tk.Label(lf, text="Scan speed (Hz)", bg=BG, fg=TEXT_SEC,
                 font=("Arial", 10)).pack(anchor="w")
        self.spd = tk.StringVar(value="400")
        cb = ttk.Combobox(lf, textvariable=self.spd, state="readonly",
                          values=[str(s) for s in SCAN_SPEEDS], font=("Arial", 10))
        cb.pack(fill="x")
        cb.bind("<<ComboboxSelected>>", lambda e: self.calc_scan())

        # Line average
        rf = tk.Frame(row, bg=BG)
        rf.grid(row=0, column=1, sticky="ew", padx=(6, 0))
        tk.Label(rf, text="Line averaging", bg=BG, fg=TEXT_SEC,
                 font=("Arial", 10)).pack(anchor="w")
        self.avg = tk.StringVar(value="1")
        cb2 = ttk.Combobox(rf, textvariable=self.avg, state="readonly",
                            values=["1", "2", "4", "8", "16"], font=("Arial", 10))
        cb2.pack(fill="x")
        cb2.bind("<<ComboboxSelected>>", lambda e: self.calc_scan())

        row2 = tk.Frame(f, bg=BG); row2.pack(fill="x", pady=(0, 8))
        row2.columnconfigure(0, weight=1); row2.columnconfigure(1, weight=1)

        # Laser power
        lf2 = tk.Frame(row2, bg=BG)
        lf2.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        tk.Label(lf2, text="Laser power (% of maximum)", bg=BG, fg=TEXT_SEC,
                 font=("Arial", 10)).pack(anchor="w")
        sr = tk.Frame(lf2, bg=BG); sr.pack(fill="x")
        self.laser = tk.DoubleVar(value=2.0)
        tk.Scale(sr, from_=0.1, to=20, resolution=0.1, variable=self.laser,
                 orient="horizontal", bg=BG, highlightthickness=0,
                 troughcolor=MET_BG, showvalue=False,
                 command=lambda e: self.calc_scan()).pack(
                     side="left", fill="x", expand=True)
        self._laser_lbl = tk.Label(sr, text="2.0 %", bg=BG, fg=TEXT_PRI,
                                   font=("Arial", 10, "bold"), width=8)
        self._laser_lbl.pack(side="right")

        # Interval
        rf2 = tk.Frame(row2, bg=BG)
        rf2.grid(row=0, column=1, sticky="ew", padx=(6, 0))
        tk.Label(rf2, text="Time-lapse interval (minutes)", bg=BG, fg=TEXT_SEC,
                 font=("Arial", 10)).pack(anchor="w")
        sr2 = tk.Frame(rf2, bg=BG); sr2.pack(fill="x")
        self.intv = tk.DoubleVar(value=5.0)
        tk.Scale(sr2, from_=0.5, to=60, resolution=0.5, variable=self.intv,
                 orient="horizontal", bg=BG, highlightthickness=0,
                 troughcolor=MET_BG, showvalue=False,
                 command=lambda e: self.calc_scan()).pack(
                     side="left", fill="x", expand=True)
        self._intv_lbl = tk.Label(sr2, text="5.0 min", bg=BG, fg=TEXT_PRI,
                                  font=("Arial", 10, "bold"), width=8)
        self._intv_lbl.pack(side="right")

        # SNR relative gain — only calculated metric
        mg = tk.Frame(f, bg=BG); mg.pack(fill="x", pady=(12, 4))
        mg.columnconfigure(0, weight=1); mg.columnconfigure(1, weight=1)
        self.m_snr = MetricCard(mg, "Relative SNR gain  √(avg / f_ref × 1000)  vs 1000 Hz / 1×")
        self.m_snr.grid(row=0, column=0, padx=4, pady=4, sticky="nsew")
        self.m_snreq = MetricCard(mg, "Equivalent single-speed alternative")
        self.m_snreq.grid(row=0, column=1, padx=4, pady=4, sticky="nsew")

        # Phototoxicity principles
        tk.Frame(f, bg=BORDER, height=1).pack(fill="x", pady=8)
        SecTitle(f, "Phototoxicity — evidence-based guiding principles").pack(
            anchor="w", pady=(0, 6))

        principles = [
            ("⚡  Laser power",
             "Minimise laser power. Phototoxicity increases non-linearly with irradiance "
             "through two-photon absorption and Type I/II photochemical reactions at high "
             "irradiances. Short-wavelength lasers (e.g. 405 nm) carry higher photon energy "
             "(E = hc/λ) and are disproportionately phototoxic.",
             "Icha et al., BioEssays 2017; Tauer, Exp Physiol 2002",
             "badge_laser"),
            ("🔄  Scan speed vs line averaging",
             "To improve SNR, prefer reducing scan speed (increasing pixel dwell time) "
             "over increasing line averaging. Both approaches improve SNR by √n, but line "
             "averaging re-exposes the same line n times in rapid succession, producing "
             "higher instantaneous photon flux at the same location.",
             "Frigault et al., J Cell Sci 2009",
             "badge_avg"),
            ("⏱  Acquisition interval",
             "Set the acquisition interval to the minimum required by the biological "
             "process, not shorter. The temporal Nyquist criterion requires Δt ≤ 1/(2k), "
             "where k is the characteristic rate constant (s⁻¹) of the process. "
             "Unnecessary oversampling in time increases cumulative photon dose without "
             "adding biological information.",
             "Shannon, Proc IRE 1949; Frigault et al., J Cell Sci 2009",
             "badge_intv"),
            ("🔬  Viability validation",
             "Phototoxicity thresholds depend on cell type, fluorophore, and culture "
             "conditions and cannot be determined from acquisition parameters alone. "
             "Include a non-illuminated control group in each experiment. Compare "
             "proliferation rate, morphology, and division behaviour against unirradiated "
             "controls. Membrane blebbing, contraction, or arrest of division indicate "
             "phototoxic damage.",
             "Frigault et al., J Cell Sci 2009; Icha et al., BioEssays 2017",
             None),
        ]

        self._pbadges = {}
        for title, desc, ref, battr in principles:
            c = Card(f); c.pack(fill="x", pady=3)
            top = tk.Frame(c, bg=CARD_BG); top.pack(fill="x", padx=10, pady=(8, 2))
            tk.Label(top, text=title, bg=CARD_BG, fg=TEXT_PRI,
                     font=("Arial", 10, "bold")).pack(side="left")
            if battr:
                b = Badge(top, bg=OK_BG, fg=OK_FG); b.pack(side="left", padx=6)
                self._pbadges[battr] = b
            tk.Label(c, text=desc, bg=CARD_BG, fg=TEXT_SEC, font=("Arial", 10),
                     wraplength=560, justify="left", anchor="w").pack(padx=10, fill="x")
            tk.Label(c, text=ref, bg=CARD_BG, fg=TEXT_MUT, font=("Arial", 9),
                     anchor="w").pack(padx=10, pady=(2, 8), anchor="w")

        # Summary
        sc = Card(f); sc.pack(fill="x", pady=(6, 4))
        hr2 = tk.Frame(sc, bg=CARD_BG); hr2.pack(fill="x", padx=10, pady=(8, 4))
        tk.Label(hr2, text="Current settings", bg=CARD_BG, fg=TEXT_PRI,
                 font=("Arial", 11, "bold")).pack(side="left")
        self._ob = Badge(hr2, bg=OK_BG, fg=OK_FG); self._ob.pack(side="left", padx=8)
        self._s_laser = RRow(sc, "Laser power"); self._s_laser.pack(fill="x", padx=10)
        self._s_avg   = RRow(sc, "Line averaging"); self._s_avg.pack(fill="x", padx=10)
        self._s_intv  = RRow(sc, "Acquisition interval"); self._s_intv.pack(fill="x", padx=10)
        self._s_tip   = Tip(sc); self._s_tip.pack(padx=10, pady=(6, 10), fill="x")

    def calc_scan(self):
        hz    = int(self.spd.get())
        avg   = int(self.avg.get())
        laser = self.laser.get()
        intv  = self.intv.get()

        self._laser_lbl.config(text=f"{laser:.1f} %")
        self._intv_lbl.config(text=f"{intv:.1f} min")

        # Only calculated metric: relative SNR
        snr_rel = math.sqrt(1000 * avg / hz)
        self.m_snr.set(f"{snr_rel:.2f} ×")
        # Equivalent single-speed: same SNR with avg=1
        eq_hz = round(1000 / snr_rel**2)
        self.m_snreq.set(f"≈ {eq_hz} Hz  /  1× averaging")

        # Qualitative assessments
        laser_ok   = laser <= 5;  laser_warn = 5 < laser <= 10
        avg_ok     = avg <= 2;    avg_warn   = 2 < avg <= 8
        intv_ok    = intv >= 3;   intv_warn  = 1 <= intv < 3

        def assess(ok, warn, ok_t, warn_t, bad_t):
            if ok:   return ok_t,   OK_FG
            if warn: return warn_t, WARN_FG
            return bad_t, BAD_FG

        lt, lc = assess(laser_ok, laser_warn,
            f"{laser:.1f}% — within recommended range (≤ 5%)",
            f"{laser:.1f}% — elevated; consider reducing",
            f"{laser:.1f}% — high for live cell imaging")
        at, ac = assess(avg_ok, avg_warn,
            f"{avg}× — acceptable",
            f"{avg}× — consider reducing scan speed to {round(hz/avg)} Hz instead",
            f"{avg}× — excessive; substantially increases photon dose per line")
        it, ic = assess(intv_ok, intv_warn,
            f"{intv:.1f} min",
            f"{intv:.1f} min — short; ensure this matches biological timescale",
            f"{intv:.1f} min — very short; cumulative photon dose will be high")

        self._s_laser.set(lt, lc)
        self._s_avg.set(at, ac)
        self._s_intv.set(it, ic)

        if "badge_laser" in self._pbadges:
            b = self._pbadges["badge_laser"]
            if laser_ok:   b.ok(f"{laser:.1f}%")
            elif laser_warn: b.warn(f"{laser:.1f}%")
            else:            b.bad(f"{laser:.1f}%")
        if "badge_avg" in self._pbadges:
            b = self._pbadges["badge_avg"]
            if avg_ok:   b.ok(f"{avg}×")
            elif avg_warn: b.warn(f"{avg}×")
            else:          b.bad(f"{avg}×")
        if "badge_intv" in self._pbadges:
            b = self._pbadges["badge_intv"]
            if intv_ok:   b.ok(f"{intv:.1f} min")
            elif intv_warn: b.warn(f"{intv:.1f} min")
            else:           b.bad(f"{intv:.1f} min")

        issues = sum([not laser_ok, not avg_ok, not intv_ok])
        if issues == 0:   self._ob.ok("All within guidance")
        elif issues == 1: self._ob.warn("1 item to review")
        else:             self._ob.bad(f"{issues} items to review")

        tips = []
        if not laser_ok:
            tips.append("Reduce laser power — most effective single measure against phototoxicity (Icha et al., 2017).")
        if not avg_ok:
            tips.append(f"To achieve equivalent SNR without repeated line exposure, "
                        f"reduce scan speed to {round(hz/avg)} Hz with 1× averaging instead.")
        if not intv_ok:
            tips.append("Increase acquisition interval to match the timescale of the biological process (Frigault et al., 2009).")
        self._s_tip.config(
            text=" ".join(tips) if tips else
            "Record all settings (scan speed, line average, laser %, interval, format) "
            "and hold constant across all experimental sessions for inter-experiment comparability "
            "(North, J Cell Biol 2006; Waters, J Cell Biol 2009).")

    # ════════════════════════════════════════════════════════════════════════
    # STEP 5 — MULTI-CHANNEL
    # ════════════════════════════════════════════════════════════════════════
    def _p4(self, f):
        SecTitle(f, "Multi-channel configuration & crosstalk assessment").pack(
            anchor="w", pady=(8, 6))

        nr = tk.Frame(f, bg=BG); nr.pack(fill="x", pady=(0, 8))
        tk.Label(nr, text="Number of channels", bg=BG, fg=TEXT_SEC,
                 font=("Arial", 10)).pack(side="left", padx=(0, 8))
        self.nch = tk.StringVar(value="2")
        for v in ["1", "2", "3", "4"]:
            tk.Radiobutton(nr, text=v, variable=self.nch, value=v,
                           bg=BG, font=("Arial", 10),
                           command=self.build_channels).pack(side="left", padx=4)

        hdr = tk.Frame(f, bg=BG); hdr.pack(fill="x", pady=(4, 2))
        for t, w in [("Fluorophore", 20), ("Ex (nm)", 8), ("Em (nm)", 8), ("Detector", 10)]:
            tk.Label(hdr, text=t.upper(), bg=BG, fg=TEXT_MUT,
                     font=("Arial", 9, "bold"), width=w).pack(side="left")

        self._ch_frame = tk.Frame(f, bg=BG); self._ch_frame.pack(fill="x")

        self._xt_card = Card(f); self._xt_card.pack(fill="x", pady=6)
        tk.Label(self._xt_card, text="Spectral crosstalk risk",
                 bg=CARD_BG, fg=TEXT_PRI, font=("Arial", 11, "bold")).pack(
                     anchor="w", padx=10, pady=(8, 4))
        self._xt_inner = tk.Frame(self._xt_card, bg=CARD_BG)
        self._xt_inner.pack(fill="x", padx=10, pady=(0, 8))

        self._seq_card = Card(f); self._seq_card.pack(fill="x", pady=4)
        tk.Label(self._seq_card, text="Acquisition mode recommendation",
                 bg=CARD_BG, fg=TEXT_PRI, font=("Arial", 11, "bold")).pack(
                     anchor="w", padx=10, pady=(8, 4))
        self._seq_tip = Tip(self._seq_card)
        self._seq_tip.pack(padx=10, pady=(0, 10), fill="x")

        tk.Label(f,
                 text=("Crosstalk risk assessed by emission peak separation (Δλ_em) and "
                       "excitation wavelength proximity (Δλ_ex). These are qualitative indicators; "
                       "quantitative crosstalk assessment requires the spectral overlap integral "
                       "C_ij = ∫ E_i(λ)·F_j(λ) dλ / ∫ F_j(λ) dλ and single-labelled control images "
                       "(Zimmermann, Adv Biochem Eng Biotechnol 2005)."),
                 bg=BG, fg=TEXT_MUT, font=("Arial", 9),
                 wraplength=580, justify="left").pack(anchor="w", pady=6)

        self._ch_vars = []
        self._ch_ex_lbls = []
        self._ch_em_lbls = []
        self._ch_det_lbls = []

    def build_channels(self):
        for w in self._ch_frame.winfo_children():
            w.destroy()
        self._ch_vars.clear()
        self._ch_ex_lbls.clear()
        self._ch_em_lbls.clear()
        self._ch_det_lbls.clear()

        n = int(self.nch.get())
        defaults = [1, 3, 0, 4]
        for i in range(n):
            row = tk.Frame(self._ch_frame, bg=BG); row.pack(fill="x", pady=2)
            var = tk.StringVar(value=FLUOR_NAMES[defaults[i] if i < len(defaults) else 0])
            cb = ttk.Combobox(row, textvariable=var, state="readonly",
                              values=FLUOR_NAMES, font=("Arial", 10), width=18)
            cb.pack(side="left", padx=(0, 8))
            cb.bind("<<ComboboxSelected>>", lambda e: self.eval_xtalk())
            ex = tk.Label(row, text="—", bg=BG, fg=TEXT_SEC, font=("Arial", 10), width=8)
            ex.pack(side="left")
            em = tk.Label(row, text="—", bg=BG, fg=TEXT_SEC, font=("Arial", 10), width=8)
            em.pack(side="left")
            dt = tk.Label(row, text="—", bg=BG, fg=TEXT_SEC, font=("Arial", 10), width=12)
            dt.pack(side="left")
            self._ch_vars.append(var)
            self._ch_ex_lbls.append(ex)
            self._ch_em_lbls.append(em)
            self._ch_det_lbls.append(dt)

        self.eval_xtalk()

    def eval_xtalk(self):
        n = int(self.nch.get())
        chs = []
        for i in range(n):
            fl = next(x for x in FLUORS if x["name"] == self._ch_vars[i].get())
            chs.append(fl)
            self._ch_ex_lbls[i].config(text=f"{fl['ex']} nm")
            self._ch_em_lbls[i].config(text=f"{fl['em']} nm")
            self._ch_det_lbls[i].config(text="HyD" if fl["ex"] <= 561 else "HyD / PMT")

        for w in self._xt_inner.winfo_children():
            w.destroy()

        has_high = False
        if n == 1:
            tk.Label(self._xt_inner, text="Single channel — no crosstalk.",
                     bg=CARD_BG, fg=TEXT_SEC, font=("Arial", 10)).pack(anchor="w")
        else:
            for i in range(n):
                for j in range(i+1, n):
                    f1, f2 = chs[i], chs[j]
                    dem = abs(f1["em"] - f2["em"])
                    dex = abs(f1["ex"] - f2["ex"])
                    if dem < 30:
                        risk, fg = f"High  (Δλ_em = {dem} nm)", BAD_FG; has_high = True
                    elif dem < 60:
                        risk, fg = f"Moderate  (Δλ_em = {dem} nm)", WARN_FG
                    elif dex < 30:
                        risk, fg = f"Low — cross-excitation risk  (Δλ_ex = {dex} nm)", INFO_FG
                    else:
                        risk, fg = f"Low  (Δλ_em = {dem} nm)", OK_FG

                    pr = tk.Frame(self._xt_inner, bg=CARD_BG); pr.pack(fill="x", pady=(4, 0))
                    tk.Label(pr, text=f"{f1['name']}  ↔  {f2['name']}",
                             bg=CARD_BG, fg=TEXT_SEC, font=("Arial", 10)).pack(side="left")
                    tk.Label(pr, text=risk, bg=CARD_BG, fg=fg,
                             font=("Arial", 10, "bold")).pack(side="right")
                    tk.Frame(self._xt_inner, bg=BORDER, height=1).pack(fill="x", pady=(2, 4))

        all_sep   = all(abs(chs[i]["em"] - chs[j]["em"]) >= 60
                        for i in range(n) for j in range(i+1, n))
        any_cross = any(abs(chs[i]["ex"] - chs[j]["ex"]) < 30
                        for i in range(n) for j in range(i+1, n))

        if n == 1:
            seq = "Single channel — no acquisition mode selection required."
        elif has_high:
            seq = ("High crosstalk risk (Δλ_em < 30 nm). Sequential acquisition is required. "
                   "Post-acquisition linear spectral unmixing is recommended; acquire "
                   "single-labelled reference images per channel under identical conditions "
                   "(Zimmermann, 2005). Consider replacing the overlapping pair with fluorophores "
                   "separated by > 60 nm.")
        elif any_cross:
            seq = ("Cross-excitation risk (Δλ_ex < 30 nm between channels). "
                   "Sequential acquisition eliminates simultaneous laser excitation. "
                   "Verify absence of cross-excitation with single-labelled control specimens.")
        elif all_sep:
            seq = ("Low crosstalk risk (Δλ_em ≥ 60 nm for all pairs). "
                   "Simultaneous acquisition is feasible. For live cell imaging this is "
                   "preferable as it reduces total acquisition time and inter-channel "
                   "motion artefacts. Verify with single-labelled controls before "
                   "committing to simultaneous mode.")
        else:
            seq = ("Moderate crosstalk risk. Sequential acquisition is recommended. "
                   "Quantify crosstalk using single-labelled control specimens and "
                   "apply linear unmixing if needed (Zimmermann, 2005).")

        self._seq_tip.config(text=seq)


# ── RUN ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    SP8Tool().mainloop()
