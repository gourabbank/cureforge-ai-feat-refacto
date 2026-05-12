# CureForge RAGE-Focused Agent Subsystem

The RAGE-Focused Agent Subsystem is a specialized multi-agent system within CureForge designed to autonomously analyze, simulate, and evolve therapeutic strategies targeting the RAGE gene (Receptor for Advanced Glycation End‑products), a validated target for cellular senescence and aging.

## Objective

The system ingests scientific literature on RAGE, generates hypotheses for blocking RAGE (via CRISPR, RNAi, small molecules, etc.), simulates effects on cellular aging and healthspan using digital twins, evolves intervention strategies via genetic algorithms, and optionally designs preclinical experiments and drafts regulatory submissions.

## Background

Russian scientists (Institute of Biology of Aging and Medicine) are developing the world’s first gene‑therapy drug blocking the RAGE receptor, supported by the Russian Ministry of Science and Higher Education. RAGE is a well‑validated, druggable target linking inflammation, senescence, and multiple age‑related diseases (diabetes, neurodegeneration, cardiovascular disease), making it ideal for CureForge’s autonomous drug discovery pipeline.

## Core Components

The subsystem comprises five main agents:

1. **RAGE Knowledge Mining Agent**
    - Sources: PubMed, ClinicalTrials.gov, patent databases (USPTO/EPO/WIPO), news about the Russian project
    - Tasks: Extract entities (RAGE gene, AGER protein, ligands, pathways, inhibitors), build a RAGE‑specific subgraph in the Longevity Knowledge Graph, identify knowledge gaps

2. **RAGE Intervention Hypothesis Generator**
    - Uses LLM + knowledge graph to propose interventions:
        - Gene editing (CRISPR‑Cas9, base/prime editing)
        - RNA interference (shRNA, siRNA, ASOs)
        - Small molecule inhibitors (known and novel)
        - Monoclonal antibodies
        - Decoy receptors (soluble RAGE)
    - Outputs per hypothesis: mechanism of action, predicted efficiency, off‑target effects, impact on Hallmarks of Aging

3. **RAGE Digital Twin Simulation Agent**
    - Extends the Digital Twin Simulator to model RAGE expression and activity
    - Parameters: Baseline RAGE expression per cell type, ligand concentrations (AGEs, S100, HMGB1), downstream effects (NF‑κB, cytokines, senescence markers)
    - For a given intervention (e.g., 50% RAGE knockdown), computes:
        - Reduction in senescent cell burden
        - Change in inflammatory biomarkers (IL‑6, TNF‑α, CRP)
        - Improvement in tissue‑specific function
        - Composite effect on CHBS and epigenetic age (by EARA)
    - Output: ΔCBA, Δhealthspan, Δmortality hazard with confidence intervals

4. **RAGE Hypothesis Evolution Engine**
    - Reuses the genetic algorithm‑based evolution engine, specialized for RAGE interventions
    - Intervention representation: vector of modality type, target site, delivery method, dose/expression level, timing
    - Fitness function: weighted sum of predicted healthspan gain, safety (off‑target score), feasibility, novelty
    - Runs evolution for >10 generations, selecting top champions

5. **RAGE Regulatory & IP Agent**
    - When a champion intervention meets fitness thresholds (e.g., >2 years healthspan gain, safety >0.9):
        - Generates provisional patent application (method of treating aging by blocking RAGE)
        - Drafts pre‑IND meeting request to FDA
        - Initiates grant proposal to Russian Ministry or international funds
        - Contacts Russian Institute of Biology of Aging and Medicine for collaboration via Collaboration Orchestrator

## Integration with Existing CureForge Modules

- Longevity Knowledge Graph – stores RAGE‑specific nodes and edges
- Evidence Mining Agent (general) – reused for RAGE literature ingestion
- Molecular Intervention Designer – for small molecule design against RAGE
- Causal Gate (DoWhy) – validates causal effect of RAGE blockade on healthspan
- Digital Twin Simulator – extended with RAGE dynamics
- Hypothesis Evolution Engine – reused for RAGE intervention evolution
- IP Agent – for patent drafting
- Regulatory Submission Agent – for IND/CTA packages
- Grant Writing Agent – for funding proposals

## Development Priorities

**Priority 0 (Immediate)**

- RAGE Knowledge Mining Agent (ingest papers, build subgraph) – 3 days
- Basic RAGE hypothesis generator (LLM + KG) – 2 days

**Priority 1 (High)**

- Extend Digital Twin Simulator with RAGE module – 5 days
- Run baseline simulations (wild‑type vs. RAGE knockout) – 2 days

**Priority 2 (Medium)**

- Integrate evolution engine for RAGE interventions – 4 days
- Add safety/off‑target prediction (CRISPR, RNAi off‑targets) – 3 days

**Priority 3 (Low)**

- Regulatory & IP automation (patent, IND, collaboration) – 3 days

Documentation & Testing – 4 days

**Total estimated developer time: 26 days**

## Deliverables

1. Python modules in `src/agents/rage/`:
    - `rage_knowledge_miner.py`
    - `rage_hypothesis_generator.py`
    - `rage_digital_twin_extension.py` (modifies `digital_twin/simulator.py`)
    - `rage_evolution_engine.py`
    - `rage_regulatory.py`
2. Configuration file `config/rage_agent.yaml` with:
    - PubMed query terms
    - Genetic algorithm parameters
    - Safety thresholds
3. Database migrations extending LKG with RAGE‑specific nodes (e.g., `RAGE_gene`, `RAGE_protein`, `RAGE_ligands`)
4. Integration tests simulating a RAGE knockout and verifying healthspan improvement
5. Documentation:
    - How to add new RAGE intervention modalities
    - How to interpret simulation outputs
    - How to trigger patent filing

## Immediate MVP Steps (First Week)

1. Run literature query on PubMed for `"RAGE AND aging"` (limit to reviews and clinical trials), extract 50 most relevant papers
2. Manually curate a small knowledge graph of known RAGE interventions (CRISPR mouse studies, azeliragon clinical trials, sRAGE studies)
3. Implement simple hypothesis generator using fixed prompt to list 5 potential RAGE‑blocking strategies (CRISPR, siRNA, small molecule, antibody, soluble decoy)
4. Run single simulation setting RAGE expression to 10% of normal in digital twin’s immune cells; observe changes in inflammatory biomarkers and senescent cell burden
5. Write short internal report summarizing potential of RAGE blockade based on simulation results

Once MVP validates concept, proceed with full evolution engine and regulatory automation.

## Collaboration with Russian Institute (Optional)

The agent will generate a collaboration proposal to the Institute of Biology of Aging and Medicine, offering to share digital twin simulation capabilities in exchange for experimental data via the Collaboration Orchestrator.

## Statistical Highlights

- RAGE links inflammation, senescence, and age‑related diseases (diabetes, neurodegeneration, cardiovascular disease)
- Russian project supported by Russian Ministry of Science and Higher Education
- Development estimated at 26 developer hours across five agents
- Fitness thresholds for regulatory action: >2 years predicted healthspan gain, safety score >0.9
