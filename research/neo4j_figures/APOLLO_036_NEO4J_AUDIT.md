# Apollo hop_036 Neo4j audit

Generated (UTC): 2026-08-07T04:48:15.973035+00:00

Read-only inspection of live Neo4j. No relationships were created, deleted, or updated.

## Execution IDs beginning with `apollo_hop_036__`

- `apollo_hop_036__20260727T205852Z__c2d8a77c` **← preferred (July 27 official)**
- `apollo_hop_036__20260803T015249Z__e3c39c61` (August repeat; not used for figures)
- `apollo_hop_036__20260803T023440Z__d3fff44b` (August repeat; not used for figures)

## Selection

Selected execution: `apollo_hop_036__20260727T205852Z__c2d8a77c`

Reason: This is the July 27 official Apollo run for `apollo_hop_036`. It contains 46 FACT and 11 CLAIM relationships across iterations 0–2, including NO_EVIDENCE claims that document a real revision sequence ending in a SUPPORTED terminal claim `Chesapeake Bay — opens_into → Atlantic Ocean`. August repeats mirror the same structure and were not needed.

## Audit: `apollo_hop_036__20260727T205852Z__c2d8a77c`

- FACT count: **46**
- CLAIM count: **11**
- CLAIM labels: {'SUPPORTED': 9, 'NO_EVIDENCE': 2}
- Unique iterations: [0, 1, 2]
- Earlier-iteration CLAIMs coexist: **True**
- Sufficient for revision-sequence visuals: **True**

### CLAIMs by sub_question_id

- sub_question_id=1: 11

### CLAIMs by (sub_question_id, iteration, label)

- (sq=1, iter=0, NO_EVIDENCE): 1
- (sq=1, iter=0, SUPPORTED): 4
- (sq=1, iter=1, NO_EVIDENCE): 1
- (sq=1, iter=1, SUPPORTED): 2
- (sq=1, iter=2, SUPPORTED): 3

### Unique FACT triples

- `Apollo 11` — `used_as_command_module` → `Columbia`
- `Apollo 11` — `used_as_lunar_module` → `Eagle`
- `Apollo 11` — `was_crewed_by` → `Neil Armstrong`
- `Apollo 11` — `was_launched_by` → `Saturn V`
- `Apollo 11` — `was_part_of` → `Apollo Program`
- `Apollo Missions` — `includes` → `Apollo 11`
- `Apollo Program` — `was_preceded_by` → `Gemini Program`
- `Atlantic Ocean` — `is_part_of` → `Global Ocean`
- `Boeing` — `assembled_at` → `Michoud Assembly Facility`
- `Capitol Hill` — `overlooks` → `National Mall`
- `Chesapeake Bay` — `opens_into` → `Atlantic Ocean`
- `Columbia` — `is_preserved_at` → `National Air and Space Museum`
- `Eagle` — `has_descent_stage_located_on` → `Moon`
- `Earth` — `is_studied_by` → `Lunar Geology`
- `Emergency Procedure` — `is_documented_in` → `Gemini 8 Mission Report`
- `Gemini 8` — `was_commanded_by` → `Neil Armstrong`
- `Gemini 8 Mission Report` — `is_archived_by` → `NASA`
- `Gemini Program` — `included` → `Gemini 8`
- `Global Ocean` — `is_studied_by` → `Oceanography`
- `Gulf Coast region` — `borders` → `Gulf of Mexico`
- `Gulf of Mexico` — `is_connected_to` → `Atlantic Ocean`
- `Louisiana` — `belongs_to` → `Gulf Coast region`
- `Lunar Near Side` — `is_visible_from` → `Earth`
- `Michoud Assembly Facility` — `is_located_in` → `New Orleans`
- `Mission Abort` — `is_classified_as` → `Emergency Procedure`
- `Moon` — `has_landing_region_as` → `Sea of Tranquility`
- `NASA` — `is_headquartered_in` → `Washington, D.C.`
- `National Air and Space Museum` — `is_located_in` → `Washington, D.C.`
- `National Mall` — `contains` → `Smithsonian Castle`
- `Neil Armstrong` — `experienced_during` → `Stuck Thruster event`
- `Neil Armstrong` — `was_born_in` → `Wapakoneta`
- `New Orleans` — `is_located_in` → `Louisiana`
- `Ohio` — `is_part_of` → `United States`
- `Potomac River` — `flows_to` → `Chesapeake Bay`
- `S-IC` — `was_built_by` → `Boeing`
- `Saturn V` — `had_first_stage_as` → `S-IC`
- `Sea of Tranquility` — `is_part_of` → `Lunar Near Side`
- `Smithsonian Castle` — `is_administered_by` → `Smithsonian Institution`
- `Smithsonian Institution` — `was_founded_by` → `United States Congress`
- `Stuck Thruster event` — `was_resolved_by` → `Mission Abort`
- `United States` — `has_capital_in` → `Washington, D.C.`
- `United States Capitol` — `is_located_on` → `Capitol Hill`
- `United States Congress` — `convenes_at` → `United States Capitol`
- `Wapakoneta` — `is_located_in` → `Ohio`
- `Washington, D.C.` — `hosts` → `Smithsonian Institution`
- `Washington, D.C.` — `is_located_on` → `Potomac River`

### Unique CLAIM triples (ignoring iteration)

- `Atlantic Ocean` — `opens_into` → `Chesapeake Bay`
- `Chesapeake Bay` — `opens_into` → `Atlantic Ocean`
- `Ohio` — `is_part_of` → `United States`
- `Potomac River` — `flows_to` → `Chesapeake Bay`
- `Wapakoneta` — `is_located_in` → `Ohio`
- `Washington, D.C.` — `has_capital_in` → `United States`
- `Washington, D.C.` — `is_located_on` → `Potomac River`

### Terminal / final-iteration CLAIMs

- iter=2 label=SUPPORTED: `Chesapeake Bay` — `opens_into` → `Atlantic Ocean`
- iter=2 label=SUPPORTED: `Potomac River` — `flows_to` → `Chesapeake Bay`
- iter=2 label=SUPPORTED: `Washington, D.C.` — `is_located_on` → `Potomac River`

### All relationships used for figures (full property dump)

