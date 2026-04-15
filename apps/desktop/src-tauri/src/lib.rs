mod cache;
mod error;
mod models;
mod notes;
mod progress;
mod secret_store;
mod service;
mod sync_client;
mod workspace;

use anyhow::{Context, Result};
use models::{
    AppBootstrapRead, ChooseWorkspaceRootInput, ConnectDeviceInput, ConnectDeviceResponse,
    CreateBlankPaperNoteInput, CreatePaperNoteFromTemplateInput, EnsurePaperWorkspaceInput,
    ImportPaperAttachmentsInput, ImportPaperAttachmentsResponse, ListPaperNotesInput,
    ListPapersInput, NoteActionResultRead, NoteTemplateRead, PaperAttachmentRead,
    PaperDetailRead, PaperListItemRead, PaperNoteDetailRead, PaperNoteSummaryRead,
    PaperWorkspaceRead, PendingMutationRead, QueuePaperPatchInput,
    QueueProgressEventCreateInput, QueueSubscriptionPolicyPatchInput,
    RefreshPaperNotesInput, RefreshPaperWorkspaceInput, SavePaperNoteInput,
    SubscriptionPolicyRead, SyncNowResponse, SyncStatusRead, TodayOverviewRead,
    WorkspaceStatusRead, WriteActionResultRead,
};
use service::{DesktopPaths, DesktopService};
use tauri::{Manager, State};

#[derive(Debug, Clone)]
struct AppState {
    paths: DesktopPaths,
}

impl AppState {
    fn desktop_service(&self) -> Result<DesktopService> {
        DesktopService::new(self.paths.clone())
    }
}

fn build_state(app: &tauri::App) -> Result<AppState> {
    let path_manager = app.path();
    let app_data_dir = path_manager
        .app_data_dir()
        .context("failed to resolve desktop app data directory")?;
    let cache_db_path = app_data_dir.join("desktop-cache.sqlite3");
    let secret_store_path = app_data_dir.join("desktop-secret-store.json");
    Ok(AppState {
        paths: DesktopPaths {
            app_data_dir,
            cache_db_path,
            secret_store_path,
        },
    })
}

fn command_error(error: anyhow::Error) -> String {
    format!("{error:#}")
}

#[allow(non_snake_case)]
#[tauri::command]
fn appBootstrap(state: State<AppState>) -> Result<AppBootstrapRead, String> {
    state
        .desktop_service()
        .and_then(|service| service.app_bootstrap())
        .map_err(command_error)
}

#[allow(non_snake_case)]
#[tauri::command]
fn connectDevice(
    state: State<AppState>,
    input: ConnectDeviceInput,
) -> Result<ConnectDeviceResponse, String> {
    let service = state.desktop_service().map_err(command_error)?;
    let api = sync_client::ReqwestSyncBackendApi::new(
        input.base_url.clone(),
        input.device_token.clone(),
    )
    .map_err(command_error)?;
    service.connect_with(input, &api).map_err(command_error)
}

#[allow(non_snake_case)]
#[tauri::command]
fn disconnectDevice(state: State<AppState>) -> Result<SyncStatusRead, String> {
    state
        .desktop_service()
        .and_then(|service| service.disconnect_device())
        .map_err(command_error)
}

#[allow(non_snake_case)]
#[tauri::command]
fn clearLocalCache(state: State<AppState>) -> Result<SyncStatusRead, String> {
    state
        .desktop_service()
        .and_then(|service| service.clear_local_cache())
        .map_err(command_error)
}

#[allow(non_snake_case)]
#[tauri::command]
fn syncNow(state: State<AppState>) -> Result<SyncNowResponse, String> {
    state
        .desktop_service()
        .and_then(|service| service.sync_now())
        .map_err(command_error)
}

#[allow(non_snake_case)]
#[tauri::command]
fn getSyncStatus(state: State<AppState>) -> Result<SyncStatusRead, String> {
    state
        .desktop_service()
        .and_then(|service| service.get_sync_status())
        .map_err(command_error)
}

#[allow(non_snake_case)]
#[tauri::command]
fn getTodayOverview(state: State<AppState>) -> Result<TodayOverviewRead, String> {
    state
        .desktop_service()
        .and_then(|service| service.get_today_overview())
        .map_err(command_error)
}

