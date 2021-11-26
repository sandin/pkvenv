#![windows_subsystem = "windows"]

use std::process::{Command, Stdio};
use std::io::{self, Write};


#[cfg(gui)]
const PYTHON_PATH: &str = "Python\\pythonw.exe";
#[cfg(not(gui))]
const PYTHON_PATH: &str = "Python\\python.exe";


fn main() {
    let status = Command::new(PYTHON_PATH)
            .args(&["-m", "pkvenv_main"])
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .status()
            //.output()
            .expect("failed to execute process");
    println!("process exited with: {:?}", status);
}
