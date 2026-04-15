use std::path::PathBuf;

use anyhow::{Context, Result};
use rusqlite::{params, Connection, OptionalExtension};
use serde_json::Value;

use crate::error::{ensure_parent_dir, invalid_state};
use crate::models::{
    DigestHighlightRead, GeneratedReviewNoteRead, PaperAttachmentRead, PaperDetailRead,
    PaperListItemRead, PaperNoteSummaryRead, PaperWorkspaceRead, PendingMutationRead,
    ProgressEventRead, RemoteSyncEvent, RemoteSyncMutationResult, ReviewCommentItemRead,
    ReviewRoundDetailRead, ReviewRoundSummaryRead, SignalSnapshotRead, SubscriptionPolicyRead,
    SyncStatusRead, TodayOverviewRead, UserConnectionRead, WorkspaceStatusRead,
};
use crate::notes::{note_status_for_path, read_note_file_stats};
use crate::progress::derive_progress_percentage;
use crate::workspace::{
    attachment_status_for_path, default_workspace_root_record, paper_workspace_ready_for_path,
    workspace_root_rebind_path, workspace_root_row_id, WorkspaceRootRecord,
    WORKSPACE_LAYOUT_VERSION,
};

const DEFAULT_PAPER_LIMIT: usize = 50;
const MAX_PAPER_LIMIT: usize = 200;
#[derive(Debug, Clone)]
pub struct LocalCache {
    path: PathBuf,
}

#[derive(Debug, Clone)]
pub struct SyncStateRecord {
    pub base_url: Option<String>,
    pub device_id: Option<String>,
    pub device_display_name: Option<String>,
    pub connected: bool,
    pub user_id: Option<String>,
    pub user_name: Option<String>,
    pub user_email: Option<String>,
    pub user_field: Option<String>,
    pub last_synced_at: Option<String>,
    pub last_event_sequence: i64,
    pub last_error: Option<String>,
}

#[derive(Debug, Clone, Default)]
pub struct OutboxStats {
    pub pending_count: i64,
    pub failed_count: i64,
    pub recent_errors: Vec<String>,
}

#[derive(Debug, Clone, Default)]
pub struct PushOutcomeSummary {
    pub pushed_count: i64,
    pub applied_count: i64,
    pub duplicate_count: i64,
    pub failed_count: i64,
}

#[derive(Debug, Clone)]
pub struct DuplicateAttachmentRecord {
    pub attachment_id: String,
    pub sha256: Option<String>,
    pub size_bytes: Option<i64>,
    pub original_file_name: String,
}

impl Default for SyncStateRecord {
    fn default() -> Self {
        Self {
            base_url: None,
            device_id: None,
            device_display_name: None,
            connected: false,
            user_id: None,
            user_name: None,
            user_email: None,
            user_field: None,
            last_synced_at: None,
            last_event_sequence: 0,
            last_error: None,
        }
    }
}

impl LocalCache {
    pub fn new(path: PathBuf) -> Self {
        Self { path }
    }

