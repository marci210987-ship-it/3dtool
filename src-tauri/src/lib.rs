use std::fs::File;
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use std::time::{SystemTime, UNIX_EPOCH};

use tauri::Manager;

#[cfg(windows)]
use std::os::windows::process::CommandExt;

/// Unter Windows keine Konsolenfenster für Kindprozesse.
#[cfg(windows)]
const KEIN_FENSTER: u32 = 0x0800_0000;

fn neues_token() -> String {
    let nanos = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|dauer| dauer.as_nanos())
        .unwrap_or(0);
    let mut wert = nanos ^ ((std::process::id() as u128) << 64) ^ 0xA5A5_F00D_C0FF_EE11;
    let mut text = String::new();
    for _ in 0..4 {
        wert = wert
            .wrapping_mul(0x9E37_79B9_7F4A_7C15)
            .wrapping_add(0xBF58_476D_1CE4_E5B9);
        text.push_str(&format!("{wert:032x}"));
    }
    text
}

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

/// Pfad des mitgelieferten Pythons (Installer) im Ressourcenordner.
fn eingebettetes_python(root: &Path) -> Option<PathBuf> {
    let pfad = if cfg!(windows) {
        root.join("python").join("python.exe")
    } else {
        root.join("python").join("bin").join("python3")
    };
    pfad.is_file().then_some(pfad)
}

fn befehl_ohne_fenster(programm: &Path) -> Command {
    let mut cmd = Command::new(programm);
    #[cfg(windows)]
    cmd.creation_flags(KEIN_FENSTER);
    cmd
}

/// Bevorzugt das mitgelieferte Python, sonst ein vorhandenes (Entwicklung, Linux/macOS).
fn python_befehl(root: &Path) -> Option<Command> {
    if let Some(exe) = eingebettetes_python(root) {
        return Some(befehl_ohne_fenster(&exe));
    }
    for name in ["python3", "python", "py"] {
        let mut probe = befehl_ohne_fenster(Path::new(name));
        probe.arg("--version");
        if probe.output().map(|o| o.status.success()).unwrap_or(false) {
            return Some(befehl_ohne_fenster(Path::new(name)));
        }
    }
    None
}

/// Protokolldatei des Dienstes im Programmordner des Benutzers (`dienst.log`), falls anlegbar.
fn dienst_log() -> Option<File> {
    let basis = std::env::var_os("APPDATA")
        .map(PathBuf::from)
        .or_else(|| std::env::var_os("HOME").map(|h| PathBuf::from(h).join(".config")))?;
    let ordner = basis.join(if cfg!(windows) { "CADStudio" } else { "cad-studio" });
    std::fs::create_dir_all(&ordner).ok()?;
    File::create(ordner.join("dienst.log")).ok()
}

fn dienst_starten(root: &Path, token: &str) -> Option<Child> {
    let mut cmd = python_befehl(root)?;
    // Das mitgelieferte Python liest seine Suchpfade aus python312._pth (dort steht der Ordner darüber);
    // PYTHONPATH gilt für ein vorhandenes System-Python.
    cmd.arg("-m")
        .arg("sidecar.server")
        .current_dir(root)
        .stdin(Stdio::null())
        .stdout(dienst_log().map(Stdio::from).unwrap_or_else(Stdio::null))
        .stderr(dienst_log().map(Stdio::from).unwrap_or_else(Stdio::null))
        .env("PYTHONPATH", root)
        .env("PYTHONUTF8", "1")
        .env("PYTHONDONTWRITEBYTECODE", "1")
        .env("PYTHONUNBUFFERED", "1")
        .env("CADSTUDIO_HOST", "127.0.0.1")
        .env("CADSTUDIO_PORT", "47321")
        .env("CADSTUDIO_TOKEN", token);
    cmd.spawn().ok()
}

#[tauri::command]
fn sitzungstoken(token: tauri::State<String>) -> String {
    token.inner().clone()
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
            let token = neues_token();
            let root = wurzel_zur_laufzeit(app.handle());
            let kind = dienst_starten(&root, &token);
            app.manage(token);
            app.manage(Dienst(Mutex::new(kind)));
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![sitzungstoken, dialog_speichern, dialog_oeffnen])
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
