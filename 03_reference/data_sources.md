# Источники данных: URL, лимиты, оговорки

## SEC EDGAR (ShadowNAV) — бесплатно, без ключа
- Ticker→CIK: https://www.sec.gov/files/company_tickers.json
- Filings по компании: https://data.sec.gov/submissions/CIK{10 цифр}.json
  (form, acceptanceDateTime, reportDate, items для 8-K; earnings 8-K = items⊇"2.02")
- Полнотекстовый поиск: https://efts.sec.gov/LATEST/search-index?q=... (UI: efts.sec.gov)
- Документы: https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/...
- ТРЕБОВАНИЯ: User-Agent с реальным email; ≤10 req/sec (в скрипте sleep 0.15)
- PIT-ключ: ТОЛЬКО acceptanceDateTime, никогда period_end
- N-PORT (интервальные credit-фонды, XML со всеми позициями и FV) — второй сенсор

## TDnet / Yanoshin (Japan) — бесплатно, без ключа
- Docs: https://webapi.yanoshin.jp/tdnet/  · спека для машин: /llms.txt
- Endpoint: https://webapi.yanoshin.jp/webapi/tdnet/list/{key}.{fmt}
  key: recent | today | YYYYmmdd | YYYYmmdd-YYYYmmdd | код | код-код
  fmt: xml (полный) | json | json2 | rss | atom | html
  params: limit (деф. 300) | hasXBRL=1 | keyword= | since_id/by_id
- Подтверждено: янв-2025 отдаётся полностью. 2023–24 и живость PDF — скрипт J1a/J1b.
- Синк с TSE каждые несколько минут; rate limit не заявлен — быть вежливыми
- Официальный TDnet (jpx): публичный поиск хранит ~31 день; платный TDnet API
  JPX = 5 лет истории + право редистрибуции (план Z, корпоративный)
- Ключевые слова событий: 業績予想の修正 (пересмотр прогноза),
  配当予想の修正 (дивиденды), 決算短信 (earnings), 自己株式 (buyback)

## J-Quants (цены/фин. Япония) — https://jpx-jquants.com/en
- Free: daily OHLC, ЛАГ 12 НЕДЕЛЬ, 5 req/min, financials только 2 года
  → события для CAR брать старше июня-2026
- Light+: ¥1,650+/мес; minute/tick add-on ¥5,500/мес (с янв-2026) — ВНЕ БЮДЖЕТА
- Есть earnings announcement dates (полезно для календаря)

## Прочее (резервы)
- Companies House Free Accounts Data Product: ежедневные/месячные bulk iXBRL,
  API 600 req/5min (профили, не финстроки)
- CMS Hospital MRF: стандартный шаблон с 01.07.2024, CSV tall/wide, TXT-указатель
  в корне сайта больницы
- regulations.gov API (comment letters), USAspending/FPDS (deobligations)
- ClinicalTrials.gov API v2: https://clinicaltrials.gov/api/v2 (version history —
  проверять, Record History частично только скрапом)

## Вендоры-конкуренты (для честных дисклеймеров)
SOLVE Workstation BDC Data (162 BDC, co-investor marks «минуты после файлинга») ·
Preqin/BlackRock private credit (loan-level, вкл. non-traded) · Oxford Ledge ·
Captain/Odyssey · Cliffwater CDLI (~21k займов, $549B) · Moody's/PIMCO/ФРБ
Бостона (описательные исследования марок)

## Литературные якоря
- Cao, Jiang, Yang, Zhang (RFS 2023) — How to Talk When a Machine Is Listening
- ФРБ Бостона 2026 — PIK rise 6%→10% по 168 BDC
- Lead-lender appraisal premium (same loan) — valuation discipline literature
- Trading on government contracts (Economics Letters 2025)
- Задача на День 3 (Japan): собрать papers 2024–2026 по English disclosure /
  foreign ownership / Japan price discovery
