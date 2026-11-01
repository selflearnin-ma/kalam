// The whole app is the web core in web/dist (Pyodide + SymPy run in the webview).
// Rust only opens the window and provides the save dialog and file writing.
#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_fs::init())
        .run(tauri::generate_context!())
        .expect("error while running Kalam");
}
