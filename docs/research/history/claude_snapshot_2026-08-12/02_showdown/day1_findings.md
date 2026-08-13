# День 1 — находки (12 августа 2026)

## Japan
1. ✅ GATE J1 ЧАСТИЧНО ПРОЙДЕН: живой запрос
   `webapi.yanoshin.jp/webapi/tdnet/list/20250101-20250131.json` вернул полный
   индекс за январь 2025: total_count=300 (кап дефолтного лимита), pubdate до
   минуты, company_code, title, document_url, url_xbrl.
2. ✅ Плотность целевых событий высокая: в одном видимом хвосте месяца ~15
   пересмотров прогнозов/дивидендов (коды 6034, 2003, 6391, 3843, 9513, 3944,
   4552, 3341, 4685, 4923, 3826, 9536...).
3. ✅ БОНУС: у части пересмотров прогнозов есть XBRL-вложения (0912*.zip),
   у 決算短信 — 0812*.zip → числовой ground truth может пережить смерть PDF.
4. ⚠️ НЕ ПРОВЕРЕНО (критично, J1b): живы ли сами PDF/XBRL по старым ссылкам
   (TDnet официально хранит файлы ~месяц; индекс у Yanoshin свой, файлы — нет).
   → скрипт day1_japan_archive_check.py.
5. ⚠️ Глубина 2023–2024 не проверена → тот же скрипт.
6. Поля url_report_type_earnings_forecast / expected_dividends в янв-2025 = null;
   проверить на свежих датах — если заполняются, это структурированный прогноз
   без парсинга PDF.

## BDC
1. ✅ Окна существуют: сезон Q2-2026 — GBDC 03.08 (после закрытия, 8-K/PR),
   BBDC 05.08, GSBD 06.08 (после закрытия, call 07.08 9:00 ET). Даже между
   «ранними» фондами окна 2–3 дня.
2. ✅ Универс для матрицы (Raymond James weekly, авг-2026): ARCC OBDC OTF BXSL
   FSK GBDC PSEC MAIN HTGC MSDL TSLX GSBD MFIC OCSL TRIN PFLT BCSF BBDC SLRC
   CGBD NMFC CSWC KBDC NCDL MSIF SCM CCAP TCPC PNNT PFLT CION WHF TPVG HRZN
   GECC RWAY GAIN GLAD OXSQ FDUS SAR OFS SLRC (топ по активам: ARCC $30.5B,
   OBDC $15.4B, OTF $15.1B, BXSL $13.8B, FSK $12.0B, GBDC $8.3B).
3. ⏳ Точная матрица за 5 кварталов → day1_bdc_reporting_order.py (нужен email
   в User-Agent).
4. ⏳ CIK non-traded (BCRED, HLEND, ASIF, OCIC) — руками через EDGAR search.

## Ограничения моих инструментов (важно знать)
- Sandbox Клода не ходит на sec.gov/yanoshin напрямую → скрипты запускаются
  на ваших маках; web_fetch Клода не может конструировать произвольные URL
  (только виденные) → пробу 2023–2024 делает ваш скрипт.
