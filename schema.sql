-- ====================================================================
-- Mechnari.ai - BigQuery DDL for the DFMEA knowledge base
-- Dataset: mechnari_engineering
-- ====================================================================
--
-- Generated from data/*.csv so the declared types match what the
-- engines actually receive. The previous hand-written version had
-- drifted: it declared two tables under names no CSV used, and was
-- missing six others.
--
-- bq_load.py does not read this file - it derives the same schema from
-- the CSV at load time, so a regenerated dataset cannot disagree with
-- the data. This is here to be read, and for anyone standing the
-- dataset up by hand.
--
-- Dates are STRING deliberately: pandas hands them to the engines as
-- strings and field_issues() does its own parsing, so typing them as
-- DATE here would change what the engines receive.

-- Two-level part taxonomy: every part belongs to a TYPE, every type to a FAMILY.
--   17 rows in the current generated dataset
CREATE TABLE IF NOT EXISTS `mechnari_engineering.part_types` (
    part_type_id                       STRING,
    part_type_name                     STRING,
    family_id                          STRING,
    family_name                        STRING,
    member_part_count                  INT64
);

-- One standard severity per effect, organization-wide. The single source of Severity.
--   16 rows in the current generated dataset
CREATE TABLE IF NOT EXISTS `mechnari_engineering.failure_effects` (
    effect_id                          STRING,
    effect_description                 STRING,
    system_level                       STRING,
    standard_severity                  INT64
);

-- The active bill of materials: parts on the current program.
--   50 rows in the current generated dataset
CREATE TABLE IF NOT EXISTS `mechnari_engineering.bom_package_hierarchy` (
    part_id                            STRING,
    system_package                     STRING,
    item_reference                     STRING,
    elementary_function                STRING,
    material_type                      STRING,
    part_type_id                       STRING
);

-- Material and drawing specification per part.
--   50 rows in the current generated dataset
CREATE TABLE IF NOT EXISTS `mechnari_engineering.material_master` (
    part_id                            STRING,
    material_id_part_name              STRING,
    yield_strength_mpa                 INT64,
    max_temp_limit_c                   INT64,
    elastomeric_rating                 STRING,
    drawing_spec_ref                   STRING
);

-- Failure modes keyed by TYPE or FAMILY scope, with the effect each causes.
--   71 rows in the current generated dataset
CREATE TABLE IF NOT EXISTS `mechnari_engineering.failure_mode_catalog` (
    mode_id                            STRING,
    scope_id                           STRING,
    scope_level                        STRING,
    failure_mode                       STRING,
    potential_cause                    STRING,
    effect_id                          STRING,
    typical_control                    STRING,
    baseline_detection                 INT64,
    recommended_action                 STRING,
    origin                             STRING,
    origin_part_id                     STRING,
    origin_part_name                   STRING
);

-- Warranty / 8D records. Many rows per part - this is the evidence base.
--   227 rows in the current generated dataset
CREATE TABLE IF NOT EXISTS `mechnari_engineering.field_issues` (
    issue_id                           STRING,
    part_id                            STRING,
    scope_id                           STRING,
    mode_id                            STRING,
    report_date                        STRING,
    units_in_service                   INT64,
    claim_count                        INT64,
    median_machine_hours               INT64,
    detection_stage                    STRING,
    observed_effect_id                 STRING,
    observed_severity                  INT64,
    description                        STRING
);

-- The DFMEA on file today: which modes each part has actually analysed, with S/O/D.
--   172 rows in the current generated dataset
CREATE TABLE IF NOT EXISTS `mechnari_engineering.dfmea_worksheet` (
    part_id                            STRING,
    mode_id                            STRING,
    severity                           INT64,
    occurrence                         INT64,
    detection                          INT64,
    current_design_control             STRING,
    analyzed_by                        STRING,
    analysis_date                      STRING,
    revision                           STRING
);
