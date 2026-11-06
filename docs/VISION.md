> **ARCHIVED — planning.md v1.0 (2 Nov 2026).** Superseded by `planning.md` v2.0 wherever they conflict. Read a section only when a phase file points to it (e.g. VISION §8.4 risk concepts, §18 post-qualification roadmap, §23.2 literature topics).

# HYPERBOREA --- Master Project Plan

**Document:** `planning.md`\
**Version:** 1.0 --- Initial planning baseline\
**Planning date:** 2 November 2026\
**Competition:** ISI --- National-level preliminary round\
**Qualification deadline:** 10 days from planning date (provisionally 12
November 2026; verify against the official notice)\
**Qualification format:** Live demonstration and presentation, 10--15
minutes\
**Post-qualification development window:** Approximately 60 days\
**Team baseline:** 4 members; team may expand\
**Pilot geography:** A small neighbourhood / ward segment in Salt Lake,
Kolkata\
**Project status:** Pre-development planning

> **Document status:** This is the working source of truth for project
> scope, architecture, delivery and agent-assisted development. The
> official competition guidelines have been reported as available but
> have not yet been provided in this conversation. Before implementation
> is locked, attach or review those guidelines and update any
> conflicting requirements in this document.

------------------------------------------------------------------------

## 1. Executive Summary

### 1.1 Project concept

**Hyperborea** is a geospatial urban intelligence platform designed to
model the relationships between infrastructure, environmental
conditions, climate hazards and urban development.

It combines a 3D geospatial interface inspired by the interaction
patterns of God's Eye View with a data platform, infrastructure
intelligence modules, an urban relationship engine and scenario-based
decision support.

Hyperborea has two equally important objectives:

1.  **Understand the existing city:** observe infrastructure and
    environmental conditions, identify vulnerabilities, and estimate how
    hazards or asset failures may affect connected systems.
2.  **Evaluate future development:** assess proposed buildings or
    infrastructure expansions against existing network capacity,
    environmental exposure, accessibility and projected risk.

The platform is intended to support multiple stakeholder groups through
role-specific access in the future: municipal authorities, urban
planners and engineers, developers, and citizens. The qualification
prototype will use **one administrator role with access to all
implemented features**.

### 1.2 Core proposition

A city is not a set of independent assets. Drainage, roads, electricity,
water, buildings, transport, climate and environmental systems depend on
one another.

Hyperborea's central technical proposition is to represent these
relationships in a **geospatial, heterogeneous, time-aware urban
dependency model** and use that model to:

-   identify infrastructure vulnerabilities;
-   estimate how a hazard or failure may propagate;
-   identify assets and services that may be affected;
-   evaluate proposed construction and expansion;
-   compare development and mitigation scenarios; and
-   explain the evidence, assumptions and uncertainty behind its
    outputs.

### 1.3 Product positioning

> Hyperborea is a geospatial urban intelligence platform that models
> dependencies between infrastructure, environmental conditions and
> human development to identify present vulnerabilities, assess
> cascading risks and evaluate future urban expansion.

Do not position Hyperborea merely as a collection of God's Eye, DrainOS,
weather, traffic and disaster dashboards. Its differentiator is the
shared relationship model and the decision workflows built on top of it.

------------------------------------------------------------------------

## 2. Vision, Mission and Objectives

### 2.1 Vision

Enable evidence-informed, climate-aware and infrastructure-resilient
urban development through an integrated geospatial intelligence system.

### 2.2 Mission

Unify heterogeneous urban data, infrastructure models and environmental
intelligence in one platform so that users can understand the current
state of a region, explore possible future conditions and evaluate
development decisions before implementation.

### 2.3 Product objectives

1.  Provide a 3D and 2D geospatial view of a bounded urban area.
2.  Represent important urban assets and their spatial and functional
    relationships.
3.  Combine public, manually curated and synthetic data while clearly
    labelling provenance.
4.  Integrate existing models, APIs and engineering tools rather than
    rebuilding mature technologies.
5.  Demonstrate at least one end-to-end cascading-risk scenario.
6.  Demonstrate at least one proposed-development assessment.
7.  Explain outputs with evidence, assumptions, confidence and
    limitations.
8.  Establish an architecture that can be expanded during the
    approximately 60-day post-qualification phase.

### 2.4 Non-goals for the 10-day qualification prototype

The prototype will not claim to:

-   monitor every asset in Kolkata;
-   provide authoritative structural safety certification;
-   predict the exact date or certainty of a building collapse;
-   provide a complete real-time electrical grid model;
-   replace municipal engineering or statutory approval;
-   provide a fully calibrated city-wide flood model;
-   guarantee future climate or traffic conditions;
-   train foundation models from scratch; or
-   deliver production-grade municipal deployment.

These may be investigated later where data, expertise, validation and
permissions permit.

------------------------------------------------------------------------

## 3. Competition and Delivery Strategy

### 3.1 Competition baseline

  -----------------------------------------------------------------------
  Item                                Current understanding
  ----------------------------------- -----------------------------------
  Competition                         ISI

  Stage                               National-level preliminary round

  Submission window                   10 days from 2 November 2026

  Provisional date                    12 November 2026; confirm official
                                      date

  Presentation                        Same date as submission

  Evaluation                          Live demonstration and presentation

  Presentation duration               10--15 minutes

  Known deliverables                  Working prototype, PPT, GitHub
                                      repository, project
                                      documentation/report, demo video,
                                      research paper/literature review

  Official guidelines                 Team says complete guidelines are
                                      available; document not yet
                                      reviewed
  -----------------------------------------------------------------------

**Immediate action:** Add the official guidelines, problem statement,
judging rubric, submission instructions and any template files to the
project workspace. A team member must extract every mandatory
requirement and create a compliance checklist before the first
development day is complete.

### 3.2 Two-stage strategy

#### Stage 1 --- Qualification prototype (10 days)

Objective: demonstrate a coherent and technically credible proof of
concept that makes the case for further development.

Required outcomes:

-   working geospatial interface;
-   one bounded Salt Lake pilot area;
-   multiple urban and environmental data layers;
-   shared asset and relationship data model;
-   functioning relationship engine;
-   one disaster / cascading-risk scenario;
-   one proposed-development scenario;
-   visible distinction between observed, modelled and simulated
    information;
-   live demonstration, PPT, repository and documentation.

The prototype should have broad feature coverage but must be honest
about which modules are data-backed, rule-based, simulated or
experimental.

#### Stage 2 --- Main project (approximately 60 days)

Objective: deepen the relationship intelligence and prediction
capabilities, improve real-world data coverage, validate the models and
deliver a more complete integrated platform.

Priority areas:

-   relationship intelligence and cascading-risk prediction;
-   improved geospatial and infrastructure datasets;
-   model calibration and evaluation;
-   field observations where access is possible;
-   more realistic hydraulic and network models;
-   better development suitability and multi-objective scenario
    analysis;
-   role-based access for different stakeholder groups;
-   full integrated platform and final competition demonstration.

### 3.3 Definition of success

**Qualification success means:**

-   the system runs reliably on demonstration hardware;
-   the 3D interface is connected to actual Hyperborea data and
    workflows;
-   at least one scenario runs end to end;
-   the relationship engine produces explainable results;
-   a proposed development can be assessed;
-   evidence and synthetic data are not confused;
-   the team can explain the architecture, assumptions and limitations.

A large number of unfinished features is not a success criterion.

------------------------------------------------------------------------

## 4. Scope and Feature Inventory

