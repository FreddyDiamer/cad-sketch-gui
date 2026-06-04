"""Глобальные стили приложения.

Содержит две темы — тёмную и светлую. Темы построены на одной и той же
структуре QSS, но с разными палитрами. Палитра вынесена в датакласс
`Palette`, а QSS собирается функцией `build_qss(palette)`.

Это позволяет:
    * легко добавлять новые темы (достаточно создать новую палитру);
    * быть уверенным, что обе темы покрывают одинаковый набор виджетов
      (один шаблон — нельзя случайно забыть стилизовать что-то для одной).

Имена тем используются как ключи QSettings и для меню «Тема».
"""
from __future__ import annotations

from dataclasses import dataclass


# --- Идентификаторы тем (используются как ключ QSettings) ---
THEME_DARK = "dark"
THEME_LIGHT = "light"


@dataclass(frozen=True)
class Palette:
    """Набор цветов одной темы. Все значения — HEX-строки."""

    # Фоны разной «глубины» — от рамки окна до рабочей области.
    bg_window: str
    bg_workspace: str
    bg_card_pending: str   # карточка ещё не выполненного шага
    bg_card_done: str      # карточка выполненного шага
    bg_card_active: str    # карточка текущего шага (с синей полосой слева)
    bg_input: str          # фон полей ввода
    bg_hover: str          # фон при наведении на кнопку/пункт меню

    # Границы.
    border: str
    border_input: str
    border_active: str     # рамка активного элемента (фокус)

    # Цвета текста.
    text: str              # основной текст
    text_muted: str        # подзаголовки, подсказки
    text_dim: str          # самый приглушённый (отключённые элементы)

    # Акцентные цвета: синий и зелёный.
    accent: str            # primary-кнопка, активные элементы
    accent_hover: str
    accent_pressed: str
    success: str           # бейдж выполненного шага

    # Вспомогательные цвета (используются точечно).
    tooltip_bg: str
    scrollbar_handle: str
    scrollbar_handle_hover: str
    primary_disabled_bg: str
    primary_disabled_text: str
    status_text: str       # цвет цифр в статус-баре


# Тёмная палитра — основная, по умолчанию.
DARK_PALETTE = Palette(
    bg_window="#1a1d21",
    bg_workspace="#16181c",
    bg_card_pending="#1f2328",
    bg_card_done="#23272e",
    bg_card_active="#262c36",
    bg_input="#1b1f24",
    bg_hover="#2b313a",

    border="#2d333b",
    border_input="#3d444d",
    border_active="#3b82f6",

    text="#e6edf3",
    text_muted="#8b949e",
    text_dim="#6e7681",

    accent="#3b82f6",
    accent_hover="#2563eb",
    accent_pressed="#1d4ed8",
    success="#2ea043",

    tooltip_bg="#2d333b",
    scrollbar_handle="#3d444d",
    scrollbar_handle_hover="#4d555f",
    primary_disabled_bg="#1f2a3a",
    primary_disabled_text="#6b7d99",
    status_text="#57606a",
)


# Светлая палитра — мягкая, без чисто-белого фона (легче для глаз).
LIGHT_PALETTE = Palette(
    bg_window="#f6f8fa",
    bg_workspace="#ffffff",
    bg_card_pending="#ffffff",
    bg_card_done="#eef1f4",
    bg_card_active="#ffffff",
    bg_input="#ffffff",
    bg_hover="#e8ebf0",

    border="#d0d7de",
    border_input="#bbc3cc",
    border_active="#3b82f6",

    text="#1f2328",
    text_muted="#57606a",
    text_dim="#8c959f",

    accent="#3b82f6",
    accent_hover="#2563eb",
    accent_pressed="#1d4ed8",
    success="#2da44e",

    tooltip_bg="#24292f",      # тёмная подсказка на светлом — для контраста
    scrollbar_handle="#bbc3cc",
    scrollbar_handle_hover="#9ba3ad",
    primary_disabled_bg="#cfd8e3",
    primary_disabled_text="#8c959f",
    status_text="#8b949e",
)


