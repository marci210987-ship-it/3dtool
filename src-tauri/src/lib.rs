use std::path::{Path, PathBuf};
use std::process::{Child, Command};
use std::sync::Mutex;

use tauri::Manager;

struct Dienst(Mutex<Option<Child>>);

fn wurzel() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .expect("Projektwurzel")
        .to_path_buf()
}

fn wurzel_zur_laufzeit(app: &tauri::AppHandle) -> PathBuf {
    if let Ok(dir) = app.path().resource_dir() {
        if dir.join("sidecar").join("server.py").is_file() {
            return dir;
        }
    }
    wurzel()
}

fn python_befehl() -> Option<Command> {
    for name in ["python3", "python", "py"] {
        let mut cmd = Command::new(name);
        cmd.arg("--version");
        if cmd.output().map(|o| o.status.success()).unwrap_or(false) {
            return Some(Command::new(name));
        }
    }
    None
}

fn dienst_starten(root: &Path) -> Option<Child> {
    let mut cmd = python_befehl()?;
    cmd.arg("-m")
        .arg("sidecar.server")
        .current_dir(root)
        .env("PYTHONPATH", root)
        .env("PYTHONUNBUFFERED", "1")
        .env("CADSTUDIO_HOST", "127.0.0.1")
        .env("CADSTUDIO_PORT", "47321");
    cmd.spawn().ok()
}

#[tauri::command]
fn dialog_speichern() -> Option<String> {
    rfd::FileDialog::new()
        .set_title("Projekt speichern")
        .add_filter("CAD Studio", &["json"])
        .save_file()
        .map(|pfad| pfad.display().to_string())
}

#[tauri::command]
fn dialog_oeffnen() -> Option<String> {
    rfd::FileDialog::new()
        .set_title("Projekt öffnen")
        .add_filter("CAD Studio", &["json"])
        .pick_file()
        .map(|pfad| pfad.display().to_string())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .setup(|app| {
            let root = wurzel_zur_laufzeit(app.handle());
            let kind = dienst_starten(&root);
            app.manage(Dienst(Mutex::new(kind)));
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![dialog_speichern, dialog_oeffnen])
        .build(tauri::generate_context!())
        .expect("CAD Studio konnte nicht starten")
        .run(|app, event| {
            if let tauri::RunEvent::Exit = event {
                if let Some(dienst) = app.try_state::<Dienst>() {
                    if let Ok(mut kind) = dienst.0.lock() {
                        if let Some(mut prozess) = kind.take() {
                            let _ = prozess.kill();
                        }
                    }
                }
            }
        });
}