    pub fn initialize(&self) -> Result<()> {
        ensure_parent_dir(&self.path)?;
        let connection = self.open()?;
        connection
            .execute_batch(
                r#"
                PRAGMA foreign_keys = ON;

                CREATE TABLE IF NOT EXISTS sync_state (
                    singleton_id INTEGER PRIMARY KEY CHECK (singleton_id = 1),
                    base_url TEXT,
                    device_id TEXT,
                    device_display_name TEXT,
                    connected INTEGER NOT NULL DEFAULT 0,
                    user_id TEXT,
                    user_name TEXT,
                    user_email TEXT,
                    user_field TEXT,
                    last_synced_at TEXT,
                    last_event_sequence INTEGER NOT NULL DEFAULT 0,
                    last_error TEXT
                );
                INSERT OR IGNORE INTO sync_state (
                    singleton_id,
                    connected,
                    last_event_sequence
                ) VALUES (1, 0, 0);

                CREATE TABLE IF NOT EXISTS paper_cache (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    paper_type TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    venue TEXT,
                    priority INTEGER NOT NULL DEFAULT 0,
                    next_action TEXT,
                    blocker TEXT,
                    last_touch_at TEXT,
                    updated_at TEXT,
                    identifiers_json TEXT NOT NULL DEFAULT '{}',
                    source_links_json TEXT NOT NULL DEFAULT '[]'
                );

                CREATE TABLE IF NOT EXISTS progress_event_cache (
                    id TEXT PRIMARY KEY,
                    paper_id TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    happened_at TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    owner TEXT,
                    evidence_links_json TEXT NOT NULL DEFAULT '[]'
                );
                CREATE INDEX IF NOT EXISTS idx_progress_event_cache_paper
                    ON progress_event_cache (paper_id, happened_at DESC, id ASC);

                CREATE TABLE IF NOT EXISTS signal_snapshot_cache (
                    id TEXT PRIMARY KEY,
                    paper_id TEXT NOT NULL,
                    source TEXT NOT NULL,
                    citation_count INTEGER,
                    download_count INTEGER,
                    read_count INTEGER,
                    inclusion_status TEXT,
                    fetched_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_signal_snapshot_cache_paper
                    ON signal_snapshot_cache (paper_id, fetched_at DESC, id ASC);

                CREATE TABLE IF NOT EXISTS subscription_policy_cache (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    frequency TEXT NOT NULL,
                    quiet_hours_json TEXT,
                    frequency_cap INTEGER NOT NULL DEFAULT 0,
                    policy_json TEXT NOT NULL DEFAULT '{}',
                    updated_at TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_subscription_policy_cache_user
                    ON subscription_policy_cache (user_id, channel, COALESCE(updated_at, '') DESC, id ASC);

                CREATE TABLE IF NOT EXISTS digest_issue_cache (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    issue_date TEXT NOT NULL,
                    status TEXT NOT NULL,
                    title TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    highlight_count INTEGER NOT NULL DEFAULT 0,
                    selected_card_count INTEGER NOT NULL DEFAULT 0,
                    deep_link_path TEXT,
                    highlights_json TEXT NOT NULL DEFAULT '[]',
                    items_json TEXT NOT NULL DEFAULT '[]',
                    updated_at TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_digest_issue_cache_user_date
                    ON digest_issue_cache (user_id, issue_date DESC, COALESCE(updated_at, '') DESC, id ASC);

                CREATE TABLE IF NOT EXISTS sync_event_cache (
                    sequence INTEGER PRIMARY KEY,
                    event_id TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    occurred_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_sync_event_cache_entity
                    ON sync_event_cache (entity_type, entity_id);

                CREATE TABLE IF NOT EXISTS mutation_outbox (
                    id TEXT PRIMARY KEY,
                    client_mutation_id TEXT NOT NULL UNIQUE,
                    mutation_type TEXT NOT NULL,
                    resource_type TEXT NOT NULL,
                    resource_id TEXT,
                    payload_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    attempt_count INTEGER NOT NULL DEFAULT 0,
                    last_error TEXT,
                    resulting_event_sequence INTEGER,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_attempted_at TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_mutation_outbox_status
                    ON mutation_outbox (status, created_at ASC, id ASC);
                CREATE INDEX IF NOT EXISTS idx_mutation_outbox_resource
                    ON mutation_outbox (resource_type, resource_id, created_at ASC, id ASC);

                CREATE TABLE IF NOT EXISTS workspace_settings (
                    id TEXT PRIMARY KEY,
                    root_path TEXT,
                    status TEXT NOT NULL DEFAULT 'unconfigured',
                    layout_version INTEGER NOT NULL DEFAULT 1,
                    last_validated_at TEXT,
                    last_error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS paper_workspace_cache (
                    paper_id TEXT PRIMARY KEY,
                    paper_title TEXT NOT NULL,
                    workspace_rel_path TEXT NOT NULL,
                    workspace_abs_path TEXT,
                    workspace_ready INTEGER NOT NULL DEFAULT 0,
                    attachment_count INTEGER NOT NULL DEFAULT 0,
                    last_imported_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS paper_attachment_cache (
                    id TEXT PRIMARY KEY,
                    paper_id TEXT NOT NULL,
                    attachment_kind TEXT NOT NULL,
                    storage_mode TEXT NOT NULL,
                    original_file_name TEXT NOT NULL,
                    stored_file_name TEXT NOT NULL,
                    file_extension TEXT,
                    relative_path TEXT NOT NULL,
                    absolute_path TEXT,
                    source_path TEXT NOT NULL,
                    size_bytes INTEGER,
                    mime_type TEXT,
                    sha256 TEXT,
                    status TEXT NOT NULL,
                    imported_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_opened_at TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_paper_attachment_cache_paper
                    ON paper_attachment_cache (paper_id, imported_at DESC, id ASC);
                CREATE INDEX IF NOT EXISTS idx_paper_attachment_cache_sha
                    ON paper_attachment_cache (paper_id, sha256, size_bytes);

                CREATE TABLE IF NOT EXISTS paper_note_cache (
                    id TEXT PRIMARY KEY,
                    paper_id TEXT NOT NULL,
                    template_kind TEXT NOT NULL,
                    title TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    relative_path TEXT NOT NULL,
                    absolute_path TEXT,
                    content_format TEXT NOT NULL,
                    source_mode TEXT NOT NULL,
                    status TEXT NOT NULL,
                    size_bytes INTEGER,
                    sha256 TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_opened_at TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_paper_note_cache_paper
                    ON paper_note_cache (paper_id, COALESCE(updated_at, '') DESC, id ASC);

                CREATE TABLE IF NOT EXISTS paper_review_round_cache (
                    id TEXT PRIMARY KEY,
                    paper_id TEXT NOT NULL,
                    round_label TEXT NOT NULL,
                    venue TEXT,
                    decision_label TEXT,
                    status TEXT NOT NULL,
                    source_mode TEXT NOT NULL,
                    reviewer_count INTEGER NOT NULL DEFAULT 0,
                    generated_response_note_id TEXT,
                    generated_matrix_note_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_paper_review_round_cache_paper
                    ON paper_review_round_cache (paper_id, COALESCE(updated_at, '') DESC, id ASC);

                CREATE TABLE IF NOT EXISTS review_comment_item_cache (
                    id TEXT PRIMARY KEY,
                    review_round_id TEXT NOT NULL,
                    paper_id TEXT NOT NULL,
                    reviewer_label TEXT NOT NULL,
                    comment_code TEXT,
                    sort_order INTEGER NOT NULL,
                    comment_text TEXT NOT NULL,
                    category TEXT,
                    disposition TEXT NOT NULL,
                    response_summary TEXT,
                    action_note TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_review_comment_item_cache_round
                    ON review_comment_item_cache (review_round_id, reviewer_label, sort_order, created_at, id);
                CREATE INDEX IF NOT EXISTS idx_review_comment_item_cache_paper
                    ON review_comment_item_cache (paper_id, review_round_id, reviewer_label, sort_order, created_at, id);

                PRAGMA user_version = 5;
                "#,
            )
            .context("failed to initialize desktop cache schema")?;
        let default_workspace = default_workspace_root_record();
        connection.execute(
            r#"
            INSERT OR IGNORE INTO workspace_settings (
                id,
                root_path,
                status,
                layout_version,
                last_validated_at,
                last_error,
                created_at,
                updated_at
            ) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8)
            "#,
            params![
                default_workspace.id,
                default_workspace.root_path,
                default_workspace.status,
                default_workspace.layout_version,
                default_workspace.last_validated_at,
                default_workspace.last_error,
                default_workspace.created_at,
                default_workspace.updated_at
            ],
        )?;
        Ok(())
    }

    pub fn open(&self) -> Result<Connection> {
        Connection::open(&self.path)
            .with_context(|| format!("failed to open desktop cache {}", self.path.display()))
    }

    pub fn sync_status(&self, token_present: bool) -> Result<SyncStatusRead> {
        let state = self.sync_state_record()?;
        let connection = self.open()?;
        let stats = load_outbox_stats(&connection)?;
        Ok(build_sync_status(state, token_present, stats))
    }

    pub fn sync_state_record(&self) -> Result<SyncStateRecord> {
        let connection = self.open()?;
        let record = connection
            .query_row(
                r#"
                SELECT
                    base_url,
                    device_id,
                    device_display_name,
                    connected,
                    user_id,
                    user_name,
                    user_email,
                    user_field,
                    last_synced_at,
                    last_event_sequence,
                    last_error
                FROM sync_state
                WHERE singleton_id = 1
                "#,
                [],
                |row| {
                    Ok(SyncStateRecord {
                        base_url: row.get(0)?,
                        device_id: row.get(1)?,
                        device_display_name: row.get(2)?,
                        connected: row.get::<_, i64>(3)? == 1,
                        user_id: row.get(4)?,
                        user_name: row.get(5)?,
                        user_email: row.get(6)?,
                        user_field: row.get(7)?,
                        last_synced_at: row.get(8)?,
                        last_event_sequence: row.get(9)?,
                        last_error: row.get(10)?,
                    })
                },
            )
            .optional()?;
        Ok(record.unwrap_or_default())
    }

    pub fn workspace_root_record(&self) -> Result<WorkspaceRootRecord> {
        let connection = self.open()?;
        let record = connection
            .query_row(
                r#"
                SELECT
                    id,
                    root_path,
                    status,
                    layout_version,
                    last_validated_at,
                    last_error,
                    created_at,
                    updated_at
                FROM workspace_settings
                WHERE id = ?1
                "#,
                params![workspace_root_row_id()],
                |row| {
                    Ok(WorkspaceRootRecord {
                        id: row.get(0)?,
                        root_path: row.get(1)?,
                        status: row.get(2)?,
                        layout_version: row.get(3)?,
                        last_validated_at: row.get(4)?,
                        last_error: row.get(5)?,
                        created_at: row.get(6)?,
                        updated_at: row.get(7)?,
                    })
                },
            )
            .optional()?;
        Ok(record.unwrap_or_else(default_workspace_root_record))
    }

    pub fn upsert_workspace_root_record(
        &self,
        root_path: Option<&str>,
        status: &str,
        last_validated_at: &str,
        last_error: Option<&str>,
    ) -> Result<()> {
        let current = self.workspace_root_record()?;
        let connection = self.open()?;
        let now = timestamp_now();
        connection.execute(
            r#"
            INSERT INTO workspace_settings (
                id,
                root_path,
                status,
                layout_version,
                last_validated_at,
                last_error,
                created_at,
                updated_at
            ) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8)
            ON CONFLICT(id) DO UPDATE SET
                root_path = excluded.root_path,
                status = excluded.status,
                layout_version = excluded.layout_version,
                last_validated_at = excluded.last_validated_at,
                last_error = excluded.last_error,
                updated_at = excluded.updated_at
            "#,
            params![
                workspace_root_row_id(),
                root_path,
                status,
                WORKSPACE_LAYOUT_VERSION,
                last_validated_at,
                last_error,
                current.created_at,
                now
            ],
        )?;
        Ok(())
    }

    pub fn workspace_status(&self) -> Result<WorkspaceStatusRead> {
        let connection = self.open()?;
        let root = self.workspace_root_record()?;
        let managed_attachment_count =
            connection.query_row("SELECT COUNT(*) FROM paper_attachment_cache", [], |row| {
                row.get(0)
            })?;
        Ok(WorkspaceStatusRead {
            root_path: root.root_path,
            status: root.status,
            layout_version: root.layout_version,
            last_validated_at: root.last_validated_at,
            last_error: root.last_error,
            managed_attachment_count,
        })
    }

    pub fn rebind_workspace_root(&self, root_path: Option<&str>) -> Result<()> {
        let mut connection = self.open()?;
        let transaction = connection.transaction()?;
        let now = timestamp_now();

        {
            let mut statement = transaction.prepare(
                r#"
                SELECT paper_id, workspace_rel_path
                FROM paper_workspace_cache
                ORDER BY paper_id ASC
                "#,
            )?;
            let rows = statement.query_map([], |row| {
                Ok((row.get::<_, String>(0)?, row.get::<_, String>(1)?))
            })?;
            for row in rows {
                let (paper_id, rel_path) = row?;
                let abs_path = workspace_root_rebind_path(root_path, &rel_path);
                let ready = paper_workspace_ready_for_path(abs_path.as_deref());
                transaction.execute(
                    r#"
                    UPDATE paper_workspace_cache
                    SET
                        workspace_abs_path = ?1,
                        workspace_ready = ?2,
                        updated_at = ?3
                    WHERE paper_id = ?4
                    "#,
                    params![abs_path, if ready { 1 } else { 0 }, now, paper_id],
                )?;
            }
        }

        {
            let mut statement = transaction.prepare(
                r#"
                SELECT id, relative_path
                FROM paper_attachment_cache
                ORDER BY id ASC
                "#,
            )?;
            let rows = statement.query_map([], |row| {
                Ok((row.get::<_, String>(0)?, row.get::<_, String>(1)?))
            })?;
            for row in rows {
                let (attachment_id, rel_path) = row?;
                let abs_path = workspace_root_rebind_path(root_path, &rel_path);
                let status = if root_path.is_some() {
                    attachment_status_for_path(abs_path.as_deref())
                } else {
                    "ready".to_string()
                };
                transaction.execute(
                    r#"
                    UPDATE paper_attachment_cache
                    SET
                        absolute_path = ?1,
                        status = ?2,
                        updated_at = ?3
                    WHERE id = ?4
                    "#,
                    params![abs_path, status, now, attachment_id],
                )?;
            }
        }

        {
            let mut statement = transaction.prepare(
                r#"
                SELECT id, relative_path
                FROM paper_note_cache
                ORDER BY id ASC
                "#,
            )?;
            let rows = statement.query_map([], |row| {
                Ok((row.get::<_, String>(0)?, row.get::<_, String>(1)?))
            })?;
            for row in rows {
                let (note_id, rel_path) = row?;
                let abs_path = workspace_root_rebind_path(root_path, &rel_path);
                let status = note_status_for_path(abs_path.as_deref());
                transaction.execute(
                    r#"
                    UPDATE paper_note_cache
                    SET
                        absolute_path = ?1,
                        status = ?2,
                        updated_at = ?3
                    WHERE id = ?4
                    "#,
                    params![abs_path, status, now, note_id],
                )?;
            }
        }

        transaction.commit()?;
        self.refresh_paper_workspace_counts()
    }

    pub fn upsert_connection(
        &self,
        base_url: &str,
        device_id: &str,
        device_display_name: &str,
        user_id: &str,
        user_name: &str,
        user_email: Option<&str>,
        user_field: Option<&str>,
    ) -> Result<()> {
        let connection = self.open()?;
        connection.execute(
            r#"
            UPDATE sync_state
            SET
                base_url = ?1,
                device_id = ?2,
                device_display_name = ?3,
                connected = 1,
                user_id = ?4,
                user_name = ?5,
                user_email = ?6,
                user_field = ?7,
                last_error = NULL
            WHERE singleton_id = 1
            "#,
            params![
                base_url,
                device_id,
                device_display_name,
                user_id,
                user_name,
                user_email,
                user_field
            ],
        )?;
        Ok(())
    }

    pub fn mark_sync_error(&self, message: &str) -> Result<()> {
        let connection = self.open()?;
        connection.execute(
            "UPDATE sync_state SET last_error = ?1 WHERE singleton_id = 1",
            params![message],
        )?;
        Ok(())
    }

    pub fn clear_sync_error(&self) -> Result<()> {
        let connection = self.open()?;
        connection.execute(
            "UPDATE sync_state SET last_error = NULL WHERE singleton_id = 1",
            [],
        )?;
        Ok(())
    }

    pub fn update_after_ack(
        &self,
        last_event_sequence: i64,
        last_synced_at: Option<&str>,
    ) -> Result<()> {
        let connection = self.open()?;
        connection.execute(
            r#"
            UPDATE sync_state
            SET
                last_event_sequence = ?1,
                last_synced_at = ?2,
                last_error = NULL
            WHERE singleton_id = 1
            "#,
            params![last_event_sequence, last_synced_at],
        )?;
        Ok(())
    }

    pub fn reset_local_cache(&self) -> Result<()> {
        let connection = self.open()?;
        connection.execute("DELETE FROM paper_cache", [])?;
        connection.execute("DELETE FROM progress_event_cache", [])?;
        connection.execute("DELETE FROM signal_snapshot_cache", [])?;
        connection.execute("DELETE FROM subscription_policy_cache", [])?;
        connection.execute("DELETE FROM digest_issue_cache", [])?;
        connection.execute("DELETE FROM sync_event_cache", [])?;
        connection.execute("DELETE FROM mutation_outbox", [])?;
        connection.execute(
            r#"
            UPDATE sync_state
            SET
                last_synced_at = NULL,
                last_event_sequence = 0,
                last_error = NULL
            WHERE singleton_id = 1
            "#,
            [],
        )?;
        Ok(())
    }

    pub fn disconnect(&self) -> Result<()> {
        self.reset_local_cache()?;
        let connection = self.open()?;
        connection.execute(
            r#"
            UPDATE sync_state
            SET
                base_url = NULL,
                device_id = NULL,
                device_display_name = NULL,
                connected = 0,
                user_id = NULL,
                user_name = NULL,
                user_email = NULL,
                user_field = NULL,
                last_error = NULL
            WHERE singleton_id = 1
            "#,
            [],
        )?;
        Ok(())
    }

    pub fn recover_inflight_mutations(&self) -> Result<()> {
        let connection = self.open()?;
        connection.execute(
            r#"
            UPDATE mutation_outbox
            SET
                status = 'queued',
                updated_at = ?1
            WHERE status = 'sending'
            "#,
            params![timestamp_now()],
        )?;
        Ok(())
    }

    pub fn enqueue_mutation(
        &self,
        id: &str,
        client_mutation_id: &str,
        mutation_type: &str,
        resource_type: &str,
        resource_id: Option<&str>,
        payload: &Value,
    ) -> Result<PendingMutationRead> {
        let connection = self.open()?;
        let now = timestamp_now();
        connection.execute(
            r#"
            INSERT INTO mutation_outbox (
                id,
                client_mutation_id,
                mutation_type,
                resource_type,
                resource_id,
                payload_json,
                status,
                attempt_count,
                created_at,
                updated_at
            ) VALUES (?1, ?2, ?3, ?4, ?5, ?6, 'queued', 0, ?7, ?7)
            "#,
            params![
                id,
                client_mutation_id,
                mutation_type,
                resource_type,
                resource_id,
                serde_json::to_string(payload)?,
                now,
            ],
        )?;
        self.get_mutation(client_mutation_id)
    }

    pub fn get_mutation(&self, client_mutation_id: &str) -> Result<PendingMutationRead> {
        let connection = self.open()?;
        query_mutation(
            &connection,
            "WHERE client_mutation_id = ?1",
            params![client_mutation_id],
        )?
        .ok_or_else(|| invalid_state(format!("mutation {client_mutation_id} was not found")))
    }

    pub fn list_pending_mutations(&self) -> Result<Vec<PendingMutationRead>> {
        let connection = self.open()?;
        let mut statement = connection.prepare(
            r#"
            SELECT
                id,
                client_mutation_id,
                mutation_type,
                resource_type,
                resource_id,
                payload_json,
                status,
                attempt_count,
                last_error,
                resulting_event_sequence,
                created_at,
                updated_at,
                last_attempted_at
            FROM mutation_outbox
            WHERE status IN ('queued', 'sending', 'failed')
            ORDER BY created_at ASC, id ASC
            "#,
        )?;
        let rows = statement.query_map([], map_mutation_row)?;
        collect_rows(rows)
    }

    pub fn pending_outbox_batch(&self) -> Result<Vec<PendingMutationRead>> {
        let connection = self.open()?;
        let mut statement = connection.prepare(
            r#"
            SELECT
                id,
                client_mutation_id,
                mutation_type,
                resource_type,
                resource_id,
                payload_json,
                status,
                attempt_count,
                last_error,
                resulting_event_sequence,
                created_at,
                updated_at,
                last_attempted_at
            FROM mutation_outbox
            WHERE status IN ('queued', 'failed')
            ORDER BY created_at ASC, id ASC
            "#,
        )?;
        let rows = statement.query_map([], map_mutation_row)?;
        collect_rows(rows)
    }

    pub fn mark_mutations_sending(&self, client_mutation_ids: &[String]) -> Result<()> {
        if client_mutation_ids.is_empty() {
            return Ok(());
        }

        let mut connection = self.open()?;
        let transaction = connection.transaction()?;
        let now = timestamp_now();
        for client_mutation_id in client_mutation_ids {
            transaction.execute(
                r#"
                UPDATE mutation_outbox
                SET
                    status = 'sending',
                    attempt_count = attempt_count + 1,
                    last_attempted_at = ?1,
                    updated_at = ?1
                WHERE client_mutation_id = ?2
                "#,
                params![now, client_mutation_id],
            )?;
        }
        transaction.commit()?;
        Ok(())
    }

    pub fn apply_push_results(
        &self,
        results: &[RemoteSyncMutationResult],
    ) -> Result<PushOutcomeSummary> {
        let mut summary = PushOutcomeSummary {
            pushed_count: results.len() as i64,
            ..PushOutcomeSummary::default()
        };
        if results.is_empty() {
            return Ok(summary);
        }

        let mut connection = self.open()?;
        let transaction = connection.transaction()?;
        let now = timestamp_now();
        for result in results {
            transaction.execute(
                r#"
                UPDATE mutation_outbox
                SET
                    status = ?1,
                    last_error = ?2,
                    resulting_event_sequence = ?3,
                    updated_at = ?4
                WHERE client_mutation_id = ?5
                "#,
                params![
                    result.status,
                    result.error_message,
                    result.resulting_event_sequence,
                    now,
                    result.client_mutation_id,
                ],
            )?;

            match result.status.as_str() {
                "applied" => summary.applied_count += 1,
                "duplicate" => summary.duplicate_count += 1,
                "failed" => summary.failed_count += 1,
                _ => {}
            }
        }
        transaction.commit()?;
        Ok(summary)
    }

    pub fn outbox_stats(&self) -> Result<OutboxStats> {
        let connection = self.open()?;
        load_outbox_stats(&connection)
    }

    pub fn upsert_paper_workspace(
        &self,
        paper_id: &str,
        paper_title: &str,
        workspace_rel_path: &str,
        workspace_abs_path: Option<&str>,
        workspace_ready: bool,
        last_imported_at: Option<&str>,
    ) -> Result<()> {
        let connection = self.open()?;
        let now = timestamp_now();
        connection.execute(
            r#"
            INSERT INTO paper_workspace_cache (
                paper_id,
                paper_title,
                workspace_rel_path,
                workspace_abs_path,
                workspace_ready,
                attachment_count,
                last_imported_at,
                created_at,
                updated_at
            ) VALUES (?1, ?2, ?3, ?4, ?5, 0, ?6, ?7, ?7)
            ON CONFLICT(paper_id) DO UPDATE SET
                paper_title = excluded.paper_title,
                workspace_rel_path = excluded.workspace_rel_path,
                workspace_abs_path = excluded.workspace_abs_path,
                workspace_ready = excluded.workspace_ready,
                last_imported_at = COALESCE(excluded.last_imported_at, paper_workspace_cache.last_imported_at),
                updated_at = excluded.updated_at
            "#,
            params![
                paper_id,
                paper_title,
                workspace_rel_path,
                workspace_abs_path,
                if workspace_ready { 1 } else { 0 },
                last_imported_at,
                now
            ],
        )?;
        self.refresh_paper_workspace_counts()
    }

    pub fn touch_paper_workspace_imported_at(
        &self,
        paper_id: &str,
        last_imported_at: &str,
    ) -> Result<()> {
        let connection = self.open()?;
        connection.execute(
            r#"
            UPDATE paper_workspace_cache
            SET
                last_imported_at = ?1,
                updated_at = ?1
            WHERE paper_id = ?2
            "#,
            params![last_imported_at, paper_id],
        )?;
        Ok(())
    }

    pub fn get_paper_workspace(&self, paper_id: &str) -> Result<PaperWorkspaceRead> {
        let connection = self.open()?;
        let row = connection
            .query_row(
                r#"
                SELECT
                    paper_id,
                    paper_title,
                    workspace_rel_path,
                    workspace_abs_path,
                    workspace_ready,
                    attachment_count,
                    last_imported_at
                FROM paper_workspace_cache
                WHERE paper_id = ?1
                "#,
                params![paper_id],
                |row| {
                    Ok(PaperWorkspaceRead {
                        paper_id: row.get(0)?,
                        paper_title: row.get(1)?,
                        workspace_rel_path: row.get(2)?,
                        workspace_abs_path: row.get(3)?,
                        workspace_ready: row.get::<_, i64>(4)? == 1,
                        attachment_count: row.get(5)?,
                        last_imported_at: row.get(6)?,
                    })
                },
            )
            .optional()?;

        if let Some(workspace) = row {
            return Ok(workspace);
        }

        let paper = connection
            .query_row(
                "SELECT title FROM paper_cache WHERE id = ?1",
                params![paper_id],
                |row| row.get::<_, String>(0),
            )
            .optional()?
            .ok_or_else(|| invalid_state(format!("paper {paper_id} is not cached")))?;
        let root = self.workspace_root_record()?;
        let rel_path = format!("papers/{paper_id}");
        Ok(PaperWorkspaceRead {
            paper_id: paper_id.to_string(),
            paper_title: paper,
            workspace_rel_path: rel_path.clone(),
            workspace_abs_path: workspace_root_rebind_path(root.root_path.as_deref(), &rel_path),
            workspace_ready: false,
            attachment_count: 0,
            last_imported_at: None,
        })
    }

    pub fn upsert_attachment(
        &self,
        id: &str,
        paper_id: &str,
        attachment_kind: &str,
        storage_mode: &str,
        original_file_name: &str,
        stored_file_name: &str,
        file_extension: Option<&str>,
        relative_path: &str,
        absolute_path: Option<&str>,
        source_path: &str,
        size_bytes: Option<i64>,
        mime_type: Option<&str>,
        sha256: Option<&str>,
        status: &str,
        imported_at: &str,
        last_opened_at: Option<&str>,
    ) -> Result<()> {
        let connection = self.open()?;
        connection.execute(
            r#"
            INSERT INTO paper_attachment_cache (
                id,
                paper_id,
                attachment_kind,
                storage_mode,
                original_file_name,
                stored_file_name,
                file_extension,
                relative_path,
                absolute_path,
                source_path,
                size_bytes,
                mime_type,
                sha256,
                status,
                imported_at,
                updated_at,
                last_opened_at
            ) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, ?14, ?15, ?15, ?16)
            ON CONFLICT(id) DO UPDATE SET
                attachment_kind = excluded.attachment_kind,
                storage_mode = excluded.storage_mode,
                original_file_name = excluded.original_file_name,
                stored_file_name = excluded.stored_file_name,
                file_extension = excluded.file_extension,
                relative_path = excluded.relative_path,
                absolute_path = excluded.absolute_path,
                source_path = excluded.source_path,
                size_bytes = excluded.size_bytes,
                mime_type = excluded.mime_type,
                sha256 = excluded.sha256,
                status = excluded.status,
                updated_at = excluded.updated_at,
                last_opened_at = excluded.last_opened_at
            "#,
            params![
                id,
                paper_id,
                attachment_kind,
                storage_mode,
                original_file_name,
                stored_file_name,
                file_extension,
                relative_path,
                absolute_path,
                source_path,
                size_bytes,
                mime_type,
                sha256,
                status,
                imported_at,
                last_opened_at
            ],
        )?;
        self.refresh_paper_workspace_counts()
    }

    pub fn get_attachment_by_id(&self, attachment_id: &str) -> Result<PaperAttachmentRead> {
        let connection = self.open()?;
        connection
            .query_row(
                r#"
                SELECT
                    id,
                    paper_id,
                    attachment_kind,
                    storage_mode,
                    original_file_name,
                    stored_file_name,
                    file_extension,
                    relative_path,
                    absolute_path,
                    source_path,
                    size_bytes,
                    mime_type,
                    sha256,
                    status,
                    imported_at,
                    updated_at,
                    last_opened_at
                FROM paper_attachment_cache
                WHERE id = ?1
                "#,
                params![attachment_id],
                map_attachment_row,
            )
            .optional()?
            .ok_or_else(|| invalid_state(format!("attachment {attachment_id} is not indexed")))
    }

    pub fn list_paper_attachments(&self, paper_id: &str) -> Result<Vec<PaperAttachmentRead>> {
        let connection = self.open()?;
        let mut statement = connection.prepare(
            r#"
            SELECT
                id,
                paper_id,
                attachment_kind,
                storage_mode,
                original_file_name,
                stored_file_name,
                file_extension,
                relative_path,
                absolute_path,
                source_path,
                size_bytes,
                mime_type,
                sha256,
                status,
                imported_at,
                updated_at,
                last_opened_at
            FROM paper_attachment_cache
            WHERE paper_id = ?1
            ORDER BY imported_at DESC, id ASC
            "#,
        )?;
        let rows = statement.query_map(params![paper_id], map_attachment_row)?;
        collect_rows(rows)
    }

    pub fn upsert_paper_note(
        &self,
        id: &str,
        paper_id: &str,
        template_kind: &str,
        title: &str,
        file_name: &str,
        relative_path: &str,
        absolute_path: Option<&str>,
        content_format: &str,
        source_mode: &str,
        status: &str,
        size_bytes: Option<i64>,
        sha256: Option<&str>,
        created_at: &str,
        updated_at: &str,
        last_opened_at: Option<&str>,
    ) -> Result<()> {
        let connection = self.open()?;
        connection.execute(
            r#"
            INSERT INTO paper_note_cache (
                id,
                paper_id,
                template_kind,
                title,
                file_name,
                relative_path,
                absolute_path,
                content_format,
                source_mode,
                status,
                size_bytes,
                sha256,
                created_at,
                updated_at,
                last_opened_at
            ) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, ?14, ?15)
            ON CONFLICT(id) DO UPDATE SET
                template_kind = excluded.template_kind,
                title = excluded.title,
                file_name = excluded.file_name,
                relative_path = excluded.relative_path,
                absolute_path = excluded.absolute_path,
                content_format = excluded.content_format,
                source_mode = excluded.source_mode,
                status = excluded.status,
                size_bytes = excluded.size_bytes,
                sha256 = excluded.sha256,
                updated_at = excluded.updated_at,
                last_opened_at = excluded.last_opened_at
            "#,
            params![
                id,
                paper_id,
                template_kind,
                title,
                file_name,
                relative_path,
                absolute_path,
                content_format,
                source_mode,
                status,
                size_bytes,
                sha256,
                created_at,
                updated_at,
                last_opened_at,
            ],
        )?;
        Ok(())
    }

    pub fn get_paper_note_summary(&self, note_id: &str) -> Result<PaperNoteSummaryRead> {
        let connection = self.open()?;
        connection
            .query_row(
                r#"
                SELECT
                    id,
                    paper_id,
                    template_kind,
                    title,
                    file_name,
                    relative_path,
                    absolute_path,
                    content_format,
                    source_mode,
                    status,
                    size_bytes,
                    sha256,
                    created_at,
                    updated_at,
                    last_opened_at
                FROM paper_note_cache
                WHERE id = ?1
                "#,
                params![note_id],
                map_note_row,
            )
            .optional()?
            .ok_or_else(|| invalid_state(format!("note {note_id} is not indexed")))
    }

    pub fn list_paper_notes(&self, paper_id: &str) -> Result<Vec<PaperNoteSummaryRead>> {
        let connection = self.open()?;
        let mut statement = connection.prepare(
            r#"
            SELECT
                id,
                paper_id,
                template_kind,
                title,
                file_name,
                relative_path,
                absolute_path,
                content_format,
                source_mode,
                status,
                size_bytes,
                sha256,
                created_at,
                updated_at,
                last_opened_at
            FROM paper_note_cache
            WHERE paper_id = ?1
            ORDER BY updated_at DESC, created_at DESC, id ASC
            "#,
        )?;
        let rows = statement.query_map(params![paper_id], map_note_row)?;
        collect_rows(rows)
    }

    pub fn upsert_review_round(
        &self,
        id: &str,
        paper_id: &str,
        round_label: &str,
        venue: Option<&str>,
        decision_label: Option<&str>,
        status: &str,
        source_mode: &str,
        reviewer_count: i64,
        generated_response_note_id: Option<&str>,
        generated_matrix_note_id: Option<&str>,
        created_at: &str,
        updated_at: &str,
    ) -> Result<ReviewRoundSummaryRead> {
        let connection = self.open()?;
        connection.execute(
            r#"
            INSERT INTO paper_review_round_cache (
                id,
                paper_id,
                round_label,
                venue,
                decision_label,
                status,
                source_mode,
                reviewer_count,
                generated_response_note_id,
                generated_matrix_note_id,
                created_at,
                updated_at
            ) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12)
            ON CONFLICT(id) DO UPDATE SET
                paper_id = excluded.paper_id,
                round_label = excluded.round_label,
                venue = excluded.venue,
                decision_label = excluded.decision_label,
                status = excluded.status,
                source_mode = excluded.source_mode,
                reviewer_count = excluded.reviewer_count,
                generated_response_note_id = excluded.generated_response_note_id,
                generated_matrix_note_id = excluded.generated_matrix_note_id,
                updated_at = excluded.updated_at
            "#,
            params![
                id,
                paper_id,
                round_label,
                venue,
                decision_label,
                status,
                source_mode,
                reviewer_count,
                generated_response_note_id,
                generated_matrix_note_id,
                created_at,
                updated_at
            ],
        )?;
        self.get_review_round_summary(id)
    }

    pub fn get_review_round_summary(
        &self,
        review_round_id: &str,
    ) -> Result<ReviewRoundSummaryRead> {
        let connection = self.open()?;
        connection
            .query_row(
                r#"
                SELECT
                    id,
                    paper_id,
                    round_label,
                    venue,
                    decision_label,
                    status,
                    source_mode,
                    reviewer_count,
                    generated_response_note_id,
                    generated_matrix_note_id,
                    created_at,
                    updated_at
                FROM paper_review_round_cache
                WHERE id = ?1
                "#,
                params![review_round_id],
                map_review_round_row,
            )
            .optional()?
            .ok_or_else(|| invalid_state(format!("review round {review_round_id} is not indexed")))
    }

    pub fn list_review_rounds(&self, paper_id: &str) -> Result<Vec<ReviewRoundSummaryRead>> {
        let connection = self.open()?;
        let mut statement = connection.prepare(
            r#"
            SELECT
                id,
                paper_id,
                round_label,
                venue,
                decision_label,
                status,
                source_mode,
                reviewer_count,
                generated_response_note_id,
                generated_matrix_note_id,
                created_at,
                updated_at
            FROM paper_review_round_cache
            WHERE paper_id = ?1
            ORDER BY
                CASE status WHEN 'open' THEN 0 ELSE 1 END,
                COALESCE(updated_at, '') DESC,
                COALESCE(created_at, '') DESC,
                id ASC
            "#,
        )?;
        let rows = statement.query_map(params![paper_id], map_review_round_row)?;
        collect_rows(rows)
    }

    pub fn next_review_comment_sort_order(&self, review_round_id: &str) -> Result<i64> {
        let connection = self.open()?;
        let max_sort_order: Option<i64> = connection.query_row(
            r#"
            SELECT MAX(sort_order)
            FROM review_comment_item_cache
            WHERE review_round_id = ?1
            "#,
            params![review_round_id],
            |row| row.get(0),
        )?;
        Ok(max_sort_order.unwrap_or(0) + 1)
    }

    pub fn upsert_review_comment(
        &self,
        id: &str,
        review_round_id: &str,
        paper_id: &str,
        reviewer_label: &str,
        comment_code: Option<&str>,
        sort_order: i64,
        comment_text: &str,
        category: Option<&str>,
        disposition: &str,
        response_summary: Option<&str>,
        action_note: Option<&str>,
        created_at: &str,
        updated_at: &str,
    ) -> Result<ReviewCommentItemRead> {
        let connection = self.open()?;
        connection.execute(
            r#"
            INSERT INTO review_comment_item_cache (
                id,
                review_round_id,
                paper_id,
                reviewer_label,
                comment_code,
                sort_order,
                comment_text,
                category,
                disposition,
                response_summary,
                action_note,
                created_at,
                updated_at
            ) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13)
            ON CONFLICT(id) DO UPDATE SET
                review_round_id = excluded.review_round_id,
                paper_id = excluded.paper_id,
                reviewer_label = excluded.reviewer_label,
                comment_code = excluded.comment_code,
                sort_order = excluded.sort_order,
                comment_text = excluded.comment_text,
                category = excluded.category,
                disposition = excluded.disposition,
                response_summary = excluded.response_summary,
                action_note = excluded.action_note,
                updated_at = excluded.updated_at
            "#,
            params![
                id,
                review_round_id,
                paper_id,
                reviewer_label,
                comment_code,
                sort_order,
                comment_text,
                category,
                disposition,
                response_summary,
                action_note,
                created_at,
                updated_at
            ],
        )?;
        self.refresh_review_round_reviewer_count(review_round_id)?;
        self.get_review_comment(id)
    }

    pub fn get_review_comment(&self, comment_id: &str) -> Result<ReviewCommentItemRead> {
        let connection = self.open()?;
        connection
            .query_row(
                r#"
                SELECT
                    id,
                    review_round_id,
                    paper_id,
                    reviewer_label,
                    comment_code,
                    sort_order,
                    comment_text,
                    category,
                    disposition,
                    response_summary,
                    action_note,
                    created_at,
                    updated_at
                FROM review_comment_item_cache
                WHERE id = ?1
                "#,
                params![comment_id],
                map_review_comment_row,
            )
            .optional()?
            .ok_or_else(|| invalid_state(format!("review comment {comment_id} is not indexed")))
    }

    pub fn list_review_comments(
        &self,
        review_round_id: &str,
    ) -> Result<Vec<ReviewCommentItemRead>> {
        let connection = self.open()?;
        let mut statement = connection.prepare(
            r#"
            SELECT
                id,
                review_round_id,
                paper_id,
                reviewer_label,
                comment_code,
                sort_order,
                comment_text,
                category,
                disposition,
                response_summary,
                action_note,
                created_at,
                updated_at
            FROM review_comment_item_cache
            WHERE review_round_id = ?1
            ORDER BY reviewer_label COLLATE NOCASE ASC, sort_order ASC, created_at ASC, id ASC
            "#,
        )?;
        let rows = statement.query_map(params![review_round_id], map_review_comment_row)?;
        collect_rows(rows)
    }

    pub fn delete_review_comment(&self, comment_id: &str) -> Result<()> {
        let existing = self.get_review_comment(comment_id)?;
        let connection = self.open()?;
        connection.execute(
            "DELETE FROM review_comment_item_cache WHERE id = ?1",
            params![comment_id],
        )?;
        self.refresh_review_round_reviewer_count(&existing.review_round_id)
    }

    pub fn get_review_round_detail(&self, review_round_id: &str) -> Result<ReviewRoundDetailRead> {
        let round = self.get_review_round_summary(review_round_id)?;
        let comments = self.list_review_comments(review_round_id)?;
        let generated_response_note = self.generated_review_note(
            round.generated_response_note_id.as_deref(),
            "response_letter",
        )?;
        let generated_matrix_note = self
            .generated_review_note(round.generated_matrix_note_id.as_deref(), "reviewer_matrix")?;
        Ok(ReviewRoundDetailRead {
            round,
            comments,
            generated_response_note,
            generated_matrix_note,
        })
    }

    pub fn generated_review_note(
        &self,
        note_id: Option<&str>,
        kind: &str,
    ) -> Result<Option<GeneratedReviewNoteRead>> {
        let Some(note_id) = note_id else {
            return Ok(None);
        };
        let note = self.get_paper_note_summary(note_id)?;
        Ok(Some(GeneratedReviewNoteRead {
            kind: kind.to_string(),
            note_id: note.id,
            title: note.title,
            relative_path: note.relative_path,
            status: note.status,
            updated_at: note.updated_at,
        }))
    }

    pub fn refresh_review_round_reviewer_count(&self, review_round_id: &str) -> Result<()> {
        let connection = self.open()?;
        let reviewer_count: i64 = connection.query_row(
            r#"
            SELECT COUNT(DISTINCT reviewer_label)
            FROM review_comment_item_cache
            WHERE review_round_id = ?1
            "#,
            params![review_round_id],
            |row| row.get(0),
        )?;
        connection.execute(
            r#"
            UPDATE paper_review_round_cache
            SET
                reviewer_count = ?1,
                updated_at = ?2
            WHERE id = ?3
            "#,
            params![reviewer_count, timestamp_now(), review_round_id],
        )?;
        Ok(())
    }

    pub fn touch_paper_note_opened_at(
        &self,
        note_id: &str,
        last_opened_at: &str,
    ) -> Result<PaperNoteSummaryRead> {
        let connection = self.open()?;
        connection.execute(
            r#"
            UPDATE paper_note_cache
            SET
                last_opened_at = ?1,
                updated_at = COALESCE(updated_at, ?1)
            WHERE id = ?2
            "#,
            params![last_opened_at, note_id],
        )?;
        self.get_paper_note_summary(note_id)
    }

    pub fn refresh_note_statuses(&self, root_path: Option<&str>, paper_id: &str) -> Result<()> {
        let mut connection = self.open()?;
        let transaction = connection.transaction()?;
        let now = timestamp_now();
        {
            let mut statement = transaction.prepare(
                r#"
                SELECT id, relative_path
                FROM paper_note_cache
                WHERE paper_id = ?1
                ORDER BY id ASC
                "#,
            )?;
            let rows = statement.query_map(params![paper_id], |row| {
                Ok((row.get::<_, String>(0)?, row.get::<_, String>(1)?))
            })?;
            for row in rows {
                let (note_id, rel_path) = row?;
                let absolute_path = workspace_root_rebind_path(root_path, &rel_path);
                let status = note_status_for_path(absolute_path.as_deref());
                let (size_bytes, sha256) = if status == "ready" {
                    if let Some(path) = absolute_path.as_deref() {
                        let stats = read_note_file_stats(std::path::Path::new(path))?;
                        (stats.size_bytes, stats.sha256)
                    } else {
                        (None, None)
                    }
                } else {
                    (None, None)
                };
                transaction.execute(
                    r#"
                    UPDATE paper_note_cache
                    SET
                        absolute_path = ?1,
                        status = ?2,
                        size_bytes = ?3,
                        sha256 = ?4,
                        updated_at = ?5
                    WHERE id = ?6
                    "#,
                    params![absolute_path, status, size_bytes, sha256, now, note_id],
                )?;
            }
        }
        transaction.commit()?;
        Ok(())
    }

    pub fn find_duplicate_attachment(
        &self,
        paper_id: &str,
        sha256: Option<&str>,
        size_bytes: Option<i64>,
    ) -> Result<Option<DuplicateAttachmentRecord>> {
        let connection = self.open()?;
        if let Some(sha256) = sha256 {
            let row = connection
                .query_row(
                    r#"
                    SELECT id, sha256, size_bytes, original_file_name
                    FROM paper_attachment_cache
                    WHERE paper_id = ?1
                      AND sha256 = ?2
                    ORDER BY imported_at DESC, id ASC
                    LIMIT 1
                    "#,
                    params![paper_id, sha256],
                    |row| {
                        Ok(DuplicateAttachmentRecord {
                            attachment_id: row.get(0)?,
                            sha256: row.get(1)?,
                            size_bytes: row.get(2)?,
                            original_file_name: row.get(3)?,
                        })
                    },
                )
                .optional()?;
            if row.is_some() {
                return Ok(row);
            }
        }

        if let Some(size_bytes) = size_bytes {
            return connection
                .query_row(
                    r#"
                    SELECT id, sha256, size_bytes, original_file_name
                    FROM paper_attachment_cache
                    WHERE paper_id = ?1
                      AND size_bytes = ?2
                    ORDER BY imported_at DESC, id ASC
                    LIMIT 1
                    "#,
                    params![paper_id, size_bytes],
                    |row| {
                        Ok(DuplicateAttachmentRecord {
                            attachment_id: row.get(0)?,
                            sha256: row.get(1)?,
                            size_bytes: row.get(2)?,
                            original_file_name: row.get(3)?,
                        })
                    },
                )
                .optional()
                .map_err(Into::into);
        }

        Ok(None)
    }

    pub fn refresh_attachment_statuses(
        &self,
        root_path: Option<&str>,
        paper_id: &str,
    ) -> Result<()> {
        let mut connection = self.open()?;
        let transaction = connection.transaction()?;
        let now = timestamp_now();
        {
            let mut statement = transaction.prepare(
                r#"
                SELECT id, relative_path
                FROM paper_attachment_cache
                WHERE paper_id = ?1
                ORDER BY id ASC
                "#,
            )?;
            let rows = statement.query_map(params![paper_id], |row| {
                Ok((row.get::<_, String>(0)?, row.get::<_, String>(1)?))
            })?;
            for row in rows {
                let (attachment_id, rel_path) = row?;
                let absolute_path = workspace_root_rebind_path(root_path, &rel_path);
                let status = if root_path.is_some() {
                    attachment_status_for_path(absolute_path.as_deref())
                } else {
                    "ready".to_string()
                };
                transaction.execute(
                    r#"
                    UPDATE paper_attachment_cache
                    SET
                        absolute_path = ?1,
                        status = ?2,
                        updated_at = ?3
                    WHERE id = ?4
                    "#,
                    params![absolute_path, status, now, attachment_id],
                )?;
            }
        }
        transaction.commit()?;
        self.refresh_paper_workspace_counts()
    }

    pub fn refresh_paper_workspace_counts(&self) -> Result<()> {
        let connection = self.open()?;
        connection.execute(
            r#"
            UPDATE paper_workspace_cache
            SET attachment_count = (
                SELECT COUNT(*)
                FROM paper_attachment_cache
                WHERE paper_attachment_cache.paper_id = paper_workspace_cache.paper_id
            )
            "#,
            [],
        )?;
        Ok(())
    }

    pub fn list_subscription_policies(&self) -> Result<Vec<SubscriptionPolicyRead>> {
        let connection = self.open()?;
        let user_id = current_user_id(&connection)?;
        let Some(user_id) = user_id else {
            return Ok(Vec::new());
        };

        let mut statement = connection.prepare(
            r#"
            SELECT
                id,
                user_id,
                channel,
                enabled,
                frequency,
                quiet_hours_json,
                frequency_cap,
                policy_json,
                updated_at
            FROM subscription_policy_cache
            WHERE user_id = ?1
            ORDER BY channel ASC, COALESCE(updated_at, '') DESC, id ASC
            "#,
        )?;
        let rows = statement.query_map(params![user_id], |row| {
            Ok((
                row.get::<_, String>(0)?,
                row.get::<_, String>(1)?,
                row.get::<_, String>(2)?,
                row.get::<_, i64>(3)? == 1,
                row.get::<_, String>(4)?,
                row.get::<_, Option<String>>(5)?,
                row.get::<_, i64>(6)?,
                row.get::<_, Option<String>>(7)?,
                row.get::<_, Option<String>>(8)?,
            ))
        })?;

        let mut policies = Vec::new();
        for row in rows {
            let row = row?;
            let outbox_state = subscription_policy_outbox_state(&connection, &row.0)?;
            policies.push(SubscriptionPolicyRead {
                id: row.0,
                user_id: row.1,
                channel: row.2,
                enabled: row.3,
                frequency: row.4,
                quiet_hours: parse_json_value(row.5),
                frequency_cap: row.6,
                policy: parse_json_value(row.7)
                    .unwrap_or_else(|| Value::Object(Default::default())),
                updated_at: row.8,
                pending_mutation_count: outbox_state.pending_count,
                last_mutation_error: outbox_state.last_error,
            });
        }
        Ok(policies)
    }

    pub fn apply_event_batch(&self, events: &[RemoteSyncEvent]) -> Result<()> {
        let mut connection = self.open()?;
        let transaction = connection.transaction()?;
        for event in events {
            apply_single_event(&transaction, event)?;
        }
        transaction.commit()?;
        Ok(())
    }

    pub fn read_today_overview(&self) -> Result<TodayOverviewRead> {
        let connection = self.open()?;
        let Some(user_id) = current_user_id(&connection)? else {
            return Ok(TodayOverviewRead {
                message: Some("Connect a desktop device to populate Today.".to_string()),
                ..TodayOverviewRead::default()
            });
        };

        let row = connection
            .query_row(
                r#"
                SELECT
                    id,
                    issue_date,
                    status,
                    title,
                    summary,
                    highlight_count,
                    selected_card_count,
                    deep_link_path,
                    highlights_json,
                    updated_at
                FROM digest_issue_cache
                WHERE user_id = ?1
                ORDER BY issue_date DESC, COALESCE(updated_at, '') DESC, id ASC
                LIMIT 1
                "#,
                params![user_id],
                |row| {
                    Ok((
                        row.get::<_, String>(0)?,
                        row.get::<_, String>(1)?,
                        row.get::<_, String>(2)?,
                        row.get::<_, String>(3)?,
                        row.get::<_, String>(4)?,
                        row.get::<_, i64>(5)?,
                        row.get::<_, i64>(6)?,
                        row.get::<_, Option<String>>(7)?,
                        row.get::<_, String>(8)?,
                        row.get::<_, Option<String>>(9)?,
                    ))
                },
            )
            .optional()?;
        let Some(row) = row else {
            return Ok(TodayOverviewRead {
                message: Some("No digest issue is cached yet.".to_string()),
                ..TodayOverviewRead::default()
            });
        };

        let highlights = self.materialize_digest_items(&row.8)?;
        Ok(TodayOverviewRead {
            state: "ready".to_string(),
            issue_id: Some(row.0),
            issue_date: Some(row.1),
            status: Some(row.2),
            title: Some(row.3),
            summary: Some(row.4),
            highlight_count: row.5,
            selected_card_count: row.6,
            deep_link_path: row.7,
            highlights,
            message: None,
            updated_at: row.9,
        })
    }

    pub fn list_papers(
        &self,
        paper_type: Option<&str>,
        stage: Option<&str>,
        limit: Option<usize>,
    ) -> Result<Vec<PaperListItemRead>> {
        let connection = self.open()?;
        let effective_limit = limit.unwrap_or(DEFAULT_PAPER_LIMIT).min(MAX_PAPER_LIMIT) as i64;
        let mut statement = connection.prepare(
            r#"
            SELECT
                id,
                user_id,
                title,
                paper_type,
                stage,
                venue,
                priority,
                next_action,
                blocker,
                last_touch_at,
                updated_at
            FROM paper_cache
            WHERE (?1 IS NULL OR paper_type = ?1)
              AND (?2 IS NULL OR stage = ?2)
            ORDER BY
                priority DESC,
                COALESCE(last_touch_at, '') DESC,
                COALESCE(updated_at, '') DESC,
                title ASC,
                id ASC
            LIMIT ?3
            "#,
        )?;
        let rows = statement.query_map(params![paper_type, stage, effective_limit], |row| {
            Ok((
                row.get::<_, String>(0)?,
                row.get::<_, String>(1)?,
                row.get::<_, String>(2)?,
                row.get::<_, String>(3)?,
                row.get::<_, String>(4)?,
                row.get::<_, Option<String>>(5)?,
                row.get::<_, i64>(6)?,
                row.get::<_, Option<String>>(7)?,
                row.get::<_, Option<String>>(8)?,
                row.get::<_, Option<String>>(9)?,
                row.get::<_, Option<String>>(10)?,
            ))
        })?;
        let mut papers = Vec::new();
        for row in rows {
            let row = row?;
            let outbox_state = paper_outbox_state(&connection, &row.0)?;
            let workspace = self.get_paper_workspace(&row.0)?;
            papers.push(PaperListItemRead {
                id: row.0,
                user_id: row.1,
                title: row.2,
                paper_type: row.3.clone(),
                stage: row.4,
                venue: row.5,
                priority: row.6,
                next_action: row.7,
                blocker: row.8,
                last_touch_at: row.9,
                progress_percentage: derive_progress_percentage(&row.3),
                updated_at: row.10,
                pending_mutation_count: outbox_state.pending_count,
                last_mutation_error: outbox_state.last_error,
                attachment_count: workspace.attachment_count,
                workspace_ready: workspace.workspace_ready,
            });
        }
        Ok(papers)
    }

    pub fn get_paper_detail(&self, paper_id: &str) -> Result<PaperDetailRead> {
        let connection = self.open()?;
        let paper = connection
            .query_row(
                r#"
                SELECT
                    id,
                    user_id,
                    title,
                    paper_type,
                    stage,
                    venue,
                    priority,
                    next_action,
                    blocker,
                    last_touch_at,
                    updated_at,
                    identifiers_json,
                    source_links_json
                FROM paper_cache
                WHERE id = ?1
                "#,
                params![paper_id],
                |row| {
                    Ok((
                        row.get::<_, String>(0)?,
                        row.get::<_, String>(1)?,
                        row.get::<_, String>(2)?,
                        row.get::<_, String>(3)?,
                        row.get::<_, String>(4)?,
                        row.get::<_, Option<String>>(5)?,
                        row.get::<_, i64>(6)?,
                        row.get::<_, Option<String>>(7)?,
                        row.get::<_, Option<String>>(8)?,
                        row.get::<_, Option<String>>(9)?,
                        row.get::<_, Option<String>>(10)?,
                        row.get::<_, String>(11)?,
                        row.get::<_, String>(12)?,
                    ))
                },
            )
            .optional()?
            .ok_or_else(|| invalid_state(format!("paper {paper_id} is not cached")))?;

        let progress_events = {
            let mut statement = connection.prepare(
                r#"
                SELECT id, paper_id, stage, happened_at, summary, owner
                FROM progress_event_cache
                WHERE paper_id = ?1
                ORDER BY happened_at DESC, id ASC
                LIMIT 10
                "#,
            )?;
            let rows = statement.query_map(params![paper_id], |row| {
                Ok(ProgressEventRead {
                    id: row.get(0)?,
                    paper_id: row.get(1)?,
                    stage: row.get(2)?,
                    happened_at: row.get(3)?,
                    summary: row.get(4)?,
                    owner: row.get(5)?,
                })
            })?;
            collect_rows(rows)?
        };

        let signal_snapshots = {
            let mut statement = connection.prepare(
                r#"
                SELECT
                    id,
                    paper_id,
                    source,
                    citation_count,
                    download_count,
                    read_count,
                    inclusion_status,
                    fetched_at
                FROM signal_snapshot_cache
                WHERE paper_id = ?1
                ORDER BY fetched_at DESC, id ASC
                LIMIT 10
                "#,
            )?;
            let rows = statement.query_map(params![paper_id], |row| {
                Ok(SignalSnapshotRead {
                    id: row.get(0)?,
                    paper_id: row.get(1)?,
                    source: row.get(2)?,
                    citation_count: row.get(3)?,
                    download_count: row.get(4)?,
                    read_count: row.get(5)?,
                    inclusion_status: row.get(6)?,
                    fetched_at: row.get(7)?,
                })
            })?;
            collect_rows(rows)?
        };

        let outbox_state = paper_outbox_state(&connection, paper_id)?;
        let workspace = self.get_paper_workspace(paper_id)?;
        let attachments = self.list_paper_attachments(paper_id)?;
        let notes = self.list_paper_notes(paper_id)?;
        let review_rounds = self.list_review_rounds(paper_id)?;
        Ok(PaperDetailRead {
            id: paper.0,
            user_id: paper.1,
            title: paper.2,
            paper_type: paper.3.clone(),
            stage: paper.4,
            venue: paper.5,
            priority: paper.6,
            next_action: paper.7,
            blocker: paper.8,
            last_touch_at: paper.9,
            progress_percentage: derive_progress_percentage(&paper.3),
            updated_at: paper.10,
            identifiers: parse_json_value(Some(paper.11))
                .unwrap_or_else(|| Value::Object(Default::default())),
            source_links: parse_json_array(Some(paper.12)),
            progress_events,
            signal_snapshots,
            pending_mutation_count: outbox_state.pending_count,
            last_mutation_error: outbox_state.last_error,
            workspace,
            attachments,
            note_count: notes.len() as i64,
            notes,
            review_round_count: review_rounds.len() as i64,
            review_rounds,
        })
    }

    fn materialize_digest_items(&self, raw_items: &str) -> Result<Vec<DigestHighlightRead>> {
        let items: Vec<Value> = serde_json::from_str(raw_items).unwrap_or_default();
        let mut materialized = Vec::new();
        for item in items {
            let source_paper_id = value_as_string(item.get("source_paper_id"));
            let paper = match source_paper_id.as_deref() {
                Some(paper_id) => self.paper_summary_by_id(paper_id)?,
                None => None,
            };
            materialized.push(DigestHighlightRead {
                sort_order: value_as_i64(item.get("sort_order")),
                pulse_card_id: value_as_string(item.get("pulse_card_id")).unwrap_or_default(),
                card_type: value_as_string(item.get("card_type")).unwrap_or_default(),
                source_paper_id,
                title: value_as_string(item.get("title")).unwrap_or_default(),
                summary: value_as_string(item.get("summary")).unwrap_or_default(),
                why_now: value_as_string(item.get("why_now")),
                paper,
            });
        }
        Ok(materialized)
    }

    fn paper_summary_by_id(&self, paper_id: &str) -> Result<Option<PaperListItemRead>> {
        let connection = self.open()?;
        let row = connection
            .query_row(
                r#"
                SELECT
                    id,
                    user_id,
                    title,
                    paper_type,
                    stage,
                    venue,
                    priority,
                    next_action,
                    blocker,
                    last_touch_at,
                    updated_at
                FROM paper_cache
                WHERE id = ?1
                "#,
                params![paper_id],
                |row| {
                    let id: String = row.get(0)?;
                    let paper_type: String = row.get(3)?;
                    Ok((
                        id,
                        row.get::<_, String>(1)?,
                        row.get::<_, String>(2)?,
                        paper_type,
                        row.get::<_, String>(4)?,
                        row.get::<_, Option<String>>(5)?,
                        row.get::<_, i64>(6)?,
                        row.get::<_, Option<String>>(7)?,
                        row.get::<_, Option<String>>(8)?,
                        row.get::<_, Option<String>>(9)?,
                        row.get::<_, Option<String>>(10)?,
                    ))
                },
            )
            .optional()?;
        match row {
            Some(row) => {
                let outbox_state = paper_outbox_state(&connection, &row.0)?;
                let workspace = self.get_paper_workspace(&row.0)?;
                Ok(Some(PaperListItemRead {
                    id: row.0,
                    user_id: row.1,
                    title: row.2,
                    paper_type: row.3.clone(),
                    stage: row.4,
                    venue: row.5,
                    priority: row.6,
                    next_action: row.7,
                    blocker: row.8,
                    last_touch_at: row.9,
                    progress_percentage: derive_progress_percentage(&row.3),
                    updated_at: row.10,
                    pending_mutation_count: outbox_state.pending_count,
                    last_mutation_error: outbox_state.last_error,
                    attachment_count: workspace.attachment_count,
                    workspace_ready: workspace.workspace_ready,
                }))
            }
            None => Ok(None),
        }
    }
}

fn apply_single_event(connection: &Connection, event: &RemoteSyncEvent) -> Result<()> {
    connection.execute(
        r#"
        INSERT INTO sync_event_cache (
            sequence,
            event_id,
            entity_type,
            entity_id,
            event_type,
            payload_json,
            occurred_at
        ) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7)
        ON CONFLICT(sequence) DO UPDATE SET
            event_id = excluded.event_id,
            entity_type = excluded.entity_type,
            entity_id = excluded.entity_id,
            event_type = excluded.event_type,
            payload_json = excluded.payload_json,
            occurred_at = excluded.occurred_at
        "#,
        params![
            event.sequence,
            event.id,
            event.entity_type,
            event.entity_id,
            event.event_type,
            serde_json::to_string(&event.payload)?,
            event.occurred_at
        ],
    )?;

    match event.entity_type.as_str() {
        "paper_profile" => upsert_paper(connection, &event.payload)?,
        "progress_event" => upsert_progress_event(connection, &event.payload)?,
        "signal_snapshot" => upsert_signal_snapshot(connection, &event.payload)?,
        "subscription_policy" => upsert_subscription_policy(connection, &event.payload)?,
        "pulse_digest_issue" => upsert_digest_issue(connection, &event.payload)?,
        _ => {}
    }
    Ok(())
}

fn upsert_paper(connection: &Connection, payload: &Value) -> Result<()> {
    let paper_id = required_string(payload, "id")?;
    let user_id = required_string(payload, "user_id")?;
    let title = required_string(payload, "title")?;
    let paper_type = required_string(payload, "type")?;
    let stage = required_string(payload, "stage")?;
    connection.execute(
        r#"
        INSERT INTO paper_cache (
            id,
            user_id,
            title,
            paper_type,
            stage,
            venue,
            priority,
            next_action,
            blocker,
            last_touch_at,
            updated_at,
            identifiers_json,
            source_links_json
        ) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13)
        ON CONFLICT(id) DO UPDATE SET
            user_id = excluded.user_id,
            title = excluded.title,
            paper_type = excluded.paper_type,
            stage = excluded.stage,
            venue = excluded.venue,
            priority = excluded.priority,
            next_action = excluded.next_action,
            blocker = excluded.blocker,
            last_touch_at = excluded.last_touch_at,
            updated_at = excluded.updated_at,
            identifiers_json = excluded.identifiers_json,
            source_links_json = excluded.source_links_json
        "#,
        params![
            paper_id,
            user_id,
            title,
            paper_type,
            stage,
            value_as_string(payload.get("venue")),
            payload.get("priority").and_then(Value::as_i64).unwrap_or(0),
            value_as_string(payload.get("next_action")),
            value_as_string(payload.get("blocker")),
            value_as_string(payload.get("last_touch_at")),
            value_as_string(payload.get("updated_at")),
            serde_json::to_string(
                payload
                    .get("identifiers")
                    .unwrap_or(&Value::Object(Default::default())),
            )?,
            serde_json::to_string(
                payload
                    .get("source_links")
                    .unwrap_or(&Value::Array(Vec::new())),
            )?,
        ],
    )?;
    connection.execute(
        r#"
        UPDATE paper_workspace_cache
        SET paper_title = ?1, updated_at = ?2
        WHERE paper_id = ?3
        "#,
        params![
            required_string(payload, "title")?,
            value_as_string(payload.get("updated_at")).unwrap_or_else(timestamp_now),
            required_string(payload, "id")?
        ],
    )?;
    Ok(())
}

fn upsert_progress_event(connection: &Connection, payload: &Value) -> Result<()> {
    connection.execute(
        r#"
        INSERT INTO progress_event_cache (
            id,
            paper_id,
            stage,
            happened_at,
            summary,
            owner,
            evidence_links_json
        ) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7)
        ON CONFLICT(id) DO UPDATE SET
            paper_id = excluded.paper_id,
            stage = excluded.stage,
            happened_at = excluded.happened_at,
            summary = excluded.summary,
            owner = excluded.owner,
            evidence_links_json = excluded.evidence_links_json
        "#,
        params![
            required_string(payload, "id")?,
            required_string(payload, "paper_id")?,
            required_string(payload, "stage")?,
            required_string(payload, "happened_at")?,
            required_string(payload, "summary")?,
            value_as_string(payload.get("owner")),
            serde_json::to_string(
                payload
                    .get("evidence_links")
                    .unwrap_or(&Value::Array(Vec::new())),
            )?,
        ],
    )?;
    Ok(())
}

fn upsert_signal_snapshot(connection: &Connection, payload: &Value) -> Result<()> {
    connection.execute(
        r#"
        INSERT INTO signal_snapshot_cache (
            id,
            paper_id,
            source,
            citation_count,
            download_count,
            read_count,
            inclusion_status,
            fetched_at
        ) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8)
        ON CONFLICT(id) DO UPDATE SET
            paper_id = excluded.paper_id,
            source = excluded.source,
            citation_count = excluded.citation_count,
            download_count = excluded.download_count,
            read_count = excluded.read_count,
            inclusion_status = excluded.inclusion_status,
            fetched_at = excluded.fetched_at
        "#,
        params![
            required_string(payload, "id")?,
            required_string(payload, "paper_id")?,
            required_string(payload, "source")?,
            payload.get("citation_count").and_then(Value::as_i64),
            payload.get("download_count").and_then(Value::as_i64),
            payload.get("read_count").and_then(Value::as_i64),
            value_as_string(payload.get("inclusion_status")),
            required_string(payload, "fetched_at")?,
        ],
    )?;
    Ok(())
}

fn upsert_subscription_policy(connection: &Connection, payload: &Value) -> Result<()> {
    connection.execute(
        r#"
        INSERT INTO subscription_policy_cache (
            id,
            user_id,
            channel,
            enabled,
            frequency,
            quiet_hours_json,
            frequency_cap,
            policy_json,
            updated_at
        ) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9)
        ON CONFLICT(id) DO UPDATE SET
            user_id = excluded.user_id,
            channel = excluded.channel,
            enabled = excluded.enabled,
            frequency = excluded.frequency,
            quiet_hours_json = excluded.quiet_hours_json,
            frequency_cap = excluded.frequency_cap,
            policy_json = excluded.policy_json,
            updated_at = excluded.updated_at
        "#,
        params![
            required_string(payload, "id")?,
            required_string(payload, "user_id")?,
            required_string(payload, "channel")?,
            if payload
                .get("enabled")
                .and_then(Value::as_bool)
                .unwrap_or(true)
            {
                1
            } else {
                0
            },
            required_string(payload, "frequency")?,
            maybe_json_string(payload.get("quiet_hours"))?,
            payload
                .get("frequency_cap")
                .and_then(Value::as_i64)
                .unwrap_or(0),
            serde_json::to_string(
                payload
                    .get("policy")
                    .unwrap_or(&Value::Object(Default::default())),
            )?,
            value_as_string(payload.get("updated_at")),
        ],
    )?;
    Ok(())
}

