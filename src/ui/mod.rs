//! OmniRip TUI module.

pub mod app;
pub mod downloader;
pub mod mode_modal;
pub mod nicotine_modal;
pub mod theme;
pub mod visuals;

pub use app::App;
pub use downloader::{AcquisitionPolicy, DownloaderState, Mp3Quality};
pub use mode_modal::{ModeModal, WorkstationMode};
pub use nicotine_modal::{NicotineModal, NicotineModalAction};
pub use theme::{ThemeKind, ThemePalette};
pub use visuals::{VisualGraphMode, VisualsDashboard};
