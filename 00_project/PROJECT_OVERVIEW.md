# Обзор проекта

## Карьерная цель
Совместный (2 человека) финансовый pet project для получения высокооплачиваемой
работы за пределами РФ: фонды, investment research, quant/ML-команды, AI-компании.
Не диплом. Обе должны понимать всю систему и указывать проект как совместный.

Проект должен показать полный цикл: нетривиальная экономическая гипотеза →
point-in-time данные с нуля → LLM/агенты по делу (не декоративно) → калиброванная
количественная модель → честный backtest (издержки, power-анализ, OOS) →
готовность зафиксировать null → работающий продукт/датасет при любом исходе.

## Ограничения
- 2× MacBook Pro (M3 32GB), локальные LLM 4B/8B/14B (Ollama/MLX)
- Бюджет: 0 ₽ старт, максимум ~5 000 ₽ суммарно на API/данные
- ЗАПРЕЩЕНО ядро на: IBES, FactSet, Bloomberg, дорогой options history
- МОЖНО: SEC/EDGAR/XBRL, TDnet/Yanoshin, J-Quants free, публичные API
- Рабочий Mac: никакого кода/данных/credentials работодателя
- ChatGPT Pro + Codex + Claude — для разработки, не как бесплатный API продукта
- LLM внутри продукта — в основном локальная

## Кандидат 1: ShadowNAV
Один BDC уже раскрыл fair-value mark private-credit facility за квартал Q →
другой листингованный BDC держит тот же facility, но ещё не отчитался за Q →
прогнозируем его скрытый mark → агрегируем в Shadow NAV → NAV/NII surprise →
(вторично) relative-value equity сигнал.

Ключевые дизайн-решения (согласованы):
- Единица = facility/tranche, не borrower (lien, ставка, maturity должны совпасть)
- Нормализация: FV/par; разложение на entry-price (cost/par) и post-entry (FV−cost)/par
- Cutoff = ПЕРВОЕ публичное раскрытие target (8-K/PR, не 10-Q)
- Primary H1 = точность nowcast марок (бухгалтерский ground truth), не returns
- Baseline-иерархия: B0 unchanged → B1 momentum → B2 median already-filed co-holders
  → B3 earliest co-holder → B4 prev-quarter median → B5 distress flags only
- H1b (categorical): non-accrual/PIK у раннего → у позднего, same date
- Equity-стадия: event study на ДАТЕ раскрытия source по акции target, минус BDC-корзина
- Кластеризация: facility×quarter И manager; общий valuation agent — измерять
- Same-manager co-investment и JV — исключать/тестировать отдельно
- Только relative value (дивидендный carry 10–12% убивает naked short)
- Честно про конкурентов: SOLVE/Preqin/Oxford Ledge продают мониторинговый слой;
  наша новизна ТОЛЬКО предсказательное звено + открытость. В питче обязательна фраза:
  "the monitoring layer is commercially available; we test whether the predictive
  and pricing layers still contain information"

## Кандидат 2: Japanese Language Wall
С апреля 2025 Prime Market TSE обязан к одновременному англ. раскрытию
(financial results + timely disclosure; summary допустим; исключение для срочных).
Standard (~1600 компаний) — нет. LLM сделал массовое чтение японского дешёвым.

Дизайн (согласован):
- Triple-diff: (Prime already-bilingual до 04.2025 = placebo) × (Prime late-translators
  = strong treatment) × (Standard = no treatment) × before/after April 2025
- Механизм-тест: эффект монотонен по foreign ownership; у no-foreign ≈ 0
- Гипотеза переформулирована под daily data: НЕ скорость в минутах, а drift T+1..T+10
- Treatment непрерывный: full/summary/none англ. вложение + лаг, по каждому событию
- Стартовый класс событий: ТОЛЬКО пересмотры прогнозов (числовой ground truth
  old/new прямо в документе/XBRL). Buybacks/M&A/value-up — потом
- Parallel trends проверить ДО основного теста; robustness без апр–мая 2025 (тарифный шок)
- Известное ограничение: эффект внутри первых минут сессии daily-барами не виден
- Расширение: «двойная стена» — value-up раскрытия Standard по-японски

## Слой агентов (для питча; строить ПОСЛЕ showdown)
ShadowNAV: Filing Locator → SOI Table Extractor → Schema Normalizer →
Entity & Tranche Resolver (LLM-ядро; regex принципиально не справляется с грязными
именами заёмщиков/траншей) → Footnote Flag Reader (PIK/non-accrual/watch) →
Data Quality auditor (не-агентный). N-PORT интервальных фондов = второй сенсор
(структурированный XML, парсинг дёшев).
Japan: Ingest → JP reader/classifier (локальная модель) → number extractor
(old/new forecast) → EN availability detector → event linker к ценам.
