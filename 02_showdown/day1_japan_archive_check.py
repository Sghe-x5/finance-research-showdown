import csv, requests, time, json, re, sys
from pathlib import Path

BASE = "https://webapi.yanoshin.jp/webapi/tdnet/list/{key}.json?limit=10000"
PERIODS = ["20230110-20230131","20230701-20230731","20240110-20240131",
           "20240701-20240731","20250110-20250131","20250701-20250731"]
KW = re.compile(r"業績予想の修正|配当予想の修正")
OUTPUT = Path(__file__).with_name("day1_japan_archive_summary.csv")

def head_ok(url):
    try:
        r = requests.get(url, timeout=30, allow_redirects=True)
        ok = r.status_code == 200 and len(r.content) > 500
        r.close()
        return ok, r.status_code
    except Exception as e:
        return False, str(e)[:60]

rows = []
for p in PERIODS:
    try:
        r = requests.get(BASE.format(key=p), timeout=60)
        data = r.json()
    except Exception as e:
        print(p, "FAIL", e); rows.append((p,0,0,"-","-")); continue
    items = [it.get("Tdnet") or it.get("TDnet") or it for it in data.get("items", [])]
    n = len(items)
    fr = [it for it in items if KW.search(it.get("title") or "")]
    pdf_status, xbrl_status = [], []
    for it in items[:400]:
        if len(pdf_status) < 2 and it.get("document_url"):
            pdf_status.append(head_ok(it["document_url"]))
        if len(xbrl_status) < 2 and it.get("url_xbrl"):
            xbrl_status.append(head_ok(it["url_xbrl"]))
        if len(pdf_status) >= 2 and len(xbrl_status) >= 2:
            break
    print(f"{p}: items={n} forecast_rev={len(fr)} "
          f"pdf={pdf_status} xbrl={xbrl_status}")
    if fr[:3]:
        for it in fr[:3]:
            print("   sample:", it.get("pubdate"), it.get("company_code"),
                  (it.get("title") or "")[:60])
    rows.append((p, n, len(fr), pdf_status, xbrl_status))
    time.sleep(2)

print("\n=== SUMMARY (в SHOWDOWN_TRACKER.md, таблица J1a/J1b) ===")
for p, n, nfr, pdf, xb in rows:
    print(f"{p[:6]}: items={n:>5} forecast_rev={nfr:>4} PDF_alive={pdf} XBRL_alive={xb}")
with OUTPUT.open("w", newline="", encoding="utf-8") as fh:
    writer = csv.writer(fh, lineterminator="\n")
    writer.writerow(["period", "items", "forecast_rev", "pdf_checks", "xbrl_checks"])
    writer.writerows(rows)
print(f"Summary saved to {OUTPUT}. A live index does not imply live documents.")
print("\nGate J1: PASS если 2023–2024 отдают items>0. "
      "Gate J1b: PASS если XBRL или PDF живы за старые периоды.")