def build_qss(p: Palette) -> str:
    """Собирает полный QSS из палитры.

    Возвращает строку, готовую к передаче в QApplication.setStyleSheet().
    Палитра используется только здесь — компоненты приложения не знают
    о конкретных цветах, они стилизуются через objectName/property.
    """
    # Заметка: QSS-стили требуют двойных фигурных скобок в f-строке,
    # чтобы остался одиночный {…}-блок селекторов.
    return f"""
/* ====================== Базовое ====================== */
QMainWindow, QWidget {{
    background-color: {p.bg_window};
    color: {p.text};
    font-size: 13px;
}}

QToolTip {{
    background-color: {p.tooltip_bg};
    color: #ffffff;
    border: 1px solid {p.border_input};
    padding: 4px 6px;
    border-radius: 4px;
}}

/* ====================== Toolbar ====================== */
QToolBar {{
    background-color: {p.bg_workspace};
    border: none;
    border-bottom: 1px solid {p.border};
    spacing: 6px;
    padding: 6px 10px;
}}

QToolBar QToolButton {{
    background-color: transparent;
    color: {p.text};
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 13px;
}}
QToolBar QToolButton:hover {{
    background-color: {p.bg_hover};
    border-color: {p.border_input};
}}
QToolBar QToolButton:pressed {{
    background-color: {p.bg_card_pending};
}}
QToolBar QToolButton:disabled {{
    color: {p.text_dim};
}}
QToolBar QToolButton::menu-indicator {{ image: none; }}

QToolBar::separator {{
    background-color: {p.border};
    width: 1px;
    margin: 6px 4px;
}}

/* ====================== Status bar ====================== */
QStatusBar {{
    background-color: {p.bg_workspace};
    color: {p.text_muted};
    border-top: 1px solid {p.border};
}}
QStatusBar QLabel {{ color: {p.text_muted}; padding: 0 8px; }}
QStatusBar::item {{ border: none; }}

/* ====================== Docks ====================== */
QDockWidget {{
    background-color: {p.bg_window};
    color: {p.text};
}}
QDockWidget::title {{
    background-color: {p.bg_workspace};
    padding: 6px 10px;
    color: {p.text_muted};
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}

/* ====================== Scroll areas ====================== */
QScrollArea, QScrollArea > QWidget > QWidget {{
    background-color: {p.bg_window};
    border: none;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {p.scrollbar_handle};
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{ background: {p.scrollbar_handle_hover}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none; border: none; height: 0;
}}

/* ====================== StepPanel — карточки ====================== */
QFrame#stepCard {{
    background-color: {p.bg_card_pending};
    border: 1px solid {p.border};
    border-radius: 10px;
}}
QFrame#stepCard[state="pending"] {{
    background-color: {p.bg_card_pending};
    border: 1px solid {p.border};
}}
QFrame#stepCard[state="pending"] QLabel#stepTitle {{ color: {p.text_dim}; }}
QFrame#stepCard[state="pending"] QLabel#stepValue,
QFrame#stepCard[state="pending"] QLabel#stepHint {{ color: {p.text_dim}; }}

QFrame#stepCard[state="done"] {{
    background-color: {p.bg_card_done};
    border: 1px solid {p.border};
}}
QFrame#stepCard[state="done"] QLabel#stepTitle {{ color: {p.text}; }}

QFrame#stepCard[state="active"] {{
    background-color: {p.bg_card_active};
    border: 1px solid {p.border};
    border-left: 3px solid {p.accent};
}}
QFrame#stepCard[state="active"] QLabel#stepTitle {{ color: {p.text}; }}

QFrame#stepCard QLabel {{ color: {p.text}; }}
QLabel#stepTitle {{ font-size: 14px; font-weight: 600; }}
QLabel#stepValue {{ color: {p.text_muted}; font-size: 12px; }}
QLabel#stepHint  {{ color: {p.text_dim}; font-size: 11px; }}

/* Бейдж */
QLabel#stepBadge {{
    min-width: 24px; max-width: 24px;
    min-height: 24px; max-height: 24px;
    font-size: 12px; font-weight: 700;
    border-radius: 12px;
    padding: 0;
}}
QLabel#stepBadge[state="done"]    {{ background-color: {p.success}; color: white; }}
QLabel#stepBadge[state="active"]  {{ background-color: {p.accent};  color: white; }}
QLabel#stepBadge[state="pending"] {{ background-color: {p.border};  color: {p.text_muted}; }}

/* ====================== Buttons ====================== */
/* Secondary (по умолчанию) */
QPushButton {{
    background-color: transparent;
    color: {p.text};
    border: 1px solid {p.border_input};
    border-radius: 6px;
    padding: 7px 14px;
    font-size: 13px;
    min-height: 18px;
}}
QPushButton:hover {{
    background-color: {p.bg_hover};
    border-color: {p.border_input};
}}
QPushButton:pressed {{
    background-color: {p.bg_card_pending};
}}
QPushButton:disabled {{
    color: {p.text_dim};
    border-color: {p.border};
    background-color: transparent;
}}

/* Primary */
QPushButton[primary="true"] {{
    background-color: {p.accent};
    color: white;
    border: 1px solid {p.accent};
    font-weight: 600;
}}
QPushButton[primary="true"]:hover {{
    background-color: {p.accent_hover};
    border-color: {p.accent_hover};
}}
QPushButton[primary="true"]:pressed {{
    background-color: {p.accent_pressed};
    border-color: {p.accent_pressed};
}}
QPushButton[primary="true"]:disabled {{
    background-color: {p.primary_disabled_bg};
    color: {p.primary_disabled_text};
    border-color: {p.primary_disabled_bg};
}}

/* ====================== Inputs ====================== */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background-color: {p.bg_input};
    color: {p.text};
    border: 1px solid {p.border_input};
    border-radius: 5px;
    padding: 4px 8px;
    selection-background-color: {p.accent};
    selection-color: white;
}}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
    border-color: {p.accent};
}}
QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QComboBox:disabled {{
    color: {p.text_dim};
    background-color: {p.bg_card_pending};
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
    border-bottom: 4px solid {p.text_muted};
    width: 0; height: 0;
}}
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
    image: none;
    border-left: 3px solid transparent;
    border-right: 3px solid transparent;
    border-top: 4px solid {p.text_muted};
    width: 0; height: 0;
}}

QComboBox::drop-down {{ border: none; width: 16px; }}
QComboBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {p.text_muted};
    width: 0; height: 0;
}}
QComboBox QAbstractItemView {{
    background-color: {p.bg_card_done};
    color: {p.text};
    selection-background-color: {p.accent};
    selection-color: white;
    border: 1px solid {p.border_input};
    outline: 0;
}}

/* ====================== Sliders ====================== */
QSlider::groove:horizontal {{
    background: {p.bg_input};
    height: 4px;
    border-radius: 2px;
}}
QSlider::sub-page:horizontal {{
    background: {p.accent};
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: white;
    border: 2px solid {p.accent};
    width: 14px;
    height: 14px;
    margin: -6px 0;
    border-radius: 9px;
}}
QSlider::handle:horizontal:hover {{ border-color: {p.accent_hover}; }}

/* ====================== Checkbox ====================== */
QCheckBox {{
    color: {p.text};
    spacing: 8px;
    padding: 2px 0;
}}
QCheckBox::indicator {{
    width: 16px; height: 16px;
    border-radius: 4px;
    border: 1px solid {p.border_input};
    background-color: {p.bg_input};
}}
QCheckBox::indicator:hover {{ border-color: {p.accent}; }}
QCheckBox::indicator:checked {{
    background-color: {p.accent};
    border-color: {p.accent};
}}
QCheckBox:disabled {{ color: {p.text_dim}; }}

/* ====================== Menu (popup) ====================== */
QMenu {{
    background-color: {p.bg_card_done};
    color: {p.text};
    border: 1px solid {p.border_input};
    border-radius: 6px;
    padding: 4px;
}}
QMenu::item {{
    padding: 6px 18px;
    border-radius: 4px;
}}
QMenu::item:selected {{
    background-color: {p.accent};
    color: white;
}}
QMenu::separator {{
    height: 1px;
    background: {p.border};
    margin: 4px 6px;
}}

/* ====================== Dialogs / message box ====================== */
QDialog, QMessageBox {{
    background-color: {p.bg_window};
    color: {p.text};
}}

/* ====================== TextEdit (журнал) ====================== */
QTextEdit {{
    background-color: {p.bg_input};
    color: {p.text};
    border: 1px solid {p.border};
    border-radius: 6px;
    padding: 6px;
}}
"""


# Готовые QSS для двух тем — собираются один раз при импорте модуля.
DARK_QSS = build_qss(DARK_PALETTE)
LIGHT_QSS = build_qss(LIGHT_PALETTE)


def get_palette(theme: str) -> Palette:
    """Возвращает палитру по идентификатору темы."""
    return LIGHT_PALETTE if theme == THEME_LIGHT else DARK_PALETTE


def get_qss(theme: str) -> str:
    """Возвращает готовый QSS по идентификатору темы."""
    return LIGHT_QSS if theme == THEME_LIGHT else DARK_QSS
