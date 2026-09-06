import os
import csv

# Create data directory if it doesn't exist
os.makedirs("data", exist_ok=True)

# Define 50 realistic heavy tractor component records spanning 5 system packages
PARTS_MASTER = [
    # --- PACKAGE 1: Fuel Routings (1-10) ---
    {
        "part_id": "TR-FL-001",
        "system_package": "Fuel Routings",
        "item_reference": "Hose 3: Fuel Cooler Supply Line",
        "elementary_function": "Transport bio-diesel fuel to cooler circuit without thermal leaks",
        "material_type": "Nitrile Rubber NBR with Aramid Braid",
        "yield_strength_mpa": 120,
        "max_temp_limit_c": 125,
        "elastomeric_rating": "NBR-Standard",
        "drawing_spec_ref": "ES 47646774",
        "failure_mode": "Wear through / line stress from mechanical interference",
        "potential_cause": "Conductive heating & chafing from close proximity to turbo hot sources",
        "historical_severity": 9,
        "historical_occurrence": 7,
        "historical_detection": 4,
        "recommended_action": "Determine final placement of cooler lines; add protective silicone fiberglass chafing sleeve."
    },
    {
        "part_id": "TR-FL-002",
        "system_package": "Fuel Routings",
        "item_reference": "Shutoff Valve Assembly & Mounting",
        "elementary_function": "Isolate fuel flow during emergency shutdown with zero leakage",
        "material_type": "Stainless Steel SS316L",
        "yield_strength_mpa": 290,
        "max_temp_limit_c": 200,
        "elastomeric_rating": "Metallic-Alloy",
        "drawing_spec_ref": "ES 47646775",
        "failure_mode": "Stem seal weep under high thermal cycling",
        "potential_cause": "Packing nut loosening under continuous engine 2nd order harmonic vibration",
        "historical_severity": 8,
        "historical_occurrence": 5,
        "historical_detection": 3,
        "recommended_action": "Apply high-temp thread locker and increase packing nut torque specification to 45 Nm."
    },
    {
        "part_id": "TR-FL-003",
        "system_package": "Fuel Routings",
        "item_reference": "High-Pressure Fuel Common Rail Feed Hose",
        "elementary_function": "Deliver pressurized diesel (15 bar) to common rail manifold",
        "material_type": "Fluoroelastomer FKM with Stainless Wire Shield",
        "yield_strength_mpa": 180,
        "max_temp_limit_c": 160,
        "elastomeric_rating": "Fluoroelastomer FKM",
        "drawing_spec_ref": "CNH-MAT-102",
        "failure_mode": "Thermal degradation & outer cover micro-cracking",
        "potential_cause": "Radiant engine bay heat soak exceeding 140°C continuous rating",
        "historical_severity": 9,
        "historical_occurrence": 6,
        "historical_detection": 4,
        "recommended_action": "Upgrade outer layer to double-braided silicone jacket; relocate 30mm away from manifold."
    },
    {
        "part_id": "TR-FL-004",
        "system_package": "Fuel Routings",
        "item_reference": "Constant-Tension Fuel Return Line Clamp",
        "elementary_function": "Maintain uniform 850N radial clamping force across thermal range",
        "material_type": "51CrV4 Spring Steel (Zinc-Nickel Plated)",
        "yield_strength_mpa": 1150,
        "max_temp_limit_c": 180,
        "elastomeric_rating": "Spring-Steel",
        "drawing_spec_ref": "CNH-SPEC-804",
        "failure_mode": "Low-temperature fuel weeping below -15°C",
        "potential_cause": "Hose rubber cold compression set exceeding clamp spring expansion margin",
        "historical_severity": 6,
        "historical_occurrence": 5,
        "historical_detection": 3,
        "recommended_action": "Upgrade to Belleville-assisted constant tension clamp with 20% higher spring travel."
    },
    {
        "part_id": "TR-FL-005",
        "system_package": "Fuel Routings",
        "item_reference": "Fuel Filter Cast Structural Bracket",
        "elementary_function": "Support dual fuel filter assembly against 20G chassis shock",
        "material_type": "ADC12 Die-Cast Aluminum",
        "yield_strength_mpa": 160,
        "max_temp_limit_c": 150,
        "elastomeric_rating": "Metallic-Alloy",
        "drawing_spec_ref": "ES 47646780",
        "failure_mode": "Resonant fatigue fracture along primary mounting lug fillet",
        "potential_cause": "First bending mode vibration (145 Hz) matching diesel engine firing frequency",
        "historical_severity": 8,
        "historical_occurrence": 6,
        "historical_detection": 5,
        "recommended_action": "Increase fillet radius from 2.5mm to 5.0mm and add 4mm stiffening rib gussets."
    },
    {
        "part_id": "TR-FL-006",
        "system_package": "Fuel Routings",
        "item_reference": "Quick-Connect Nylon Fuel Coupling",
        "elementary_function": "Enable tool-less leak-free fuel line connection during service",
        "material_type": "PA66-GF30 (30% Glass Reinforced Nylon)",
        "yield_strength_mpa": 175,
        "max_temp_limit_c": 130,
        "elastomeric_rating": "Glass-Reinforced-Nylon",
        "drawing_spec_ref": "SAE J2044",
        "failure_mode": "Retaining latch tab embrittlement fracture",
        "potential_cause": "UV exposure combined with calcium chloride road salt chemical degradation",
        "historical_severity": 9,
        "historical_occurrence": 4,
        "historical_detection": 6,
        "recommended_action": "Mandate UV-stabilized PA12 nylon compound and stainless steel secondary locking clip."
    },
    {
        "part_id": "TR-FL-007",
        "system_package": "Fuel Routings",
        "item_reference": "Primary Water Separator Drain Bowl Assembly",
        "elementary_function": "Collect separated water from fuel with manual drain valve",
        "material_type": "Polycarbonate Clear Bowl with Brass Valve",
        "yield_strength_mpa": 65,
        "max_temp_limit_c": 110,
        "elastomeric_rating": "Thermoplastic Polymer",
        "drawing_spec_ref": "CNH-MAT-108",
        "failure_mode": "Stress corrosion cracking of polymer bowl body",
        "potential_cause": "Chemical attack from aggressive biodiesel additives under high ambient temperature",
        "historical_severity": 7,
        "historical_occurrence": 4,
        "historical_detection": 3,
        "recommended_action": "Switch bowl material to chemical-resistant Grilamid TR-90 nylon."
    },
    {
        "part_id": "TR-FL-008",
        "system_package": "Fuel Routings",
        "item_reference": "Fuel Tank Breather & Vapor Vent Tube",
        "elementary_function": "Equalize fuel tank internal pressure during high-flow consumption",
        "material_type": "HDPE High-Density Polyethylene",
        "yield_strength_mpa": 28,
        "max_temp_limit_c": 90,
        "elastomeric_rating": "Thermoplastic Polymer",
        "drawing_spec_ref": "ES 47646788",
        "failure_mode": "Vent line pinch and fuel starvation under chassis twist",
        "potential_cause": "Inadequate clearance to rear axle suspension link during max articulation",
        "historical_severity": 8,
        "historical_occurrence": 5,
        "historical_detection": 4,
        "recommended_action": "Reroute tube through internal frame channel with steel spiral armor sleeve."
    },
    {
        "part_id": "TR-FL-009",
        "system_package": "Fuel Routings",
        "item_reference": "Injector Spill-Off Fuel Return Harness",
        "elementary_function": "Recirculate excess injector fuel back to main storage tank",
        "material_type": "Polyamide PA12 Braided Tubing",
        "yield_strength_mpa": 55,
        "max_temp_limit_c": 120,
        "elastomeric_rating": "Thermoplastic Polymer",
        "drawing_spec_ref": "CNH-SPEC-812",
        "failure_mode": "Barb fitting pop-off under cold start pressure spikes",
        "potential_cause": "Viscous cold fuel creating transient backpressure above barb pull-off rating",
        "historical_severity": 7,
        "historical_occurrence": 6,
        "historical_detection": 3,
        "recommended_action": "Replace push-on barbs with positive-locking brass crimp ferrules."
    },
    {
        "part_id": "TR-FL-010",
        "system_package": "Fuel Routings",
        "item_reference": "Fuel Transfer Pump Suction Line Strainer",
        "elementary_function": "Filter coarse particulates (>200 micron) prior to lift pump intake",
        "material_type": "SS304 Mesh with Nylon Housing",
        "yield_strength_mpa": 210,
        "max_temp_limit_c": 115,
        "elastomeric_rating": "Metallic-Alloy",
        "drawing_spec_ref": "ES 47646792",
        "failure_mode": "Mesh collapse under severe bio-paraffin wax clogging",
        "potential_cause": "Cold diesel wax precipitation restricting flow area during sub-zero operation",
        "historical_severity": 6,
        "historical_occurrence": 5,
        "historical_detection": 3,
        "recommended_action": "Add 50W electric PTC heater element into suction strainer housing."
    },

    # --- PACKAGE 2: AC Routings (11-20) ---
    {
        "part_id": "TR-AC-011",
        "system_package": "AC Routings",
        "item_reference": "HVAC Refrigerant Suction Hose Assembly",
        "elementary_function": "Route gaseous R134a/R1234yf refrigerant from evaporator to compressor",
        "material_type": "PA/IIR Barrier Hose with Steel Ferrules",
        "yield_strength_mpa": 110,
        "max_temp_limit_c": 135,
        "elastomeric_rating": "Butyl-IIR-Barrier",
        "drawing_spec_ref": "ES 47646801",
        "failure_mode": "Refrigerant leakage at aluminum crimp fitting collar",
        "potential_cause": "Axial fretting between ferrule crimp and rubber barrier under engine shake",
        "historical_severity": 7,
        "historical_occurrence": 6,
        "historical_detection": 5,
        "recommended_action": "Mandate 8-segment deep bubble crimp geometry with HNBR inner sealant coating."
    },
    {
        "part_id": "TR-AC-012",
        "system_package": "AC Routings",
        "item_reference": "Swaged Aluminum Condenser Discharge Tube",
        "elementary_function": "Direct hot high-pressure gas from compressor to front condenser radiator",
        "material_type": "Aluminum Alloy 3003-H14",
        "yield_strength_mpa": 145,
        "max_temp_limit_c": 150,
        "elastomeric_rating": "Metallic-Alloy",
        "drawing_spec_ref": "CNH-MAT-204",
        "failure_mode": "Wall abrasion pinhole leak against engine frame rail",
        "potential_cause": "Inadequate clearance (<15mm) allowing contact during chassis torsional twist",
        "historical_severity": 5,
        "historical_occurrence": 5,
        "historical_detection": 4,
        "recommended_action": "Add rigid P-clamp support bracket to maintain guaranteed 25mm clearance."
    },
    {
        "part_id": "TR-AC-013",
        "system_package": "AC Routings",
        "item_reference": "AC Compressor Cast Iron Mount Bracket",
        "elementary_function": "Rigidly bolt heavy compressor to engine block under 22G engine shake",
        "material_type": "Ductile Iron GGG40",
        "yield_strength_mpa": 250,
        "max_temp_limit_c": 250,
        "elastomeric_rating": "Metallic-Alloy",
        "drawing_spec_ref": "ES 47646805",
        "failure_mode": "Brittle fatigue fracture at lower compressor bolt eyelet",
        "potential_cause": "Casting shrinkage porosity combined with cantilevered belt tension load",
        "historical_severity": 8,
        "historical_occurrence": 5,
        "historical_detection": 4,
        "recommended_action": "Specify 100% X-ray inspection on casting lugs; increase lug wall thickness by 3mm."
    },
    {
        "part_id": "TR-AC-014",
        "system_package": "AC Routings",
        "item_reference": "HNBR O-Ring Refrigerant Joint Seal",
        "elementary_function": "Prevent high-pressure R1234yf leakage across block fittings",
        "material_type": "HNBR 70 Shore A (Hydrogenated Nitrile)",
        "yield_strength_mpa": 22,
        "max_temp_limit_c": 140,
        "elastomeric_rating": "HNBR-HighTemp",
        "drawing_spec_ref": "SAE J2064",
        "failure_mode": "Seal extrusion and permanent compression set loss",
        "potential_cause": "Engine compartment heat soak exceeding 135°C after engine shutdown",
        "historical_severity": 6,
        "historical_occurrence": 4,
        "historical_detection": 3,
        "recommended_action": "Upgrade seal compound to FKM Fluorocarbon with PTFE anti-extrusion backup ring."
    },
    {
        "part_id": "TR-AC-015",
        "system_package": "AC Routings",
        "item_reference": "Evaporator Block Expansion Valve Assembly",
        "elementary_function": "Meter liquid refrigerant flow into cab HVAC evaporator core",
        "material_type": "Anodized Extruded Aluminum 6061-T6",
        "yield_strength_mpa": 276,
        "max_temp_limit_c": 120,
        "elastomeric_rating": "Metallic-Alloy",
        "drawing_spec_ref": "CNH-SPEC-820",
        "failure_mode": "Internal orifice clogging and cab cooling loss",
        "potential_cause": "Desiccant silica gel breakdown debris from receiver-drier bottle",
        "historical_severity": 6,
        "historical_occurrence": 4,
        "historical_detection": 2,
        "recommended_action": "Incorporate 50-micron stainless steel inlet filter mesh inside valve body."
    },
    {
        "part_id": "TR-AC-016",
        "system_package": "AC Routings",
        "item_reference": "Receiver Drier Mounting Strap Bracket",
        "elementary_function": "Secure aluminum receiver-drier cylinder to cab subframe",
        "material_type": "Galvanized Low Carbon Steel ST12",
        "yield_strength_mpa": 210,
        "max_temp_limit_c": 100,
        "elastomeric_rating": "Metallic-Alloy",
        "drawing_spec_ref": "ES 47646810",
        "failure_mode": "Galvanic corrosion pitting on aluminum bottle housing",
        "potential_cause": "Direct steel-to-aluminum contact without insulating isolator gasket",
        "historical_severity": 5,
        "historical_occurrence": 6,
        "historical_detection": 3,
        "recommended_action": "Add EPDM rubber sleeve lining inside mounting strap."
    },
    {
        "part_id": "TR-AC-017",
        "system_package": "AC Routings",
        "item_reference": "Cab Roof HVAC Blower Duct Hose Clamp",
        "elementary_function": "Fasten flexible airflow ducting to cab overhead ventilation nozzles",
        "material_type": "AISI 304 Stainless Steel Band Clamp",
        "yield_strength_mpa": 205,
        "max_temp_limit_c": 110,
        "elastomeric_rating": "Metallic-Alloy",
        "drawing_spec_ref": "CNH-MAT-210",
        "failure_mode": "Blower noise chitter and duct slippage",
        "potential_cause": "Torque loss of worm-gear screw under cab heating/cooling cycles",
        "historical_severity": 4,
        "historical_occurrence": 5,
        "historical_detection": 2,
        "recommended_action": "Switch to constant-tension spring-loaded T-bolt clamp."
    },
    {
        "part_id": "TR-AC-018",
        "system_package": "AC Routings",
        "item_reference": "High-Pressure Service Port Valve Cap & Core",
        "elementary_function": "Provide sealed service access point for HVAC recharge equipment",
        "material_type": "Brass Body with Neoprene Internal Seal",
        "yield_strength_mpa": 200,
        "max_temp_limit_c": 120,
        "elastomeric_rating": "Metallic-Alloy",
        "drawing_spec_ref": "SAE J639",
        "failure_mode": "Schrader valve core leak following dealership servicing",
        "potential_cause": "Dirt ingress into valve seat during field servicing without protective dust cap",
        "historical_severity": 5,
        "historical_occurrence": 4,
        "historical_detection": 3,
        "recommended_action": "Tether heavy-duty rubber sealed dust cap directly to service port body."
    },
    {
        "part_id": "TR-AC-019",
        "system_package": "AC Routings",
        "item_reference": "Cab Isolated Liquid Line AC Hose",
        "elementary_function": "Carry condensed liquid refrigerant up cab rear A-pillar",
        "material_type": "EPDM Rubber with Synthetic Textile Braid",
        "yield_strength_mpa": 95,
        "max_temp_limit_c": 125,
        "elastomeric_rating": "EPDM-Peroxide",
        "drawing_spec_ref": "ES 47646818",
        "failure_mode": "A-pillar trim buzzing & structure-borne noise transmission",
        "potential_cause": "Hose stiffness transmitting compressor pulsation frequencies into cab sheet metal",
        "historical_severity": 4,
        "historical_occurrence": 7,
        "historical_detection": 2,
        "recommended_action": "Insert inline hydraulic noise attenuator loop at cab isolation interface."
    },
    {
        "part_id": "TR-AC-020",
        "system_package": "AC Routings",
        "item_reference": "Compressor Variable Displacement Solenoid Valve",
        "elementary_function": "Regulate compressor displacement based on cab cooling demand",
        "material_type": "Steel Housing with Molded Epoxy Coil",
        "yield_strength_mpa": 310,
        "max_temp_limit_c": 140,
        "elastomeric_rating": "Metallic-Alloy",
        "drawing_spec_ref": "CNH-SPEC-828",
        "failure_mode": "Solenoid coil short circuit under high humidity washdown",
        "potential_cause": "High-pressure power washer intrusion past connector seal",
        "historical_severity": 7,
        "historical_occurrence": 3,
        "historical_detection": 4,
        "recommended_action": "Upgrade connector housing to Deutsch DT IP69K sealed connector."
    },

    # --- PACKAGE 3: Hydraulic Steering & Implement Routings (21-30) ---
    {
        "part_id": "TR-HYD-021",
        "system_package": "Hydraulic Steering Routings",
        "item_reference": "Steering Cylinder High-Pressure Flex Hose",
        "elementary_function": "Transmit 350 bar hydraulic power to front axle steering cylinder",
        "material_type": "Four-Spiral Steel Wire Reinforced Rubber (SAE 100R15)",
        "yield_strength_mpa": 450,
        "max_temp_limit_c": 125,
        "elastomeric_rating": "Wire-Spiral-Rubber",
        "drawing_spec_ref": "ES 47646830",
        "failure_mode": "Catastrophic hose wire burst & high-pressure oil spray",
        "potential_cause": "Transient hydraulic shock wave exceeding impulse fatigue limit (500k cycles)",
        "historical_severity": 10,
        "historical_occurrence": 5,
        "historical_detection": 4,
        "recommended_action": "Upgrade hose specification to 6-spiral wire SAE 100R17 rated for 420 bar working pressure."
    },
    {
        "part_id": "TR-HYD-022",
        "system_package": "Hydraulic Steering Routings",
        "item_reference": "Steering Arm Forged Steel Bracket",
        "elementary_function": "Transfer steering cylinder thrust load to kingpin spindle assembly",
        "material_type": "Forged AISI 4140 Quenched & Tempered",
        "yield_strength_mpa": 880,
        "max_temp_limit_c": 300,
        "elastomeric_rating": "Metallic-Alloy",
        "drawing_spec_ref": "CNH-MAT-302",
        "failure_mode": "Bore micro-fretting & steering play accumulation",
        "potential_cause": "Insufficient bore surface hardness (HRC < 35) under cyclic steering torque",
        "historical_severity": 8,
        "historical_occurrence": 4,
        "historical_detection": 5,
        "recommended_action": "Induction harden kingpin taper bore to HRC 55-60 to depth of 2.5mm."
    },
    {
        "part_id": "TR-HYD-023",
        "system_package": "Hydraulic Steering Routings",
        "item_reference": "Steel Hydraulic Swivel Bulkhead Adapter",
        "elementary_function": "Provide 360-degree rotation joint for front loader hydraulic lines",
        "material_type": "Free-Cutting Carbon Steel 11SMn30 (Zinc Plated)",
        "yield_strength_mpa": 380,
        "max_temp_limit_c": 180,
        "elastomeric_rating": "Metallic-Alloy",
        "drawing_spec_ref": "ISO 8434-1",
        "failure_mode": "Thread shear & fitting disconnection during maintenance",
        "potential_cause": "Over-torquing beyond 60 Nm combined with low shear strength of 11SMn30 steel",
        "historical_severity": 7,
        "historical_occurrence": 3,
        "historical_detection": 2,
        "recommended_action": "Upgrade adapter body material to High-Strength Forged 42CrMo4 Steel."
    },
    {
        "part_id": "TR-HYD-024",
        "system_package": "Hydraulic Steering Routings",
        "item_reference": "Priority Steering Valve Control Line",
        "elementary_function": "Ensure steering circuit maintains hydraulic oil priority over implement hydraulics",
        "material_type": "Cold Drawn Seamless Steel Tube E235+N",
        "yield_strength_mpa": 340,
        "max_temp_limit_c": 200,
        "elastomeric_rating": "Metallic-Alloy",
        "drawing_spec_ref": "ES 47646835",
        "failure_mode": "Crater pitting & pinhole oil leak under severe salt spray",
        "potential_cause": "Zinc plating breakdown under aggressive winter de-icing chemicals",
        "historical_severity": 9,
        "historical_occurrence": 3,
        "historical_detection": 4,
        "recommended_action": "Mandate Zinc-Nickel (ZnNi) plating with minimum 720-hour salt spray endurance."
    },
    {
        "part_id": "TR-HYD-025",
        "system_package": "Hydraulic Steering Routings",
        "item_reference": "Low-Pressure Hydraulic Oil Return Hose",
        "elementary_function": "Return oil from steering valve back to main hydraulic reservoir",
        "material_type": "NBR Synthetic Rubber with Textile Reinforcement",
        "yield_strength_mpa": 85,
        "max_temp_limit_c": 110,
        "elastomeric_rating": "NBR-Standard",
        "drawing_spec_ref": "CNH-MAT-308",
        "failure_mode": "Hose collapse & oil cavitation under cold start suction",
        "potential_cause": "Vacuum collapse of inner rubber tube when fluid viscosity is high at -20°C",
        "historical_severity": 6,
        "historical_occurrence": 4,
        "historical_detection": 3,
        "recommended_action": "Insert internal stainless steel helical wire coil inside hose lumen."
    },
    {
        "part_id": "TR-HYD-026",
        "system_package": "Hydraulic Steering Routings",
        "item_reference": "Rear 3-Point Hitch Implement Cylinder Hose",
        "elementary_function": "Supply high-pressure fluid to lift heavy agricultural implements",
        "material_type": "Two-Wire Braid Rubber Hose (SAE 100R2AT)",
        "yield_strength_mpa": 280,
        "max_temp_limit_c": 120,
        "elastomeric_rating": "Wire-Braid-Rubber",
        "drawing_spec_ref": "ES 47646840",
        "failure_mode": "Outer cover gouging from 3-point hitch sway link pinch",
        "potential_cause": "Insufficient clearance during extreme hitch lateral sway movement",
        "historical_severity": 8,
        "historical_occurrence": 6,
        "historical_detection": 3,
        "recommended_action": "Add heavy-duty UHMW polyethylene spiral wrap guard over hose length."
    },
    {
        "part_id": "TR-HYD-027",
        "system_package": "Hydraulic Steering Routings",
        "item_reference": "Hydrostatic Steering Orbitrol Valve Mounting Plate",
        "elementary_function": "Attach steering unit below cab floor pan with isolation dampers",
        "material_type": "Structural Steel S355JR",
        "yield_strength_mpa": 355,
        "max_temp_limit_c": 150,
        "elastomeric_rating": "Metallic-Alloy",
        "drawing_spec_ref": "CNH-SPEC-840",
        "failure_mode": "Cab floor pan oil drumming & steering wheel vibration",
        "potential_cause": "Dampener stiffness too high transmitting orbitrol pressure ripples",
        "historical_severity": 4,
        "historical_occurrence": 6,
        "historical_detection": 2,
        "recommended_action": "Redesign with dual-durometer tuned rubber isolation bushings."
    },
    {
        "part_id": "TR-HYD-028",
        "system_package": "Hydraulic Steering Routings",
        "item_reference": "Implement Quick-Disconnect Female Coupler",
        "elementary_function": "Provide push-pull coupling interface for tractor trailing equipment",
        "material_type": "Hardened Carbon Steel 45 (Chrome Plated)",
        "yield_strength_mpa": 600,
        "max_temp_limit_c": 150,
        "elastomeric_rating": "Metallic-Alloy",
        "drawing_spec_ref": "ISO 5675",
        "failure_mode": "Poppet valve stuck open leading to hydraulic oil spillage",
        "potential_cause": "Dirt particle contamination jamming internal poppet return spring",
        "historical_severity": 7,
        "historical_occurrence": 5,
        "historical_detection": 2,
        "recommended_action": "Include automatic breakaway dust covers with internal flushing grooves."
    },
    {
        "part_id": "TR-HYD-029",
        "system_package": "Hydraulic Steering Routings",
        "item_reference": "Electro-Hydraulic Steering Pilot Sensor Line",
        "elementary_function": "Transmit pilot hydraulic signal to auto-guidance valve block",
        "material_type": "Micro-Bore Flexible Polyamide Hose",
        "yield_strength_mpa": 140,
        "max_temp_limit_c": 115,
        "elastomeric_rating": "Thermoplastic Polymer",
        "drawing_spec_ref": "ES 47646848",
        "failure_mode": "Steering drift due to air entrapment in pilot line",
        "potential_cause": "High compliance in micro-bore tube expanding under pilot pressure",
        "historical_severity": 7,
        "historical_occurrence": 4,
        "historical_detection": 4,
        "recommended_action": "Replace flex tube with rigid stainless steel 4mm hard line."
    },
    {
        "part_id": "TR-HYD-030",
        "system_package": "Hydraulic Steering Routings",
        "item_reference": "Hydraulic Oil Cooler Bypass Thermo-Valve",
        "elementary_function": "Bypass hydraulic oil cooler during cold startup to accelerate warm-up",
        "material_type": "Cast Aluminum Alloy AC4C",
        "yield_strength_mpa": 220,
        "max_temp_limit_c": 160,
        "elastomeric_rating": "Metallic-Alloy",
        "drawing_spec_ref": "CNH-MAT-318",
        "failure_mode": "Wax element stuck in bypass mode causing oil overheating",
        "potential_cause": "Thermal degradation of paraffin wax charge after 1,500 operating hours",
        "historical_severity": 8,
        "historical_occurrence": 4,
        "historical_detection": 3,
        "recommended_action": "Replace wax element with bimetallic disc actuator rated for 5,000 hours."
    },

    # --- PACKAGE 4: Engine Cooling Routings (31-40) ---
    {
        "part_id": "TR-ENG-031",
        "system_package": "Engine Cooling Routings",
        "item_reference": "Radiator Upper Coolant Feed Hose",
        "elementary_function": "Deliver 95°C engine coolant from thermostat housing to radiator",
        "material_type": "Peroxide-Cured EPDM with Polyester Reinforcement",
        "yield_strength_mpa": 80,
        "max_temp_limit_c": 140,
        "elastomeric_rating": "EPDM-Peroxide",
        "drawing_spec_ref": "ES 47646860",
        "failure_mode": "Electrochemical degradation (ECD) inner tube micro-channeling",
        "potential_cause": "Stray electrical currents in coolant fluid creating galvanic degradation",
        "historical_severity": 8,
        "historical_occurrence": 5,
        "historical_detection": 4,
        "recommended_action": "Mandate ECD-resistant EPDM rubber compound (SAE J20 R4 Class D-1)."
    },
    {
        "part_id": "TR-ENG-032",
        "system_package": "Engine Cooling Routings",
        "item_reference": "Radiator Lower Suction Coolant Hose",
        "elementary_function": "Return cooled glycol mixture from radiator bottom tank to water pump",
        "material_type": "EPDM Rubber with Internal Helical Steel Wire",
        "yield_strength_mpa": 85,
        "max_temp_limit_c": 135,
        "elastomeric_rating": "EPDM-Peroxide",
        "drawing_spec_ref": "CNH-MAT-402",
        "failure_mode": "Hose suction collapse under high engine RPM",
        "potential_cause": "Corrosion fracture of internal wire spring under acidic glycol breakdown",
        "historical_severity": 9,
        "historical_occurrence": 4,
        "historical_detection": 4,
        "recommended_action": "Switch wire spring material to stainless steel 302 wire."
    },
    {
        "part_id": "TR-ENG-033",
        "system_package": "Engine Cooling Routings",
        "item_reference": "Coolant Degassing Expansion Tank Hose",
        "elementary_function": "Vent trapped air and steam from cylinder head to deaeration tank",
        "material_type": "Silicone Rubber VMQ with Aramid Braid",
        "yield_strength_mpa": 90,
        "max_temp_limit_c": 175,
        "elastomeric_rating": "Silicone-VMQ",
        "drawing_spec_ref": "ES 47646865",
        "failure_mode": "Coolant vapor permeation loss requiring frequent top-ups",
        "potential_cause": "High steam permeability coefficient of standard silicone rubber",
        "historical_severity": 5,
        "historical_occurrence": 6,
        "historical_detection": 2,
        "recommended_action": "Add fluoro-silicone (FVMQ) inner liner barrier layer."
    },
    {
        "part_id": "TR-ENG-034",
        "system_package": "Engine Cooling Routings",
        "item_reference": "Thermostat Housing Constant-Tension Clamp",
        "elementary_function": "Maintain 900N clamping load around cast aluminum thermostat neck",
        "material_type": "Stainless Steel 301 Band with Belleville Washers",
        "yield_strength_mpa": 950,
        "max_temp_limit_c": 200,
        "elastomeric_rating": "Spring-Steel",
        "drawing_spec_ref": "CNH-SPEC-850",
        "failure_mode": "Coolant weeping during extreme cold soak (-25°C)",
        "potential_cause": "EPDM hose neck relaxation exceeding clamp Belleville spring travel",
        "historical_severity": 6,
        "historical_occurrence": 5,
        "historical_detection": 3,
        "recommended_action": "Increase Belleville washer stack height to allow double spring displacement."
    },
    {
        "part_id": "TR-ENG-035",
        "system_package": "Engine Cooling Routings",
        "item_reference": "Water Pump Bypass Hard Rigid Tube",
        "elementary_function": "Recirculate coolant through engine block during engine warm-up",
        "material_type": "E235 Steel Tube with Electro-Coated Finish",
        "yield_strength_mpa": 330,
        "max_temp_limit_c": 180,
        "elastomeric_rating": "Metallic-Alloy",
        "drawing_spec_ref": "ES 47646870",
        "failure_mode": "Internal cavitation erosion pitting at 90-degree elbow bend",
        "potential_cause": "High coolant velocity (>4.5 m/s) creating localized vapor bubble collapse",
        "historical_severity": 7,
        "historical_occurrence": 4,
        "historical_detection": 4,
        "recommended_action": "Increase bend radius ratio R/D from 1.5 to 2.5 to reduce flow turbulence."
    },
    {
        "part_id": "TR-ENG-036",
        "system_package": "Engine Cooling Routings",
        "item_reference": "Transmission Oil Cooler Heat Exchanger Hose",
        "elementary_function": "Route transmission fluid to liquid-to-liquid oil cooler",
        "material_type": "HNBR Inner, Aramid Reinforcement, EPDM Cover",
        "yield_strength_mpa": 115,
        "max_temp_limit_c": 150,
        "elastomeric_rating": "HNBR-HighTemp",
        "drawing_spec_ref": "CNH-MAT-410",
        "failure_mode": "Oil blistering and outer cover delamination",
        "potential_cause": "Transmission fluid additives (sulfur-phosphorus EP) swelling inner rubber",
        "historical_severity": 8,
        "historical_occurrence": 4,
        "historical_detection": 3,
        "recommended_action": "Upgrade inner rubber liner to Fluoroelastomer FKM."
    },
    {
        "part_id": "TR-ENG-037",
        "system_package": "Engine Cooling Routings",
        "item_reference": "Turbocharger Coolant Supply Hard Line",
        "elementary_function": "Feed pressurized coolant to turbo center housing bearing section",
        "material_type": "Seamless Stainless Steel 316L",
        "yield_strength_mpa": 290,
        "max_temp_limit_c": 450,
        "elastomeric_rating": "Metallic-Alloy",
        "drawing_spec_ref": "ES 47646878",
        "failure_mode": "Thermal shock cracking at banjo fitting brazed joint",
        "potential_cause": "Severe thermal gradient during hot engine shutdown (coking temperature >300°C)",
        "historical_severity": 9,
        "historical_occurrence": 3,
        "historical_detection": 5,
        "recommended_action": "Replace brazed banjo fitting with one-piece forged stainless steel fitting."
    },
    {
        "part_id": "TR-ENG-038",
        "system_package": "Engine Cooling Routings",
        "item_reference": "EGR Cooler Return Coolant Hose",
        "elementary_function": "Carry heated coolant away from Exhaust Gas Recirculation cooler",
        "material_type": "High-Temp Aramid Reinforced Silicone (VMQ)",
        "yield_strength_mpa": 105,
        "max_temp_limit_c": 200,
        "elastomeric_rating": "Silicone-VMQ",
        "drawing_spec_ref": "CNH-SPEC-860",
        "failure_mode": "Hose hardening & brittle snapping when touched during maintenance",
        "potential_cause": "Exhaust heat radiation exceeding 180°C continuous silicone thermal limit",
        "historical_severity": 7,
        "historical_occurrence": 5,
        "historical_detection": 3,
        "recommended_action": "Install reflective aluminum heat shield guard over EGR return hose."
    },
    {
        "part_id": "TR-ENG-039",
        "system_package": "Engine Cooling Routings",
        "item_reference": "Engine Fan Shroud Structural Support Bracket",
        "elementary_function": "Position cooling fan shroud relative to engine crankshaft pulley",
        "material_type": "Stamped High-Strength Steel S420MC",
        "yield_strength_mpa": 420,
        "max_temp_limit_c": 150,
        "elastomeric_rating": "Metallic-Alloy",
        "drawing_spec_ref": "ES 47646885",
        "failure_mode": "Fan blade tip clipping against shroud ring",
        "potential_cause": "Bracket flexure under heavy chassis twist allowing shroud misalignment",
        "historical_severity": 9,
        "historical_occurrence": 4,
        "historical_detection": 4,
        "recommended_action": "Add diagonal cross-brace tie rod to stiffen fan shroud structure."
    },
    {
        "part_id": "TR-ENG-040",
        "system_package": "Engine Cooling Routings",
        "item_reference": "Engine Block Coolant Drain Valve Cock",
        "elementary_function": "Allow complete drainage of engine coolant during overhaul service",
        "material_type": "Forged Brass CW614N",
        "yield_strength_mpa": 250,
        "max_temp_limit_c": 160,
        "elastomeric_rating": "Metallic-Alloy",
        "drawing_spec_ref": "CNH-MAT-420",
        "failure_mode": "Dezincification corrosion & stem snapping upon opening",
        "potential_cause": "Aggressive tap water used in field topping off coolant mixture",
        "historical_severity": 6,
        "historical_occurrence": 4,
        "historical_detection": 2,
        "recommended_action": "Switch drain cock material to DZR (Dezincification Resistant) Brass CW602N."
    },

    # --- PACKAGE 5: Electrical & Pneumatic Brake Routings (41-50) ---
    {
        "part_id": "TR-ELE-041",
        "system_package": "Pneumatic & Electrical Routings",
        "item_reference": "Trailer Pneumatic Brake Supply Line",
        "elementary_function": "Deliver 8.5 bar compressed air to trailer pneumatic braking system",
        "material_type": "Polyamide PA12 Air Brake Tubing",
        "yield_strength_mpa": 60,
        "max_temp_limit_c": 100,
        "elastomeric_rating": "Thermoplastic Polymer",
        "drawing_spec_ref": "DIN 74324",
        "failure_mode": "Kinking and trailer brake locking during sharp turn",
        "potential_cause": "Inadequate bend radius allowance at cab rear articulation joint",
        "historical_severity": 10,
        "historical_occurrence": 4,
        "historical_detection": 5,
        "recommended_action": "Incorporate coiled spiral spring-back air line assembly (Gladhand extension)."
    },
    {
        "part_id": "TR-ELE-042",
        "system_package": "Pneumatic & Electrical Routings",
        "item_reference": "Main Engine Wiring Harness Flexible Conduit",
        "elementary_function": "Protect 48-pin ECU sensor wires from heat, oil, and abrasion",
        "material_type": "Modified Polypropylene Slit Corrugated Tubing",
        "yield_strength_mpa": 35,
        "max_temp_limit_c": 135,
        "elastomeric_rating": "Thermoplastic Polymer",
        "drawing_spec_ref": "ES 47646901",
        "failure_mode": "Conduit melting & wire insulation short circuit to ground",
        "potential_cause": "Conduit sagging onto exhaust manifold heat shield",
        "historical_severity": 9,
        "historical_occurrence": 5,
        "historical_detection": 4,
        "recommended_action": "Upgrade conduit material to high-temp PA6 nylon with metal P-clamp retaining clips."
    },
    {
        "part_id": "TR-ELE-043",
        "system_package": "Pneumatic & Electrical Routings",
        "item_reference": "Heavy-Duty Battery Cable Rubber Insulated P-Clamp",
        "elementary_function": "Support 70mm2 starter motor positive battery cable along frame rail",
        "material_type": "Galvanized Steel Strap with EPDM Cushion",
        "yield_strength_mpa": 220,
        "max_temp_limit_c": 120,
        "elastomeric_rating": "EPDM-Peroxide",
        "drawing_spec_ref": "CNH-MAT-502",
        "failure_mode": "Short circuit arc-flash against frame rail",
        "potential_cause": "EPDM rubber cushion wearing through under continuous cable vibration",
        "historical_severity": 10,
        "historical_occurrence": 3,
        "historical_detection": 5,
        "recommended_action": "Add secondary thick-walled polyolefin heat shrink sleeve over cable under P-clamp."
    },
    {
        "part_id": "TR-ELE-044",
        "system_package": "Pneumatic & Electrical Routings",
        "item_reference": "Starter Motor Solenoid Protective Boot",
        "elementary_function": "Seal starter high-current B+ terminal against water and mud splash",
        "material_type": "Silicone Rubber Elastomer",
        "yield_strength_mpa": 15,
        "max_temp_limit_c": 160,
        "elastomeric_rating": "Silicone-VMQ",
        "drawing_spec_ref": "ES 47646905",
        "failure_mode": "Boot tearing and starter corrosion failure",
        "potential_cause": "Tearing during assembly due to sharp edges on terminal lug",
        "historical_severity": 7,
        "historical_occurrence": 6,
        "historical_detection": 3,
        "recommended_action": "Specify tear-resistant liquid silicone rubber (LSR) with rounded terminal lugs."
    },
    {
        "part_id": "TR-ELE-045",
        "system_package": "Pneumatic & Electrical Routings",
        "item_reference": "Air Compressor Discharge Stainless Steel Braided Tube",
        "elementary_function": "Convey hot compressed air (220°C) from compressor to air dryer",
        "material_type": "PTFE Inner Tube with Stainless Steel Wire Braid",
        "yield_strength_mpa": 220,
        "max_temp_limit_c": 260,
        "elastomeric_rating": "PTFE-Fluoropolymer",
        "drawing_spec_ref": "CNH-SPEC-875",
        "failure_mode": "Carbon buildup restriction inside PTFE tube lumen",
        "potential_cause": "Compressor oil carryover coking under extreme 220°C discharge heat",
        "historical_severity": 8,
        "historical_occurrence": 4,
        "historical_detection": 3,
        "recommended_action": "Increase internal tube diameter from 12mm to 16mm and add cooling fin section."
    },
    {
        "part_id": "TR-ELE-046",
        "system_package": "Pneumatic & Electrical Routings",
        "item_reference": "Wheel Speed ABS Sensor Cable Guard Bracket",
        "elementary_function": "Protect wheel speed sensor wiring from crop debris and mud packing",
        "material_type": "Stamped Stainless Steel 304",
        "yield_strength_mpa": 290,
        "max_temp_limit_c": 200,
        "elastomeric_rating": "Metallic-Alloy",
        "drawing_spec_ref": "ES 47646910",
        "failure_mode": "Sensor wire rip-out during field tilling",
        "potential_cause": "Heavy corn stalk wrapping around unprotected wheel speed cable loop",
        "historical_severity": 8,
        "historical_occurrence": 6,
        "historical_detection": 4,
        "recommended_action": "Fully enclose cable inside heavy-duty steel channel guard."
    },
    {
        "part_id": "TR-ELE-047",
        "system_package": "Pneumatic & Electrical Routings",
        "item_reference": "Park Brake Actuator Bowden Pull Cable Sleeve",
        "elementary_function": "Transmit mechanical handbrake lever pull force to rear axle calipers",
        "material_type": "Steel Wire Core with POM Polyacetal Liner & PVC Jacket",
        "yield_strength_mpa": 450,
        "max_temp_limit_c": 90,
        "elastomeric_rating": "Thermoplastic Polymer",
        "drawing_spec_ref": "CNH-MAT-510",
        "failure_mode": "Park brake binding & pad drag in winter",
        "potential_cause": "Water ingress freezing inside cable liner at sub-zero temperatures",
        "historical_severity": 8,
        "historical_occurrence": 5,
        "historical_detection": 3,
        "recommended_action": "Incorporate double-lip silicone end wiper seals with synthetic low-temp grease."
    },
    {
        "part_id": "TR-ELE-048",
        "system_package": "Pneumatic & Electrical Routings",
        "item_reference": "Cab Floor Frame Wire Harness Pass-Through Grommet",
        "elementary_function": "Seal cab floor pan wire penetration against dust, noise, and water",
        "material_type": "EPDM Closed-Cell Sponge Rubber",
        "yield_strength_mpa": 10,
        "max_temp_limit_c": 120,
        "elastomeric_rating": "EPDM-Peroxide",
        "drawing_spec_ref": "ES 47646918",
        "failure_mode": "Dust & water leaks into cab interior during pressure washing",
        "potential_cause": "Incomplete sealing around bundled irregular wire harness shapes",
        "historical_severity": 6,
        "historical_occurrence": 6,
        "historical_detection": 2,
        "recommended_action": "Switch to pourable polyurethane gel foam sealing grommet block."
    },
    {
        "part_id": "TR-ELE-049",
        "system_package": "Pneumatic & Electrical Routings",
        "item_reference": "Hydraulic Main Pressure Transducer Fitting",
        "elementary_function": "Mount 0-400 bar electronic pressure sensor into valve manifold",
        "material_type": "High-Strength Steel 42CrMo4",
        "yield_strength_mpa": 750,
        "max_temp_limit_c": 150,
        "elastomeric_rating": "Metallic-Alloy",
        "drawing_spec_ref": "CNH-SPEC-885",
        "failure_mode": "Sensor diaphragm fatigue failure & internal oil leak",
        "potential_cause": "High-frequency hydraulic pressure ripple spikes from piston pump",
        "historical_severity": 9,
        "historical_occurrence": 3,
        "historical_detection": 5,
        "recommended_action": "Incorporate 0.8mm micro-orifice snubber inside sensor adapter thread port."
    },
    {
        "part_id": "TR-ELE-050",
        "system_package": "Pneumatic & Electrical Routings",
        "item_reference": "Rear Differential Lock Pneumatic Actuator Line",
        "elementary_function": "Engage rear differential lock via 6 bar pneumatic pressure pulse",
        "material_type": "Polyurethane PUR Flexible Tubing",
        "yield_strength_mpa": 45,
        "max_temp_limit_c": 85,
        "elastomeric_rating": "Thermoplastic Polymer",
        "drawing_spec_ref": "ES 47646925",
        "failure_mode": "Loss of differential lock engagement under heavy field pull",
        "potential_cause": "Tubing softening and swelling under ambient hydraulic fluid mist",
        "historical_severity": 7,
        "historical_occurrence": 4,
        "historical_detection": 3,
        "recommended_action": "Upgrade tube material to oil-resistant Polyamide PA11."
    }
]


