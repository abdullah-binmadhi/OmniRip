//! OmniRip: Audiophile Studio System EQ, Mastering Suite & Harvester in pure Rust.

pub mod autoeq;
pub mod dsp;
pub mod harvest;
pub mod ui;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let mut app = ui::App::new();
    app.run().await
}
