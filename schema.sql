-- ====================================================================
-- Mechnari.ai - BigQuery DDL & Reference Data Schema
-- Dataset: mechnari_engineering
-- ====================================================================

-- 1. Materials Master Table
-- Stores mechanical, thermal, and fatigue property thresholds for engineering alloys.
CREATE TABLE IF NOT EXISTS `mechnari_engineering.materials_master` (
    material_id STRING OPTIONS(description="Unique Identifier for the material alloy"),
    material_name STRING OPTIONS(description="Standard Material Designation (e.g. Al 6061-T6)"),
    category STRING OPTIONS(description="Material Category (Aluminum, Steel, Titanium, Polymer)"),
    yield_strength_mpa FLOAT64 OPTIONS(description="Yield Strength in MPa (0.2% offset)"),
    ultimate_tensile_strength_mpa FLOAT64 OPTIONS(description="Ultimate Tensile Strength in MPa"),
    density_g_cm3 FLOAT64 OPTIONS(description="Density in g/cm3"),
    thermal_limit_celsius FLOAT64 OPTIONS(description="Maximum Operating Temperature limit in Celsius"),
    fatigue_limit_mpa FLOAT64 OPTIONS(description="Endurance Limit / Fatigue Strength in MPa"),
    poissons_ratio FLOAT64 OPTIONS(description="Poisson's Ratio"),
    elastic_modulus_gpa FLOAT64 OPTIONS(description="Young's Modulus in GPa"),
    cost_index STRING OPTIONS(description="Relative Cost Tier (Low, Medium, High, Ultra-High)"),
    created_at TIMESTAMP OPTIONS(description="Record Creation Timestamp")
);

-- 2. Failure Modes Catalog Table
-- Stores standard DFMEA failure mechanisms, S/O/D baselines, and standardized ECO mitigations.
CREATE TABLE IF NOT EXISTS `mechnari_engineering.failure_modes_catalog` (
    failure_id STRING OPTIONS(description="Unique Failure Mode Code (e.g. FM-001)"),
    component_category STRING OPTIONS(description="Subsystem/Component Type (e.g., Fasteners, Shafts, Weldments, Seals)"),
    failure_mode STRING OPTIONS(description="Observable Failure Mode (e.g., Fatigue Cracking, Thermal Degradation)"),
    potential_cause STRING OPTIONS(description="Root Physical Mechanism"),
    default_severity INT64 OPTIONS(description="Default Severity score (1-10)"),
    default_occurrence INT64 OPTIONS(description="Default Occurrence score (1-10)"),
    default_detection INT64 OPTIONS(description="Default Detection score (1-10)"),
    recommended_eco_action STRING OPTIONS(description="Automated Engineering Change Order mitigation guidance"),
    target_material_id STRING OPTIONS(description="Suggested alternative material ID from materials_master"),
    updated_at TIMESTAMP OPTIONS(description="Last Revision Timestamp")
);

-- ====================================================================
-- Sample Seed Data Insertion
-- ====================================================================

-- Populate Materials Master
INSERT INTO `mechnari_engineering.materials_master` (
    material_id, material_name, category, yield_strength_mpa, ultimate_tensile_strength_mpa,
    density_g_cm3, thermal_limit_celsius, fatigue_limit_mpa, poissons_ratio, elastic_modulus_gpa, cost_index, created_at
) VALUES 
('MAT-AL6061', 'Aluminium 6061-T6', 'Aluminum Alloy', 276.0, 310.0, 2.70, 150.0, 96.0, 0.33, 68.9, 'Low', CURRENT_TIMESTAMP()),
('MAT-AL7075', 'Aluminium 7075-T6', 'Aluminum Alloy', 503.0, 572.0, 2.81, 120.0, 159.0, 0.33, 71.7, 'Medium', CURRENT_TIMESTAMP()),
('MAT-ST4140', 'AISI 4140 Alloy Steel', 'Steel Alloy', 655.0, 850.0, 7.85, 400.0, 370.0, 0.29, 205.0, 'Medium', CURRENT_TIMESTAMP()),
('MAT-SS316', 'Stainless Steel 316L', 'Stainless Steel', 290.0, 580.0, 8.00, 800.0, 240.0, 0.30, 193.0, 'Medium-High', CURRENT_TIMESTAMP()),
('MAT-TI64', 'Titanium Ti-6Al-4V (Grade 5)', 'Titanium Alloy', 880.0, 950.0, 4.43, 400.0, 510.0, 0.34, 113.8, 'High', CURRENT_TIMESTAMP()),
('MAT-PEEK', 'PEEK (Polyether Ether Ketone)', 'Polymer', 100.0, 100.0, 1.32, 250.0, 60.0, 0.40, 3.6, 'High', CURRENT_TIMESTAMP());

-- Populate Failure Modes Catalog
INSERT INTO `mechnari_engineering.failure_modes_catalog` (
    failure_id, component_category, failure_mode, potential_cause, default_severity, default_occurrence, default_detection, recommended_eco_action, target_material_id, updated_at
) VALUES 
('FM-101', 'Shafts & Axles', 'Fatigue Fracture under Rotary Bending', 'Cyclic bending moment exceeding fatigue limit at fillet shoulder radius.', 8, 6, 7, 'Increase shoulder fillet radius from R0.5 to R2.5mm to minimize stress concentration K_t. Upgrade material from AL6061 to AISI 4140 Steel or Ti-6Al-4V.', 'MAT-ST4140', CURRENT_TIMESTAMP()),
('FM-102', 'Bolted Joints', 'Thread Stripping & Preload Loss', 'Insufficient thread engagement length and vibration-induced self-loosening.', 9, 5, 6, 'ECO: Increase thread engagement length to 1.5x bolt diameter. Apply Helicoil inserts for aluminum parent material and specify Loctite 243 threadlocker.', 'MAT-ST4140', CURRENT_TIMESTAMP()),
('FM-103', 'Enclosures & Brackets', 'Excessive Deflection under Load', 'Flexural rigidity (E * I) insufficient for operational dynamic load.', 6, 7, 4, 'ECO: Add stiffening ribs (width = 0.5t) along principal stress axis. Change material to 7075-T6 to boost Elastic Modulus and Yield Strength.', 'MAT-AL7075', CURRENT_TIMESTAMP()),
('FM-104', 'High-Temp Housings', 'Thermal Softening and Creep Failure', 'Operating temperature exceeds glass transition / thermal stability threshold.', 9, 4, 8, 'ECO: Upgrade housing material to Stainless Steel 316L or PEEK polymer. Incorporate active cooling fins and thermal barrier ceramic coating.', 'MAT-SS316', CURRENT_TIMESTAMP()),
('FM-105', 'Hydraulic Seals', 'Extrusion & Fluid Leakage', 'Excessive clearance gap under peak system pressure spikes.', 8, 5, 5, 'ECO: Add PTFE back-up rings to O-ring groove design. Tighten tolerance class on bore housing from H9 to H7.', 'MAT-PEEK', CURRENT_TIMESTAMP());