### 4.1 Platform modules

  -----------------------------------------------------------------------
  Module                  Intended capability     Qualification
                                                  implementation
  ----------------------- ----------------------- -----------------------
  Geospatial command      3D/2D regional view,    Working
  centre                  layers, asset selection 

  Building intelligence   Building footprints,    GIS attributes; limited
                          attributes, condition   CV demonstration if
                          indicators              feasible

  Drainage intelligence   Drain assets,           Curated/synthetic
                          connectivity, capacity  network plus simplified
                          and vulnerability       engineering rules or
                                                  SWMM

  Electrical intelligence Transformers,           Curated/synthetic
                          substations, network    network; clearly
                          links, capacity and     labelled
                          exposure                

  Transportation          Roads, connectivity,    OSM road network and
                          accessibility and       routing/traffic data
                          commute impact          where available

  Weather                 Current and forecast    Existing API
                          weather indicators      

  Climate                 Historical trends and   Public historical data
                          climate-related         and derived indicators
                          exposure indicators     

  Water                   Water availability and  Public/curated
                          quality observations    observations; sample
                                                  data only when labelled

  Air/environment         Air quality, land       Public data/API and
                          cover, vegetation and   remote sensing where
                          environmental           feasible
                          indicators              

  Disaster intelligence   Hazard scenario and     Scenario engine and
                          potential impact        relationship
                          assessment              propagation

  Infrastructure health   Asset condition and     Rule-based indicators
                          capacity risk           and limited CV

  Relationship engine     Spatial, physical and   Central graph model
                          functional dependencies 

  Development             Proposed building/site  GIS suitability and
  intelligence            assessment              capacity rules

  What-if simulation      Compare baseline and    At least two comparable
                          intervention scenarios  scenarios

  Reporting               Evidence, risk,         Downloadable or
                          constraints and         on-screen report
                          recommendations         

  Access control          Role-specific           One administrator role
                          permissions             for qualification
  -----------------------------------------------------------------------

### 4.2 Priority labels

-   **P0 --- Qualification critical:** must work for the initial round.
-   **P1 --- Important:** implement if P0 is stable.
-   **P2 --- Post-qualification:** deepen during the 60-day phase.

#### P0

1.  Geospatial interface and pilot boundary.
2.  Common asset schema and spatial database.
3.  Roads and building footprints.
4.  Drainage network representation.
5.  Weather/rainfall input.
6.  Urban relationship graph.
7.  Risk propagation / scenario engine.
8.  Proposed-development assessment.
9.  Evidence and data-status labels.
10. Reliable live demonstration.

#### P1

1.  Electrical network representation.
2.  Air-quality and water-quality layers.
3.  Basic CV inference.
4.  Traffic or commute integration.
5.  Report export.
6.  Additional climate indicators.
7.  More polished dashboards.

#### P2

1.  Advanced GNN models.
2.  Extensive model fine-tuning.
3.  Calibrated multi-event flood modelling.
4.  Field-verified asset condition.
5.  Multi-role access and permissions.
6.  Multi-objective urban optimization.
7.  Large-area or multi-city support.
8.  Production deployment and operational monitoring.

------------------------------------------------------------------------

## 5. Pilot Geography and Data Strategy

### 5.1 Pilot region

-   City: Kolkata metropolitan area.
-   Selected area: Salt Lake.
-   Scale: one small neighbourhood or ward segment.
-   Exact boundary: **TBD**.
-   Selection principle: choose the smallest area that offers useful
    building and road coverage, plausible drainage context, accessible
    environmental data and a demonstrable development scenario.

Do not choose a boundary solely because it looks impressive in a 3D map.
Choose it based on data availability and a coherent scenario.

### 5.2 Data strategy

Use a hybrid data strategy:

1.  **Public data:** open geospatial datasets, public APIs, satellite
    products and government/open-data sources.
2.  **Manually curated data:** assets digitized or checked by the team
    from credible maps, documents or field observations.
3.  **Synthetic data:** missing infrastructure attributes, network
    capacities, asset conditions or scenario inputs created for
    controlled demonstration.

Every record must carry provenance and status metadata. Synthetic data
must never be presented as observed municipal infrastructure.

### 5.3 Data status taxonomy

Every displayed data item or derived result should be identifiable as
one of:

-   **Observed:** directly measured or obtained from a cited source.
-   **Curated:** manually transcribed, digitized or verified by the
    team.
-   **Modelled:** calculated from observed/curated inputs using a
    defined model or rule.
-   **Simulated:** generated for a hypothetical scenario or test.
-   **Unknown / unavailable:** not known or not sufficiently supported.

Include source, retrieval date, spatial coverage, temporal coverage,
units, licence/terms, transformations and confidence where possible.

### 5.4 Candidate data sources and tools

The team must verify availability, geographic coverage, access terms,
update frequency and licence before use.

  -----------------------------------------------------------------------
  Data need               Candidate source/tool   Notes
  ----------------------- ----------------------- -----------------------
  Roads and paths         OpenStreetMap           Check ODbL attribution
                                                  and database
                                                  obligations

  Building footprints     OpenStreetMap,          Validate completeness
                          available open building locally
                          datasets                

  Satellite imagery       Copernicus Sentinel-2   Useful for land cover
                                                  and change; not a
                                                  substitute for
                                                  structural inspection

  Elevation               Copernicus DEM or other Resolution and vertical
                          suitable open DEM       accuracy must be
                                                  recorded

  Weather                 Open-Meteo or another   Verify API terms and
                          documented weather API  historical/forecast
                                                  availability

  Air quality             Official/open           Record station location
                          monitoring sources      and measurement time
                          where available         

  Water quality           Public agency datasets  Do not fabricate
                          or field observations   observed quality values

  Drainage                Public municipal        Underground network
                          records, open maps,     completeness may be
                          curated or synthetic    poor
                          assets                  

  Electricity             Public records or       Avoid implying access
                          manually                to confidential grid
                          curated/synthetic       topology
                          network                 

  Traffic                 OpenStreetMap routing   Distinguish live
                          plus available traffic  traffic from routing
                          feeds                   estimates

  Disaster history        Credible government and Preserve event date,
                          research records        location and source

  Hydraulic simulation    EPA SWMM                Use a simplified,
                                                  documented catchment
                                                  model if data is
                                                  limited
  -----------------------------------------------------------------------

### 5.5 Data acquisition register

Create `data/DATA_SOURCES.md` with one entry per dataset:

-   Dataset name and provider.
-   URL or access method.
-   Licence / terms.
-   Date accessed.
-   Spatial and temporal coverage.
-   Coordinate reference system.
-   Schema and units.
-   Missingness and quality concerns.
-   Transformation / preprocessing.
-   Whether data is observed, curated, modelled or simulated.
-   Which module uses it.
-   Known limitations.

### 5.6 Geographic and data validation

-   Use a consistent projected coordinate reference system for local
    distance/area calculations; document the CRS.
-   Preserve source coordinates and transformations.
-   Validate geometries and topology.
-   Check for duplicate assets and disconnected network segments.
-   Confirm that road, drainage and electrical network layers are not
    accidentally treated as the same graph.
-   Never infer underground connectivity solely from surface proximity.
-   Store timestamps with timezone and source context.
-   Keep raw source files immutable; store processed data separately.

------------------------------------------------------------------------

## 6. System Architecture

### 6.1 Architectural principles

1.  The geospatial interface must be replaceable without rewriting the
    intelligence engine.
2.  The relationship engine must be independent of the frontend.
3.  Data ingestion, normalization, storage, modelling and visualization
    must be separate concerns.
4.  All modules must use shared identifiers and documented API
    contracts.
5.  Synthetic and observed data must remain distinguishable end to end.
6.  Models must expose assumptions, provenance and
    confidence/uncertainty where possible.
7.  The prototype should prefer a modular monolith over unnecessary
    microservices.
8.  The system must run locally with documented setup instructions.

### 6.2 High-level architecture