# =====================================================================
# NORMALIZED DATA MODEL EMITTER
# =====================================================================
# PARTS_MASTER above stays the single authoring source for the 50 active
# parts. Everything below reshapes it into the normalized tables the
# platform actually runs on:
#
#   part_types.csv          - the family / type taxonomy every part belongs to
#   failure_effects.csv     - one severity per effect, org wide
#   failure_mode_catalog.csv- failure modes keyed by TYPE or FAMILY, with provenance
#   field_issues.csv        - many warranty records per part (not 1:1)
#   dfmea_worksheet.csv     - the DFMEA actually on file today (incomplete
#                             on purpose - this is what gap detection diffs
#                             the catalog against)
#
# The three v1 files are still emitted unchanged so the existing app keeps
# working while the new layer is wired in.

import random
from datetime import date, timedelta

from taxonomy import (
    PART_FAMILIES,
    PART_TYPES,
    FAILURE_EFFECTS,
    PART_ASSIGNMENTS,
    PRIOR_PROGRAM_MODES,
    family_of,
    scope_level,
    scopes_for_part,
)

SEED = 20260907
DATA_DIR = "data"

# AIAG-style occurrence anchor: score -> incidents per 1000 units in service.
OCCURRENCE_RATE_PER_1000 = {
    10: 120.0, 9: 55.0, 8: 22.0, 7: 11.0, 6: 5.0,
    5: 2.0, 4: 1.0, 3: 0.5, 2: 0.1, 1: 0.01,
}

