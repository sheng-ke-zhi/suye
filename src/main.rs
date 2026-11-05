use std::env;
use std::fs;
use std::path::Path;
use std::process::ExitCode;

const TOOLS: [&str; 4] = ["git", "python3", "cargo", "rustc"];

fn is_executable(path: &Path) -> bool {
    let Ok(metadata) = fs::metadata(path) else {
        return false;
    };
    if !metadata.is_file() {
        return false;
    }
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        metadata.permissions().mode() & 0o111 != 0
    }
    #[cfg(not(unix))]
    {
        true
    }
}

fn doctor() -> ExitCode {
    let search_path = env::var_os("PATH").unwrap_or_default();
    let mut missing = false;
    for tool in TOOLS {
        let filename = format!("{tool}{}", env::consts::EXE_SUFFIX);
        let available = !search_path.is_empty()
            && env::split_paths(&search_path)
                .any(|directory| is_executable(&directory.join(&filename)));
        let status = if available { "OK" } else { "MISSING" };
        println!("[{status}] {tool}");
        missing |= !available;
    }
    if missing {
        println!("Make missing tools executable and available on PATH, then rerun suye doctor.");
    }
    ExitCode::from(u8::from(missing))
}

fn main() -> ExitCode {
    let arguments: Vec<_> = env::args_os().skip(1).collect();
    if arguments.len() == 1 {
        if arguments[0] == "doctor" {
            return doctor();
        }
        if arguments[0] == "--version" {
            println!("suye {}", env!("CARGO_PKG_VERSION"));
            return ExitCode::SUCCESS;
        }
        if arguments[0] == "--help" || arguments[0] == "-h" {
            println!("Read-only development toolchain diagnostics.\nUsage: suye doctor | --version | --help");
            return ExitCode::SUCCESS;
        }
    }
    eprintln!("Usage: suye doctor | --version | --help");
    ExitCode::from(2)
}
