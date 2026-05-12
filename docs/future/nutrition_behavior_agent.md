# Nutrition & Behavior Recommendation Agent System

An autonomous agent system that analyzes scientific literature and real-world data on nutrition, lifestyle behaviors, and their impact on aging and disease to generate evidence-based, personalized recommendations. The system uses simulation cycles to test, refine, and evolve recommendations, creating a closed loop from data to actionable advice.

## System Overview

The Nutrition & Behavior Recommendation Agent System consists of three interlocking sub-agents operating in a continuous loop:

1. Evidence Mining Agent - Ingests and structures nutrition/behavior data
2. Recommendation Agent - Generates personalized recommendations using LLM + causal inference
3. Simulation & Evolution Agent - Tests recommendations via digital twin simulation and evolves them using genetic algorithms

This system integrates with the existing CureForge multi-agent architecture under the Domain Supervisor for "Molecular & Lifestyle Epidemiology."

## Core Components

### Evidence Mining Agent

Continuously ingests and structures data from:

- Peer-reviewed literature (PubMed, nutrition journals, gerontology)
- Large-scale cohort studies (NHANES, UK Biobank, Nurses' Health Study)
- Wearable and dietary recall datasets
- Clinical trial registries for nutrition/behavioral interventions

Output: A structured Nutrition-Behavior Knowledge Graph with nodes for foods, nutrients, behaviors, biomarkers, diseases, and aging hallmarks, connected by edges representing effect direction, effect size, confidence, and study metadata.

### Recommendation Agent

For a given user profile (age, sex, genetics, current health, lifestyle):

- Queries the knowledge graph
- Uses an LLM plus causal inference layer to generate:
    - Ranked dietary changes (e.g., "increase omega-3 to 2g/day, reduce saturated fat to <10% calories")
    - Behavioral modifications (e.g., "add 30 min moderate exercise 5x/week, improve sleep consistency")
    - A composite Personalized Longevity Score (PLS) with confidence intervals

Output: Structured recommendation object with citations and predicted healthspan impact.

### Simulation & Evolution Agent

Takes each recommendation and:

- Translates it into a parameterized intervention
- Runs digital twin simulations on virtual human cohorts
- Measures effects on epigenetic age (EARA), Composite 12-Hallmark Biomarker Score (CHBS), predicted lifespan/healthspan, and mortality hazard
- Evolves recommendations using genetic algorithm (mutation, crossover, fitness based on PLS improvement)
- Proposes new hypotheses (e.g., "time-restricted eating + cold exposure synergy") that re-enter the recommendation pipeline

## Integration with Existing Architecture

- Evidence Mining Agent runs as a Data Mining Agent under the Domain Supervisor for "Molecular & Lifestyle Epidemiology"
- Recommendation Agent sits under the same Domain Supervisor and is called by the Autonomous Research Cycle (ARC)
- Simulation & Evolution Agent invokes the Digital Twin Simulator and communicates with the Hypothesis Evolution Engine
- Uses the Causal Gate for causal validation and MBEC engine to monitor healthspan improvements

## Development Priorities

| Priority | Component                    | Description                                                                                                                                                                                                |
| -------- | ---------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| P0       | Evidence Mining Agent        | Build knowledge graph ingestion pipeline from NHANES, UK Biobank, and PubMed. Implement basic node-edge extraction using LLM + rule-based entity recognition. Store in existing Longevity Knowledge Graph. |
| P0       | Basic Recommendation Agent   | For synthetic user profile, query knowledge graph and generate simple ranked recommendations using LLM. Output PLS. No causal inference yet.                                                               |
| P1       | Simulation & Evolution (MVP) | Hard-code recommendation templates (e.g., "increase fiber", "reduce sedentary time") and run through digital twin simulator. Collect outcome metrics.                                                      |
| P1       | Causal Layer                 | Integrate DoWhy engine to filter recommendations – only those passing refutation tests (causal) are kept. Use existing Causal Gate code.                                                                   |
| P2       | Full Evolutionary Loop       | Implement genetic algorithm to mutate and recombine recommendations. Use PLS improvement as fitness. Run multiple generations automatically.                                                               |
| P2       | Personalization Engine       | Use real user data (wearable, food logs) as input. Output personalized PDF reports and API endpoints.                                                                                                      |

## Technical Specifications

### Data Sources (Initial)

- NHANES (1999–2020): Diet, physical activity, lab biomarkers, mortality
- UK Biobank: Dietary recall, accelerometry, genetic data, health outcomes
- PubMed: Full-text articles via Entrez API (systematic reviews, RCTs)
- ClinicalTrials.gov: Completed interventions with nutrition/behavior arms

### Knowledge Graph Schema (Extending Existing LKG)

**New Node Types:**

- Food (name, nutrient profile, food group)
- Nutrient (omega-3, vitamin D, fiber, etc.)
- Behavior (sleep duration, walking steps, meditation, etc.)
- Biomarker (HbA1c, CRP, LDL, etc.) - linked to nutrition/behavior

**New Edge Types:**

- RAISES / LOWERS (effect on biomarker or disease risk)
- SYNERGIZES / ANTAGONIZES (interactions)

### Recommendation Output Format

```json
{
  "user_id": "uuid",
  "timestamp": "2026-04-23T…",
  "PLS": 0.78,
  "recommendations": [
    {
      "type": "diet",
      "action": "Increase omega-3 fatty acids intake to 2g/day (from fatty fish or algae oil)",
      "evidence_level": "A (RCT meta-analysis)",
      "predicted_healthspan_gain_years": 1.2,
      "confidence_interval": [0.8, 1.6],
      "causal_validated": true,
      "citations": ["PMID:…", "PMC:…"]
    },
    ...
  ]
}
```

### Simulation Integration

The Simulation & Evolution Agent translates recommendations into deltas on digital twin variables:

- "Increase fiber by 10g/day" → modify gut microbiome composition, reduce inflammatory biomarkers
- "Add 30 min walking/day" → reduce BMI, improve cardiovascular fitness

These deltas are applied in the digital twin's intervention step. The simulator runs forward for 5-20 simulated years and returns ΔCHBS, ΔCBA, Δmortality.

### Evolution Algorithm

- **Representation**: Each recommendation is a set of (action, duration, magnitude) pairs
- **Initial Population**: Top 20 recommendations from Recommendation Agent
- **Fitness**: ΔPLS = (PLS_simulated – PLS_baseline)
- **Operators**:
    - Mutation: Change magnitude of one action, add/remove an action
    - Crossover: Merge two parent recommendation sets
- **Selection**: Tournament selection (size 3), keep top 5 per generation
- **Generations**: 10, or stop when fitness improvement < 1% for 2 generations

## Deliverables

1. Python module `src/agents/nutrition_behavior/` containing:
    - `evidence_miner.py`
    - `recommendation_engine.py`
    - `evolution_agent.py`
    - `knowledge_graph_updater.py`
2. Configuration file `config/nutrition_behavior.yaml` with data source credentials, LLM prompts, evolution parameters
3. Database migrations to extend Longevity Knowledge Graph schema for nutrition/behavior nodes and edges
4. Integration with Digital Twin Simulator – new intervention types for dietary/behavioral deltas
5. Unit tests for knowledge graph extraction, recommendation generation, and evolution loop
6. Documentation – how to add new data sources, interpret recommendations, run batch simulations

## Timeline Estimate (Developer Days)

| Task                                                              | Days   |
| ----------------------------------------------------------------- | ------ |
| Set up data ingestion for NHANES & UK Biobank                     | 4      |
| Build PubMed text mining pipeline (entity extraction)             | 3      |
| Create knowledge graph schema extension and ingestion             | 2      |
| Implement basic recommendation agent (LLM + KG query)             | 3      |
| Integrate causal gate (reuse existing DoWhy module)               | 2      |
| Modify Digital Twin Simulator to accept nutrition/behavior deltas | 4      |
| Build simulation runner and outcome collection                    | 3      |
| Implement genetic algorithm evolution loop                        | 4      |
| Create personalization input interface (API)                      | 2      |
| Testing & documentation                                           | 5      |
| **Total**                                                         | **32** |

## How to Start (Immediate MVP)

1. Ingest NHANES 2017-2018 dietary + lab data into Pandas DataFrame. Extract simple associations (e.g., "fiber intake correlates with lower CRP").
2. Build static knowledge graph from these associations (hard-coded rules for 10 foods and 5 behaviors).
3. Write single-user recommendation function taking age, sex, BMI and returning short text recommendation using GPT-4 with prompt: "Based on the following evidence, suggest 3 dietary changes..."
4. Run single simulation where digital twin's diet changes are applied linearly. Verify outputs change as expected.
5. Expand to full evolutionary loop.