# Detection score -> where the failure was actually caught. A mode only
# escapes to the field when the design control is weak, so the stage and
# the detection score have to agree or the data is not credible.
DETECTION_STAGE = [
    (8, "FIELD_CUSTOMER"),
    (6, "DEALER_SERVICE"),
    (4, "END_OF_LINE_TEST"),
    (0, "VALIDATION_TEST"),
]

# Parts whose DFMEA on file scores an effect below the organization
# standard - seeded deliberately so the severity consistency check has
# something real to find.
SEVERITY_DRIFT_PARTS = {
    "TR-FL-003": -2,
    "TR-HYD-021": -2,
    "TR-ELE-041": -3,
    "TR-AC-020": -2,
    "TR-ENG-037": -1,
    "TR-ELE-043": -2,
}

WORKSHOP_TEAMS = [
    "DFMEA Workshop Team A",
    "DFMEA Workshop Team B",
    "DFMEA Workshop Team C",
]


def _scope_suffix(scope_id):
    return scope_id.replace("PT-", "").replace("FAM-", "")


def _detection_stage(detection):
    for threshold, stage in DETECTION_STAGE:
        if detection >= threshold:
            return stage
    return "VALIDATION_TEST"


def build_catalog():
    """
    Failure modes keyed by the SCOPE they generalize to, from current and
    prior programs. A mode proven on one part attaches to that part's type;
    a lesson that holds across a whole family attaches to the family.
    """
    catalog = []
    counters = {}

    # 1. Every active part contributes its proven failure mode to its type.
    for part in PARTS_MASTER:
        pid = part["part_id"]
        part_type_id, effect_id = PART_ASSIGNMENTS[pid]
        counters[part_type_id] = counters.get(part_type_id, 0) + 1
        catalog.append({
            "mode_id": "FM-%s-%02d" % (_scope_suffix(part_type_id), counters[part_type_id]),
            "scope_id": part_type_id,
            "scope_level": "TYPE",
            "failure_mode": part["failure_mode"],
            "potential_cause": part["potential_cause"],
            "effect_id": effect_id,
            "typical_control": "Design review and validation test plan",
            "baseline_detection": part["historical_detection"],
            "recommended_action": part["recommended_action"],
            "origin": "CURRENT_PROGRAM",
            "origin_part_id": pid,
            "origin_part_name": part["item_reference"],
        })

    # 2. Prior programs contribute modes whose parts have left the BOM.
    for mode in PRIOR_PROGRAM_MODES:
        scope_id = mode["scope_id"]
        counters[scope_id] = counters.get(scope_id, 0) + 1
        catalog.append({
            "mode_id": "FM-%s-%02d" % (_scope_suffix(scope_id), counters[scope_id]),
            "scope_id": scope_id,
            "scope_level": scope_level(scope_id),
            "failure_mode": mode["failure_mode"],
            "potential_cause": mode["potential_cause"],
            "effect_id": mode["effect_id"],
            "typical_control": mode["typical_control"],
            "baseline_detection": mode["baseline_detection"],
            "recommended_action": mode["recommended_action"],
            "origin": "PRIOR_PROGRAM",
            "origin_part_id": mode["legacy_part_id"],
            "origin_part_name": mode["legacy_part_name"],
        })

    return catalog


