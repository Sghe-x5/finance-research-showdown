# Prompt for Codex — reconcile, commit and push Day 1

Ты работаешь в локальном Git-репозитории проекта. Рядом находится распакованная
папка `finance_project_day1_push_pack` с каноническими заметками и исправленной
таблицей. Выполни работу полностью, а не просто напиши инструкции.

## Цель

Сохранить и запушить Day 1 showdown так, чтобы:

- новые документы из push pack попали в репозиторий;
- более свежие локальные скрипты Codex НЕ были затёрты старыми файлами Клода;
- известные ошибки BDC reporting-order были исправлены;
- Япония была описана честно: index alive, tested old PDF/XBRL = 404;
- Git history содержала воспроизводимый frozen snapshot;
- никакие секреты, абсолютные локальные пути и рабочие credentials не попали в Git.

## 1. Сначала проинспектируй репозиторий

Выполни и покажи краткий итог:

```bash
git rev-parse --show-toplevel
git branch --show-current
git remote -v
git status --short
```

Не удаляй и не сбрасывай существующие изменения.

Если текущая ветка `main`/`master`, создай ветку:

```bash
git switch -c research/day1-showdown-reconciled
```

Если уже на рабочей feature-ветке, продолжай на ней.

## 2. Merge push pack

Найди распакованную папку по файлу `00_START_HERE.md`.

Добавь:

- `00_START_HERE.md` → корень репозитория как `DAY1_START_HERE.md`
- `docs/*` → `docs/research/`
- `spreadsheets/*` → `artifacts/day1/`
- `templates/*` → `data/templates/`
- `research_history/*` → `docs/research/history/`

Не копируй старые Python-скрипты из исторического snapshot в active showdown.

## 3. Сохрани новейшие локальные результаты Codex

Предпочтительны текущие локальные версии:

- `02_showdown/day1_japan_archive_check.py`
- `02_showdown/day1_bdc_reporting_order.py`
- `02_showdown/find_nontraded_ciks.py`
- `02_showdown/reporting_order.csv`

Не заменяй их более старыми версиями.

Убедись, что Japan script:

- использует `limit=10000`;
- сохраняет counts;
- явно фиксирует tested PDF/XBRL 404;
- не интерпретирует index availability как document availability.

## 4. Исправь BDC reporting-order classification ДО коммита

Текущий скрипт ошибочно принимал scheduling/dividend 8-K за результаты.

Известные regression cases:

- OBDC 2025Q2 `2025-07-01` — scheduling announcement, не results;
- GBDC 2025Q2 `2025-07-07` — scheduling announcement, не results.

Нужен `first_public_results_timestamp`, а не первый 8-K после period end.

Кандидат считается results/NAV disclosure только если подтверждено одно из:

- 8-K Item 2.02 с фактическими quarterly results;
- EX-99 earnings/NAV press release;
- официальный IR results release;
- 10-Q/10-K, если более раннего results disclosure не было.

Исключить:

- earnings-date announcements;
- dividend declarations;
- pure scheduling;
- Item 7.01 без фактических результатов/NAV.

Добавь regression tests/assertions хотя бы для OBDC и GBDC, чтобы эти даты больше
не возвращались как results.

После исправления пересчитай `reporting_order.csv` и summary:

- p25 / median / p75 window;
- >1d / >3d / >5d;
- exact timestamp source;
- verification status.

Если сетевой вызов временно не проходит, не выдумывай CSV. Сохрани исправленный
код, пометь CSV stale и напиши точную причину в Day 1 findings.

## 5. Обнови active docs

Обнови/создай:

- `README.md`
- `02_showdown/SHOWDOWN_TRACKER.md`
- `02_showdown/day1_findings.md`
- `02_showdown/PREREGISTRATION.md`

Используй как source of truth:

- `docs/research/01_DAY1_CANONICAL_FINDINGS.md`
- `docs/research/03_PREREGISTRATION_V2.md`
- sheet `Day1_Reconciliation` в reconciled workbook.

Обязательные формулировки:

- флагман не выбран;
- ShadowNAV windows exist, exact counts provisional until corrected results dates;
- non-traded-first core story refuted;
- Japan index alive;
- tested old documents/XBRL 404;
- Day 2 gates are exact facilities and recoverable numeric forecast revisions;
- dashboard scores/priors are not selection criteria.

## 6. Hygiene / security

Проверь:

```bash
rg -n "<local-home>/|api[_-]?key|secret|token|password|BEGIN .*PRIVATE KEY" .
find . -name '.DS_Store' -o -name '__pycache__' -o -name '*.pyc'
```

Не коммить:

- `.env`;
- API keys;
- реальные рабочие credentials;
- локальные absolute paths;
- downloaded raw datasets/DBs, если они большие;
- `.DS_Store`, `__pycache__`, `.pyc`.

Обнови `.gitignore` при необходимости.

SEC User-Agent email должен браться из env/config/example, а не быть
захардкоженным личным адресом в публичном репозитории. Добавь `.env.example`
без секретов, если нужно.

## 7. Проверки

Запусти минимум:

```bash
python3 -m py_compile \
  02_showdown/day1_japan_archive_check.py \
  02_showdown/day1_bdc_reporting_order.py \
  02_showdown/find_nontraded_ciks.py
```

Если есть tests:

```bash
python3 -m pytest -q
```

Также проверь, что CSV читается и имеет ожидаемые колонки.

Покажи краткий diff summary:

```bash
git diff --stat
git status --short
```

## 8. Commit

Предпочтительно два логичных коммита:

1. `fix: classify BDC result disclosures and refresh day-1 evidence`
2. `research: freeze reconciled day-1 showdown notes and preregistration`

Если изменения невозможно чисто разделить, сделай один:

`research: reconcile and freeze day-1 showdown`

Не amend существующие чужие коммиты и не force-push.

Создай annotated tag:

```bash
git tag -a showdown-day1-reconciled-2026-08-12 \
  -m "Frozen reconciled Day 1 evidence before manual outcomes"
```

## 9. Push

Запушь рабочую ветку и tag:

```bash
git push -u origin HEAD
git push origin showdown-day1-reconciled-2026-08-12
```

Если remote/auth отсутствует, не симулируй успех. Покажи точную ошибку и
минимальные команды, которые должен выполнить пользователь.

## 10. Финальный отчёт

В конце сообщи:

- branch;
- commit hash(es);
- tag;
- pushed remote;
- список добавленных/обновлённых файлов;
- какие tests прошли;
- пересчитаны ли BDC windows или CSV оставлен stale;
- любые blockers.

Не начинай Day 2 и не открывай target outcomes в этом задании.
