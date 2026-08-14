# Полная история Finance Research Showdown

Дата актуализации: **14 августа 2026 года**.

Этот документ подробно объясняет, что именно было сделано, зачем менялся дизайн,
какие результаты оказались ошибочными или исследовательски слабыми, что было
исправлено и где проходит текущая граница проекта. Это не рекламный pitch и не
попытка спрятать неудачи. Наоборот, неудачные пилоты сохранены как часть
воспроизводимого исследовательского следа.

## 1. С чего начинали

Изначальная задача была ограничена 72-часовым evidence-first showdown между
двумя финансовыми research-проектами:

1. **ShadowNAV** — использовать более раннюю квартальную оценку одного и того же
   private-credit facility у одного BDC, чтобы предсказать ещё не опубликованную
   оценку более позднего listed BDC.
2. **Japanese Language Wall** — проверить, связан ли post-announcement drift
   после японских пересмотров прогноза с отсутствием или задержкой английского
   раскрытия.

На старте были введены жёсткие границы:

- сначала доказать доступность и корректность данных;
- не строить UI, агентные системы, торговую стратегию или ML до простых
  baseline-тестов;
- не выбирать красивые примеры после просмотра target outcomes;
- фиксировать seeds, IDs, SHA-256 и момент доступности информации;
- предпочитать null или остановку проекта красивому, но нечестному результату;
- не коммитить raw ZIP, credentials, `.env`, API keys и private blind mappings.

## 2. День 1 — проверка существования данных

### 2.1. BDC reporting order

Первым вопросом было не «есть ли alpha», а «существуют ли вообще окна между
публикациями разных BDC». Для 15 listed BDC были собраны события первого
публичного раскрытия квартальных результатов:

- 8-K Item 2.02;
- EX-99 earnings/NAV release;
- официальный IR release;
- 10-Q/10-K только как fallback, если ничего более раннего не найдено.

Первоначальная классификация давала false positives: анонсы будущей даты
earnings call, scheduling notices и dividend-only 8-K выглядели как ранние
results. Логику исправили через content-based проверку EX-99. В частности:

- OBDC `2025-07-01` для 2025Q2 — не results;
- GBDC `2025-07-07` для 2025Q2 — не results;
- будущий FSK scheduling notice также закреплён regression test.

После очистки пяти кварталов получили:

| Показатель | Значение |
|---|---:|
| Упорядоченные source→target окна | 525 |
| p25 | 1.993 дня |
| Медиана | 5.999 дня |
| p75 | 12.988 дня |
| Окна длиннее 1 дня | 451 |
| Окна длиннее 3 дней | 343 |
| Окна длиннее 5 дней | 291 |

Вывод Дня 1: временные окна существуют, но окно между фондами ещё не означает,
что оба держат **один и тот же facility**. Поэтому это только data-availability
gate, а не результат стратегии.

### 2.2. Non-traded BDC

Была отдельно проверена гипотеза, что non-traded BDC являются ранними сенсорами.
В пилоте все 20 наблюдений non-traded фондов были позже медианного listed BDC;
медианная задержка составила около девяти дней, а 17 из 20 раскрылись после как
минимум 14 из 15 listed BDC.

Основная история `non-traded-first` была опровергнута. Non-traded фонды позже
остались допустимыми только как потенциальные source в отдельных окнах, а не как
центральный механизм.

### 2.3. Японский исторический индекс

Неофициальный Yanoshin/TDnet index был проверен на шести периодах 2023–2025.
После исправления лимита API индекс возвращал тысячи записей и сотни заголовков
forecast revisions в каждом тестовом месяце. Значит, исторические timestamps,
security codes, event IDs и японские titles доступны.

Но все протестированные старые `document_url` и `url_xbrl` после redirect дали
HTTP 404. Поэтому уже в День 1 было зафиксировано различие:

- **исторический индекс жив**;
- **историческое численное содержимое документов не доказано**.

Без old/new revenue, operating profit, ordinary profit и net income нельзя
проводить полноценный event study по силе revision.

### 2.4. Freeze Дня 1

Канонические выводы и исправленный reporting order были заморожены:

- branch: `research/day1-showdown-reconciled`;
- tag: `showdown-day1-reconciled-2026-08-12`;
- tag commit: `78de52b`.

На этом этапе оба трека считались живыми, а флагман не был выбран.

## 3. День 2 — первый mechanism pilot

