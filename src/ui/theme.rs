//! Multi-Palette Theme Engine for OmniRip TUI.
//! Supports 7 high-contrast color palettes: Cyberpunk Neon, Tokyo Night, Monokai Pro,
//! Matrix Green, Nordic Frost, Dracula Night, and Amber CRT.

use ratatui::style::Color;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ThemeKind {
    CyberpunkNeon,
    TokyoNight,
    MonokaiPro,
    MatrixGreen,
    NordicFrost,
    DraculaNight,
    AmberCrt,
}

#[derive(Debug, Clone, Copy)]
pub struct ThemePalette {
    pub kind: ThemeKind,
    pub name: &'static str,
    pub primary: Color,
    pub secondary: Color,
    pub accent: Color,
    pub background: Color,
    pub surface: Color,
    pub border: Color,
    pub text: Color,
    pub text_dim: Color,
    pub success: Color,
    pub warning: Color,
    pub error: Color,
}

impl ThemePalette {
    pub fn for_kind(kind: ThemeKind) -> Self {
        match kind {
            ThemeKind::CyberpunkNeon => Self {
                kind,
                name: "Cyberpunk Neon",
                primary: Color::Rgb(255, 0, 127),      // Hot Pink
                secondary: Color::Rgb(0, 240, 255),    // Neon Cyan
                accent: Color::Rgb(255, 230, 0),       // Laser Yellow
                background: Color::Rgb(13, 9, 26),     // Deep Void
                surface: Color::Rgb(26, 20, 53),       // Panel
                border: Color::Rgb(0, 240, 255),
                text: Color::White,
                text_dim: Color::Rgb(140, 130, 170),
                success: Color::Rgb(0, 255, 159),
                warning: Color::Rgb(255, 170, 0),
                error: Color::Rgb(255, 51, 102),
            },
            ThemeKind::TokyoNight => Self {
                kind,
                name: "Tokyo Night",
                primary: Color::Rgb(125, 207, 255),    // Sky Cyan
                secondary: Color::Rgb(187, 154, 247),  // Lilac
                accent: Color::Rgb(224, 175, 104),     // Amber
                background: Color::Rgb(26, 27, 38),    // Deep Navy
                surface: Color::Rgb(36, 40, 59),
                border: Color::Rgb(125, 207, 255),
                text: Color::Rgb(192, 202, 245),
                text_dim: Color::Rgb(86, 95, 137),
                success: Color::Rgb(158, 206, 106),
                warning: Color::Rgb(224, 175, 104),
                error: Color::Rgb(247, 118, 142),
            },
            ThemeKind::MonokaiPro => Self {
                kind,
                name: "Monokai Pro",
                primary: Color::Rgb(255, 216, 102),    // Warm Amber
                secondary: Color::Rgb(169, 220, 118),  // Pastel Green
                accent: Color::Rgb(255, 97, 136),      // Magenta
                background: Color::Rgb(45, 42, 46),    // Charcoal
                surface: Color::Rgb(64, 60, 65),
                border: Color::Rgb(255, 216, 102),
                text: Color::Rgb(252, 252, 250),
                text_dim: Color::Rgb(114, 112, 114),
                success: Color::Rgb(169, 220, 118),
                warning: Color::Rgb(255, 216, 102),
                error: Color::Rgb(255, 97, 136),
            },
            ThemeKind::MatrixGreen => Self {
                kind,
                name: "Matrix Green",
                primary: Color::Rgb(0, 255, 65),       // Phosphor Green
                secondary: Color::Rgb(0, 143, 17),     // Forest Green
                accent: Color::Rgb(180, 255, 180),
                background: Color::Rgb(13, 2, 8),      // Pure Dark
                surface: Color::Rgb(20, 30, 20),
                border: Color::Rgb(0, 255, 65),
                text: Color::Rgb(0, 255, 65),
                text_dim: Color::Rgb(0, 100, 20),
                success: Color::Rgb(0, 255, 65),
                warning: Color::Rgb(180, 255, 0),
                error: Color::Rgb(255, 50, 50),
            },
            ThemeKind::NordicFrost => Self {
                kind,
                name: "Nordic Frost",
                primary: Color::Rgb(136, 192, 208),    // Frost Cyan
                secondary: Color::Rgb(129, 161, 193),  // Glacial Blue
                accent: Color::Rgb(235, 203, 139),     // Sun Yellow
                background: Color::Rgb(46, 52, 64),    // Polar Night
                surface: Color::Rgb(59, 66, 82),
                border: Color::Rgb(136, 192, 208),
                text: Color::Rgb(236, 239, 244),
                text_dim: Color::Rgb(140, 150, 170),
                success: Color::Rgb(163, 190, 140),
                warning: Color::Rgb(235, 203, 139),
                error: Color::Rgb(191, 97, 106),
            },
            ThemeKind::DraculaNight => Self {
                kind,
                name: "Dracula Night",
                primary: Color::Rgb(189, 147, 249),    // Purple
                secondary: Color::Rgb(255, 121, 198),  // Pink
                accent: Color::Rgb(139, 233, 253),     // Cyan
                background: Color::Rgb(40, 42, 54),    // Dark Blue
                surface: Color::Rgb(68, 71, 90),
                border: Color::Rgb(189, 147, 249),
                text: Color::Rgb(248, 248, 242),
                text_dim: Color::Rgb(98, 114, 164),
                success: Color::Rgb(80, 250, 123),
                warning: Color::Rgb(241, 250, 140),
                error: Color::Rgb(255, 85, 85),
            },
            ThemeKind::AmberCrt => Self {
                kind,
                name: "Amber CRT",
                primary: Color::Rgb(255, 176, 0),      // Amber Glow
                secondary: Color::Rgb(200, 130, 0),    // Dark Amber
                accent: Color::Rgb(255, 220, 100),
                background: Color::Rgb(26, 17, 0),     // Retro Phosphor Background
                surface: Color::Rgb(45, 30, 0),
                border: Color::Rgb(255, 176, 0),
                text: Color::Rgb(255, 176, 0),
                text_dim: Color::Rgb(150, 95, 0),
                success: Color::Rgb(255, 200, 50),
                warning: Color::Rgb(255, 150, 0),
                error: Color::Rgb(255, 70, 0),
            },
        }
    }

    pub fn cycle(&mut self) {
        let next_kind = match self.kind {
            ThemeKind::CyberpunkNeon => ThemeKind::TokyoNight,
            ThemeKind::TokyoNight => ThemeKind::MonokaiPro,
            ThemeKind::MonokaiPro => ThemeKind::MatrixGreen,
            ThemeKind::MatrixGreen => ThemeKind::NordicFrost,
            ThemeKind::NordicFrost => ThemeKind::DraculaNight,
            ThemeKind::DraculaNight => ThemeKind::AmberCrt,
            ThemeKind::AmberCrt => ThemeKind::CyberpunkNeon,
        };
        *self = Self::for_kind(next_kind);
    }
}

impl Default for ThemePalette {
    fn default() -> Self {
        Self::for_kind(ThemeKind::CyberpunkNeon)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_theme_cycle() {
        let mut theme = ThemePalette::default();
        assert_eq!(theme.kind, ThemeKind::CyberpunkNeon);
        theme.cycle();
        assert_eq!(theme.kind, ThemeKind::TokyoNight);
        theme.cycle();
        assert_eq!(theme.kind, ThemeKind::MonokaiPro);
    }
}
