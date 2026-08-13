# Day 1 — канонические находки и исправления

Дата: **2026-08-12**

Это канонический документ Дня 1. Он заменяет конфликтующие формулировки в
старых меморандумах, первом Excel и первоначальных версиях скриптов.

## 1. ShadowNAV: что уже известно

### 1.1. Временные окна существуют

BDC раскрывают квартальные результаты в разные даты. После удаления очевидных
ложных ранних событий многодневные source→target окна остаются.

После content-based проверки SEC EX-99 получено исправленное рабочее
распределение для пяти полных кварталов:

- 525 упорядоченных пар между 15 listed BDC;
- p25 / median / p75 = `1.993 / 5.999 / 12.988` дня;
- `>1d = 451`, `>3d = 343`, `>5d = 291`;
- OBDC 2025Q2 `07-01` и GBDC 2025Q2 `07-07` исключены как scheduling
  announcements после проверки EX-99;
- CSV сохраняет точные acceptance timestamps, accession/source URL, тип события,
  verification status и exclusion reason.

**Канонический вывод:** окна есть и их Day 1 SEC/EX-99 distribution пересчитан,
но exact distribution остаётся provisional до ручной проверки возможных более
ранних IR-only releases. Это не число сделок и не доказательство сигнала:
exact-facility gate остаётся открытым.

### 1.2. Правильный event timestamp

Для каждого BDC нужен:

`first_public_results_timestamp`

Это минимум из:

- 8-K Item 2.02 с earnings results;
- EX-99 earnings release / NAV disclosure;
- официальный IR press release;
- 10-Q/10-K acceptance timestamp, если более раннего раскрытия не было.

Не считаются results events:

- анонс даты будущего earnings call;
- dividend declaration;
- scheduling 8-K;
- обычный Item 7.01 без фактических результатов/NAV;
- filing calendar placeholder.

Same-day пары упорядочиваются по точному времени и market session.

### 1.3. Non-traded BDC

Codex-пилот:

- все 20 non-traded наблюдений были позже медианного listed BDC;
- медианная задержка около 9 дней;
- 17 из 20 появились после как минимум 14 из 15 listed BDC.

Следствие:

- история «non-traded BDC как основной ранний sensor» опровергнута;
- отдельные `non-traded → very-late listed target` окна могут существовать и
  проверяются только как нишевой поднабор.

### 1.4. Главный незакрытый gate

Пока не известно, сколько календарных окон содержат **exact same facilities**.

Same borrower недостаточно. Минимальные поля матча:

- canonical borrower;
- facility type;
- lien/seniority;
- currency;
- base rate;
- spread;
- maturity;
- principal/par;
- при наличии — tranche/commitment details.

До этого нельзя говорить о ShadowNAV signal.

### 1.5. Frozen primary outcome

Primary H1:

> Улучшает ли ранний same-quarter co-holder mark прогноз ещё не опубликованного
> same-quarter mark позднего target по тому же facility?

Цель:

- `FV / par`;
- отдельно entry component `cost / par`;
- отдельно post-entry component `(FV - cost) / par`.

Baselines:

1. target mark unchanged;
2. target own mark momentum;
3. median already-filed co-holders;
4. earliest available co-holder;
5. categorical distress only.

Secondary:

- PIK / non-accrual / restructuring propagation;
- Shadow NAV aggregation;
- source-date target relative return.

Stock return не является primary ground truth.

## 2. Japan Language Wall: что уже известно

### 2.1. Исторический индекс жив

После `limit=10000` Codex получил:

| Период | items | forecast-revision title matches |
|---|---:|---:|
| 2023-01-10—2023-01-31 | 4 031 | 313 |
| 2023-07-01—2023-07-31 | 5 380 | 237 |
| 2024-01-10—2024-01-31 | 4 027 | 296 |
| 2024-07-01—2024-07-31 | 5 848 | 229 |
| 2025-01-10—2025-01-31 | 4 162 | 304 |
| 2025-07-01—2025-07-31 | 6 216 | 244 |

Это подтверждает доступность исторического индекса, timestamps, security codes и
японских заголовков.

### 2.2. Underlying documents не подтверждены

Все протестированные старые `document_url` и `url_xbrl` после redirect вернули 404.

Следствие:

- нельзя писать «исторические документы доступны»;
- title/index sample достаточен для подсчёта потока, но недостаточен для
  извлечения old/new forecast numbers;
- Day 2 должен найти воспроизводимый альтернативный источник:
  issuer IR, J-Quants statements, IR Bank, Wayback или другой архив.

### 2.3. Начальный класс событий заморожен

Только:

`業績予想の修正` — пересмотр earnings forecast.

Не смешивать пока:

- dividends;
- buybacks;
- M&A;
- value-up;
- special gains/losses.

Нужные поля:

- old revenue / operating profit / ordinary profit / net income forecast;
- new values;
- percentage change;
- publication timestamp;
- Prime / Standard / Growth;
- Japanese document;
- English full / summary / none;
- English publication lag;
- prior English-disclosure behavior;
- foreign ownership;
- prices `T0 / T+1 / T+3 / T+5 / T+10`.

### 2.4. Цена

J-Quants Free имеет 12-недельную задержку. Для исторического теста использовать
события старше задержки. Бесплатно нельзя проверить intraday language effect.

Primary Japan question — дневной drift, не минуты.

## 3. Что нельзя считать результатом

- 407 окон >3 дней и median 13.3 дня из первоначального загрязнённого CSV;
- workbook scores 89/82;
- priors 52/48;
- число заголовков forecast revision как число пригодных financial events;
- любой `same borrower` как exact facility;
- отсутствие PDF по двум ссылкам как доказательство отсутствия всех архивов;
- существование co-holder marks как доказательство equity alpha.

## 4. Day 1 final status

| Track | Status | Fatal next gate |
|---|---|---|
| ShadowNAV | Alive | Exact same facilities + manual OOS nowcast vs baseline |
| Japan | Alive but blocked on content | Recover old/new numeric forecasts and JP/EN treatment |
| Flagship | Not selected | Day 2/3 evidence only |
