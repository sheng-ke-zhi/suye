use std::process::Command;

fn run(arguments: &[&str]) -> std::process::Output {
    Command::new(env!("CARGO_BIN_EXE_suye"))
        .args(arguments)
        .output()
        .unwrap()
}

#[test]
fn help_version_and_invalid_arguments() {
    for arguments in [&["--help"][..], &["-h"], &["--version"]] {
        assert!(run(arguments).status.success());
    }
    assert_eq!(run(&["--version"]).stdout, b"suye 0.1.0\n");
    for arguments in [&[][..], &["unknown"], &["doctor", "extra"]] {
        assert_eq!(run(arguments).status.code(), Some(2));
    }
}

#[test]
fn empty_or_unset_path_reports_all_tools_missing() {
    for unset in [false, true] {
        let mut command = Command::new(env!("CARGO_BIN_EXE_suye"));
        command.arg("doctor").env("PATH", "");
        if unset {
            command.env_remove("PATH");
        }
        let output = command.output().unwrap();
        assert_eq!(output.status.code(), Some(1));
        assert_eq!(
            String::from_utf8_lossy(&output.stdout)
                .matches("[MISSING]")
                .count(),
            4
        );
    }
}

#[cfg(unix)]
#[test]
fn doctor_checks_executable_files_without_running_them_or_leaking_secrets() {
    use std::fs;
    use std::os::unix::fs::PermissionsExt;

    let directory = std::env::temp_dir().join(format!("suye-test-{}", std::process::id()));
    fs::create_dir(&directory).unwrap();
    let tools = ["git", "python3", "cargo", "rustc"];
    let diagnose = || {
        Command::new(env!("CARGO_BIN_EXE_suye"))
            .arg("doctor")
            .env("PATH", &directory)
            .env("SUYE_SECRET", "must-not-appear")
            .output()
            .unwrap()
    };
    let empty = diagnose();
    assert_eq!(empty.status.code(), Some(1));
    assert_eq!(
        String::from_utf8_lossy(&empty.stdout)
            .matches("[MISSING]")
            .count(),
        4
    );
    for tool in tools {
        let path = directory.join(tool);
        fs::write(&path, b"not an executable program").unwrap();
        fs::set_permissions(path, fs::Permissions::from_mode(0o755)).unwrap();
    }
    let healthy = diagnose();
    assert!(healthy.status.success());
    let expected: String = tools.iter().map(|tool| format!("[OK] {tool}\n")).collect();
    assert_eq!(String::from_utf8_lossy(&healthy.stdout), expected);
    fs::set_permissions(directory.join("cargo"), fs::Permissions::from_mode(0o644)).unwrap();
    fs::remove_file(directory.join("rustc")).unwrap();
    fs::create_dir(directory.join("rustc")).unwrap();
    let missing = diagnose();
    assert_eq!(missing.status.code(), Some(1));
    let output = String::from_utf8_lossy(&missing.stdout);
    assert!(output.contains("[MISSING] cargo"));
    assert!(output.contains("[MISSING] rustc"));
    assert!(!output.contains("must-not-appear"));
    assert!(missing.stderr.is_empty());
    fs::remove_dir_all(directory).unwrap();
}