fn upsert_digest_issue(connection: &Connection, payload: &Value) -> Result<()> {
    connection.execute(
        r#"
        INSERT INTO digest_issue_cache (
            id,
            user_id,
            issue_date,
            status,
            title,
            summary,
            highlight_count,
            selected_card_count,
            deep_link_path,
            highlights_json,
            items_json,
            updated_at
        ) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12)
        ON CONFLICT(id) DO UPDATE SET
            user_id = excluded.user_id,
            issue_date = excluded.issue_date,
            status = excluded.status,
            title = excluded.title,
            summary = excluded.summary,
            highlight_count = excluded.highlight_count,
            selected_card_count = excluded.selected_card_count,
            deep_link_path = excluded.deep_link_path,
            highlights_json = excluded.highlights_json,
            items_json = excluded.items_json,
            updated_at = excluded.updated_at
        "#,
        params![
            required_string(payload, "id")?,
            required_string(payload, "user_id")?,
            required_string(payload, "issue_date")?,
            required_string(payload, "status")?,
            required_string(payload, "title")?,
            required_string(payload, "summary")?,
            payload
                .get("highlight_count")
                .and_then(Value::as_i64)
                .unwrap_or(0),
            payload
                .get("selected_card_count")
                .and_then(Value::as_i64)
                .unwrap_or(0),
            value_as_string(payload.get("deep_link_path")),
            serde_json::to_string(
                payload
                    .get("highlights")
                    .unwrap_or(&Value::Array(Vec::new())),
            )?,
            serde_json::to_string(payload.get("items").unwrap_or(&Value::Array(Vec::new())))?,
            value_as_string(payload.get("updated_at")),
        ],
    )?;
    Ok(())
}