``` text
                  HYPERBOREA WEB APPLICATION
          3D/2D GIS • Layers • Scenarios • Dashboards
                              |
                         API Gateway
                              |
       +----------------------+----------------------+
       |                      |                      |
  Asset & GIS API        Scenario API           Report API
       |                      |                      |
       +----------------------+----------------------+
                              |
                    URBAN DATA FOUNDATION
             PostgreSQL + PostGIS + file storage
                              |
       +----------------------+----------------------+
       |                      |                      |
 Infrastructure         Climate &             External Data
 Intelligence           Environment            Ingestion
       |                      |                      |
       +----------------------+----------------------+
                              |
                URBAN RELATIONSHIP ENGINE
        Heterogeneous graph • Dependency rules • Risk propagation
                              |
                 DECISION / EXPLANATION ENGINE
       Risk factors • Scenario comparison • Recommendations
```

### 6.3 Recommended stack

  ------------------------------------------------------------------------
  Layer                   Recommended technology  Reason
  ----------------------- ----------------------- ------------------------
  Frontend                React + TypeScript      Component-based
                                                  interface

  3D geospatial           CesiumJS                3D globe and geospatial
                                                  visualization

  2D GIS                  Leaflet or MapLibre GL  Practical 2D map and
                          JS                      layer workflows

  Backend                 Python FastAPI          AI, GIS and model
                                                  integration

  Database                PostgreSQL + PostGIS    Relational and spatial
                                                  data

  Graph prototype         NetworkX                Fast, transparent graph
                                                  algorithms

  Graph ML later          PyTorch Geometric       Heterogeneous/temporal
                                                  graph experiments

  Geospatial processing   GeoPandas, Shapely,     Vector/raster processing
                          Rasterio                

  CV                      PyTorch, Ultralytics    Pretrained inference and
                          YOLO, OpenCV            selective fine-tuning

  Forecasting             scikit-learn,           Baseline predictive
                          XGBoost/LightGBM,       models
                          statsmodels as          
                          appropriate             

  Hydraulic modelling     EPA SWMM where          Established stormwater
                          appropriate             modelling

  Visualization           CesiumJS, charting      Spatial and time-series
                          library                 presentation

  Containers              Docker / Docker Compose Reproducible local setup

  Version control         Git + GitHub            Collaboration and review

  Testing                 pytest, frontend test   Reliability
                          framework, API tests    

  Documentation           Markdown                Shared project
                                                  documentation
  ------------------------------------------------------------------------

Do not add Neo4j, Kubernetes, blockchain, a message broker or multiple
databases unless a concrete requirement justifies the operational cost.

### 6.4 God's Eye decision

Selected reference: **Bilawal Sidhu's original God's Eye View**.

Current decision: implement Hyperborea independently using CesiumJS and
appropriate open technologies, while retaining the important user-facing
capabilities and interaction patterns of the reference.

Interpretation of "retain almost all functionality":

-   Retain the desired 3D globe/map experience.
-   Retain useful layer controls and geospatial exploration patterns.
-   Recreate relevant visualization and navigation capabilities using
    independently implemented Hyperborea components.
-   Add urban infrastructure, environment, risk and scenario workflows.
-   Do not assume that all original integrations, data feeds or
    proprietary provider services can be copied or used.
-   Do not copy source code unless the team deliberately changes to a
    compliant fork/reuse approach and completes a licence review.

Before implementation, inspect the original repository, its current
licence, dependencies, third-party services, data providers and
attribution requirements. A source-code licence does not automatically
grant rights to third-party datasets, imagery, APIs or models. Preserve
required notices and comply with provider terms.

**Architecture rule:** Hyperborea's data and intelligence APIs must not
depend on God's Eye's internal implementation.

------------------------------------------------------------------------

## 7. Urban Data Model

### 7.1 Core entities

Initial entity types:

-   Region / administrative boundary.
-   Building.
-   Road segment.
-   Drain segment.
-   Drain inlet / manhole.
-   Pump / outfall.
-   Transformer / substation / electrical segment.
-   Water asset / water observation.
-   Environmental monitoring station.
-   Weather observation / forecast.
-   Critical facility (e.g. hospital, school, emergency facility).
-   Proposed development.
-   Hazard event.
-   Inspection / maintenance record.
-   Scenario.
-   Model output / risk assessment.

### 7.2 Common asset fields

Every asset should have a stable internal ID and, where relevant:

``` text
asset_id
asset_type
name
geometry
location
source_id
data_status
source_reference
observed_at
ingested_at
last_verified_at
condition
capacity
capacity_unit
operational_status
attributes_json
confidence
notes
```

Do not force every field onto every asset. Use typed tables or validated
schemas where possible; use JSON attributes only for genuinely variable
properties.

### 7.3 Relationship types

Examples:

-   `CONNECTED_TO`
-   `DRAINS_TO`
-   `SUPPLIES`
-   `SERVES`
-   `ACCESSIBLE_VIA`
-   `LOCATED_WITHIN`
-   `EXPOSED_TO`
-   `NEAR`
-   `DEPENDS_ON`
-   `OVERLOADS`
-   `AFFECTS`
-   `MITIGATED_BY`
-   `PROPOSED_ADJACENT_TO`

Each relationship should include:

``` text
relationship_id
source_asset_id
target_asset_id
relationship_type
direction
weight_or_capacity
unit
valid_from
valid_to
evidence_source
data_status
confidence
assumptions
```

A relationship must have a defined meaning. Do not use arbitrary edge
weights without explaining their units or derivation.

------------------------------------------------------------------------

## 8. Urban Relationship Intelligence Engine

### 8.1 Role in Hyperborea

This is the central integration and differentiation component.

It should combine:

-   spatial relationships;
-   physical network connectivity;
-   service dependencies;
-   capacity constraints;
-   environmental exposure;
-   temporal state; and
-   scenario-specific changes.

### 8.2 Initial implementation

For the qualification prototype:

1.  Create a heterogeneous graph from shared asset records.
2.  Add explicit relationships from source data, curated topology and
    documented rules.
3.  Attach asset condition, capacity and exposure attributes.
4.  Implement graph traversal and rule-based dependency propagation.
5.  Calculate transparent risk indicators.
6.  Display affected assets and the relationship path that produced the
    result.
7.  Allow scenario parameters to alter the state of selected assets or
    environmental inputs.

Use NetworkX initially. A graph database is optional. Do not train a GNN
merely to claim AI; an explainable rule-based graph can be more
defensible with sparse data.

### 8.3 Example cascading-risk workflow

``` text
Extreme rainfall scenario
          |
          v
Rainfall / runoff input
          |
          v
Drainage capacity assessment
          |
          v
Potentially overloaded drainage assets
          |
          v
Spatial exposure and connected road segments
          |
          v
Electrical asset exposure assessment
          |
          v
Potentially affected critical facilities / services
          |
          v
Explainable impact summary and intervention options
```

This is a scenario-based estimate, not proof that a failure will occur.

### 8.4 Risk model design

Separate the concepts:

-   **Hazard:** intensity and probability/likelihood of an external
    event.
-   **Exposure:** assets and people in the affected area.
-   **Vulnerability:** susceptibility of an asset to damage or
    disruption.
-   **Consequence:** impact if the asset is affected.
-   **Risk:** a defined combination of the above.

A simple prototype score may use normalized components, but the formula,
weights and assumptions must be shown. Do not label an arbitrary score
as a scientifically calibrated probability.

### 8.5 Explanation output

For each risk result, show:

-   affected asset(s);
-   initiating condition;
-   dependency path;
-   input values and sources;
-   model/rule used;
-   assumptions;
-   data status;
-   confidence or uncertainty;
-   possible mitigation;
-   what additional data would improve the assessment.

### 8.6 Post-qualification research direction

Investigate whether a heterogeneous, temporal, geospatial graph improves
risk propagation and prediction compared with:

-   independent asset-level models;
-   conventional GIS overlays;
-   simple threshold rules;
-   non-graph machine-learning baselines.

Potential later methods include heterogeneous GNNs, temporal graph
models and graph-based anomaly detection. Use them only when the data
volume, labels and evaluation design justify them.

------------------------------------------------------------------------

## 9. Intelligence Modules

### 9.1 Building intelligence

