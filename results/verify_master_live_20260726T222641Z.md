# Live verification report

- timestamp_utc: `20260726T222641Z`
- model: `gemma4:e4b` (9.6 GB, same digest as gemma4:latest)
- ollama_version: `ollama version is 0.30.6`
- ollama_num_ctx: `32768`
- ollama_num_predict: `4096`
- ollama_request_timeout: `600`
- neo4j: bolt://localhost:7687 user=neo4j database=neo4j image=existing grapheval-neo4j container
- live Neo4j pytest: 4 passed
- live Ollama pytest: 2 passed (~179s)
- API /dependencies: neo4j connected + ollama reachable/model installed
- API custom smoke: Rack R7 / Service A runs succeeded after restart
- API benchmark apollo_hop_001: predicted contains Neil Armstrong; pipeline RESOLVED; 49 facts
