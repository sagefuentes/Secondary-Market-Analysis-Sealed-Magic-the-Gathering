# Secondary Market Analysis — Sealed Magic: The Gathering Booster Boxes

![Power BI](https://img.shields.io/badge/Power%20BI-F2C811?style=flat&logo=powerbi&logoColor=black)
![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)
![Data Source](https://img.shields.io/badge/Source-PriceCharting.com-informational?style=flat)

A data analytics portfolio project analysing the secondary market for sealed Magic: The Gathering booster boxes, from vintage 1993 printings through to 2025 releases. Price data is sourced from completed eBay sales tracked by PriceCharting.com and visualised across three interactive Power BI report pages.

> **Note:** A screen recording walkthrough of the interactive report is available [here](#) *(link to be added)*.

---

## Project Overview

Magic: The Gathering sealed booster boxes represent a unique collectibles market — prices are driven by card availability, format legality, reprint announcements, and speculative demand. This project explores:

- How secondary market prices have changed across 117+ sets from 1993 to 2025
- Which set types (Standard, Masters, Commander, Un-Set, Universes Beyond) command the highest prices
- Which sets have experienced the greatest volatility and the largest corrections from their tracked peak prices
- The relationship between a set's release year and its current secondary market value

---

## Repository Contents

```
├── mtg_price_scraper.py        # Main scraper — pulls monthly price history from PriceCharting.com
├── debug_urls.py               # Diagnostic script — validates URLs and inspects available data keys
├── MTG_Booster_Box_Analysis.pbix  # Power BI Desktop report file
└── README.md
```

> **The dataset (CSV) is not included in this repository.** PriceCharting.com's terms of service prohibit redistribution of their price data. Run `mtg_price_scraper.py` to generate your own dataset — see instructions below.

---

## Data Source

**Source:** [PriceCharting.com](https://www.pricecharting.com)

PriceCharting tracks completed eBay and marketplace sales for collectibles. All prices in this dataset reflect **secondary market transactions**, not retail MSRP. Data is recorded monthly per set, with most sets tracked from mid-2021 onwards. A small number of vintage sets (Alpha/Beta era) have shorter tracking windows due to infrequent sales.

**Coverage:**
- 117 sets across all major product types
- May 2021 – June 2026
- Draft and Play boosters tracked where applicable (noted in set name)
- Universes Beyond sets flagged separately while retaining their Standard set type classification

**Limitations:**
- Pre-2021 price history is not available — the speculation spike of 2020–2021 cannot be fully contextualised against a pre-COVID baseline
- Vintage sets with infrequent sales (Arabian Nights, Portal Three Kingdoms, Legends) may reflect anomalous single transactions rather than sustained market prices
- Peak prices for vintage sets should be interpreted with caution for the same reason

---

## Scraper Setup and Usage

### Requirements

```bash
uv add requests beautifulsoup4 pandas
```

Or with pip:

```bash
pip install requests beautifulsoup4 pandas
```

### Running the Scraper

```bash
python mtg_price_scraper.py
```

The scraper will:
1. Hit the PriceCharting homepage to establish a session
2. Request each set page with a 2-second delay between requests
3. Extract monthly price history from the `VGPC.chart_data["used"]` JavaScript object embedded in each page
4. Output `mtg_booster_box_prices.csv` in the working directory

**Expected runtime:** approximately 4–5 minutes for the full set list.

### Output Format

| Column | Type | Description |
|---|---|---|
| `set_name` | Text | Display name of the set |
| `set_type` | Text | Core / Standard / Masters / Commander / Special / Un-Set / Beta |
| `is_universes_beyond` | Integer (0/1) | 1 if the set is a Universes Beyond product |
| `release_year` | Integer | Year the set was originally released |
| `date` | Date | First day of the month the price was recorded |
| `price_usd` | Decimal | Secondary market price in USD |
| `source_url` | Text | PriceCharting URL the data was scraped from |

### Validating URLs

If you want to add new sets or diagnose missing data, run the debug script first:

```bash
python debug_urls.py
```

This checks each URL for HTTP status, confirms `VGPC.chart_data` is present, and reports which data keys have non-zero values and how many monthly data points are available.

---

## Power BI Report

Open `MTG_Booster_Box_Analysis.pbix` in [Power BI Desktop](https://powerbi.microsoft.com/desktop/) (free download). When prompted, point the data source at your locally generated `mtg_booster_box_prices.csv` and refresh.

The report uses the **Accessible Orchid** theme throughout.

### Page 1 — Overview

A summary dashboard providing a high-level view of the dataset.

- **KPI cards:** Sets tracked, Period Low/High current prices with set names, Period Low/High historical prices with set names
- **Average Sealed Booster Box Price Over Time** — line chart showing the mean price across all tracked sets by month
- **All-Time Peak Prices by Set** — horizontal bar chart sorted by peak price, colour-coded by set type
- **Slicers:** Set Release Year range, Set Type, Universe (Within / Beyond)

### Page 2 — Price History

An exploratory page for comparing individual set price histories.

- **Secondary Market Sealed Booster Box Price History** — multi-line chart with one line per selected set; legend replaced by tooltips to handle the full set list
- **Release Year vs. Average Secondary Market Price by Set** — scatter plot showing the relationship between release era and average tracked price, with an X-axis range slider; sets above $5,000 average excluded for scale
- **Slicers:** Set Name (searchable), Set Type (searchable)
- **Cards:** Sets tracked in current selection, Price History Date Range

### Page 3 — Value Analysis

An analytical page focused on price volatility and peak-to-current corrections.

- **Peak to Current Ratio by Set** — horizontal bar chart showing how far each set's current price sits below its tracked peak; sets above 10× excluded for scale, full values visible in the table
- **Volatility % by Set** — bar chart showing price range as a percentage of peak price
- **Summary table** — all sets with Current Price, Peak Price, P/C Ratio, and Volatility %, conditionally formatted green (stable) to red (volatile / corrected)
- **Cards:** Average Volatility %, Least Volatile Set, Most Volatile Set
- **Slicer:** Set Name, Set Type

### DAX Measures

Key calculated measures used in the report:

| Measure | Description |
|---|---|
| `Peak Price` | All-time maximum recorded price per set |
| `Current Price` | Price at the most recent recorded month |
| `Peak to Current Ratio` | Peak ÷ Current — higher values indicate greater correction from peak |
| `Price Volatility` | Max minus Min price over the tracked period |
| `Volatility %` | Price Volatility ÷ Peak Price × 100 |
| `Avg Volatility %` | Average Volatility % across all sets in filter context |

---

## Skills Demonstrated

- **Python:** Web scraping with `requests` and `BeautifulSoup`, JavaScript data extraction via regex, session management, rate limiting, `pandas` data wrangling
- **Power BI:** Data modelling, DAX measures and calculated columns, cross-filter management, conditional formatting, custom theming, multi-page report design
- **Data analysis:** Outlier handling, scale decisions for skewed distributions, volatility metrics, domain-informed data interpretation

---

## Acknowledgements

Price data sourced from [PriceCharting.com](https://www.pricecharting.com). Magic: The Gathering is a trademark of Wizards of the Coast. This project is non-commercial and for portfolio purposes only.
