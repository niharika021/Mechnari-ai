"""
Mechnari.ai - Part Taxonomy, Failure Effects & Cross-Program Mode Catalog
=========================================================================
Authoring source for the normalized data model. Nothing here is read at
runtime; generate_csv_data.py bakes it into CSVs under data/.

Three ideas live in this file:

1. PART_TYPES - every part belongs to a *type*, and every type belongs to a
   *family*. Failure modes are properties of a type or a family, which is
   what makes it possible to ask "what has this kind of part failed from
   before?"

   The two levels exist because inheritance has to be narrow enough to stay
   true. A mode attaches at the level it actually generalizes to: chafing
   wear-through is real for any flexible line (family), coking inside a
   PTFE lumen is only real downstream of an air compressor (type). Attach
   everything at one broad level and the tool starts telling engineers to
   check a wire conduit for park brake binding, which is how a system like
   this loses its reader in one screen.

2. FAILURE_EFFECTS - Severity is a property of the failure *effect* at a
   system level, not of an individual analysis. Holding effects in one
   table lets the platform enforce a single severity per effect across
   every program (a standard IATF / AIAG-VDA audit expectation).

3. PRIOR_PROGRAM_MODES - failure modes learned on earlier programs whose
   parts are no longer in the active BOM. These are the institutional
   memory a manual DFMEA workshop forgets, and they are where most gap
   detection findings come from.
"""

# =====================================================================
# 1. PART TYPE TAXONOMY (family -> type)
# =====================================================================

PART_FAMILIES = {
    "FAM-FLEX-ROUTING":  "Flexible Fluid Routing",
    "FAM-RIGID-ROUTING": "Rigid Tube & Line Routing",
    "FAM-JOINT":         "Joints, Clamps & Connections",
    "FAM-STRUCTURE":     "Structural Mounting",
    "FAM-SEALING":       "Static Sealing",
    "FAM-FLOW-CONTROL":  "Flow Control Devices",
    "FAM-PROTECTION":    "Routing Protection & Control Cables",
    "FAM-FLUID-COND":    "Fluid Conditioning",
}

PART_TYPES = {
    "PT-HOSE-FUEL":       {"name": "Fuel Hose / Flexible Fuel Line",      "family": "FAM-FLEX-ROUTING"},
    "PT-HOSE-REFRIG":     {"name": "Refrigerant Hose Assembly",           "family": "FAM-FLEX-ROUTING"},
    "PT-HOSE-HYD":        {"name": "Hydraulic Hose Assembly",             "family": "FAM-FLEX-ROUTING"},
    "PT-HOSE-COOLANT":    {"name": "Coolant / Heat Exchanger Hose",       "family": "FAM-FLEX-ROUTING"},
    "PT-HOSE-HOTGAS":     {"name": "Hot Compressed Gas Hose",             "family": "FAM-FLEX-ROUTING"},
    "PT-TUBE-RIGID":      {"name": "Rigid Tube / Hard Line",              "family": "FAM-RIGID-ROUTING"},
    "PT-TUBE-PNEUMATIC":  {"name": "Pneumatic Control & Brake Tubing",    "family": "FAM-RIGID-ROUTING"},
    "PT-CLAMP":           {"name": "Hose Clamp / Retaining Clamp",        "family": "FAM-JOINT"},
    "PT-COUPLING":        {"name": "Quick Connect Coupling",              "family": "FAM-JOINT"},
    "PT-FITTING":         {"name": "Threaded Fitting / Adapter / Port",   "family": "FAM-JOINT"},
    "PT-BRACKET":         {"name": "Structural Bracket / Mounting Plate", "family": "FAM-STRUCTURE"},
    "PT-SEAL":            {"name": "Static Seal / Boot / Grommet",        "family": "FAM-SEALING"},
    "PT-VALVE-MECH":      {"name": "Mechanical Valve Assembly",           "family": "FAM-FLOW-CONTROL"},
    "PT-VALVE-SOLENOID":  {"name": "Solenoid / Electro-Hydraulic Valve",  "family": "FAM-FLOW-CONTROL"},
    "PT-CONDUIT-ELEC":    {"name": "Electrical Protective Conduit",       "family": "FAM-PROTECTION"},
    "PT-CABLE-MECH":      {"name": "Mechanical Control Cable Assembly",   "family": "FAM-PROTECTION"},
    "PT-FILTER-SEP":      {"name": "Filtration & Separation Device",      "family": "FAM-FLUID-COND"},
}

