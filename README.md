# Posta Kenya · Payment Performance & Revenue Analytics

Interactive Streamlit + Plotly dashboard for `Cleaned_Payment_Data.csv`.

## Run
```bash
pip install -r requirements.txt
streamlit run app.py
```
Keep `Cleaned_Payment_Data.csv` next to `app.py` (or upload a CSV in the sidebar).
Put the official logo in `assets/` (see `assets/README.txt`).

## What you can change on screen
- **Period**: core operating period, last 7/30/90 days, this/last month, all records, custom range
- **Filters**: channel, status, payment amount range, commission band, hour of day, "only records needing review"; one-click reset
- **Analysis**: measure (Amount Paid / Invoice Amount / Commission), daily-weekly-monthly grain, smoothing window, previous-period comparison
- **Anomaly settings**: outlier method (IQR on log or raw, Z-score, top percentile), limit and side, unusual-day sensitivity

## Tabs
Overview · Time patterns (weekday x hour heatmap, calendar view) · Channels & status (Pareto, treemap, mix over time, scorecard) · Payment size (histogram, bands, violin, concentration/Gini) · Commission · Statistics (Kruskal-Wallis, Mann-Whitney, Spearman, Pearson, normality, linear/quadratic/cubic fit with slope interval) · Anomalies & data quality (17 rules, unusual days, repeated-reference explorer, Excel export) · Data explorer (pivot builder, search, CSV download)

## Data handling notes
- Required columns: `Date`, `Amount Paid`, `ID`. Other columns unlock the related sections.
- The default period starts at the first month with meaningful activity; isolated earlier records are flagged ("Dated before the core period") rather than silently dropped. Choose "All records" to include them.
- Calendar days with no records are shown as gaps, not zeros.
- Repeated references are counted on the full file, so filters never hide a repeat. They are flags for review, not confirmed duplicates.
- Statistical tests are non-parametric; with 100k+ rows read the effect size, not only the p-value.