### 3.1. Официальный SEC flat-file pipeline

Вместо массового scraping filings использовали официальные SEC BDC Data Sets.
Downloader сначала открывал официальную страницу, обнаруживал ссылки на архивы,
инвентаризировал ZIP и только затем выбирал таблицы. Имена файлов заранее не
предполагались.

Для пилота были доступны архивы 2025Q3 и 2025Q4. В Git сохранили URL,
retrieval timestamp, byte size, ZIP inventory, CRC, schema/header hashes и
SHA-256. Сами raw ZIP и нормализованный кеш остались вне Git.

Parser:

- соединял `sub.tsv` и `soi.tsv` по `adsh`;
- использовал acceptance timestamp как время доступности;
- не подменял время доступности датой конца квартала;
- сохранял raw provenance и source concepts.

Масштаб пилота:

| Стадия | Количество |
|---|---:|
| Raw SOI rows для 19 фондов | 73 845 |
| Нормализованные investment/facility rows | 54 285 |
| Cross-BDC borrower-blocked candidate pairs | 13 672 |

### 3.2. Первый matching benchmark и его проблема

Facility matcher сравнивал borrower, debt/equity, tranche/facility type, lien,
currency, reference-rate family, spread, maturity, funded status и acquisition
date. Однако первоначальный benchmark не был независимым: adjudication code по
умолчанию присваивал `manual_label = predicted_label`, кроме небольшого списка
corrections.

Из-за этого механические 100% precision и 100% recall не являются измеренной
точностью. Они были позже явно понижены до `upper bound by construction`.

Отдельная проблема: candidate blocking начинался с exact normalized borrower.
Значит, recall существовал только внутри уже найденного borrower block и ничего
не говорил о потерянных aliases.

### 3.3. Честный freeze и невалидный confirmatory вывод

До reveal были зафиксированы:

- 45 eligible IDs для 2025Q3;
- случайные 15 observation IDs с seed `20260813`;
- eligible-ID hash;
- frozen-sample hash;
- contaminated Auctane и Medallia исключены из estimates.

Git freeze действительно предшествовал появлению outcomes. Но после freeze
определение adjusted predictor было изменено, а строки ещё содержали повторные
XBRL slices вместо агрегированного economic facility. Поэтому confirmatory
интерпретация была утрачена, даже несмотря на честный порядок коммитов.

### 3.4. Что показал Day 2 reveal

Ошибки измерялись в percentage points facility mark:

| Метод | n | MAE, pp |
|---|---:|---:|
| B0: target mark unchanged | 15 | 0.3270 |
| B2: median уже раскрывшихся co-holders | 15 | 0.3901 |
| B3: earliest exact co-holder | 15 | 0.8101 |
| B4: previous-quarter cross-lender median | 15 | 0.5648 |
| Post-freeze prior-gap-adjusted source | 15 | 0.0680 |

Наивное копирование первого co-holder проиграло persistence: `0.8101` против
`0.3270`. Красивое `0.0680` также не пережило sensitivity audit:

- 13 из 15 adjusted predictions совпадали с B0;
- всё преимущество создавал один borrower — PetVet Care Centers;
- без PetVet MAE обоих методов равен `0.0696 pp`;
- leave-one-borrower-out полностью убирает преимущество;
- sample содержит только один квартал, два source и два target фонда.

Честный вывод: Day 2 не доказал сигнал. Он показал один интересный PetVet case и
одновременно обнаружил unit-of-analysis bug, post-freeze formula change и
невалидный matching benchmark. Старый frozen sample не исправлялся задним числом
и сохранён как **failed exploratory pilot**.

### 3.5. Japan Day 2

Были сохранены восемь supplied numeric seeds и случайно выбраны ещё 32 события
из universe 678. Все новые TDnet links дали 404; IRBank probe дал 403; J-Quants
не был настроен; Wayback в этом ограниченном пилоте не выполнялся.

Поэтому корректный показатель был:

- независимое восстановление: `0/32`;
- supplied provisional seeds: `8`;
- общий provisional denominator: `8/40`, но не независимые `8/8`.

Treatment fields не были воспроизводимо заполнены, price event study не запускался.

### 3.6. Freeze Дня 2

- freeze commit: `a495f39`;
- results/audit commit: `0cb5f8c`;
- branch: `research/day2-mechanism-pilot`;
- tag: `showdown-day2-mechanism-2026-08-13`.

