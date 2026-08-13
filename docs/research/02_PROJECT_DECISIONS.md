# Проектные решения, которые уже нельзя переобсуждать без новых данных

## Карьерная цель

Проект — не обещание автономной торговой стратегии. Он должен стать
**investment-research engineering product**:

- point-in-time ingestion;
- сложный proprietary/derived dataset;
- entity resolution;
- проверяемый LLM extraction;
- numerical impact model;
- evidence и uncertainty;
- analyst-ready research packet;
- отдельный честный alpha test.

Фондовый аналитик/PM может принимать финальное решение. Для роли research
engineer / quant developer это нормальный и сильный продукт.

## Финальные два кандидата до конца showdown

### ShadowNAV

Первый BDC раскрывает mark по facility за квартал Q; поздний listed BDC держит
тот же facility, но ещё не опубликовал Q results/NAV. Система nowcast'ит его mark,
Shadow NAV и distress flags.

Коммерческий мониторинг co-holder marks уже существует (SOLVE, Preqin и др.).
Заявляемая новизна только:

- first-reporter predictive layer;
- preregistered open validation;
- source-date pricing test;
- appraiser/manager fixed-effects research.

### Japanese Language Wall

TSE Prime получил обязательное English disclosure с апреля 2025, Standard — нет.
Система строит English-normalized dataset forecast revisions и тестирует drift.

Основной design:

- Prime already bilingual before mandate = placebo;
- Prime late/non-simultaneous translators = strong treatment;
- Standard = no treatment;
- before/after April 2025;
- interaction with foreign ownership;
- event-level full/summary/none and English lag.

## Замороженные направления минимум на месяц

- generic pre-earnings;
- PIT consensus collector as flagship;
- Machine-Flattery / Model Monoculture alpha;
- standalone RegimeShift;
- Silent XBRL Revision;
- hospital MRF;
- UK private accounts;
- prediction markets;
- government deobligations;
- supplier finance;
- новые «идеи №37».

Они могут вернуться только если оба текущих проекта провалят заранее заданные gates.

## Общие методологические правила

1. Point-in-time availability timestamp, не period end.
2. LLM извлекает facts/evidence; вероятности считает quant model.
3. Unique event IDs, raw payloads и hashes.
4. Preregistration до outcomes.
5. Random manual sample до открытия target outcomes.
6. Самый простой baseline первым.
7. Locked OOS, walk-forward, no random time split.
8. Realistic spreads, borrow, dividends, liquidity and survivorship.
9. Returns adjusted by relevant sector/factor benchmark.
10. NO TRADE / insufficient evidence — допустимый output.
11. Не писать first in the world / nobody does it / guaranteed alpha.
12. До measurement validity: no UI, agents, fine-tune or production ingestion.