fn paper_outbox_state(connection: &Connection, paper_id: &str) -> Result<ResourceOutboxState> {
    query_resource_outbox_state(connection, paper_id, &["paper_profile", "progress_event"])
}

fn subscription_policy_outbox_state(
    connection: &Connection,
    policy_id: &str,
) -> Result<ResourceOutboxState> {
    query_resource_outbox_state(connection, policy_id, &["subscription_policy"])
}

#[derive(Debug, Clone, Default)]
struct ResourceOutboxState {
    pending_count: i64,
    last_error: Option<String>,
}

fn query_resource_outbox_state(
    connection: &Connection,
    resource_id: &str,
    resource_types: &[&str],
) -> Result<ResourceOutboxState> {
    let pending_count = match resource_types {
        [single] => connection.query_row(
            r#"
            SELECT COUNT(*)
            FROM mutation_outbox
            WHERE resource_type = ?1
              AND resource_id = ?2
              AND status IN ('queued', 'sending')
            "#,
            params![single, resource_id],
            |row| row.get(0),
        )?,
        [first, second] => connection.query_row(
            r#"
            SELECT COUNT(*)
            FROM mutation_outbox
            WHERE resource_type IN (?1, ?2)
              AND resource_id = ?3
              AND status IN ('queued', 'sending')
            "#,
            params![first, second, resource_id],
            |row| row.get(0),
        )?,
        _ => 0,
    };

    let last_error = match resource_types {
        [single] => connection
            .query_row(
                r#"
                SELECT last_error
                FROM mutation_outbox
                WHERE resource_type = ?1
                  AND resource_id = ?2
                  AND status = 'failed'
                  AND last_error IS NOT NULL
                ORDER BY updated_at DESC, id DESC
                LIMIT 1
                "#,
                params![single, resource_id],
                |row| row.get(0),
            )
            .optional()?,
        [first, second] => connection
            .query_row(
                r#"
                SELECT last_error
                FROM mutation_outbox
                WHERE resource_type IN (?1, ?2)
                  AND resource_id = ?3
                  AND status = 'failed'
                  AND last_error IS NOT NULL
                ORDER BY updated_at DESC, id DESC
                LIMIT 1
                "#,
                params![first, second, resource_id],
                |row| row.get(0),
            )
            .optional()?,
        _ => None,
    };

    Ok(ResourceOutboxState {
        pending_count,
        last_error,
    })
}

