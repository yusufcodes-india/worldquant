import sqlite3
import logging
from app.db.connection import get_db

logger = logging.getLogger("alpha_pilot.migrations")

MIGRATIONS = [
    (
        "001_initial_schema",
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS campaigns (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            profile_name TEXT NOT NULL,
            profile_snapshot TEXT NOT NULL, -- JSON
            budget_simulations INTEGER NOT NULL DEFAULT 1500,
            submitted_simulations_count INTEGER NOT NULL DEFAULT 0,
            budget_gemini_calls INTEGER NOT NULL DEFAULT 150,
            gemini_calls_count INTEGER NOT NULL DEFAULT 0,
            budget_tokens INTEGER NOT NULL DEFAULT 500000,
            tokens_used_count INTEGER NOT NULL DEFAULT 0,
            simulation_concurrency INTEGER NOT NULL DEFAULT 1,
            stop_on_first_qualifying INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'created', -- created, running, paused, completed, cancelled
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS candidates (
            id TEXT PRIMARY KEY,
            campaign_id TEXT NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
            expression TEXT NOT NULL,
            normalized_hash TEXT NOT NULL,
            hypothesis TEXT,
            signal_family TEXT,
            parent_candidate_id TEXT,
            design_change TEXT,
            expected_risks TEXT,
            estimated_fields INTEGER DEFAULT 0,
            estimated_operators INTEGER DEFAULT 0,
            validation_status TEXT NOT NULL, -- passed, failed
            validation_errors TEXT, -- JSON array
            queue_status TEXT NOT NULL DEFAULT 'generated', 
            -- generated, validation_failed, ready, reserved, submitting, submission_uncertain, running, completed, failed, cancelled
            submission_id TEXT,
            retry_count INTEGER NOT NULL DEFAULT 0,
            retry_history TEXT, -- JSON array
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_candidates_campaign_id ON candidates(campaign_id);
        CREATE INDEX IF NOT EXISTS idx_candidates_queue_status ON candidates(queue_status);
        CREATE INDEX IF NOT EXISTS idx_candidates_normalized_hash ON candidates(normalized_hash);

        CREATE TABLE IF NOT EXISTS simulation_results (
            id TEXT PRIMARY KEY,
            candidate_id TEXT NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
            campaign_id TEXT NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
            is_mock INTEGER NOT NULL DEFAULT 1,
            platform_status TEXT NOT NULL,
            main_sharpe REAL,
            fitness REAL,
            turnover REAL,
            subuniverse_sharpe REAL,
            subuniverse_cutoff REAL,
            subuniverse_pass_margin REAL,
            weight_distribution_pass INTEGER,
            platform_reported_field_count INTEGER,
            platform_reported_op_count INTEGER,
            counts_verified INTEGER NOT NULL DEFAULT 0,
            raw_response TEXT, -- JSON
            pnl_series TEXT, -- JSON array of {date: str, pnl: float}
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_sim_results_candidate_id ON simulation_results(candidate_id);
        CREATE INDEX IF NOT EXISTS idx_sim_results_campaign_id ON simulation_results(campaign_id);

        CREATE TABLE IF NOT EXISTS correlation_records (
            id TEXT PRIMARY KEY,
            candidate_id TEXT NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
            check_type TEXT NOT NULL, -- self_correlation, production_correlation, pairwise_candidate
            status TEXT NOT NULL, -- NOT CHECKED, CHECK IN PROGRESS, LOCAL ESTIMATE ONLY, MANUALLY REPORTED, PLATFORM VERIFIED PASS, PLATFORM VERIFIED FAIL, STALE / RECHECK REQUIRED, CHECK UNAVAILABLE
            measured_value REAL,
            target_value REAL,
            official_threshold REAL,
            official_pass INTEGER, -- NULL, 0, 1
            comparison_alphas TEXT, -- JSON array
            is_local_estimate INTEGER NOT NULL DEFAULT 0,
            provenance_source TEXT NOT NULL, -- mock, platform_api, manual_import, local_pnl_calc
            notes TEXT,
            checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_corr_records_candidate_id ON correlation_records(candidate_id);

        CREATE TABLE IF NOT EXISTS reference_library (
            id TEXT PRIMARY KEY, -- Alpha ID (e.g. S1, S2 or custom)
            expression TEXT NOT NULL,
            signal_family TEXT,
            description TEXT,
            status TEXT NOT NULL DEFAULT 'USER_REPORTED', -- USER_REPORTED, PLATFORM_VERIFIED, SUBMITTED
            submitted_date TEXT,
            settings TEXT, -- JSON
            pnl_series TEXT, -- JSON array
            raw_metadata TEXT, -- JSON
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS app_config (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS quota_tracker (
            id TEXT PRIMARY KEY,
            provider TEXT NOT NULL, -- gemini, brain
            calls_count INTEGER NOT NULL DEFAULT 0,
            tokens_count INTEGER NOT NULL DEFAULT 0,
            last_reset_date TEXT NOT NULL,
            is_paused INTEGER NOT NULL DEFAULT 0,
            backoff_until TEXT
        );

        CREATE TABLE IF NOT EXISTS audit_log (
            id TEXT PRIMARY KEY,
            event_type TEXT NOT NULL,
            details TEXT NOT NULL, -- JSON
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
]

def run_migrations():
    """Runs database migrations idempotently."""
    with get_db() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY, applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);")
        cursor = conn.cursor()
        cursor.execute("SELECT version FROM schema_migrations")
        applied = {row[0] for row in cursor.fetchall()}
        
        for version, script in MIGRATIONS:
            if version not in applied:
                logger.info(f"Applying migration: {version}")
                cursor.executescript(script)
                cursor.execute("INSERT INTO schema_migrations (version) VALUES (?)", (version,))
                conn.commit()
