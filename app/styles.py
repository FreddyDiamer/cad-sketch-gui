"""Глобальные стили приложения. Тёмная тема, единая для всех виджетов."""
from __future__ import annotations


# Палитра
BG_WINDOW = "#1a1d21"
BG_WORKSPACE = "#16181c"
BG_CARD_PENDING = "#1f2328"
BG_CARD_DONE = "#23272e"
BG_CARD_ACTIVE = "#262c36"
BG_INPUT = "#1b1f24"
BG_HOVER = "#2b313a"

BORDER = "#2d333b"
BORDER_INPUT = "#3d444d"
BORDER_ACTIVE = "#3b82f6"

TEXT = "#e6edf3"
TEXT_MUTED = "#8b949e"
TEXT_DIM = "#6e7681"

ACCENT = "#3b82f6"
ACCENT_HOVER = "#2563eb"
ACCENT_PRESSED = "#1d4ed8"
SUCCESS = "#2ea043"


DARK_QSS = f"""
/* ====================== Базовое ====================== */
QMainWindow, QWidget {{
    background-color: {BG_WINDOW};
    color: {TEXT};
    font-size: 13px;
}}

QToolTip {{
    background-color: #2d333b;
    color: {TEXT};
    border: 1px solid {BORDER_INPUT};
    padding: 4px 6px;
    border-radius: 4px;
}}

/* ====================== Toolbar ====================== */
QToolBar {{
    background-color: {BG_WORKSPACE};
    border: none;
    border-bottom: 1px solid {BORDER};
    spacing: 6px;
    padding: 6px 10px;
}}

QToolBar QToolButton {{
    background-color: transparent;
    color: {TEXT};
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 13px;
}}
QToolBar QToolButton:hover {{
    background-color: {BG_HOVER};
    border-color: {BORDER_INPUT};
}}
QToolBar QToolButton:pressed {{
    background-color: {BG_CARD_PENDING};
}}
QToolBar QToolButton:disabled {{
    color: {TEXT_DIM};
}}
QToolBar QToolButton::menu-indicator {{ image: none; }}

QToolBar::separator {{
    background-color: {BORDER};
    width: 1px;
    margin: 6px 4px;
}}

/* ====================== Status bar ====================== */
QStatusBar {{
    background-color: {BG_WORKSPACE};
    color: {TEXT_MUTED};
    border-top: 1px solid {BORDER};
}}
QStatusBar QLabel {{ color: {TEXT_MUTED}; padding: 0 8px; }}
QStatusBar::item {{ border: none; }}

/* ====================== Docks ====================== */
QDockWidget {{
    background-color: {BG_WINDOW};
    color: {TEXT};
}}
QDockWidget::title {{
    background-color: {BG_WORKSPACE};
    padding: 6px 10px;
    color: {TEXT_MUTED};
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}

/* ====================== Scroll areas ====================== */
QScrollArea, QScrollArea > QWidget > QWidget {{
    background-color: {BG_WINDOW};
    border: none;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: #3d444d;
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{ background: #4d555f; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none; border: none; height: 0;
}}

/* ====================== StepPanel — карточки ====================== */
QFrame#stepCard {{
    background-color: {BG_CARD_PENDING};
    border: 1px solid {BORDER};
    border-radius: 10px;
}}
QFrame#stepCard[state="pending"] {{
    background-color: {BG_CARD_PENDING};
    border: 1px solid {BORDER};
}}
QFrame#stepCard[state="pending"] QLabel#stepTitle {{ color: {TEXT_DIM}; }}
QFrame#stepCard[state="pending"] QLabel#stepValue,
QFrame#stepCard[state="pending"] QLabel#stepHint {{ color: {TEXT_DIM}; }}

QFrame#stepCard[state="done"] {{
    background-color: {BG_CARD_DONE};
    border: 1px solid {BORDER};
}}
QFrame#stepCard[state="done"] QLabel#stepTitle {{ color: {TEXT}; }}

QFrame#stepCard[state="active"] {{
    background-color: {BG_CARD_ACTIVE};
    border: 1px solid {BORDER};
    border-left: 3px solid {ACCENT};
}}
QFrame#stepCard[state="active"] QLabel#stepTitle {{ color: {TEXT}; }}

QFrame#stepCard QLabel {{ color: {TEXT}; }}
QLabel#stepTitle {{ font-size: 14px; font-weight: 600; }}
QLabel#stepValue {{ color: {TEXT_MUTED}; font-size: 12px; }}
QLabel#stepHint  {{ color: {TEXT_DIM}; font-size: 11px; }}

/* Бейдж */
QLabel#stepBadge {{
    min-width: 24px; max-width: 24px;
    min-height: 24px; max-height: 24px;
    font-size: 12px; font-weight: 700;
    border-radius: 12px;
    padding: 0;
}}
QLabel#stepBadge[state="done"]    {{ background-color: {SUCCESS}; color: white; }}
QLabel#stepBadge[state="active"]  {{ background-color: {ACCENT};  color: white; }}
QLabel#stepBadge[state="pending"] {{ background-color: {BORDER};  color: {TEXT_MUTED}; }}

/* ====================== Buttons ====================== */
/* Secondary (по умолчанию) */
QPushButton {{
    background-color: transparent;
    color: {TEXT};
    border: 1px solid {BORDER_INPUT};
    border-radius: 6px;
    padding: 7px 14px;
    font-size: 13px;
    min-height: 18px;
}}
QPushButton:hover {{
    background-color: {BG_HOVER};
    border-color: #4d555f;
}}
QPushButton:pressed {{
    background-color: {BG_CARD_PENDING};
}}
QPushButton:disabled {{
    color: {TEXT_DIM};
    border-color: {BORDER};
    background-color: transparent;
}}

/* Primary */
QPushButton[primary="true"] {{
    background-color: {ACCENT};
    color: white;
    border: 1px solid {ACCENT};
    font-weight: 600;
}}
QPushButton[primary="true"]:hover {{
    background-color: {ACCENT_HOVER};
    border-color: {ACCENT_HOVER};
}}
QPushButton[primary="true"]:pressed {{
    background-color: {ACCENT_PRESSED};
    border-color: {ACCENT_PRESSED};
}}
QPushButton[primary="true"]:disabled {{
    background-color: #1f2a3a;
    color: #6b7d99;
    border-color: #1f2a3a;
}}

/* ====================== Inputs ====================== */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background-color: {BG_INPUT};
    color: {TEXT};
    border: 1px solid {BORDER_INPUT};
    border-radius: 5px;
    padding: 4px 8px;
    selection-background-color: {ACCENT};
    selection-color: white;
}}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
    border-color: {ACCENT};
}}
QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QComboBox:disabled {{
    color: {TEXT_DIM};
    background-color: {BG_CARD_PENDING};
}}

QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
    background-color: transparent;
    border: none;
    width: 14px;
}}
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
    image: none;
    border-left: 3px solid transparent;
    border-right: 3px solid transparent;
    border-bottom: 4px solid {TEXT_MUTED};
    width: 0; height: 0;
}}
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
    image: none;
    border-left: 3px solid transparent;
    border-right: 3px solid transparent;
    border-top: 4px solid {TEXT_MUTED};
    width: 0; height: 0;
}}

QComboBox::drop-down {{ border: none; width: 16px; }}
QComboBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {TEXT_MUTED};
    width: 0; height: 0;
}}
QComboBox QAbstractItemView {{
    background-color: {BG_CARD_DONE};
    color: {TEXT};
    selection-background-color: {ACCENT};
    selection-color: white;
    border: 1px solid {BORDER_INPUT};
    outline: 0;
}}

/* ====================== Sliders ====================== */
QSlider::groove:horizontal {{
    background: {BG_INPUT};
    height: 4px;
    border-radius: 2px;
}}
QSlider::sub-page:horizontal {{
    background: {ACCENT};
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: white;
    border: 2px solid {ACCENT};
    width: 14px;
    height: 14px;
    margin: -6px 0;
    border-radius: 9px;
}}
QSlider::handle:horizontal:hover {{ border-color: {ACCENT_HOVER}; }}

/* ====================== Checkbox ====================== */
QCheckBox {{
    color: {TEXT};
    spacing: 8px;
    padding: 2px 0;
}}
QCheckBox::indicator {{
    width: 16px; height: 16px;
    border-radius: 4px;
    border: 1px solid {BORDER_INPUT};
    background-color: {BG_INPUT};
}}
QCheckBox::indicator:hover {{ border-color: {ACCENT}; }}
QCheckBox::indicator:checked {{
    background-color: {ACCENT};
    border-color: {ACCENT};
}}
QCheckBox:disabled {{ color: {TEXT_DIM}; }}

/* ====================== Menu (popup) ====================== */
QMenu {{
    background-color: {BG_CARD_DONE};
    color: {TEXT};
    border: 1px solid {BORDER_INPUT};
    border-radius: 6px;
    padding: 4px;
}}
QMenu::item {{
    padding: 6px 18px;
    border-radius: 4px;
}}
QMenu::item:selected {{
    background-color: {ACCENT};
    color: white;
}}
QMenu::separator {{
    height: 1px;
    background: {BORDER};
    margin: 4px 6px;
}}

/* ====================== Dialogs / message box ====================== */
QDialog, QMessageBox {{
    background-color: {BG_WINDOW};
    color: {TEXT};
}}

/* ====================== TextEdit (журнал) ====================== */
QTextEdit {{
    background-color: {BG_INPUT};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 6px;
}}
"""