#### FACTs
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:6425` FACT `Apollo 11` — `was_crewed_by` → `Neil Armstrong` | execution_id=`apollo_hop_036__20260727T205852Z__c2d8a77c`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:6426` FACT `Neil Armstrong` — `was_born_in` → `Wapakoneta` | execution_id=`apollo_hop_036__20260727T205852Z__c2d8a77c`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:6427` FACT `Wapakoneta` — `is_located_in` → `Ohio` | execution_id=`apollo_hop_036__20260727T205852Z__c2d8a77c`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:6428` FACT `Ohio` — `is_part_of` → `United States` | execution_id=`apollo_hop_036__20260727T205852Z__c2d8a77c`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:6429` FACT `United States` — `has_capital_in` → `Washington, D.C.` | execution_id=`apollo_hop_036__20260727T205852Z__c2d8a77c`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:6430` FACT `Washington, D.C.` — `is_located_on` → `Potomac River` | execution_id=`apollo_hop_036__20260727T205852Z__c2d8a77c`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:6431` FACT `Potomac River` — `flows_to` → `Chesapeake Bay` | execution_id=`apollo_hop_036__20260727T205852Z__c2d8a77c`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:6432` FACT `Chesapeake Bay` — `opens_into` → `Atlantic Ocean` | execution_id=`apollo_hop_036__20260727T205852Z__c2d8a77c`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:6433` FACT `Atlantic Ocean` — `is_part_of` → `Global Ocean` | execution_id=`apollo_hop_036__20260727T205852Z__c2d8a77c`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:6434` FACT `Global Ocean` — `is_studied_by` → `Oceanography` | execution_id=`apollo_hop_036__20260727T205852Z__c2d8a77c`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:6435` FACT `Apollo 11` — `was_launched_by` → `Saturn V` | execution_id=`apollo_hop_036__20260727T205852Z__c2d8a77c`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:6436` FACT `Saturn V` — `had_first_stage_as` → `S-IC` | execution_id=`apollo_hop_036__20260727T205852Z__c2d8a77c`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:6437` FACT `S-IC` — `was_built_by` → `Boeing` | execution_id=`apollo_hop_036__20260727T205852Z__c2d8a77c`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:6438` FACT `Boeing` — `assembled_at` → `Michoud Assembly Facility` | execution_id=`apollo_hop_036__20260727T205852Z__c2d8a77c`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:6439` FACT `Michoud Assembly Facility` — `is_located_in` → `New Orleans` | execution_id=`apollo_hop_036__20260727T205852Z__c2d8a77c`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:6440` FACT `New Orleans` — `is_located_in` → `Louisiana` | execution_id=`apollo_hop_036__20260727T205852Z__c2d8a77c`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:6441` FACT `Louisiana` — `belongs_to` → `Gulf Coast region` | execution_id=`apollo_hop_036__20260727T205852Z__c2d8a77c`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:6442` FACT `Gulf Coast region` — `borders` → `Gulf of Mexico` | execution_id=`apollo_hop_036__20260727T205852Z__c2d8a77c`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:6443` FACT `Gulf of Mexico` — `is_connected_to` → `Atlantic Ocean` | execution_id=`apollo_hop_036__20260727T205852Z__c2d8a77c`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:6444` FACT `Apollo 11` — `used_as_command_module` → `Columbia` | execution_id=`apollo_hop_036__20260727T205852Z__c2d8a77c`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:6445` FACT `Columbia` — `is_preserved_at` → `National Air and Space Museum` | execution_id=`apollo_hop_036__20260727T205852Z__c2d8a77c`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:6446` FACT `National Air and Space Museum` — `is_located_in` → `Washington, D.C.` | execution_id=`apollo_hop_036__20260727T205852Z__c2d8a77c`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:6447` FACT `Washington, D.C.` — `hosts` → `Smithsonian Institution` | execution_id=`apollo_hop_036__20260727T205852Z__c2d8a77c`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:6448` FACT `Smithsonian Institution` — `was_founded_by` → `United States Congress` | execution_id=`apollo_hop_036__20260727T205852Z__c2d8a77c`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:6449` FACT `United States Congress` — `convenes_at` → `United States Capitol` | execution_id=`apollo_hop_036__20260727T205852Z__c2d8a77c`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:6450` FACT `United States Capitol` — `is_located_on` → `Capitol Hill` | execution_id=`apollo_hop_036__20260727T205852Z__c2d8a77c`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:6451` FACT `Capitol Hill` — `overlooks` → `National Mall` | execution_id=`apollo_hop_036__20260727T205852Z__c2d8a77c`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:6452` FACT `National Mall` — `contains` → `Smithsonian Castle` | execution_id=`apollo_hop_036__20260727T205852Z__c2d8a77c`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:6453` FACT `Smithsonian Castle` — `is_administered_by` → `Smithsonian Institution` | execution_id=`apollo_hop_036__20260727T205852Z__c2d8a77c`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:6454` FACT `Apollo 11` — `used_as_lunar_module` → `Eagle` | execution_id=`apollo_hop_036__20260727T205852Z__c2d8a77c`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:6455` FACT `Eagle` — `has_descent_stage_located_on` → `Moon` | execution_id=`apollo_hop_036__20260727T205852Z__c2d8a77c`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:6456` FACT `Moon` — `has_landing_region_as` → `Sea of Tranquility` | execution_id=`apollo_hop_036__20260727T205852Z__c2d8a77c`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:6457` FACT `Sea of Tranquility` — `is_part_of` → `Lunar Near Side` | execution_id=`apollo_hop_036__20260727T205852Z__c2d8a77c`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:6458` FACT `Lunar Near Side` — `is_visible_from` → `Earth` | execution_id=`apollo_hop_036__20260727T205852Z__c2d8a77c`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:6459` FACT `Earth` — `is_studied_by` → `Lunar Geology` | execution_id=`apollo_hop_036__20260727T205852Z__c2d8a77c`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:6460` FACT `Apollo Missions` — `includes` → `Apollo 11` | execution_id=`apollo_hop_036__20260727T205852Z__c2d8a77c`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:6461` FACT `Apollo 11` — `was_part_of` → `Apollo Program` | execution_id=`apollo_hop_036__20260727T205852Z__c2d8a77c`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:6462` FACT `Apollo Program` — `was_preceded_by` → `Gemini Program` | execution_id=`apollo_hop_036__20260727T205852Z__c2d8a77c`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:6463` FACT `Gemini Program` — `included` → `Gemini 8` | execution_id=`apollo_hop_036__20260727T205852Z__c2d8a77c`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:6464` FACT `Gemini 8` — `was_commanded_by` → `Neil Armstrong` | execution_id=`apollo_hop_036__20260727T205852Z__c2d8a77c`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:6465` FACT `Neil Armstrong` — `experienced_during` → `Stuck Thruster event` | execution_id=`apollo_hop_036__20260727T205852Z__c2d8a77c`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:6466` FACT `Stuck Thruster event` — `was_resolved_by` → `Mission Abort` | execution_id=`apollo_hop_036__20260727T205852Z__c2d8a77c`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:6467` FACT `Mission Abort` — `is_classified_as` → `Emergency Procedure` | execution_id=`apollo_hop_036__20260727T205852Z__c2d8a77c`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:6468` FACT `Emergency Procedure` — `is_documented_in` → `Gemini 8 Mission Report` | execution_id=`apollo_hop_036__20260727T205852Z__c2d8a77c`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:6469` FACT `Gemini 8 Mission Report` — `is_archived_by` → `NASA` | execution_id=`apollo_hop_036__20260727T205852Z__c2d8a77c`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:6470` FACT `NASA` — `is_headquartered_in` → `Washington, D.C.` | execution_id=`apollo_hop_036__20260727T205852Z__c2d8a77c`