fn load_outbox_stats(connection: &Connection) -> Result<OutboxStats> {
    let pending_count = connection.query_row(
        "SELECT COUNT(*) FROM mutation_outbox WHERE status IN ('queued', 'sending')",
        [],
        |row| row.get(0),
    )?;
    let failed_count = connection.query_row(
        "SELECT COUNT(*) FROM mutation_outbox WHERE status = 'failed'",
        [],
        |row| row.get(0),
    )?;

    let mut statement = connection.prepare(
        r#"
        SELECT last_error
        FROM mutation_outbox
        WHERE status = 'failed'
          AND last_error IS NOT NULL
        ORDER BY updated_at DESC, id DESC
        LIMIT 3
        "#,
    )?;
    let rows = statement.query_map([], |row| row.get::<_, String>(0))?;
    let recent_errors = collect_rows(rows)?;

    Ok(OutboxStats {
        pending_count,
        failed_count,
        recent_errors,
    })
}

fn current_user_id(connection: &Connection) -> Result<Option<String>> {
    Ok(connection
        .query_row(
            "SELECT user_id FROM sync_state WHERE singleton_id = 1",
            [],
            |row| row.get::<_, Option<String>>(0),
        )
        .optional()
        .map_err(anyhow::Error::from)?
        .flatten())
}

