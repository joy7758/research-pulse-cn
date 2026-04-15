use std::path::PathBuf;

use anyhow::{Context, Result};
use serde_json::{json, Value};
use uuid::Uuid;

use crate::cache::{LocalCache, PushOutcomeSummary};
use crate::error::invalid_state;
use crate::models::{
    AppBootstrapRead, ChooseWorkspaceRootInput, ConnectDeviceInput, ConnectDeviceResponse,
    CreateBlankPaperNoteInput, CreatePaperNoteFromTemplateInput, ImportPaperAttachmentsInput,
    ImportPaperAttachmentsResponse, ListPapersInput, ListReviewRoundsInput,
    NoteActionResultRead, NoteTemplateRead, PaperAttachmentImportResultRead,
    PaperAttachmentRead, PaperDetailRead, PaperListItemRead, PaperNoteDetailRead,
    PaperNoteSummaryRead, PaperWorkspaceRead, PendingMutationRead, QueuePaperPatchInput,
    QueueProgressEventCreateInput, QueueSubscriptionPolicyPatchInput,
    RemoteSyncMutationRequest, RemoteSyncPushRequest, ReviewActionResultRead,
    ReviewCommentItemRead, ReviewRoundDetailRead, ReviewRoundSummaryRead,
    SavePaperNoteInput, SubscriptionPolicyRead, SyncNowResponse, SyncStatusRead,
    TodayOverviewRead, UpdateReviewRoundInput, AddReviewCommentInput, CreateReviewRoundInput,
    DeleteReviewCommentInput, ListReviewCommentsInput, ReviewRoundLookupInput,
    UserConnectionRead, WorkspaceStatusRead, WriteActionResultRead,
};
use crate::notes::{
    list_note_templates, note_status_for_path, prepare_blank_note, prepare_generated_note,
    prepare_template_note, read_note_file, write_note_file, NoteTemplateContext,
};
use crate::review::{
    default_review_disposition, render_response_letter_note, render_reviewer_matrix_note,
    validate_review_disposition, validate_review_round_status,
};
use crate::secret_store::FileSecretStore;
use crate::sync_client::{ReqwestSyncBackendApi, SyncBackendApi};
use crate::workspace::{
    attachment_status_for_path, build_workspace_layout, collect_file_import_metadata,
    ensure_paper_workspace_layout, paper_workspace_ready_for_path, path_to_string,
    prepare_attachment_import, should_treat_as_duplicate, validate_attachment_kind,
    validate_workspace_root, workspace_root_rebind_path, WorkspaceRootRecord,
};

const FEED_PAGE_LIMIT: usize = 100;

#[derive(Debug, Clone)]
pub struct DesktopPaths {
    pub app_data_dir: PathBuf,
    pub cache_db_path: PathBuf,
    pub secret_store_path: PathBuf,
}

#[derive(Debug, Clone)]
pub struct DesktopService {
    pub paths: DesktopPaths,
}

impl DesktopService {
    pub fn new(paths: DesktopPaths) -> Result<Self> {
        std::fs::create_dir_all(&paths.app_data_dir)
            .with_context(|| format!("failed to create {}", paths.app_data_dir.display()))?;
        let cache = LocalCache::new(paths.cache_db_path.clone());
        cache.initialize()?;
        Ok(Self { paths })
    }

    pub fn app_bootstrap(&self) -> Result<AppBootstrapRead> {
        Ok(AppBootstrapRead {
            sync_status: self.get_sync_status()?,
            today_overview: self.get_today_overview()?,
        })
    }

    pub fn get_sync_status(&self) -> Result<SyncStatusRead> {
        let cache = self.cache();
        let token_present = self.secret_store().load_device_token()?.is_some();
        cache.sync_status(token_present)
    }

    pub fn get_today_overview(&self) -> Result<TodayOverviewRead> {
        self.cache().read_today_overview()
    }

    pub fn list_papers(&self, filters: Option<ListPapersInput>) -> Result<Vec<PaperListItemRead>> {
        let filters = filters.unwrap_or_default();
        self.cache().list_papers(
            filters.paper_type.as_deref(),
            filters.stage.as_deref(),
            filters.limit,
        )
    }

    pub fn get_paper_detail(&self, paper_id: &str) -> Result<PaperDetailRead> {
        self.cache().get_paper_detail(paper_id)
    }

    pub fn list_subscription_policies(&self) -> Result<Vec<SubscriptionPolicyRead>> {
        self.cache().list_subscription_policies()
    }

    pub fn list_pending_mutations(&self) -> Result<Vec<PendingMutationRead>> {
        self.cache().list_pending_mutations()
    }

    pub fn get_workspace_status(&self) -> Result<WorkspaceStatusRead> {
        let cache = self.cache();
        let current = cache.workspace_root_record()?;
        let validation = validate_workspace_root(current.root_path.as_deref());
        cache.upsert_workspace_root_record(
            validation.root_path.as_deref(),
            &validation.status,
            validation.last_validated_at.as_str(),
            validation.last_error.as_deref(),
        )?;
        cache.rebind_workspace_root(validation.root_path.as_deref())?;
        cache.workspace_status()
    }

    pub fn choose_workspace_root(
        &self,
        input: ChooseWorkspaceRootInput,
    ) -> Result<WorkspaceStatusRead> {
        let validation = validate_workspace_root(Some(&input.selected_path));
        if validation.status != "ready" {
            return Err(invalid_state(
                validation
                    .last_error
                    .unwrap_or_else(|| "workspace root is not valid".to_string()),
            ));
        }
        let cache = self.cache();
        cache.upsert_workspace_root_record(
            validation.root_path.as_deref(),
            &validation.status,
            validation.last_validated_at.as_str(),
            None,
        )?;
        cache.rebind_workspace_root(validation.root_path.as_deref())?;
        cache.workspace_status()
    }

    pub fn clear_workspace_root(&self) -> Result<WorkspaceStatusRead> {
        let cache = self.cache();
        let validation = validate_workspace_root(None);
        cache.upsert_workspace_root_record(
            None,
            &validation.status,
            validation.last_validated_at.as_str(),
            None,
        )?;
        cache.rebind_workspace_root(None)?;
        cache.workspace_status()
    }

    pub fn ensure_paper_workspace(&self, paper_id: &str) -> Result<PaperWorkspaceRead> {
        if paper_id.trim().is_empty() {
            return Err(invalid_state("paper_id is required"));
        }
        let cache = self.cache();
        let root = self.ensure_workspace_root_ready()?;
        let paper = cache.get_paper_detail(paper_id)?;
        let layout = ensure_paper_workspace_layout(
            std::path::Path::new(&root.root_path.clone().unwrap_or_default()),
            paper_id,
            &paper.title,
        )?;
        cache.upsert_paper_workspace(
            paper_id,
            &paper.title,
            &layout.paper_rel_path,
            Some(path_to_string(&layout.paper_abs_path).as_str()),
            true,
            None,
        )?;
        cache.get_paper_workspace(paper_id)
    }

    pub fn get_paper_workspace(&self, paper_id: &str) -> Result<PaperWorkspaceRead> {
        if paper_id.trim().is_empty() {
            return Err(invalid_state("paper_id is required"));
        }
        self.cache().get_paper_workspace(paper_id)
    }

    pub fn list_paper_attachments(&self, paper_id: &str) -> Result<Vec<PaperAttachmentRead>> {
        if paper_id.trim().is_empty() {
            return Err(invalid_state("paper_id is required"));
        }
        self.cache().list_paper_attachments(paper_id)
    }

    pub fn list_note_templates(&self) -> Result<Vec<NoteTemplateRead>> {
        Ok(list_note_templates())
    }

    pub fn list_paper_notes(&self, paper_id: &str) -> Result<Vec<PaperNoteSummaryRead>> {
        if paper_id.trim().is_empty() {
            return Err(invalid_state("paper_id is required"));
        }
        self.cache().list_paper_notes(paper_id)
    }

    pub fn create_paper_note_from_template(
        &self,
        input: CreatePaperNoteFromTemplateInput,
    ) -> Result<NoteActionResultRead> {
        if input.paper_id.trim().is_empty() {
            return Err(invalid_state("paper_id is required"));
        }
        let cache = self.cache();
        let paper = cache.get_paper_detail(&input.paper_id)?;
        let root = self.ensure_workspace_root_ready()?;
        let root_path = std::path::Path::new(root.root_path.as_deref().unwrap_or_default());
        let layout = ensure_paper_workspace_layout(root_path, &paper.id, &paper.title)?;
        cache.upsert_paper_workspace(
            &paper.id,
            &paper.title,
            &layout.paper_rel_path,
            Some(path_to_string(&layout.paper_abs_path).as_str()),
            true,
            paper.workspace.last_imported_at.as_deref(),
        )?;

        let created_at = chrono::Utc::now().to_rfc3339();
        let note_id = Uuid::new_v4().to_string();
        let prepared = prepare_template_note(
            &layout,
            &input.template_kind,
            &build_note_context(&paper),
            &note_id,
            &created_at,
        )?;
        let file_stats = write_note_file(&prepared.absolute_path, &prepared.content)?;
        let status = note_status_for_path(Some(&prepared.absolute_path));
        cache.upsert_paper_note(
            &prepared.note_id,
            &paper.id,
            &prepared.template_kind,
            &prepared.title,
            &prepared.file_name,
            &prepared.relative_path,
            Some(&prepared.absolute_path),
            "markdown",
            &prepared.source_mode,
            &status,
            file_stats.size_bytes,
            file_stats.sha256.as_deref(),
            &prepared.created_at,
            &prepared.created_at,
            None,
        )?;
        let note = self.get_paper_note(&prepared.note_id)?;
        self.record_local_work_activity(
            Some(&paper.id),
            "note_created",
            format!("Created note \"{}\".", prepared.title),
            json!({
                "note_id": prepared.note_id,
                "template_kind": prepared.template_kind,
                "source_mode": prepared.source_mode,
            }),
            &prepared.created_at,
        )?;
        Ok(NoteActionResultRead {
            note,
            message: format!("Created {} from template.", prepared.title),
        })
    }

    pub fn create_blank_paper_note(
        &self,
        input: CreateBlankPaperNoteInput,
    ) -> Result<NoteActionResultRead> {
        if input.paper_id.trim().is_empty() {
            return Err(invalid_state("paper_id is required"));
        }
        let cache = self.cache();
        let paper = cache.get_paper_detail(&input.paper_id)?;
        let root = self.ensure_workspace_root_ready()?;
        let root_path = std::path::Path::new(root.root_path.as_deref().unwrap_or_default());
        let layout = ensure_paper_workspace_layout(root_path, &paper.id, &paper.title)?;
        cache.upsert_paper_workspace(
            &paper.id,
            &paper.title,
            &layout.paper_rel_path,
            Some(path_to_string(&layout.paper_abs_path).as_str()),
            true,
            paper.workspace.last_imported_at.as_deref(),
        )?;

        let created_at = chrono::Utc::now().to_rfc3339();
        let note_id = Uuid::new_v4().to_string();
        let prepared = prepare_blank_note(
            &layout,
            input.title.as_deref(),
            &build_note_context(&paper),
            &note_id,
            &created_at,
        )?;
        let file_stats = write_note_file(&prepared.absolute_path, &prepared.content)?;
        let status = note_status_for_path(Some(&prepared.absolute_path));
        cache.upsert_paper_note(
            &prepared.note_id,
            &paper.id,
            &prepared.template_kind,
            &prepared.title,
            &prepared.file_name,
            &prepared.relative_path,
            Some(&prepared.absolute_path),
            "markdown",
            &prepared.source_mode,
            &status,
            file_stats.size_bytes,
            file_stats.sha256.as_deref(),
            &prepared.created_at,
            &prepared.created_at,
            None,
        )?;
        let note = self.get_paper_note(&prepared.note_id)?;
        self.record_local_work_activity(
            Some(&paper.id),
            "note_created",
            format!("Created note \"{}\".", prepared.title),
            json!({
                "note_id": prepared.note_id,
                "template_kind": prepared.template_kind,
                "source_mode": prepared.source_mode,
            }),
            &prepared.created_at,
        )?;
        Ok(NoteActionResultRead {
            note,
            message: format!("Created {}.", prepared.title),
        })
    }

