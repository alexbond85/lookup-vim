use tauri::{Manager, RunEvent};
use tauri_plugin_shell::ShellExt;
use std::sync::Mutex;
use std::time::Duration;
use std::net::TcpStream;

const SERVER_PORT: u16 = 2989;
const MAX_STARTUP_WAIT_MS: u64 = 30000; // 30 seconds max wait
const HEALTH_CHECK_INTERVAL_MS: u64 = 200; // Check every 200ms

// Store the sidecar process handle
struct ServerState {
    child: Mutex<Option<tauri_plugin_shell::process::CommandChild>>,
}

/// Check if the server is ready by attempting a TCP connection
fn is_server_ready() -> bool {
    TcpStream::connect_timeout(
        &format!("127.0.0.1:{}", SERVER_PORT).parse().unwrap(),
        Duration::from_millis(100)
    ).is_ok()
}

/// Wait for the server to be ready with timeout
fn wait_for_server_ready() -> bool {
    let start = std::time::Instant::now();
    let timeout = Duration::from_millis(MAX_STARTUP_WAIT_MS);
    let interval = Duration::from_millis(HEALTH_CHECK_INTERVAL_MS);

    println!("Waiting for backend server to be ready on port {}...", SERVER_PORT);

    while start.elapsed() < timeout {
        if is_server_ready() {
            println!("Backend server is ready! (took {:?})", start.elapsed());
            return true;
        }
        std::thread::sleep(interval);
    }

    eprintln!("Backend server failed to start within {} seconds", MAX_STARTUP_WAIT_MS / 1000);
    false
}

/// Kill the sidecar process and any orphaned processes on the port
fn kill_sidecar(state: &ServerState) {
    // First, kill the managed child process
    let mut guard = state.child.lock().unwrap();
    if let Some(child) = guard.take() {
        println!("Killing backend server...");
        let _ = child.kill();
    }
    drop(guard); // Release the lock

    // Also kill any process still listening on the port (handles orphaned uvicorn workers)
    // Use lsof to find PIDs and kill them
    println!("Cleaning up any remaining processes on port {}...", SERVER_PORT);
    let _ = std::process::Command::new("sh")
        .args(["-c", &format!("lsof -ti :{} | xargs kill -9 2>/dev/null", SERVER_PORT)])
        .output();

    // Give it a moment to clean up
    std::thread::sleep(Duration::from_millis(100));
    println!("Backend server stopped");
}

#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! You've been greeted from Rust!", name)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let app = tauri::Builder::default()
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

            // Wait for the server to be ready (with health check)
            if !wait_for_server_ready() {
                eprintln!("Warning: Backend server may not be fully ready");
            }

            println!("Backend server started");
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![greet])
        .build(tauri::generate_context!())
        .expect("error while building tauri application");

    // Run the app with event handling for proper cleanup
    app.run(|app_handle, event| {
        match event {
            RunEvent::ExitRequested { .. } | RunEvent::Exit => {
                // Kill the sidecar when the app exits
                let state = app_handle.state::<ServerState>();
                kill_sidecar(&state);
            }
            _ => {}
        }
    });
}
