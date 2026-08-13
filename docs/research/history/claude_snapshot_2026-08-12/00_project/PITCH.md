# Питчи и материалы для резюме

## Если нужно назвать один проект СЕГОДНЯ — называть ShadowNAV
(история уже в EDGAR → результат за 8–12 недель; private credit — самая горячая
тема в фондах; бухгалтерский ground truth; агенты не декоративные)

## Одно предложение (EN)
"We use the first public fair-value mark from one private-credit holder to infer
the still-unreported NAV and earnings impact at listed BDCs holding the same
facility — with an agent pipeline that rebuilds a point-in-time loan-level
database from SEC filings."

## Одно предложение (RU)
Используем первую опубликованную оценку кредита у одного private-credit фонда,
чтобы предсказать ещё не раскрытый NAV других публичных BDC, держащих тот же кредит.

## Строка в CV
"Built ShadowNAV: an LLM-agent pipeline that extracts and entity-resolves
loan-level holdings across US BDC filings, and a preregistered nowcasting model
predicting still-unpublished same-quarter fair-value marks from earlier co-holder
disclosures, benchmarked against naive baselines with out-of-sample validation."

## Pitch фонду (полный, EN)
"We rebuild a point-in-time, loan-level database of every Schedule of Investments
filed by US BDCs, resolve borrowers and facilities across lenders, and exploit
asynchronous quarterly reporting: when an early filer discloses its mark on a
shared facility, we nowcast the still-unpublished same-quarter mark of later
filers, aggregate to a Shadow NAV, and test on a preregistered basis whether
(a) the nowcast beats naive baselines out of sample and (b) listed BDC equities
underreact to early co-holder disclosures. Stage (a) is tested against an
objective accounting ground truth with thousands of observations; stage (b) is
deliberately treated as lower-powered and reported as such."

## Обязательный честный дисклеймер (спросят про SOLVE)
"The monitoring layer — who holds what and at what mark — is commercially
available (SOLVE, Preqin). We test whether the predictive layer and the
equity-pricing layer still contain information, which I found no published
study doing for the complete chain."

## Чего НЕЛЬЗЯ обещать/писать
first in the world · nobody does it · mathematically guaranteed alpha ·
vendor vacuum · «мы нашли данные, которые никто не соединяет» ·
прогноз движения цены в день earnings как главное обещание

## Если флагманом станет Japan — заготовка
"April 2025 gave Japan a clean natural experiment: TSE Prime became subject to
mandatory simultaneous English disclosure while Standard did not. We build an
open English-normalized dataset of TDnet timely disclosures and test, in a
triple-difference design interacted with foreign ownership, whether the language
barrier still prices in as post-announcement drift."

## Процесс как часть питча (работает на любой исход)
"We generated ~35 hypotheses, adversarially killed 33 across three review rounds
(vendor checks, regulatory-status checks, identification-design checks),
preregistered selection criteria, and let 72 hours of raw data pick the flagship."
