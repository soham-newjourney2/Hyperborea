"""Edge-type registry (planning §6) — the one place relationship semantics live; the UI reads it via /graph/summary."""

EDGE_TYPES: dict[str, dict] = {
    "DRAINS_TO": {
        "label": "drains to", "source": ["drain"], "target": ["drain", "outfall"], "physical": True, "active": True,
        "description": "Stormwater flows from the source drain into the target drain or outfall (P06 routing DAG).",
    },
    "ADJACENT_TO": {
        "label": "runs along", "source": ["drain"], "target": ["road"], "physical": True, "active": True,
        "description": "The drain is laid along this road edge (side-drain assumption) — a blocked/overflowing drain "
                       "floods this road first.",
    },
    "ACCESSIBLE_VIA": {
        "label": "accessed via", "source": ["building", "facility"], "target": ["road"], "physical": True,
        "active": True, "description": "Nearest road edge within 50 m — the entrance road for the asset.",
    },
    "LOCATED_WITHIN": {
        "label": "inside", "source": ["building", "drain", "manhole"], "target": ["catchment"], "physical": True,
        "active": True, "description": "The asset lies inside this drainage catchment; its rain runs off there.",
    },
    "DEPENDS_ON": {
        "label": "depends on", "source": ["facility"], "target": ["road", "transformer"], "physical": False, "active": True,
        "description": "Functional dependency: the facility needs these road edges (≤ 50 m, up to 3) for access "
                       "and its supplying transformer for power (P10).",
    },
    # Defined in planning §6, populated by later phases.
    "SUPPLIES": {"label": "supplies power to", "source": ["substation", "transformer"],
                 "target": ["substation", "transformer", "building", "facility"], "physical": True, "active": True,
                 "description": "Electrical supply on the SIMULATED network: grid → primary substation → 11 kV "
                                "transformer → building / facility (P10)."},
    "EXPOSED_TO": {"label": "exposed to", "source": ["*"], "target": ["hazard_zone"], "physical": False,
                   "active": False, "description": "Scenario-only exposure to a hazard zone (P08)."},
    "PROPOSED_ADJACENT_TO": {"label": "proposed next to", "source": ["proposed_site"], "target": ["*"],
                             "physical": False, "active": False, "scenario_only": True,
                             "description": "Scenario-only adjacency of a proposed development to a drain/road "
                                            "(P09 overlay; never added to the baseline graph)."},
}

# layer → node kind (UI colours/shapes by kind; asset_type keeps the detail, e.g. hospital)
LAYER_KIND = {"buildings": "building", "roads": "road", "drains": "drain", "drain_nodes": "manhole",
              "outfalls": "outfall", "catchments": "catchment", "facilities": "facility",
              "substations": "substation", "transformers": "transformer"}
