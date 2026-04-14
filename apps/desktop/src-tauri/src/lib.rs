mod cache;
mod error;
mod models;
mod progress;
mod secret_store;
mod service;
mod sync_client;

use anyhow::{Context, Result};
use models::{
    AppBootstrapRead, ConnectDeviceInput, ConnectDeviceResponse, ListPapersInput, PaperDetailRead,
    PaperListItemRead, PendingMutationRead, QueuePaperPatchInput, QueueProgressEventCreateInput,
    QueueSubscriptionPolicyPatchInput, SubscriptionPolicyRead, SyncNowResponse, SyncStatusRead,
    TodayOverviewRead, WriteActionResultRead,
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
            queuePaperPatch,
            queueProgressEventCreate,
            queueSubscriptionPolicyPatch
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
