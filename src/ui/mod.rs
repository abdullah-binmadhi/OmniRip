//! OmniRip TUI module.

pub mod account_modal;
pub mod app;
pub mod archiver;
pub mod downloader;
pub mod gear_modal;
pub mod mode_modal;
pub mod nicotine_modal;
pub mod preset_modal;
pub mod setup_modal;
pub mod streaming_hub;
pub mod theme;
pub mod visuals;

pub use account_modal::{AccountModalAction, AccountSyncModal};

pub use app::App;
pub use archiver::{ArchiverState, FolderTemplate, TargetQuality};
pub use downloader::{AcquisitionPolicy, DownloaderState, Mp3Quality};
pub use gear_modal::GearWizardModal;
pub use mode_modal::{ModeModal, WorkstationMode};
pub use nicotine_modal::{NicotineModal, NicotineModalAction};
pub use preset_modal::{render_preset_modal, ModalKeyAction, PresetModalState};
pub use setup_modal::{SetupModalAction, SetupModalState};
pub use streaming_hub::StreamingHubState;
pub use theme::{ThemeKind, ThemePalette};
pub use visuals::{VisualGraphMode, VisualsDashboard};
