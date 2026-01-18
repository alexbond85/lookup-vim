use tauri::Manager;
use tauri_plugin_shell::ShellExt;
use std::sync::Mutex;
use std::time::Duration;

// Store the sidecar process handle
struct ServerState {
    child: Mutex<Option<tauri_plugin_shell::process::CommandChild>>,
}

#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! You've been greeted from Rust!", name)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_shell::init())
        .manage(ServerState {
            child: Mutex::new(None),
        })
        .setup(|app| {
            // Spawn the Python backend sidecar
            let sidecar_command = app.shell().sidecar("vimlookup-server").unwrap();

            let (mut rx, child) = sidecar_command.spawn().expect("Failed to spawn sidecar");

            // Store the child process handle for cleanup
            let state = app.state::<ServerState>();
            *state.child.lock().unwrap() = Some(child);

            // Log sidecar output in a separate thread
            tauri::async_runtime::spawn(async move {
                use tauri_plugin_shell::process::CommandEvent;
                while let Some(event) = rx.recv().await {
                    match event {
                        CommandEvent::Stdout(line) => {
                            let line_str = String::from_utf8_lossy(&line);
                            println!("[server] {}", line_str);
                        }
                        CommandEvent::Stderr(line) => {
                            let line_str = String::from_utf8_lossy(&line);
                            eprintln!("[server] {}", line_str);
                        }
                        CommandEvent::Error(err) => {
                            eprintln!("[server error] {}", err);
                        }
                        CommandEvent::Terminated(status) => {
                            println!("[server] Process terminated with status: {:?}", status);
                            break;
                        }
                        _ => {}
                    }
                }
            });

            // Wait a moment for the server to start
            std::thread::sleep(Duration::from_millis(1500));

            println!("Backend server started");
            Ok(())
        })
        .on_window_event(|window, event| {
            // Kill the sidecar when the window closes
            if let tauri::WindowEvent::CloseRequested { .. } = event {
                let state = window.state::<ServerState>();
                let mut guard = state.child.lock().unwrap();
                if let Some(child) = guard.take() {
                    let _ = child.kill();
                    println!("Backend server stopped");
                }
            }
        })
        .invoke_handler(tauri::generate_handler![greet])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