def build_field_issues(catalog, rng):
    """Many warranty records per part, with the volumes Occurrence derives from."""
    issues = []
    part_by_id = {p["part_id"]: p for p in PARTS_MASTER}
    prior_by_mode = {m["failure_mode"]: m for m in PRIOR_PROGRAM_MODES}

    for entry in catalog:
        mode_id = entry["mode_id"]
        origin_part = entry["origin_part_id"]
        effect = FAILURE_EFFECTS[entry["effect_id"]]

        if entry["origin"] == "CURRENT_PROGRAM":
            part = part_by_id[origin_part]
            occurrence_anchor = part["historical_occurrence"]
            part_name = part["item_reference"]
        else:
            occurrence_anchor = rng.randint(4, 7)
            part_name = prior_by_mode[entry["failure_mode"]]["legacy_part_name"]

        # More recurrent modes produce more separate warranty records.
        record_count = 1 + min(3, occurrence_anchor // 3)
        rate = OCCURRENCE_RATE_PER_1000[occurrence_anchor]

        for _ in range(record_count):
            report_date = date(2021, 1, 1) + timedelta(days=rng.randint(0, 1750))
            units = rng.randrange(1200, 9200, 100)
            claims = max(1, int(round(rate * units / 1000.0)))
            issues.append({
                "issue_id": None,
                "part_id": origin_part,
                "scope_id": entry["scope_id"],
                "mode_id": mode_id,
                "report_date": report_date.isoformat(),
                "units_in_service": units,
                "claim_count": claims,
                "median_machine_hours": rng.randrange(200, 3800, 50),
                "detection_stage": _detection_stage(entry["baseline_detection"]),
                "observed_effect_id": entry["effect_id"],
                "observed_severity": effect["standard_severity"],
                "description": "%s observed on %s. Root cause: %s" % (
                    entry["failure_mode"], part_name, entry["potential_cause"]),
            })

    # Number the 8D reports chronologically, the way a real register runs.
    issues.sort(key=lambda r: (r["report_date"], r["part_id"], r["mode_id"]))
    seq = {}
    for record in issues:
        year = int(record["report_date"][:4])
        seq[year] = seq.get(year, 0) + 1
        record["issue_id"] = "8D-%d-%04d" % (year, seq[year])
    return issues


def build_worksheet(catalog, rng):
    """The DFMEA on file today - deliberately covering only part of the catalog."""
    by_scope = {}
    for entry in catalog:
        by_scope.setdefault(entry["scope_id"], []).append(entry)

    rows = []
    for idx, part in enumerate(PARTS_MASTER):
        pid = part["part_id"]
        # A part inherits from its own type and from its family.
        applicable = [e for scope in scopes_for_part(pid) for e in by_scope.get(scope, [])]
        own_mode = next(e for e in applicable if e["origin_part_id"] == pid)
        others = [e for e in applicable if e["mode_id"] != own_mode["mode_id"]]

        # The workshop always analyses the mode this exact part is known for,
        # then a subset of what the rest of the type has taught the company.
        chosen = [own_mode]
        for entry in others:
            if rng.random() < 0.45:
                chosen.append(entry)
        # Guarantee at least one unanalysed mode wherever the type has more
        # than one - a DFMEA with nothing missing is not a realistic baseline.
        while others and len(chosen) > len(others):
            chosen.pop()

        team = WORKSHOP_TEAMS[idx % len(WORKSHOP_TEAMS)]
        analysis_date = (date(2025, 1, 6) + timedelta(days=(idx % 40) * 7)).isoformat()
        drift = SEVERITY_DRIFT_PARTS.get(pid, 0)

        for entry in chosen:
            standard_s = FAILURE_EFFECTS[entry["effect_id"]]["standard_severity"]
            severity = standard_s
            if drift and entry["mode_id"] == own_mode["mode_id"]:
                severity = max(1, standard_s + drift)

            if entry["mode_id"] == own_mode["mode_id"]:
                occurrence = part["historical_occurrence"]
                detection = part["historical_detection"]
            else:
                # Inherited modes get a workshop estimate, not field evidence.
                occurrence = rng.randint(2, 5)
                detection = max(1, min(10, entry["baseline_detection"] + rng.randint(-1, 1)))

            rows.append({
                "part_id": pid,
                "mode_id": entry["mode_id"],
                "severity": severity,
                "occurrence": occurrence,
                "detection": detection,
                "current_design_control": entry["typical_control"],
                "analyzed_by": team,
                "analysis_date": analysis_date,
                "revision": "Rev A",
            })

    return rows


def write_csv(path, header, rows):
    with open(path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=header, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print("[OK] %-42s %d rows" % (path, len(rows)))


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    rng = random.Random(SEED)

    # ---- v1 tables (unchanged consumers keep working) ----------------
    write_csv(
        os.path.join(DATA_DIR, "bom_package_hierarchy.csv"),
        ["part_id", "system_package", "item_reference", "elementary_function",
         "material_type", "part_type_id"],
        [dict(p, part_type_id=PART_ASSIGNMENTS[p["part_id"]][0]) for p in PARTS_MASTER],
    )

    write_csv(
        os.path.join(DATA_DIR, "material_master.csv"),
        ["part_id", "material_id_part_name", "yield_strength_mpa",
         "max_temp_limit_c", "elastomeric_rating", "drawing_spec_ref"],
        [dict(p, material_id_part_name=p["item_reference"]) for p in PARTS_MASTER],
    )

    write_csv(
        os.path.join(DATA_DIR, "historical_field_issues.csv"),
        ["part_id", "failure_mode", "potential_cause", "historical_severity",
         "historical_occurrence", "historical_detection", "recommended_action"],
        PARTS_MASTER,
    )

    # ---- normalized tables -------------------------------------------
    write_csv(
        os.path.join(DATA_DIR, "part_types.csv"),
        ["part_type_id", "part_type_name", "family_id", "family_name",
         "member_part_count"],
        [
            {
                "part_type_id": tid,
                "part_type_name": meta["name"],
                "family_id": meta["family"],
                "family_name": PART_FAMILIES[meta["family"]],
                "member_part_count": sum(
                    1 for v in PART_ASSIGNMENTS.values() if v[0] == tid),
            }
            for tid, meta in PART_TYPES.items()
        ],
    )

    write_csv(
        os.path.join(DATA_DIR, "failure_effects.csv"),
        ["effect_id", "effect_description", "system_level", "standard_severity"],
        [
            {
                "effect_id": eid,
                "effect_description": meta["description"],
                "system_level": meta["system_level"],
                "standard_severity": meta["standard_severity"],
            }
            for eid, meta in FAILURE_EFFECTS.items()
        ],
    )

    catalog = build_catalog()
    write_csv(
        os.path.join(DATA_DIR, "failure_mode_catalog.csv"),
        ["mode_id", "scope_id", "scope_level", "failure_mode", "potential_cause",
         "effect_id", "typical_control", "baseline_detection", "recommended_action",
         "origin", "origin_part_id", "origin_part_name"],
        catalog,
    )

    write_csv(
        os.path.join(DATA_DIR, "field_issues.csv"),
        ["issue_id", "part_id", "scope_id", "mode_id", "report_date",
         "units_in_service", "claim_count", "median_machine_hours",
         "detection_stage", "observed_effect_id", "observed_severity", "description"],
        build_field_issues(catalog, rng),
    )

    write_csv(
        os.path.join(DATA_DIR, "dfmea_worksheet.csv"),
        ["part_id", "mode_id", "severity", "occurrence", "detection",
         "current_design_control", "analyzed_by", "analysis_date", "revision"],
        build_worksheet(catalog, rng),
    )


if __name__ == "__main__":
    main()
