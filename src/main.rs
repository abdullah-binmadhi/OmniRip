//! OmniRip: Audiophile Studio System EQ, Mastering Suite & Harvester in pure Rust.

pub mod autoeq;
pub mod driver;
pub mod dsp;
pub mod harvest;
pub mod ui;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    harvest::bootstrap::ToolResolver::activate_user_tools_path();
    let args: Vec<String> = std::env::args().collect();
    if args.len() > 1 && args[1] == "driver" {
        return driver::run_driver_cli(&args[2..]);
    }
    if args.len() > 1 && args[1] == "feed" {
        return dsp::transport::run_feed_cli(&args[2..]);
    }
    if args.len() > 1 && args[1] == "stream" {
        if let Some(url) = args.get(2) {
            return dsp::transport::run_stream_cli(url);
        } else {
            eprintln!("Usage: omnirip stream <url>");
            std::process::exit(1);
        }
    }
    if args.len() > 1 && args[1] == "mic" {
        return dsp::streamer::run_mic_cli(&args[2..]);
    }

    if args.iter().any(|a| a == "--no-mic") {
        dsp::volume_storage::save_mic_setting(false);
    } else {
        // Guarantee system loopback capture is active on launch so sound engine works immediately
        dsp::volume_storage::save_mic_setting(true);
    }

    let mut app = ui::App::new();
    app.run().await
}