# =====================================================================
# 2. FAILURE EFFECT REGISTRY (single source of truth for Severity)
# =====================================================================
# standard_severity follows AIAG-VDA severity intent:
#   9-10 safety / regulatory, 7-8 loss of primary function,
#   5-6 degraded function, 3-4 annoyance, 1-2 no discernible effect.

FAILURE_EFFECTS = {
    "EF-01": {"description": "Fuel or oil leak onto hot surface - fire risk",     "system_level": "Machine",   "standard_severity": 9},
    "EF-02": {"description": "External fluid leak, no ignition source",           "system_level": "Subsystem", "standard_severity": 7},
    "EF-03": {"description": "Loss or degradation of steering assist",            "system_level": "Machine",   "standard_severity": 9},
    "EF-04": {"description": "Degraded or lost braking function",                 "system_level": "Machine",   "standard_severity": 10},
    "EF-05": {"description": "Fluid overheat - engine or hydraulic power derate", "system_level": "Machine",   "standard_severity": 8},
    "EF-06": {"description": "Machine immobilised - unplanned field breakdown",   "system_level": "Machine",   "standard_severity": 8},
    "EF-07": {"description": "Loss of implement or hitch function",               "system_level": "Subsystem", "standard_severity": 7},
    "EF-08": {"description": "Hydraulic circuit contamination",                   "system_level": "Subsystem", "standard_severity": 7},
    "EF-09": {"description": "Electrical short - arc flash / fire risk",          "system_level": "Machine",   "standard_severity": 9},
    "EF-10": {"description": "Refrigerant release to atmosphere - regulatory",    "system_level": "Machine",   "standard_severity": 6},
    "EF-11": {"description": "Loss of cab climate control",                       "system_level": "Cab",       "standard_severity": 4},
    "EF-12": {"description": "Cab noise, buzz or vibration nuisance",             "system_level": "Cab",       "standard_severity": 3},
    "EF-13": {"description": "Water or dust ingress into cab",                    "system_level": "Cab",       "standard_severity": 4},
    "EF-14": {"description": "Emissions system fault - EGR / aftertreatment",     "system_level": "Machine",   "standard_severity": 7},
    "EF-15": {"description": "Unscheduled service / warranty repair",             "system_level": "Subsystem", "standard_severity": 5},
    "EF-16": {"description": "Degraded sensor signal / guidance fault",           "system_level": "Subsystem", "standard_severity": 6},
}

# =====================================================================
# 3. PART -> (TYPE, PRIMARY FAILURE EFFECT) ASSIGNMENT
# =====================================================================
# The effect is the consequence of that part's own historical failure mode.