    pub fn get_paper_note(&self, note_id: &str) -> Result<PaperNoteDetailRead> {
        if note_id.trim().is_empty() {
            return Err(invalid_state("note_id is required"));
        }
        let cache = self.cache();
        cache.get_paper_note_summary(note_id)?;
        let last_opened_at = chrono::Utc::now().to_rfc3339();
        let note = cache.touch_paper_note_opened_at(note_id, &last_opened_at)?;
        let content = if note.status == "ready" {
            note.absolute_path
                .as_deref()
                .map(read_note_file)
                .transpose()?
        } else {
            None
        };
        Ok(PaperNoteDetailRead { note, content })
    }

    pub fn save_paper_note(&self, input: SavePaperNoteInput) -> Result<NoteActionResultRead> {
        if input.note_id.trim().is_empty() {
            return Err(invalid_state("note_id is required"));
        }
        let cache = self.cache();
        let existing = cache.get_paper_note_summary(&input.note_id)?;
        let absolute_path = existing.absolute_path.clone().ok_or_else(|| {
            invalid_state("note file path is not available because the workspace root is missing")
        })?;
        let _ = self.ensure_workspace_root_ready()?;
        let file_stats = write_note_file(&absolute_path, &input.content)?;
        let updated_at = chrono::Utc::now().to_rfc3339();
        let status = note_status_for_path(Some(&absolute_path));
        cache.upsert_paper_note(
            &existing.id,
            &existing.paper_id,
            &existing.template_kind,
            &existing.title,
            &existing.file_name,
            &existing.relative_path,
            Some(&absolute_path),
            &existing.content_format,
            &existing.source_mode,
            &status,
            file_stats.size_bytes,
            file_stats.sha256.as_deref(),
            &existing.created_at,
            &updated_at,
            Some(&updated_at),
        )?;
        let note = self.get_paper_note(&existing.id)?;
        self.record_local_work_activity(
            Some(&existing.paper_id),
            "note_saved",
            format!("Saved note \"{}\".", existing.title),
            json!({
                "note_id": existing.id,
                "template_kind": existing.template_kind,
            }),
            &updated_at,
        )?;
        Ok(NoteActionResultRead {
            note,
            message: format!("Saved {}.", existing.title),
        })
    }

    pub fn refresh_paper_notes(&self, paper_id: &str) -> Result<Vec<PaperNoteSummaryRead>> {
        if paper_id.trim().is_empty() {
            return Err(invalid_state("paper_id is required"));
        }
        let cache = self.cache();
        let root_status = self.get_workspace_status()?;
        cache.refresh_note_statuses(root_status.root_path.as_deref(), paper_id)?;
        cache.list_paper_notes(paper_id)
    }

    pub fn list_review_rounds(
        &self,
        input: ListReviewRoundsInput,
    ) -> Result<Vec<ReviewRoundSummaryRead>> {
        if input.paper_id.trim().is_empty() {
            return Err(invalid_state("paper_id is required"));
        }
        self.cache().list_review_rounds(&input.paper_id)
    }

    pub fn create_review_round(
        &self,
        input: CreateReviewRoundInput,
    ) -> Result<ReviewActionResultRead> {
        if input.paper_id.trim().is_empty() {
            return Err(invalid_state("paper_id is required"));
        }
        let round_label = non_empty(input.round_label)
            .ok_or_else(|| invalid_state("round_label is required"))?;
        let cache = self.cache();
        let paper = cache.get_paper_detail(&input.paper_id)?;
        let round_id = Uuid::new_v4().to_string();
        let created_at = chrono::Utc::now().to_rfc3339();
        let round = cache.upsert_review_round(
            &round_id,
            &paper.id,
            &round_label,
            input.venue.as_deref().and_then(trimmed_optional),
            input
                .decision_label
                .as_deref()
                .and_then(trimmed_optional),
            "open",
            "manual",
            0,
            None,
            None,
            &created_at,
            &created_at,
        )?;
        let detail = cache.get_review_round_detail(&round.id)?;
        self.record_local_work_activity(
            Some(&paper.id),
            "review_round_created",
            format!("Created review round \"{}\".", round.round_label),
            json!({
                "review_round_id": round.id,
                "round_label": round.round_label,
            }),
            &created_at,
        )?;
        Ok(ReviewActionResultRead {
            message: format!("Created review round {}.", round.round_label),
            round: Some(round),
            comment: None,
            detail: Some(detail),
            generated_note: None,
        })
    }

    pub fn update_review_round(
        &self,
        input: UpdateReviewRoundInput,
    ) -> Result<ReviewActionResultRead> {
        if input.review_round_id.trim().is_empty() {
            return Err(invalid_state("review_round_id is required"));
        }
        let cache = self.cache();
        let existing = cache.get_review_round_summary(&input.review_round_id)?;
        let round_label = match input.round_label {
            Some(value) => {
                non_empty(value).ok_or_else(|| invalid_state("round_label must not be empty"))?
            }
            None => existing.round_label.clone(),
        };
        let status = match input.status {
            Some(value) => validate_review_round_status(&value)?,
            None => existing.status.clone(),
        };
        let round = cache.upsert_review_round(
            &existing.id,
            &existing.paper_id,
            &round_label,
            option_override(existing.venue.as_deref(), input.venue.as_deref()),
            option_override(
                existing.decision_label.as_deref(),
                input.decision_label.as_deref(),
            ),
            &status,
            &existing.source_mode,
            existing.reviewer_count,
            existing.generated_response_note_id.as_deref(),
            existing.generated_matrix_note_id.as_deref(),
            &existing.created_at,
            &chrono::Utc::now().to_rfc3339(),
        )?;
        let detail = cache.get_review_round_detail(&round.id)?;
        Ok(ReviewActionResultRead {
            message: format!("Updated review round {}.", round.round_label),
            round: Some(round),
            comment: None,
            detail: Some(detail),
            generated_note: None,
        })
    }

    pub fn list_review_comments(
        &self,
        input: ListReviewCommentsInput,
    ) -> Result<Vec<ReviewCommentItemRead>> {
        if input.review_round_id.trim().is_empty() {
            return Err(invalid_state("review_round_id is required"));
        }
        self.cache().list_review_comments(&input.review_round_id)
    }

    pub fn add_review_comment(
        &self,
        input: AddReviewCommentInput,
    ) -> Result<ReviewActionResultRead> {
        if input.review_round_id.trim().is_empty() {
            return Err(invalid_state("review_round_id is required"));
        }
        let reviewer_label = non_empty(input.reviewer_label)
            .ok_or_else(|| invalid_state("reviewer_label is required"))?;
        let comment_text =
            non_empty(input.comment_text).ok_or_else(|| invalid_state("comment_text is required"))?;
        let cache = self.cache();
        let round = cache.get_review_round_summary(&input.review_round_id)?;
        let comment_id = Uuid::new_v4().to_string();
        let created_at = chrono::Utc::now().to_rfc3339();
        let comment = cache.upsert_review_comment(
            &comment_id,
            &round.id,
            &round.paper_id,
            &reviewer_label,
            input.comment_code.as_deref().and_then(trimmed_optional),
            cache.next_review_comment_sort_order(&round.id)?,
            &comment_text,
            input.category.as_deref().and_then(trimmed_optional),
            &input
                .disposition
                .map(|value| validate_review_disposition(&value))
                .transpose()?
                .unwrap_or_else(default_review_disposition),
            input.response_summary.as_deref().and_then(trimmed_optional),
            input.action_note.as_deref().and_then(trimmed_optional),
            &created_at,
            &created_at,
        )?;
        let detail = cache.get_review_round_detail(&round.id)?;
        Ok(ReviewActionResultRead {
            message: format!("Added review comment for {}.", comment.reviewer_label),
            round: Some(detail.round.clone()),
            comment: Some(comment),
            detail: Some(detail),
            generated_note: None,
        })
    }

    pub fn update_review_comment(
        &self,
        input: crate::models::UpdateReviewCommentInput,
    ) -> Result<ReviewActionResultRead> {
        if input.comment_id.trim().is_empty() {
            return Err(invalid_state("comment_id is required"));
        }
        let cache = self.cache();
        let existing = cache.get_review_comment(&input.comment_id)?;
        let reviewer_label = match input.reviewer_label {
            Some(value) => {
                non_empty(value).ok_or_else(|| invalid_state("reviewer_label must not be empty"))?
            }
            None => existing.reviewer_label.clone(),
        };
        let comment_text = match input.comment_text {
            Some(value) => {
                non_empty(value).ok_or_else(|| invalid_state("comment_text must not be empty"))?
            }
            None => existing.comment_text.clone(),
        };
        let disposition = match input.disposition {
            Some(value) => validate_review_disposition(&value)?,
            None => existing.disposition.clone(),
        };
        let comment = cache.upsert_review_comment(
            &existing.id,
            &existing.review_round_id,
            &existing.paper_id,
            &reviewer_label,
            option_override(existing.comment_code.as_deref(), input.comment_code.as_deref()),
            existing.sort_order,
            &comment_text,
            option_override(existing.category.as_deref(), input.category.as_deref()),
            &disposition,
            option_override(
                existing.response_summary.as_deref(),
                input.response_summary.as_deref(),
            ),
            option_override(existing.action_note.as_deref(), input.action_note.as_deref()),
            &existing.created_at,
            &chrono::Utc::now().to_rfc3339(),
        )?;
        let detail = cache.get_review_round_detail(&existing.review_round_id)?;
        Ok(ReviewActionResultRead {
            message: format!("Updated review comment {}.", comment.id),
            round: Some(detail.round.clone()),
            comment: Some(comment),
            detail: Some(detail),
            generated_note: None,
        })
    }

    pub fn delete_review_comment(
        &self,
        input: DeleteReviewCommentInput,
    ) -> Result<ReviewActionResultRead> {
        if input.comment_id.trim().is_empty() {
            return Err(invalid_state("comment_id is required"));
        }
        let cache = self.cache();
        let existing = cache.get_review_comment(&input.comment_id)?;
        cache.delete_review_comment(&existing.id)?;
        let detail = cache.get_review_round_detail(&existing.review_round_id)?;
        Ok(ReviewActionResultRead {
            message: format!("Deleted review comment {}.", existing.id),
            round: Some(detail.round.clone()),
            comment: None,
            detail: Some(detail),
            generated_note: None,
        })
    }

    pub fn generate_reviewer_matrix_note(
        &self,
        input: ReviewRoundLookupInput,
    ) -> Result<ReviewActionResultRead> {
        self.generate_review_note(&input.review_round_id, "reviewer_matrix")
    }

    pub fn generate_response_letter_note(
        &self,
        input: ReviewRoundLookupInput,
    ) -> Result<ReviewActionResultRead> {
        self.generate_review_note(&input.review_round_id, "response_letter")
    }

    pub fn get_review_round_detail(
        &self,
        input: ReviewRoundLookupInput,
    ) -> Result<ReviewRoundDetailRead> {
        if input.review_round_id.trim().is_empty() {
            return Err(invalid_state("review_round_id is required"));
        }
        self.cache().get_review_round_detail(&input.review_round_id)
    }