#[allow(non_snake_case)]
#[tauri::command]
fn listPapers(
    state: State<AppState>,
    filters: Option<ListPapersInput>,
) -> Result<Vec<PaperListItemRead>, String> {
    state
        .desktop_service()
        .and_then(|service| service.list_papers(filters))
        .map_err(command_error)
}

#[allow(non_snake_case)]
#[tauri::command]
fn getPaperDetail(state: State<AppState>, paperId: String) -> Result<PaperDetailRead, String> {
    state
        .desktop_service()
        .and_then(|service| service.get_paper_detail(&paperId))
        .map_err(command_error)
}

#[allow(non_snake_case)]
#[tauri::command]
fn listSubscriptionPolicies(state: State<AppState>) -> Result<Vec<SubscriptionPolicyRead>, String> {
    state
        .desktop_service()
        .and_then(|service| service.list_subscription_policies())
        .map_err(command_error)
}

#[allow(non_snake_case)]
#[tauri::command]
fn listPendingMutations(state: State<AppState>) -> Result<Vec<PendingMutationRead>, String> {
    state
        .desktop_service()
        .and_then(|service| service.list_pending_mutations())
        .map_err(command_error)
}

#[allow(non_snake_case)]
#[tauri::command]
fn getWorkspaceStatus(state: State<AppState>) -> Result<WorkspaceStatusRead, String> {
    state
        .desktop_service()
        .and_then(|service| service.get_workspace_status())
        .map_err(command_error)
}

#[allow(non_snake_case)]
#[tauri::command]
fn chooseWorkspaceRoot(
    state: State<AppState>,
    input: ChooseWorkspaceRootInput,
) -> Result<WorkspaceStatusRead, String> {
    state
        .desktop_service()
        .and_then(|service| service.choose_workspace_root(input))
        .map_err(command_error)
}

#[allow(non_snake_case)]
#[tauri::command]
fn clearWorkspaceRoot(state: State<AppState>) -> Result<WorkspaceStatusRead, String> {
    state
        .desktop_service()
        .and_then(|service| service.clear_workspace_root())
        .map_err(command_error)
}

#[allow(non_snake_case)]
#[tauri::command]
fn ensurePaperWorkspace(
    state: State<AppState>,
    input: EnsurePaperWorkspaceInput,
) -> Result<PaperWorkspaceRead, String> {
    state
        .desktop_service()
        .and_then(|service| service.ensure_paper_workspace(&input.paper_id))
        .map_err(command_error)
}

#[allow(non_snake_case)]
#[tauri::command]
fn getPaperWorkspace(
    state: State<AppState>,
    paperId: String,
) -> Result<PaperWorkspaceRead, String> {
    state
        .desktop_service()
        .and_then(|service| service.get_paper_workspace(&paperId))
        .map_err(command_error)
}

#[allow(non_snake_case)]
#[tauri::command]
fn listPaperAttachments(
    state: State<AppState>,
    paperId: String,
) -> Result<Vec<PaperAttachmentRead>, String> {
    state
        .desktop_service()
        .and_then(|service| service.list_paper_attachments(&paperId))
        .map_err(command_error)
}

#[allow(non_snake_case)]
#[tauri::command]
fn listNoteTemplates(state: State<AppState>) -> Result<Vec<NoteTemplateRead>, String> {
    state
        .desktop_service()
        .and_then(|service| service.list_note_templates())
        .map_err(command_error)
}

#[allow(non_snake_case)]
#[tauri::command]
fn listPaperNotes(
    state: State<AppState>,
    input: ListPaperNotesInput,
) -> Result<Vec<PaperNoteSummaryRead>, String> {
    state
        .desktop_service()
        .and_then(|service| service.list_paper_notes(&input.paper_id))
        .map_err(command_error)
}

#[allow(non_snake_case)]
#[tauri::command]
fn createPaperNoteFromTemplate(
    state: State<AppState>,
    input: CreatePaperNoteFromTemplateInput,
) -> Result<NoteActionResultRead, String> {
    state
        .desktop_service()
        .and_then(|service| service.create_paper_note_from_template(input))
        .map_err(command_error)
}

