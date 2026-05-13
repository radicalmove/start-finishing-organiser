use std::{
    fs,
    io::Write,
    process::{Child, Command, Stdio},
    sync::Mutex,
};

use tauri::Manager;

mod credential_store;

const BACKEND_BIND_ADDR: &str = "127.0.0.1:8088";
const BACKEND_BINARY_NAME: &str = "sfo-server";
const BACKEND_DATABASE_FILE: &str = "sfo-rust.db";

struct BackendState(Mutex<Option<Child>>);

fn should_spawn_backend() -> bool {
    should_spawn_backend_from_flag(
        std::env::var("SFO_SPAWN_BACKEND").ok().as_deref(),
        cfg!(target_os = "macos") && !cfg!(mobile),
    )
}

fn should_spawn_backend_from_flag(flag: Option<&str>, default_enabled: bool) -> bool {
    match flag.map(str::trim).filter(|value| !value.is_empty()) {
        Some(value) if value == "1" || value.eq_ignore_ascii_case("true") => true,
        Some(value) if value == "0" || value.eq_ignore_ascii_case("false") => false,
        Some(_) => false,
        None => default_enabled,
    }
}

#[cfg(test)]
mod tests {
    use super::{backend_resource_candidates, should_spawn_backend_from_flag};

    #[test]
    fn backend_spawn_defaults_to_desktop_policy_when_unset() {
        assert!(should_spawn_backend_from_flag(None, true));
        assert!(!should_spawn_backend_from_flag(None, false));
    }

    #[test]
    fn backend_spawn_accepts_true_flags() {
        assert!(should_spawn_backend_from_flag(Some("1"), false));
        assert!(should_spawn_backend_from_flag(Some("true"), false));
        assert!(should_spawn_backend_from_flag(Some("TRUE"), false));
    }

    #[test]
    fn backend_spawn_rejects_other_flags() {
        assert!(!should_spawn_backend_from_flag(Some("0"), true));
        assert!(!should_spawn_backend_from_flag(Some("false"), true));
        assert!(!should_spawn_backend_from_flag(Some("yes"), true));
    }

    #[test]
    fn backend_resource_candidates_prefer_current_rust_server() {
        let candidates = backend_resource_candidates(std::path::Path::new("/bundle/Resources"));

        assert_eq!(
            candidates[0],
            std::path::Path::new("/bundle/Resources/bin/sfo-server")
        );
        assert!(candidates.iter().all(|path| {
            path.file_name()
                .and_then(|name| name.to_str())
                .is_some_and(|name| name.starts_with("sfo-server"))
        }));
    }
}

fn spawn_backend(app: &tauri::AppHandle) -> Option<Child> {
    if !should_spawn_backend() {
        return None;
    }

    let log_dir = app
        .path()
        .app_log_dir()
        .unwrap_or_else(|_| app.path().app_data_dir().unwrap_or_default().join("logs"));
    let _ = fs::create_dir_all(&log_dir);
    let spawn_log_path = log_dir.join("backend_spawn.log");
    let spawn_log = |message: &str| {
        if let Ok(mut file) = fs::OpenOptions::new()
            .create(true)
            .append(true)
            .open(&spawn_log_path)
        {
            let _ = writeln!(file, "{message}");
        }
    };

    spawn_log("---- spawn attempt ----");
    let resource_dir = match app.path().resource_dir() {
        Ok(dir) => dir,
        Err(err) => {
            spawn_log(&format!("resource_dir error: {err}"));
            return None;
        }
    };
    spawn_log(&format!("resource_dir: {}", resource_dir.display()));
    let Some(backend_path) = find_backend_resource(&resource_dir) else {
        spawn_log(&format!(
            "backend binary not found; checked {:?}",
            backend_resource_candidates(&resource_dir)
        ));
        return None;
    };
    spawn_log(&format!("backend_path: {}", backend_path.display()));

    let app_data_dir = match app.path().app_data_dir() {
        Ok(dir) => dir,
        Err(err) => {
            spawn_log(&format!("app_data_dir error: {err}"));
            return None;
        }
    };
    if let Err(err) = fs::create_dir_all(&app_data_dir) {
        spawn_log(&format!("app_data_dir create error: {err}"));
    }
    let db_path = app_data_dir.join(BACKEND_DATABASE_FILE);
    let db_url = format!("sqlite:///{}", db_path.display());
    spawn_log(&format!("db_url: {db_url}"));

    let log_path = log_dir.join("backend.log");
    spawn_log(&format!("backend_log: {}", log_path.display()));

    let mut cmd = Command::new(backend_path);
    cmd.env("SFO_RUST_DATABASE_URL", db_url)
        .env("SFO_RUST_BIND", BACKEND_BIND_ADDR)
        .env("SFO_TAURI", "1");

    match fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(log_path)
    {
        Ok(file) => {
            if let Ok(stdout_file) = file.try_clone() {
                cmd.stdout(Stdio::from(stdout_file));
            }
            cmd.stderr(Stdio::from(file));
        }
        Err(_) => {
            cmd.stdout(Stdio::null()).stderr(Stdio::null());
        }
    }

    match cmd.spawn() {
        Ok(child) => Some(child),
        Err(err) => {
            spawn_log(&format!("failed to start backend: {err}"));
            None
        }
    }
}

fn find_backend_resource(resource_dir: &std::path::Path) -> Option<std::path::PathBuf> {
    backend_resource_candidates(resource_dir)
        .into_iter()
        .find(|path| path.exists())
}

fn backend_resource_candidates(resource_dir: &std::path::Path) -> Vec<std::path::PathBuf> {
    let bin_dir = resource_dir.join("bin");
    vec![
        bin_dir.join(BACKEND_BINARY_NAME),
        bin_dir.join("sfo-server-aarch64-apple-darwin"),
        bin_dir.join("sfo-server-x86_64-apple-darwin"),
    ]
}

fn shutdown_backend(app: &tauri::AppHandle) {
    if let Some(state) = app.try_state::<BackendState>() {
        if let Some(mut child) = state
            .inner()
            .0
            .lock()
            .ok()
            .and_then(|mut guard| guard.take())
        {
            let _ = child.kill();
        }
    }
}

#[tauri::command]
fn get_api_token() -> Result<Option<String>, String> {
    credential_store::get_api_token()
}

#[tauri::command]
fn set_api_token(token: String) -> Result<(), String> {
    credential_store::set_api_token(&token)
}

#[tauri::command]
fn clear_api_token() -> Result<(), String> {
    credential_store::clear_api_token()
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let mut builder = tauri::Builder::default();

    if cfg!(debug_assertions) {
        builder = builder.plugin(
            tauri_plugin_log::Builder::default()
                .level(log::LevelFilter::Info)
                .build(),
        );
    }

    let app = builder
        .invoke_handler(tauri::generate_handler![
            get_api_token,
            set_api_token,
            clear_api_token,
        ])
        .setup(|app| {
            let child = spawn_backend(&app.handle());
            app.manage(BackendState(Mutex::new(child)));
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building tauri application");

    app.run(|app_handle, event| {
        if matches!(
            event,
            tauri::RunEvent::ExitRequested { .. } | tauri::RunEvent::Exit { .. }
        ) {
            shutdown_backend(app_handle);
        }
    });
}