**Qualification:** - Load building footprints and available
attributes. - Display height/use/age only where sourced or labelled as
assumed. - Derive simple density and land-use indicators. - Optionally
demonstrate pretrained building/roof/road detection on suitable imagery.

**Later:** - Fine-tune selected CV models on locally labelled data. -
Add inspection workflows and structural-condition indicators. -
Integrate engineering inspection data where permissions and expertise
exist.

**Safety/validity boundary:** Satellite imagery and generic CV
detections cannot certify structural integrity or predict an individual
building's collapse.

### 9.2 Drainage intelligence

**Qualification:** - Represent a small drainage network with inlets,
segments, junctions, pumps/outfalls where data is available. - Use
curated or synthetic capacities when actual capacities are
unavailable. - Run simplified capacity checks or a bounded SWMM model. -
Identify possible bottlenecks under a rainfall scenario.

**Later:** - Improve catchment delineation and elevation inputs. -
Calibrate against observed rainfall/flood information. - Add field
inspection and maintenance evidence. - Evaluate model performance
against documented events.

### 9.3 Electrical intelligence

**Qualification:** - Represent selected transformers/substations/links
using public, curated or synthetic data. - Demonstrate capacity and
flood-exposure logic. - Make missing or assumed topology obvious.

**Later:** - Seek authoritative or permissioned network data. - Improve
load and outage modelling. - Model dependencies with drainage, roads and
critical facilities.

Do not imply that a synthetic network is the actual distribution grid.

### 9.4 Transportation and commute

**Qualification:** - Use road network connectivity and basic
routing/accessibility. - Identify road segments potentially affected in
the disaster scenario. - Use live traffic only if a permitted and
reliable feed is available.

**Later:** - Add time-dependent traffic, travel-time and service
accessibility analysis. - Evaluate changes from proposed development.

### 9.5 Weather and climate

Distinguish weather forecasts from climate analysis.

**Qualification:** - Integrate current/forecast weather data from a
documented API. - Add historical rainfall/temperature indicators where
accessible. - Run user-selected rainfall scenarios. - Show the time
range and source.

**Later:** - Add longer-term climate datasets and scenario analysis. -
Quantify uncertainty and downscaling limitations.

### 9.6 Water

**Qualification:** - Display available water-quality observations or a
clearly labelled demonstration dataset. - Show sampling location, date,
parameter and unit. - Avoid interpolating sparse observations as if they
were continuous measurements.

**Later:** - Add field sampling and sensor integration if access
permits. - Study groundwater/water-quality trends with adequate temporal
coverage.

### 9.7 Air quality and environment

**Qualification:** - Integrate available monitoring observations. - Add
land-cover/vegetation indicators from suitable remote-sensing
products. - Display station location and observation time.

**Later:** - Add spatial/temporal modelling and exposure assessment. -
Validate derived surfaces against independent measurements.

### 9.8 Disaster intelligence

**Qualification:** - Implement one carefully defined
extreme-rainfall/flood scenario. - Combine drainage capacity rules/model
outputs with spatial exposure and graph dependencies. - Visualize
potentially affected assets and routes.

**Later:** - Add heat, storm, service outage and other hazard scenarios
as data allows. - Improve hazard models and cascading consequence
analysis.

------------------------------------------------------------------------

## 10. Urban Development Intelligence

### 10.1 Purpose

Evaluate a proposed building or infrastructure expansion against the
current and scenario-adjusted condition of the surrounding urban system.

### 10.2 Qualification workflow

1.  Administrator selects a site or draws a proposed development
    footprint.
2.  Administrator enters a small set of project assumptions
    (e.g. building type, approximate floor area, expected occupancy or
    demand assumptions).
3.  System retrieves surrounding buildings, roads, drainage, electrical
    and environmental layers.
4.  System estimates service demand using explicit assumptions.
5.  System checks relevant network capacity and exposure.
6.  System generates constraints, risks and potential mitigation
    requirements.
7.  Administrator compares at least two scenarios or sites.

### 10.3 Output categories

-   `Suitable under current assumptions`
-   `Conditionally suitable — upgrades or further assessment required`
-   `Potentially unsuitable under current assumptions`
-   `Insufficient data`

Avoid presenting the output as a statutory planning approval or
engineering certification.

### 10.4 Multi-objective assessment

Potential dimensions:

-   drainage adequacy;
-   electricity availability;
-   water availability;
-   road access and commute;
-   flood exposure;
-   heat exposure;
-   land-use compatibility;
-   environmental impact;
-   proximity to critical facilities.

For the prototype, use transparent criteria and weights. Later,
investigate sensitivity analysis and multi-objective optimization.

### 10.5 Signature comparison

Show:

-   Scenario A: proposed development without upgrades.
-   Scenario B: same development with selected infrastructure upgrades.
-   Option C: alternative site, if data supports comparison.

Explain which assumptions change and how the assessment changes.

------------------------------------------------------------------------

## 11. AI/ML Strategy

### 11.1 General principle

Reuse established technologies and pretrained models. Fine-tune only
where useful data and time permit. The team's contribution should focus
on the integration, relationship model, scenario logic, validation and
decision support.

### 11.2 Qualification approach

  ------------------------------------------------------------------------
  Problem                 Initial method          Later direction
  ----------------------- ----------------------- ------------------------
  Asset detection         Pretrained CV model /   Fine-tuned local model
                          manual GIS              

  Image classification    Pretrained model and    Region-specific
                          limited labels          validation

  Infrastructure anomaly  Rules and simple        Better labelled-data
                          anomaly baseline        model

  Climate indicators      Existing API and        Calibrated forecasting
                          statistical baselines   

  Drainage capacity       Engineering rules /     Calibrated hydraulic
                          SWMM                    model

  Risk propagation        NetworkX graph rules    Heterogeneous/temporal
                                                  graph learning

  Site suitability        GIS multicriteria       Multi-objective
                          analysis                optimization

  Report generation       Deterministic templates Optional grounded
                                                  language assistance
  ------------------------------------------------------------------------

### 11.3 Model selection requirements

For every model record:

-   task and intended use;
-   model name and version;
-   source and licence;
-   training data provenance;
-   input/output format;
-   inference requirements;
-   evaluation metric;
-   known limitations;
-   whether fine-tuned;
-   deployment location (local/cloud);
-   reproducibility instructions.

### 11.4 Model evaluation

Use task-appropriate metrics:

-   CV: precision, recall, F1, mAP, confusion matrix.
-   Classification: class-wise precision/recall, F1, calibration where
    appropriate.
-   Forecasting: MAE/RMSE and baseline comparison; use time-based
    splits.
-   Risk ranking: precision/recall at selected thresholds, ranking
    metrics and event-based validation where labels exist.
-   Hydraulic model: compare simulated outputs with available
    observations or published benchmark cases.
-   Site assessment: sensitivity analysis and expert/engineering review,
    not just accuracy against synthetic labels.

Do not claim model performance without a reproducible test set and
documented evaluation.

### 11.5 AI limitations

-   A model trained on synthetic labels does not establish real-world
    predictive accuracy.
-   Public imagery may be outdated, low-resolution or incomplete.
-   Data leakage can inflate results.
-   Risk scores are not probabilities unless calibrated and validated as
    such.
-   LLM-generated explanations must be grounded in actual model outputs
    and source data.

------------------------------------------------------------------------

## 12. User Interface and Experience

### 12.1 Qualification role

One **Administrator** role with access to all implemented modules.

Do not spend qualification time implementing multiple permission
systems. Keep the code architecture ready for role-based access later.

### 12.2 Main application areas

1.  **Command Centre:** regional 3D map, status summary and active
    scenario.
2.  **Layer Manager:** buildings, roads, drainage, electrical, weather,
    environment and hazards.
3.  **Asset Inspector:** selected asset details, provenance,
    relationships and condition.
4.  **Relationship Explorer:** graph view of dependencies and affected
    assets.
