use std::path::PathBuf;

use anyhow::{Context, Result};
use rusqlite::{params, Connection, OptionalExtension};
use serde_json::Value;

use crate::error::{ensure_parent_dir, invalid_state};
use crate::models::{
    DigestHighlightRead, PaperDetailRead, PaperListItemRead, ProgressEventRead, RemoteSyncEvent,
    SignalSnapshotRead, SyncStatusRead, TodayOverviewRead, UserConnectionRead,
};
use crate::progress::derive_progress_percentage;

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
                    ON digest_issue_cache (user_id, issue_date DESC, updated_at DESC, id ASC);

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

                PRAGMA user_version = 1;
                "#,
            )
            .context("failed to initialize desktop cache schema")?;
        Ok(())
    }

    pub fn open(&self) -> Result<Connection> {
        Connection::open(&self.path)
            .with_context(|| format!("failed to open desktop cache {}", self.path.display()))
    }

    pub fn sync_status(&self, token_present: bool) -> Result<SyncStatusRead> {
        let state = self.sync_state_record()?;
        Ok(build_sync_status(state, token_present))
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
        connection.execute("UPDATE sync_state SET last_error = NULL WHERE singleton_id = 1", [])?;
        Ok(())
    }

    pub fn update_after_ack(&self, last_event_sequence: i64, last_synced_at: Option<&str>) -> Result<()> {
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
        connection.execute("DELETE FROM digest_issue_cache", [])?;
        connection.execute("DELETE FROM sync_event_cache", [])?;
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
        let user_id: Option<String> = connection
            .query_row("SELECT user_id FROM sync_state WHERE singleton_id = 1", [], |row| row.get(0))
            .optional()?;
        let Some(user_id) = user_id else {
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

    pub fn list_papers(&self, paper_type: Option<&str>, stage: Option<&str>, limit: Option<usize>) -> Result<Vec<PaperListItemRead>> {
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
            let paper_type: String = row.get(3)?;
            Ok(PaperListItemRead {
                id: row.get(0)?,
                user_id: row.get(1)?,
                title: row.get(2)?,
                paper_type: paper_type.clone(),
                stage: row.get(4)?,
                venue: row.get(5)?,
                priority: row.get(6)?,
                next_action: row.get(7)?,
                blocker: row.get(8)?,
                last_touch_at: row.get(9)?,
                progress_percentage: derive_progress_percentage(&paper_type),
                updated_at: row.get(10)?,
            })
        })?;
        let mut papers = Vec::new();
        for row in rows {
            papers.push(row?);
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
            let mut items = Vec::new();
            for row in rows {
                items.push(row?);
            }
            items
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
            let mut items = Vec::new();
            for row in rows {
                items.push(row?);
            }
            items
        };

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
            identifiers: serde_json::from_str(&paper.11).unwrap_or(Value::Object(Default::default())),
            source_links: serde_json::from_str(&paper.12).unwrap_or_default(),
            progress_events,
            signal_snapshots,
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
                    let paper_type: String = row.get(3)?;
                    Ok(PaperListItemRead {
                        id: row.get(0)?,
                        user_id: row.get(1)?,
                        title: row.get(2)?,
                        paper_type: paper_type.clone(),
                        stage: row.get(4)?,
                        venue: row.get(5)?,
                        priority: row.get(6)?,
                        next_action: row.get(7)?,
                        blocker: row.get(8)?,
                        last_touch_at: row.get(9)?,
                        progress_percentage: derive_progress_percentage(&paper_type),
                        updated_at: row.get(10)?,
                    })
                },
            )
            .optional()?;
        Ok(row)
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
        "pulse_digest_issue" => upsert_digest_issue(connection, &event.payload)?,
        _ => {}
    }
    Ok(())
}

fn upsert_paper(connection: &Connection, payload: &Value) -> Result<()> {
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
            required_string(payload, "id")?,
            required_string(payload, "user_id")?,
            required_string(payload, "title")?,
            required_string(payload, "type")?,
            required_string(payload, "stage")?,
            value_as_string(payload.get("venue")),
            payload.get("priority").and_then(Value::as_i64).unwrap_or(0),
            value_as_string(payload.get("next_action")),
            value_as_string(payload.get("blocker")),
            value_as_string(payload.get("last_touch_at")),
            value_as_string(payload.get("updated_at")),
            serde_json::to_string(payload.get("identifiers").unwrap_or(&Value::Object(Default::default())))?,
            serde_json::to_string(payload.get("source_links").unwrap_or(&Value::Array(Vec::new())))?,
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
            serde_json::to_string(payload.get("evidence_links").unwrap_or(&Value::Array(Vec::new())))?,
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
            payload.get("highlight_count").and_then(Value::as_i64).unwrap_or(0),
            payload
                .get("selected_card_count")
                .and_then(Value::as_i64)
                .unwrap_or(0),
            value_as_string(payload.get("deep_link_path")),
            serde_json::to_string(payload.get("highlights").unwrap_or(&Value::Array(Vec::new())))?,
            serde_json::to_string(payload.get("items").unwrap_or(&Value::Array(Vec::new())))?,
            value_as_string(payload.get("updated_at")),
        ],
    )?;
    Ok(())
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

fn build_sync_status(state: SyncStateRecord, token_present: bool) -> SyncStatusRead {
    let current_user_summary = match (
        state.user_id.clone(),
        state.user_name.clone(),
        state.base_url.clone(),
        state.device_id.clone(),
        state.device_display_name.clone(),
    ) {
        (
            Some(user_id),
            Some(name),
            Some(base_url),
            Some(device_id),
            Some(device_display_name),
        ) => Some(UserConnectionRead {
            user_id,
            name,
            email: state.user_email.clone(),
            field: state.user_field.clone(),
            base_url,
            device_id,
            device_display_name,
        }),
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
    fn apply_event_batch_materializes_paper_detail_and_today() {
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
                        "highlight_count": 1,
                        "selected_card_count": 1,
                        "deep_link_path": "/mini/pulse-digests/user-1/2026-04-15",
                        "highlights": [{
                            "sort_order": 1,
                            "pulse_card_id": "card-1",
                            "card_type": "signal_change",
                            "source_paper_id": "paper-1",
                            "title": "Signal update",
                            "summary": "Summary",
                            "why_now": "Why now"
                        }],
                        "items": [{
                            "sort_order": 1,
                            "pulse_card_id": "card-1",
                            "card_type": "signal_change",
                            "source_paper_id": "paper-1",
                            "title": "Signal update",
                            "summary": "Summary",
                            "why_now": "Why now"
                        }],
                        "updated_at": "2026-04-15T00:00:00Z"
                    }),
                },
            ])
            .unwrap();

        let detail = cache.get_paper_detail("paper-1").unwrap();
        assert_eq!(detail.progress_percentage, 80);
        assert_eq!(detail.progress_events.len(), 1);

        let today = cache.read_today_overview().unwrap();
        assert_eq!(today.state, "ready");
        assert_eq!(today.highlights.len(), 1);
        assert_eq!(today.highlights[0].paper.as_ref().unwrap().id, "paper-1");
    }

    #[test]
    fn reset_local_cache_clears_cached_state() {
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
        cache.reset_local_cache().unwrap();

        assert!(cache.list_papers(None, None, None).unwrap().is_empty());
        assert_eq!(cache.sync_state_record().unwrap().last_event_sequence, 0);
    }
}