#[allow(non_snake_case)]
#[tauri::command]
fn createBlankPaperNote(
    state: State<AppState>,
    input: CreateBlankPaperNoteInput,
) -> Result<NoteActionResultRead, String> {
    state
        .desktop_service()
        .and_then(|service| service.create_blank_paper_note(input))
        .map_err(command_error)
}

#[allow(non_snake_case)]
#[tauri::command]
fn getPaperNote(
    state: State<AppState>,
    noteId: String,
) -> Result<PaperNoteDetailRead, String> {
    state
        .desktop_service()
        .and_then(|service| service.get_paper_note(&noteId))
        .map_err(command_error)
}

#[allow(non_snake_case)]
#[tauri::command]
fn savePaperNote(
    state: State<AppState>,
    input: SavePaperNoteInput,
) -> Result<NoteActionResultRead, String> {
    state
        .desktop_service()
        .and_then(|service| service.save_paper_note(input))
        .map_err(command_error)
}

#[allow(non_snake_case)]
#[tauri::command]
fn refreshPaperNotes(
    state: State<AppState>,
    input: RefreshPaperNotesInput,
) -> Result<Vec<PaperNoteSummaryRead>, String> {
    state
        .desktop_service()
        .and_then(|service| service.refresh_paper_notes(&input.paper_id))
        .map_err(command_error)
}

#[allow(non_snake_case)]
#[tauri::command]
fn importPaperAttachments(
    state: State<AppState>,
    input: ImportPaperAttachmentsInput,
) -> Result<ImportPaperAttachmentsResponse, String> {
    state
        .desktop_service()
        .and_then(|service| service.import_paper_attachments(input))
        .map_err(command_error)
}

#[allow(non_snake_case)]
#[tauri::command]
fn refreshPaperWorkspace(
    state: State<AppState>,
    input: RefreshPaperWorkspaceInput,
) -> Result<PaperWorkspaceRead, String> {
    state
        .desktop_service()
        .and_then(|service| service.refresh_paper_workspace(&input.paper_id))
        .map_err(command_error)
}

#[allow(non_snake_case)]
#[tauri::command]
fn queuePaperPatch(
    state: State<AppState>,
    input: QueuePaperPatchInput,
) -> Result<WriteActionResultRead, String> {
    state
        .desktop_service()
        .and_then(|service| service.queue_paper_patch(input))
        .map_err(command_error)
}

#[allow(non_snake_case)]
#[tauri::command]
fn queueProgressEventCreate(
    state: State<AppState>,
    input: QueueProgressEventCreateInput,
) -> Result<WriteActionResultRead, String> {
    state
        .desktop_service()
        .and_then(|service| service.queue_progress_event_create(input))
        .map_err(command_error)
}

#[allow(non_snake_case)]
#[tauri::command]
fn queueSubscriptionPolicyPatch(
    state: State<AppState>,
    input: QueueSubscriptionPolicyPatchInput,
) -> Result<WriteActionResultRead, String> {
    state
        .desktop_service()
        .and_then(|service| service.queue_subscription_policy_patch(input))
        .map_err(command_error)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .setup(|app| {
            let state = build_state(app).map_err(|error| {
                std::io::Error::other(format!("failed to initialize desktop state: {error:#}"))
            })?;
            app.manage(state);
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            appBootstrap,
            connectDevice,
            disconnectDevice,
            clearLocalCache,
            syncNow,
            getSyncStatus,
            getTodayOverview,
            listPapers,
            getPaperDetail,
            listSubscriptionPolicies,
            listPendingMutations,
            getWorkspaceStatus,
            chooseWorkspaceRoot,
            clearWorkspaceRoot,
            ensurePaperWorkspace,
            getPaperWorkspace,
            listPaperAttachments,
            listNoteTemplates,
            listPaperNotes,
            createPaperNoteFromTemplate,
            createBlankPaperNote,
            getPaperNote,
            savePaperNote,
            refreshPaperNotes,
            importPaperAttachments,
            refreshPaperWorkspace,
            queuePaperPatch,
            queueProgressEventCreate,
            queueSubscriptionPolicyPatch
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