5.  **Risk & Disaster Lab:** scenario inputs, outputs and propagation
    paths.
6.  **Development Assessment:** proposed site, assumptions, constraints
    and comparison.
7.  **Reports:** summary, evidence, limitations and recommended next
    steps.

### 12.3 UI requirements

-   Make observed/modelled/simulated status visible.
-   Show units and timestamps.
-   Provide map legend and layer toggles.
-   Use clear risk explanations rather than unexplained red/green
    markers.
-   Keep the map responsive and avoid loading every layer at once.
-   Provide a fallback 2D view if 3D rendering is slow.
-   Ensure the demo can be run without depending on an unreliable live
    API.

### 12.4 Visual design

Recommended style: professional geospatial command centre, high
contrast, restrained use of warning colours, clear map legends and
compact technical panels. Avoid excessive animation and decorative
dashboards that obscure the actual analytical workflow.

------------------------------------------------------------------------

## 13. Team Structure and Responsibilities

### 13.1 Team baseline

-   Four active members.
-   Each member has worked with at least one of the listed skill areas;
    the team collectively reports exposure to AI/ML, web, app, backend,
    frontend, data engineering, GIS, blockchain, DevOps/cloud, UI/UX and
    research/mathematics.
-   Technical architecture is a shared responsibility.
-   Team may expand after qualification.

### 13.2 Suggested workstreams

  -----------------------------------------------------------------------
  Workstream              Primary responsibility  Shared interface
  ----------------------- ----------------------- -----------------------
  Geospatial frontend     CesiumJS, React,        API contracts and map
                          layers, asset inspector feature schema

  Backend/data/GIS        FastAPI, PostGIS,       Shared entity and
                          ingestion,              geometry schema
                          normalization           

  AI/ML/environment       CV, weather/environment Model input/output
                          integration, model      contracts
                          evaluation              

  Relationship/scenario   Graph schema,           Shared asset and
  engine                  dependency rules, risk  relationship schema
                          propagation,            
                          development logic       

  All members             Integration, review,    Definition of done
                          testing, presentation   
  -----------------------------------------------------------------------

One person may own multiple workstreams. Assign one named owner per task
even when work is collaborative.

### 13.3 Team operating rules

-   One person owns each task's completion.
-   Architecture changes require review by at least two members.
-   No agent or member changes shared schemas without notifying the
    team.
-   Merge frequently; avoid large unreviewed branches.
-   Maintain a daily integration build.
-   Record decisions in `docs/DECISIONS.md`.

------------------------------------------------------------------------

## 14. AI Agent and Coding Workflow

### 14.1 Available tools

-   VS Code.
-   GitHub.
-   Docker.
-   Claude Code and Claude Opus access as reported by the team.
-   ChatGPT.
-   Codex may become available.
-   Google Colab.
-   Kaggle Notebooks.
-   Two HP OMEN laptops:
    -   Laptop A: 16 GB DDR5, RTX 4050; reported 6 GB VRAM.
    -   Laptop B: 24 GB DDR5, RTX 5050; verify exact GPU VRAM and power
        specifications.

**Hardware note:** Verify the exact RTX 5050 laptop specification with
the manufacturer's page or GPU utility. Do not assume its VRAM or TGP
based only on an informal description. Both laptops can support
development; use Colab/Kaggle for heavier training when free quota and
availability permit.

### 14.2 Human-led AI assistance

The selected workflow is human-led development with AI assistance, not
fully autonomous agents.

AI should accelerate implementation, tests, documentation and debugging.
Humans remain responsible for:

-   architecture and trade-offs;
-   data source and licence review;
-   scientific assumptions;
-   relationship semantics;
-   model validation;
-   security;
-   final integration and acceptance.

### 14.3 Suggested agent roles

These are task roles, not necessarily separate subscriptions or
autonomous agents.

1.  **Architecture assistant:** reviews requirements, designs
    interfaces, checks consistency.
2.  **Frontend assistant:** implements map, panels, layer controls and
    workflows.
3.  **Backend assistant:** implements APIs, schemas and ingestion.
4.  **AI/GIS assistant:** builds preprocessing, model wrappers and
    spatial analysis.
5.  **Relationship-engine assistant:** implements graph and scenario
    logic.
6.  **QA assistant:** writes tests, reproduces bugs and reviews edge
    cases.
7.  **Documentation assistant:** maintains setup instructions,
    architecture and demo scripts.

### 14.4 Agent task template

Every substantial task assigned to an AI assistant must include:

``` text
TASK ID:
TASK NAME:
OWNER:
OBJECTIVE:
CONTEXT:
FILES / MODULES IN SCOPE:
FILES / MODULES OUT OF SCOPE:
DEPENDENCIES:
INPUT CONTRACT:
OUTPUT CONTRACT:
TECHNOLOGY CONSTRAINTS:
DATA / SOURCE REQUIREMENTS:
ACCEPTANCE CRITERIA:
TESTS REQUIRED:
KNOWN LIMITATIONS:
DELIVERABLES:
```

### 14.5 AI coding rules

-   Read existing files before editing.
-   Do not invent API responses, datasets or library capabilities.
-   Do not silently replace dependencies or framework versions.
-   Do not rewrite unrelated modules.
-   Use typed interfaces and validation.
-   Add tests with meaningful changes.
-   Explain assumptions and unresolved questions.
-   Never commit secrets, API keys or credentials.
-   Do not fabricate model metrics.
-   Do not label synthetic data as real.
-   Keep changes small and reviewable.
-   Ask before changing shared schemas or architecture.
-   Report files changed, commands run, test results and known issues.

### 14.6 Parallel development

Parallelize independent modules only after shared contracts are agreed.
Use feature branches and pull requests. Avoid concurrent edits to the
same core files.

------------------------------------------------------------------------

## 15. Repository and Project Structure

Suggested starting structure:

``` text
hyperborea/
├── README.md
├── planning.md
├── LICENSE
├── .gitignore
├── .env.example
├── docker-compose.yml
├── docs/
│   ├── ARCHITECTURE.md
│   ├── API_CONTRACTS.md
│   ├── DATA_SOURCES.md
│   ├── DATA_DICTIONARY.md
│   ├── DECISIONS.md
│   ├── MODEL_CARD_TEMPLATE.md
│   ├── VALIDATION_PLAN.md
│   ├── DEMO_SCRIPT.md
│   └── SUBMISSION_CHECKLIST.md
├── frontend/
│   ├── src/
│   └── package.json
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── main.py
│   └── tests/
├── intelligence/
│   ├── infrastructure/
│   ├── climate/
│   ├── environment/
│   ├── disaster/
│   ├── development/
│   └── relationship_engine/
├── data/
│   ├── raw/
│   ├── processed/
│   ├── synthetic/
│   └── DATA_SOURCES.md
├── models/
│   ├── pretrained/
│   ├── experiments/
│   └── model_cards/
├── notebooks/
├── scripts/
├── tests/
└── presentation/
    ├── slides/
    ├── demo_video/
    └── report/
```

Adjust the structure to the chosen framework and actual implementation.
Do not create empty folders purely to match the diagram.

### 15.1 Git workflow

-   `main`: stable, demonstrable code.
-   `develop`: integration branch if the team needs it.
-   `feature/<task-id>-<short-name>`: task branches.
-   Pull requests require review and passing tests.
-   Tag qualification release, e.g. `qualification-v1.0`.
-   Use meaningful commits.
-   Keep `.env` and credentials out of Git.
-   Use GitHub Issues/Projects for task tracking.

------------------------------------------------------------------------

## 16. Ten-Day Qualification Sprint

### 16.1 Sprint assumptions

-   Ten calendar days from 2 November 2026; exact dates must be checked
    against the official competition deadline.
-   Four active team members.
-   Human-led AI-assisted coding.
-   Two laptops, free cloud notebooks where available.
-   One small Salt Lake pilot area.
-   Hybrid public, curated and synthetic data.
-   One administrator role.
-   Live presentation and demonstration on the submission date.

