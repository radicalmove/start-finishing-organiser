use std::{
  fs,
  io::Write,
  process::{Child, Command, Stdio},
  sync::Mutex,
};

use tauri::Manager;

struct BackendState(Mutex<Option<Child>>);

fn should_spawn_backend() -> bool {
  if let Ok(flag) = std::env::var("SFO_SPAWN_BACKEND") {
    return flag == "1" || flag.eq_ignore_ascii_case("true");
  }
  !cfg!(debug_assertions)
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
  let backend_path = resource_dir.join("bin").join("sfo-backend");
  if !backend_path.exists() {
    spawn_log(&format!(
      "backend binary not found at {}",
      backend_path.display()
    ));
    return None;
  }
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
  let db_path = app_data_dir.join("sfo.db");
  let db_url = format!("sqlite:///{}", db_path.display());
  spawn_log(&format!("db_url: {db_url}"));

  let app_config_dir = match app.path().app_config_dir() {
    Ok(dir) => dir,
    Err(err) => {
      spawn_log(&format!("app_config_dir error: {err}"));
      return None;
    }
  };
  if let Err(err) = fs::create_dir_all(&app_config_dir) {
    spawn_log(&format!("app_config_dir create error: {err}"));
  }

  let creds_target = app_config_dir.join("gmail_credentials.json");
  if !creds_target.exists() {
    let bundled_creds = resource_dir.join("resources").join("gmail_credentials.json");
    if bundled_creds.exists() {
      let should_copy = fs::metadata(&bundled_creds)
        .map(|meta| meta.len() > 0)
        .unwrap_or(false);
      if should_copy {
        if let Err(err) = fs::copy(&bundled_creds, &creds_target) {
          spawn_log(&format!("copy gmail credentials error: {err}"));
        }
      } else {
        spawn_log("bundled gmail credentials empty; skipping copy");
      }
    }
  }
  let token_path = app_config_dir.join("gmail_token.json");

  let log_path = log_dir.join("backend.log");
  spawn_log(&format!("backend_log: {}", log_path.display()));

  let mut cmd = Command::new(backend_path);
  cmd.env("SFO_DATABASE_URL", db_url)
    .env("SFO_GMAIL_CLIENT_SECRETS", &creds_target)
    .env("SFO_GMAIL_TOKEN_PATH", &token_path)
    .env("SFO_HOST", "127.0.0.1")
    .env("SFO_PORT", "8000")
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
    .setup(|app| {
      let child = spawn_backend(&app.handle());
      app.manage(BackendState(Mutex::new(child)));
      Ok(())
    })
    .build(tauri::generate_context!())
    .expect("error while building tauri application");

  app.run(|app_handle, event| {
    if matches!(event, tauri::RunEvent::ExitRequested { .. } | tauri::RunEvent::Exit { .. }) {
      shutdown_backend(app_handle);
    }
  });
}