#### CLAIMs
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:6475` CLAIM `Chesapeake Bay` — `opens_into` → `Atlantic Ocean` | label=`SUPPORTED` iteration=0 sub_question_id=1 | reason=`Claim matches a KGc fact.` | conflicting_fact=`` | execution_id=`apollo_hop_036__20260727T205852Z__c2d8a77c`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:6472` CLAIM `Ohio` — `is_part_of` → `United States` | label=`SUPPORTED` iteration=0 sub_question_id=1 | reason=`Claim matches a KGc fact.` | conflicting_fact=`` | execution_id=`apollo_hop_036__20260727T205852Z__c2d8a77c`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:6474` CLAIM `Potomac River` — `flows_to` → `Chesapeake Bay` | label=`SUPPORTED` iteration=0 sub_question_id=1 | reason=`Claim matches a KGc fact.` | conflicting_fact=`` | execution_id=`apollo_hop_036__20260727T205852Z__c2d8a77c`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:6471` CLAIM `Wapakoneta` — `is_located_in` → `Ohio` | label=`SUPPORTED` iteration=0 sub_question_id=1 | reason=`Claim matches a KGc fact.` | conflicting_fact=`` | execution_id=`apollo_hop_036__20260727T205852Z__c2d8a77c`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:6473` CLAIM `Washington, D.C.` — `has_capital_in` → `United States` | label=`NO_EVIDENCE` iteration=0 sub_question_id=1 | reason=`KGc has no matching fact for this claim.` | conflicting_fact=`` | execution_id=`apollo_hop_036__20260727T205852Z__c2d8a77c`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:6476` CLAIM `Atlantic Ocean` — `opens_into` → `Chesapeake Bay` | label=`NO_EVIDENCE` iteration=1 sub_question_id=1 | reason=`KGc has no matching fact for this claim.` | conflicting_fact=`` | execution_id=`apollo_hop_036__20260727T205852Z__c2d8a77c`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:6477` CLAIM `Potomac River` — `flows_to` → `Chesapeake Bay` | label=`SUPPORTED` iteration=1 sub_question_id=1 | reason=`Claim matches a KGc fact.` | conflicting_fact=`` | execution_id=`apollo_hop_036__20260727T205852Z__c2d8a77c`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:6478` CLAIM `Washington, D.C.` — `is_located_on` → `Potomac River` | label=`SUPPORTED` iteration=1 sub_question_id=1 | reason=`Claim matches a KGc fact.` | conflicting_fact=`` | execution_id=`apollo_hop_036__20260727T205852Z__c2d8a77c`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:6479` CLAIM `Chesapeake Bay` — `opens_into` → `Atlantic Ocean` | label=`SUPPORTED` iteration=2 sub_question_id=1 | reason=`Claim matches a KGc fact.` | conflicting_fact=`` | execution_id=`apollo_hop_036__20260727T205852Z__c2d8a77c`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:6480` CLAIM `Potomac River` — `flows_to` → `Chesapeake Bay` | label=`SUPPORTED` iteration=2 sub_question_id=1 | reason=`Claim matches a KGc fact.` | conflicting_fact=`` | execution_id=`apollo_hop_036__20260727T205852Z__c2d8a77c`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:6481` CLAIM `Washington, D.C.` — `is_located_on` → `Potomac River` | label=`SUPPORTED` iteration=2 sub_question_id=1 | reason=`Claim matches a KGc fact.` | conflicting_fact=`` | execution_id=`apollo_hop_036__20260727T205852Z__c2d8a77c`

## Audit: `apollo_hop_036__20260803T015249Z__e3c39c61`

- FACT count: **46**
- CLAIM count: **11**
- CLAIM labels: {'SUPPORTED': 9, 'NO_EVIDENCE': 2}
- Unique iterations: [0, 1, 2]
- Earlier-iteration CLAIMs coexist: **True**
- Sufficient for revision-sequence visuals: **True**

### CLAIMs by sub_question_id

- sub_question_id=1: 11

### CLAIMs by (sub_question_id, iteration, label)

- (sq=1, iter=0, NO_EVIDENCE): 1
- (sq=1, iter=0, SUPPORTED): 4
- (sq=1, iter=1, NO_EVIDENCE): 1
- (sq=1, iter=1, SUPPORTED): 2
- (sq=1, iter=2, SUPPORTED): 3

### Unique FACT triples

- `Apollo 11` — `used_as_command_module` → `Columbia`
- `Apollo 11` — `used_as_lunar_module` → `Eagle`
- `Apollo 11` — `was_crewed_by` → `Neil Armstrong`
- `Apollo 11` — `was_launched_by` → `Saturn V`
- `Apollo 11` — `was_part_of` → `Apollo Program`
- `Apollo Missions` — `includes` → `Apollo 11`
- `Apollo Program` — `was_preceded_by` → `Gemini Program`
- `Atlantic Ocean` — `is_part_of` → `Global Ocean`
- `Boeing` — `assembled_at` → `Michoud Assembly Facility`
- `Capitol Hill` — `overlooks` → `National Mall`
- `Chesapeake Bay` — `opens_into` → `Atlantic Ocean`
- `Columbia` — `is_preserved_at` → `National Air and Space Museum`
- `Eagle` — `has_descent_stage_located_on` → `Moon`
- `Earth` — `is_studied_by` → `Lunar Geology`
- `Emergency Procedure` — `is_documented_in` → `Gemini 8 Mission Report`
- `Gemini 8` — `was_commanded_by` → `Neil Armstrong`
- `Gemini 8 Mission Report` — `is_archived_by` → `NASA`
- `Gemini Program` — `included` → `Gemini 8`
- `Global Ocean` — `is_studied_by` → `Oceanography`
- `Gulf Coast region` — `borders` → `Gulf of Mexico`
- `Gulf of Mexico` — `is_connected_to` → `Atlantic Ocean`
- `Louisiana` — `belongs_to` → `Gulf Coast region`
- `Lunar Near Side` — `is_visible_from` → `Earth`
- `Michoud Assembly Facility` — `is_located_in` → `New Orleans`
- `Mission Abort` — `is_classified_as` → `Emergency Procedure`
- `Moon` — `has_landing_region_as` → `Sea of Tranquility`
- `NASA` — `is_headquartered_in` → `Washington, D.C.`
- `National Air and Space Museum` — `is_located_in` → `Washington, D.C.`
- `National Mall` — `contains` → `Smithsonian Castle`
- `Neil Armstrong` — `experienced_during` → `Stuck Thruster event`
- `Neil Armstrong` — `was_born_in` → `Wapakoneta`
- `New Orleans` — `is_located_in` → `Louisiana`
- `Ohio` — `is_part_of` → `United States`
- `Potomac River` — `flows_to` → `Chesapeake Bay`
- `S-IC` — `was_built_by` → `Boeing`
- `Saturn V` — `had_first_stage_as` → `S-IC`
- `Sea of Tranquility` — `is_part_of` → `Lunar Near Side`
- `Smithsonian Castle` — `is_administered_by` → `Smithsonian Institution`
- `Smithsonian Institution` — `was_founded_by` → `United States Congress`
- `Stuck Thruster event` — `was_resolved_by` → `Mission Abort`
- `United States` — `has_capital_in` → `Washington, D.C.`
- `United States Capitol` — `is_located_on` → `Capitol Hill`
- `United States Congress` — `convenes_at` → `United States Capitol`
- `Wapakoneta` — `is_located_in` → `Ohio`
- `Washington, D.C.` — `hosts` → `Smithsonian Institution`
- `Washington, D.C.` — `is_located_on` → `Potomac River`

### Unique CLAIM triples (ignoring iteration)

- `Atlantic Ocean` — `opens_into` → `Chesapeake Bay`
- `Chesapeake Bay` — `opens_into` → `Atlantic Ocean`
- `Ohio` — `is_part_of` → `United States`
- `Potomac River` — `flows_to` → `Chesapeake Bay`
- `Wapakoneta` — `is_located_in` → `Ohio`
- `Washington, D.C.` — `has_capital_in` → `United States`
- `Washington, D.C.` — `is_located_on` → `Potomac River`

### Terminal / final-iteration CLAIMs

- iter=2 label=SUPPORTED: `Chesapeake Bay` — `opens_into` → `Atlantic Ocean`
- iter=2 label=SUPPORTED: `Potomac River` — `flows_to` → `Chesapeake Bay`
- iter=2 label=SUPPORTED: `Washington, D.C.` — `is_located_on` → `Potomac River`

### All relationships used for figures (full property dump)

#### FACTs
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:8999` FACT `Apollo 11` — `was_crewed_by` → `Neil Armstrong` | execution_id=`apollo_hop_036__20260803T015249Z__e3c39c61`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:9000` FACT `Neil Armstrong` — `was_born_in` → `Wapakoneta` | execution_id=`apollo_hop_036__20260803T015249Z__e3c39c61`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:9001` FACT `Wapakoneta` — `is_located_in` → `Ohio` | execution_id=`apollo_hop_036__20260803T015249Z__e3c39c61`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:9002` FACT `Ohio` — `is_part_of` → `United States` | execution_id=`apollo_hop_036__20260803T015249Z__e3c39c61`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:9003` FACT `United States` — `has_capital_in` → `Washington, D.C.` | execution_id=`apollo_hop_036__20260803T015249Z__e3c39c61`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:9004` FACT `Washington, D.C.` — `is_located_on` → `Potomac River` | execution_id=`apollo_hop_036__20260803T015249Z__e3c39c61`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:9005` FACT `Potomac River` — `flows_to` → `Chesapeake Bay` | execution_id=`apollo_hop_036__20260803T015249Z__e3c39c61`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:9006` FACT `Chesapeake Bay` — `opens_into` → `Atlantic Ocean` | execution_id=`apollo_hop_036__20260803T015249Z__e3c39c61`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:9007` FACT `Atlantic Ocean` — `is_part_of` → `Global Ocean` | execution_id=`apollo_hop_036__20260803T015249Z__e3c39c61`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:9008` FACT `Global Ocean` — `is_studied_by` → `Oceanography` | execution_id=`apollo_hop_036__20260803T015249Z__e3c39c61`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:9009` FACT `Apollo 11` — `was_launched_by` → `Saturn V` | execution_id=`apollo_hop_036__20260803T015249Z__e3c39c61`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:9010` FACT `Saturn V` — `had_first_stage_as` → `S-IC` | execution_id=`apollo_hop_036__20260803T015249Z__e3c39c61`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:9011` FACT `S-IC` — `was_built_by` → `Boeing` | execution_id=`apollo_hop_036__20260803T015249Z__e3c39c61`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:9012` FACT `Boeing` — `assembled_at` → `Michoud Assembly Facility` | execution_id=`apollo_hop_036__20260803T015249Z__e3c39c61`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:9013` FACT `Michoud Assembly Facility` — `is_located_in` → `New Orleans` | execution_id=`apollo_hop_036__20260803T015249Z__e3c39c61`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:9014` FACT `New Orleans` — `is_located_in` → `Louisiana` | execution_id=`apollo_hop_036__20260803T015249Z__e3c39c61`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:9015` FACT `Louisiana` — `belongs_to` → `Gulf Coast region` | execution_id=`apollo_hop_036__20260803T015249Z__e3c39c61`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:9016` FACT `Gulf Coast region` — `borders` → `Gulf of Mexico` | execution_id=`apollo_hop_036__20260803T015249Z__e3c39c61`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:9017` FACT `Gulf of Mexico` — `is_connected_to` → `Atlantic Ocean` | execution_id=`apollo_hop_036__20260803T015249Z__e3c39c61`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:9018` FACT `Apollo 11` — `used_as_command_module` → `Columbia` | execution_id=`apollo_hop_036__20260803T015249Z__e3c39c61`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:9019` FACT `Columbia` — `is_preserved_at` → `National Air and Space Museum` | execution_id=`apollo_hop_036__20260803T015249Z__e3c39c61`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:9020` FACT `National Air and Space Museum` — `is_located_in` → `Washington, D.C.` | execution_id=`apollo_hop_036__20260803T015249Z__e3c39c61`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:9021` FACT `Washington, D.C.` — `hosts` → `Smithsonian Institution` | execution_id=`apollo_hop_036__20260803T015249Z__e3c39c61`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:9022` FACT `Smithsonian Institution` — `was_founded_by` → `United States Congress` | execution_id=`apollo_hop_036__20260803T015249Z__e3c39c61`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:9023` FACT `United States Congress` — `convenes_at` → `United States Capitol` | execution_id=`apollo_hop_036__20260803T015249Z__e3c39c61`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:9024` FACT `United States Capitol` — `is_located_on` → `Capitol Hill` | execution_id=`apollo_hop_036__20260803T015249Z__e3c39c61`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:9025` FACT `Capitol Hill` — `overlooks` → `National Mall` | execution_id=`apollo_hop_036__20260803T015249Z__e3c39c61`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:9026` FACT `National Mall` — `contains` → `Smithsonian Castle` | execution_id=`apollo_hop_036__20260803T015249Z__e3c39c61`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:9027` FACT `Smithsonian Castle` — `is_administered_by` → `Smithsonian Institution` | execution_id=`apollo_hop_036__20260803T015249Z__e3c39c61`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:9028` FACT `Apollo 11` — `used_as_lunar_module` → `Eagle` | execution_id=`apollo_hop_036__20260803T015249Z__e3c39c61`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:9029` FACT `Eagle` — `has_descent_stage_located_on` → `Moon` | execution_id=`apollo_hop_036__20260803T015249Z__e3c39c61`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:9030` FACT `Moon` — `has_landing_region_as` → `Sea of Tranquility` | execution_id=`apollo_hop_036__20260803T015249Z__e3c39c61`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:9031` FACT `Sea of Tranquility` — `is_part_of` → `Lunar Near Side` | execution_id=`apollo_hop_036__20260803T015249Z__e3c39c61`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:9032` FACT `Lunar Near Side` — `is_visible_from` → `Earth` | execution_id=`apollo_hop_036__20260803T015249Z__e3c39c61`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:9033` FACT `Earth` — `is_studied_by` → `Lunar Geology` | execution_id=`apollo_hop_036__20260803T015249Z__e3c39c61`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:9034` FACT `Apollo Missions` — `includes` → `Apollo 11` | execution_id=`apollo_hop_036__20260803T015249Z__e3c39c61`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:9035` FACT `Apollo 11` — `was_part_of` → `Apollo Program` | execution_id=`apollo_hop_036__20260803T015249Z__e3c39c61`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:9036` FACT `Apollo Program` — `was_preceded_by` → `Gemini Program` | execution_id=`apollo_hop_036__20260803T015249Z__e3c39c61`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:9037` FACT `Gemini Program` — `included` → `Gemini 8` | execution_id=`apollo_hop_036__20260803T015249Z__e3c39c61`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:9038` FACT `Gemini 8` — `was_commanded_by` → `Neil Armstrong` | execution_id=`apollo_hop_036__20260803T015249Z__e3c39c61`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:9039` FACT `Neil Armstrong` — `experienced_during` → `Stuck Thruster event` | execution_id=`apollo_hop_036__20260803T015249Z__e3c39c61`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:9040` FACT `Stuck Thruster event` — `was_resolved_by` → `Mission Abort` | execution_id=`apollo_hop_036__20260803T015249Z__e3c39c61`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:9041` FACT `Mission Abort` — `is_classified_as` → `Emergency Procedure` | execution_id=`apollo_hop_036__20260803T015249Z__e3c39c61`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:9042` FACT `Emergency Procedure` — `is_documented_in` → `Gemini 8 Mission Report` | execution_id=`apollo_hop_036__20260803T015249Z__e3c39c61`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:9043` FACT `Gemini 8 Mission Report` — `is_archived_by` → `NASA` | execution_id=`apollo_hop_036__20260803T015249Z__e3c39c61`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:9044` FACT `NASA` — `is_headquartered_in` → `Washington, D.C.` | execution_id=`apollo_hop_036__20260803T015249Z__e3c39c61`

#### CLAIMs
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:9049` CLAIM `Chesapeake Bay` — `opens_into` → `Atlantic Ocean` | label=`SUPPORTED` iteration=0 sub_question_id=1 | reason=`Claim matches a KGc fact.` | conflicting_fact=`` | execution_id=`apollo_hop_036__20260803T015249Z__e3c39c61`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:9046` CLAIM `Ohio` — `is_part_of` → `United States` | label=`SUPPORTED` iteration=0 sub_question_id=1 | reason=`Claim matches a KGc fact.` | conflicting_fact=`` | execution_id=`apollo_hop_036__20260803T015249Z__e3c39c61`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:9048` CLAIM `Potomac River` — `flows_to` → `Chesapeake Bay` | label=`SUPPORTED` iteration=0 sub_question_id=1 | reason=`Claim matches a KGc fact.` | conflicting_fact=`` | execution_id=`apollo_hop_036__20260803T015249Z__e3c39c61`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:9045` CLAIM `Wapakoneta` — `is_located_in` → `Ohio` | label=`SUPPORTED` iteration=0 sub_question_id=1 | reason=`Claim matches a KGc fact.` | conflicting_fact=`` | execution_id=`apollo_hop_036__20260803T015249Z__e3c39c61`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:9047` CLAIM `Washington, D.C.` — `has_capital_in` → `United States` | label=`NO_EVIDENCE` iteration=0 sub_question_id=1 | reason=`KGc has no matching fact for this claim.` | conflicting_fact=`` | execution_id=`apollo_hop_036__20260803T015249Z__e3c39c61`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:9050` CLAIM `Atlantic Ocean` — `opens_into` → `Chesapeake Bay` | label=`NO_EVIDENCE` iteration=1 sub_question_id=1 | reason=`KGc has no matching fact for this claim.` | conflicting_fact=`` | execution_id=`apollo_hop_036__20260803T015249Z__e3c39c61`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:9051` CLAIM `Potomac River` — `flows_to` → `Chesapeake Bay` | label=`SUPPORTED` iteration=1 sub_question_id=1 | reason=`Claim matches a KGc fact.` | conflicting_fact=`` | execution_id=`apollo_hop_036__20260803T015249Z__e3c39c61`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:9052` CLAIM `Washington, D.C.` — `is_located_on` → `Potomac River` | label=`SUPPORTED` iteration=1 sub_question_id=1 | reason=`Claim matches a KGc fact.` | conflicting_fact=`` | execution_id=`apollo_hop_036__20260803T015249Z__e3c39c61`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:9053` CLAIM `Chesapeake Bay` — `opens_into` → `Atlantic Ocean` | label=`SUPPORTED` iteration=2 sub_question_id=1 | reason=`Claim matches a KGc fact.` | conflicting_fact=`` | execution_id=`apollo_hop_036__20260803T015249Z__e3c39c61`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:9054` CLAIM `Potomac River` — `flows_to` → `Chesapeake Bay` | label=`SUPPORTED` iteration=2 sub_question_id=1 | reason=`Claim matches a KGc fact.` | conflicting_fact=`` | execution_id=`apollo_hop_036__20260803T015249Z__e3c39c61`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:9055` CLAIM `Washington, D.C.` — `is_located_on` → `Potomac River` | label=`SUPPORTED` iteration=2 sub_question_id=1 | reason=`Claim matches a KGc fact.` | conflicting_fact=`` | execution_id=`apollo_hop_036__20260803T015249Z__e3c39c61`

