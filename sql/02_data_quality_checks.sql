-- =====================================================
-- DATA QUALITY ASSESSMENT
-- Run after CSV import to validate data integrity
-- =====================================================

-- 1. COMPLETENESS CHECK (Null/Missing Critical Fields)
SELECT
  'patients' AS table_name,
  COUNT(*) AS total_rows,
  SUM(CASE WHEN "Id" IS NULL THEN 1 ELSE 0 END) AS missing_id,
  SUM(CASE WHEN "BIRTHDATE" IS NULL THEN 1 ELSE 0 END) AS missing_birthdate
FROM raw.patients

UNION ALL

SELECT
  'mart.medications' AS table_name,
  COUNT(*) AS total_rows,
  SUM(CASE WHEN patient_id IS NULL THEN 1 ELSE 0 END) AS missing_pid,
  SUM(CASE WHEN total_cost IS NULL THEN 1 ELSE 0 END) AS missing_cost
FROM mart.medications;


-- 2. INTEGRITY CHECK (Orphan Records)
-- Records in child tables that don't have a parent in the patients table
SELECT 'Orphan encounters (no patient match)' AS issue,
       COUNT(*) AS issue_count
FROM raw.encounters e
LEFT JOIN raw.patients p ON e."PATIENT" = p."Id"
WHERE p."Id" IS NULL

UNION ALL

SELECT 'Orphan medications (no patient match)' AS issue,
       COUNT(*) AS issue_count
FROM mart.medications m
LEFT JOIN raw.patients p ON m.patient_id = p."Id"
WHERE p."Id" IS NULL;


-- 3. VALIDITY CHECK (Logical Consistency)
-- Birthdates cannot be in the future
SELECT 'Future birthdates' AS issue,
       COUNT(*) AS issue_count
FROM raw.patients
WHERE "BIRTHDATE"::date > CURRENT_DATE;

-- Costs should not be negative
SELECT 'Negative medication costs' AS issue,
       COUNT(*) AS issue_count
FROM mart.medications
WHERE total_cost < 0;


-- 4. UNIQUENESS & CONSISTENCY CHECK (New Addition)
-- Check for Duplicate Primary Keys in Patients (Should be 0)
SELECT 'Duplicate Patient IDs' as issue, 
       count(*) as issue_count
FROM (
    SELECT "Id" FROM raw.patients GROUP BY "Id" HAVING COUNT(*) > 1
) sub;

-- Check for Exact Duplicate Rows in Medications (Should be 0)
SELECT 'Duplicate Medication Entries' as issue,
       count(*) as issue_count
FROM (
    SELECT patient_id, start_ts, medication_code, count(*)
    FROM mart.medications
    GROUP BY 1, 2, 3
    HAVING count(*) > 1
) sub;


-- =====================================================
-- DATA PROFILE SUMMARY
-- Quick stats for the analyst
-- =====================================================
SELECT 
  ROUND(100.0 * COUNT(*) FILTER (WHERE "DEATHDATE" IS NOT NULL) / COUNT(*), 2) AS deceased_pct,
  ROUND(AVG(EXTRACT(YEAR FROM AGE(COALESCE("DEATHDATE"::date, CURRENT_DATE), "BIRTHDATE"::date)))::numeric, 1) AS avg_age_years,
  MIN("BIRTHDATE"::date) AS oldest_birthdate,
  MAX("BIRTHDATE"::date) AS youngest_birthdate
FROM raw.patients;