Тег сохраняет исход пилота, включая его ошибки; он не переписывался.

## 4. День 3 — ремонт измерительного слоя до нового reveal

Цель Дня 3 была не получить новый красивый MAE, а исправить измерение до того,
как target outcomes снова станут видимыми.

### 4.1. Новая единица наблюдения

XBRL slices были агрегированы до economic facility:

`BDC × quarter × borrower × facility/tranche × lien × currency × reference rate × spread × maturity × funded status`.

Внутри одного BDC разные facilities больше не объединялись автоматически по
25 bp tolerance или maturity month. Cross-lender tolerances оставались только
на matching stage. UNKNOWN-поля не использовались для агрессивного merge.

Результат основной агрегации: **188 999 economic facilities** по восьми SEC
archives. Были созданы отдельные audit samples для 100 multi-lot groups и 100
строк, удалённых как issuer totals. Эти review-файлы не получили автоматические
human labels.

### 4.2. Расширенный reporting calendar

Календарь был расширен с 2025-only назад до report periods 2023Q4–2025Q3.
Для 19 фондов сохранили явную строку на каждый fund×period, включая возможный
missing status.

Итог:

- expected: 152;
- verified: 152;
- missing: 0;
- periodic filing fallback: 100;
- excluded scheduling candidates: 64;
- filing lag: 14–81 день, медиана 37.5 дня.

Candidate search window составлял 0–120 дней после period end. Интервал 20–80
дней был диагностикой, а не hard filter, чтобы не потерять поздние 10-K.

### 4.3. Pre-reveal eligibility и power guard

Eligibility использовала только:

- source current public facility;
- source prior public facility;
- target prior public facility;
- verified reporting order;
- момент, когда source facility mark реально стал публичным.

Target same-quarter outcome не читался. Movement определялся только на
агрегированном facility:

`abs(source_current_mark - source_prior_mark) >= 0.005`.

Все 11 ранее просмотренных borrowers были исключены во всех периодах: PetVet,
MRI Software, Anaplan, Viant Medical, Hyland Software, Fortis Solutions, PPV
Intermediate, Ping Identity, Pye-Barker, Auctane и Medallia.

| Report period | Eligible | Movement observations | Unique movement facilities |
|---|---:|---:|---:|
| 2023Q4 | 0 | 0 | 0 |
| 2024Q1 | 24 | 11 | 10 |
| 2024Q2 | 31 | 14 | 13 |
| 2024Q3 | 33 | 9 | 8 |
| 2024Q4 | 9 | 1 | 1 |
| 2025Q1 | 13 | 2 | 2 |
| 2025Q2 | 10 | 3 | 3 |
| 2025Q3 | 11 | 4 | 4 — development, не входит в guard |

Untouched independent total = **37**, то есть planning guard `>=20` пройден.
Это разрешает только планирование. Freeze и reveal остаются запрещены.

### 4.4. Почему наблюдений теряется так много

Был построен explicit eligibility funnel из 1 410 180 directional
source-facility/other-listed-target possibilities. Главные потери:

1. ограниченный universe из 19 фондов — около **49.8%**;
2. слабое XBRL facility tagging — около **42.9%**;
3. borrower matching — около **6.8%**.

В восьми архивах обнаружено 186 BDC CIK. Предварительный screen нашёл 87
кандидатов для возможного расширения, включая 21 дополнительный listed target.
Ни один из них автоматически не добавлен: reporting calendar и независимость
movement events ещё нужно подтверждать отдельно.

### 4.5. Эволюция blind facility benchmark

Blind-файл менялся версиями, но старые версии не удалялись:

1. `blind_facility_pairs.csv` — 60 simple-random pairs; sampling design не
   измерял high-confidence precision и был помечен
   `superseded_wrong_sampling_design`.
2. `blind_facility_pairs_v2.csv` — правильные 60/30/30 hidden strata, но позже
   был superseded из-за parser/join omissions, обнаруженных field-lineage audit.
3. `blind_facility_pairs_v3.csv` — текущий clean-review file после ремонта.

V3 содержит:

- 60 hidden predicted same-facility/high;
- 30 hard same-borrower/different-facility;
- 30 uncertain/alias/distractor;
- randomized left/right order;
- ни одного из 11 development borrowers;
- никаких predicted labels, confidence scores или row-level strata.