fn query_mutation<P>(
    connection: &Connection,
    where_clause: &str,
    params: P,
) -> Result<Option<PendingMutationRead>>
where
    P: rusqlite::Params,
{
    let query = format!(
        r#"
        SELECT
            id,
            client_mutation_id,
            mutation_type,
            resource_type,
            resource_id,
            payload_json,
            status,
            attempt_count,
            last_error,
            resulting_event_sequence,
            created_at,
            updated_at,
            last_attempted_at
        FROM mutation_outbox
        {where_clause}
        LIMIT 1
        "#
    );
    connection
        .query_row(&query, params, map_mutation_row)
        .optional()
        .map_err(Into::into)
}

fn map_mutation_row(row: &rusqlite::Row<'_>) -> rusqlite::Result<PendingMutationRead> {
    let payload_raw: String = row.get(5)?;
    Ok(PendingMutationRead {
        id: row.get(0)?,
        client_mutation_id: row.get(1)?,
        mutation_type: row.get(2)?,
        resource_type: row.get(3)?,
        resource_id: row.get(4)?,
        payload: parse_json_value(Some(payload_raw))
            .unwrap_or_else(|| Value::Object(Default::default())),
        status: row.get(6)?,
        attempt_count: row.get(7)?,
        last_error: row.get(8)?,
        resulting_event_sequence: row.get(9)?,
        created_at: row.get(10)?,
        updated_at: row.get(11)?,
        last_attempted_at: row.get(12)?,
    })
}