    pub fn import_paper_attachments(
        &self,
        input: ImportPaperAttachmentsInput,
    ) -> Result<ImportPaperAttachmentsResponse> {
        if input.paper_id.trim().is_empty() {
            return Err(invalid_state("paper_id is required"));
        }
        if input.source_paths.is_empty() {
            return Err(invalid_state("source_paths must not be empty"));
        }
        let attachment_kind = validate_attachment_kind(&input.attachment_kind)?;
        let cache = self.cache();
        let root = self.ensure_workspace_root_ready()?;
        let paper = cache.get_paper_detail(&input.paper_id)?;
        let root_path = std::path::Path::new(root.root_path.as_deref().unwrap_or_default());
        let layout = ensure_paper_workspace_layout(root_path, &input.paper_id, &paper.title)?;
        cache.upsert_paper_workspace(
            &input.paper_id,
            &paper.title,
            &layout.paper_rel_path,
            Some(path_to_string(&layout.paper_abs_path).as_str()),
            true,
            None,
        )?;

        let imported_at = chrono::Utc::now().to_rfc3339();
        let mut results = Vec::new();
        let mut imported_any = false;
        let mut last_error_message = None;

        for source_path in input.source_paths {
            match self.import_single_attachment(
                &cache,
                &paper.id,
                &paper.title,
                &attachment_kind,
                &layout,
                &source_path,
                &imported_at,
            ) {
                Ok(result) => {
                    if result.status == "imported" {
                        imported_any = true;
                    }
                    results.push(result);
                }
                Err(error) => {
                    let message = format!("{error:#}");
                    last_error_message = Some(message.clone());
                    results.push(PaperAttachmentImportResultRead {
                        source_path,
                        status: "failed".to_string(),
                        message: Some(message),
                        attachment: None,
                    });
                }
            }
        }

        if imported_any {
            cache.touch_paper_workspace_imported_at(&paper.id, &imported_at)?;
            let imported_count = results
                .iter()
                .filter(|result| result.status == "imported")
                .count();
            self.record_local_work_activity(
                Some(&paper.id),
                "attachment_imported",
                format!(
                    "Imported {} {} attachment{} for \"{}\".",
                    imported_count,
                    attachment_kind,
                    if imported_count == 1 { "" } else { "s" },
                    paper.title,
                ),
                json!({
                    "attachment_kind": attachment_kind,
                    "imported_count": imported_count,
                }),
                &imported_at,
            )?;
        }
        let workspace = self.refresh_paper_workspace(&paper.id)?;
        if results.iter().all(|result| result.status == "failed") {
            return Err(invalid_state(
                last_error_message.unwrap_or_else(|| "attachment import failed".to_string()),
            ));
        }
        Ok(ImportPaperAttachmentsResponse { workspace, results })
    }

    pub fn refresh_paper_workspace(&self, paper_id: &str) -> Result<PaperWorkspaceRead> {
        if paper_id.trim().is_empty() {
            return Err(invalid_state("paper_id is required"));
        }
        let cache = self.cache();
        let root = self.get_workspace_status()?;
        let root_path = root.root_path.as_deref();
        let paper_title = cache.get_paper_detail(paper_id)?.title;
        let fallback_rel_path = build_workspace_layout(
            std::path::Path::new(root_path.unwrap_or(".")),
            paper_id,
        )
        .paper_rel_path;
        let current = cache.get_paper_workspace(paper_id).unwrap_or(PaperWorkspaceRead {
            paper_id: paper_id.to_string(),
            paper_title: paper_title.clone(),
            workspace_rel_path: fallback_rel_path,
            workspace_abs_path: workspace_root_rebind_path(root_path, &format!("papers/{paper_id}")),
            workspace_ready: false,
            attachment_count: 0,
            last_imported_at: None,
        });
        let workspace_abs_path =
            workspace_root_rebind_path(root_path, &current.workspace_rel_path);
        let workspace_ready = paper_workspace_ready_for_path(workspace_abs_path.as_deref());
        cache.upsert_paper_workspace(
            paper_id,
            &paper_title,
            &current.workspace_rel_path,
            workspace_abs_path.as_deref(),
            workspace_ready,
            current.last_imported_at.as_deref(),
        )?;
        cache.refresh_attachment_statuses(root_path, paper_id)?;
        cache.refresh_note_statuses(root_path, paper_id)?;
        cache.get_paper_workspace(paper_id)
    }

    pub fn connect_with<A: SyncBackendApi>(
        &self,
        input: ConnectDeviceInput,
        api: &A,
    ) -> Result<ConnectDeviceResponse> {
        let base_url = normalize_base_url(&input.base_url)?;
        let remote = api.sync_me()?;

        let cache = self.cache();
        let current = cache.sync_state_record()?;
        let should_reset = current.device_id.as_deref() != Some(remote.device.id.as_str())
            || current.base_url.as_deref() != Some(base_url.as_str())
            || current.user_id.as_deref() != Some(remote.user.id.as_str());

        if should_reset {
            cache.reset_local_cache()?;
        }

        self.secret_store().save_device_token(input.device_token.trim())?;
        let effective_display_name = input
            .device_display_name
            .filter(|value| !value.trim().is_empty())
            .unwrap_or_else(|| remote.device.display_name.clone());
        cache.upsert_connection(
            &base_url,
            &remote.device.id,
            &effective_display_name,
            &remote.user.id,
            &remote.user.name,
            remote.user.email.as_deref(),
            remote.user.field.as_deref(),
        )?;
        let sync = self.sync_with(api)?;
        let connection = sync
            .sync_status
            .current_user_summary
            .clone()
            .ok_or_else(|| invalid_state("connected desktop state is missing user summary"))?;
        Ok(ConnectDeviceResponse {
            sync_status: sync.sync_status,
            connection,
            today_overview: sync.today_overview,
        })
    }

    pub fn sync_now(&self) -> Result<SyncNowResponse> {
        let (base_url, token) = self.load_connection()?;
        let api = ReqwestSyncBackendApi::new(base_url, token)?;
        self.sync_with(&api)
    }

    pub fn queue_paper_patch(&self, input: QueuePaperPatchInput) -> Result<WriteActionResultRead> {
        if input.paper_id.trim().is_empty() {
            return Err(invalid_state("paper_id is required"));
        }
        if input.priority.is_some_and(|value| value < 1) {
            return Err(invalid_state("priority must be at least 1"));
        }

        let mut payload = serde_json::Map::new();
        if let Some(stage) = input.stage.and_then(non_empty) {
            payload.insert("stage".to_string(), Value::String(stage));
        }
        if let Some(venue) = input.venue {
            payload.insert("venue".to_string(), value_or_null(venue));
        }
        if let Some(next_action) = input.next_action {
            payload.insert("next_action".to_string(), value_or_null(next_action));
        }
        if let Some(blocker) = input.blocker {
            payload.insert("blocker".to_string(), value_or_null(blocker));
        }
        if let Some(priority) = input.priority {
            payload.insert("priority".to_string(), Value::from(priority));
        }
        if let Some(last_touch_at) = input.last_touch_at {
            payload.insert("last_touch_at".to_string(), value_or_null(last_touch_at));
        }
        if payload.is_empty() {
            return Err(invalid_state("paper.patch requires at least one field"));
        }

        self.cache().get_paper_detail(&input.paper_id)?;
        self.queue_mutation_and_maybe_sync(
            "paper.patch",
            "paper_profile",
            Some(input.paper_id),
            Value::Object(payload),
        )
    }

    pub fn queue_progress_event_create(
        &self,
        input: QueueProgressEventCreateInput,
    ) -> Result<WriteActionResultRead> {
        if input.paper_id.trim().is_empty() {
            return Err(invalid_state("paper_id is required"));
        }
        if input.stage.trim().is_empty() {
            return Err(invalid_state("stage is required"));
        }
        if input.happened_at.trim().is_empty() {
            return Err(invalid_state("happened_at is required"));
        }
        if input.summary.trim().is_empty() {
            return Err(invalid_state("summary is required"));
        }

        self.cache().get_paper_detail(&input.paper_id)?;
        self.queue_mutation_and_maybe_sync(
            "progress_event.create",
            "progress_event",
            Some(input.paper_id),
            json!({
                "stage": input.stage.trim(),
                "happened_at": input.happened_at.trim(),
                "summary": input.summary.trim(),
                "owner": input.owner.and_then(non_empty),
            }),
        )
    }

    pub fn queue_subscription_policy_patch(
        &self,
        input: QueueSubscriptionPolicyPatchInput,
    ) -> Result<WriteActionResultRead> {
        if input.subscription_policy_id.trim().is_empty() {
            return Err(invalid_state("subscription_policy_id is required"));
        }
        if input.frequency_cap.is_some_and(|value| value < 1) {
            return Err(invalid_state("frequencyCap must be at least 1"));
        }

        let mut payload = serde_json::Map::new();
        if let Some(enabled) = input.enabled {
            payload.insert("enabled".to_string(), Value::Bool(enabled));
        }
        if let Some(quiet_hours) = input.quiet_hours {
            if !quiet_hours.is_object() && !quiet_hours.is_null() {
                return Err(invalid_state("quietHours must be an object or null"));
            }
            payload.insert("quiet_hours".to_string(), quiet_hours);
        }
        if let Some(frequency_cap) = input.frequency_cap {
            payload.insert("frequency_cap".to_string(), Value::from(frequency_cap));
        }
        if let Some(policy) = input.policy {
            if !policy.is_object() && !policy.is_null() {
                return Err(invalid_state("policy must be an object or null"));
            }
            payload.insert("policy".to_string(), policy);
        }
        if payload.is_empty() {
            return Err(invalid_state(
                "subscription_policy.patch requires at least one field",
            ));
        }

        let policy_exists = self
            .cache()
            .list_subscription_policies()?
            .into_iter()
            .any(|policy| policy.id == input.subscription_policy_id);
        if !policy_exists {
            return Err(invalid_state(format!(
                "subscription policy {} is not cached",
                input.subscription_policy_id
            )));
        }

        self.queue_mutation_and_maybe_sync(
            "subscription_policy.patch",
            "subscription_policy",
            Some(input.subscription_policy_id),
            Value::Object(payload),
        )
    }

    pub fn disconnect_device(&self) -> Result<SyncStatusRead> {
        self.secret_store().clear()?;
        self.cache().disconnect()?;
        self.get_sync_status()
    }

    pub fn clear_local_cache(&self) -> Result<SyncStatusRead> {
        self.cache().reset_local_cache()?;
        self.get_sync_status()
    }

    pub fn sync_with<A: SyncBackendApi>(&self, api: &A) -> Result<SyncNowResponse> {
        let cache = self.cache();
        let state = cache.sync_state_record()?;
        if !state.connected {
            return Err(invalid_state("desktop is not connected"));
        }

        let sync_outcome = (|| -> Result<(PushOutcomeSummary, i64, i64, i64)> {
            cache.recover_inflight_mutations()?;

            let pending_mutations = cache.pending_outbox_batch()?;
            let push_summary = if pending_mutations.is_empty() {
                PushOutcomeSummary::default()
            } else {
                let client_mutation_ids = pending_mutations
                    .iter()
                    .map(|mutation| mutation.client_mutation_id.clone())
                    .collect::<Vec<_>>();
                cache.mark_mutations_sending(&client_mutation_ids)?;
                let response = api.push(&RemoteSyncPushRequest {
                    mutations: pending_mutations
                        .iter()
                        .map(|mutation| RemoteSyncMutationRequest {
                            client_mutation_id: mutation.client_mutation_id.clone(),
                            mutation_type: mutation.mutation_type.clone(),
                            resource_type: mutation.resource_type.clone(),
                            resource_id: mutation.resource_id.clone(),
                            payload: mutation.payload.clone(),
                        })
                        .collect(),
                })?;
                cache.apply_push_results(&response.results)?
            };

            let mut pages_fetched = 0_i64;
            let mut events_applied = 0_i64;
            let mut next_after_sequence = state.last_event_sequence;
            let mut final_sequence = state.last_event_sequence;

            loop {
                let page = api.feed(next_after_sequence, FEED_PAGE_LIMIT)?;
                if page.events.is_empty() {
                    break;
                }
                cache.apply_event_batch(&page.events)?;
                events_applied += page.events.len() as i64;
                pages_fetched += 1;
                final_sequence = page.next_after_sequence;
                next_after_sequence = page.next_after_sequence;
                if !page.has_more {
                    break;
                }
            }

            let acknowledged_sequence = if final_sequence > state.last_event_sequence {
                let ack = api.ack(final_sequence)?;
                cache.update_after_ack(ack.last_event_sequence, ack.last_synced_at.as_deref())?;
                ack.last_event_sequence
            } else {
                state.last_event_sequence
            };

            Ok((push_summary, pages_fetched, events_applied, acknowledged_sequence))
        })();

        let (push_summary, pages_fetched, events_applied, acknowledged_sequence) = match sync_outcome
        {
            Ok(result) => result,
            Err(error) => {
                let message = format!("{error:#}");
                let _ = cache.recover_inflight_mutations();
                let _ = cache.mark_sync_error(&message);
                return Err(error);
            }
        };

        cache.clear_sync_error()?;
        let outbox_stats = cache.outbox_stats()?;
        let token_present = self.secret_store().load_device_token()?.is_some();
        Ok(SyncNowResponse {
            sync_status: cache.sync_status(token_present)?,
            pushed_count: push_summary.pushed_count,
            applied_count: push_summary.applied_count,
            duplicate_count: push_summary.duplicate_count,
            failed_count: push_summary.failed_count,
            pages_fetched,
            events_applied,
            acknowledged_sequence,
            pending_mutation_count: outbox_stats.pending_count,
            failed_mutation_count: outbox_stats.failed_count,
            today_overview: cache.read_today_overview()?,
        })
    }

