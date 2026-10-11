//! OmniRip: Audiophile Studio System EQ, Mastering Suite & Harvester in pure Rust.

pub mod autoeq;
pub mod driver;
pub mod dsp;
pub mod harvest;
pub mod ui;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
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

    let mut app = ui::App::new();
    app.run().await
}