Private mapping хранится только в ignored path. В Git находится лишь его hash и
aggregate 60/30/30 counts. Текущий публичный SHA-256:

`f4ec256bf4502f5cb6979ff218d3b5457481f0ae21bdb75841d4bb3c1d357c2b`.

Alias benchmark содержит 30 случайных ARCC debt borrowers и 128 shuffled
OBDC/NMFC candidate rows. Scores также скрыты. Его SHA-256:

`d37f5daeb4eb6cee9e4ddb2e7690978a6ac899c30305b4fda268bb7424a8b64e`.

### 4.6. Field-lineage audit

После того как в blind CSV четыре поля оказались пустыми на 100%, были проверены
все десять members каждого из восьми официальных SEC ZIP, включая `soi.tsv`,
`txt.tsv`, `num.tsv`, dimensions и taxonomy concepts. Значения не извлекались
эвристически из identifier text.

| Поле | Диагноз | Что нашли и исправили |
|---|---|---|
| maturity | `join_loss` | Supporting `InvestmentMaturityDate` / `InvestmentDueDate` не были joined; восстановлено 2 320 exact-key значений |
| currency | `source_absent` | В схеме axis есть, но для qualifying facility population явно tagged values отсутствовали |
| reference_rate | `parser_loss` + малый join loss | 159 raw rows не переживали old canonicalizer; восстановлены только 9 однозначных benchmark families, без выдумывания из prose |
| acquisition_date | `join_loss` | Supporting facts не были joined; восстановлено 3 349 exact-key значений |

Aggregation и blind export сами значения не теряли. После ремонта candidate
universe оказался byte-identical: восстановленные поля относились к HTGC/TSLX и
не встречались в overlapping borrower pairs текущего sample. Поэтому в v3 эти
четыре поля всё ещё пусты, но теперь это **аудированный information ceiling**, а
не неизвестный pipeline bug. Будущий matcher обязан уметь `uncertain/abstain` и
показывать coverage и abstention rate, а не только precision.

### 4.7. Manager map и fallback audit

По официальным filings построена canonical manager map для всех 19 BDC.
Подтверждены, среди прочих:

- ARCC / ASIF → Ares Management;
- OBDC / OCIC → Blue Owl Credit;
- BCRED / BXSL → Blackstone Credit & Insurance.

Manager overlap:

| Layer | Same-manager | Cross-manager |
|---|---:|---:|
| Full candidate universe | 18 252 | 22 088 |
| Blind v3 | 84 | 36 |
| Eligible pre-reveal | 0 | 131 |
| Untouched movement observations | 0 | 40 |
| Untouched unique movement facilities | 0 | 37 |

Cross-manager movement count также проходит guard 20, поэтому именно
cross-manager разрешён как будущий primary preregistration stratum. Это всё ещё
не разрешение на freeze.

Все 100 periodic fallback rows были проверены на более ранние 8-K/EX-99. Ни
одного более раннего exact facility mark или target results cutoff не нашли:

- target cutoff shifted: 0/100;
- source mark timestamp shifted: 0/100;
- movement count до/после: 37/37.

### 4.8. Japan valid-window repair и итоговый статус

Первый Day 3 gate унаследовал старое окно 2023–июль 2024 и был признан
`invalid_window_design` до recovery: оно лежало вне rolling history бесплатного
J-Quants.

Universe пересобрали до попыток восстановления за фиксированное окно
`2024-09-01…2026-05-15`, используя только title/metadata filters:

- raw revision titles: 4 448;
- clean intent events: 3 999;
- excluded dirty titles: 449;
- frozen sample: 20;
- seed: `20260813`;
- sample ID hash:
  `3a510bef6cfe937ac6eb192fef87ff311ac85826927fdd30053a9586f3cdc5a6`.

Failed rows не заменялись. Финальный machine-phase status:

- historical TDnet documents: 0/20;
- Wayback snapshots: 0/20;
- issuer IR: не выполнялся в масштабе;
- J-Quants: доступ блокировался CDN из региона исследователя;
- complete scalable numeric recovery: не продемонстрирован.

Поэтому Japan demoted to a live-data product **under current access, budget and
licensing constraints**. Это не утверждение, что legal path вообще не существует.
Трек можно реактивировать через рабочий J-Quants, licensed historical TDnet,
institutional data, масштабируемый issuer-IR recovery или prospective live
collection. Сохранены 2023–2026 index, timestamps, IDs, titles и event classes.