    fn queue_mutation_and_maybe_sync(
        &self,
        mutation_type: &str,
        resource_type: &str,
        resource_id: Option<String>,
        payload: Value,
    ) -> Result<WriteActionResultRead> {
        self.ensure_local_connection_ready()?;
        let mutation_id = Uuid::new_v4().to_string();
        let client_mutation_id = format!("desktop-{mutation_id}");
        let cache = self.cache();
        cache.enqueue_mutation(
            &mutation_id,
            &client_mutation_id,
            mutation_type,
            resource_type,
            resource_id.as_deref(),
            &payload,
        )?;

        let sync_attempt = self.try_sync_immediately();
        let mutation = cache.get_mutation(&client_mutation_id)?;
        let outbox_stats = cache.outbox_stats()?;
        let sync_status = self.get_sync_status()?;
        let (sync_attempted, sync_succeeded, sync_error) = match sync_attempt {
            Ok(Some(_)) => (true, true, None),
            Ok(None) => (false, false, None),
            Err(error) => (true, false, Some(error)),
        };

        Ok(WriteActionResultRead {
            mutation,
            sync_attempted,
            sync_succeeded,
            sync_error,
            sync_status,
            pending_mutation_count: outbox_stats.pending_count,
            failed_mutation_count: outbox_stats.failed_count,
        })
    }

    fn record_local_work_activity(
        &self,
        paper_id: Option<&str>,
        activity_type: &str,
        summary: String,
        metadata: Value,
        happened_at: &str,
    ) -> Result<()> {
        if self.get_sync_status()?.current_user_summary.is_none() {
            return Ok(());
        }
        let mutation_id = Uuid::new_v4().to_string();
        let client_mutation_id = format!("desktop-{mutation_id}");
        let payload = json!({
            "paper_id": paper_id,
            "activity_type": activity_type,
            "summary": summary,
            "metadata": metadata,
            "happened_at": happened_at,
        });
        self.cache().enqueue_mutation(
            &mutation_id,
            &client_mutation_id,
            "work_activity.record",
            "work_activity_event",
            paper_id,
            &payload,
        )?;
        Ok(())
    }

    fn try_sync_immediately(&self) -> Result<Option<SyncNowResponse>, String> {
        match self.load_connection() {
            Ok((base_url, token)) => {
                let api = ReqwestSyncBackendApi::new(base_url, token).map_err(error_to_string)?;
                self.sync_with(&api).map(Some).map_err(error_to_string)
            }
            Err(_) => Ok(None),
        }
    }

    fn ensure_local_connection_ready(&self) -> Result<UserConnectionRead> {
        self.get_sync_status()?
            .current_user_summary
            .ok_or_else(|| invalid_state("desktop must be connected before queueing writes"))
    }

    fn load_connection(&self) -> Result<(String, String)> {
        let state = self.cache().sync_state_record()?;
        let base_url = state
            .base_url
            .ok_or_else(|| invalid_state("desktop base URL is not configured"))?;
        let token = self
            .secret_store()
            .load_device_token()?
            .ok_or_else(|| invalid_state("desktop device token is not configured"))?;
        Ok((base_url, token))
    }

    fn cache(&self) -> LocalCache {
        LocalCache::new(self.paths.cache_db_path.clone())
    }

    fn secret_store(&self) -> FileSecretStore {
        FileSecretStore::new(self.paths.secret_store_path.clone())
    }

    fn ensure_workspace_root_ready(&self) -> Result<WorkspaceRootRecord> {
        let _ = self.get_workspace_status()?;
        let root = self.cache().workspace_root_record()?;
        if root.status != "ready" {
            return Err(invalid_state(
                root.last_error
                    .unwrap_or_else(|| "workspace root is not configured and ready".to_string()),
            ));
        }
        Ok(root)
    }

    fn generate_review_note(
        &self,
        review_round_id: &str,
        template_kind: &str,
    ) -> Result<ReviewActionResultRead> {
        if review_round_id.trim().is_empty() {
            return Err(invalid_state("review_round_id is required"));
        }
        let cache = self.cache();
        let detail = cache.get_review_round_detail(review_round_id)?;
        let paper = cache.get_paper_detail(&detail.round.paper_id)?;
        let root = self.ensure_workspace_root_ready()?;
        let root_path = std::path::Path::new(root.root_path.as_deref().unwrap_or_default());
        let layout = ensure_paper_workspace_layout(root_path, &paper.id, &paper.title)?;
        cache.upsert_paper_workspace(
            &paper.id,
            &paper.title,
            &layout.paper_rel_path,
            Some(path_to_string(&layout.paper_abs_path).as_str()),
            true,
            paper.workspace.last_imported_at.as_deref(),
        )?;

        let rendered = match template_kind {
            "reviewer_matrix" => {
                render_reviewer_matrix_note(&build_note_context(&paper), &detail.round, &detail.comments)
            }
            "response_letter" => {
                render_response_letter_note(&build_note_context(&paper), &detail.round, &detail.comments)
            }
            _ => {
                return Err(invalid_state(format!(
                    "unsupported review note template kind {template_kind}"
                )));
            }
        };

        let note_id = match template_kind {
            "reviewer_matrix" => detail.round.generated_matrix_note_id.clone(),
            "response_letter" => detail.round.generated_response_note_id.clone(),
            _ => None,
        };

        let generated_note = if let Some(existing_note_id) = note_id {
            self.update_generated_review_note(
                &cache,
                &paper.id,
                &existing_note_id,
                &rendered.title,
                &rendered.content,
                &rendered.template_kind,
            )
            .or_else(|_| {
                self.create_generated_review_note(
                    &cache,
                    &paper.id,
                    &layout,
                    &rendered.title,
                    &rendered.content,
                    &rendered.template_kind,
                )
            })?
        } else {
            self.create_generated_review_note(
                &cache,
                &paper.id,
                &layout,
                &rendered.title,
                &rendered.content,
                &rendered.template_kind,
            )?
        };

        let refreshed_round = cache.get_review_round_summary(review_round_id)?;
        let updated_round = cache.upsert_review_round(
            &refreshed_round.id,
            &refreshed_round.paper_id,
            &refreshed_round.round_label,
            refreshed_round.venue.as_deref(),
            refreshed_round.decision_label.as_deref(),
            &refreshed_round.status,
            &refreshed_round.source_mode,
            refreshed_round.reviewer_count,
            if template_kind == "response_letter" {
                Some(generated_note.note_id.as_str())
            } else {
                refreshed_round.generated_response_note_id.as_deref()
            },
            if template_kind == "reviewer_matrix" {
                Some(generated_note.note_id.as_str())
            } else {
                refreshed_round.generated_matrix_note_id.as_deref()
            },
            &refreshed_round.created_at,
            &chrono::Utc::now().to_rfc3339(),
        )?;
        let updated_detail = cache.get_review_round_detail(review_round_id)?;
        let activity_type = match template_kind {
            "reviewer_matrix" => "reviewer_matrix_generated",
            "response_letter" => "response_letter_generated",
            _ => unreachable!("template kind already validated"),
        };
        let activity_happened_at = chrono::Utc::now().to_rfc3339();
        self.record_local_work_activity(
            Some(&paper.id),
            activity_type,
            format!("Generated {} for {}.", rendered.title, updated_round.round_label),
            json!({
                "review_round_id": updated_round.id,
                "note_id": generated_note.note_id,
                "template_kind": template_kind,
            }),
            &activity_happened_at,
        )?;
        Ok(ReviewActionResultRead {
            message: format!("Generated {} note for {}.", rendered.title, updated_round.round_label),
            round: Some(updated_round),
            comment: None,
            detail: Some(updated_detail),
            generated_note: Some(generated_note),
        })
    }

    fn create_generated_review_note(
        &self,
        cache: &LocalCache,
        paper_id: &str,
        layout: &crate::workspace::WorkspaceLayoutPaths,
        title: &str,
        content: &str,
        template_kind: &str,
    ) -> Result<crate::models::GeneratedReviewNoteRead> {
        let created_at = chrono::Utc::now().to_rfc3339();
        let note_id = Uuid::new_v4().to_string();
        let prepared = prepare_generated_note(
            layout,
            template_kind,
            title,
            content,
            &note_id,
            &created_at,
        )?;
        let file_stats = write_note_file(&prepared.absolute_path, &prepared.content)?;
        let status = note_status_for_path(Some(&prepared.absolute_path));
        cache.upsert_paper_note(
            &prepared.note_id,
            paper_id,
            &prepared.template_kind,
            &prepared.title,
            &prepared.file_name,
            &prepared.relative_path,
            Some(&prepared.absolute_path),
            "markdown",
            &prepared.source_mode,
            &status,
            file_stats.size_bytes,
            file_stats.sha256.as_deref(),
            &prepared.created_at,
            &prepared.created_at,
            Some(&prepared.created_at),
        )?;
        cache.generated_review_note(Some(&prepared.note_id), template_kind)?
            .ok_or_else(|| invalid_state("generated note was not indexed"))
    }

    fn update_generated_review_note(
        &self,
        cache: &LocalCache,
        paper_id: &str,
        note_id: &str,
        title: &str,
        content: &str,
        template_kind: &str,
    ) -> Result<crate::models::GeneratedReviewNoteRead> {
        let existing = cache.get_paper_note_summary(note_id)?;
        let absolute_path = existing.absolute_path.clone().ok_or_else(|| {
            invalid_state("generated note path is not available because the workspace root is missing")
        })?;
        let updated_at = chrono::Utc::now().to_rfc3339();
        let file_stats = write_note_file(&absolute_path, content)?;
        let status = note_status_for_path(Some(&absolute_path));
        cache.upsert_paper_note(
            &existing.id,
            paper_id,
            template_kind,
            title,
            &existing.file_name,
            &existing.relative_path,
            Some(&absolute_path),
            "markdown",
            "generated",
            &status,
            file_stats.size_bytes,
            file_stats.sha256.as_deref(),
            &existing.created_at,
            &updated_at,
            Some(&updated_at),
        )?;
        cache.generated_review_note(Some(&existing.id), template_kind)?
            .ok_or_else(|| invalid_state("generated note was not indexed"))
    }

    fn import_single_attachment(
        &self,
        cache: &LocalCache,
        paper_id: &str,
        paper_title: &str,
        attachment_kind: &str,
        layout: &crate::workspace::WorkspaceLayoutPaths,
        source_path: &str,
        imported_at: &str,
    ) -> Result<PaperAttachmentImportResultRead> {
        let metadata = collect_file_import_metadata(source_path)?;
        if let Some(duplicate) =
            cache.find_duplicate_attachment(paper_id, metadata.sha256.as_deref(), metadata.size_bytes)?
        {
            if should_treat_as_duplicate(
                duplicate.sha256.as_deref(),
                duplicate.size_bytes,
                &duplicate.original_file_name,
                &metadata,
            ) {
                let attachment = cache.get_attachment_by_id(&duplicate.attachment_id)?;
                return Ok(PaperAttachmentImportResultRead {
                    source_path: metadata.source_path.clone(),
                    status: "duplicate".to_string(),
                    message: Some(format!(
                        "duplicate attachment already indexed for {paper_title}"
                    )),
                    attachment: Some(attachment),
                });
            }
        }

        let prepared = prepare_attachment_import(layout, &metadata, imported_at)?;
        crate::workspace::copy_managed_attachment(&prepared)?;
        let status = attachment_status_for_path(Some(&prepared.absolute_path));
        cache.upsert_attachment(
            &prepared.attachment_id,
            paper_id,
            attachment_kind,
            "managed_copy",
            &metadata.original_file_name,
            &prepared.stored_file_name,
            metadata.file_extension.as_deref(),
            &prepared.relative_path,
            Some(prepared.absolute_path.as_str()),
            &metadata.source_path,
            metadata.size_bytes,
            metadata.mime_type.as_deref(),
            metadata.sha256.as_deref(),
            &status,
            imported_at,
            None,
        )?;

        Ok(PaperAttachmentImportResultRead {
            source_path: metadata.source_path,
            status: "imported".to_string(),
            message: None,
            attachment: Some(cache.get_attachment_by_id(&prepared.attachment_id)?),
        })
    }
}