PART_ASSIGNMENTS = {
    # --- Fuel Routings ---
    "TR-FL-001":  ("PT-HOSE-FUEL",      "EF-01"),
    "TR-FL-002":  ("PT-VALVE-MECH",          "EF-02"),
    "TR-FL-003":  ("PT-HOSE-FUEL",      "EF-01"),
    "TR-FL-004":  ("PT-CLAMP",          "EF-02"),
    "TR-FL-005":  ("PT-BRACKET",        "EF-06"),
    "TR-FL-006":  ("PT-COUPLING",       "EF-01"),
    "TR-FL-007":  ("PT-FILTER-SEP",     "EF-02"),
    "TR-FL-008":  ("PT-TUBE-RIGID",     "EF-06"),
    "TR-FL-009":  ("PT-HOSE-FUEL",      "EF-01"),
    "TR-FL-010":  ("PT-FILTER-SEP",     "EF-06"),
    # --- AC Routings ---
    "TR-AC-011":  ("PT-HOSE-REFRIG",    "EF-10"),
    "TR-AC-012":  ("PT-TUBE-RIGID",     "EF-10"),
    "TR-AC-013":  ("PT-BRACKET",        "EF-06"),
    "TR-AC-014":  ("PT-SEAL",           "EF-10"),
    "TR-AC-015":  ("PT-VALVE-MECH",          "EF-11"),
    "TR-AC-016":  ("PT-BRACKET",        "EF-10"),
    "TR-AC-017":  ("PT-CLAMP",          "EF-12"),
    "TR-AC-018":  ("PT-VALVE-MECH",          "EF-10"),
    "TR-AC-019":  ("PT-HOSE-REFRIG",    "EF-12"),
    "TR-AC-020":  ("PT-VALVE-SOLENOID",          "EF-09"),
    # --- Hydraulic Steering Routings ---
    "TR-HYD-021": ("PT-HOSE-HYD",       "EF-03"),
    "TR-HYD-022": ("PT-BRACKET",        "EF-03"),
    "TR-HYD-023": ("PT-FITTING",        "EF-03"),
    "TR-HYD-024": ("PT-TUBE-RIGID",     "EF-02"),
    "TR-HYD-025": ("PT-HOSE-HYD",       "EF-03"),
    "TR-HYD-026": ("PT-HOSE-HYD",       "EF-07"),
    "TR-HYD-027": ("PT-BRACKET",        "EF-12"),
    "TR-HYD-028": ("PT-COUPLING",       "EF-08"),
    "TR-HYD-029": ("PT-HOSE-HYD",       "EF-16"),
    "TR-HYD-030": ("PT-VALVE-MECH",          "EF-05"),
    # --- Engine Cooling Routings ---
    "TR-ENG-031": ("PT-HOSE-COOLANT",   "EF-05"),
    "TR-ENG-032": ("PT-HOSE-COOLANT",   "EF-05"),
    "TR-ENG-033": ("PT-HOSE-COOLANT",   "EF-15"),
    "TR-ENG-034": ("PT-CLAMP",          "EF-02"),
    "TR-ENG-035": ("PT-TUBE-RIGID",     "EF-05"),
    "TR-ENG-036": ("PT-HOSE-COOLANT",   "EF-02"),
    "TR-ENG-037": ("PT-TUBE-RIGID",     "EF-06"),
    "TR-ENG-038": ("PT-HOSE-COOLANT",   "EF-14"),
    "TR-ENG-039": ("PT-BRACKET",        "EF-06"),
    "TR-ENG-040": ("PT-VALVE-MECH",          "EF-05"),
    # --- Pneumatic & Electrical Routings ---
    "TR-ELE-041": ("PT-TUBE-PNEUMATIC", "EF-04"),
    "TR-ELE-042": ("PT-CONDUIT-ELEC", "EF-09"),
    "TR-ELE-043": ("PT-CLAMP",          "EF-09"),
    "TR-ELE-044": ("PT-SEAL",           "EF-06"),
    "TR-ELE-045": ("PT-HOSE-HOTGAS", "EF-04"),
    "TR-ELE-046": ("PT-BRACKET",        "EF-16"),
    "TR-ELE-047": ("PT-CABLE-MECH", "EF-04"),
    "TR-ELE-048": ("PT-SEAL",           "EF-13"),
    "TR-ELE-049": ("PT-FITTING",        "EF-08"),
    "TR-ELE-050": ("PT-TUBE-PNEUMATIC", "EF-07"),
}

# =====================================================================
# 4. PRIOR PROGRAM FAILURE MODES (institutional memory)
# =====================================================================
# Modes proven on earlier programs. The parts that failed are retired and
# no longer in the active BOM, so a manual workshop working off the current
# BOM will not see them - but they remain valid for the part TYPE.

