# Finance Research Project — Day 1 Reconciled Push Pack

Дата фиксации: **2026-08-12**

Этот пакет нужен для одного действия: добавить в Git-репозиторий канонические
заметки Дня 1, исправленную таблицу, пререгистрацию и план Дня 2, не затерев
более свежие локальные скрипты Codex.

## Текущий статус

Флагман ещё **не выбран**. В 72-часовом showdown остаются два кандидата:

1. **ShadowNAV** — ранний mark одного BDC используется для nowcast ещё не
   опубликованного same-quarter mark/NAV позднего listed BDC по тому же facility.
2. **Japanese Language Wall** — проверка дневного post-announcement drift после
   пересмотров прогнозов в зависимости от English disclosure treatment,
   сегмента TSE и foreign ownership.

## Что День 1 подтвердил

- BDC действительно публикуют результаты не одновременно; многодневные окна есть.
- Часть ранних дат из первого Codex-скрипта была ложной: scheduling/dividend 8-K
  ошибочно принимались за results disclosures. В active CSV они исключены по
  содержимому EX-99; исправленное распределение остаётся provisional до ручной
  проверки возможных IR-only releases.
- Non-traded BDC в пилоте в основном публиковались позже listed BDC; использовать
  их как основной ранний sensor нельзя.
- Исторический индекс Yanoshin жив и отдаёт тысячи записей за тестовые месяцы
  2023–2025.
- Проверенные старые PDF/XBRL-ссылки Yanoshin/TDnet дают 404. Индекс и заголовки
  доступны, underlying documents пока не восстановлены.
- Флагман нельзя выбирать по старым scores 89/82, priors 52/48 или по количеству
  необработанных календарных пар.

## Канонический порядок чтения

1. `docs/01_DAY1_CANONICAL_FINDINGS.md`
2. `docs/02_PROJECT_DECISIONS.md`
3. `docs/03_PREREGISTRATION_V2.md`
4. `docs/04_DAY2_EXECUTION_PLAN.md`
5. `docs/05_CLAUDE_ARCHIVE_AUDIT.md`
6. `docs/06_CODEX_PUSH_PROMPT.md`
7. `spreadsheets/finance_project_day1_tracker_reconciled.xlsx`

## Важно при merge

В локальном репозитории уже есть более свежие файлы Codex:

- `day1_japan_archive_check.py`
- `day1_bdc_reporting_order.py`
- `find_nontraded_ciks.py`
- `reporting_order.csv`

Они **не входят в этот ZIP намеренно**. Их нельзя заменять старыми версиями из
архива Клода. При этом BDC reporting-order script нужно исправить так, чтобы
scheduling/dividend 8-K не считались публикацией результатов, затем пересчитать CSV.

## Не делать сейчас

- не строить UI;
- не писать агентов;
- не fine-tune модели;
- не считать Sharpe;
- не выбирать новый третий проект;
- не заявлять найденную alpha;
- не открывать outcomes ручной выборки до фиксации random seed и sample IDs.