fn normalize_base_url(value: &str) -> Result<String> {
    let trimmed = value.trim().trim_end_matches('/');
    if trimmed.is_empty() {
        return Err(invalid_state("backend base URL is required"));
    }
    Ok(trimmed.to_string())
}

fn non_empty(value: impl Into<String>) -> Option<String> {
    let value = value.into();
    let trimmed = value.trim();
    if trimmed.is_empty() {
        None
    } else {
        Some(trimmed.to_string())
    }
}

fn trimmed_optional(value: &str) -> Option<&str> {
    let trimmed = value.trim();
    if trimmed.is_empty() {
        None
    } else {
        Some(trimmed)
    }
}

fn option_override<'a>(current: Option<&'a str>, incoming: Option<&'a str>) -> Option<&'a str> {
    match incoming {
        Some(value) => trimmed_optional(value),
        None => current,
    }
}

fn value_or_null(value: String) -> Value {
    match non_empty(value) {
        Some(text) => Value::String(text),
        None => Value::Null,
    }
}

fn error_to_string(error: anyhow::Error) -> String {
    format!("{error:#}")
}

fn build_note_context(paper: &PaperDetailRead) -> NoteTemplateContext {
    NoteTemplateContext {
        paper_id: paper.id.clone(),
        paper_title: paper.title.clone(),
        stage: paper.stage.clone(),
        venue: paper.venue.clone(),
        next_action: paper.next_action.clone(),
        blocker: paper.blocker.clone(),
    }
}

#[cfg(test)]
mod tests {
    use std::{cell::RefCell, path::PathBuf, rc::Rc};

    use serde_json::json;
    use tempfile::tempdir;

    use super::{ChooseWorkspaceRootInput, ConnectDeviceInput, DesktopPaths, DesktopService, ListPapersInput};
    use crate::models::{
        AddReviewCommentInput, CreateBlankPaperNoteInput, CreatePaperNoteFromTemplateInput,
        CreateReviewRoundInput, DeleteReviewCommentInput, ImportPaperAttachmentsInput,
        QueuePaperPatchInput, QueueProgressEventCreateInput, QueueSubscriptionPolicyPatchInput,
        ReviewRoundLookupInput, SavePaperNoteInput, UpdateReviewCommentInput,
        RemoteSyncAck, RemoteSyncDevice, RemoteSyncEvent, RemoteSyncFeed, RemoteSyncMe, RemoteSyncMutationResult,
        RemoteSyncPushRequest, RemoteSyncPushResponse, RemoteSyncUser,
    };
    use crate::sync_client::SyncBackendApi;

    #[derive(Clone, Default)]
    struct FakeApi {
        sync_me_result: Rc<RefCell<Option<anyhow::Result<RemoteSyncMe>>>>,
        push_results: Rc<RefCell<Vec<anyhow::Result<RemoteSyncPushResponse>>>>,
        feed_results: Rc<RefCell<Vec<anyhow::Result<RemoteSyncFeed>>>>,
        ack_calls: Rc<RefCell<Vec<i64>>>,
        call_log: Rc<RefCell<Vec<String>>>,
        pushed_batches: Rc<RefCell<Vec<RemoteSyncPushRequest>>>,
    }

    impl SyncBackendApi for FakeApi {
        fn sync_me(&self) -> anyhow::Result<RemoteSyncMe> {
            self.call_log.borrow_mut().push("sync_me".to_string());
            self.sync_me_result
                .borrow_mut()
                .take()
                .unwrap_or_else(|| Err(anyhow::anyhow!("missing sync_me result")))
        }

        fn push(&self, payload: &RemoteSyncPushRequest) -> anyhow::Result<RemoteSyncPushResponse> {
            self.call_log.borrow_mut().push("push".to_string());
            self.pushed_batches.borrow_mut().push(payload.clone());
            if self.push_results.borrow().is_empty() {
                return Ok(RemoteSyncPushResponse { results: Vec::new() });
            }
            self.push_results.borrow_mut().remove(0)
        }

        fn feed(&self, after_sequence: i64, _limit: usize) -> anyhow::Result<RemoteSyncFeed> {
            self.call_log
                .borrow_mut()
                .push(format!("feed:{after_sequence}"));
            if self.feed_results.borrow().is_empty() {
                return Ok(RemoteSyncFeed {
                    events: Vec::new(),
                    next_after_sequence: after_sequence,
                    has_more: false,
                });
            }
            self.feed_results.borrow_mut().remove(0)
        }

        fn ack(&self, last_event_sequence: i64) -> anyhow::Result<RemoteSyncAck> {
            self.call_log.borrow_mut().push("ack".to_string());
            self.ack_calls.borrow_mut().push(last_event_sequence);
            Ok(RemoteSyncAck {
                last_event_sequence,
                last_synced_at: Some("2026-04-15T00:00:00Z".to_string()),
            })
        }
    }

    fn service() -> DesktopService {
        let dir = tempdir().unwrap();
        let root = dir.path().to_path_buf();
        std::mem::forget(dir);
        DesktopService::new(DesktopPaths {
            app_data_dir: root.clone(),
            cache_db_path: root.join("desktop.sqlite3"),
            secret_store_path: root.join("device-secret.json"),
        })
        .unwrap()
    }

    fn new_temp_path() -> PathBuf {
        let dir = tempdir().unwrap();
        let path = dir.path().to_path_buf();
        std::mem::forget(dir);
        path
    }

    fn connect(service: &DesktopService, api: &FakeApi, feed_results: Vec<anyhow::Result<RemoteSyncFeed>>) {
        api.sync_me_result.replace(Some(Ok(RemoteSyncMe {
            device: RemoteSyncDevice {
                id: "device-1".to_string(),
                user_id: "user-1".to_string(),
                client_type: "desktop".to_string(),
                display_name: "Primary Desktop".to_string(),
                is_active: true,
                last_seen_at: None,
                created_at: "2026-04-15T00:00:00Z".to_string(),
                updated_at: "2026-04-15T00:00:00Z".to_string(),
                last_event_sequence: 0,
                last_synced_at: None,
            },
            user: RemoteSyncUser {
                id: "user-1".to_string(),
                name: "Desktop User".to_string(),
                email: Some("desktop@example.com".to_string()),
                field: Some("Materials".to_string()),
            },
        })));
        api.feed_results.replace(feed_results);
        service
            .connect_with(
                ConnectDeviceInput {
                    base_url: "http://localhost:8000".to_string(),
                    device_token: "good-token".to_string(),
                    device_display_name: Some("Primary Desktop".to_string()),
                },
                api,
            )
            .unwrap();
    }

    fn paper_event(stage: &str, sequence: i64) -> RemoteSyncEvent {
        RemoteSyncEvent {
            id: format!("evt-paper-{sequence}"),
            sequence,
            user_id: "user-1".to_string(),
            entity_type: "paper_profile".to_string(),
            entity_id: "paper-1".to_string(),
            event_type: "updated".to_string(),
            event_source: "sync_push".to_string(),
            occurred_at: "2026-04-15T00:00:00Z".to_string(),
            payload: serde_json::json!({
                "id": "paper-1",
                "user_id": "user-1",
                "title": "Desktop Paper",
                "type": "revision",
                "stage": stage,
                "venue": "JOM",
                "priority": 4,
                "next_action": "Prepare response",
                "blocker": null,
                "last_touch_at": "2026-04-15T00:00:00Z",
                "updated_at": "2026-04-15T00:00:00Z",
                "identifiers": {},
                "source_links": []
            }),
        }
    }

    fn policy_event(enabled: bool, frequency_cap: i64, sequence: i64) -> RemoteSyncEvent {
        RemoteSyncEvent {
            id: format!("evt-policy-{sequence}"),
            sequence,
            user_id: "user-1".to_string(),
            entity_type: "subscription_policy".to_string(),
            entity_id: "policy-1".to_string(),
            event_type: "updated".to_string(),
            event_source: "sync_push".to_string(),
            occurred_at: "2026-04-15T00:00:00Z".to_string(),
            payload: serde_json::json!({
                "id": "policy-1",
                "user_id": "user-1",
                "channel": "in_app",
                "enabled": enabled,
                "frequency": "daily",
                "quiet_hours": {"start": "22:00", "end": "07:00"},
                "frequency_cap": frequency_cap,
                "policy": {"stale_days": 10},
                "updated_at": "2026-04-15T00:00:00Z"
            }),
        }
    }

    fn progress_event(sequence: i64) -> RemoteSyncEvent {
        RemoteSyncEvent {
            id: format!("evt-progress-{sequence}"),
            sequence,
            user_id: "user-1".to_string(),
            entity_type: "progress_event".to_string(),
            entity_id: format!("progress-{sequence}"),
            event_type: "created".to_string(),
            event_source: "sync_push".to_string(),
            occurred_at: "2026-04-15T00:00:00Z".to_string(),
            payload: serde_json::json!({
                "id": format!("progress-{sequence}"),
                "paper_id": "paper-1",
                "stage": "revision",
                "happened_at": "2026-04-15T00:00:00Z",
                "summary": "Submitted revision",
                "owner": "desktop",
                "evidence_links": []
            }),
        }
    }

    fn digest_event(sequence: i64) -> RemoteSyncEvent {
        RemoteSyncEvent {
            id: format!("evt-digest-{sequence}"),
            sequence,
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
        }
    }

    fn work_activity_mutations(service: &DesktopService) -> Vec<crate::models::PendingMutationRead> {
        service
            .list_pending_mutations()
            .unwrap()
            .into_iter()
            .filter(|mutation| mutation.mutation_type == "work_activity.record")
            .collect()
    }

    #[test]
    fn connect_device_rejects_invalid_token_path_with_mocked_backend() {
        let service = service();
        let api = FakeApi {
            sync_me_result: Rc::new(RefCell::new(Some(Err(anyhow::anyhow!(
                "sync authentication failed"
            ))))),
            ..FakeApi::default()
        };

        let result = service.connect_with(
            ConnectDeviceInput {
                base_url: "http://localhost:8000".to_string(),
                device_token: "bad-token".to_string(),
                device_display_name: Some("Primary Desktop".to_string()),
            },
            &api,
        );

        assert!(result.is_err());
    }

    #[test]
    fn queue_paper_patch_creates_outbox_row() {
        let service = service();
        let api = FakeApi {
            push_results: Rc::new(RefCell::new(vec![Err(anyhow::anyhow!("network down"))])),
            ..FakeApi::default()
        };
        connect(
            &service,
            &api,
            vec![Ok(RemoteSyncFeed {
                events: vec![paper_event("revision", 1)],
                next_after_sequence: 1,
                has_more: false,
            })],
        );

        let result = service
            .queue_paper_patch(QueuePaperPatchInput {
                paper_id: "paper-1".to_string(),
                stage: Some("under_review".to_string()),
                venue: None,
                next_action: None,
                blocker: None,
                priority: None,
                last_touch_at: None,
            })
            .unwrap();

        assert_eq!(result.mutation.mutation_type, "paper.patch");
        assert_eq!(service.list_pending_mutations().unwrap().len(), 1);
    }

