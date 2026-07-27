# Hop-two / hop-three resolution diagnosis

## Failing example

```text
In which town was the Apollo 11 crew member Neil Armstrong born?
```

Trusted FACTS available to the comparator:

```text
Apollo 11 — crewed_by → Neil Armstrong
Neil Armstrong — born_in → Wapakoneta
```

Correct answer text reaching the iteration engine:

```text
Wapakoneta
```

## Incorrect pre-fix behavior

`derive_question_target` scanned surface keywords without regard to grammatical
role. The phrase `crew member` matched the crew intent even though it only
qualifies Neil Armstrong:

| Stage | Pre-fix value |
| --- | --- |
| Derived question target | `intent=crew_members`, `canonical_relation=crewed_by`, `primary_subject=Apollo 11` |
| Raw extracted claim | `Neil Armstrong — born_in → Wapakoneta` |
| Conditioned claim | `Apollo 11 — crewed_by → Wapakoneta` |
| Grounded / aligned claim | `Apollo 11 — crewed_by → Wapakoneta` |
| Comparison result | `CONTRADICTED` (conflicts with trusted `crewed_by → Neil Armstrong`) |
| Target satisfaction | unsatisfied |
| Feedback | rewrite the contradicted crew attribute |
| Stop reason | eventually `MAX_ITERATIONS` |

## Expected target

```text
intent=birthplace
canonical_relation=born_in
primary_subject=Neil Armstrong
```

Expected conditioned / aligned claim:

```text
Neil Armstrong — born_in → Wapakoneta
```

## Corrected behavior

Intent selection now prefers the interrogative frame:

1. Interrogative phrase (`In which town` / `Where` / `Which company` …)
2. Head of the wh-noun phrase (town / company / state / crew member …)
3. Requested predicate of the *main* clause (`born`, `built`, `contains`, `flew` …), never a nested qualifier predicate (`launched`, `headquartered`, …)

Entity-description qualifiers such as `crew member` no longer override the
requested answer type. `condition_claims_to_question` also preserves claims that
already match the selected relation family, so a correct birthplace claim is
never rewritten into a crew relation.

## Why correct text previously reached `MAX_ITERATIONS`

The answer string was already correct. Internal bookkeeping forced it into the
wrong relation family, the comparator labeled that synthetic claim
`CONTRADICTED`, feedback demanded a rewrite that could not simultaneously satisfy
the hijacked crew target and the true birthplace fact, and the iteration loop
exhausted its budget at `MAX_ITERATIONS`.
