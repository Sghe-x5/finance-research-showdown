# Аудит папки Клода: что важно, что архивировать, что не использовать как current

## Сохранить и держать актуальным

### `00_project/PROJECT_OVERVIEW.md`

Полезен: цели, ограничения, два кандидата, общая архитектура.
Нужно обновить ссылкой на канонические документы этого пакета.

### `00_project/PITCH.md`

Полезен как черновик. Но фраза «если назвать один проект сегодня — ShadowNAV»
не является финальным решением. До конца showdown файл должен быть помечен
`PROVISIONAL`.

### `01_memos/graveyard.md`

Очень важен. Он предотвращает бесконечные pivots и повторную «перепродажу»
убитых идей. Сохранить как research history.

### `03_reference/methodology_rules.md`

Один из самых ценных файлов архива. Сохранить почти без изменений.

### `03_reference/data_sources.md`

Полезен, но обновить:

- Yanoshin historical index alive;
- tested old PDF/XBRL links return 404;
- `limit=10000`;
- BDC first-results classification caveat;
- local Codex scripts and generated CSV are current source.

### `02_showdown/PREREGISTRATION.md`

Очень важен по назначению, но его версия устарела. Заменить канонической
`docs/03_PREREGISTRATION_V2.md`; старую оставить только в history.

### `02_showdown/SHOWDOWN_TRACKER.md`

Сохранить, но переписать Day 1 facts по
`docs/01_DAY1_CANONICAL_FINDINGS.md`.

### `02_showdown/day1_findings.md`

Старый snapshot полезен для истории, но не canonical. Он был создан до проверки
404 и до выявления scheduling 8-K false positives.

## Исторические, не канонические

- `memo1_three_branches.md`
- `memo2_new_ideas.md`
- `memo3_shadownav_vs_japan.md`

Они полезны для интервью: показывают процесс убийства гипотез. Но claims и scores
из них нельзя использовать без проверки актуального canonical doc.

## Не использовать для overwrite

Скрипты из оригинального ZIP Клода:

- `day1_bdc_reporting_order.py`
- `day1_japan_archive_check.py`

Локальные версии Codex новее. В частности:

- Japan version использует `limit=10000`;
- local repo содержит `find_nontraded_ciks.py`;
- local repo содержит `reporting_order.csv`;
- BDC script всё ещё требует исправления false-positive scheduling 8-K.

Поэтому старые скрипты не включены в активную часть этого push pack.

## Что считать single source of truth после merge

1. `docs/01_DAY1_CANONICAL_FINDINGS.md`
2. `docs/03_PREREGISTRATION_V2.md`
3. `spreadsheets/finance_project_day1_tracker_reconciled.xlsx`
4. latest local Codex scripts + regenerated CSV
5. Git commit/tag of the frozen state
