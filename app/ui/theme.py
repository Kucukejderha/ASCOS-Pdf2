"""Pdf2 tasarım token'ları.

QSS özel değişken desteklemediği için token'lar Python sözlüğü olarak tutulur
ve QSS string'ine formatlanır. Yeni widget stilleri buradaki token'lardan
beslenmeli; sabit renk kodu QSS içine gömülmemeli.
"""

from __future__ import annotations

TOKENS: dict[str, str] = {
    "paper": "#F3F1EC",
    "surface": "#FFFFFF",
    "ink": "#22252A",
    "ink_hover": "#33373D",
    "muted": "#6E7278",
    "line": "#DCD8CF",
    "line_strong": "#C4BFB4",
    "accent": "#B3372A",
    "accent_soft": "#F7EAE8",
    "success": "#4E7A57",
    "warning": "#9A6B1F",
    "selection": "#ECE9E2",
    "hover": "#F6F4EF",
}

FONT_DISPLAY = "Bahnschrift"
FONT_BODY = "Segoe UI"
FONT_MONO = "Consolas"


def stylesheet() -> str:
    t = TOKENS
    return f"""
* {{
    font-family: "{FONT_BODY}";
    font-size: 10pt;
}}

QMainWindow, QDialog {{
    background: {t["paper"]};
}}

QWidget#Canvas {{
    background: {t["paper"]};
}}

QFrame#Header {{
    background: {t["surface"]};
    border-bottom: 1px solid {t["line"]};
}}

QLabel#Wordmark {{
    font-family: "{FONT_DISPLAY}";
    font-size: 17pt;
    font-weight: 600;
    color: {t["ink"]};
}}

QLabel#Subtitle {{
    color: {t["muted"]};
    font-size: 9.5pt;
}}

QLabel#SectionTitle {{
    font-family: "{FONT_DISPLAY}";
    font-size: 11pt;
    font-weight: 600;
    color: {t["ink"]};
}}

QLabel#Muted {{
    color: {t["muted"]};
}}

QLabel#Mono {{
    font-family: "{FONT_MONO}";
    color: {t["muted"]};
}}

QTabWidget::pane {{
    border: none;
    background: {t["paper"]};
}}

QTabWidget::tab-bar {{
    alignment: left;
    left: 12px;
}}

QTabBar::tab {{
    background: transparent;
    color: {t["muted"]};
    padding: 10px 2px;
    margin-right: 28px;
    border-bottom: 2px solid transparent;
    font-family: "{FONT_DISPLAY}";
    font-size: 11pt;
}}

QTabBar::tab:hover {{
    color: {t["ink"]};
}}

QTabBar::tab:selected {{
    color: {t["ink"]};
    border-bottom: 2px solid {t["accent"]};
}}

QFrame#Panel {{
    background: {t["surface"]};
    border: 1px solid {t["line"]};
    border-radius: 2px;
}}

QFrame#ToolStrip {{
    background: {t["paper"]};
    border-right: 1px solid {t["line"]};
}}

QFrame#ToolStrip QPushButton {{
    text-align: left;
    padding: 4px 10px;
}}

QLabel#PanelTitle {{
    font-family: "{FONT_DISPLAY}";
    font-size: 10.5pt;
    font-weight: 600;
    color: {t["ink"]};
}}

QPushButton {{
    background: {t["surface"]};
    color: {t["ink"]};
    border: 1px solid {t["line_strong"]};
    border-radius: 2px;
    padding: 6px 14px;
}}

QPushButton:hover {{
    border-color: {t["ink"]};
}}

QPushButton:pressed {{
    background: {t["hover"]};
}}

QPushButton:checked {{
    background: {t["selection"]};
    border-color: {t["ink"]};
    font-weight: 600;
}}

QPushButton:disabled {{
    color: {t["muted"]};
    border-color: {t["line"]};
}}

QPushButton#Primary {{
    background: {t["ink"]};
    color: {t["surface"]};
    border: 1px solid {t["ink"]};
    font-weight: 600;
    padding: 8px 22px;
}}

QPushButton#Primary:hover {{
    background: {t["ink_hover"]};
    border-color: {t["ink_hover"]};
}}

QPushButton#Primary:disabled {{
    background: {t["line_strong"]};
    border-color: {t["line_strong"]};
    color: {t["surface"]};
}}

QPushButton#Danger {{
    background: transparent;
    color: {t["accent"]};
    border: 1px solid {t["accent"]};
}}

QPushButton#Danger:hover {{
    background: {t["accent_soft"]};
}}

QPushButton#Ghost {{
    background: transparent;
    border: none;
    color: {t["muted"]};
    padding: 4px 8px;
}}

QPushButton#Ghost:hover {{
    color: {t["ink"]};
}}

QLineEdit, QComboBox, QSpinBox {{
    background: {t["surface"]};
    color: {t["ink"]};
    border: 1px solid {t["line_strong"]};
    border-radius: 2px;
    padding: 5px 8px;
    selection-background-color: {t["ink"]};
    selection-color: {t["surface"]};
}}

QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{
    border-color: {t["ink"]};
}}

QLineEdit:disabled, QComboBox:disabled {{
    background: {t["paper"]};
    color: {t["muted"]};
}}

QComboBox::drop-down {{
    border: none;
    width: 22px;
}}

QComboBox QAbstractItemView {{
    background: {t["surface"]};
    border: 1px solid {t["line_strong"]};
    selection-background-color: {t["selection"]};
    selection-color: {t["ink"]};
    outline: none;
}}

QCheckBox, QRadioButton {{
    color: {t["ink"]};
    spacing: 7px;
}}

QCheckBox::indicator, QRadioButton::indicator {{
    width: 14px;
    height: 14px;
    border: 1px solid {t["line_strong"]};
    background: {t["surface"]};
}}

QCheckBox::indicator {{
    border-radius: 2px;
}}

QRadioButton::indicator {{
    border-radius: 8px;
}}

QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
    background: {t["ink"]};
    border-color: {t["ink"]};
}}

QListWidget {{
    background: {t["surface"]};
    border: none;
    outline: none;
}}

QListWidget::item {{
    color: {t["ink"]};
    padding: 8px 10px;
    border-bottom: 1px solid {t["line"]};
}}

QListWidget::item:hover {{
    background: {t["hover"]};
}}

QListWidget::item:selected {{
    background: {t["selection"]};
    color: {t["ink"]};
}}

QScrollArea {{
    border: none;
    background: transparent;
}}

QProgressBar {{
    background: {t["line"]};
    border: none;
    border-radius: 2px;
    height: 6px;
    text-align: center;
}}

QProgressBar::chunk {{
    background: {t["ink"]};
    border-radius: 2px;
}}

QProgressBar[done="true"]::chunk {{
    background: {t["success"]};
}}

QProgressBar[error="true"]::chunk {{
    background: {t["accent"]};
}}

QStatusBar {{
    background: {t["paper"]};
    color: {t["muted"]};
    border-top: 1px solid {t["line"]};
}}

QStatusBar::item {{
    border: none;
}}

QToolTip {{
    background: {t["ink"]};
    color: {t["surface"]};
    border: none;
    padding: 5px 8px;
}}

QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 0;
}}

QScrollBar::handle:vertical {{
    background: {t["line_strong"]};
    border-radius: 2px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background: {t["muted"]};
}}

QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
    margin: 0;
}}

QScrollBar::handle:horizontal {{
    background: {t["line_strong"]};
    border-radius: 2px;
    min-width: 30px;
}}

QScrollBar::add-line, QScrollBar::sub-line {{
    width: 0;
    height: 0;
}}

QSplitter::handle {{
    background: {t["line"]};
    width: 1px;
}}

QMenu {{
    background: {t["surface"]};
    border: 1px solid {t["line_strong"]};
}}

QMenu::item {{
    padding: 6px 22px;
    color: {t["ink"]};
}}

QMenu::item:selected {{
    background: {t["selection"]};
}}
"""
