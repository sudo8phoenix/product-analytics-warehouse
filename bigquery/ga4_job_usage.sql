-- Run in the US region to retrieve observed BigQuery usage for the
-- GA4 profile, view deployment, and validation jobs. Sandbox usage is
-- quota consumption, not evidence of a monetary charge.

SELECT job_id, creation_time, state, error_result,
  total_bytes_processed, total_bytes_billed, total_slot_ms,
  TIMESTAMP_DIFF(end_time, start_time, MILLISECOND) AS elapsed_ms
FROM `gen-lang-client-0195528254.region-us.INFORMATION_SCHEMA.JOBS_BY_PROJECT`
WHERE job_id IN (
  'job_kLCgQGEvStNRkP8xawo-oJZF9CDy',
  'job_M8IUMOjc_tV-0TLub-TuBXSxJrfu',
  'job_B3-NOzb7OlWnrl7_CbpTNElFUfaE',
  'job_pf_cnsrX7BKV2GoS1dWTJwXR1c2I',
  'job_BZx3M1hZTCz4ri3R8XWt4jDwnhGF',
  'job_NPRe_0YyrYCB3lMiiMZuvLbebjvt'
)
ORDER BY creation_time;