## 5. Человеческая граница после машинной фазы

Машина не должна сама разметить собственный benchmark. Поэтому после commit
`60644ce`:

- Reviewer A выполнил blind facility labeling вне репозитория;
- labels не передавались Codex и отсутствуют в Git;
- private facility/alias keys не открывались и не копировались;
- canonical v3 и alias CSV остаются unlabeled и byte-stable;
- будущие clean reviewers получают только публичные копии файлов.

После независимых разметок люди должны сравнить disagreements, посчитать
precision/coverage/abstention и принять решение о preregistration v3. Codex не
имеет права самостоятельно перейти к reveal.

## 6. Что сейчас можно и нельзя утверждать

| Формулировка | Статус |
|---|---|
| BDC reporting windows существуют | Подтверждено |
| Non-traded BDC обычно раскрываются первыми | Опровергнуто в пилоте |
| Наивный earliest co-holder лучше persistence | Не подтверждено; в Day 2 проиграл |
| Adjusted ShadowNAV MAE = 0.068 pp — общий сигнал | Запрещено: эффект целиком PetVet и формула менялась после freeze |
| Есть минимум 20 pre-reveal movement facilities для планирования | Подтверждено: 37 untouched cross-manager facilities |
| Matcher имеет precision >=95% | Пока неизвестно; нужны независимые blind labels |
| ShadowNAV доказал alpha | Нет |
| Japan historical index доступен | Да |
| Старые TDnet PDF/XBRL доступны | Нет в протестированных ссылках: 404 |
| Для Japan доказан масштабируемый исторический numeric recovery | Нет при текущих ограничениях |
| Флагман окончательно выбран | Нет |

## 7. Git-хронология и зачем нужны checkpoint'ы

| Commit | Смысл |
|---|---|
| `b35443d` | Исправлена классификация BDC results и обновлены Day 1 evidence |
| `78de52b` | Заморожены канонические Day 1 notes и preregistration |
| `a495f39` | Добавлен SEC facility pipeline и до reveal зафиксированы Day 2 IDs |
| `0cb5f8c` | Зафиксированы Day 2 results, Japan recovery и честные caveats |
| `1b51413` | Начат ремонт measurement layer и Day 3 audits |
| `3bc421e` | Заморожены valid-window Japan gate и начальный movement guard |
| `255f693` | Записаны pre-key archive attempts для Japan |
| `4ecf665` | Ужесточены blind exclusions и recovery provenance |
| `00ee149` | Исправлена economic aggregation и sampling design benchmark v2 |
| `05f982b` | Расширен reporting calendar и закрыта machine pre-reveal phase |
| `60644ce` | Исправлен field lineage, создан blind v3, проведены manager/fallback audits |
| `ceeb566` | Репозиторий получил актуальную навигацию, reviewer guide и GitHub CI |

Frozen tags:

- `showdown-day1-reconciled-2026-08-12`;
- `showdown-day2-mechanism-2026-08-13`.

Day 3 results tag намеренно отсутствует, потому что нового reveal не было.

## 8. Как организован репозиторий после уборки

- root `README.md` — короткая публичная витрина и текущий статус;
- этот файл — подробная история на русском;
- `docs/research/README.md` — карта канонических, frozen и historical документов;
- `data/README.md` — какие outputs current, какие superseded и почему;
- `scripts/README.md` — разница между frozen Day 2 и corrected Day 3 code;
- `REVIEWER_GUIDE.md` — независимая разметка без private keys и leakage;
- `.github/workflows/ci.yml` — tests, compile и tracked-file hygiene;
- `.github/PULL_REQUEST_TEMPLATE.md` — checklist исследовательской целостности.

Ни один Day 1/Day 2 tag, research CSV, blind CSV или private mapping ради этой
уборки не перемещался и не переписывался.

## 9. Точная следующая развилка

До нового freeze одновременно должны выполниться три условия:

1. независимый blind benchmark проходит заранее установленный precision gate;
2. после всех exclusions сохраняется не менее 20 независимых movement events;
3. финальная preregistration v3 утверждена людьми до просмотра outcomes.

Если matching не проходит — matcher ремонтируется, но outcomes не открываются.
Если matching проходит — люди решают, достаточно ли текущих 37 events или нужно
расширить universe. Только после этого возможны новый frozen sample и отдельный
reveal commit. До такого решения проект остаётся в статусе **pre-reveal**.