### 16.2 Day-by-day plan

  -----------------------------------------------------------------------
  Day                     Main goal               Required deliverable
  ----------------------- ----------------------- -----------------------
  1                       Lock scope, inspect     Requirements checklist,
                          guidelines, choose      repo, data-source
                          pilot boundary,         shortlist, shared
                          repository and          schemas
                          architecture            

  2                       Geospatial foundation   Running 3D/2D map,
                                                  pilot boundary,
                                                  buildings and roads

  3                       Data platform and       PostGIS, asset
                          infrastructure assets   registry,
                                                  drainage/electrical
                                                  records with provenance

  4                       Environmental and       Weather/rainfall and
                          climate layers          available environmental
                                                  observations

  5                       Relationship engine     Graph construction,
                                                  typed relationships,
                                                  graph explorer/API

  6                       Disaster scenario       Rainfall/capacity
                                                  scenario, affected
                                                  assets and explainable
                                                  propagation

  7                       Development scenario    Proposed site, demand
                                                  assumptions,
                                                  suitability and upgrade
                                                  assessment

  8                       End-to-end integration  Unified admin workflow,
                                                  report output, stable
                                                  demo path

  9                       Validation and          Regression tests, data
                          hardening               audit, performance
                                                  checks, recorded backup
                                                  demo

  10                      Submission and          Final repository, PPT,
                          presentation            report, video and live
                                                  demonstration
  -----------------------------------------------------------------------

### 16.3 Daily operating cadence

-   Morning: agree on deliverables and blockers.
-   Midday: integrate work in progress; do not wait until end of day.
-   Evening: run full application and scenario smoke tests.
-   End of day: update task tracker, decisions and known issues.
-   Reserve a daily integration window.

### 16.4 Qualification acceptance criteria

**Geospatial** - App loads the selected Salt Lake region. - User can
toggle core layers. - User can select an asset and inspect its
attributes and provenance.

**Data** - Raw and processed data are separated. - Synthetic assets are
labelled. - Units, timestamps and sources are visible where relevant.

**Relationship engine** - Graph contains more than one asset type. -
Relationships have explicit semantics. - At least one scenario
propagates through multiple relationship types. - The UI explains the
path and assumptions.

**Disaster scenario** - User can select a rainfall scenario. -
Drainage/capacity logic produces a result. - The system identifies
potentially affected roads/assets. - Output is labelled as modelled or
simulated as appropriate.

**Development scenario** - User can place or select a proposed site. -
System checks multiple infrastructure/environmental dimensions. - At
least two scenarios can be compared. - Recommendations explain
constraints and assumptions.

**Reliability** - Full demo runs from documented setup. - Critical API
and scenario tests pass. - Backup screenshots/video are available. - No
critical dependency on an untested live external service.

### 16.5 Scope-cut order if behind schedule

Cut in this order:

1.  Advanced CV fine-tuning.
2.  Live traffic integration.
3.  Advanced electrical modelling.
4.  Water-quality interpolation.
5.  Complex report styling.
6.  Extra visual effects and secondary dashboards.

Do **not** cut: - shared asset model; - relationship engine; - one
end-to-end disaster scenario; - one development assessment; - provenance
labels; - stable live demo.

------------------------------------------------------------------------

## 17. Qualification Demonstration and Pitch

### 17.1 Recommended 10--15 minute structure

  -----------------------------------------------------------------------
  Time                                Content
  ----------------------------------- -----------------------------------
  0:00--1:30                          Urban problem, motivation and
                                      Hyperborea proposition

  1:30--3:00                          3D regional digital twin and data
                                      layers

  3:00--5:30                          Existing infrastructure and
                                      environmental intelligence

  5:30--8:00                          Extreme-rainfall and cascading-risk
                                      scenario

  8:00--10:30                         Proposed-development assessment and
                                      scenario comparison

  10:30--12:30                        Relationship-engine architecture,
                                      data provenance and validation

  12:30--14:00                        Two-month roadmap, expected impact
                                      and limitations

  14:00--15:00                        Buffer / questions, subject to
                                      event rules
  -----------------------------------------------------------------------

Adapt the order to the official presentation rules. If judges interrupt
or the allotted time is shorter, prioritize the live scenario and
relationship engine.

### 17.2 Main narrative

1.  Urban infrastructure systems are interdependent.
2.  Separate monitoring tools do not automatically explain cross-system
    consequences.
3.  Hyperborea builds a common geospatial and relationship
    representation.
4.  It uses that representation to explore current vulnerabilities and
    future development.
5.  The prototype demonstrates this through a bounded region and
    transparent scenarios.
6.  The next phase will improve data quality, model validation and
    predictive capability.

### 17.3 Demo preparation

-   Preload data and cache non-live assets.
-   Test on the actual presentation laptop and display.
-   Have a local fallback if internet access fails.
-   Record a full backup video.
-   Prepare a fixed demo scenario with known expected outputs.
-   Avoid entering untested parameters during the live presentation.
-   Keep a one-page architecture diagram.
-   Prepare answers on data provenance, model validation, novelty,
    limitations and scalability.

------------------------------------------------------------------------

## 18. Two-Month Post-Qualification Roadmap

### 18.1 Strategic priority

The team selected **relationship intelligence and prediction** as the
primary focus, while targeting research-grade models, real-world data
integration, a complete integrated platform and a final competition
demonstration.

### 18.2 Suggested 60-day phases

  ------------------------------------------------------------------------
  Phase                             Days Focus            Deliverables
  ---------------- --------------------- ---------------- ----------------
  A                                 1--7 Audit prototype, Revised
                                         guidelines, data requirements,
                                         and architecture data plan,
                                                          baseline metrics

  B                                8--18 Improve real     Better asset
                                         data and         coverage,
                                         infrastructure   verified
                                         topology         relationships,
                                                          data quality
                                                          report

  C                               19--30 Relationship     Baselines, graph
                                         model and        model
                                         prediction       experiments,
                                                          validation
                                                          results

  D                               31--40 Disaster and     Improved hazard
                                         development      propagation and
                                         simulation       multi-scenario
                                                          assessment

  E                               41--50 Field validation Field
                                         and integration  observations if
                                                          possible,
                                                          integrated
                                                          platform, RBAC

  F                               51--60 Testing,         Final model
                                         documentation    cards, report,
                                         and final        presentation and
                                         demonstration    release
  ------------------------------------------------------------------------

### 18.3 Research workstream

Develop an experimental question such as:

> Does a geospatial heterogeneous relationship model improve the
> identification and ranking of cascading urban infrastructure risks
> compared with independent asset-level models and conventional
> GIS/rule-based baselines?

Potential comparison methods:

-   GIS overlay and threshold rules;
-   independent asset-level risk models;
-   simple graph propagation;
-   graph-based machine learning;
-   heterogeneous or temporal GNN, if data supports it.

Research should include:

-   explicit hypotheses;
-   data description and provenance;
-   baseline methods;
-   train/validation/test separation;
-   spatial and temporal leakage checks;
-   suitable metrics;
-   ablation studies;
-   uncertainty and limitations;
-   reproducible code and configuration.

A research paper is a target, not a guaranteed outcome. Do not claim
novelty or performance until a literature review and controlled
experiments support it.

### 18.4 Team expansion

If additional members join, add them to bounded workstreams such as:

-   data acquisition and GIS quality;
-   hydraulic modelling;
-   environmental data;
-   model evaluation;
-   UI testing and documentation.

Do not expand the architecture merely because the team grows.

------------------------------------------------------------------------

## 19. Testing, Validation and Quality Assurance

### 19.1 Testing levels

1.  **Unit tests:** calculations, transformations, schema validation and
    graph rules.
2.  **Integration tests:** database, APIs, model services and frontend.
3.  **Data tests:** geometry validity, missingness, duplicates, units
    and provenance.