    #[test]
    fn queue_progress_event_create_creates_outbox_row() {
        let service = service();
        let api = FakeApi {
            push_results: Rc::new(RefCell::new(vec![Err(anyhow::anyhow!("network down"))])),
            ..FakeApi::default()
        };
        connect(
            &service,
            &api,
            vec![Ok(RemoteSyncFeed {
                events: vec![paper_event("revision", 1)],
                next_after_sequence: 1,
                has_more: false,
            })],
        );

        let result = service
            .queue_progress_event_create(QueueProgressEventCreateInput {
                paper_id: "paper-1".to_string(),
                stage: "revision".to_string(),
                happened_at: "2026-04-15T00:00:00Z".to_string(),
                summary: "Queued from desktop".to_string(),
                owner: Some("desktop".to_string()),
            })
            .unwrap();

        assert_eq!(result.mutation.mutation_type, "progress_event.create");
        assert_eq!(service.list_pending_mutations().unwrap().len(), 1);
    }

    #[test]
    fn queue_subscription_policy_patch_creates_outbox_row() {
        let service = service();
        let api = FakeApi {
            push_results: Rc::new(RefCell::new(vec![Err(anyhow::anyhow!("network down"))])),
            ..FakeApi::default()
        };
        connect(
            &service,
            &api,
            vec![Ok(RemoteSyncFeed {
                events: vec![policy_event(true, 3, 1)],
                next_after_sequence: 1,
                has_more: false,
            })],
        );

        let result = service
            .queue_subscription_policy_patch(QueueSubscriptionPolicyPatchInput {
                subscription_policy_id: "policy-1".to_string(),
                enabled: Some(false),
                quiet_hours: None,
                frequency_cap: Some(5),
                policy: None,
            })
            .unwrap();

        assert_eq!(result.mutation.mutation_type, "subscription_policy.patch");
        assert_eq!(service.list_pending_mutations().unwrap().len(), 1);
    }

    #[test]
    fn sync_now_pushes_before_pulling_feed() {
        let service = service();
        let api = FakeApi {
            push_results: Rc::new(RefCell::new(vec![Ok(RemoteSyncPushResponse {
                results: vec![RemoteSyncMutationResult {
                    client_mutation_id: "desktop-seeded".to_string(),
                    status: "applied".to_string(),
                    error_message: None,
                    resulting_event_sequence: Some(2),
                }],
            })])),
            ..FakeApi::default()
        };
        connect(
            &service,
            &api,
            vec![Ok(RemoteSyncFeed {
                events: vec![paper_event("revision", 1)],
                next_after_sequence: 1,
                has_more: false,
            })],
        );

        service
            .cache()
            .enqueue_mutation(
                "seeded",
                "desktop-seeded",
                "paper.patch",
                "paper_profile",
                Some("paper-1"),
                &json!({"stage": "under_review"}),
            )
            .unwrap();
        api.feed_results.replace(vec![Ok(RemoteSyncFeed {
            events: vec![paper_event("under_review", 2)],
            next_after_sequence: 2,
            has_more: false,
        })]);

        let response = service.sync_with(&api).unwrap();

        assert_eq!(response.pushed_count, 1);
        assert_eq!(
            api.call_log.borrow().last().map(String::as_str),
            Some("ack")
        );
        let log = api.call_log.borrow().clone();
        let push_idx = log.iter().rposition(|entry| entry == "push").unwrap();
        let feed_idx = log.iter().rposition(|entry| entry.starts_with("feed:1")).unwrap();
        let ack_idx = log.iter().rposition(|entry| entry == "ack").unwrap();
        assert!(push_idx < feed_idx);
        assert!(feed_idx < ack_idx);
    }

    #[test]
    fn duplicate_mutation_result_is_not_fatal() {
        let service = service();
        let api = FakeApi {
            push_results: Rc::new(RefCell::new(vec![Ok(RemoteSyncPushResponse {
                results: vec![RemoteSyncMutationResult {
                    client_mutation_id: "desktop-seeded".to_string(),
                    status: "duplicate".to_string(),
                    error_message: None,
                    resulting_event_sequence: Some(1),
                }],
            })])),
            ..FakeApi::default()
        };
        connect(
            &service,
            &api,
            vec![Ok(RemoteSyncFeed {
                events: vec![paper_event("revision", 1)],
                next_after_sequence: 1,
                has_more: false,
            })],
        );
        service
            .cache()
            .enqueue_mutation(
                "seeded",
                "desktop-seeded",
                "paper.patch",
                "paper_profile",
                Some("paper-1"),
                &json!({"stage": "revision"}),
            )
            .unwrap();
        api.feed_results.replace(vec![]);

        let response = service.sync_with(&api).unwrap();

        assert_eq!(response.duplicate_count, 1);
        assert_eq!(response.failed_count, 0);
        assert!(service.list_pending_mutations().unwrap().is_empty());
    }

    #[test]
    fn failed_mutation_keeps_error_state_visible() {
        let service = service();
        let api = FakeApi {
            push_results: Rc::new(RefCell::new(vec![Ok(RemoteSyncPushResponse {
                results: vec![RemoteSyncMutationResult {
                    client_mutation_id: "desktop-seeded".to_string(),
                    status: "failed".to_string(),
                    error_message: Some("validation failed".to_string()),
                    resulting_event_sequence: None,
                }],
            })])),
            ..FakeApi::default()
        };
        connect(
            &service,
            &api,
            vec![Ok(RemoteSyncFeed {
                events: vec![paper_event("revision", 1)],
                next_after_sequence: 1,
                has_more: false,
            })],
        );
        service
            .cache()
            .enqueue_mutation(
                "seeded",
                "desktop-seeded",
                "paper.patch",
                "paper_profile",
                Some("paper-1"),
                &json!({"stage": "revision"}),
            )
            .unwrap();

        let response = service.sync_with(&api).unwrap();
        let paper = service.get_paper_detail("paper-1").unwrap();

        assert_eq!(response.failed_count, 1);
        assert_eq!(paper.last_mutation_error.as_deref(), Some("validation failed"));
        assert_eq!(service.get_sync_status().unwrap().failed_mutation_count, 1);
    }

    #[test]
    fn successful_paper_patch_roundtrip_updates_cache_after_sync_event_apply() {
        let service = service();
        let api = FakeApi {
            push_results: Rc::new(RefCell::new(vec![Err(anyhow::anyhow!("network down"))])),
            ..FakeApi::default()
        };
        connect(
            &service,
            &api,
            vec![Ok(RemoteSyncFeed {
                events: vec![paper_event("revision", 1)],
                next_after_sequence: 1,
                has_more: false,
            })],
        );
        let result = service
            .queue_paper_patch(QueuePaperPatchInput {
                paper_id: "paper-1".to_string(),
                stage: Some("under_review".to_string()),
                venue: None,
                next_action: None,
                blocker: None,
                priority: None,
                last_touch_at: None,
            })
            .unwrap();
        api.push_results.replace(vec![Ok(RemoteSyncPushResponse {
            results: vec![RemoteSyncMutationResult {
                client_mutation_id: result.mutation.client_mutation_id.clone(),
                status: "applied".to_string(),
                error_message: None,
                resulting_event_sequence: Some(2),
            }],
        })]);
        api.feed_results.replace(vec![Ok(RemoteSyncFeed {
            events: vec![paper_event("under_review", 2)],
            next_after_sequence: 2,
            has_more: false,
        })]);

        let result = service.sync_with(&api).unwrap();
        let paper = service.get_paper_detail("paper-1").unwrap();

        assert_eq!(result.applied_count, 1);
        assert_eq!(paper.stage, "under_review");
        assert_eq!(paper.pending_mutation_count, 0);
    }

    #[test]
    fn successful_progress_event_roundtrip_updates_progress_cache() {
        let service = service();
        let api = FakeApi {
            push_results: Rc::new(RefCell::new(vec![Err(anyhow::anyhow!("network down"))])),
            ..FakeApi::default()
        };
        connect(
            &service,
            &api,
            vec![Ok(RemoteSyncFeed {
                events: vec![paper_event("revision", 1)],
                next_after_sequence: 1,
                has_more: false,
            })],
        );
        let result = service
            .queue_progress_event_create(QueueProgressEventCreateInput {
                paper_id: "paper-1".to_string(),
                stage: "revision".to_string(),
                happened_at: "2026-04-15T00:00:00Z".to_string(),
                summary: "Queued from desktop".to_string(),
                owner: Some("desktop".to_string()),
            })
            .unwrap();
        api.push_results.replace(vec![Ok(RemoteSyncPushResponse {
            results: vec![RemoteSyncMutationResult {
                client_mutation_id: result.mutation.client_mutation_id.clone(),
                status: "applied".to_string(),
                error_message: None,
                resulting_event_sequence: Some(2),
            }],
        })]);
        api.feed_results.replace(vec![Ok(RemoteSyncFeed {
            events: vec![progress_event(2)],
            next_after_sequence: 2,
            has_more: false,
        })]);

        let _ = service.sync_with(&api).unwrap();
        let paper = service.get_paper_detail("paper-1").unwrap();
        assert_eq!(paper.progress_events.len(), 1);
    }

    #[test]
    fn successful_subscription_policy_roundtrip_updates_cache() {
        let service = service();
        let api = FakeApi {
            push_results: Rc::new(RefCell::new(vec![Err(anyhow::anyhow!("network down"))])),
            ..FakeApi::default()
        };
        connect(
            &service,
            &api,
            vec![Ok(RemoteSyncFeed {
                events: vec![policy_event(true, 3, 1)],
                next_after_sequence: 1,
                has_more: false,
            })],
        );
        let result = service
            .queue_subscription_policy_patch(QueueSubscriptionPolicyPatchInput {
                subscription_policy_id: "policy-1".to_string(),
                enabled: Some(false),
                quiet_hours: Some(json!({"start": "23:00", "end": "07:00"})),
                frequency_cap: Some(5),
                policy: None,
            })
            .unwrap();
        api.push_results.replace(vec![Ok(RemoteSyncPushResponse {
            results: vec![RemoteSyncMutationResult {
                client_mutation_id: result.mutation.client_mutation_id.clone(),
                status: "applied".to_string(),
                error_message: None,
                resulting_event_sequence: Some(2),
            }],
        })]);
        api.feed_results.replace(vec![Ok(RemoteSyncFeed {
            events: vec![policy_event(false, 5, 2)],
            next_after_sequence: 2,
            has_more: false,
        })]);

        let _ = service.sync_with(&api).unwrap();
        let policies = service.list_subscription_policies().unwrap();
        assert!(!policies[0].enabled);
        assert_eq!(policies[0].frequency_cap, 5);
    }

    #[test]
    fn clear_local_cache_resets_cache_and_outbox_state() {
        let service = service();
        let api = FakeApi::default();
        connect(
            &service,
            &api,
            vec![Ok(RemoteSyncFeed {
                events: vec![paper_event("revision", 1), digest_event(2)],
                next_after_sequence: 2,
                has_more: false,
            })],
        );
        service
            .cache()
            .enqueue_mutation(
                "seeded",
                "desktop-seeded",
                "paper.patch",
                "paper_profile",
                Some("paper-1"),
                &json!({"stage": "revision"}),
            )
            .unwrap();

        let status = service.clear_local_cache().unwrap();
        assert_eq!(status.last_event_sequence, 0);
        assert_eq!(status.pending_mutation_count, 0);
        assert!(service.list_papers(None).unwrap().is_empty());
        assert!(service.list_pending_mutations().unwrap().is_empty());
    }

    #[test]
    fn get_sync_status_includes_pending_and_failed_counts() {
        let service = service();
        let api = FakeApi::default();
        connect(
            &service,
            &api,
            vec![Ok(RemoteSyncFeed {
                events: vec![paper_event("revision", 1)],
                next_after_sequence: 1,
                has_more: false,
            })],
        );
        service
            .cache()
            .enqueue_mutation(
                "queued",
                "desktop-queued",
                "paper.patch",
                "paper_profile",
                Some("paper-1"),
                &json!({"stage": "under_review"}),
            )
            .unwrap();
        service
            .cache()
            .enqueue_mutation(
                "failed",
                "desktop-failed",
                "paper.patch",
                "paper_profile",
                Some("paper-1"),
                &json!({"stage": "under_review"}),
            )
            .unwrap();
        service
            .cache()
            .apply_push_results(&[RemoteSyncMutationResult {
                client_mutation_id: "desktop-failed".to_string(),
                status: "failed".to_string(),
                error_message: Some("boom".to_string()),
                resulting_event_sequence: None,
            }])
            .unwrap();

        let status = service.get_sync_status().unwrap();
        assert_eq!(status.pending_mutation_count, 1);
        assert_eq!(status.failed_mutation_count, 1);
        assert_eq!(status.recent_outbox_errors, vec!["boom".to_string()]);
    }