## Audit: `apollo_hop_036__20260803T023440Z__d3fff44b`

- FACT count: **46**
- CLAIM count: **11**
- CLAIM labels: {'SUPPORTED': 9, 'NO_EVIDENCE': 2}
- Unique iterations: [0, 1, 2]
- Earlier-iteration CLAIMs coexist: **True**
- Sufficient for revision-sequence visuals: **True**

### CLAIMs by sub_question_id

- sub_question_id=1: 11

### CLAIMs by (sub_question_id, iteration, label)

- (sq=1, iter=0, NO_EVIDENCE): 1
- (sq=1, iter=0, SUPPORTED): 4
- (sq=1, iter=1, NO_EVIDENCE): 1
- (sq=1, iter=1, SUPPORTED): 2
- (sq=1, iter=2, SUPPORTED): 3

### Unique FACT triples

- `Apollo 11` — `used_as_command_module` → `Columbia`
- `Apollo 11` — `used_as_lunar_module` → `Eagle`
- `Apollo 11` — `was_crewed_by` → `Neil Armstrong`
- `Apollo 11` — `was_launched_by` → `Saturn V`
- `Apollo 11` — `was_part_of` → `Apollo Program`
- `Apollo Missions` — `includes` → `Apollo 11`
- `Apollo Program` — `was_preceded_by` → `Gemini Program`
- `Atlantic Ocean` — `is_part_of` → `Global Ocean`
- `Boeing` — `assembled_at` → `Michoud Assembly Facility`
- `Capitol Hill` — `overlooks` → `National Mall`
- `Chesapeake Bay` — `opens_into` → `Atlantic Ocean`
- `Columbia` — `is_preserved_at` → `National Air and Space Museum`
- `Eagle` — `has_descent_stage_located_on` → `Moon`
- `Earth` — `is_studied_by` → `Lunar Geology`
- `Emergency Procedure` — `is_documented_in` → `Gemini 8 Mission Report`
- `Gemini 8` — `was_commanded_by` → `Neil Armstrong`
- `Gemini 8 Mission Report` — `is_archived_by` → `NASA`
- `Gemini Program` — `included` → `Gemini 8`
- `Global Ocean` — `is_studied_by` → `Oceanography`
- `Gulf Coast region` — `borders` → `Gulf of Mexico`
- `Gulf of Mexico` — `is_connected_to` → `Atlantic Ocean`
- `Louisiana` — `belongs_to` → `Gulf Coast region`
- `Lunar Near Side` — `is_visible_from` → `Earth`
- `Michoud Assembly Facility` — `is_located_in` → `New Orleans`
- `Mission Abort` — `is_classified_as` → `Emergency Procedure`
- `Moon` — `has_landing_region_as` → `Sea of Tranquility`
- `NASA` — `is_headquartered_in` → `Washington, D.C.`
- `National Air and Space Museum` — `is_located_in` → `Washington, D.C.`
- `National Mall` — `contains` → `Smithsonian Castle`
- `Neil Armstrong` — `experienced_during` → `Stuck Thruster event`
- `Neil Armstrong` — `was_born_in` → `Wapakoneta`
- `New Orleans` — `is_located_in` → `Louisiana`
- `Ohio` — `is_part_of` → `United States`
- `Potomac River` — `flows_to` → `Chesapeake Bay`
- `S-IC` — `was_built_by` → `Boeing`
- `Saturn V` — `had_first_stage_as` → `S-IC`
- `Sea of Tranquility` — `is_part_of` → `Lunar Near Side`
- `Smithsonian Castle` — `is_administered_by` → `Smithsonian Institution`
- `Smithsonian Institution` — `was_founded_by` → `United States Congress`
- `Stuck Thruster event` — `was_resolved_by` → `Mission Abort`
- `United States` — `has_capital_in` → `Washington, D.C.`
- `United States Capitol` — `is_located_on` → `Capitol Hill`
- `United States Congress` — `convenes_at` → `United States Capitol`
- `Wapakoneta` — `is_located_in` → `Ohio`
- `Washington, D.C.` — `hosts` → `Smithsonian Institution`
- `Washington, D.C.` — `is_located_on` → `Potomac River`