PRIOR_PROGRAM_MODES = [
    {
        "scope_id": "PT-HOSE-FUEL",
        "failure_mode": "Fuel leakage at crimped ferrule joint",
        "potential_cause": "Ferrule crimp relaxation after repeated thermal cycling of the hose stem",
        "effect_id": "EF-01",
        "typical_control": "End-of-line 6 bar air-decay leak test",
        "baseline_detection": 4,
        "recommended_action": "Specify controlled crimp diameter with 100% post-crimp gauge check; move to a cold-formed one-piece stem.",
        "legacy_part_id": "TR-LEG-FL-901",
        "legacy_part_name": "Fuel Feed Hose (Program T6, retired 2022)",
    },
    {
        "scope_id": "PT-HOSE-FUEL",
        "failure_mode": "Inner tube swelling and delamination on high biodiesel blends",
        "potential_cause": "B20+ fatty acid methyl ester attack on the standard NBR inner liner",
        "effect_id": "EF-06",
        "typical_control": "Fluid compatibility soak test at type approval only",
        "baseline_detection": 6,
        "recommended_action": "Qualify the inner liner to B30 soak schedule; move to an FKM / NBR co-extruded liner.",
        "legacy_part_id": "TR-LEG-FL-903",
        "legacy_part_name": "Fuel Return Line (Program T6, retired 2022)",
    },
    {
        "scope_id": "PT-HOSE-COOLANT",
        "failure_mode": "Hose burst at clamp interface after cover ageing",
        "potential_cause": "Cover ozone cracking reducing wall section under clamp compression",
        "effect_id": "EF-05",
        "typical_control": "Visual inspection at scheduled service",
        "baseline_detection": 6,
        "recommended_action": "Move to a peroxide-cured EPDM cover and add ozone resistance to the drawing spec.",
        "legacy_part_id": "TR-LEG-EN-911",
        "legacy_part_name": "Radiator Hose (Program T5, retired 2021)",
    },
    {
        "scope_id": "FAM-FLEX-ROUTING",
        "failure_mode": "Cover pinhole leak from abrasion against adjacent harness",
        "potential_cause": "Relative motion between hose and wiring harness with no separation clip",
        "effect_id": "EF-02",
        "typical_control": "Design review clearance check",
        "baseline_detection": 5,
        "recommended_action": "Mandate 15mm separation or spiral wrap wherever a hose and harness share a routing corridor.",
        "legacy_part_id": "TR-LEG-HY-921",
        "legacy_part_name": "Loader Boom Hose (Program T5, retired 2021)",
    },
    {
        "scope_id": "PT-BRACKET",
        "failure_mode": "Weld seam cracking in the heat affected zone",
        "potential_cause": "Undercut at the weld toe acting as a crack initiation site under cyclic load",
        "effect_id": "EF-06",
        "typical_control": "Sample dye penetrant inspection",
        "baseline_detection": 6,
        "recommended_action": "Specify weld toe grinding and 100% visual per ISO 5817 class B on safety-related brackets.",
        "legacy_part_id": "TR-LEG-ST-931",
        "legacy_part_name": "Cab Mount Bracket (Program T5, retired 2020)",
    },
    {
        "scope_id": "PT-BRACKET",
        "failure_mode": "Fastener preload loss and bracket rattle",
        "potential_cause": "Paint film creep under the bolt head relaxing joint preload over thermal cycles",
        "effect_id": "EF-12",
        "typical_control": "Assembly torque audit",
        "baseline_detection": 4,
        "recommended_action": "Use flange bolts with a serrated bearing face; mask paint at bolt seating faces.",
        "legacy_part_id": "TR-LEG-ST-933",
        "legacy_part_name": "Fender Support Bracket (Program T5, retired 2020)",
    },
    {
        "scope_id": "PT-CLAMP",
        "failure_mode": "Clamp band stress corrosion cracking in salt environments",
        "potential_cause": "Chloride attack on sensitised 301 stainless band under sustained tensile load",
        "effect_id": "EF-02",
        "typical_control": "480h salt spray on sample lots",
        "baseline_detection": 5,
        "recommended_action": "Move band material to 316L or Zn-Ni coated carbon steel for chassis-exposed positions.",
        "legacy_part_id": "TR-LEG-CL-941",
        "legacy_part_name": "Coolant Hose Clamp (Program T5, retired 2021)",
    },
    {
        "scope_id": "FAM-FLOW-CONTROL",
        "failure_mode": "Valve body porosity leak from casting defect",
        "potential_cause": "Gas porosity in the die cast body wall opening under pressure cycling",
        "effect_id": "EF-02",
        "typical_control": "Sample pressure test per casting lot",
        "baseline_detection": 6,
        "recommended_action": "100% air-decay leak test on cast bodies; add porosity acceptance criteria to the drawing.",
        "legacy_part_id": "TR-LEG-VL-951",
        "legacy_part_name": "Hydraulic Selector Valve (Program T4, retired 2019)",
    },
    {
        "scope_id": "FAM-FLOW-CONTROL",
        "failure_mode": "Actuation seizure after long dormancy in cold climates",
        "potential_cause": "Condensate freezing around the spool with no drainage path",
        "effect_id": "EF-15",
        "typical_control": "Cold chamber functional test at type approval",
        "baseline_detection": 7,
        "recommended_action": "Add a drain path and low-temperature grease; extend cold soak validation to -30C after 30 day dormancy.",
        "legacy_part_id": "TR-LEG-VL-953",
        "legacy_part_name": "Air Tank Drain Valve (Program T4, retired 2019)",
    },
    {
        "scope_id": "FAM-RIGID-ROUTING",
        "failure_mode": "Flare joint leak from over-torque during field service",
        "potential_cause": "No torque specification on service documentation leading to flare cracking",
        "effect_id": "EF-02",
        "typical_control": "None - relies on technician judgement",
        "baseline_detection": 7,
        "recommended_action": "Publish torque values on the service label and adopt a torque-tolerant captive sleeve fitting.",
        "legacy_part_id": "TR-LEG-TB-961",
        "legacy_part_name": "Brake Hard Line (Program T5, retired 2021)",
    },
    {
        "scope_id": "PT-SEAL",
        "failure_mode": "Seal chemical swell from incorrect service fluid",
        "potential_cause": "Field top-up with non-approved fluid attacking the elastomer compound",
        "effect_id": "EF-02",
        "typical_control": "Service manual fluid specification",
        "baseline_detection": 7,
        "recommended_action": "Select a broad-compatibility compound (HNBR or FKM) and add a fluid spec label at every fill point.",
        "legacy_part_id": "TR-LEG-SL-971",
        "legacy_part_name": "Transmission Cover Seal (Program T4, retired 2019)",
    },
    {
        "scope_id": "PT-COUPLING",
        "failure_mode": "Dust cap loss leading to contamination ingress at the coupler",
        "potential_cause": "Tether fatigue fracture allowing the cap to be lost in the field",
        "effect_id": "EF-08",
        "typical_control": "None in service",
        "baseline_detection": 6,
        "recommended_action": "Integrate a captive hinged cap into the coupler body rather than a tethered separate part.",
        "legacy_part_id": "TR-LEG-CP-981",
        "legacy_part_name": "Implement Coupler (Program T5, retired 2021)",
    },
    {
        "scope_id": "PT-TUBE-PNEUMATIC",
        "failure_mode": "Tube kink at bulkhead pass-through restricting air flow",
        "potential_cause": "Bend radius below the specified minimum where the tube crosses the frame",
        "effect_id": "EF-04",
        "typical_control": "Assembly visual check",
        "baseline_detection": 5,
        "recommended_action": "Add a moulded bend support at every bulkhead crossing and verify radius on the digital mock-up.",
        "legacy_part_id": "TR-LEG-PN-991",
        "legacy_part_name": "Air Supply Tube (Program T5, retired 2020)",
    },
    {
        "scope_id": "FAM-JOINT",
        "failure_mode": "Thread galling on stainless fitting during assembly",
        "potential_cause": "Like-on-like austenitic stainless thread contact without anti-seize",
        "effect_id": "EF-15",
        "typical_control": "Assembly torque monitoring",
        "baseline_detection": 4,
        "recommended_action": "Specify dissimilar thread hardness or a dry film lubricant coating on one mating thread.",
        "legacy_part_id": "TR-LEG-FT-995",
        "legacy_part_name": "Manifold Port Adapter (Program T4, retired 2019)",
    },
    {
        "scope_id": "PT-CONDUIT-ELEC",
        "failure_mode": "Sleeve end fraying exposing conductors to abrasion",
        "potential_cause": "Cut sleeve end left untreated at the harness breakout",
        "effect_id": "EF-09",
        "typical_control": "Harness visual inspection",
        "baseline_detection": 5,
        "recommended_action": "Require heat-sealed or moulded sleeve terminations at every breakout point.",
        "legacy_part_id": "TR-LEG-CD-997",
        "legacy_part_name": "Chassis Harness Conduit (Program T5, retired 2021)",
    },
    {
        "scope_id": "PT-HOSE-REFRIG",
        "failure_mode": "Refrigerant permeation loss through the hose wall over service life",
        "potential_cause": "Barrier layer permeability above the rate assumed for the charge size",
        "effect_id": "EF-10",
        "typical_control": "Annual dealer recharge",
        "baseline_detection": 8,
        "recommended_action": "Move to a veneer barrier construction and set a permeation rate limit on the drawing.",
        "legacy_part_id": "TR-LEG-AC-999",
        "legacy_part_name": "AC Suction Hose (Program T4, retired 2019)",
    },
    {
        "scope_id": "PT-FILTER-SEP",
        "failure_mode": "Housing thread cross-threading during service causing leak",
        "potential_cause": "Coarse thread pitch on a polymer housing tightened by hand in the field",
        "effect_id": "EF-02",
        "typical_control": "Service training only",
        "baseline_detection": 7,
        "recommended_action": "Adopt a bayonet or quarter-turn interface for serviceable polymer housings.",
        "legacy_part_id": "TR-LEG-FS-993",
        "legacy_part_name": "Water Separator Housing (Program T5, retired 2020)",
    },
    {
        "scope_id": "FAM-FLEX-ROUTING",
        "failure_mode": "Chafing wear-through against adjacent structure",
        "potential_cause": "Line contacting a frame member or bracket edge with no separation clip or sleeve",
        "effect_id": "EF-02",
        "typical_control": "Digital mock-up clearance check at design freeze",
        "baseline_detection": 5,
        "recommended_action": "Hold 15mm minimum clearance to any edge or moving structure; add a rubber-cushioned P-clamp at every crossing.",
        "legacy_part_id": "TR-LEG-GN-801",
        "legacy_part_name": "Multiple flexible lines (Programs T4-T6, recurring)",
    },
    {
        "scope_id": "PT-HOSE-HOTGAS",
        "failure_mode": "Braid strand fatigue fracture at the ferrule",
        "potential_cause": "Thermal cycling of the braid against a rigid crimp with no strain relief",
        "effect_id": "EF-02",
        "typical_control": "Pressure cycling test at type approval",
        "baseline_detection": 6,
        "recommended_action": "Add a moulded strain relief boot at the ferrule and extend cycling validation to the hot discharge duty cycle.",
        "legacy_part_id": "TR-LEG-PN-995",
        "legacy_part_name": "Compressor Discharge Hose (Program T5, retired 2021)",
    },
    {
        "scope_id": "PT-VALVE-SOLENOID",
        "failure_mode": "Coil insulation breakdown from thermal ageing",
        "potential_cause": "Continuous duty coil temperature above the winding insulation class rating",
        "effect_id": "EF-09",
        "typical_control": "Coil resistance check at end of line",
        "baseline_detection": 6,
        "recommended_action": "Move to class H winding insulation and verify coil temperature rise at maximum ambient with the valve held energised.",
        "legacy_part_id": "TR-LEG-VL-957",
        "legacy_part_name": "Transmission Shift Solenoid (Program T4, retired 2019)",
    },
    {
        "scope_id": "PT-CABLE-MECH",
        "failure_mode": "Inner cable corrosion increasing actuation effort",
        "potential_cause": "Liner permeability allowing moisture to reach the uncoated steel core",
        "effect_id": "EF-15",
        "typical_control": "Actuation force check at end of line",
        "baseline_detection": 5,
        "recommended_action": "Specify a galvanised or PTFE-coated inner core and seal both cable ends against water ingress.",
        "legacy_part_id": "TR-LEG-CB-985",
        "legacy_part_name": "Throttle Control Cable (Program T4, retired 2019)",
    },
]


def part_type_of(part_id: str) -> str:
    return PART_ASSIGNMENTS[part_id][0]


def family_of(part_type_id: str) -> str:
    return PART_TYPES[part_type_id]["family"]


def effect_of(part_id: str) -> str:
    return PART_ASSIGNMENTS[part_id][1]


def standard_severity(effect_id: str) -> int:
    return FAILURE_EFFECTS[effect_id]["standard_severity"]


def scope_level(scope_id: str) -> str:
    """A mode attaches either to one part type or to a whole family."""
    return "FAMILY" if scope_id.startswith("FAM-") else "TYPE"


def scopes_for_part(part_id: str):
    """Every scope a part inherits failure modes from, narrowest first."""
    part_type_id = part_type_of(part_id)
    return [part_type_id, family_of(part_type_id)]