    #[test]
    fn get_paper_detail_exposes_pending_mutation_state() {
        let service = service();
        let api = FakeApi::default();
        connect(
            &service,
            &api,
            vec![Ok(RemoteSyncFeed {
                events: vec![paper_event("revision", 1)],
                next_after_sequence: 1,
                has_more: false,
            })],
        );
        service
            .cache()
            .enqueue_mutation(
                "queued",
                "desktop-queued",
                "paper.patch",
                "paper_profile",
                Some("paper-1"),
                &json!({"stage": "under_review"}),
            )
            .unwrap();

        let detail = service.get_paper_detail("paper-1").unwrap();
        assert_eq!(detail.pending_mutation_count, 1);
    }

    #[test]
    fn list_papers_keeps_stable_ordering_contract() {
        let service = service();
        let api = FakeApi::default();
        connect(
            &service,
            &api,
            vec![Ok(RemoteSyncFeed {
                events: vec![paper_event("revision", 1)],
                next_after_sequence: 1,
                has_more: false,
            })],
        );

        let papers = service
            .list_papers(Some(ListPapersInput {
                paper_type: Some("revision".to_string()),
                ..ListPapersInput::default()
            }))
            .unwrap();
        assert_eq!(papers.len(), 1);
    }

    #[test]
    fn choose_workspace_root_persists_valid_root() {
        let service = service();
        let workspace_root = new_temp_path();

        let status = service
            .choose_workspace_root(ChooseWorkspaceRootInput {
                selected_path: workspace_root.to_string_lossy().into_owned(),
            })
            .unwrap();
        let canonical = std::fs::canonicalize(&workspace_root).unwrap();

        assert_eq!(status.status, "ready");
        assert_eq!(
            service.get_workspace_status().unwrap().root_path,
            Some(canonical.to_string_lossy().into_owned())
        );
    }

    #[test]
    fn ensure_paper_workspace_creates_expected_layout() {
        let service = service();
        let api = FakeApi::default();
        let workspace_root = new_temp_path();
        connect(
            &service,
            &api,
            vec![Ok(RemoteSyncFeed {
                events: vec![paper_event("revision", 1)],
                next_after_sequence: 1,
                has_more: false,
            })],
        );
        service
            .choose_workspace_root(ChooseWorkspaceRootInput {
                selected_path: workspace_root.to_string_lossy().into_owned(),
            })
            .unwrap();

        let workspace = service.ensure_paper_workspace("paper-1").unwrap();
        let workspace_path = PathBuf::from(workspace.workspace_abs_path.unwrap());
        assert!(workspace.workspace_ready);
        assert!(workspace_path.join("attachments").exists());
        assert!(workspace_path.join("notes").exists());
        assert!(workspace_path.join("exports").exists());
        assert!(workspace_path.join("workspace.json").exists());
    }

    #[test]
    fn import_attachment_managed_copy_and_duplicate_detection_work() {
        let service = service();
        let api = FakeApi::default();
        let workspace_root = new_temp_path();
        let source_dir = new_temp_path();
        let source_file = source_dir.join("draft.pdf");
        std::fs::write(&source_file, b"paper draft").unwrap();
        connect(
            &service,
            &api,
            vec![Ok(RemoteSyncFeed {
                events: vec![paper_event("revision", 1)],
                next_after_sequence: 1,
                has_more: false,
            })],
        );
        service
            .choose_workspace_root(ChooseWorkspaceRootInput {
                selected_path: workspace_root.to_string_lossy().into_owned(),
            })
            .unwrap();

        let imported = service
            .import_paper_attachments(ImportPaperAttachmentsInput {
                paper_id: "paper-1".to_string(),
                attachment_kind: "manuscript".to_string(),
                source_paths: vec![source_file.to_string_lossy().into_owned()],
            })
            .unwrap();
        assert_eq!(imported.results[0].status, "imported");
        let attachment = imported.results[0].attachment.clone().unwrap();
        assert!(PathBuf::from(&attachment.absolute_path.clone().unwrap()).exists());
        assert!(source_file.exists());

        let duplicate = service
            .import_paper_attachments(ImportPaperAttachmentsInput {
                paper_id: "paper-1".to_string(),
                attachment_kind: "manuscript".to_string(),
                source_paths: vec![source_file.to_string_lossy().into_owned()],
            })
            .unwrap();
        assert_eq!(duplicate.results[0].status, "duplicate");
        assert_eq!(service.list_paper_attachments("paper-1").unwrap().len(), 1);
        let work_mutations = work_activity_mutations(&service);
        assert_eq!(work_mutations.len(), 1);
        assert_eq!(
            work_mutations[0].payload["activity_type"].as_str(),
            Some("attachment_imported")
        );
    }

    #[test]
    fn refresh_workspace_marks_missing_files() {
        let service = service();
        let api = FakeApi::default();
        let workspace_root = new_temp_path();
        let source_dir = new_temp_path();
        let source_file = source_dir.join("review.txt");
        std::fs::write(&source_file, b"review text").unwrap();
        connect(
            &service,
            &api,
            vec![Ok(RemoteSyncFeed {
                events: vec![paper_event("revision", 1)],
                next_after_sequence: 1,
                has_more: false,
            })],
        );
        service
            .choose_workspace_root(ChooseWorkspaceRootInput {
                selected_path: workspace_root.to_string_lossy().into_owned(),
            })
            .unwrap();
        let imported = service
            .import_paper_attachments(ImportPaperAttachmentsInput {
                paper_id: "paper-1".to_string(),
                attachment_kind: "review".to_string(),
                source_paths: vec![source_file.to_string_lossy().into_owned()],
            })
            .unwrap();
        let managed_path = PathBuf::from(
            imported.results[0]
                .attachment
                .clone()
                .unwrap()
                .absolute_path
                .unwrap(),
        );
        std::fs::remove_file(managed_path).unwrap();

        let workspace = service.refresh_paper_workspace("paper-1").unwrap();
        assert_eq!(workspace.attachment_count, 1);
        assert_eq!(
            service.list_paper_attachments("paper-1").unwrap()[0].status,
            "missing"
        );
    }

    #[test]
    fn clear_local_cache_and_disconnect_do_not_delete_managed_files() {
        let service = service();
        let api = FakeApi::default();
        let workspace_root = new_temp_path();
        let source_dir = new_temp_path();
        let source_file = source_dir.join("response.docx");
        std::fs::write(&source_file, b"response").unwrap();
        connect(
            &service,
            &api,
            vec![Ok(RemoteSyncFeed {
                events: vec![paper_event("revision", 1)],
                next_after_sequence: 1,
                has_more: false,
            })],
        );
        service
            .choose_workspace_root(ChooseWorkspaceRootInput {
                selected_path: workspace_root.to_string_lossy().into_owned(),
            })
            .unwrap();
        let imported = service
            .import_paper_attachments(ImportPaperAttachmentsInput {
                paper_id: "paper-1".to_string(),
                attachment_kind: "response_letter".to_string(),
                source_paths: vec![source_file.to_string_lossy().into_owned()],
            })
            .unwrap();
        let managed_path = PathBuf::from(
            imported.results[0]
                .attachment
                .clone()
                .unwrap()
                .absolute_path
                .unwrap(),
        );

        service.clear_local_cache().unwrap();
        assert!(managed_path.exists());
        assert_eq!(service.list_paper_attachments("paper-1").unwrap().len(), 1);

        service.disconnect_device().unwrap();
        assert!(managed_path.exists());
        assert_eq!(service.list_paper_attachments("paper-1").unwrap().len(), 1);
    }

    #[test]
    fn list_note_templates_returns_all_built_ins() {
        let service = service();
        let templates = service.list_note_templates().unwrap();
        assert_eq!(templates.len(), 6);
        assert!(templates.iter().any(|template| template.kind == "reviewer_matrix"));
    }

    #[test]
    fn create_note_from_template_creates_file_and_metadata() {
        let service = service();
        let api = FakeApi::default();
        let workspace_root = new_temp_path();
        connect(
            &service,
            &api,
            vec![Ok(RemoteSyncFeed {
                events: vec![paper_event("revision", 1)],
                next_after_sequence: 1,
                has_more: false,
            })],
        );
        service
            .choose_workspace_root(ChooseWorkspaceRootInput {
                selected_path: workspace_root.to_string_lossy().into_owned(),
            })
            .unwrap();

        let created = service
            .create_paper_note_from_template(CreatePaperNoteFromTemplateInput {
                paper_id: "paper-1".to_string(),
                template_kind: "research_note".to_string(),
            })
            .unwrap();

        assert_eq!(created.note.note.template_kind, "research_note");
        assert!(created.note.content.unwrap_or_default().contains("# Research Note"));
        assert!(PathBuf::from(created.note.note.absolute_path.unwrap()).exists());
        assert_eq!(service.list_paper_notes("paper-1").unwrap().len(), 1);
        let work_mutations = work_activity_mutations(&service);
        assert_eq!(work_mutations.len(), 1);
        assert_eq!(
            work_mutations[0].payload["activity_type"].as_str(),
            Some("note_created")
        );
    }

    #[test]
    fn create_blank_note_creates_markdown_file_under_notes_directory() {
        let service = service();
        let api = FakeApi::default();
        let workspace_root = new_temp_path();
        connect(
            &service,
            &api,
            vec![Ok(RemoteSyncFeed {
                events: vec![paper_event("revision", 1)],
                next_after_sequence: 1,
                has_more: false,
            })],
        );
        service
            .choose_workspace_root(ChooseWorkspaceRootInput {
                selected_path: workspace_root.to_string_lossy().into_owned(),
            })
            .unwrap();

        let created = service
            .create_blank_paper_note(CreateBlankPaperNoteInput {
                paper_id: "paper-1".to_string(),
                title: Some("Working Draft".to_string()),
            })
            .unwrap();

        let note = created.note.note;
        assert_eq!(note.source_mode, "blank");
        assert!(note.relative_path.contains("papers/paper-1/notes/"));
        assert!(note.file_name.ends_with(".md"));
    }

    #[test]
    fn get_and_save_paper_note_roundtrip_updates_disk_and_metadata() {
        let service = service();
        let api = FakeApi::default();
        let workspace_root = new_temp_path();
        connect(
            &service,
            &api,
            vec![Ok(RemoteSyncFeed {
                events: vec![paper_event("revision", 1)],
                next_after_sequence: 1,
                has_more: false,
            })],
        );
        service
            .choose_workspace_root(ChooseWorkspaceRootInput {
                selected_path: workspace_root.to_string_lossy().into_owned(),
            })
            .unwrap();

        let created = service
            .create_paper_note_from_template(CreatePaperNoteFromTemplateInput {
                paper_id: "paper-1".to_string(),
                template_kind: "revision_plan".to_string(),
            })
            .unwrap();
        let loaded = service.get_paper_note(&created.note.note.id).unwrap();
        assert!(loaded.content.unwrap_or_default().contains("# Revision Plan"));

        let saved = service
            .save_paper_note(SavePaperNoteInput {
                note_id: created.note.note.id.clone(),
                content: "# Updated Note\n\nSaved locally.\n".to_string(),
            })
            .unwrap();
        let absolute_path = PathBuf::from(saved.note.note.absolute_path.clone().unwrap());
        let disk_content = std::fs::read_to_string(absolute_path).unwrap();
        assert_eq!(disk_content, "# Updated Note\n\nSaved locally.\n");
        assert_eq!(saved.note.content.unwrap_or_default(), "# Updated Note\n\nSaved locally.\n");
        assert!(saved.note.note.sha256.is_some());
        let work_mutations = work_activity_mutations(&service);
        assert_eq!(work_mutations.len(), 2);
        assert_eq!(
            work_mutations[1].payload["activity_type"].as_str(),
            Some("note_saved")
        );
    }

