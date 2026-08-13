# Методологические правила (действуют для любого флагмана)

1. LLM извлекает структурированные факты и evidence; вероятности считает
   отдельная калиброванная количественная модель. LLM не выдумывает P(x)=78%.
2. Только point-in-time данные. Ключ доступности = acceptance/publication
   datetime, никогда period_end.
3. Unique event IDs, дедупликация (amendments = отдельные строки), raw payload
   + hash хранится.
4. Никакого look-ahead: scaler fit только на train; prompts/models/version
   hashes сохраняются; contamination исторических LLM учитывается.
5. Реалистичные издержки: спреды, borrow, ликвидность, delistings, survivorship,
   ДИВИДЕНДНЫЙ CARRY BDC (10–12%) → только relative value.
6. Factor/industry-adjusted returns; для BDC — минус равновзвешенная корзина
   сектора, не stock−SPY.
7. Preregistered primary test: сигнал/окно/метрика фиксируются ДО просмотра
   результата. Правило выбора флагмана — тоже.
8. Power analysis обязателен; t=1.5 не доказательство; underpowered-стадии
   объявляются вспомогательными заранее.
9. Locked OOS + live forward test; каждый прогноз фиксируется до события
   (timestamp, версия, inputs, hash) в immutable journal.
10. Модель умеет говорить NO TRADE.
11. Запрещённые фразы: first in the world / nobody does it / guaranteed alpha /
    vendor vacuum. «Не нашли статьи» формулируется только как
    "I found no published study testing the complete chain".
12. Вендор-чек и статус регулирования — ДО проектирования любой идеи.
13. Baseline-дисциплина: сначала самый тупой baseline; ML/агенты получают право
    существовать, только если бьют его OOS.
14. Случайные выборки для ручных проверок — генератором, до просмотра исходов.
15. Кластеризация ошибок по всем осям общности (facility×quarter, manager,
    valuation agent).
16. Null-result допустим; проект обязан оставлять после null датасет/benchmark/
    engine/инфраструктуру.
17. До валидации измерения — никаких дашбордов и красивых интерфейсов.
