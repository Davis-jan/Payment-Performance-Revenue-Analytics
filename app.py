"""
Posta Kenya · Payment Performance & Revenue Analytics
-----------------------------------------------------
A fully interactive Streamlit dashboard for the cleaned eCitizen payment export.

Run:  streamlit run app.py
Data: Cleaned_Payment_Data.csv in this folder (or upload another CSV in the sidebar).
Logo: drop the official Posta logo into ./assets/ (any file whose name contains
      "posta" or "logo"), or upload it from the sidebar.
"""
import base64
import io
import itertools
import re
from datetime import timedelta
from pathlib import Path
from typing import Literal, cast

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from packaging.version import Version
from plotly.subplots import make_subplots
from scipy import stats

# ════════════════════════════════════════════════════════════════════════════
# Constants & branding
# ════════════════════════════════════════════════════════════════════════════
APP_DIR = Path(__file__).parent
ASSETS = APP_DIR / "assets"
DATA_FILE = APP_DIR / "Cleaned_Payment_Data.csv"

ORG = "Posta Kenya"
TITLE = "Payment Performance & Revenue Analytics"

NAVY, BLUE, SKY, PALE = "#0B2A5B", "#1457B8", "#8DB8F2", "#EAF1FB"
RED, MAROON = "#C8102E", "#7A1F2E"
INK, SLATE, LINE, GRID = "#14213D", "#5B6B86", "#DCE5F2", "#E8EEF7"
COLORWAY = [BLUE, MAROON, SKY, "#4F6D9A", NAVY, "#B04A5A", "#6FA3E8", "#8892A6"]
FONT = "Plus Jakarta Sans, Segoe UI, Arial, sans-serif"
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

LOGO_EXT = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
            ".webp": "image/webp", ".svg": "image/svg+xml"}

# Neutral stand-in used only until the official logo file is supplied.
FALLBACK_LOGO = f"""<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 260 80'>
<rect x='6' y='16' width='64' height='46' rx='5' fill='none' stroke='{NAVY}' stroke-width='5'/>
<path d='M8 20 L38 44 L68 20' fill='none' stroke='{RED}' stroke-width='5' stroke-linejoin='round'/>
<text x='84' y='42' font-family='Arial,sans-serif' font-weight='800' font-size='28' fill='{NAVY}'>POSTA</text>
<text x='85' y='62' font-family='Arial,sans-serif' font-weight='600' font-size='15' letter-spacing='3' fill='{RED}'>KENYA</text>
</svg>""".encode()


def find_logo():
    """Return (bytes, mime) for the first logo found in ./assets or the app folder."""
    for folder in (ASSETS, APP_DIR):
        if not folder.exists():
            continue
        for p in sorted(folder.iterdir()):
            if p.suffix.lower() in LOGO_EXT and ("posta" in p.stem.lower() or "logo" in p.stem.lower()):
                return p.read_bytes(), LOGO_EXT[p.suffix.lower()], True
    return FALLBACK_LOGO, "image/svg+xml", False


def data_uri(raw: bytes, mime: str) -> str:
    return f"data:{mime};base64,{base64.b64encode(raw).decode()}"


st.set_page_config(page_title=f"{ORG} · Payment Intelligence", page_icon="📮",
                   layout="wide", initial_sidebar_state="expanded")

NEW_API = Version(st.__version__.split("+")[0]) >= Version("1.50")
_KEY = itertools.count()


def show(fig):
    key = f"chart_{next(_KEY)}"
    if NEW_API:
        st.plotly_chart(fig, width="stretch", key=key)
    else:
        st.plotly_chart(fig, use_container_width=True, key=key)


def table(df, height=None, **kw):
    if NEW_API:
        if height:
            st.dataframe(df, use_container_width=True, hide_index=True,
                         height=height, **kw)
        else:
            st.dataframe(df, use_container_width=True, hide_index=True, **kw)
    else:
        if height:
            st.dataframe(df, use_container_width=True, hide_index=True,
                         height=height, **kw)
        else:
            st.dataframe(df, use_container_width=True, hide_index=True, **kw)