4.  **Scenario tests:** known inputs produce expected deterministic
    outputs.
5.  **Model tests:** held-out evaluation and baseline comparison.
6.  **UI tests:** layer controls, asset selection and scenario workflow.
7.  **Performance tests:** initial load, map rendering, graph traversal
    and API response.
8.  **Demo rehearsal:** full presentation on actual hardware.

### 19.2 Validation principles

-   Use independent sources where possible.
-   Separate training and test data by time and/or geography where
    appropriate.
-   Do not tune on the final evaluation set.
-   Record every assumption.
-   Compare with simple baselines.
-   Use expert review for engineering interpretations.
-   Report uncertainty and missing data.
-   Avoid false precision.

### 19.3 Example scenario tests

-   Rainfall below configured capacity should not trigger an overload
    rule.
-   Increasing rainfall beyond a defined capacity threshold should
    change the modelled result.
-   A disconnected asset should not be treated as physically connected.
-   A proposed development should alter only the scenario state, not
    overwrite the observed baseline.
-   Synthetic assets should remain labelled synthetic in reports and map
    popups.
-   Changing an intervention should produce a reproducible scenario
    comparison.

------------------------------------------------------------------------

## 20. Security, Ethics and Responsible Use

-   Keep API keys in environment variables and `.env` files excluded
    from Git.
-   Do not upload sensitive personal, utility or restricted
    infrastructure data to public AI services.
-   Respect data provider terms and licences.
-   Do not expose private household or sensitive infrastructure
    information.
-   Do not present the prototype as an official municipal decision or
    safety certification.
-   Make uncertainty and data gaps visible.
-   Provide human review for high-impact recommendations.
-   Keep a record of model versions and scenario assumptions.
-   Use role-based access and audit logs in the later platform.
-   Avoid publishing precise sensitive infrastructure details without
    authorization.

------------------------------------------------------------------------

## 21. Risks and Mitigations

  -----------------------------------------------------------------------
  Risk                    Impact                  Mitigation
  ----------------------- ----------------------- -----------------------
  Incomplete drainage     Weak physical network   Bound the pilot area;
  maps                    model                   curate a small network;
                                                  label assumptions

  No reliable electrical  Misleading dependency   Use a clearly
  topology                analysis                synthetic/curated
                                                  demonstrator network

  God's Eye reference     Frontend delay          Build independently
  integration complexity                          with CesiumJS; keep the
                                                  reference as design
                                                  inspiration

  External API outage     Demo failure            Cache data and provide
                                                  static fallback

  Synthetic data mistaken Credibility and ethics  Persistent provenance
  for real                risk                    labels and
                                                  documentation

  AI agents create        Integration failure     Shared contracts, small
  inconsistent modules                            PRs, human review

  Too many features       Incomplete core         Protect P0 scope and
                          workflow                use cut order

  No labelled training    Unsupported ML claims   Use rules/pretrained
  data                                            models; defer learned
                                                  models

  Weak validation         Judges question         Show baselines, known
                          credibility             scenario tests and
                                                  limitations

  Hardware limits         Slow local experiments  Small models, optimized
                                                  batches, Colab/Kaggle
                                                  when available

  Time lost to UI polish  Core logic incomplete   Build functional UI
                                                  first

  Team coordination       Parallel work conflicts Named owners, daily
  issues                                          integration and
                                                  decision log
  -----------------------------------------------------------------------

------------------------------------------------------------------------

## 22. UN Sustainable Development Goals Alignment

The United Nations has **17 Sustainable Development Goals**, not 17
separate "problems." Hyperborea can contribute to selected goals; it
should not claim to solve all 17.

### 22.1 Direct alignment

  -----------------------------------------------------------------------
  SDG                     Goal                    Hyperborea contribution
  ----------------------- ----------------------- -----------------------
  SDG 6                   Clean Water and         Water observations,
                          Sanitation              drainage, flood and
                                                  water infrastructure
                                                  intelligence

  SDG 7                   Affordable and Clean    Electricity network
                          Energy                  capacity, resilience
                                                  and exposure analysis

  SDG 9                   Industry, Innovation    Infrastructure
                          and Infrastructure      observability,
                                                  resilience and
                                                  integrated planning

  SDG 11                  Sustainable Cities and  Urban risk,
                          Communities             accessibility, disaster
                                                  preparedness and
                                                  development suitability

  SDG 13                  Climate Action          Climate exposure,
                                                  hazard scenarios and
                                                  adaptation planning
  -----------------------------------------------------------------------

### 22.2 Secondary alignment

  -----------------------------------------------------------------------
  SDG                     Goal                    Potential contribution
  ----------------------- ----------------------- -----------------------
  SDG 3                   Good Health and         Air quality, heat
                          Well-being              exposure and access to
                                                  critical services

  SDG 8                   Decent Work and         More resilient
                          Economic Growth         infrastructure and
                                                  commute/accessibility
                                                  analysis

  SDG 10                  Reduced Inequalities    Identify underserved
                                                  areas and unequal
                                                  access, if relevant
                                                  data is available

  SDG 12                  Responsible Consumption Better resource and
                          and Production          infrastructure planning

  SDG 15                  Life on Land            Land-cover, vegetation
                                                  and ecological exposure
                                                  indicators

  SDG 17                  Partnerships for the    Data and validation
                          Goals                   partnerships with
                                                  institutions and
                                                  authorities
  -----------------------------------------------------------------------

### 22.3 SDG communication rule

For competition materials:

-   Identify SDG 9, 11 and 13 as the strongest overall alignment.
-   Explain SDG 6 and 7 through actual water and energy modules.
-   Treat other goals as secondary or conditional.
-   Link claims to measurable outputs where possible.
-   Do not claim that the platform directly achieves an SDG simply
    because a related map layer exists.

------------------------------------------------------------------------

## 23. Project Documentation and Submission Deliverables

Maintain these artifacts:

  ---------------------------------------------------------------------------
  Artifact                    Purpose                 Owner
  --------------------------- ----------------------- -----------------------
  `planning.md`               Master plan             Shared

  `README.md`                 Setup, overview and     Backend/integration
                              demo instructions       owner

  `ARCHITECTURE.md`           System design           Shared

  `DATA_SOURCES.md`           Data provenance and     Data/GIS owner
                              licence register        

  `DATA_DICTIONARY.md`        Entities, fields and    Backend/data owner
                              units                   

  `API_CONTRACTS.md`          API request/response    Backend + frontend
                              definitions             

  `VALIDATION_PLAN.md`        Test and evaluation     AI/ML owner
                              design                  

  `DECISIONS.md`              Architecture decision   Shared
                              records                 

  `DEMO_SCRIPT.md`            Repeatable live         Presentation owner
                              demonstration           

  `SUBMISSION_CHECKLIST.md`   Competition compliance  Shared

  Model cards                 Model limitations and   AI/ML owner
                              evaluation              

  PPT                         Competition             Shared
                              presentation            

  Project report              Problem, methodology,   Shared
                              implementation and      
                              results                 

  Demo video                  Backup and review       Shared
                              artifact                

  Research/literature review  Prior work and research Research owner
                              gap                     
  ---------------------------------------------------------------------------

### 23.1 README minimum contents

-   Project summary.
-   Problem and proposed solution.
-   Screenshots.
-   Architecture overview.
-   Technology stack.
-   Setup instructions.
-   Environment variables.
-   Data source and licence notes.
-   Demo scenario.
-   Testing instructions.
-   Limitations.
-   Team contributions.
-   Future roadmap.

### 23.2 Research/literature review

The literature review should cover:

-   urban digital twins;
-   infrastructure interdependency modelling;
-   cascading infrastructure failure;
-   climate risk and urban resilience;
-   geospatial graph learning;
-   flood/drainage modelling;
-   multi-criteria site suitability and urban planning.