    #[test]
    fn refresh_notes_marks_missing_files_without_deleting_rows() {
        let service = service();
        let api = FakeApi::default();
        let workspace_root = new_temp_path();
        connect(
            &service,
            &api,
            vec![Ok(RemoteSyncFeed {
                events: vec![paper_event("revision", 1)],
                next_after_sequence: 1,
                has_more: false,
            })],
        );
        service
            .choose_workspace_root(ChooseWorkspaceRootInput {
                selected_path: workspace_root.to_string_lossy().into_owned(),
            })
            .unwrap();

        let created = service
            .create_blank_paper_note(CreateBlankPaperNoteInput {
                paper_id: "paper-1".to_string(),
                title: Some("Scratchpad".to_string()),
            })
            .unwrap();
        let note_path = PathBuf::from(created.note.note.absolute_path.unwrap());
        std::fs::remove_file(&note_path).unwrap();

        let notes = service.refresh_paper_notes("paper-1").unwrap();
        assert_eq!(notes.len(), 1);
        assert_eq!(notes[0].status, "missing");
    }

    #[test]
    fn clear_local_cache_and_disconnect_do_not_delete_note_files() {
        let service = service();
        let api = FakeApi::default();
        let workspace_root = new_temp_path();
        connect(
            &service,
            &api,
            vec![Ok(RemoteSyncFeed {
                events: vec![paper_event("revision", 1)],
                next_after_sequence: 1,
                has_more: false,
            })],
        );
        service
            .choose_workspace_root(ChooseWorkspaceRootInput {
                selected_path: workspace_root.to_string_lossy().into_owned(),
            })
            .unwrap();
        let created = service
            .create_blank_paper_note(CreateBlankPaperNoteInput {
                paper_id: "paper-1".to_string(),
                title: Some("Local Note".to_string()),
            })
            .unwrap();
        let note_path = PathBuf::from(created.note.note.absolute_path.unwrap());

        service.clear_local_cache().unwrap();
        assert!(note_path.exists());
        assert_eq!(service.list_paper_notes("paper-1").unwrap().len(), 1);

        service.disconnect_device().unwrap();
        assert!(note_path.exists());
        assert_eq!(service.list_paper_notes("paper-1").unwrap().len(), 1);
    }

    #[test]
    fn create_review_round_creates_round_row() {
        let service = service();
        let api = FakeApi::default();
        connect(
            &service,
            &api,
            vec![Ok(RemoteSyncFeed {
                events: vec![paper_event("revision", 1)],
                next_after_sequence: 1,
                has_more: false,
            })],
        );

        let result = service
            .create_review_round(CreateReviewRoundInput {
                paper_id: "paper-1".to_string(),
                round_label: "Round 1".to_string(),
                venue: Some("JOM".to_string()),
                decision_label: Some("Major revision".to_string()),
            })
            .unwrap();

        assert_eq!(result.round.as_ref().map(|round| round.round_label.as_str()), Some("Round 1"));
        assert_eq!(service.get_paper_detail("paper-1").unwrap().review_round_count, 1);
        let work_mutations = work_activity_mutations(&service);
        assert_eq!(work_mutations.len(), 1);
        assert_eq!(
            work_mutations[0].payload["activity_type"].as_str(),
            Some("review_round_created")
        );
    }

    #[test]
    fn review_comment_crud_and_ordering_work() {
        let service = service();
        let api = FakeApi::default();
        connect(
            &service,
            &api,
            vec![Ok(RemoteSyncFeed {
                events: vec![paper_event("revision", 1)],
                next_after_sequence: 1,
                has_more: false,
            })],
        );
        let round = service
            .create_review_round(CreateReviewRoundInput {
                paper_id: "paper-1".to_string(),
                round_label: "Round 1".to_string(),
                venue: None,
                decision_label: None,
            })
            .unwrap()
            .round
            .unwrap();

        service
            .add_review_comment(AddReviewCommentInput {
                review_round_id: round.id.clone(),
                reviewer_label: "Reviewer 2".to_string(),
                comment_code: Some("R2-1".to_string()),
                comment_text: "Second reviewer comment".to_string(),
                category: Some("clarity".to_string()),
                disposition: Some("todo".to_string()),
                response_summary: None,
                action_note: None,
            })
            .unwrap();
        let created = service
            .add_review_comment(AddReviewCommentInput {
                review_round_id: round.id.clone(),
                reviewer_label: "Reviewer 1".to_string(),
                comment_code: Some("R1-1".to_string()),
                comment_text: "First reviewer comment".to_string(),
                category: Some("method".to_string()),
                disposition: Some("todo".to_string()),
                response_summary: Some("Initial response".to_string()),
                action_note: Some("Add clarification".to_string()),
            })
            .unwrap();

        let ordered = service
            .get_review_round_detail(ReviewRoundLookupInput {
                review_round_id: round.id.clone(),
            })
            .unwrap();
        assert_eq!(ordered.comments[0].reviewer_label, "Reviewer 1");
        assert_eq!(ordered.round.reviewer_count, 2);

        let updated = service
            .update_review_comment(UpdateReviewCommentInput {
                comment_id: created.comment.unwrap().id,
                reviewer_label: None,
                comment_code: None,
                comment_text: None,
                category: None,
                disposition: Some("done".to_string()),
                response_summary: Some("Updated response".to_string()),
                action_note: Some("Revised action".to_string()),
            })
            .unwrap();
        assert_eq!(
            updated.comment.as_ref().and_then(|comment| comment.response_summary.as_deref()),
            Some("Updated response")
        );

        let delete_target = ordered.comments[0].id.clone();
        let deleted = service
            .delete_review_comment(DeleteReviewCommentInput {
                comment_id: delete_target,
            })
            .unwrap();
        assert_eq!(deleted.detail.unwrap().comments.len(), 1);
    }

    #[test]
    fn generate_review_notes_create_and_update_local_markdown_files() {
        let service = service();
        let api = FakeApi::default();
        let workspace_root = new_temp_path();
        connect(
            &service,
            &api,
            vec![Ok(RemoteSyncFeed {
                events: vec![paper_event("revision", 1)],
                next_after_sequence: 1,
                has_more: false,
            })],
        );
        service
            .choose_workspace_root(ChooseWorkspaceRootInput {
                selected_path: workspace_root.to_string_lossy().into_owned(),
            })
            .unwrap();
        let round = service
            .create_review_round(CreateReviewRoundInput {
                paper_id: "paper-1".to_string(),
                round_label: "Round 1".to_string(),
                venue: Some("JOM".to_string()),
                decision_label: Some("Major revision".to_string()),
            })
            .unwrap()
            .round
            .unwrap();
        service
            .add_review_comment(AddReviewCommentInput {
                review_round_id: round.id.clone(),
                reviewer_label: "Reviewer 1".to_string(),
                comment_code: Some("R1-1".to_string()),
                comment_text: "Please expand the method section".to_string(),
                category: Some("method".to_string()),
                disposition: Some("todo".to_string()),
                response_summary: Some("We expanded Section 2.".to_string()),
                action_note: Some("Update methods text.".to_string()),
            })
            .unwrap();

        let first = service
            .generate_response_letter_note(ReviewRoundLookupInput {
                review_round_id: round.id.clone(),
            })
            .unwrap();
        let first_note = first.generated_note.unwrap();
        let first_detail = service
            .get_paper_note(&first_note.note_id)
            .unwrap();
        assert!(first_detail.content.unwrap_or_default().contains("We expanded Section 2."));

        service
            .add_review_comment(AddReviewCommentInput {
                review_round_id: round.id.clone(),
                reviewer_label: "Reviewer 1".to_string(),
                comment_code: Some("R1-2".to_string()),
                comment_text: "Please clarify limitations".to_string(),
                category: Some("discussion".to_string()),
                disposition: Some("todo".to_string()),
                response_summary: Some("We added a limitations paragraph.".to_string()),
                action_note: Some("Revise discussion.".to_string()),
            })
            .unwrap();
        let second = service
            .generate_response_letter_note(ReviewRoundLookupInput {
                review_round_id: round.id.clone(),
            })
            .unwrap();
        let second_note = second.generated_note.unwrap();
        assert_eq!(first_note.note_id, second_note.note_id);
        let updated_detail = service.get_paper_note(&second_note.note_id).unwrap();
        assert!(updated_detail
            .content
            .unwrap_or_default()
            .contains("limitations paragraph"));

        let matrix = service
            .generate_reviewer_matrix_note(ReviewRoundLookupInput {
                review_round_id: round.id.clone(),
            })
            .unwrap();
        assert_eq!(
            matrix.generated_note.as_ref().map(|note| note.kind.as_str()),
            Some("reviewer_matrix")
        );
        let work_mutations = work_activity_mutations(&service);
        assert!(work_mutations.iter().any(|mutation| {
            mutation.payload["activity_type"].as_str() == Some("response_letter_generated")
        }));
        assert!(work_mutations.iter().any(|mutation| {
            mutation.payload["activity_type"].as_str() == Some("reviewer_matrix_generated")
        }));
    }

    #[test]
    fn clear_local_cache_and_disconnect_do_not_delete_generated_review_notes() {
        let service = service();
        let api = FakeApi::default();
        let workspace_root = new_temp_path();
        connect(
            &service,
            &api,
            vec![Ok(RemoteSyncFeed {
                events: vec![paper_event("revision", 1)],
                next_after_sequence: 1,
                has_more: false,
            })],
        );
        service
            .choose_workspace_root(ChooseWorkspaceRootInput {
                selected_path: workspace_root.to_string_lossy().into_owned(),
            })
            .unwrap();
        let round = service
            .create_review_round(CreateReviewRoundInput {
                paper_id: "paper-1".to_string(),
                round_label: "Round 1".to_string(),
                venue: Some("JOM".to_string()),
                decision_label: None,
            })
            .unwrap()
            .round
            .unwrap();
        service
            .add_review_comment(AddReviewCommentInput {
                review_round_id: round.id.clone(),
                reviewer_label: "Reviewer 1".to_string(),
                comment_code: Some("R1-1".to_string()),
                comment_text: "Minor correction".to_string(),
                category: None,
                disposition: Some("todo".to_string()),
                response_summary: Some("Corrected in the manuscript.".to_string()),
                action_note: None,
            })
            .unwrap();
        let generated = service
            .generate_reviewer_matrix_note(ReviewRoundLookupInput {
                review_round_id: round.id.clone(),
            })
            .unwrap()
            .generated_note
            .unwrap();
        let note_path = PathBuf::from(
            service
                .get_paper_note(&generated.note_id)
                .unwrap()
                .note
                .absolute_path
                .unwrap(),
        );

        service.clear_local_cache().unwrap();
        assert!(note_path.exists());

        service.disconnect_device().unwrap();
        assert!(note_path.exists());
    }

    #[test]
    fn sync_now_handles_work_activity_record_mutations() {
        let service = service();
        let api = FakeApi {
            push_results: Rc::new(RefCell::new(vec![Ok(RemoteSyncPushResponse {
                results: vec![RemoteSyncMutationResult {
                    client_mutation_id: "desktop-activity".to_string(),
                    status: "applied".to_string(),
                    error_message: None,
                    resulting_event_sequence: None,
                }],
            })])),
            ..FakeApi::default()
        };
        connect(
            &service,
            &api,
            vec![Ok(RemoteSyncFeed {
                events: vec![paper_event("revision", 1)],
                next_after_sequence: 1,
                has_more: false,
            })],
        );
        service
            .cache()
            .enqueue_mutation(
                "activity",
                "desktop-activity",
                "work_activity.record",
                "work_activity_event",
                Some("paper-1"),
                &json!({
                    "paper_id": "paper-1",
                    "activity_type": "note_saved",
                    "summary": "Saved a local note.",
                    "metadata": {"note_id": "note-1"},
                    "happened_at": "2026-04-15T00:00:00Z"
                }),
            )
            .unwrap();

        let response = service.sync_with(&api).unwrap();

        assert_eq!(response.applied_count, 1);
        assert_eq!(response.failed_count, 0);
        assert_eq!(response.pending_mutation_count, 0);
    }
}