fn map_attachment_row(row: &rusqlite::Row<'_>) -> rusqlite::Result<PaperAttachmentRead> {
    Ok(PaperAttachmentRead {
        id: row.get(0)?,
        paper_id: row.get(1)?,
        attachment_kind: row.get(2)?,
        storage_mode: row.get(3)?,
        original_file_name: row.get(4)?,
        stored_file_name: row.get(5)?,
        file_extension: row.get(6)?,
        relative_path: row.get(7)?,
        absolute_path: row.get(8)?,
        source_path: row.get(9)?,
        size_bytes: row.get(10)?,
        mime_type: row.get(11)?,
        sha256: row.get(12)?,
        status: row.get(13)?,
        imported_at: row.get(14)?,
        updated_at: row.get(15)?,
        last_opened_at: row.get(16)?,
    })
}

fn map_note_row(row: &rusqlite::Row<'_>) -> rusqlite::Result<PaperNoteSummaryRead> {
    Ok(PaperNoteSummaryRead {
        id: row.get(0)?,
        paper_id: row.get(1)?,
        template_kind: row.get(2)?,
        title: row.get(3)?,
        file_name: row.get(4)?,
        relative_path: row.get(5)?,
        absolute_path: row.get(6)?,
        content_format: row.get(7)?,
        source_mode: row.get(8)?,
        status: row.get(9)?,
        size_bytes: row.get(10)?,
        sha256: row.get(11)?,
        created_at: row.get(12)?,
        updated_at: row.get(13)?,
        last_opened_at: row.get(14)?,
    })
}

fn map_review_round_row(row: &rusqlite::Row<'_>) -> rusqlite::Result<ReviewRoundSummaryRead> {
    Ok(ReviewRoundSummaryRead {
        id: row.get(0)?,
        paper_id: row.get(1)?,
        round_label: row.get(2)?,
        venue: row.get(3)?,
        decision_label: row.get(4)?,
        status: row.get(5)?,
        source_mode: row.get(6)?,
        reviewer_count: row.get(7)?,
        generated_response_note_id: row.get(8)?,
        generated_matrix_note_id: row.get(9)?,
        created_at: row.get(10)?,
        updated_at: row.get(11)?,
    })
}

