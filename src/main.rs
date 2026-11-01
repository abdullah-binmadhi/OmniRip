//! OmniRip: Audiophile Studio System EQ, Mastering Suite & Harvester in pure Rust.

use crossterm::cursor::Show;
use crossterm::event::DisableBracketedPaste;
use crossterm::execute;
use crossterm::terminal::{disable_raw_mode, LeaveAlternateScreen};

pub mod autoeq;
pub mod driver;
pub mod dsp;
pub mod harvest;
pub mod ui;

const USAGE: &str = "\
Usage:
  omnirip                              start the TUI
  omnirip driver [status|install|uninstall]
  omnirip feed [--file <path>]         feed raw 48 kHz f32 stereo PCM into the engine
  omnirip stream <url>                 stream an http(s) URL through the engine
  omnirip --help | --version";

/// What the process was asked to do.
#[derive(Debug, PartialEq, Eq)]
enum Command {
    Tui,
    Help,
    Version,
    Driver(Vec<String>),
    Feed(Vec<String>),
    Stream(Option<String>),
    Unknown(String),
}

/// Maps process arguments (program name first) to a command. Unknown flags are rejected rather than
/// silently starting the TUI.
fn parse_command(args: &[String]) -> Command {
    match args.get(1).map(String::as_str) {
        None | Some("--no-mic") => Command::Tui,
        Some("-h") | Some("--help") | Some("help") => Command::Help,
        Some("-V") | Some("--version") => Command::Version,
        Some("driver") => Command::Driver(args[2..].to_vec()),
        Some("feed") => Command::Feed(args[2..].to_vec()),
        Some("stream") => Command::Stream(args.get(2).cloned()),
        Some(other) => Command::Unknown(other.to_string()),
    }
}

/// Restores the terminal before a panic message is printed, so a crash never leaves raw mode on.
/// It also returns system output from a loopback device, so a crash does not leave the Mac silent.
fn install_panic_hook() {
    let default_hook = std::panic::take_hook();
    std::panic::set_hook(Box::new(move |info| {
        let _ = disable_raw_mode();
        let _ = execute!(std::io::stdout(), LeaveAlternateScreen, DisableBracketedPaste, Show);
        dsp::streamer::restore_system_output();
        default_hook(info);
    }));
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    install_panic_hook();
    harvest::bootstrap::ToolResolver::activate_user_tools_path();
    let args: Vec<String> = std::env::args().collect();

    match parse_command(&args) {
        Command::Help => {
            println!("{USAGE}");
            return Ok(());
        }
        Command::Version => {
            println!("omnirip {}", env!("CARGO_PKG_VERSION"));
            return Ok(());
        }
        Command::Driver(rest) => return driver::run_driver_cli(&rest),
        Command::Feed(rest) => return dsp::transport::run_feed_cli(&rest),
        Command::Stream(Some(url)) => return dsp::transport::run_stream_cli(&url),
        Command::Stream(None) => {
            eprintln!("Usage: omnirip stream <url>");
            std::process::exit(1);
        }
        Command::Unknown(arg) => {
            eprintln!("omnirip: unknown argument '{arg}'\n\n{USAGE}");
            std::process::exit(2);
        }
        Command::Tui => {}
    }

    // Input capture (the X key) always starts off on launch; `--no-mic` is still accepted and changes nothing.

    let mut app = ui::App::new();
    app.run().await
}

#[cfg(test)]
mod tests {
    use super::*;

    fn args(list: &[&str]) -> Vec<String> {
        list.iter().map(|s| s.to_string()).collect()
    }

    #[test]
    fn no_arguments_starts_the_tui() {
        assert_eq!(parse_command(&args(&["omnirip"])), Command::Tui);
    }

    #[test]
    fn no_mic_flag_still_starts_the_tui() {
        assert_eq!(parse_command(&args(&["omnirip", "--no-mic"])), Command::Tui);
    }

    #[test]
    fn help_and_version_are_recognised() {
        assert_eq!(parse_command(&args(&["omnirip", "--help"])), Command::Help);
        assert_eq!(parse_command(&args(&["omnirip", "-h"])), Command::Help);
        assert_eq!(parse_command(&args(&["omnirip", "--version"])), Command::Version);
        assert_eq!(parse_command(&args(&["omnirip", "-V"])), Command::Version);
    }

    #[test]
    fn unknown_flags_are_rejected_instead_of_starting_the_tui() {
        assert_eq!(
            parse_command(&args(&["omnirip", "--bogus"])),
            Command::Unknown("--bogus".to_string())
        );
    }

    #[test]
    fn subcommands_keep_their_arguments() {
        assert_eq!(
            parse_command(&args(&["omnirip", "driver", "status"])),
            Command::Driver(args(&["status"]))
        );
        assert_eq!(
            parse_command(&args(&["omnirip", "feed", "--file", "a.raw"])),
            Command::Feed(args(&["--file", "a.raw"]))
        );
        assert_eq!(
            parse_command(&args(&["omnirip", "stream", "https://example.com/x"])),
            Command::Stream(Some("https://example.com/x".to_string()))
        );
        assert_eq!(parse_command(&args(&["omnirip", "stream"])), Command::Stream(None));
    }
}