# ════════════════════════════════════════════════════════════════════════════
# Styling
# ════════════════════════════════════════════════════════════════════════════
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
.stApp, .stMarkdown, .stTabs button, label, h1, h2, h3, h4 {{ font-family: 'Plus Jakarta Sans','Segoe UI',Arial,sans-serif; }}
.stApp {{ background:#F4F7FC; }}
[data-testid="stHeader"] {{ background:transparent; }}
.block-container {{ padding-top:1.1rem; max-width:1560px; }}
[data-testid="stSidebar"] {{ background:#FFFFFF; border-right:1px solid {LINE}; }}
[data-testid="stSidebar"] h4 {{ color:{NAVY}; font-size:14px; margin:10px 0 2px 0; }}

.hero {{ display:flex; align-items:center; gap:22px; background:{NAVY}; border-bottom:4px solid {RED};
        border-radius:10px; padding:16px 24px; margin-bottom:14px; }}
.hero .logo {{ background:#fff; border-radius:8px; padding:8px 14px; height:62px; display:flex; align-items:center; }}
.hero .logo img {{ height:46px; max-width:210px; object-fit:contain; }}
.hero .t {{ color:#fff; font-size:25px; font-weight:800; letter-spacing:.2px; line-height:1.2; }}
.hero .s {{ color:#B9CCEB; font-size:13px; margin-top:3px; }}
.hero .chip {{ margin-left:auto; text-align:right; color:#DCE8FA; font-size:12.5px; line-height:1.6; }}
.hero .chip b {{ color:#fff; font-size:14px; }}

.kpi {{ background:#fff; border:1px solid {LINE}; border-left:4px solid {BLUE}; border-radius:10px;
       padding:13px 15px 11px 15px; height:100%; min-height:98px; }}
.kpi.alert {{ border-left-color:{RED}; }}
.kpi .l {{ color:{SLATE}; font-size:12.5px; font-weight:600; }}
.kpi .v {{ color:{NAVY}; font-size:24px; font-weight:800; line-height:1.25; margin-top:3px; }}
.kpi.alert .v {{ color:#9E0C25; }}
.kpi .d {{ font-size:12px; margin-top:3px; color:{SLATE}; }}
.kpi .d.up {{ color:{BLUE}; font-weight:600; }} .kpi .d.down {{ color:{RED}; font-weight:600; }}

.sec-t {{ color:{NAVY}; font-size:19px; font-weight:800; margin:18px 0 1px 0; }}
.sec-s {{ color:{SLATE}; font-size:12.5px; margin-bottom:10px; max-width:980px; }}
.note {{ color:{SLATE}; font-size:12px; margin:4px 0 8px 0; }}
.insights {{ background:#fff; border:1px solid {LINE}; border-radius:10px; padding:12px 18px; margin:10px 0 4px 0; }}
.insights li {{ color:#2B3A55; font-size:13.5px; margin:5px 0; }}
.insights .h {{ color:{NAVY}; font-weight:800; font-size:14px; }}

table.rules {{ width:100%; border-collapse:collapse; background:#fff; border:1px solid {LINE}; font-size:13px; }}
table.rules th {{ background:{PALE}; color:{NAVY}; text-align:left; padding:8px 10px; font-weight:700; }}
table.rules td {{ padding:7px 10px; border-top:1px solid {LINE}; color:#2B3A55; }}
.chipsev {{ display:inline-block; padding:1px 9px; border-radius:20px; font-size:11.5px; font-weight:700; }}
.sev-High {{ background:#FBE3E7; color:#9E0C25; }} .sev-Medium {{ background:#FFF1D6; color:#8A5A00; }}
.sev-Info {{ background:{PALE}; color:{BLUE}; }}

[data-testid="stPlotlyChart"] {{ background:#fff; border:1px solid {LINE}; border-radius:10px; padding:4px; }}
.stTabs [data-baseweb="tab-list"] {{ gap:2px; border-bottom:1px solid {LINE}; }}
.stTabs [data-baseweb="tab"] {{ font-weight:600; color:{SLATE}; padding:8px 14px; }}
.stTabs [aria-selected="true"] {{ color:{NAVY}; }}
</style>
""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# Anomaly rules
# ════════════════════════════════════════════════════════════════════════════
RULES = [
    dict(key="recon", label="Invoice ≠ paid + commission", sev="High",
         why="Invoice Amount should equal Amount Paid plus the eCitizen commission."),
    dict(key="neg_comm", label="Negative commission", sev="High",
         why="Commission below zero is not expected and affects reconciliation."),
    dict(key="zero_neg", label="Zero or negative payment", sev="High",
         why="A payment of zero or less needs a business explanation."),
    dict(key="missing_amt", label="Missing payment amount", sev="High",
         why="Record cannot be included in collection totals."),
    dict(key="rep_pair", label="Same payment & invoice reference repeated", sev="High",
         why="Strongest repeat pattern: both references match another row. Verify before calling it a duplicate."),
    dict(key="sci_ref", label="Reference in scientific notation", sev="High",
         why="Usually a spreadsheet conversion (e.g. 1.2E+10). Such references cannot be trusted for duplicate checks."),
    dict(key="outlier", label="Unusually large payment", sev="Medium",
         why="Outside the limit set by the chosen outlier method. Large payments can be legitimate."),
    dict(key="rep_pay", label="Payment reference repeated", sev="Medium",
         why="Reference appears on more than one row (may be one payment settling several invoices)."),
    dict(key="rep_inv", label="Invoice reference repeated", sev="Medium",
         why="Same invoice reference on more than one row."),
    dict(key="miss_ref", label="Missing payment reference", sev="Medium",
         why="Payment cannot be traced to the channel statement."),
    dict(key="miss_chan", label="Missing payment channel", sev="Medium",
         why="Channel not recorded, so the payment is excluded from channel analysis."),
    dict(key="rare_status", label="Rare or unrecognised status", sev="Medium",
         why="Status is numeric or makes up under 0.1% of records."),
    dict(key="legacy_date", label="Dated before the core period", sev="Medium",
         why="Date falls before the system's regular operating period (isolated historic records)."),
    dict(key="no_date", label="Missing date", sev="Medium",
         why="Record cannot be placed on the timeline."),
    dict(key="zero_comm", label="Zero commission", sev="Info",
         why="Commission is exactly zero. Often valid; listed so it can be confirmed."),
    dict(key="off_hours", label="Off-hours (00:00–05:59)", sev="Info",
         why="Transaction time is outside normal service hours."),
    dict(key="mpesa_variant", label="M-Pesa label variant", sev="Info",
         why="Channel written as MPesa / Mpesa instead of MPESA."),
]
RULE = {r["key"]: r for r in RULES}
STATIC_KEYS = [r["key"] for r in RULES if r["key"] != "outlier"]
REVIEW_KEYS = [r["key"] for r in RULES if r["sev"] in ("High", "Medium")]
SCI = r"^\d+(\.\d+)?[eE][+-]?\d+$"

BANDS = [-np.inf, 500, 1000, 2500, 5000, 10000, 50000, np.inf]
BAND_LABELS = ["Under 500", "500–999", "1,000–2,499", "2,500–4,999", "5,000–9,999", "10,000–49,999", "50,000+"]


# ════════════════════════════════════════════════════════════════════════════
# Data loading
# ════════════════════════════════════════════════════════════════════════════
def _count_map(s: pd.Series) -> pd.Series:
    return s.map(s.value_counts()).fillna(0).astype(int)


@st.cache_data(show_spinner="Reading and preparing the payment data…")
def load_data(file_bytes, harmonise: bool):
    src = io.BytesIO(file_bytes) if file_bytes else DATA_FILE
    raw = pd.read_csv(src, dtype={"Payment Reference": str, "Invoice Ref": str, "Invoice Number": str,
                                  "Payment Channel": str, "Status": str, "Time": str})
    missing = [c for c in ("Date", "Amount Paid", "ID") if c not in raw.columns]
    if missing:
        raise ValueError(f"Required columns are missing: {missing}")

    caps = {c: c in raw.columns for c in ("Invoice Amount", "Ecitizen Commission", "Time",
                                          "Payment Reference", "Invoice Ref", "Payment Channel", "Status")}
    for c in ("Invoice Amount", "Ecitizen Commission"):
        raw[c] = pd.to_numeric(raw[c], errors="coerce") if caps[c] else np.nan
    for c in ("Payment Reference", "Invoice Ref", "Payment Channel", "Status", "Time"):
        if not caps[c]:
            raw[c] = np.nan
        raw[c] = raw[c].astype("string").str.strip().replace({"": pd.NA}).astype("object")

    df = raw.copy()
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.normalize()
    df["Amount Paid"] = pd.to_numeric(df["Amount Paid"], errors="coerce")
    df["_n"] = 1

    # Time of day
    t = pd.to_datetime(df["Time"], format="%H:%M:%S", errors="coerce")
    if t.isna().any():
        t = t.fillna(pd.to_datetime(df["Time"], format="%H:%M", errors="coerce"))
    df["Hour"] = t.dt.hour

    # Channel labels
    df["Channel (raw)"] = df["Payment Channel"]
    squashed = df["Payment Channel"].fillna("").str.lower().str.replace(r"[^a-z]", "", regex=True)
    is_mpesa = squashed.eq("mpesa")
    df["flag_mpesa_variant"] = is_mpesa & df["Payment Channel"].ne("MPESA")
    if harmonise:
        df.loc[is_mpesa, "Payment Channel"] = "MPESA"
    df["flag_miss_chan"] = df["Payment Channel"].isna()
    df["Payment Channel"] = df["Payment Channel"].fillna("Not recorded")

    df["Status"] = df["Status"].fillna("Unknown")

    # Calendar helpers
    df["Weekday"] = pd.Categorical(df["Date"].dt.day_name(), categories=WEEKDAYS, ordered=True)
    df["Month"] = df["Date"].dt.strftime("%Y-%m")

    # Payment bands
    df["Payment band"] = pd.cut(df["Amount Paid"], BANDS, labels=BAND_LABELS, right=False)
    comm = df["Ecitizen Commission"].round(2)
    order = sorted(comm.dropna().unique())
    labels = {v: ("Negative" if v < 0 else f"KSh {v:g}") for v in order}
    df["Commission band"] = pd.Categorical(
        comm.map(labels).fillna("Missing"),
        categories=[labels[v] for v in order] + ["Missing"], ordered=True)

    # Core operating period = from the first month that has meaningful activity
    d = df["Date"].dropna()
    if len(d):
        per = d.dt.to_period("M")
        mc = per.value_counts()
        first_ok = mc[mc.astype("float64") >= float(mc.max()) * 0.01].index.min()
        core_start = d[per == first_ok].min()
    else:
        core_start = pd.NaT

    # Reference counts are measured on the full file so filters never hide a repeat
    df["Ref_Count"] = _count_map(df["Payment Reference"])
    df["Inv_Count"] = _count_map(df["Invoice Ref"])
    pair = df["Payment Reference"] + "|" + df["Invoice Ref"]
    df["Pair_Count"] = _count_map(pair)

    # Static rule flags
    amt, com = df["Amount Paid"], df["Ecitizen Commission"]
    share = df["Status"].value_counts(normalize=True)
    rare = share[share < 0.001].index
    df["flag_recon"] = (df["Invoice Amount"] - amt - com).abs().gt(0.01)
    df["flag_neg_comm"] = com.lt(0)
    df["flag_zero_neg"] = amt.le(0)
    df["flag_missing_amt"] = amt.isna()
    df["flag_rep_pair"] = df["Pair_Count"].gt(1)
    df["flag_sci_ref"] = df["Payment Reference"].fillna("").str.match(SCI)
    df["flag_rep_pay"] = df["Ref_Count"].gt(1)
    df["flag_rep_inv"] = df["Inv_Count"].gt(1)
    df["flag_miss_ref"] = df["Payment Reference"].isna()
    df["flag_rare_status"] = df["Status"].isin(rare) | df["Status"].str.fullmatch(r"\d+").fillna(False)
    df["flag_legacy_date"] = df["Date"].lt(core_start) if pd.notna(core_start) else False
    df["flag_no_date"] = df["Date"].isna()
    df["flag_zero_comm"] = com.eq(0)
    df["flag_off_hours"] = df["Hour"].lt(6).fillna(False)
    for k in STATIC_KEYS:
        df["flag_" + k] = df["flag_" + k].fillna(False).astype(bool)

    df["Review_Flags"] = df[["flag_" + k for k in REVIEW_KEYS if k != "outlier"]].sum(axis=1)
    return df, caps, core_start


# ════════════════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════════════════
def money(x, dec=0):
    return "—" if x is None or pd.isna(x) else f"KSh {x:,.{dec}f}"


def compact(x):
    if x is None or pd.isna(x):
        return "—"
    a = abs(x)
    for div, suf in ((1e9, "B"), (1e6, "M")):
        if a >= div:
            return f"KSh {x / div:,.2f}{suf}"
    return f"KSh {x:,.0f}"


def delta_html(cur, prev, inverse=False, label="vs previous period"):
    if prev is None or cur is None or pd.isna(prev) or pd.isna(cur) or prev == 0:
        return '<div class="d">&nbsp;</div>'
    ch = (cur - prev) / abs(prev) * 100
    good = (ch <= 0) if inverse else (ch >= 0)
    cls = "up" if good else "down"
    return f'<div class="d {cls}">{"▲" if ch >= 0 else "▼"} {abs(ch):.1f}% {label}</div>'


def kpi(label, value, sub="", tone="", tip=""):
    st.markdown(f'<div class="kpi {tone}" title="{tip or value}"><div class="l">{label}</div>'
                f'<div class="v">{value}</div>{sub or "<div class=d>&nbsp;</div>"}</div>', unsafe_allow_html=True)


def section(title, sub=""):
    st.markdown(f'<div class="sec-t">{title}</div>' + (f'<div class="sec-s">{sub}</div>' if sub else ""),
                unsafe_allow_html=True)


def style(fig, h=420, title=None):
    fig.update_layout(
        template="plotly_white", height=h, paper_bgcolor="white", plot_bgcolor="white", colorway=COLORWAY,
        font=dict(family=FONT, color=SLATE, size=12),
        margin=dict(l=55, r=25, t=62 if title else 30, b=45),
        title=dict(text=f"<b>{title}</b>", x=0.01, xanchor="left", font=dict(size=15, color=NAVY)) if title else None,
        hoverlabel=dict(bgcolor="white", font_size=12),
        legend=dict(orientation="h", y=1.13 if title else 1.06, x=0))
    fig.update_xaxes(showgrid=False, linecolor=LINE, zeroline=False)
    fig.update_yaxes(gridcolor=GRID, zeroline=False, linecolor=LINE)
    return fig


def outlier_mask(s, fit, method, thr, side):
    """Flag values in `s` using limits learned from `fit` (the current selection)."""
    log = "log" in method
    f = fit.dropna()
    tf = np.log1p(f.clip(lower=0)) if log else f
    tv = np.log1p(s.clip(lower=0)) if log else s
    if method.startswith("IQR"):
        q1, q3 = tf.quantile([.25, .75])
        lo, hi = q1 - thr * (q3 - q1), q3 + thr * (q3 - q1)
    elif method.startswith("Z-score"):
        lo, hi = tf.mean() - thr * tf.std(), tf.mean() + thr * tf.std()
    else:
        lo, hi = f.quantile((100 - thr) / 100), f.quantile(thr / 100)
    high, low = tv.gt(hi), tv.lt(lo)
    m = high if side == "High only" else (high | low)
    back = (lambda v: float(np.expm1(v))) if log else (lambda v: float(v))
    return (m & s.notna()), (back(lo), back(hi))


def build_series(d, measure, grain, win):
    if grain == "Daily":
        key, freq = d["Date"], "D"
    elif grain == "Weekly":
        key, freq = d["Date"] - pd.to_timedelta(d["Date"].dt.weekday, unit="D"), "W-MON"
    else:
        key, freq = d["Date"].dt.to_period("M").dt.to_timestamp(), "MS"
    g = d.groupby(key).agg(Revenue=(measure, "sum"), Transactions=("_n", "sum"), Average=(measure, "mean"))
    g.loc[g["Average"].isna(), "Revenue"] = np.nan
    g = g.reindex(pd.date_range(g.index.min(), g.index.max(), freq=freq))
    g.index.name = "Period"
    mp = max(2, int(np.ceil(win * 0.6)))
    g["Revenue_roll"] = g["Revenue"].rolling(win, min_periods=mp).mean()
    g["Tx_roll"] = g["Transactions"].rolling(win, min_periods=mp).mean()
    g["Weekday"] = g.index.day_name()
    return g


def daily_anomalies(daily, thr):
    """Robust z-score of each day against a centred rolling median."""
    r = daily["Revenue"]
    base = r.rolling(15, center=True, min_periods=5).median()
    resid = r - base
    mad = (resid - resid.median()).abs().median()
    z = 0.6745 * resid / mad if mad and mad > 0 else resid * np.nan
    return z, z.abs().gt(thr)


def pct(x, d=1):
    return "—" if pd.isna(x) else f"{x * 100:.{d}f}%"


def pfmt(p):
    return "<0.001" if p < 0.001 else f"{p:.3f}"


def gini(values):
    v = np.sort(values[values > 0])
    if len(v) < 2:
        return np.nan
    cum = np.cumsum(v)
    return float((len(v) + 1 - 2 * (cum.sum() / cum[-1])) / len(v))


# ════════════════════════════════════════════════════════════════════════════
# Sidebar – branding, data, filters, analysis settings
# ════════════════════════════════════════════════════════════════════════════
logo_bytes, logo_mime, logo_official = find_logo()

with st.sidebar:
    with st.expander("Data & branding", expanded=False):
        up_data = st.file_uploader("Replace the dataset (CSV)", type=["csv"])
        up_logo = st.file_uploader("Logo (PNG, JPG, SVG)", type=[e[1:] for e in LOGO_EXT])
        harmonise = st.toggle("Merge MPesa / Mpesa into MPESA", value=True, key="f_harm",
                              help="Spelling variants are always flagged; this only controls whether they are grouped together.")
        if not logo_official and not up_logo:
            st.caption("Showing a placeholder mark. Save the official logo as assets/posta_logo.png or upload it above.")
if up_logo is not None:
    logo_bytes, logo_mime = up_logo.getvalue(), up_logo.type or "image/png"

file_bytes = up_data.getvalue() if up_data else None
sig = (up_data.name, up_data.size) if up_data else "default"
if st.session_state.get("_sig") != sig:
    for k in [k for k in st.session_state if k.startswith("f_") and k != "f_harm"]:
        del st.session_state[k]
    st.session_state["_sig"] = sig

try:
    df, caps, core_start = load_data(file_bytes, harmonise)
except Exception as exc:  # noqa: BLE001
    st.error(f"Could not load the dataset: {exc}")
    st.stop()

dated = df["Date"].dropna()
if dated.empty:
    st.error("The dataset has no valid dates.")
    st.stop()
dmin, dmax = dated.min().date(), dated.max().date()
core = (core_start.date() if pd.notna(core_start) else dmin)

MEASURES = {"Amount Paid": "Amount Paid"}
if caps["Invoice Amount"]:
    MEASURES["Invoice Amount"] = "Invoice Amount"
if caps["Ecitizen Commission"]:
    MEASURES["eCitizen Commission"] = "Ecitizen Commission"

PRESETS = ["Core operating period", "Last 7 days", "Last 30 days", "Last 90 days",
           "This month", "Last month", "All records", "Custom range"]


def preset_range(p):
    if p == "Core operating period":
        s, e = core, dmax
    elif p == "All records":
        s, e = dmin, dmax
    elif p == "This month":
        s, e = dmax.replace(day=1), dmax
    elif p == "Last month":
        e = dmax.replace(day=1) - timedelta(days=1)
        s = e.replace(day=1)
    else:
        n = {"Last 7 days": 7, "Last 30 days": 30, "Last 90 days": 90}[p]
        s, e = dmax - timedelta(days=n - 1), dmax
    return max(s, dmin), min(e, dmax)


def reset_filters():
    for k in [k for k in st.session_state if k.startswith("f_") and k != "f_harm"]:
        del st.session_state[k]


with st.sidebar:
    st.image(data_uri(logo_bytes, logo_mime), width=170)
    st.markdown("#### Period")
    preset = st.selectbox("Quick select", PRESETS, key="f_preset", label_visibility="collapsed")
    if preset == "Custom range":
        dr = st.date_input("Custom range", value=(core, dmax), min_value=dmin, max_value=dmax, key="f_dates")
        start, end = (dr if isinstance(dr, (tuple, list)) and len(dr) == 2 else (core, dmax))
    else:
        start, end = preset_range(preset)
    st.caption(f"{start:%d %b %Y} → {end:%d %b %Y}")

    st.markdown("#### Filters")
    channels = sorted(df["Payment Channel"].unique())
    statuses = sorted(df["Status"].unique())
    sel_ch = st.multiselect("Payment channel", channels, default=channels, key="f_ch")
    sel_st = st.multiselect("Payment status", statuses, default=statuses, key="f_st")
    with st.expander("More filters"):
        amax = float(np.nanmax(df["Amount Paid"]))
        amin = float(np.nanmin(df["Amount Paid"]))
        c1, c2 = st.columns(2)
        a_lo = c1.number_input("Min payment", value=amin, min_value=amin, max_value=amax, key="f_amin")
        a_hi = c2.number_input("Max payment", value=amax, min_value=amin, max_value=amax, key="f_amax")
        bands = list(df["Commission band"].cat.categories)
        sel_cb = st.multiselect("Commission band", bands, default=bands, key="f_cb") if caps["Ecitizen Commission"] else bands
        sel_hr = st.slider("Hour of day", 0, 23, (0, 23), key="f_hr") if df["Hour"].notna().any() else (0, 23)
        only_flagged = st.toggle("Only records needing review", value=False, key="f_flagged",
                                 help="Shows rows carrying a High or Medium data-quality flag.")
    st.button("↺ Reset filters", on_click=reset_filters)

    st.markdown("#### Analysis")
    measure_label = st.selectbox("Measure", list(MEASURES), key="f_measure")
    measure = MEASURES[measure_label]
    grain = st.radio("Time grain", ["Daily", "Weekly", "Monthly"], horizontal=True, key="f_grain")
    win_default = {"Daily": 7, "Weekly": 4, "Monthly": 3}[grain]
    win = st.slider("Smoothing window (periods)", 2, 30, win_default, key=f"f_win_{grain}")
    compare = st.toggle("Compare with previous period", value=True, key="f_cmp")
    with st.expander("Anomaly settings"):
        o_method = st.selectbox("Payment outlier method",
                                ["IQR fence (log scale)", "IQR fence (raw amounts)", "Z-score (log scale)", "Top percentile"],
                                key="f_om")
        cfg = {"IQR fence (log scale)": (0.5, 5.0, 1.5, 0.1, "IQR multiplier"),
               "IQR fence (raw amounts)": (1.0, 10.0, 3.0, 0.5, "IQR multiplier"),
               "Z-score (log scale)": (1.5, 5.0, 3.0, 0.1, "Z threshold"),
               "Top percentile": (90.0, 99.99, 99.5, 0.01, "Percentile")}[o_method]
        o_thr = st.slider(cfg[4], cfg[0], cfg[1], cfg[2], cfg[3], key=f"f_ot_{o_method}")
        o_side = st.radio("Flag", ["High only", "High and low"], horizontal=True, key="f_os")
        d_thr = st.slider("Unusual-day sensitivity (robust z)", 2.0, 6.0, 3.5, 0.1, key="f_dz",
                          help="Days whose collections sit this many robust deviations from the local median are flagged.")

# ════════════════════════════════════════════════════════════════════════════
# Filtering
# ════════════════════════════════════════════════════════════════════════════
amt_default = (a_lo <= amin) and (a_hi >= amax)
others = (df["Payment Channel"].isin(sel_ch) & df["Status"].isin(sel_st)
          & (df["Amount Paid"].between(a_lo, a_hi) | (df["Amount Paid"].isna() & amt_default))
          & df["Commission band"].isin(sel_cb)
          & (df["Hour"].between(*sel_hr) | (df["Hour"].isna() & (sel_hr == (0, 23)))))
if only_flagged:
    others &= df["Review_Flags"].gt(0)

in_range = df["Date"].between(pd.Timestamp(start), pd.Timestamp(end))
cur = df[others & in_range].copy()

span = (end - start).days + 1
p_end = start - timedelta(days=1)
p_start = p_end - timedelta(days=span - 1)
prev = None
if compare and p_start >= core:
    pv = df[others & df["Date"].between(pd.Timestamp(p_start), pd.Timestamp(p_end))]
    prev = pv if len(pv) else None

# ════════════════════════════════════════════════════════════════════════════
# Header
# ════════════════════════════════════════════════════════════════════════════
st.markdown(f"""
<div class="hero">
  <div class="logo"><img src="{data_uri(logo_bytes, logo_mime)}" alt="{ORG} logo"></div>
  <div><div class="t">{TITLE}</div>
       <div class="s">{ORG} · eCitizen payment collections, transaction behaviour and data-quality monitoring</div></div>
  <div class="chip"><b>{start:%d %b %Y} – {end:%d %b %Y}</b><br>{len(cur):,} of {len(df):,} records · measure: {measure_label}</div>
</div>""", unsafe_allow_html=True)

if cur.empty:
    st.warning("No transactions match the current filters. Widen the period or reset the filters in the sidebar.")
    st.stop()

# ── Outlier flags & combined flag table (selection and full file share the same limits)
out_cur, (o_lo, o_hi) = outlier_mask(cur["Amount Paid"], cur["Amount Paid"], o_method, o_thr, o_side)
out_all, _ = outlier_mask(df["Amount Paid"], cur["Amount Paid"], o_method, o_thr, o_side)
cur["flag_outlier"] = out_cur
masks_cur = {r["key"]: (cur["flag_outlier"] if r["key"] == "outlier" else cur["flag_" + r["key"]]) for r in RULES}
counts_all = {r["key"]: int(out_all.sum() if r["key"] == "outlier" else df["flag_" + r["key"]].sum()) for r in RULES}
counts_cur = {k: int(v.sum()) for k, v in masks_cur.items()}
review_mask = np.zeros(len(cur), dtype=bool)
for key in REVIEW_KEYS:
    review_mask |= masks_cur[key].to_numpy(dtype=bool)
cur["Needs review"] = review_mask

# ── Series
series = build_series(cur, measure, grain, win)
daily = series if grain == "Daily" else build_series(cur, measure, "Daily", 7)
z_day, day_flag = daily_anomalies(daily, d_thr)
daily["Z"], daily["Unusual"] = z_day, day_flag

# ════════════════════════════════════════════════════════════════════════════
# KPI cards
# ════════════════════════════════════════════════════════════════════════════
tot = cur[measure].sum()
n_tx = len(cur)
avg_pay = cur[measure].mean()
med_pay = cur[measure].median()
comm_tot = cur["Ecitizen Commission"].sum() if caps["Ecitizen Commission"] else np.nan
active_days = int(daily["Transactions"].notna().sum())
gap_days = int(daily["Transactions"].isna().sum())

p_tot = prev[measure].sum() if prev is not None else None
p_n = len(prev) if prev is not None else None
p_avg = prev[measure].mean() if prev is not None else None
p_med = prev[measure].median() if prev is not None else None
p_comm = prev["Ecitizen Commission"].sum() if prev is not None and caps["Ecitizen Commission"] else None
p_days = int(prev["Date"].nunique()) if prev is not None else None

cols = st.columns(6)
with cols[0]:
    kpi(f"Total {measure_label.lower()}", compact(tot), delta_html(tot, p_tot), tip=money(tot))
with cols[1]:
    kpi("Transactions", f"{n_tx:,}", delta_html(n_tx, p_n))
with cols[2]:
    kpi("Average payment", money(avg_pay), delta_html(avg_pay, p_avg))
with cols[3]:
    kpi("Median payment", money(med_pay), delta_html(med_pay, p_med))
with cols[4]:
    kpi("eCitizen commission", compact(comm_tot), delta_html(comm_tot, p_comm), tip=money(comm_tot))
with cols[5]:
    kpi("Days with activity", f"{active_days:,}", delta_html(active_days, p_days))

n_rev = int(review_mask.sum())
rep_rows = cur[cur["flag_rep_pay"]]
rep_value = rep_rows.loc[rep_rows.groupby("Payment Reference").cumcount() > 0, "Amount Paid"].sum()
st.write("")
cols = st.columns(4)
with cols[0]:
    kpi("Records needing review", f"{n_rev:,}", f'<div class="d">{n_rev / n_tx * 100:.1f}% of selection (High + Medium flags)</div>', "alert")
with cols[1]:
    kpi("Unusually large payments", f"{counts_cur['outlier']:,}", f'<div class="d">Above {money(o_hi)} · {o_method}</div>', "alert")
with cols[2]:
    kpi("Rows with a repeated payment reference", f"{counts_cur['rep_pay']:,}",
        f'<div class="d">{counts_cur["rep_pair"]:,} also repeat the invoice reference</div>', "alert")
with cols[3]:
    kpi("Value in repeat rows (after first)", compact(rep_value), '<div class="d">Exposure to verify, not a confirmed loss</div>', "alert", tip=money(rep_value))

prev_note = (f"Compared with {p_start:%d %b %Y} – {p_end:%d %b %Y}." if prev is not None else
             "No comparable earlier period inside the core operating period." if compare else "Comparison is switched off.")
excluded = len(df) - len(cur)
st.markdown(f'<div class="note">{prev_note} Showing {n_tx:,} of {len(df):,} records ({excluded:,} excluded by period or filters). '
            f'{gap_days} calendar day(s) in the range have no records and are shown as gaps, not zeros.</div>', unsafe_allow_html=True)

# ── Auto-generated insights
ins = []
dd = daily.dropna(subset=["Revenue"])
if len(dd):
    top = dd["Revenue"].idxmax()
    med = dd["Revenue"].median()
    ins.append(f"Peak day was <b>{top:%a %d %b %Y}</b> with {money(dd.loc[top, 'Revenue'])}"
               + (f", {dd.loc[top, 'Revenue'] / med:.1f}× the median day." if med > 0 else "."))
    wk = dd.groupby("Weekday")["Revenue"].mean().dropna()
    if len(wk) > 1:
        ins.append(f"<b>{wk.idxmax()}</b> is the strongest weekday (avg {money(wk.max())}); <b>{wk.idxmin()}</b> the weakest ({money(wk.min())}).")
if cur["Hour"].notna().any():
    hc = cur["Hour"].value_counts(normalize=True)
    peak_hour = int(float(str(hc.idxmax())))
    ins.append(f"Peak hour is <b>{peak_hour:02d}:00–{peak_hour + 1:02d}:00</b>, handling {pct(hc.max())} of transactions.")
chn = cur.groupby("Payment Channel").agg(n=("_n", "sum"), v=(measure, "sum")).sort_values("n", ascending=False)
if len(chn):
    ins.append(f"<b>{chn.index[0]}</b> carries {pct(chn['n'].iloc[0] / chn['n'].sum())} of transactions and {pct(chn['v'].iloc[0] / chn['v'].sum())} of {measure_label.lower()}.")
pos = cur.loc[cur[measure] > 0, measure].sort_values(ascending=False)
if len(pos) > 100:
    k = max(1, int(len(pos) * 0.01))
    ins.append(f"The largest 1% of payments ({k:,} transactions) contribute {pct(pos.iloc[:k].sum() / pos.sum())} of the total.")
if prev is not None and p_tot:
    ch = (tot - p_tot) / abs(p_tot)
    ins.append(f"{measure_label} {'rose' if ch >= 0 else 'fell'} {abs(ch) * 100:.1f}% against the previous period.")
n_unusual = int(day_flag.sum())
if n_unusual:
    ins.append(f"<b>{n_unusual}</b> day(s) look unusual against their local trend (see the Anomalies tab).")
st.markdown('<div class="insights"><div class="h">What stands out</div><ul style="margin:6px 0 2px 18px;padding:0">'
            + "".join(f"<li>{i}</li>" for i in ins) + "</ul></div>", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════
# Tabs
# ════════════════════════════════════════════════════════════════════════════
t_over, t_time, t_chan, t_size, t_comm, t_stat, t_anom, t_data = st.tabs(
    ["Overview", "Time patterns", "Channels & status", "Payment size", "Commission",
     "Statistics", "Anomalies & data quality", "Data explorer"])

unit = {"Daily": "day", "Weekly": "week", "Monthly": "month"}[grain]

# ───────────────────────── Overview ─────────────────────────
with t_over:
    section(f"{measure_label} and transaction trend",
            f"{grain} totals with a {win}-{unit} rolling average. Red markers are days that look unusual against their local trend.")
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.07, row_heights=[0.6, 0.4])
    fig.add_bar(x=series.index, y=series["Revenue"], name=measure_label, marker_color=SKY, opacity=.85,
                hovertemplate="%{x|%d %b %Y}<br>KSh %{y:,.0f}<extra></extra>", row=1, col=1)
    fig.add_scatter(x=series.index, y=series["Revenue_roll"], name=f"{win}-{unit} average", mode="lines",
                    line=dict(color=NAVY, width=3), hovertemplate="%{x|%d %b %Y}<br>Average: KSh %{y:,.0f}<extra></extra>", row=1, col=1)
    if prev is not None and grain == "Daily":
        pd_ser = build_series(prev, measure, "Daily", win)
        fig.add_scatter(x=pd_ser.index + pd.Timedelta(days=span), y=pd_ser["Revenue"], name="Previous period",
                        mode="lines", line=dict(color="#8892A6", width=1.5, dash="dot"),
                        hovertemplate="Previous period<br>KSh %{y:,.0f}<extra></extra>", row=1, col=1)
    if grain == "Daily":
        um = daily[daily["Unusual"]]
        fig.add_scatter(x=um.index, y=um["Revenue"], mode="markers", name="Unusual day",
                        marker=dict(color=RED, size=9, line=dict(color="white", width=1)),
                        hovertemplate="%{x|%d %b %Y}<br>KSh %{y:,.0f}<extra>Unusual day</extra>", row=1, col=1)
    fig.add_bar(x=series.index, y=series["Transactions"], name="Transactions", marker_color="#B7CDEB",
                hovertemplate="%{x|%d %b %Y}<br>%{y:,.0f} transactions<extra></extra>", row=2, col=1)
    fig.add_scatter(x=series.index, y=series["Tx_roll"], name=f"Transactions {win}-{unit} average", mode="lines",
                    line=dict(color=MAROON, width=2.5), hovertemplate="%{y:,.0f}<extra>average</extra>", row=2, col=1)
    fig.update_yaxes(title_text="KSh", tickformat=",.0f", row=1, col=1)
    fig.update_yaxes(title_text="Transactions", tickformat=",", row=2, col=1)
    fig.update_layout(hovermode="x unified", barmode="overlay")
    fig.update_xaxes(rangeslider=dict(visible=True, thickness=0.05), row=2, col=1)
    show(style(fig, 700))

    c1, c2 = st.columns(2)
    with c1:
        f2 = go.Figure(go.Scatter(x=series.index, y=series["Average"], mode="lines+markers", connectgaps=False,
                                  line=dict(color=BLUE, width=2), marker=dict(size=4),
                                  hovertemplate="%{x|%d %b %Y}<br>KSh %{y:,.0f}<extra></extra>"))
        f2.update_yaxes(tickformat=",.0f", title_text="KSh")
        show(style(f2, 380, f"Average payment per transaction ({grain.lower()})"))
    with c2:
        cum = series["Revenue"].fillna(0).cumsum()
        f3 = go.Figure(go.Scatter(x=cum.index, y=cum, fill="tozeroy", line=dict(color=NAVY, width=2),
                                  fillcolor="rgba(20,87,184,.18)", hovertemplate="%{x|%d %b %Y}<br>KSh %{y:,.0f}<extra></extra>"))
        f3.update_yaxes(tickformat=",.0f", title_text="KSh")
        show(style(f3, 380, f"Cumulative {measure_label.lower()}"))

    section("Monthly summary")
    mon = (cur.groupby("Month").agg(Transactions=("_n", "sum"), Total=(measure, "sum"), Average=(measure, "mean"),
                                    Median=(measure, "median"), Commission=("Ecitizen Commission", "sum"),
                                    Active_days=("Date", "nunique")).reset_index())
    mon["Change in total"] = mon["Total"].pct_change()
    sty = mon.style.format({"Transactions": "{:,.0f}", "Total": "{:,.0f}", "Average": "{:,.0f}", "Median": "{:,.0f}",
                            "Commission": "{:,.0f}", "Active_days": "{:,.0f}", "Change in total": "{:+.1%}"}, na_rep="—")
    table(sty)

# ───────────────────────── Time patterns ─────────────────────────
with t_time:
    section("When do payments arrive?", "Switch the metric to see whether busy periods are driven by volume or by value.")
    tm = st.radio("Metric", ["Transactions", "Collections"], horizontal=True, key="f_tm")
    val = "_n" if tm == "Transactions" else measure
    agg = "sum"

    a, b = st.columns([1.15, 1])
    with a:
        if cur["Hour"].notna().any():
            hm = cur.pivot_table(index="Weekday", columns="Hour", values=val, aggfunc=agg, observed=False).reindex(WEEKDAYS)
            f = go.Figure(go.Heatmap(z=hm.values, x=[f"{int(h):02d}" for h in hm.columns], y=hm.index,
                                     colorscale=[[0, PALE], [.5, SKY], [1, NAVY]], xgap=2, ygap=2,
                                     hovertemplate="%{y} %{x}:00<br>%{z:,.0f}<extra></extra>"))
            f.update_yaxes(autorange="reversed")
            f.update_xaxes(title_text="Hour of day")
            show(style(f, 400, f"{tm} by weekday and hour"))
        else:
            st.info("This dataset has no usable Time column, so hourly patterns are unavailable.")
    with b:
        wd = cur.groupby("Weekday", observed=False)[val].sum().reindex(WEEKDAYS)
        f = go.Figure(go.Bar(x=wd.index, y=wd.values, marker_color=[BLUE if d not in ("Saturday", "Sunday") else MAROON for d in wd.index],
                             hovertemplate="%{x}<br>%{y:,.0f}<extra></extra>"))
        f.update_yaxes(tickformat=",.0f")
        show(style(f, 400, f"{tm} by weekday"))

    a, b = st.columns(2)
    with a:
        if cur["Hour"].notna().any():
            hr = cur.groupby("Hour")[val].sum()
            f = go.Figure(go.Scatter(x=hr.index, y=hr.values, mode="lines+markers", line=dict(color=BLUE, width=3),
                                     fill="tozeroy", fillcolor="rgba(20,87,184,.12)",
                                     hovertemplate="%{x:02d}:00<br>%{y:,.0f}<extra></extra>"))
            f.update_xaxes(dtick=2, title_text="Hour of day")
            show(style(f, 360, f"{tm} by hour of day"))
    with b:
        dom = cur.groupby(cur["Date"].dt.day)[val].sum()
        f = go.Figure(go.Bar(x=dom.index, y=dom.values, marker_color=SKY, hovertemplate="Day %{x}<br>%{y:,.0f}<extra></extra>"))
        f.update_xaxes(dtick=2, title_text="Day of month")
        show(style(f, 360, f"{tm} by day of month"))

    cal = daily.dropna(subset=["Transactions"]).copy()
    cal["Value"] = cal["Transactions"] if tm == "Transactions" else cal["Revenue"]
    cal["Week"] = cal.index - pd.to_timedelta(cal.index.weekday, unit="D")
    cp = cal.pivot_table(index="Weekday", columns="Week", values="Value", aggfunc="sum").reindex(WEEKDAYS)
    f = go.Figure(go.Heatmap(z=cp.values, x=cp.columns, y=cp.index, colorscale=[[0, PALE], [.5, SKY], [1, NAVY]],
                             xgap=2, ygap=2, hovertemplate="Week of %{x|%d %b %Y}<br>%{y}<br>%{z:,.0f}<extra></extra>"))
    f.update_yaxes(autorange="reversed")
    show(style(f, 330, f"Calendar view — {tm.lower()} per day"))

# ───────────────────────── Channels & status ─────────────────────────
with t_chan:
    section("Payment channels", "Pareto view: bars show each channel, the line shows the running share of the total.")
    cm = st.radio("Rank channels by", ["Transactions", "Collections"], horizontal=True, key="f_cm")
    ch = (cur.groupby("Payment Channel").agg(Transactions=("_n", "sum"), Collections=("Amount Paid", "sum"),
                                             Average=("Amount Paid", "mean"), Median=("Amount Paid", "median"),
                                             Commission=("Ecitizen Commission", "sum"))
          .sort_values(cm, ascending=False))
    ch["Share"] = ch[cm] / ch[cm].sum()
    ch["Cumulative"] = ch["Share"].cumsum()
    a, b = st.columns([1.3, 1])
    with a:
        top_n = st.slider("Channels to display", 3, max(3, len(ch)), min(10, max(3, len(ch))), key="f_topn") if len(ch) > 3 else len(ch)
        pc = ch.head(top_n)
        f = make_subplots(specs=[[{"secondary_y": True}]])
        f.add_bar(x=pc.index, y=pc[cm], name=cm, marker_color=BLUE, hovertemplate="%{x}<br>%{y:,.0f}<extra></extra>")
        f.add_scatter(x=pc.index, y=pc["Cumulative"], name="Cumulative share", mode="lines+markers",
                      line=dict(color=RED, width=2.5), hovertemplate="%{y:.1%}<extra>cumulative</extra>", secondary_y=True)
        f.update_yaxes(tickformat=".0%", range=[0, 1.02], secondary_y=True, showgrid=False)
        f.update_yaxes(tickformat=",.0f", secondary_y=False)
        f.update_xaxes(tickangle=-30)
        show(style(f, 430, f"{cm} by channel"))
    with b:
        tree = cur[cur["Amount Paid"] > 0].groupby(["Payment Channel", "Status"], observed=True)["Amount Paid"].sum().reset_index()
        f = px.treemap(tree, path=[px.Constant("All"), "Payment Channel", "Status"], values="Amount Paid",
                       color_discrete_sequence=COLORWAY)
        f.update_traces(hovertemplate="%{label}<br>KSh %{value:,.0f}<extra></extra>", root_color="white")
        show(style(f, 430, "Collections by channel and status"))

    section("Channel mix over time")
    mode = st.radio("Show", ["Absolute", "Share of total"], horizontal=True, key="f_mix")
    top6 = list(ch.index[:6])
    mix = cur.assign(Channel=np.where(cur["Payment Channel"].isin(top6), cur["Payment Channel"], "Other"))
    mx = mix.groupby(["Month", "Channel"])["_n"].sum().reset_index()
    f = px.bar(mx, x="Month", y="_n", color="Channel", color_discrete_sequence=COLORWAY, labels={"_n": "Transactions"})
    if mode == "Share of total":
        f.update_layout(barnorm="percent")
    f.update_yaxes(title_text="% of transactions" if mode == "Share of total" else "Transactions")
    show(style(f, 400))

    a, b = st.columns([1.4, 1])
    with a:
        section("Channel scorecard")
        sc = ch.reset_index()[["Payment Channel", "Transactions", "Collections", "Average", "Median", "Commission", "Share"]]
        table(sc.style.format({"Transactions": "{:,.0f}", "Collections": "{:,.0f}", "Average": "{:,.0f}",
                               "Median": "{:,.0f}", "Commission": "{:,.0f}", "Share": "{:.1%}"}, na_rep="—"), height=360)
    with b:
        section("Status")
        stt = cur.groupby("Status").agg(Transactions=("_n", "sum"), Collections=("Amount Paid", "sum")).reset_index()
        f = px.pie(stt, names="Status", values="Transactions", hole=.6, color_discrete_sequence=COLORWAY)
        f.update_traces(textinfo="percent+label", hovertemplate="%{label}<br>%{value:,.0f} transactions<extra></extra>")
        show(style(f, 300))
        table(stt.style.format({"Transactions": "{:,.0f}", "Collections": "{:,.0f}"}))

# ───────────────────────── Payment size ─────────────────────────
with t_size:
    section("How large are payments?", "Payments are heavily right-skewed, so a log scale shows the whole range at once.")
    pay = cur["Amount Paid"].dropna()
    a, b = st.columns(2)
    with a:
        scale = st.radio("Histogram scale", ["Log", "Linear (to 99th percentile)"], horizontal=True, key="f_hs")
        if scale == "Log":
            pp = pay[pay > 0]
            lo, hi = np.log10(pp.min()), np.log10(pp.max())
            cnt, edges = np.histogram(np.log10(pp), bins=48, range=(lo, hi))
            ctr, wid = (edges[:-1] + edges[1:]) / 2, np.diff(edges)
            tv = [v for v in (10, 100, 500, 1000, 2500, 5000, 10000, 50000, 100000, 500000) if 10 ** lo <= v <= 10 ** hi * 1.5]
            f = go.Figure(go.Bar(x=ctr, y=cnt, width=wid * .96, marker_color=BLUE,
                                 customdata=np.c_[10 ** edges[:-1], 10 ** edges[1:]],
                                 hovertemplate="KSh %{customdata[0]:,.0f} – %{customdata[1]:,.0f}<br>%{y:,} payments<extra></extra>"))
            f.update_xaxes(tickvals=np.log10(tv), ticktext=[f"{v:,}" for v in tv], title_text="Payment (KSh, log scale)")
        else:
            clip = pay[pay <= pay.quantile(.99)]
            cnt, edges = np.histogram(clip, bins=60)
            f = go.Figure(go.Bar(x=(edges[:-1] + edges[1:]) / 2, y=cnt, width=np.diff(edges) * .96, marker_color=BLUE,
                                 customdata=np.c_[edges[:-1], edges[1:]],
                                 hovertemplate="KSh %{customdata[0]:,.0f} – %{customdata[1]:,.0f}<br>%{y:,} payments<extra></extra>"))
            f.update_xaxes(title_text="Payment (KSh)")
        f.add_vline(x=np.log10(max(pay.median(), 1)) if scale == "Log" else pay.median(), line_dash="dot", line_color=RED,
                    annotation_text=f"median {pay.median():,.0f}", annotation_font_color=RED)
        f.update_yaxes(title_text="Payments", tickformat=",")
        show(style(f, 400, "Distribution of payments"))
    with b:
        bd = cur.groupby("Payment band", observed=False).agg(Payments=("_n", "sum"), Collections=("Amount Paid", "sum")).reset_index()
        bd["Share of payments"] = bd["Payments"] / bd["Payments"].sum()
        bd["Share of collections"] = bd["Collections"] / bd["Collections"].sum()
        f = go.Figure()
        f.add_bar(x=bd["Payment band"], y=bd["Share of payments"], name="Share of payments", marker_color=SKY)
        f.add_bar(x=bd["Payment band"], y=bd["Share of collections"], name="Share of collections", marker_color=NAVY)
        f.update_layout(barmode="group")
        f.update_yaxes(tickformat=".0%")
        show(style(f, 400, "Payment bands: few large payments, most of the value"))

    a, b = st.columns(2)
    with a:
        grp = st.selectbox("Compare payment sizes by", ["Payment Channel", "Weekday", "Month", "Status", "Commission band"], key="f_vg")
        topg = cur[grp].value_counts().head(8).index
        sub = cur[cur[grp].isin(topg) & cur["Amount Paid"].gt(0)]
        sub = sub.sample(frac=1, random_state=1).groupby(grp, observed=True).head(3000)
        f = px.violin(sub, x=grp, y="Amount Paid", color=grp, box=True, points=False, color_discrete_sequence=COLORWAY)
        f.update_yaxes(type="log", title_text="Amount paid (KSh, log)")
        f.update_layout(showlegend=False)
        show(style(f, 420, f"Payment size by {grp.lower()} (violin + box)"))
    with b:
        vs = np.sort(pay[pay > 0].to_numpy(dtype=float))
        if len(vs) > 10:
            cum = np.cumsum(vs) / vs.sum()
            xs = np.linspace(0, 1, len(vs))
            idx = np.linspace(0, len(vs) - 1, 400).astype(int)
            g = gini(vs)
            f = go.Figure()
            f.add_scatter(x=[0, 1], y=[0, 1], mode="lines", line=dict(color="#8892A6", dash="dot"), name="Perfect equality")
            f.add_scatter(x=xs[idx], y=cum[idx], mode="lines", fill="tonexty", fillcolor="rgba(20,87,184,.12)",
                          line=dict(color=BLUE, width=3), name="Collections", hovertemplate="Bottom %{x:.0%} of payments → %{y:.1%} of value<extra></extra>")
            f.update_xaxes(tickformat=".0%", title_text="Cumulative share of payments (smallest first)")
            f.update_yaxes(tickformat=".0%", title_text="Cumulative share of value")
            show(style(f, 420, f"Concentration of value (Gini {g:.2f})"))

# ───────────────────────── Commission ─────────────────────────
with t_comm:
    if not caps["Ecitizen Commission"]:
        st.info("This dataset has no 'Ecitizen Commission' column.")
    else:
        cc = cur.dropna(subset=["Ecitizen Commission"])
        section("eCitizen commission", "Commission is shown as recorded; the reconciliation rule checks Invoice = Paid + Commission.")
        k = st.columns(4)
        rate = cc["Ecitizen Commission"].sum() / cc["Invoice Amount"].sum() if caps["Invoice Amount"] and cc["Invoice Amount"].sum() else np.nan
        with k[0]:
            kpi("Total commission", compact(comm_tot), delta_html(comm_tot, p_comm), tip=money(comm_tot))
        with k[1]:
            kpi("Average per transaction", money(cc["Ecitizen Commission"].mean(), 2))
        with k[2]:
            kpi("Commission as share of invoices", pct(rate, 2))
        with k[3]:
            kpi("Zero-commission entries", f"{counts_cur['zero_comm']:,}",
                f'<div class="d">{counts_cur["zero_comm"] / n_tx * 100:.1f}% of selection</div>', "alert" if counts_cur["zero_comm"] else "")
        st.write("")
        a, b = st.columns(2)
        with a:
            cb = cur.groupby("Commission band", observed=False).agg(Transactions=("_n", "sum"), Commission=("Ecitizen Commission", "sum")).reset_index()
            f = make_subplots(specs=[[{"secondary_y": True}]])
            f.add_bar(x=cb["Commission band"], y=cb["Transactions"], name="Transactions", marker_color=BLUE)
            f.add_scatter(x=cb["Commission band"], y=cb["Commission"], name="Commission earned", mode="lines+markers",
                          line=dict(color=RED, width=2.5), secondary_y=True)
            f.update_yaxes(tickformat=",.0f")
            show(style(f, 400, "Transactions and commission by commission band"))
        with b:
            smp = cc.sample(min(len(cc), 8000), random_state=3)
            f = px.scatter(smp, x="Amount Paid", y="Ecitizen Commission", color="Payment Channel", opacity=.55,
                           color_discrete_sequence=COLORWAY, hover_data=["Date"])
            f.update_xaxes(type="log", title_text="Amount paid (KSh, log)")
            f.update_yaxes(title_text="Commission (KSh)")
            show(style(f, 400, "Commission against payment size (sample of 8,000)"))
        a, b = st.columns(2)
        with a:
            cm_m = cur.groupby("Month").agg(Commission=("Ecitizen Commission", "sum")).reset_index()
            f = px.bar(cm_m, x="Month", y="Commission", color_discrete_sequence=[NAVY])
            f.update_yaxes(tickformat=",.0f", title_text="KSh")
            show(style(f, 360, "Commission by month"))
        with b:
            cch = cur.groupby("Payment Channel").agg(Commission=("Ecitizen Commission", "sum")).sort_values("Commission", ascending=False).head(10).reset_index()
            f = px.bar(cch, x="Commission", y="Payment Channel", orientation="h", color_discrete_sequence=[BLUE])
            f.update_yaxes(autorange="reversed")
            f.update_xaxes(tickformat=",.0f", title_text="KSh")
            show(style(f, 360, "Commission by channel"))

# ───────────────────────── Statistics ─────────────────────────
with t_stat:
    section("Statistical tests", "Non-parametric tests are used because daily collections and payment sizes are skewed. "
            "With very large samples almost any difference is 'significant', so read the effect size alongside the p-value.")
    alpha = st.select_slider("Significance level", options=[0.01, 0.05, 0.10], value=0.05, key="f_alpha")
    rows = []

    def add(q, test, stat, p, effect, reading):
        rows.append({"Question": q, "Test": test, "Statistic": stat, "p-value": pfmt(p) if p is not None else "—",
                     "Effect size": effect, "Result": ("Significant" if p is not None and p < alpha else "Not significant"),
                     "Reading": reading})

    d = daily.dropna(subset=["Revenue"])
    if len(d) >= 8:
        rho, p = map(float, stats.spearmanr(np.arange(len(d)), d["Revenue"]))
        add("Is daily revenue trending over the period?", "Spearman rank correlation with time", f"ρ = {rho:.2f}", p, f"|ρ| = {abs(rho):.2f}",
            "Upward trend." if p < alpha and rho > 0 else "Downward trend." if p < alpha else "No reliable trend.")
        groups = [g["Revenue"].values for _, g in d.groupby("Weekday") if len(g) >= 3]
        if len(groups) >= 2:
            H, p = stats.kruskal(*groups)
            n_, k_ = sum(len(g) for g in groups), len(groups)
            eps = max(0.0, (H - k_ + 1) / (n_ - k_)) if n_ > k_ else np.nan
            add("Does daily revenue differ by weekday?", "Kruskal–Wallis", f"H = {H:.1f}", p, f"ε² = {eps:.2f}",
                "Weekday matters." if p < alpha else "No clear weekday effect.")
        we, wk = d[d["Weekday"].isin(["Saturday", "Sunday"])]["Revenue"], d[~d["Weekday"].isin(["Saturday", "Sunday"])]["Revenue"]
        if len(we) >= 3 and len(wk) >= 3:
            U, p = stats.mannwhitneyu(we, wk)
            rb = 1 - 2 * U / (len(we) * len(wk))
            add("Do weekends differ from weekdays?", "Mann–Whitney U", f"U = {U:,.0f}", p, f"r = {rb:+.2f}",
                f"Weekend median {money(we.median())} vs weekday {money(wk.median())}.")
        if len(d) >= 20:
            k2, p = stats.normaltest(d["Revenue"])
            add("Is daily revenue normally distributed?", "D'Agostino–Pearson", f"K² = {k2:.1f}", p, f"skew = {stats.skew(d['Revenue']):.2f}",
                "Not normal; medians and rank tests are more reliable." if p < alpha else "Consistent with a normal distribution.")
        if prev is not None:
            pdly = build_series(prev, measure, "Daily", 7).dropna(subset=["Revenue"])
            if len(pdly) >= 3:
                U, p = stats.mannwhitneyu(d["Revenue"], pdly["Revenue"])
                rb = 1 - 2 * U / (len(d) * len(pdly))
                add("Has daily revenue shifted since the previous period?", "Mann–Whitney U", f"U = {U:,.0f}", p, f"r = {rb:+.2f}",
                    f"Median day {money(d['Revenue'].median())} now vs {money(pdly['Revenue'].median())} before.")
    both = daily.dropna(subset=["Revenue", "Transactions"])
    if len(both) >= 8:
        r, p = map(float, stats.pearsonr(both["Transactions"], both["Revenue"]))
        add("Does revenue rise with transaction volume?", "Pearson correlation", f"r = {r:.2f}", p, f"R² = {r * r:.2f}",
            f"{r * r * 100:.0f}% of the day-to-day change in revenue is explained by volume.")
    top5 = cur["Payment Channel"].value_counts().head(5).index
    cg = [cur.loc[cur["Payment Channel"] == c, "Amount Paid"].dropna().values for c in top5]
    cg = [g for g in cg if len(g) >= 3]
    if len(cg) >= 2:
        H, p = stats.kruskal(*cg)
        n_, k_ = sum(len(g) for g in cg), len(cg)
        add("Does payment size differ between the leading channels?", "Kruskal–Wallis", f"H = {H:,.1f}", p,
            f"ε² = {max(0.0, (H - k_ + 1) / (n_ - k_)):.2f}", "Channels attract different payment sizes." if p < alpha else "No clear difference.")
    if rows:
        table(pd.DataFrame(rows), height=min(420, 60 + 38 * len(rows)))
    else:
        st.info("Not enough data in the current selection to run the tests. Widen the period.")

    section("Revenue against volume", "Choose a polynomial degree to compare a straight-line slope with a curve.")
    deg = st.radio("Fit", ["Linear", "Quadratic", "Cubic"], horizontal=True, key="f_deg")
    degree = {"Linear": 1, "Quadratic": 2, "Cubic": 3}[deg]
    sc_d = daily.dropna(subset=["Revenue", "Transactions"])
    sc_d = sc_d[sc_d["Transactions"] > 0]
    if len(sc_d) > degree + 3:
        x, y = sc_d["Transactions"].values.astype(float), sc_d["Revenue"].values
        coef = np.polyfit(x, y, degree)
        yh = np.polyval(coef, x)
        r2 = 1 - ((y - yh) ** 2).sum() / ((y - y.mean()) ** 2).sum()
        xs = np.linspace(x.min(), x.max(), 200)
        f = px.scatter(sc_d.reset_index(), x="Transactions", y="Revenue", color="Weekday", hover_name="Period",
                       category_orders={"Weekday": WEEKDAYS}, color_discrete_sequence=COLORWAY, opacity=.8)
        f.add_scatter(x=xs, y=np.polyval(coef, xs), mode="lines", name=f"{deg} fit", line=dict(color=RED, width=3))
        f.update_xaxes(title_text="Transactions per day")
        f.update_yaxes(title_text=f"{measure_label} per day (KSh)", tickformat=",.0f")
        show(style(f, 460, f"{deg} fit · R² = {r2:.2f}"))
        slope, intercept, _, _, stderr = stats.linregress(x, y)
        tcrit = stats.t.ppf(0.975, len(x) - 2)
        st.markdown(f'<div class="note">Straight-line reading: each extra daily transaction is associated with about '
                f'<b>{money(slope)}</b> more revenue (95% interval {money(slope - tcrit * stderr)} to {money(slope + tcrit * stderr)}); '
                f'intercept {money(intercept)}. This is an association, not proof that volume causes revenue.</div>', unsafe_allow_html=True)

# ───────────────────────── Anomalies & data quality ─────────────────────────
with t_anom:
    section("Rule-based checks", "Every rule is a prompt to investigate, not a finding of error or fraud. Counts are shown for the current selection and for the whole file.")
    html = ['<table class="rules"><tr><th>Check</th><th>Severity</th><th style="text-align:right">In selection</th>'
           '<th style="text-align:right">Share</th><th style="text-align:right">Whole file</th><th>Why it matters</th></tr>']
    for r in sorted(RULES, key=lambda r: ["High", "Medium", "Info"].index(r["sev"])):
        n = counts_cur[r["key"]]
        why = r["why"] + (f" Current limit: above {money(o_hi)}." if r["key"] == "outlier" else "")
        html.append(f'<tr><td><b>{r["label"]}</b></td><td><span class="chipsev sev-{r["sev"]}">{r["sev"]}</span></td>'
                    f'<td style="text-align:right">{n:,}</td><td style="text-align:right">{n / n_tx * 100:.2f}%</td>'
                    f'<td style="text-align:right">{counts_all[r["key"]]:,}</td><td>{why}</td></tr>')
    st.markdown("".join(html) + "</table>", unsafe_allow_html=True)
    st.write("")

    a, b = st.columns([1, 1.25])
    with a:
        bar = pd.DataFrame([{"Check": r["label"], "Records": counts_cur[r["key"]], "Severity": r["sev"]} for r in RULES])
        bar = bar[bar["Records"] > 0].sort_values("Records")
        f = px.bar(bar, x="Records", y="Check", color="Severity", orientation="h",
                   color_discrete_map={"High": RED, "Medium": "#E0A030", "Info": SKY})
        f.update_xaxes(type="log", title_text="Records (log scale)")
        show(style(f, 430, "Flags in the current selection"))
    with b:
        fig = go.Figure()
        fig.add_bar(x=daily.index, y=daily["Revenue"], marker_color=SKY, name="Daily revenue")
        um = daily[daily["Unusual"]]
        fig.add_scatter(x=um.index, y=um["Revenue"], mode="markers", name="Unusual day",
                        marker=dict(color=RED, size=10, line=dict(color="white", width=1)),
                        customdata=um["Z"], hovertemplate="%{x|%d %b %Y}<br>KSh %{y:,.0f}<br>robust z = %{customdata:.1f}<extra></extra>")
        fig.update_yaxes(tickformat=",.0f", title_text="KSh")
        show(style(fig, 430, f"Unusual days ({len(um)} flagged at |z| > {d_thr:.1f})"))

    section("Inspect flagged records")
    opts = [f'{r["label"]} ({counts_cur[r["key"]]:,})' for r in RULES if counts_cur[r["key"]] > 0]
    keys = [r["key"] for r in RULES if counts_cur[r["key"]] > 0]
    if keys:
        pick = st.selectbox("Check to inspect", opts, key="f_pick")
        k = keys[opts.index(pick)]
        cols_show = [c for c in ["ID", "Date", "Time", "Payment Channel", "Channel (raw)", "Payment Reference", "Invoice Ref",
                                 "Amount Paid", "Invoice Amount", "Ecitizen Commission", "Status", "Ref_Count", "Pair_Count"] if c in cur.columns]
        view = cur[masks_cur[k]][cols_show].sort_values("Amount Paid", ascending=False)
        st.caption(f"{len(view):,} record(s). {RULE[k]['why']}")
        table(view.head(3000), height=330)
        st.download_button("Download these records (CSV)", view.to_csv(index=False).encode(), f"flagged_{k}.csv", "text/csv")
    else:
        st.success("No flags in the current selection.")

    section("Repeated payment references",
            "Grouped by reference so each case can be checked against the channel statement. A repeat is not automatically a duplicate: "
            "one reference may legitimately settle several invoices, and scientific-notation references may be spreadsheet damage.")
    if len(rep_rows):
        rg = (rep_rows.groupby("Payment Reference").agg(Rows=("_n", "sum"), Invoices=("Invoice Ref", "nunique"),
                                                         Distinct_amounts=("Amount Paid", "nunique"), Total_paid=("Amount Paid", "sum"),
                                                         First=("Date", "min"), Last=("Date", "max"),
                                                         Sci_notation=("flag_sci_ref", "max")).reset_index())
        rg["Pattern"] = np.where(rg["Sci_notation"], "Scientific notation — verify source",
                          np.where(rg["Invoices"] < rg["Rows"], "Same invoice repeated", "Shared across invoices"))
        rg = rg.sort_values(["Rows", "Total_paid"], ascending=False).drop(columns="Sci_notation")
        s1, s2, s3 = st.columns(3)
        s1.metric("Repeated references", f"{len(rg):,}")
        s2.metric("Rows involved", f"{int(rg['Rows'].sum()):,}")
        s3.metric("Largest repeat group", f"{int(rg['Rows'].max()):,} rows")
        table(rg.head(500).style.format({"Total_paid": "{:,.0f}", "Rows": "{:,.0f}", "Invoices": "{:,.0f}",
                                         "Distinct_amounts": "{:,.0f}", "First": "{:%d %b %Y}", "Last": "{:%d %b %Y}"}, na_rep="—"), height=330)
    else:
        st.success("No repeated payment references in the current selection.")

    section("Export")
    if st.button("Prepare Excel report for the current selection", key="f_xl"):
        flag_cols = [("flag_outlier" if r["key"] == "outlier" else "flag_" + r["key"]) for r in RULES]
        fl = cur[flag_cols].copy()
        fl.columns = [r["label"] for r in RULES]
        anyf = fl.any(axis=1)
        names = np.array(fl.columns, dtype=object)
        flagged = cur.loc[anyf, [c for c in ["ID", "Date", "Time", "Payment Channel", "Payment Reference", "Invoice Ref",
                                             "Amount Paid", "Invoice Amount", "Ecitizen Commission", "Status"] if c in cur.columns]].copy()
        flagged["Flags"] = ["; ".join(names[row]) for row in fl.loc[anyf].values]
        summary = pd.DataFrame({
            "Metric": ["Period", "Records", f"Total {measure_label}", "Average payment", "Median payment", "eCitizen commission",
                       "Records needing review", "Unusual days"],
            "Value": [f"{start} to {end}", n_tx, round(tot, 2), round(avg_pay, 2), round(med_pay, 2),
                      None if pd.isna(comm_tot) else round(comm_tot, 2), n_rev, n_unusual]})
        rules_df = pd.DataFrame([{"Check": r["label"], "Severity": r["sev"], "In selection": counts_cur[r["key"]],
                                  "Whole file": counts_all[r["key"]], "Why it matters": r["why"]} for r in RULES])
        bio = io.BytesIO()
        with pd.ExcelWriter(bio, engine="openpyxl") as xw:
            summary.to_excel(xw, sheet_name="Summary", index=False)
            rules_df.to_excel(xw, sheet_name="Checks", index=False)
            mon.to_excel(xw, sheet_name="Monthly", index=False)
            ch.reset_index().to_excel(xw, sheet_name="Channels", index=False)
            flagged.head(100000).to_excel(xw, sheet_name="Flagged records", index=False)
            for ws in xw.book.worksheets:
                for cell in ws[1]:
                    cell.font = cell.font.copy(bold=True, color="FFFFFF")
                    cell.fill = cell.fill.copy(fgColor="0B2A5B", fill_type="solid")
                from openpyxl.utils import get_column_letter
                for column_index, col in enumerate(ws.columns, start=1):
                    column_letter = get_column_letter(column_index)
                    ws.column_dimensions[column_letter].width = min(48, max(12, max(len(str(c.value or "")) for c in col[:50]) + 2))
        st.session_state["xl_bytes"] = bio.getvalue()
    if "xl_bytes" in st.session_state:
        st.download_button("Download Excel report", st.session_state["xl_bytes"], "payment_review_report.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ───────────────────────── Data explorer ─────────────────────────
with t_data:
    section("Pivot builder", "Build your own summary: pick the dimensions, the value and how to combine it.")
    DIMS = ["Payment Channel", "Status", "Weekday", "Month", "Hour", "Commission band", "Payment band"]
    p1, p2, p3, p4 = st.columns(4)
    rows_d = p1.selectbox("Rows", DIMS, index=0, key="f_pr")
    cols_d = p2.selectbox("Columns", ["(none)"] + DIMS, index=0, key="f_pc")
    val_d = p3.selectbox("Value", ["Transactions", "Amount Paid", "Invoice Amount", "Ecitizen Commission"], key="f_pv")
    agg_d = p4.selectbox("Combine by", ["sum", "mean", "median", "max", "count"], key="f_pa")
    src = cur.copy()
    vcol = "_n" if val_d == "Transactions" else val_d
    afn = cast(Literal["sum", "mean", "median", "max", "count"],
               "sum" if val_d == "Transactions" and agg_d != "count" else agg_d)
    if cols_d == "(none)" or cols_d == rows_d:
        pv = src.groupby(rows_d, observed=True)[vcol].agg(afn).reset_index()
        f = px.bar(pv, x=rows_d, y=vcol, color_discrete_sequence=[BLUE])
        f.update_yaxes(title_text=f"{afn} of {val_d}", tickformat=",.0f")
        show(style(f, 380))
        table(pv.style.format({vcol: "{:,.2f}"}, na_rep="—"))
    else:
        pv = src.pivot_table(index=rows_d, columns=cols_d, values=vcol, aggfunc=afn, observed=True).fillna(0)
        f = px.imshow(pv, aspect="auto", color_continuous_scale=[[0, PALE], [.5, SKY], [1, NAVY]])
        show(style(f, 420))
        table(pv.reset_index().style.format("{:,.0f}", subset=pv.columns, na_rep="—"), height=320)

    section("Browse and search records")
    q1, q2 = st.columns([2, 3])
    query = q1.text_input("Search payment reference, invoice reference or invoice number", key="f_q")
    show_cols = q2.multiselect("Columns", [c for c in cur.columns if not c.startswith(("flag_", "_"))],
                               default=[c for c in ["ID", "Date", "Time", "Payment Channel", "Payment Reference", "Invoice Ref",
                                                    "Amount Paid", "Invoice Amount", "Ecitizen Commission", "Status"] if c in cur.columns], key="f_cols")
    view = cur
    if query:
        qq = query.strip()
        hit = pd.Series(False, index=cur.index)
        for c in ("Payment Reference", "Invoice Ref", "Invoice Number"):
            if c in cur.columns:
                hit |= cur[c].fillna("").str.contains(qq, case=False, regex=False)
        view = cur[hit]
    st.caption(f"{len(view):,} record(s) match. Showing the most recent 5,000.")
    table(view[show_cols].sort_values("Date", ascending=False).head(5000), height=380)
    st.download_button("Download matching records (CSV)", view[show_cols].to_csv(index=False).encode(),
                       "payment_records.csv", "text/csv")

st.markdown(f'<div class="note" style="margin-top:22px;border-top:1px solid {LINE};padding-top:8px">'
            f'{ORG} · Payment Intelligence. Figures are calculated from the filtered records. Calendar gaps are not treated as zero-activity days. '
            f'Flags prompt investigation; they are not a determination of error or fraud.</div>', unsafe_allow_html=True)