fn map_review_comment_row(row: &rusqlite::Row<'_>) -> rusqlite::Result<ReviewCommentItemRead> {
    Ok(ReviewCommentItemRead {
        id: row.get(0)?,
        review_round_id: row.get(1)?,
        paper_id: row.get(2)?,
        reviewer_label: row.get(3)?,
        comment_code: row.get(4)?,
        sort_order: row.get(5)?,
        comment_text: row.get(6)?,
        category: row.get(7)?,
        disposition: row.get(8)?,
        response_summary: row.get(9)?,
        action_note: row.get(10)?,
        created_at: row.get(11)?,
        updated_at: row.get(12)?,
    })
}

fn collect_rows<T>(
    rows: rusqlite::MappedRows<'_, impl FnMut(&rusqlite::Row<'_>) -> rusqlite::Result<T>>,
) -> Result<Vec<T>> {
    let mut items = Vec::new();
    for row in rows {
        items.push(row?);
    }
    Ok(items)
}

fn required_string(payload: &Value, key: &str) -> Result<String> {
    value_as_string(payload.get(key))
        .ok_or_else(|| invalid_state(format!("expected string field {key} in sync payload")))
}

fn value_as_string(value: Option<&Value>) -> Option<String> {
    match value {
        Some(Value::String(text)) => Some(text.clone()),
        Some(Value::Null) | None => None,
        Some(other) => Some(other.to_string()),
    }
}

fn value_as_i64(value: Option<&Value>) -> i64 {
    value.and_then(Value::as_i64).unwrap_or_default()
}

fn maybe_json_string(value: Option<&Value>) -> Result<Option<String>> {
    match value {
        Some(Value::Null) | None => Ok(None),
        Some(other) => Ok(Some(serde_json::to_string(other)?)),
    }
}

fn parse_json_value(raw: Option<String>) -> Option<Value> {
    raw.and_then(|value| serde_json::from_str(&value).ok())
}

fn parse_json_array(raw: Option<String>) -> Vec<String> {
    parse_json_value(raw)
        .and_then(|value| serde_json::from_value::<Vec<String>>(value).ok())
        .unwrap_or_default()
}

fn timestamp_now() -> String {
    chrono::Utc::now().to_rfc3339()
}

fn build_sync_status(
    state: SyncStateRecord,
    token_present: bool,
    stats: OutboxStats,
) -> SyncStatusRead {
    let current_user_summary = match (
        state.user_id.clone(),
        state.user_name.clone(),
        state.base_url.clone(),
        state.device_id.clone(),
        state.device_display_name.clone(),
    ) {
        (Some(user_id), Some(name), Some(base_url), Some(device_id), Some(device_display_name)) => {
            Some(UserConnectionRead {
                user_id,
                name,
                email: state.user_email.clone(),
                field: state.user_field.clone(),
                base_url,
                device_id,
                device_display_name,
            })
        }
        _ => None,
    };
    SyncStatusRead {
        connected: state.connected && token_present,
        base_url: state.base_url,
        device_id: state.device_id,
        device_display_name: state.device_display_name,
        last_synced_at: state.last_synced_at,
        last_event_sequence: state.last_event_sequence,
        last_error: state.last_error,
        pending_mutation_count: stats.pending_count,
        failed_mutation_count: stats.failed_count,
        recent_outbox_errors: stats.recent_errors,
        current_user_summary,
    }
}

#[cfg(test)]
mod tests {
    use tempfile::tempdir;

    use super::LocalCache;
    use crate::models::RemoteSyncEvent;

    fn cache() -> LocalCache {
        let dir = tempdir().unwrap();
        let root = dir.path().to_path_buf();
        std::mem::forget(dir);
        let cache = LocalCache::new(root.join("desktop.sqlite3"));
        cache.initialize().unwrap();
        cache
    }

    #[test]
    fn apply_event_batch_materializes_paper_detail_today_and_subscription_policy() {
        let cache = cache();
        cache
            .upsert_connection(
                "http://localhost:8000",
                "device-1",
                "Primary Desktop",
                "user-1",
                "Desktop User",
                Some("desktop@example.com"),
                Some("Materials"),
            )
            .unwrap();

        cache
            .apply_event_batch(&[
                RemoteSyncEvent {
                    id: "evt-1".to_string(),
                    sequence: 1,
                    user_id: "user-1".to_string(),
                    entity_type: "paper_profile".to_string(),
                    entity_id: "paper-1".to_string(),
                    event_type: "created".to_string(),
                    event_source: "api".to_string(),
                    occurred_at: "2026-04-15T00:00:00Z".to_string(),
                    payload: serde_json::json!({
                        "id": "paper-1",
                        "user_id": "user-1",
                        "title": "Desktop Paper",
                        "type": "revision",
                        "stage": "revision",
                        "venue": "JOM",
                        "priority": 5,
                        "next_action": "Prepare response",
                        "blocker": null,
                        "last_touch_at": "2026-04-15T00:00:00Z",
                        "updated_at": "2026-04-15T00:00:00Z",
                        "identifiers": {"doi": "10.1000/test"},
                        "source_links": ["https://example.local/paper"],
                    }),
                },
                RemoteSyncEvent {
                    id: "evt-2".to_string(),
                    sequence: 2,
                    user_id: "user-1".to_string(),
                    entity_type: "progress_event".to_string(),
                    entity_id: "progress-1".to_string(),
                    event_type: "created".to_string(),
                    event_source: "api".to_string(),
                    occurred_at: "2026-04-15T00:00:00Z".to_string(),
                    payload: serde_json::json!({
                        "id": "progress-1",
                        "paper_id": "paper-1",
                        "stage": "revision",
                        "happened_at": "2026-04-15T00:00:00Z",
                        "summary": "Added from sync feed",
                        "owner": "desktop",
                        "evidence_links": [],
                    }),
                },
                RemoteSyncEvent {
                    id: "evt-3".to_string(),
                    sequence: 3,
                    user_id: "user-1".to_string(),
                    entity_type: "subscription_policy".to_string(),
                    entity_id: "policy-1".to_string(),
                    event_type: "updated".to_string(),
                    event_source: "api".to_string(),
                    occurred_at: "2026-04-15T00:00:00Z".to_string(),
                    payload: serde_json::json!({
                        "id": "policy-1",
                        "user_id": "user-1",
                        "channel": "in_app",
                        "enabled": true,
                        "frequency": "daily",
                        "quiet_hours": {"start": "22:00", "end": "07:00"},
                        "frequency_cap": 3,
                        "policy": {"stale_days": 10},
                        "updated_at": "2026-04-15T00:00:00Z",
                    }),
                },
                RemoteSyncEvent {
                    id: "evt-4".to_string(),
                    sequence: 4,
                    user_id: "user-1".to_string(),
                    entity_type: "pulse_digest_issue".to_string(),
                    entity_id: "digest-1".to_string(),
                    event_type: "updated".to_string(),
                    event_source: "worker".to_string(),
                    occurred_at: "2026-04-15T00:00:00Z".to_string(),
                    payload: serde_json::json!({
                        "id": "digest-1",
                        "user_id": "user-1",
                        "issue_date": "2026-04-15",
                        "status": "ready",
                        "title": "Digest",
                        "summary": "Summary",
                        "highlight_count": 2,
                        "selected_card_count": 2,
                        "deep_link_path": "/mini/pulse-digests/user-1/2026-04-15",
                        "highlights": [{
                            "sort_order": 1,
                            "pulse_card_id": "card-1",
                            "card_type": "signal_change",
                            "source_paper_id": "paper-1",
                            "title": "Signal update",
                            "summary": "Summary",
                            "why_now": "Why now"
                        }, {
                            "sort_order": 2,
                            "pulse_card_id": "card-2",
                            "card_type": "yesterday_summary",
                            "source_paper_id": serde_json::Value::Null,
                            "title": "Yesterday summary for 2026-04-14",
                            "summary": "Yesterday recorded 2 activities.",
                            "why_now": "2026-04-14 provides a concise recap before today's work starts."
                        }],
                        "items": [{
                            "sort_order": 1,
                            "pulse_card_id": "card-1",
                            "card_type": "signal_change",
                            "source_paper_id": "paper-1",
                            "title": "Signal update",
                            "summary": "Summary",
                            "why_now": "Why now"
                        }, {
                            "sort_order": 2,
                            "pulse_card_id": "card-2",
                            "card_type": "yesterday_summary",
                            "source_paper_id": serde_json::Value::Null,
                            "title": "Yesterday summary for 2026-04-14",
                            "summary": "Yesterday recorded 2 activities.",
                            "why_now": "2026-04-14 provides a concise recap before today's work starts."
                        }],
                        "updated_at": "2026-04-15T00:00:00Z"
                    }),
                },
            ])
            .unwrap();

        let detail = cache.get_paper_detail("paper-1").unwrap();
        assert_eq!(detail.progress_percentage, 80);
        assert_eq!(detail.progress_events.len(), 1);

        let policies = cache.list_subscription_policies().unwrap();
        assert_eq!(policies.len(), 1);
        assert_eq!(policies[0].channel, "in_app");

        let today = cache.read_today_overview().unwrap();
        assert_eq!(today.state, "ready");
        assert_eq!(today.highlights.len(), 2);
        assert_eq!(today.highlights[0].paper.as_ref().unwrap().id, "paper-1");
        assert_eq!(today.highlights[1].card_type, "yesterday_summary");
        assert!(today.highlights[1].paper.is_none());
    }

    #[test]
    fn queued_mutation_is_visible_in_outbox_and_sync_status() {
        let cache = cache();
        cache
            .enqueue_mutation(
                "mutation-1",
                "client-1",
                "paper.patch",
                "paper_profile",
                Some("paper-1"),
                &serde_json::json!({"stage": "revision"}),
            )
            .unwrap();

        let pending = cache.list_pending_mutations().unwrap();
        assert_eq!(pending.len(), 1);
        assert_eq!(pending[0].status, "queued");

        let status = cache.sync_status(false).unwrap();
        assert_eq!(status.pending_mutation_count, 1);
        assert_eq!(status.failed_mutation_count, 0);
    }

    #[test]
    fn reset_local_cache_clears_cached_state_and_outbox() {
        let cache = cache();
        cache
            .upsert_connection(
                "http://localhost:8000",
                "device-1",
                "Primary Desktop",
                "user-1",
                "Desktop User",
                Some("desktop@example.com"),
                None,
            )
            .unwrap();
        cache
            .apply_event_batch(&[RemoteSyncEvent {
                id: "evt-1".to_string(),
                sequence: 1,
                user_id: "user-1".to_string(),
                entity_type: "paper_profile".to_string(),
                entity_id: "paper-1".to_string(),
                event_type: "created".to_string(),
                event_source: "api".to_string(),
                occurred_at: "2026-04-15T00:00:00Z".to_string(),
                payload: serde_json::json!({
                    "id": "paper-1",
                    "user_id": "user-1",
                    "title": "Desktop Paper",
                    "type": "published",
                    "stage": "published",
                    "priority": 3,
                    "identifiers": {},
                    "source_links": []
                }),
            }])
            .unwrap();
        cache
            .enqueue_mutation(
                "mutation-1",
                "client-1",
                "paper.patch",
                "paper_profile",
                Some("paper-1"),
                &serde_json::json!({"stage": "revision"}),
            )
            .unwrap();
        cache.reset_local_cache().unwrap();

        assert!(cache.list_papers(None, None, None).unwrap().is_empty());
        assert!(cache.list_pending_mutations().unwrap().is_empty());
        assert_eq!(cache.sync_state_record().unwrap().last_event_sequence, 0);
    }
}