### Unique CLAIM triples (ignoring iteration)

- `Atlantic Ocean` — `opens_into` → `Chesapeake Bay`
- `Chesapeake Bay` — `opens_into` → `Atlantic Ocean`
- `Ohio` — `is_part_of` → `United States`
- `Potomac River` — `flows_to` → `Chesapeake Bay`
- `Wapakoneta` — `is_located_in` → `Ohio`
- `Washington, D.C.` — `has_capital_in` → `United States`
- `Washington, D.C.` — `is_located_on` → `Potomac River`

### Terminal / final-iteration CLAIMs

- iter=2 label=SUPPORTED: `Chesapeake Bay` — `opens_into` → `Atlantic Ocean`
- iter=2 label=SUPPORTED: `Potomac River` — `flows_to` → `Chesapeake Bay`
- iter=2 label=SUPPORTED: `Washington, D.C.` — `is_located_on` → `Potomac River`

### All relationships used for figures (full property dump)

#### FACTs
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:11468` FACT `Apollo 11` — `was_crewed_by` → `Neil Armstrong` | execution_id=`apollo_hop_036__20260803T023440Z__d3fff44b`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:11469` FACT `Neil Armstrong` — `was_born_in` → `Wapakoneta` | execution_id=`apollo_hop_036__20260803T023440Z__d3fff44b`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:11470` FACT `Wapakoneta` — `is_located_in` → `Ohio` | execution_id=`apollo_hop_036__20260803T023440Z__d3fff44b`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:11471` FACT `Ohio` — `is_part_of` → `United States` | execution_id=`apollo_hop_036__20260803T023440Z__d3fff44b`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:11472` FACT `United States` — `has_capital_in` → `Washington, D.C.` | execution_id=`apollo_hop_036__20260803T023440Z__d3fff44b`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:11473` FACT `Washington, D.C.` — `is_located_on` → `Potomac River` | execution_id=`apollo_hop_036__20260803T023440Z__d3fff44b`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:11474` FACT `Potomac River` — `flows_to` → `Chesapeake Bay` | execution_id=`apollo_hop_036__20260803T023440Z__d3fff44b`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:11475` FACT `Chesapeake Bay` — `opens_into` → `Atlantic Ocean` | execution_id=`apollo_hop_036__20260803T023440Z__d3fff44b`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:11476` FACT `Atlantic Ocean` — `is_part_of` → `Global Ocean` | execution_id=`apollo_hop_036__20260803T023440Z__d3fff44b`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:11477` FACT `Global Ocean` — `is_studied_by` → `Oceanography` | execution_id=`apollo_hop_036__20260803T023440Z__d3fff44b`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:11478` FACT `Apollo 11` — `was_launched_by` → `Saturn V` | execution_id=`apollo_hop_036__20260803T023440Z__d3fff44b`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:11479` FACT `Saturn V` — `had_first_stage_as` → `S-IC` | execution_id=`apollo_hop_036__20260803T023440Z__d3fff44b`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:11480` FACT `S-IC` — `was_built_by` → `Boeing` | execution_id=`apollo_hop_036__20260803T023440Z__d3fff44b`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:11481` FACT `Boeing` — `assembled_at` → `Michoud Assembly Facility` | execution_id=`apollo_hop_036__20260803T023440Z__d3fff44b`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:11482` FACT `Michoud Assembly Facility` — `is_located_in` → `New Orleans` | execution_id=`apollo_hop_036__20260803T023440Z__d3fff44b`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:11483` FACT `New Orleans` — `is_located_in` → `Louisiana` | execution_id=`apollo_hop_036__20260803T023440Z__d3fff44b`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:11484` FACT `Louisiana` — `belongs_to` → `Gulf Coast region` | execution_id=`apollo_hop_036__20260803T023440Z__d3fff44b`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:11485` FACT `Gulf Coast region` — `borders` → `Gulf of Mexico` | execution_id=`apollo_hop_036__20260803T023440Z__d3fff44b`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:11486` FACT `Gulf of Mexico` — `is_connected_to` → `Atlantic Ocean` | execution_id=`apollo_hop_036__20260803T023440Z__d3fff44b`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:11487` FACT `Apollo 11` — `used_as_command_module` → `Columbia` | execution_id=`apollo_hop_036__20260803T023440Z__d3fff44b`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:11488` FACT `Columbia` — `is_preserved_at` → `National Air and Space Museum` | execution_id=`apollo_hop_036__20260803T023440Z__d3fff44b`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:11489` FACT `National Air and Space Museum` — `is_located_in` → `Washington, D.C.` | execution_id=`apollo_hop_036__20260803T023440Z__d3fff44b`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:11490` FACT `Washington, D.C.` — `hosts` → `Smithsonian Institution` | execution_id=`apollo_hop_036__20260803T023440Z__d3fff44b`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:11491` FACT `Smithsonian Institution` — `was_founded_by` → `United States Congress` | execution_id=`apollo_hop_036__20260803T023440Z__d3fff44b`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:11492` FACT `United States Congress` — `convenes_at` → `United States Capitol` | execution_id=`apollo_hop_036__20260803T023440Z__d3fff44b`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:11493` FACT `United States Capitol` — `is_located_on` → `Capitol Hill` | execution_id=`apollo_hop_036__20260803T023440Z__d3fff44b`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:11494` FACT `Capitol Hill` — `overlooks` → `National Mall` | execution_id=`apollo_hop_036__20260803T023440Z__d3fff44b`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:11495` FACT `National Mall` — `contains` → `Smithsonian Castle` | execution_id=`apollo_hop_036__20260803T023440Z__d3fff44b`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:11496` FACT `Smithsonian Castle` — `is_administered_by` → `Smithsonian Institution` | execution_id=`apollo_hop_036__20260803T023440Z__d3fff44b`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:11497` FACT `Apollo 11` — `used_as_lunar_module` → `Eagle` | execution_id=`apollo_hop_036__20260803T023440Z__d3fff44b`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:11498` FACT `Eagle` — `has_descent_stage_located_on` → `Moon` | execution_id=`apollo_hop_036__20260803T023440Z__d3fff44b`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:11499` FACT `Moon` — `has_landing_region_as` → `Sea of Tranquility` | execution_id=`apollo_hop_036__20260803T023440Z__d3fff44b`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:11500` FACT `Sea of Tranquility` — `is_part_of` → `Lunar Near Side` | execution_id=`apollo_hop_036__20260803T023440Z__d3fff44b`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:11501` FACT `Lunar Near Side` — `is_visible_from` → `Earth` | execution_id=`apollo_hop_036__20260803T023440Z__d3fff44b`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:11502` FACT `Earth` — `is_studied_by` → `Lunar Geology` | execution_id=`apollo_hop_036__20260803T023440Z__d3fff44b`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:11503` FACT `Apollo Missions` — `includes` → `Apollo 11` | execution_id=`apollo_hop_036__20260803T023440Z__d3fff44b`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:11504` FACT `Apollo 11` — `was_part_of` → `Apollo Program` | execution_id=`apollo_hop_036__20260803T023440Z__d3fff44b`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:11505` FACT `Apollo Program` — `was_preceded_by` → `Gemini Program` | execution_id=`apollo_hop_036__20260803T023440Z__d3fff44b`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:11506` FACT `Gemini Program` — `included` → `Gemini 8` | execution_id=`apollo_hop_036__20260803T023440Z__d3fff44b`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:11507` FACT `Gemini 8` — `was_commanded_by` → `Neil Armstrong` | execution_id=`apollo_hop_036__20260803T023440Z__d3fff44b`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:11508` FACT `Neil Armstrong` — `experienced_during` → `Stuck Thruster event` | execution_id=`apollo_hop_036__20260803T023440Z__d3fff44b`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:11509` FACT `Stuck Thruster event` — `was_resolved_by` → `Mission Abort` | execution_id=`apollo_hop_036__20260803T023440Z__d3fff44b`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:11510` FACT `Mission Abort` — `is_classified_as` → `Emergency Procedure` | execution_id=`apollo_hop_036__20260803T023440Z__d3fff44b`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:11511` FACT `Emergency Procedure` — `is_documented_in` → `Gemini 8 Mission Report` | execution_id=`apollo_hop_036__20260803T023440Z__d3fff44b`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:11512` FACT `Gemini 8 Mission Report` — `is_archived_by` → `NASA` | execution_id=`apollo_hop_036__20260803T023440Z__d3fff44b`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:11513` FACT `NASA` — `is_headquartered_in` → `Washington, D.C.` | execution_id=`apollo_hop_036__20260803T023440Z__d3fff44b`