For every paper, record the problem, data, methods, results, limitations
and relevance to Hyperborea. Identify a research gap from the literature
rather than declaring one in advance.

------------------------------------------------------------------------

## 24. Open Decisions and Questions

The following must be resolved before or during implementation.

  ------------------------------------------------------------------------------------------
  ID             Decision / missing    Priority       Owner                   Status
                 information                                                  
  -------------- --------------------- -------------- ----------------------- --------------
  D-01           Official ISI          P0             Team                    Open
                 guidelines and                                               
                 judging rubric must                                          
                 be reviewed                                                  

  D-02           Confirm exact         P0             Team                    Open
                 submission date and                                          
                 time                                                         

  D-03           Select exact Salt     P0             GIS/data                Open
                 Lake pilot boundary                                          

  D-04           Inspect current God's P0             Frontend                Open
                 Eye reference                                                
                 repository                                                   

  D-05           Decide exact          P0             Frontend/architecture   Open
                 recreated                                                    
                 functionality versus                                         
                 independent                                                  
                 Hyperborea features                                          

  D-06           Confirm available     P0             GIS/data                Open
                 public drainage data                                         
                 for pilot region                                             

  D-07           Confirm availability  P0             GIS/data                Open
                 of electrical network                                        
                 information or define                                        
                 synthetic scope                                              

  D-08           Confirm               P0             Data                    Open
                 weather/environment                                          
                 APIs and terms                                               

  D-09           Confirm whether the   P0             Team                    Open
                 ISI submission                                               
                 requires a particular                                        
                 template or report                                           
                 format                                                       

  D-10           Confirm exact GPU     P1             Team                    Open
                 VRAM/TGP and laptop                                          
                 CPU specifications                                           

  D-11           Determine whether     P1             Team                    Open
                 field visits or                                              
                 expert review are                                            
                 possible in the                                              
                 60-day phase                                                 

  D-12           Decide whether        P1             Team                    Open
                 additional team                                              
                 members will join                                            
                 after qualification                                          

  D-13           Select model          P1             AI/ML                   Open
                 candidates after data                                        
                 inspection and                                               
                 baseline testing                                             

  D-14           Confirm               P1             Backend/DevOps          Open
                 deployment/hosting                                           
                 requirements                                                 
  ------------------------------------------------------------------------------------------

------------------------------------------------------------------------

## 25. Master Task Tracker

Use this table as the top-level tracker. Break each item into GitHub
issues.

  --------------------------------------------------------------------------------------------------------------------------
  Task ID    Task                Priority   Owner              Dependencies         Acceptance criteria           Status
  ---------- ------------------- ---------- ------------------ -------------------- ----------------------------- ----------
  HB-001     Review ISI          P0         TBD                Official guidelines  Compliance checklist complete Not
             guidelines                                                                                           started

  HB-002     Select pilot        P0         TBD                Data scan            Bounded region documented     Not
             boundary                                                                                             started

  HB-003     Inspect God's Eye   P0         TBD                Repository access    Feature and licence review    Not
             reference                                                                                            started

  HB-004     Initialize          P0         TBD                Architecture         Reproducible local startup    Not
             repository and                                                                                       started
             Docker                                                                                               

  HB-005     Define asset and    P0         TBD                Pilot boundary       Shared schema reviewed        Not
             relationship                                                                                         started
             schemas                                                                                              

  HB-006     Build CesiumJS map  P0         TBD                Frontend setup       Pilot region renders          Not
                                                                                                                  started

  HB-007     Ingest buildings    P0         TBD                Data sources,        Layers render and are         Not
             and roads                                         PostGIS              queryable                     started

  HB-008     Create drainage     P0         TBD                Schema,              Network represented and       Not
             asset network                                     source/curated data  labelled                      started

  HB-009     Create electrical   P1         TBD                Schema               Network and provenance        Not
             demonstrator                                                           visible                       started
             network                                                                                              

  HB-010     Integrate           P0         TBD                API/data source      Timestamped input visible     Not
             weather/rainfall                                                                                     started
             data                                                                                                 

  HB-011     Add                 P1         TBD                Data availability    Sources and units visible     Not
             environment/water                                                                                    started
             layers                                                                                               

  HB-012     Implement           P0         TBD                Shared schema        Multiple node/edge types work Not
             relationship graph                                                                                   started

  HB-013     Implement           P0         TBD                Graph, rainfall,     Explainable path and affected Not
             cascading-risk                                    drainage             assets                        started
             scenario                                                                                             

  HB-014     Implement           P0         TBD                GIS, graph, capacity Proposed site assessed        Not
             development                                       rules                                              started
             assessment                                                                                           

  HB-015     Add scenario        P0         TBD                HB-013, HB-014       Baseline and alternative      Not
             comparison                                                             compare                       started

  HB-016     Add provenance and  P0         All data modules   Data status model    Observed/modelled/simulated   Not
             uncertainty UI                                                         visible                       started

  HB-017     Integrate admin     P0         Frontend/backend   APIs                 End-to-end workflow works     Not
             dashboard                                                                                            started

  HB-018     Add tests and demo  P0         QA/shared          Integrated app       Critical tests pass; backup   Not
             fallback                                                               exists                        started

  HB-019     Prepare PPT and     P0         Shared             Stable prototype     Submission-ready artifacts    Not
             report                                                                                               started

  HB-020     Record demo video   P0         Shared             Stable prototype     Full fallback demo recorded   Not
                                                                                                                  started

  HB-021     Improve real data   P1         TBD                Qualification        Data quality report           Not
             coverage                                                                                             started

  HB-022     Establish model     P1         TBD                Data and labels      Reproducible metrics          Not
             baselines                                                                                            started

  HB-023     Evaluate            P1         TBD                Adequate graph data  Comparison with baselines     Not
             graph-learning                                                                                       started
             models                                                                                               

  HB-024     Field validation    P1         TBD                Access/permissions   Observations documented       Not
                                                                                                                  started

  HB-025     Multi-role access   P1         TBD                Stable platform      Role tests pass               Not
                                                                                                                  started
  --------------------------------------------------------------------------------------------------------------------------

Task status options: `Not started`, `In progress`, `Blocked`,
`In review`, `Done`, `Deferred`.

------------------------------------------------------------------------

## 26. Definition of Done

A task is complete only when:

-   its acceptance criteria are met;
-   implementation is committed to the correct branch;
-   tests are added or relevant manual verification is recorded;
-   documentation is updated;
-   data provenance and assumptions are documented;
-   no secrets are committed;
-   the task owner reports known limitations;
-   integration with dependent modules is checked.

A feature is not complete merely because an AI agent generated code for
it.

------------------------------------------------------------------------

## 27. Immediate Next Actions

Complete these in order:

1.  Attach and review the official ISI guidelines and judging rubric.
2.  Confirm the exact deadline and submission format.
3.  Create the GitHub repository and add this file as `planning.md`.
4.  Inspect the God's Eye reference repository and document the features
    to recreate.
5.  Select a small Salt Lake pilot boundary after a quick
    data-availability scan.
6.  Create the shared asset, relationship and scenario schemas.
7.  Assign owners to the P0 tasks.
8.  Start the map and data foundation in parallel.
9.  Schedule a daily integration and demonstration check.
10. Protect the relationship engine and two end-to-end scenarios from
    scope cuts.

------------------------------------------------------------------------

## 28. Final Project Principle

**Hyperborea should not attempt to prove that it can predict everything
about a city in ten days. It should prove that it can connect urban
systems, represent their dependencies, simulate meaningful scenarios and
explain the consequences of development decisions.**

The qualification prototype demonstrates the architecture and the core
idea. The subsequent 60-day phase establishes data quality, scientific
validity, predictive performance and broader applicability.

The project should consistently distinguish what is observed, what is
modelled, what is simulated and what remains unknown.

That discipline is essential to making Hyperborea technically credible,
researchable and useful for real urban decision-making.

------------------------------------------------------------------------

**End of planning document.**
