# Меморандум №3 (сжато): ShadowNAV vs Japan + финальные договорённости

## Переход Cross-Lender Convergence → ShadowNAV (идея ChatGPT, принята)
First-Reporter Same-Quarter чище по трём осям:
- причинность: не нужна история «кредитор сходится к другим» — обе марки описывают
  одно состояние одного актива на одну дату, разными timestamps публикации
- ground truth: нет 3 месяцев событий между t и t+1
- торгуемость: настоящий forecast до публикации, а не ретро-регрессия
Convergence t→t+1 остаётся SECONDARY H2 на той же инфраструктуре.

## Четыре поправки Клода к ShadowNAV (приняты обеими сторонами)
1. ВЕНДОРЫ: SOLVE Workstation BDC Data продаёт ровно co-holder marks «через
   минуты после файлинга» (162 BDC, 44k инвестиций, ~10k компаний); Preqin/BlackRock
   — loan-level BDC holdings включая non-traded; + Oxford Ledge, Captain/Odyssey.
   → мониторинговый слой коммодитизирован; moat только predictive model;
   вероятность equity-эффективности выше; честный дисклеймер обязателен.
2. VALUATION AGENTS: общий сторонний оценщик (Kroll/Houlihan/Lincoln) у source и
   target → предсказуемость отличная, но механизм «один карандаш в двух тетрадях».
   Для торговли ок, для статистики: кластеризация по appraiser; вытаскивать
   оценщиков из 10-K; «appraiser fixed effects» — бонусный research-угол.
3. ХРОНОЛОГИЯ: non-traded скорее файлят ПОЗЖЕ listed (лист. мега-BDC рано ради
   earnings call) → «non-traded как source» может инвертироваться. Проверить
   матрицей порядка (День 1).
4. EQUITY-СТАДИЯ ПЕРЕВЁРНУТА: primary тест 3-й стадии = event study на ДАТЕ
   раскрытия source по акции target (информация публична с этого момента);
   события = существенные co-held markdowns (сотни) вместо target×quarter (~50×N).

## Ответы по Японии
- Архив: Yanoshin WEB-API (с 2009), date-range запросы, XBRL-фильтр, llms.txt;
  подтверждён янв-2025 живым запросом (День 1). Fallback: официальный JPX TDnet
  API = 5 лет истории, но корпоративный/платный (план Z).
- Цены: J-Quants free = daily, лаг 12 недель (ок для истории). Intraday: minute/tick
  с янв-2026 = платный add-on ¥5,500/мес поверх Light → вне бюджета.
  → гипотеза переформулирована: drift T+1..T+10, не минуты.
- «Кто медленный» = эмпирический вопрос → foreign ownership градиент как тест механизма.
- Triple-diff (идея ChatGPT, принята): already-bilingual Prime (placebo) ×
  late-translator Prime (treatment) × Standard (control) × before/after 04.2025.
  + parallel trends ДО теста; + контроль размера/ликвидности (группа 2 не случайна);
  + treatment как непрерывная величина (full/summary/лаг); + robustness без
  апр–мая 2025 (тарифный шок).

## Decision table бутылочных горлышек (пре-дата)
| Горлышко | ShadowNAV | Japan |
| История | высокая уверенность (EDGAR 2015+) | средняя→высокая (янв-2025 подтверждён) |
| Стоимость | 0 ₽ | 0 ₽ daily |
| Мощность | ст.1 высокая; ст.3 средняя (source-date design) | средне-высокая за 2–3 года событий |
| Время до ground truth | дни | дни при живом архиве |
| Прямота механизма | максимальная | через foreign-ownership градиент |
| Вендоры | ВЫСОКАЯ конкуренция | глобальных продуктов не найдено |
| Ценность при null | понижена | высокая (открытого аналога нет) |

## Финальные договорённости (после обмена с ChatGPT)
- Pre-data prior: Japan 52 / ShadowNAV 48
- Пивоты прекращены; заморожены: pre-earnings, RegimeShift, Machine-Flattery,
  Silent XBRL Revision (резерв при двойной смерти), hospital, UK, prediction
  markets, deobligations (резерв №3), supplier finance (feature)
- 72h showdown = проверка 4+4 смертельных неизвестных, не мини-стратегии
- Выбор по фактической decision table, не по 86/84
- Baseline-дисциплина: median already-filed co-holders; ML/агенты имеют право
  существовать только если бьют его OOS (в большинстве окон co-holder один →
  реальная планка = «добавляет ли что-то к марке первого файлера»)
- 3 страховки Клода: (а) 10 ручных прогнозов выбирать ГЕНЕРАТОРОМ до просмотра
  исходов; (б) в CAR вычитать BDC-корзину; (в) события Japan старше июня-2026
  из-за 12-недельного лага
- Победа при «оба живы»: более прямой переход new info → observable ground truth
  + скорость нормальной OOS-выборки

## Дополнительные идеи Клода (в бэклог ShadowNAV)
- N-PORT интервальных credit-фондов = второй сенсор (структурированный XML)
- H1b categorical: non-accrual/PIK propagation (robust to parsing noise)
- Календарь порядка отчётности → forecast-возможности известны ЗАРАНЕЕ на сезон
- Japan: «двойная стена» = language × value-up content на Standard