#### CLAIMs
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:11518` CLAIM `Chesapeake Bay` — `opens_into` → `Atlantic Ocean` | label=`SUPPORTED` iteration=0 sub_question_id=1 | reason=`Claim matches a KGc fact.` | conflicting_fact=`` | execution_id=`apollo_hop_036__20260803T023440Z__d3fff44b`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:11515` CLAIM `Ohio` — `is_part_of` → `United States` | label=`SUPPORTED` iteration=0 sub_question_id=1 | reason=`Claim matches a KGc fact.` | conflicting_fact=`` | execution_id=`apollo_hop_036__20260803T023440Z__d3fff44b`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:11517` CLAIM `Potomac River` — `flows_to` → `Chesapeake Bay` | label=`SUPPORTED` iteration=0 sub_question_id=1 | reason=`Claim matches a KGc fact.` | conflicting_fact=`` | execution_id=`apollo_hop_036__20260803T023440Z__d3fff44b`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:11514` CLAIM `Wapakoneta` — `is_located_in` → `Ohio` | label=`SUPPORTED` iteration=0 sub_question_id=1 | reason=`Claim matches a KGc fact.` | conflicting_fact=`` | execution_id=`apollo_hop_036__20260803T023440Z__d3fff44b`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:11516` CLAIM `Washington, D.C.` — `has_capital_in` → `United States` | label=`NO_EVIDENCE` iteration=0 sub_question_id=1 | reason=`KGc has no matching fact for this claim.` | conflicting_fact=`` | execution_id=`apollo_hop_036__20260803T023440Z__d3fff44b`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:11519` CLAIM `Atlantic Ocean` — `opens_into` → `Chesapeake Bay` | label=`NO_EVIDENCE` iteration=1 sub_question_id=1 | reason=`KGc has no matching fact for this claim.` | conflicting_fact=`` | execution_id=`apollo_hop_036__20260803T023440Z__d3fff44b`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:11520` CLAIM `Potomac River` — `flows_to` → `Chesapeake Bay` | label=`SUPPORTED` iteration=1 sub_question_id=1 | reason=`Claim matches a KGc fact.` | conflicting_fact=`` | execution_id=`apollo_hop_036__20260803T023440Z__d3fff44b`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:11521` CLAIM `Washington, D.C.` — `is_located_on` → `Potomac River` | label=`SUPPORTED` iteration=1 sub_question_id=1 | reason=`Claim matches a KGc fact.` | conflicting_fact=`` | execution_id=`apollo_hop_036__20260803T023440Z__d3fff44b`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:11522` CLAIM `Chesapeake Bay` — `opens_into` → `Atlantic Ocean` | label=`SUPPORTED` iteration=2 sub_question_id=1 | reason=`Claim matches a KGc fact.` | conflicting_fact=`` | execution_id=`apollo_hop_036__20260803T023440Z__d3fff44b`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:11523` CLAIM `Potomac River` — `flows_to` → `Chesapeake Bay` | label=`SUPPORTED` iteration=2 sub_question_id=1 | reason=`Claim matches a KGc fact.` | conflicting_fact=`` | execution_id=`apollo_hop_036__20260803T023440Z__d3fff44b`
- id=`5:c465d26d-268b-420d-a2ae-5fa68bb98b7b:11524` CLAIM `Washington, D.C.` — `is_located_on` → `Potomac River` | label=`SUPPORTED` iteration=2 sub_question_id=1 | reason=`Claim matches a KGc fact.` | conflicting_fact=`` | execution_id=`apollo_hop_036__20260803T023440Z__d3fff44b`

