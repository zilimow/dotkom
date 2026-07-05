from openpyxl.utils import get_column_letter
from streamlit_option_menu import option_menu
import database.db_manager as db
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from pathlib import Path
import streamlit as st
import pandas as pd
import threading
import datetime
import requests
import logging
import hashlib
import time
import os
import io


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# ==================== CONSTANTS ====================

FLEET_TYPES = [
    "Автогрейдер",
    "Вилочный погрузчик",
    "Гусеничный бульдозер",
    "Гусеничный экскаватор",
    "Колесный бульдозер",
    "Колесный экскаватор",
    "Самосвал",
    "Телескопический погрузчик",
    "Фронтальный погрузчик",
    "Шинный манипулятор"
]


# ==================== HELPER FUNCTIONS ====================

def load_external_css(file_path: str):
    """Load external CSS file for styling."""
    try:
        with open(file_path, "r", encoding="utf-8") as file_stream:
            css_rules = file_stream.read()
            st.markdown(f"<style>{css_rules}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning(f"CSS file not found at: {file_path}")



def info_panel():
    # 1. Сбор данных для инфо-строки
    current_user_fio = st.session_state.get("user_fio", "Каекбердин Р.Р.")  
    current_role_str = "Администратор" if st.session_state.get("role") == "admin" else "Механик"
    
    months_ru = {
        1: "января", 2: "февраля", 3: "марта", 4: "апреля",
        5: "мая", 6: "июня", 7: "июля", 8: "августа",
        9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"
    }
    today = datetime.date.today()
    current_date = f"{today.day} {months_ru[today.month]} {today.year} г."
    current_time = datetime.datetime.now().strftime("%H:%M")
    
    try:
        stats = db.get_equipment_statistics()
        total_equipment = stats.get('total', 0)
    except Exception:
        total_equipment = 0

    base_meta_html = (
        f"📅 {current_date}"
        f" &nbsp;|&nbsp; "
        f"🕒 {current_time}"
        f" &nbsp;|&nbsp; "
        f"🚜 Всего техники: <b>{total_equipment}</b>"
    )

    # 2. Чистая стилизация (Никаких скрытых кнопок)
    st.html(
        """
        <style>
            .system-fixed-top-bar {
                position: fixed !important;
                left: 5rem !important; 
                width: calc(100% - 10rem) !important;
                top: 0 !important;
                background-color: #FFFFFF !important; 
                border-bottom: 1px solid #CCCCCC !important;
                padding-top: 6px !important;       
                padding-bottom: 6px !important;       
                padding-left: 0px !important;  
                padding-right: 0px !important; 
                display: flex !important;
                justify-content: space-between !important;
                align-items: center !important;
                z-index: 99999 !important;          
                box-sizing: border-box !important;
            }
            .top-bar-text {
                font-size: 11px !important;
                color: #555555 !important;
                margin: 0 !important;
                padding: 0 !important;
                font-family: monospace !important;
            }
            .stMainBlockContainer { padding-top: 5px !important; }
            [data-testid="stHeader"] { display: none !important; height: 0px !important; visibility: hidden !important; }
            #MainMenu { visibility: hidden !important; }
            
            .top-bar-btn {
                background-color: #140A9A !important; color: #FFFFFF !important;
                border: 1px solid #140A9A !important; padding: 3px 8px !important;
                font-size: 10px !important; font-family: sans-serif;
                border-radius: 4px !important; cursor: pointer;
                text-decoration: none !important; display: inline-block;
                margin-left: 10px; transition: all 0.2s ease;
            }
            .top-bar-btn:hover { background-color: #2e7d32 !important; border-color: #2e7d32 !important; }
        </style>
        """
    )

    # 3. ОТРИСОВКА ВЕРХНЕЙ СТРОКИ
    # ИСПРАВЛЕНО: Ссылка Выйти ведет на ?logout=1 и открывается строго в ТЕКУЩЕЙ вкладке (target="_self")
    st.markdown(
        f"""
        <div class="system-fixed-top-bar">
            <div>
                <p class="top-bar-text">
                    {base_meta_html}
                </p>
            </div>
            <div>
                <p class="top-bar-text">
                    Пользователь: <b>{current_user_fio}</b> ({current_role_str})
                    <a href="?logout=1" target="_self" class="top-bar-btn">Выйти</a>
                </p>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )




        
def app_header():
    """Отображение шапки приложения с шестеренкой."""
    gear_class = "icon-admin" if st.session_state.get("role") == "admin" else "icon-guest"
    
        
    # Отрисовка названия с подчеркивающей линией
    st.markdown(f"""
        <style>
        .header-container-underlined {{
            width: 100% !important;
            box-sizing: border-box;
            border-bottom: 3px solid #140A9A; 
            padding-bottom: 0px;      
            margin-bottom: 15px;       
        }}
        
        .header-logo-text {{
            margin: 0; 
            padding: 0; 
            font-size: 48px; 
            font-weight: 600; 
            color: #140A9A !important; 
            line-height: 1;
        }}
        </style>

        <div class="header-container-underlined">
            <div class="header-wrapper">
                <svg class="{gear_class}" width="34" height="34" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M19.43 12.98c.04-.32.07-.64.07-.98s-.03-.66-.07-.98l2.11-1.65c.19-.15.24-.42.12-.64l-2-3.46c-.12-.22-.39-.3-.61-.22l-2.49 1c-.52-.4-1.08-.73-1.69-.98l-.38-2.65C14.46 2.18 14.25 2 14 2h-4c-.25 0-.46.18-.49.42l-.38 2.65c-.61.25-1.17.59-1.69.98l-2.49-1c-.23-.09-.49 0-.61.22l-2 3.46c-.13.22-.07.49.12.64l2.11 1.65c-.04.32-.07.65-.07.98s.03.66.07.98l-2.11 1.65c-.19.15-.24.42-.12.64l2 3.46c.12.22.39.3.61.22l2.49-1c.52.4 1.08.73 1.69.98l.38 2.65c.03.24.24.42.49.42h4c.25 0 .46-.18.49-.42l.38-2.65c.61-.25 1.17-.59 1.69-.98l2.49 1c.23.09.49 0 .61-.22l2-3.46c.12-.22.07-.49-.12-.64l-2.11-1.65zM12 15.5c-1.93 0-3.5-1.57-3.5-3.5s1.57-3.5 3.5-3.5 3.5 1.57 3.5 3.5-1.57 3.5-3.5 3.5z"/>
                </svg>
                <h1 class="header-logo-text">MECHANIK</h1>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
def app_footer():
    """Отрисовка текстового блока футера (все стили подгружаются из style.css)."""
    st.markdown('<p class="pure-clean-footer">© 2026 Radik · All rights reserved</p>', unsafe_allow_html=True)

def reset_update_modal_filters():
    """Сброс фильтров поиска внутри модального окна редактирования."""
    st.session_state["m_up_q"] = ""
    st.session_state["m_up_t"] = "Все"
    st.session_state["m_up_reset_counter"] = (
        st.session_state.get("m_up_reset_counter", 0) + 1
    )


@st.dialog(":material/edit: Редактировать существующую технику", width="large")
def manual_update_modal(df_equipment: pd.DataFrame):
    """Окно изменения с мгновенным сообщением и авто-обновлением таблицы на фоне."""
    if "m_up_q" not in st.session_state:
        st.session_state["m_up_q"] = ""
    if "m_up_t" not in st.session_state:
        st.session_state["m_up_t"] = "Все"
    if "m_up_reset_counter" not in st.session_state:
        st.session_state["m_up_reset_counter"] = 0

    count = st.session_state["m_up_reset_counter"]

    col_src, col_type = st.columns(2)
    with col_src:
        lookup_query = (
            st.text_input(
                "Бортовой номер техники",
                placeholder="Введите бортовой номер...",
                key=f"m_up_board_input_{count}",
            )
            .strip()
            .lower()
        )
    with col_type:
        type_options = ["Все"] + FLEET_TYPES
        selected_type = st.selectbox(
            "Тип техники", type_options, key=f"m_up_type_select_{count}"
        )

    btn_find_col, btn_reset_col = st.columns(2)
    with btn_find_col:
        trigger_find = st.button(
            ":material/search: Найти",
            type="primary",
            width='stretch',
            key="m_up_find_action_btn",
        )
    with btn_reset_col:
        has_search = bool(
            st.session_state["m_up_q"]
            or st.session_state["m_up_t"] != "Все"
            or lookup_query
            or selected_type != "Все"
        )
        st.button(
            ":material/refresh: Сбросить",
            disabled=not has_search,
            width='stretch',
            key="m_up_reset_action_btn",
            on_click=reset_update_modal_filters,
        )

    if trigger_find:
        st.session_state["m_up_q"] = lookup_query
        st.session_state["m_up_t"] = selected_type

    active_search = st.session_state["m_up_q"]
    active_type = st.session_state["m_up_t"]

    if not active_search and active_type == "Все":
        st.info(
            "Введите бортовой номер или выберите тип техники и нажмите 'Найти'."
        )
        return

    filtered = df_equipment.copy()
    if active_search:
        mask = (
            filtered["eq_board"]
            .astype(str)
            .str.lower()
            .str.contains(active_search, na=False)
        )
        filtered = filtered[mask]
    if active_type != "Все":
        filtered = filtered[filtered["eq_type"] == active_type]

    if filtered.empty:
        st.error("Техника с такими параметрами не найдена.")
        return

    filtered["display_label"] = (
        filtered["eq_board"].astype(str)
        + " | "
        + filtered["eq_type"].astype(str)
        + " | "
        + filtered["eq_model"].astype(str)
    )
    selected_label = st.selectbox(
        "Найдено совпадений. Выберите нужную цель:",
        filtered["display_label"].tolist(),
        key=f"modal_update_target_{count}",
    )

    matched_rows = filtered[filtered["display_label"] == selected_label]
    if matched_rows.empty:
        st.error("Ошибка при выборе машины.")
        return

    # Железно извлекаем первую найденную строку
    current_eq = matched_rows.iloc[0]
    equipment_id = int(current_eq["id"])

    # Читаем тип техники из базы данных для точной синхронизации
    db_type = str(current_eq.get("eq_type", "")).strip()

    # СТРОГОЕ ИСПРАВЛЕНИЕ: Защита списка от сброса на дефолтный Автогрейдер
    local_fleet_types = list(FLEET_TYPES)
    
    # Если в БД лежит старое название, которого больше нет в коде,
    # мы гарантированно добавляем его в локальный список, чтобы не было ошибки длины length
    if db_type and (db_type not in local_fleet_types):
        local_fleet_types.append(db_type)

    # Безопасный расчет индекса: если что-то пойдет не так, индекс железно встанет на 0
    try:
        type_index = local_fleet_types.index(db_type)
    except (ValueError, IndexError):
        type_index = 0

    # Вспомогательная функция очистки вывода для полей ввода формы
    def clean_val(field_name):
        val = current_eq.get(field_name, "")
        if pd.isna(val) or str(val).strip().lower() in ["none", "nan"]:
            return ""
        return str(val).strip()

    # Форма редактирования данных
    with st.form(
        key=f"modal_update_execution_form_{equipment_id}_{count}",
        clear_on_submit=False,
    ):
        col1, col2 = st.columns(2)
        with col1:
            eq_board = st.text_input(
                "Бортовой номер *",
                value=clean_val("eq_board"),
                key=f"m_up_board_{equipment_id}_{count}",
            ).strip()
            eq_type = st.selectbox(
                "Тип",
                local_fleet_types,
                index=int(type_index),
                key=f"m_up_type_{equipment_id}_{count}",
            )
            eq_model = st.text_input(
                "Модель *",
                value=clean_val("eq_model"),
                key=f"m_up_model_{equipment_id}_{count}",
            ).strip()
            eq_serial = st.text_input(
                "Серийный номер",
                value=clean_val("eq_serial"),
                key=f"m_up_serial_{equipment_id}_{count}",
            ).strip()
        with col2:
            eq_year = st.text_input(
                "Год производства",
                value=clean_val("eq_year"),
                key=f"m_up_year_{equipment_id}_{count}",
            ).strip()
            eq_engine = st.text_input(
                "ДВС",
                value=clean_val("eq_engine"),
                key=f"m_up_engine_{equipment_id}_{count}",
            ).strip()
            eq_engine_number = st.text_input(
                "Номер двигателя",
                value=clean_val("eq_engine_number"),
                key=f"m_up_engine_num_{equipment_id}_{count}",
            ).strip()
            eq_code = st.text_input(
                "Код",
                value=clean_val("eq_code"),
                key=f"m_up_code_{equipment_id}_{count}",
            ).strip()

        st.write(" ")
        submitted = st.form_submit_button(
            "Обновить данные", width='stretch'
        )

        status_placeholder = st.empty()

        if submitted:
            status_placeholder.empty()
            if not eq_board or not eq_model:
                status_placeholder.markdown(
                    '<div class="var-destruct-error">❌ Бортовой номер и Модель обязательны!</div>',
                    unsafe_allow_html=True,
                )
            else:
                is_duplicate = False
                if not df_equipment.empty:
                    match_board = (
                        df_equipment["eq_board"].astype(str).str.lower()
                        == eq_board.lower()
                    )
                    match_model = (
                        df_equipment["eq_model"].astype(str).str.lower()
                        == eq_model.lower()
                    )
                    match_type = (
                        df_equipment["eq_type"].astype(str).str.lower()
                        == eq_type.lower()
                    )
                    duplicate_mask = (
                        match_board
                        & match_model
                        & match_type
                        & (df_equipment["id"].astype(int) != equipment_id)
                    )

                    if duplicate_mask.any():
                        status_placeholder.markdown(
                            f'<div class="self-destruct-error">❌ Ошибка: В базе уже существует точно такая же техника!</div>',
                            unsafe_allow_html=True,
                        )
                        is_duplicate = True

                if not is_duplicate:
                    try:
                        db.update_equipment(
                            equipment_id=equipment_id,
                            eq_board=eq_board,
                            eq_type=eq_type,
                            eq_model=eq_model,
                            eq_serial=eq_serial,
                            eq_year=eq_year,
                            eq_engine=eq_engine,
                            eq_engine_number=eq_engine_number,
                            eq_code=eq_code,
                        )

                        status_placeholder.markdown(
                            '<div class="self-destruct-success">✅ Данные техники успешно обновлены в базе!</div>',
                            unsafe_allow_html=True,
                        )

                        st.session_state["m_up_q"] = ""
                        st.session_state["m_up_t"] = "Все"
                        st.session_state["m_up_reset_counter"] += 1

                        time.sleep(1.2)
                        st.rerun()
                    except Exception as e:
                        status_placeholder.markdown(
                            f'<div class="self-destruct-error">❌ Ошибка: {e}</div>',
                            unsafe_allow_html=True,
                        )


def reset_delete_modal_filters():
    """Сброс фильтров поиска внутри модального окна удаления."""
    st.session_state["m_del_q"] = ""
    st.session_state["m_del_t"] = "Все"
    st.session_state["m_del_reset_counter"] = (
        st.session_state.get("m_del_reset_counter", 0) + 1
    )


@st.dialog("Удаление техники из базы", width="large")
def manual_delete_modal(df_equipment: pd.DataFrame):
    """Окно удаления техники со мгновенным сообщением и авто-обновлением таблицы на фоне."""
    if "m_del_q" not in st.session_state:
        st.session_state["m_del_q"] = ""
    if "m_del_t" not in st.session_state:
        st.session_state["m_del_t"] = "Все"
    if "m_del_reset_counter" not in st.session_state:
        st.session_state["m_del_reset_counter"] = 0

    count = st.session_state["m_del_reset_counter"]

    col_src, col_type = st.columns(2)
    with col_src:
        lookup_query = (
            st.text_input(
                "Бортовой номер техники",
                placeholder="Введите бортовой номер...",
                key=f"m_del_board_input_{count}",
            )
            .strip()
            .lower()
        )
    with col_type:
        type_options = ["Все"] + FLEET_TYPES
        selected_type = st.selectbox(
            "Тип техники", type_options, key=f"m_del_type_select_{count}"
        )

    btn_find_col, btn_reset_col = st.columns(2)
    with btn_find_col:
        trigger_find = st.button(
            ":material/search:   Найти",
            type="primary",
            width='stretch',
            key="m_del_find_action_btn",
        )
    with btn_reset_col:
        has_search = bool(
            st.session_state["m_del_q"]
            or st.session_state["m_del_t"] != "Все"
            or lookup_query
            or selected_type != "Все"
        )
        st.button(
            ":material/refresh: Сбросить",
            disabled=not has_search,
            width='stretch',
            key="m_del_reset_action_btn",
            on_click=reset_delete_modal_filters,
        )

    if trigger_find:
        st.session_state["m_del_q"] = lookup_query
        st.session_state["m_del_t"] = selected_type

    active_search = st.session_state["m_del_q"]
    active_type = st.session_state["m_del_t"]

    if not active_search and active_type == "Все":
        st.info(
            "Введите бортовой номер или выберите тип техники и нажмите 'Найти'."
        )
        return

    filtered = df_equipment.copy()
    if active_search:
        mask = (
            filtered["eq_board"]
            .astype(str)
            .str.lower()
            .str.contains(active_search, na=False)
        )
        filtered = filtered[mask]
    if active_type != "Все":
        filtered = filtered[filtered["eq_type"] == active_type]

    if filtered.empty:
        st.error("Техника с такими параметрами не найдена.")
        return

    filtered["display_label"] = (
        filtered["eq_board"].astype(str)
        + " | "
        + filtered["eq_type"].astype(str)
        + " | "
        + filtered["eq_model"].astype(str)
    )
    selected_label = st.selectbox(
        "Выберите точную машину для УДАЛЕНИЯ:",
        filtered["display_label"].tolist(),
        key=f"modal_delete_target_{count}",
    )

    matched_rows = filtered[filtered["display_label"] == selected_label]
    if matched_rows.empty:
        st.error("Ошибка при выборе машины.")
        return

    # Безопасное извлечение первой строки через iloc[0]
    current_eq = matched_rows.iloc[0]
    equipment_id = int(current_eq["id"])

    st.markdown(" ")
    st.markdown(
        f"""
        <div style='background-color: #ffebee; border-left: 5px solid #d32f2f; padding: 12px; margin-bottom: 15px; border-radius: 4px;'>
            <span style='color: #c62828; font-weight: bold;'>⚠️ Внимание!</span> 
            <span style='color: #c62828;'>Вы собираетесь навсегда удалить объект:</span><br>
            <strong>{selected_label}</strong>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form(
        f"modal_delete_execution_form_{equipment_id}_{count}",
        clear_on_submit=True,
    ):
        confirm_delete = st.checkbox(
            "Я подтверждаю, что хочу удалить эту единицу из ERP системы"
        )
        submitted = st.form_submit_button(
            "Удалить технику из базы", type="primary", width='stretch'
        )

        status_placeholder = st.empty()

        if submitted:
            if not confirm_delete:
                status_placeholder.markdown(
                    '<div class="self-destruct-error">❌ Необходимо поставить галочку подтверждения операции!</div>',
                    unsafe_allow_html=True,
                )
            else:
                try:
                    # Вызываем функцию удаления из db_manager
                    db.delete_equipment(equipment_id=equipment_id)

                    # Выводим статус успеха
                    status_placeholder.markdown(
                        '<div class="self-destruct-success">🛑 Единица техники успешно удалена из системы!</div>',
                        unsafe_allow_html=True,
                    )

                    # Сбрасываем фильтры
                    st.session_state["m_del_q"] = ""
                    st.session_state["m_del_t"] = "Все"
                    st.session_state["m_del_reset_counter"] += 1

                    # Микро-таймаут и перезапуск
                    time.sleep(1.2)
                    st.rerun()
                except Exception as e:
                    status_placeholder.markdown(
                        f'<div class="self-destruct-error">❌ Ошибка: {e}</div>',
                        unsafe_allow_html=True,
                    )
           

@st.dialog(":material/add_box: Добавить новую технику в базу", width="large")
def manual_add_modal(df_equipment: pd.DataFrame):
    """Форма добавления техники внутри модального окна с композитной проверкой дубликатов."""

    with st.form("modal_add_equipment_form", clear_on_submit=False):
        st.markdown(
            """
            <style>
            /* Скрывает текст подсказки в самом низу формы */
            .stForm [data-testid="caption"],
            .stForm [data-testid="stCaptionContainer"],
            [data-testid="stFormSubmitButton"] + div,
            form div:last-child {
                display: none !important;
                height: 0px !important;
                margin: 0 !important;
                padding: 0 !important;
                visibility: hidden !important;
                font-size: 0px !important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
        
        col1, col2 = st.columns(2)

        with col1:
            eq_board = st.text_input(
                "Бортовой номер *", key="add_eq_board"
            ).strip()
            eq_type = st.selectbox("Тип", FLEET_TYPES, key="add_eq_type")
            eq_model = st.text_input("Модель *", key="add_eq_model").strip()
            eq_serial = st.text_input(
                "Серийный номер", key="add_eq_serial"
            ).strip()
        with col2:
            eq_year = st.text_input(
                "Год производства",
                placeholder="например: 2020",
                key="add_eq_year",
            ).strip()
            eq_engine = st.text_input("ДВС", key="add_eq_current_engine").strip()
            eq_engine_number = st.text_input(
                "Номер двигателя", key="add_eq_engine_num"
            ).strip()
            eq_code = st.text_input("Код", key="add_eq_code").strip()

        st.write(" ")
        submitted = st.form_submit_button(
            "Сохранить машину", width='stretch'
        )
        status_placeholder = st.empty()

        if submitted:
            status_placeholder.empty()
            with status_placeholder.container():
                if not eq_board or not eq_model:
                    status_placeholder.markdown(
                        '<div class="self-destruct-error">❌ Заполните обязательные поля!</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    is_duplicate = False

                    if not df_equipment.empty:
                        # Проверяем ОДНОВРЕМЕННОЕ совпадение Борта, Модели и Типа техники
                        match_board = (
                            df_equipment["eq_board"].astype(str).str.lower()
                            == eq_board.lower()
                        )
                        match_model = (
                            df_equipment["eq_model"].astype(str).str.lower()
                            == eq_model.lower()
                        )
                        match_type = (
                            df_equipment["eq_type"].astype(str).str.lower()
                            == eq_type.lower()
                        )

                        exact_duplicate = match_board & match_model & match_type

                        if exact_duplicate.any():
                            status_placeholder.markdown(
                                f'<div class="self-destruct-error">Ошибка: В базе уже существует {eq_type} с бортовым {eq_board} и моделью {eq_model}!</div>',
                                unsafe_allow_html=True,
                            )
                            is_duplicate = True

                    if not is_duplicate:
                        try:
                            # Передаем аргументы в функцию добавления
                            # Названия аргументов должны строго совпадать с аргументами в db_manager
                            db.add_equipment(
                                eq_board=eq_board,
                                eq_type=eq_type,
                                eq_model=eq_model,
                                eq_serial=eq_serial,
                                eq_year=eq_year,
                                eq_engine=eq_engine,
                                eq_engine_number=eq_engine_number,
                                eq_code=eq_code,
                            )

                            status_placeholder.markdown(
                                '<div class="self-destruct-success">✅ Машина успешно добавлена в базу!</div>',
                                unsafe_allow_html=True,
                            )
                            time.sleep(1.2)
                            st.rerun()

                        except Exception as e:
                            status_placeholder.markdown(
                                f'<div class="self-destruct-error">❌ Ошибка сохранения: {e}</div>',
                                unsafe_allow_html=True,
                            )
                            
                            

    
    
    
    
        
def equipment_filters(df_equipment: pd.DataFrame) -> pd.DataFrame:
    """Панель поиска и управления с широким полем ключевых слов на первом месте, точечным бортовым номером на втором."""
    
    # Инициализация состояний сессии
    if "submitted_search" not in st.session_state:
        st.session_state["submitted_search"] = ""
    if "submitted_board" not in st.session_state:
        st.session_state["submitted_board"] = ""
    if "submitted_type" not in st.session_state:
        st.session_state["submitted_type"] = "Все"
    if "submitted_model" not in st.session_state:
        st.session_state["submitted_model"] = "Все"
    
    with st.container(border=True):
        st.caption("Поиск по технике")
            
        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])

        with col1:
            # Поиск по ключевым словам
            search_query = st.text_input(
                "Ключевые слова",
                value=st.session_state["submitted_search"],
                key="filter_search",
            ).strip()

        with col2:
            # Поиск по бортовому номеру
            board_query = st.text_input(
                "Бортовой номер",
                value=st.session_state["submitted_board"],
                key="filter_board",
            ).strip()

        with col3:
            # Поиск по типу
            type_options = ["Все"] + FLEET_TYPES
            try:
                type_idx = type_options.index(st.session_state["submitted_type"])
            except ValueError:
                type_idx = 0
            selected_type = st.selectbox(
                "Тип техники", type_options, index=type_idx, key="filter_type"
            )

        with col4:
            # Поиск по модели
            # Предварительная фильтрация базы НА ЛЕТУ для выпадающего списка моделей
            pre_filtered = df_equipment.copy()

            # Сначала по борту
            if board_query:
                pre_filtered = pre_filtered[
                    pre_filtered["eq_board"].astype(str).str.lower()
                    == board_query.lower()
                ]

            # Затем по ключевым словам
            if search_query:
                q = search_query.lower()
                mask = (
                    pre_filtered["eq_model"].astype(str).str.lower().str.contains(q, na=False)
                    | pre_filtered["eq_serial"].astype(str).str.lower().str.contains(q, na=False)
                    | pre_filtered["eq_engine"].astype(str).str.lower().str.contains(q, na=False)
                )
                pre_filtered = pre_filtered[mask]

            # Затем по типу
            if selected_type != "Все":
                pre_filtered = pre_filtered[pre_filtered["eq_type"] == selected_type]

            # Формируем чистый список уникальных моделей
            available_models = (
                pre_filtered["eq_model"]
                .dropna()
                .astype(str)
                .str.strip()
                .unique()
                .tolist()
            )
            available_models = sorted([m for m in available_models if m != ""])
            model_options = ["Все"] + available_models

            try:
                model_idx = model_options.index(st.session_state["submitted_model"])
            except ValueError:
                model_idx = 0

            selected_model = st.selectbox(
                "Модель техники", model_options, index=model_idx, key="filter_model"
            )

        
        col1, col2, _, _, _ = st.columns([0.99, 0.99, 0.99, 1, 1])

        with col1:
            if st.button(
                ":material/search: Показать",
                type="primary",
                width='stretch',
                key="main_search_submit_btn",
            ):
                st.session_state["submitted_search"] = search_query
                st.session_state["submitted_board"] = board_query
                st.session_state["submitted_type"] = selected_type
                st.session_state["submitted_model"] = selected_model
                st.rerun()

        with col2:
            has_active_filters = bool(
                st.session_state["submitted_search"]
                or st.session_state["submitted_board"]
                or st.session_state["submitted_type"] != "Все"
                or st.session_state["submitted_model"] != "Все"
            )
            st.button(
                ":material/refresh: Сбросить",
                disabled=not has_active_filters,
                width='stretch',
                on_click=clear_search_filters,
                key="main_search_reset_btn",
            )
    

    # ИТОГОВАЯ ФИЛЬТРАЦИЯ ДЛЯ ТАБЛИЦЫ
    filtered_df = df_equipment.copy()
    confirm_q = st.session_state["submitted_search"]
    confirm_board = st.session_state["submitted_board"]
    confirm_type = st.session_state["submitted_type"]
    confirm_model = st.session_state["submitted_model"]

    # Точечный поиск по борту
    if confirm_board:
        filtered_df = filtered_df[
            filtered_df["eq_board"].astype(str).str.lower() == confirm_board.lower()
        ]

    # Поиск по ключевым словам по остальным колонкам
    if confirm_q:
        q = confirm_q.strip().lower()
        mask = (
            filtered_df["eq_model"].astype(str).str.lower().str.contains(q, na=False)
            | filtered_df["eq_board"].astype(str).str.lower().str.contains(q, na=False)
            | filtered_df["eq_serial"].astype(str).str.lower().str.contains(q, na=False)
            | filtered_df["eq_year"].astype(str).str.lower().str.contains(q, na=False)
            | filtered_df["eq_engine"].astype(str).str.lower().str.contains(q, na=False)
            | filtered_df["eq_engine_number"].astype(str).str.lower().str.contains(q, na=False)
            | filtered_df["eq_code"].astype(str).str.lower().str.contains(q, na=False)
        )
        filtered_df = filtered_df[mask]

    if confirm_type != "Все":
        filtered_df = filtered_df[filtered_df["eq_type"] == confirm_type]

    if confirm_model != "Все":
        filtered_df = filtered_df[filtered_df["eq_model"] == confirm_model]

    return filtered_df.reset_index(drop=True)


# Global clear callback function
def clear_search_filters():
    """Safely clear input caches in memory before page rendering."""
    # 1. Сбрасываем визуальные состояния виджетов ввода
    st.session_state["filter_search"] = ""
    st.session_state["filter_board"] = ""
    st.session_state["filter_type"] = "Все"
    st.session_state["filter_model"] = "Все"

    # 2. Сбрасываем зафиксированные подтвержденные фильтры
    if "submitted_search" in st.session_state:
        st.session_state["submitted_search"] = ""
    if "submitted_board" in st.session_state:
        st.session_state["submitted_board"] = ""
    if "submitted_type" in st.session_state:
        st.session_state["submitted_type"] = "Все"
    if "submitted_model" in st.session_state:
        st.session_state["submitted_model"] = "Все" 


def equipment_table(df_to_display: pd.DataFrame):
    """Отрисовка таблицы техники в зависимости от примененных фильтров"""
    # Is_admin flag для оптимизации разметки
    
    is_admin = st.session_state.get("role") == "admin"
    
    # Кнопки управления для Администратора
    if is_admin:
        with st.container(border=True):
            st.caption("Операции со списком техники")
            col1, col2, col3  = st.columns(3)
            with col1:
                if st.button(
                    ":material/add_box: Добавить",
                    width='stretch',
                    key="panel_add_btn",
                ):
                    manual_add_modal(df_to_display)
            with col2:
                if st.button(
                    ":material/edit: Изменить",
                    width='stretch',
                    key="panel_edit_btn",
                ):
                    st.session_state["show_update_success"] = False
                    st.session_state["m_up_q"] = ""
                    st.session_state["m_up_t"] = "Все"
                    st.session_state["m_up_reset_counter"] = (
                        st.session_state.get("m_up_reset_counter", 0) + 1
                    )
                    manual_update_modal(df_to_display)
            with col3:
                if st.button(
                    ":material/delete: Удалить",
                    width='stretch',
                    key="panel_delete_btn",
                ):
                    st.session_state["m_del_q"] = ""
                    st.session_state["m_del_t"] = "Все"
                    st.session_state["m_del_reset_counter"] = (
                        st.session_state.get("m_del_reset_counter", 0) + 1
                    )
                    manual_delete_modal(df_to_display)
                
                
            
            col1, col2, col3 = st.columns(3)
            with col1:  
                export_excel_template()
            with col2:
                import_excel_data()
            with col3:
                export_excel_data()
                
            st.write("")
    
    
    if df_to_display.empty:
        st.info("Техника с такими параметрами не найдена. Попробуйте изменить фильтры.")
        return
        
    # Настройка отображения колонок
    column_config = {
        "eq_board": st.column_config.TextColumn("Бортовой номер", width=70),
        "eq_type": st.column_config.TextColumn("Тип"),
        "eq_model": st.column_config.TextColumn("Модель"),
        "eq_serial": st.column_config.TextColumn("Серийный номер"),
        "eq_year": st.column_config.TextColumn("Год производства"),
        "eq_engine": st.column_config.TextColumn("ДВС"),
        "eq_engine_number": st.column_config.TextColumn("Номер двигателя"),
        "eq_code": st.column_config.TextColumn("Код"),
    }

    # Display columns (without ID)
    display_columns = ["eq_board", "eq_type", "eq_model", "eq_serial", "eq_year", "eq_engine", "eq_engine_number", "eq_code"]
    
    # Извлекаем только нужные для отображения колонки (без системного ID)
    display_df = df_to_display[display_columns].copy()
    
    # Фильтр техники по ключевому слову, бортовому номеру, типу и модели
    display_df = display_df.sort_values(
        by=["eq_type", "eq_board"], 
        ascending=[True, True]
    )
    
    
    st.caption("Список техники")  
    
    # Отрисовка таблицы
    st.dataframe(
        display_df, 
        column_config=column_config, 
        width='stretch',
        hide_index=True,
        height="content"
    )


def work_table(df_initial: pd.DataFrame, df_to_display: pd.DataFrame):
    """Вывод кнопок управления и интерактивной таблицы журнала работ."""
    
    # 1. СНАЧАЛА ОБЪЯВЛЯЕМ КОНФИГУРАЦИЮ ОТОБРАЖЕНИЯ КОЛОНОК
    column_config = {
        "eq_date": st.column_config.TextColumn("Дата", width=95),
        "eq_board": st.column_config.TextColumn("Бортовой номер", width=95),
        "eq_type": st.column_config.TextColumn("Тип", width=140),
        "eq_model": st.column_config.TextColumn("Модель", width=110),
        "eq_task": st.column_config.TextColumn("Задание", width=110),
        "eq_desc": st.column_config.TextColumn("Описание", width=280),
        "eq_hours": st.column_config.NumberColumn("Моточасы", format="%d", width=95),
        "time_start": st.column_config.TextColumn("Начало", width=65),
        "time_end": st.column_config.TextColumn("Окончание", width=65),
        "eq_executor": st.column_config.TextColumn("Исполнитель", width=140),
        "eq_notes": st.column_config.TextColumn("Примечание", width=280),
    }

    display_cols = [
        "eq_date", "eq_board", "eq_type", "eq_model", "eq_task", 
        "eq_desc", "eq_hours", "time_start", "time_end", "eq_executor", "eq_notes"
    ]

    # 2. ФОРМИРУЕМ ДАТАФРЕЙМ ДЛЯ ВЫВОДА (С ПЕРЕИМЕНОВАНИЕМ)
    if df_to_display.empty:
        display_df = pd.DataFrame(columns=display_cols)
        selection_mode = []
    else:
        rename_map = {
            "work_date": "eq_date",
            "work_task": "eq_task",
            "work_desc": "eq_desc",
            "work_hours": "eq_hours",
            "work_executor": "eq_executor",
            "work_notes": "eq_notes"
        }
        working_df = df_to_display.copy()
        working_df.rename(columns=rename_map, inplace=True)
        valid_cols = [col for col in display_cols if col in working_df.columns]
        
        # Гарантируем, что системный id записи НЕ потеряется при фильтрации и долетит до модалок
        if "id" in working_df.columns and "id" not in valid_cols:
            valid_cols.append("id")
            
        display_df = working_df[valid_cols].copy()
        selection_mode = "single-row"

    # 3. БЕЗОПАСНО ИЗВЛЕКАЕМ ИНДЕКС СТРОКИ КАК ЧИСЛО (Через)
    selected_row_index = None
    if "w_table_selection" in st.session_state:
        selected_rows = st.session_state["w_table_selection"].get("selection", {}).get("rows", [])
        if selected_rows:
            # Извлекаем первый элемент списка, преобразуя его в чистое целое число int
            selected_row_index = int(selected_rows[0]) 

    # 4. РЕНДЕРИНГ КНОПОК УПРАВЛЕНИЯ
    act_col1, act_col2, act_col3, act_col4 = st.columns(4)
    
    with act_col1:
        btn_view = st.button(":material/insert_drive_file: Открыть задание", use_container_width=True, key="w_view_action_btn", disabled=selected_row_index is None)
        if btn_view and selected_row_index is not None:
            row_data = display_df.iloc[selected_row_index]
            open_view_modal(row_data)

    if st.session_state.get("role") == "admin":
        with act_col2:
            if st.button("➕ Добавить", use_container_width=True, key="w_add_action_btn"):
                clear_add_workflow_cache() 
                df_equipment_raw = db.load_equipment()
                manual_add_work_modal(df_equipment_raw)
        with act_col3:
            btn_edit = st.button("✏️ Изменить", use_container_width=True, key="w_edit_action_btn", disabled=selected_row_index is None)
            if btn_edit and selected_row_index is not None:
                # Извлекаем готовую отформатированную строку Pandas Series
                row_data = display_df.iloc[selected_row_index]
                open_edit_modal(row_data)
        with act_col4:
            btn_del = st.button("🗑️ Удалить", use_container_width=True, key="w_del_action_btn", disabled=selected_row_index is None)
            if btn_del and selected_row_index is not None:
                row_data = display_df.iloc[selected_row_index]
                open_delete_modal(
                    record_id=row_data.get("id"),
                    eq_date=row_data.get("eq_date"),
                    eq_board=row_data.get("eq_board"),
                    eq_task=row_data.get("eq_task"),
                    eq_executor=row_data.get("eq_executor")
                )
    else:
        with act_col2: st.write("")
        with act_col3: st.write("")
        with act_col4: st.write("")
        
    st.write(" ")
    
    # 5. ОТРИСОВКА ИНТЕРАКТИВНОЙ ТАБЛИЦЫ
    st.caption("Список работ")
    st.dataframe(
        display_df,
        column_config=column_config, # Теперь переменная гарантированно объявлена выше!
        width='stretch',
        hide_index=True,
        height="content",
        on_select="rerun", 
        selection_mode=selection_mode,
        key="w_table_selection" 
    )



def clear_work_filters():
    """Сброс всех поисковых фильтров журнала работ."""
    st.session_state["w_submitted_search"] = ""
    st.session_state["w_submitted_board"] = ""
    st.session_state["w_submitted_type"] = "Все"
    st.session_state["w_submitted_model"] = "Все"
    # Сброс кэша самих полей ввода (ключей key)
    st.session_state["w_filter_search"] = ""
    st.session_state["filter_board_works"] = ""
    st.session_state["w_filter_type"] = "Все"
    st.session_state["w_filter_model"] = "Все"


import streamlit as st
import pandas as pd

def work_filters(df_works: pd.DataFrame) -> dict:
    """Отрисовывает панель поиска на вкладке РАБОТЫ и возвращает словарь активных фильтров."""
    # Инициализация состояний подтвержденных фильтров в сессии
    if "w_submitted_search" not in st.session_state: st.session_state["w_submitted_search"] = ""
    if "w_submitted_board" not in st.session_state: st.session_state["w_submitted_board"] = ""
    if "w_submitted_type" not in st.session_state: st.session_state["w_submitted_type"] = "Все"
    if "w_submitted_model" not in st.session_state: st.session_state["w_submitted_model"] = "Все"

    # РЯД 1: Поля ввода
    with st.container(border=True):
        st.caption("Поиск по работам")
        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
        
        with col1:
            search_q = st.text_input(
                "Ключевые слова", 
                value=st.session_state["w_submitted_search"]
            ).strip()
        with col2:
            board_q = st.text_input(
                "Бортовой номер", 
                value=st.session_state["w_submitted_board"]
            ).strip()
        with col3:
            type_options = ["Все"] + FLEET_TYPES
            try: t_idx = type_options.index(st.session_state["w_submitted_type"])
            except ValueError: t_idx = 0
            selected_type = st.selectbox("Тип техники", type_options, index=t_idx)
        with col4:
            # На ходу фильтруем датафрейм по выбранному типу техники (если выбрано не "Все")
            if selected_type != "Все":
                df_for_models = df_works[df_works['eq_type'] == selected_type]
            else:
                df_for_models = df_works

            # Собираем уникальные модели строго для выбранного типа техники
            available_models = df_for_models['eq_model'].dropna().astype(str).str.strip().unique().tolist()
            model_options = ["Все"] + sorted([m for m in available_models if m != ""])
            
            # Защита от вылета индекса при смене типа техники
            try: 
                m_idx = model_options.index(st.session_state["w_submitted_model"])
            except ValueError: 
                m_idx = 0
                
            selected_model = st.selectbox("Модель техники", model_options, index=m_idx)

        # РЯД 2: Кнопки управления поиском
        col1, col2, _, _, _ = st.columns([0.99, 0.99, 0.99, 1, 1])
        with col1:
            if st.button(":material/search: Показать", type="primary", use_container_width=True, key="w_search_btn_action"):
                st.session_state["w_submitted_search"] = search_q
                st.session_state["w_submitted_board"] = board_q
                st.session_state["w_submitted_type"] = selected_type
                st.session_state["w_submitted_model"] = selected_model
                st.rerun()
                
        with col2:
            has_filters = bool(
                st.session_state["w_submitted_search"] or 
                st.session_state["w_submitted_board"] or 
                st.session_state["w_submitted_type"] != "Все" or 
                st.session_state["w_submitted_model"] != "Все"
            )
            st.button(
                ":material/refresh: Сбросить", 
                disabled=not has_filters, 
                use_container_width=True, 
                on_click=clear_work_filters, 
                key="w_reset_btn_action"
            )

    # Возвращаем текущие подтвержденные значения фильтров
    return {
        "search": st.session_state["w_submitted_search"],
        "board": st.session_state["w_submitted_board"],
        "type": st.session_state["w_submitted_type"],
        "model": st.session_state["w_submitted_model"]
    }


def clear_add_workflow_cache():
    """Вызывается строго в момент клика по кнопке 'Добавить' на главной панели."""
    st.session_state["w_add_cad_type"] = ""
    st.session_state["w_add_cad_model"] = ""
    st.session_state["w_add_cad_board"] = ""
    st.session_state["w_add_active_eq_id"] = None


@st.dialog(":material/add: Добавить запись", width="large")
def manual_add_work_modal(df_equipment: pd.DataFrame):
    """Модальное окно с каскадными списками, автосбросом и гарантированным сохранением."""
    
    if df_equipment.empty:
        st.error("В базе данных нет техники. Сначала добавьте машины во вкладке 'Техника'.")
        return

    # Логика умного времени по умолчанию
    current_hour = datetime.datetime.now().hour
    default_start, default_end = (datetime.time(7, 0), datetime.time(19, 0)) if 7 <= current_hour < 19 else (datetime.time(19, 0), datetime.time(7, 0))

    # РЯД 1: Каскадные списки выбора техники (Вне формы st.form для мгновенного отклика)
    col_t, col_m, col_b = st.columns(3)

    with col_t:
        available_types = sorted(df_equipment["eq_type"].dropna().unique().tolist())
        selected_type = st.selectbox("1. Тип техники *", [""] + available_types, key="w_add_cad_type", accept_new_options=True)

    with col_m:
        if selected_type:
            df_filtered_by_type = df_equipment[df_equipment["eq_type"] == selected_type]
            available_models = sorted(df_filtered_by_type["eq_model"].dropna().unique().tolist())
            model_options = [""] + available_models
            disabled_model = False
        else:
            model_options, disabled_model = [""], True
        selected_model = st.selectbox("2. Модель техники *", model_options, key="w_add_cad_model", disabled=disabled_model)

    with col_b:
        if selected_type and selected_model:
            df_filtered_final = df_filtered_by_type[df_filtered_by_type["eq_model"] == selected_model]
            available_boards = sorted(df_filtered_final["eq_board"].astype(str).unique().tolist())
            board_options = [""] + available_boards
            disabled_board = False
        else:
            board_options, disabled_board = [""], True
        selected_board = st.selectbox("3. Бортовой номер *", board_options, key="w_add_cad_board", disabled=disabled_board)

    # Если машина не выбрана до конца — показываем красивую подсказку и НЕ рисуем форму дальше
    if not (selected_type and selected_model and selected_board):
        st.info("Пожалуйста, последовательно выберите тип, модель и бортовой номер техники.")
        return

    # Если дошли сюда — машина выбрана. Находим её строчку в датафрейме для вывода инфо
    target_row = df_filtered_final[df_filtered_final["eq_board"].astype(str) == selected_board]
    if target_row.empty:
        st.error("Ошибка определения машины в базе.")
        return

    # Выводим серийный номер, если есть
    db_serial = target_row.iloc[0].get("eq_serial", "")
    if db_serial and not pd.isna(db_serial):
        st.caption(f"🔧 Серийный номер выбранной машины: **{db_serial}**")
        
    active_employees = db.get_active_users_list()
    
    employee_ids = [emp["id"] for emp in active_employees]
    employee_fios = [emp["fio"] for emp in active_employees]
    
    # Автоподстановка: вычисляем индекс текущего залогиненного пользователя
    current_uid = st.session_state.get("user_id", None)
    try:
        default_executor_idx = employee_ids.index(current_uid)
    except ValueError:
        default_executor_idx = 0  # Если совпадений нет, выберем первого сотрудника в списке

    # РЯД 2: ФОРМА ВВОДА ДАННЫХ
    with st.form("modal_add_work_form_new_id", clear_on_submit=False):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            work_date = st.date_input("Дата выполнения", value=datetime.date.today(), format="DD.MM.YYYY", key="w_add_modal_date")
        with c2:
            work_hours = st.number_input("Моточасы (наработка)", min_value=0, value=0, step=1, key="w_add_modal_hours")
        with c3:
            t_start = st.time_input("Время начала", value=default_start, key="w_add_modal_t_start")
        with c4:
            t_end = st.time_input("Время окончания", value=default_end, key="w_add_modal_t_end")

        c5, c6 = st.columns(2)
        with c5:
            work_task = st.text_input("Задание (плановое ТО, регламент)", placeholder="Например: ТО 4000", key="w_add_modal_task").strip()
        with c6:
            selected_executor_fio = st.selectbox(
                "Исполнитель (ФИО) *", 
                options=employee_fios, 
                index=default_executor_idx,
                key="w_add_modal_executor_select"
            )

        work_desc = st.text_area("Описание выполненных работ *", placeholder="Что конкретно было сделано...", height=80, key="w_add_modal_desc").strip()
        work_notes = st.text_area("Примечание (технические замеры, нюансы)", placeholder="Например: закачали 7 МПа...", height=80, key="w_add_modal_notes").strip()

        st.write(" ")
        form_status = st.container()
        submitted = st.form_submit_button("Сохранить запись в журнал", use_container_width=True)

        if submitted:
            if not work_desc:
                form_status.error("❌ Поля Исполнитель и Описание работ обязательны для заполнения!")
            elif t_start == t_end:
                form_status.error("❌ Ошибка времени: Время начала и окончания смены не могут совпадать!")
            else:
                # НАДЕЖНАЯ ВАЛИДАЦИЯ СМЕНЫ
                start_minutes = t_start.hour * 60 + t_start.minute
                end_minutes = t_end.hour * 60 + t_end.minute
                is_day_shift = (7 <= t_start.hour < 19)

                if is_day_shift and end_minutes <= start_minutes:
                    form_status.error("❌ Ошибка времени: Время окончания дневной смены не может быть раньше начала!")
                else:
                    try:
                        # ВЫЧИСЛЯЕМ СИСТЕМНЫЙ ID ПРЯМО ЗДЕСЬ (Утечка через session_state полностью исключена!)
                        active_equipment_id = int(target_row.iloc[0]["id"])
                        
                        chosen_executor_id = employee_ids[employee_fios.index(selected_executor_fio)]

                        str_start = t_start.strftime("%H:%M")
                        str_end = t_end.strftime("%H:%M")
                        str_date = work_date.strftime("%d.%m.%Y")

                        db.add_work_order(
                            equipment_id=active_equipment_id,
                            work_date=str_date,
                            work_task=work_task,
                            work_desc=work_desc,
                            work_hours=float(work_hours),
                            time_start=str_start,
                            time_end=str_end,
                            executor_user_id=chosen_executor_id, # Пишем ID в таблицу базы данных
                            work_notes=work_notes,
                        )

                        form_status.success("✅ Запись о работе успешно сохранена в журнал!")
                        
                        # Закрываем модальное окно
                        st.session_state["show_add_modal"] = False
                        time.sleep(1.0)
                        st.rerun()
                        
                    except Exception as e:
                        form_status.error(f"❌ Ошибка базы данных: {e}")
                        import traceback
                        form_status.code(traceback.format_exc())

@st.dialog(":material/edit: Изменить запись", width="large")
def open_edit_modal(row_data: pd.Series):
    """Модальное окно для редактирования существующей записи журнала работ с выбором исполнителя по ID."""
    st.write(f"📝 Редактирование записи для машины с бортовым номером: **{row_data.get('eq_board')}**")
    
    # --- СТРАТЕГИЯ: ПОДГОТОВКА СПИСКА ИСПОЛНИТЕЛЕЙ ---
    active_employees = db.get_active_users_list()
    
    if not active_employees:
        st.error("❌ Ошибка: В системе нет зарегистрированных сотрудников! Редактирование невозможно.")
        return
        
    employee_ids = [emp["id"] for emp in active_employees]
    employee_fios = [emp["fio"] for emp in active_employees]
    
    # Вычисляем текущего исполнителя наряда для фокуса селектбокса
    current_executor_fio = str(row_data.get("eq_executor", "")).strip()
    try:
        # Пытаемся найти индекс текущего ФИО в списке сотрудников
        default_executor_idx = employee_fios.index(current_executor_fio)
    except ValueError:
        default_executor_idx = 0  # Если сотрудник уволен/не найден, берем первого в списке

    # Форма с предзаполненными данными из row_data
    with st.form("modal_edit_work_form"):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            try:
                current_date = datetime.datetime.strptime(row_data.get("eq_date", ""), "%d.%m.%Y").date()
            except Exception:
                try:
                    current_date = datetime.datetime.strptime(row_data.get("eq_date", ""), "%Y-%m-%d").date()
                except Exception:
                    current_date = datetime.date.today()
                
            work_date = st.date_input("Дата выполнения", value=current_date, format="DD.MM.YYYY")
        with c2:
            work_hours = st.number_input("Моточасы (наработка)", min_value=0, value=int(row_data.get("eq_hours", 0)), step=1)
        with c3:
            try:
                t_start_obj = datetime.datetime.strptime(row_data.get("time_start", "07:00"), "%H:%M").time()
            except Exception:
                t_start_obj = datetime.time(7, 0)
            t_start = st.time_input("Время начала", value=t_start_obj)
        with c4:
            try:
                t_end_obj = datetime.datetime.strptime(row_data.get("time_end", "19:00"), "%H:%M").time()
            except Exception:
                t_end_obj = datetime.time(19, 0)
            t_end = st.time_input("Время окончания", value=t_end_obj)

        c5, c6 = st.columns(2)
        with c5:
            work_task = st.text_input("Задание", value=str(row_data.get("eq_task", ""))).strip()
        with c6:
            # ИСПРАВЛЕНО: Текстовое поле заменено на выпадающий список сотрудников
            selected_executor_fio = st.selectbox(
                "Исполнитель (ФИО) *", 
                options=employee_fios, 
                index=default_executor_idx,
                key="w_edit_modal_executor_select"
            )

        work_desc = st.text_area("Описание выполненных работ *", value=str(row_data.get("eq_desc", "")), height=80).strip()
        work_notes = st.text_area("Примечание", value=str(row_data.get("eq_notes", "")), height=80).strip()

        st.write(" ")
        form_status = st.container()
        
        submitted = st.form_submit_button("Сохранить изменения", use_container_width=True)

        if submitted:
            # ИСПРАВЛЕНО: Валидация на пустоту строки исполнителя убрана, так как selectbox всегда заполнен
            if not work_desc:
                form_status.error("❌ Поле Описание работ обязательно!")
            elif t_start == t_end:
                form_status.error("❌ Время начала и окончания не могут совпадать!")
            else:
                try:
                    str_start = t_start.strftime("%H:%M")
                    str_end = t_end.strftime("%H:%M")
                    str_date = work_date.strftime("%d.%m.%Y")
                    
                    record_id = int(row_data.get("id"))
                    
                    # ИСПРАВЛЕНО: Определяем числовой ID выбранного в селектбоксе исполнителя прямо перед записью в БД
                    chosen_executor_id = employee_ids[employee_fios.index(selected_executor_fio)]

                    # Вызываем функцию обновления в бэкенде (передаем ID вместо текста)
                    db.update_work_order(
                        record_id=record_id,
                        work_date=str_date,
                        work_task=work_task,
                        work_desc=work_desc,
                        work_hours=float(work_hours),
                        time_start=str_start,
                        time_end=str_end,
                        executor_user_id=chosen_executor_id, # Передаем числовую переменную связи
                        work_notes=work_notes,
                    )

                    st.success("✅ Изменения успешно сохранены!")
                    if "w_table_selection" in st.session_state:
                        st.session_state["w_table_selection"] = {"selection": {"rows": [], "columns": []}}
                    time.sleep(1.0)
                    st.rerun()
                except Exception as e:
                    form_status.error(f"❌ Ошибка обновления: {e}")

@st.dialog("⚠️ Подтверждение удаления", width="small")
def open_delete_modal(record_id: int, eq_date: str, eq_board: str, eq_task: str, eq_executor: str):
    """Модальное окно для безопасного удаления записи."""
    st.warning(f"Вы уверены, что хотите полностью удалить запись от **{eq_date}** для машины **{eq_board}**?")
    st.write(f"**Задание:** {eq_task}")
    st.write(f"**Исполнитель:** {eq_executor}")
    st.divider()
    
    col_yes, col_no = st.columns(2)
    with col_yes:
        if st.button("Да, удалить", type="primary", use_container_width=True):
            try:
                # Очищаем ID от возможных преобразований Pandas (float/object)
                clean_id = int(float(str(record_id)))
                
                # Вызываем функцию из бэкенда (работает по первичному ключу наряда)
                db.delete_work_order(clean_id)
                
                st.success("✅ Запись успешно удалена!")
                if "w_table_selection" in st.session_state:
                    st.session_state["w_table_selection"] = {"selection": {"rows": [], "columns": []}}
                time.sleep(1.0)
                st.rerun()
            except Exception as e:
                st.error(f"Ошибка удаления: {e}")
                
    with col_no:
        if st.button("Отмена", use_container_width=True):
            # Сбрасываем выделение, чтобы галочка не висела зря
            if "w_table_selection" in st.session_state:
                st.session_state["w_table_selection"] = {"selection": {"rows": [], "columns": []}}
            st.rerun()
            
            
@st.dialog(":material/task: Карточка выполненной работы", width="large")
def open_view_modal(row_data: pd.Series):
    """Модальное окно для детального просмотра параметров выбранной работы."""
    
    # Заголовок с основной информацией о машине
    st.subheader(f"{row_data.get('eq_type')} {row_data.get('eq_model')} №{row_data.get('eq_board')} | Дата выполнения: **{row_data.get('eq_date')}**")
    st.divider()
    
    # Ряд 1: Временные и эксплуатационные показатели
    c1, c2, c3 = st.columns(3)
    with c1:
        # ИСПРАВЛЕНО: Безопасное отображение моточасов (работает и с int, и с float типами данных)
        try:
            hours_val = f"{float(row_data.get('eq_hours', 0)):.1f}".replace(".0", "")
        except Exception:
            hours_val = str(row_data.get('eq_hours', 0))
        st.metric(label="Наработка (моточасы)", value=f"{hours_val} м/ч")
        
    with c2:
        st.metric(label="Время начала смены", value=str(row_data.get("time_start", "—")))
    with c3:
        st.metric(label="Время окончания", value=str(row_data.get("time_end", "—")))
        
    st.write(" ")
    
    # Ряд 2: Текстовые данные
    st.text_input("Плановое задание", value=str(row_data.get("eq_task", "—")), disabled=True)
    st.text_input("Исполнитель работ", value=str(row_data.get("eq_executor", "—")), disabled=True)
    
    # Большие текстовые блоки
    st.text_area("Детальное описание выполненных работ", value=str(row_data.get("eq_desc", "—")), height=120, disabled=True)
    st.text_area("Технические примечания / Замеры", value=str(row_data.get("eq_notes", "—")), height=80, disabled=True)
    
    st.divider()
    
    # Кнопка закрытия карточки
    if st.button("Закрыть карточку", use_container_width=True, type="primary"):
        # Дополнительно сбрасываем галочку выделения строки, чтобы интерфейс выглядел аккуратно
        if "w_table_selection" in st.session_state:
            st.session_state["w_table_selection"] = {"selection": {"rows": [], "columns": []}}
        st.rerun()


def filter_work_data(df_works: pd.DataFrame, filters: dict) -> pd.DataFrame:
    """Фильтрует переданный DataFrame на основе словаря критериев поиска."""
    filtered = df_works.copy()

    # 1. Строгий точечный поиск по борту (точное совпадение строки)
    if filters["board"]:
        filtered = filtered[filtered['eq_board'].astype(str).str.lower() == filters["board"].lower()]
        
    # 2. Поиск по типу техники
    if filters["type"] != "Все":
        filtered = filtered[filtered['eq_type'] == filters["type"]]
        
    # 3. Поиск по модели техники
    if filters["model"] != "Все":
        filtered = filtered[filtered['eq_model'] == filters["model"]]
        
    # 4. Ослабленный поиск по куску ключевого слова во всех текстовых полях журнала
    if filters["search"]:
        q = filters["search"].lower()
        mask = (
            filtered['eq_task'].astype(str).str.lower().str.contains(q, na=False) | 
            filtered['eq_desc'].astype(str).str.lower().str.contains(q, na=False) | 
            filtered['eq_executor'].astype(str).str.lower().str.contains(q, na=False) |
            filtered['eq_notes'].astype(str).str.lower().str.contains(q, na=False)
        )
        filtered = filtered[mask]
        
    return filtered.reset_index(drop=True)

def export_excel_template():
    """Скачивание шаблона эксель с техникой"""
    # Генерируем пустой xlsx-шаблон в памяти
    blank_eq_file = db.generate_equipment_blank_template()
    
    # Кнопка скачивания бланка техники
    st.download_button(
        label=":material/download: Скачать Шаблон_Список_техники.xlsx",
        data=blank_eq_file,
        file_name="Шаблон_Список_техники.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        width="stretch", 
        key="settings_download_eq_template_btn"
    )
    
def import_excel_data():
    """Загрузка в базу списка техинки по шаблону"""
    # Инициализируем состояние видимости загрузчика, если его еще нет
    if "show_uploader" not in st.session_state:
        st.session_state.show_uploader = False

    # 2. Кнопка загрузки файла
    if st.button(
        label=":material/upload: Импортировать Список техники (.xlsx)", 
        width="stretch",
        key="settings_trigger_upload_btn"
    ):
        # Меняем состояние на противоположное при клике
        st.session_state.show_uploader = not st.session_state.show_uploader

    # Если кнопка была нажата, ровно под ней открывается поле для выбора файла
    if st.session_state.show_uploader:
        uploaded_file = st.file_uploader(
            label="Выберите заполненный файл шаблона:",
            type=["xlsx"],
            accept_multiple_files=False,
            key="settings_upload_eq_file"
        )

        if uploaded_file is not None:
            success, message = db.import_equipment_from_excel(uploaded_file)
            if success:
                st.success(message)
                # Скрываем загрузчик после успешного импорта
                st.session_state.show_uploader = False
                st.rerun()
            else:
                st.error(message)

def export_excel_data():
    """Функция экспорта текущей базы данных в файл эксель"""
    export_current_date = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    exported_eq_file = db.export_equipment_to_excel()
    st.download_button(
        label=":material/upload_file: Выгрузить список техники (.xlsx)",
        data=exported_eq_file,
        file_name=f"Список_техники_{export_current_date}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        width="stretch",
        key="settings_export_eq_btn",
    )

def auth_page():    
    # ==============================================================================
    # ИЗОЛИРОВАННЫЙ БЛОК: ВХОД И РЕГИСТРАЦИЯ
    # ==============================================================================
    if not st.session_state.get("auth_logged_in", False):
        st.html("""
            <style>
                /* Намертво вырезаем верхнюю панель Streamlit до её отрисовки, убирая прыжки */
                [data-testid="stHeader"] {
                    display: none !important;
                    height: 0px !important;
                    visibility: hidden !important;
                }
                /* Скрываем служебное меню настроек (три точки) */
                #MainMenu {
                    visibility: hidden !important;
                }
                .stMainBlockContainer { 
                    max-width: 420px !important; 
                    padding-top: 10% !important; 
                }
            </style>
        """)
        
        with st.container(border=True):
            st.markdown("<h2 style='text-align: center; color: #140A9A; margin-bottom: 0;'>MECHANIK</h2>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; color: gray; font-size: 13px;'>Система оперативного учета ТОиР</p>", unsafe_allow_html=True)
            st.write(" ")
            
            # --- Контроль состояния радио-кнопки ---
            if "auth_mode" not in st.session_state:
                st.session_state["auth_mode"] = "Вход в систему"

            # Callback-функция для синхронизации при ручном клике пользователя
            def on_auth_mode_change():
                st.session_state["auth_mode"] = st.session_state["auth_mode_selector_widget"]

            options = ["Вход в систему", "Регистрация"]
            current_index = options.index(st.session_state["auth_mode"])

            # Сохраняем строго в auth_mode, чтобы избежать конфликта имен
            auth_mode = st.radio(
                "Выберите действие:",
                options=options,
                index=current_index,
                key="auth_mode_selector_widget",
                on_change=on_auth_mode_change
            )
            st.divider()
            
            # --- РЕЖИМ 1: ВХОД В СИСТЕМУ ---
            if auth_mode == "Вход в систему":
                default_login = st.session_state.get("last_registered_user", "")
                
                # Передаем сохраненный логин в value
                login_user = st.text_input("Логин", value=default_login, key="login_username_field").strip()
                login_pwd = st.text_input("Пароль", type="password", key="login_password_field")
                st.write(" ")
                
                if st.button("Войти в программу", type="primary", use_container_width=True):
                    if not login_user or not login_pwd:
                        st.error("🔒 Заполните все поля для входа!")
                    else:
                        user_data = db.verify_user_credentials(login_user, login_pwd)
                        if user_data:
                            st.session_state["auth_logged_in"] = True
                            st.session_state["user_fio"] = user_data["fio"]
                            st.session_state["role"] = user_data["role"]
                            st.session_state["user_id"] = user_data.get("id") 
                            
                            st.toast(f"🎉 Добро пожаловать, {user_data['fio']}!")
                            time.sleep(1.5)
                            st.rerun()
                        else:
                            st.error("❌ Неверный логин или пароль!")
            
            # --- РЕЖИМ 2: РЕГИСТРАЦИЯ НОВОГО СОТРУДНИКА ---
            else:
                reg_fio = st.text_input("ФИО сотрудника", placeholder="Иванов И. И.", key="reg_fio_field").strip()
                reg_user = st.text_input("Желаемый логин", placeholder="ivanov99", key="reg_user_field").strip()
                reg_pwd = st.text_input("Придумайте пароль", type="password", key="reg_pwd_field")
                st.write(" ")
                
                if st.button("Зарегистрировать аккаунт", type="primary", use_container_width=True):
                    if not reg_fio or not reg_user or not reg_pwd:
                        st.error("⚠️ Пожалуйста, заполните все поля формы!")
                    elif len(reg_pwd) < 4:
                        st.error("⚠️ Пароль должен быть не менее 4 символов!")
                    else:
                        try:
                            # Записываем нового пользователя в базу данных
                            db.register_new_user(reg_user, reg_fio, reg_pwd, role="user")
                            
                            st.success(f"🎉 Пользователь {reg_user} успешно зарегистрирован!")
                            
                            # 1. Запоминаем логин для автозаполнения
                            st.session_state["last_registered_user"] = reg_user
                            
                            # 2. МЕНЯЕМ РЕЖИМ: Переводим текстовый статус во "Вход в систему"
                            st.session_state["auth_mode"] = "Вход в систему"
                            
                            # 3. Полностью вырезаем кэш виджета, чтобы он принудительно перестроился по новому auth_mode
                            st.session_state.pop("auth_mode_selector_widget", None)
                            
                            time.sleep(1.5)
                            st.rerun()
                            
                        except db.DatabaseError as e:
                            st.error(f"❌ {e}")
        
        st.stop()

# --- ГЛАВНЫЕ ВКЛАДКИ ---
def equipment_tab():
    """Функция вкладки Техника"""
    # Загружаем сырые данные из базы данных 
    df_raw = db.load_equipment()
    
    # Выводим панель фильтрации техники
    filtered_data = equipment_filters(df_raw)
    
    # Отрисовываем таблицу со списком техники 
    equipment_table(filtered_data)
        
        
def works_tab():
    """Функция главной вкладки Работы"""

    # 1. Загружаем из базы полный срез выполненных ремонтов/ТО
    df_raw_maintenance = db.load_work_orders()
    
    # 2. По значениям на панели фильтров (возвращает словарь выбранных значений)
    current_filters = work_filters(df_raw_maintenance)
    
    # 3. Фильтруем данные на основе выбранных критериев
    filtered_maintenance = filter_work_data(df_raw_maintenance, current_filters)
    
    # 4. Выводим кнопки управления админа и итоговую интерактивную таблицу
    # Передаем исходный df_raw_maintenance для работы кнопок "Добавить/Изменить",
    # и отфильтрованный filtered_maintenance для отображения в самой таблице.
    work_table(df_raw_maintenance, filtered_maintenance)


    
def tools_tab():
    """Функция вкладки Инструменты"""
    pass
    

def docs_tab():
    """Функция вкладки Документы"""
    # 1. Разделяем рабочую область вашей вкладки на две колонки
    # Левая колонка для меню (умеренно узкая), правая — для форм ввода
    st.write("")
    col_menu, col_content = st.columns([1.2, 3.5], gap="medium")

    with col_menu:
        
        
        # 2. Инициализируем литое вертикальное option_menu
        selected_subtab = option_menu(
            menu_title=None,       # Скрываем общий заголовок виджета
            options=["Профиль компании", "Финаzнсы и Налоги", "Склад и Логистика"],
            icons=["building", "wallet2", "box-seam"], # Названия иконок Bootstrap
            menu_icon="cast", 
            default_index=0,       # Индекс вкладки, открытой по умолчанию
            orientation="vertical", # Принудительный вертикальный режим
            styles={
                "container": {
                    "padding": "0px !important", 
                    "background-color": "#ffffff",
                    "border": "1px solid #E0E0E0",
                    "border-radius": "8px"
                },
                "icon": {
                    "color": "#666666", 
                    "font-size": "16px"
                }, 
                "nav-link": {
                    "font-size": "15px", 
                    "text-align": "left", 
                    "margin": "0px", 
                    "--hover-color": "#F8F9FA", # Цвет при наведении мыши
                    "border-radius": "0px",     # Делаем пункты прямоугольными внутри литого блока
                    "padding": "12px 15px"
                },
                "nav-link-selected": {
                    "background-color": "#F8F9FA", # Глубокий синий цвет для активного пункта ERP
                    "color": "black",
                    "font-weight": "600"
                }
            }
        )

    # 3. Динамическая отрисовка контента в правой колонке в зависимости от строки в selected_subtab
    with col_content:
        if selected_subtab == "Профиль компании":
            
            with st.form("form_profile"):
                st.caption("Профиль компании")
                st.text_input("Название компании", value="ООО Рога и Копыта")
                st.text_input("ИНН", value="7701234567")
                st.form_submit_button("Сохранить изменения", type="primary")
                
        elif selected_subtab == "Финансы и Налоги":
            
            with st.form("form_finance"):
                st.caption("Финансы и Налоги")
                st.selectbox("Валюта по умолчанию", ["RUB (₽)", "USD ($)", "EUR (€)"])
                st.slider("Ставка НДС (%)", 0, 20, 20)
                st.form_submit_button("Принять экономические правила", type="primary")
                
        elif selected_subtab == "Склад и Логистика":
            
            with st.form("form_logistic"):
                st.caption("Склад и Логистика")
                st.radio("Стратегия списания запасов", ["FIFO", "LIFO", "По средней стоимости"])
                st.toggle("Разрешить отрицательные остатки", value=False)
                st.form_submit_button("Сохранить параметры", type="primary")
            
            

def settings_tab():
    """Панель настроек: редактирование данных сотрудников (для админа) и личная смена пароля."""
    
    
    is_admin = st.session_state.get("role") == "admin"
    current_user_login = "admin" if is_admin else st.session_state.get("login_username_field", "user")
    
    # Инициализируем состояние редактирования в сессии, если его еще нет
    if "edit_user_id" not in st.session_state:
        st.session_state["edit_user_id"] = None
    
    # Распределяем пространство: 4 части слева (Панель админа), 2 части справа (Смена своего пароля)
    col1, col2 = st.columns(2)
    
    # ==============================================================================
    # ЛЕВАЯ КОЛОНКА: УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ (Доступно ТОЛЬКО Администратору)
    # ==============================================================================
    with col1:    
        if is_admin:
            st.markdown("### 👥 Управление доступом сотрудников")
            st.caption("Список учетных записей. Вы можете изменить ФИО, логин, роль или сбросить забытый пароль.")
            
            # 1. Читаем всех пользователей из базы данных (кроме самого суперадмина 'admin')
            try:
                with db.get_connection_context() as conn:
                    df_users = pd.read_sql_query("""
                        SELECT id, username, fio, role 
                        FROM users 
                        WHERE username != 'admin'
                        ORDER BY fio ASC;
                    """, conn)
            except Exception as e:
                st.error(f"Ошибка загрузки пользователей: {e}")
                df_users = pd.DataFrame()

            if df_users.empty:
                st.info("ℹ️ В системе пока нет других зарегистрированных сотрудников.")
            else:
                # 2. Отрисовываем каждого пользователя красивой строчкой
                for _, row in df_users.iterrows():
                    user_id = row["id"]
                    u_login = row["username"]
                    u_fio = row["fio"]
                    u_role = row["role"]
                    
                    with st.container(border=True):
                        # ПРОВЕРКА: Если этот конкретный пользователь выбран для редактирования
                        if st.session_state["edit_user_id"] == user_id:
                            st.markdown(f"📝 **Редактирование профиля: `{u_login}`**")
                            
                            # Поля для изменения данных
                            new_fio = st.text_input("ФИО сотрудника", value=u_fio, key=f"edit_fio_{user_id}").strip()
                            new_login = st.text_input("Логин (Имя пользователя)", value=u_login, key=f"edit_login_{user_id}").strip()
                            
                            role_options = ["user", "admin"]
                            role_labels = {"user": "Диспетчер (Пользователь)", "admin": "Администратор"}
                            try:
                                current_role_idx = role_options.index(u_role)
                            except ValueError:
                                current_role_idx = 0
                                
                            new_role = st.selectbox(
                                "Права доступа", 
                                options=role_options, 
                                index=current_role_idx,
                                format_func=lambda x: role_labels[x],
                                key=f"edit_role_{user_id}"
                            )
                            
                            # Кнопки сохранения и отмены
                            btn_save_col, btn_cancel_col = st.columns(2)
                            with btn_save_col:
                                if st.button("💾 Сохранить", key=f"save_user_changes_{user_id}", type="primary", use_container_width=True):
                                    if not new_fio or not new_login:
                                        st.error("⚠️ Поля ФИО и Логин не могут быть пустыми!")
                                    else:
                                        try:
                                            with db.get_connection_context() as conn:
                                                cursor = conn.cursor()
                                                cursor.execute("""
                                                    UPDATE users 
                                                    SET fio = ?, username = ?, role = ? 
                                                    WHERE id = ?
                                                """, (new_fio, new_login, new_role, user_id))
                                            st.toast(f"✅ Данные сотрудника {new_login} обновлены!")
                                            st.session_state["edit_user_id"] = None # Выходим из режима редактирования      
                                            time.sleep(1.0)
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"Ошибка при обновлении: логин уже занят или сбой БД. {e}")
                            with btn_cancel_col:
                                if st.button("❌ Отмена", key=f"cancel_user_changes_{user_id}", use_container_width=True):
                                    st.session_state["edit_user_id"] = None
                                    st.rerun()
                        
                        # ОБЫЧНЫЙ РЕЖИМ (Просмотр карточки)
                        else:
                            role_title = "Администратор" if u_role == "admin" else "Диспетчер (Пользователь)"
                            row_col1, row_col2, row_col3 = st.columns([0.55, 0.23, 0.22], vertical_alignment="center")
                            
                            with row_col1:
                                st.markdown(f"FIO: **{u_fio}** &nbsp;|&nbsp; Login: `{u_login}`")
                                st.caption(f"Роль в системе: {role_title}")
                                
                            with row_col2:
                                # Кнопка переключения в режим редактирования
                                if st.button("✏️ Изменить", key=f"edit_user_trigger_{user_id}", use_container_width=True):
                                    st.session_state["edit_user_id"] = user_id
                                    st.rerun()
                                    
                            with row_col3:
                                # Кнопка сброса пароля
                                if st.button("🔄 Сброс", key=f"reset_user_pwd_btn_{user_id}", use_container_width=True):
                                    temp_password = "123456"
                                    temp_hash = hashlib.sha256(temp_password.encode()).hexdigest()
                                    try:
                                        with db.get_connection_context() as conn:
                                            cursor = conn.cursor()
                                            cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (temp_hash, user_id))
                                        st.toast(f"🔑 Пароль для {u_login} сброшен на: {temp_password}", icon="🔑")
                                        time.sleep(1.5)
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Ошибка сброса: {e}")
        else:
            st.write("")
        
    # ==============================================================================
    # ПРАВАЯ КОЛОНКА: ЛИЧНАЯ СМЕНА ПАРОЛЯ (Доступно всем вошедшим)
    # ==============================================================================
    with col2:        
        if st.session_state.get("auth_logged_in"):
            with st.expander("Изменить пароль"):
                with st.container(border=True):
                    st.caption(f"Вы вошли как: **{st.session_state.get('user_fio')}**")
                    
                    new_pwd = st.text_input("Новый сложный пароль", type="password", placeholder="Минимум 6 знаков", key="set_tab_new_pwd")
                    confirm_pwd = st.text_input("Повторите новый пароль", type="password", placeholder="Повтор...", key="set_tab_confirm_pwd")
                    st.write(" ")
                    
                    if st.button("🖫 Сохранить мой пароль", type="primary", use_container_width=True):
                        if not new_pwd or not confirm_pwd:
                            st.error("⚠️ Заполните оба поля формы!")
                        elif len(new_pwd) < 6:
                            st.error("⚠️ Пароль слишком короткий!")
                        elif new_pwd != confirm_pwd:
                            st.error("❌ Введенные пароли не совпадают!")
                        else:
                            new_hash = hashlib.sha256(new_pwd.encode()).hexdigest()
                            try:
                                with db.get_connection_context() as conn:
                                    cursor = conn.cursor()
                                    cursor.execute("UPDATE users SET password_hash = ? WHERE username = ?", (new_hash, current_user_login))
                                st.success("🎉 Ваш пароль успешно изменен!")
                                time.sleep(1.5)
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Ошибка записи в БД: {e}")
        else:
            st.warning("Пожалуйста, авторизуйтесь.")


def main():
    """Application entry point."""
    # Настройка страницы
    st.set_page_config(page_title="MECHANIK", layout="wide", page_icon=":material/construction:")
    
    # Load styles
    load_external_css(".streamlit/style.css")
    
        # Initialize database
    try:
        db.init_db()
    except Exception as e:
        st.error(f"Ошибка подключения к базе данных: {e}")
        logger.error(f"Database initialization failed: {e}")
        st.stop()
    
    # 1. СТРОГО ЗДЕСЬ: Гарантируем наличие переменных для всей программы сразу
    if "auth_logged_in" not in st.session_state: 
        st.session_state["auth_logged_in"] = False
    if "role" not in st.session_state: 
        st.session_state["role"] = "user"
    if "user_fio" not in st.session_state: 
        st.session_state["user_fio"] = "Гость" # По умолчанию пишем универсальный статус

    # 2. Перехватчик логаута (теперь он работает в полной безопасности)
    if st.query_params.get("logout") == "1":
        st.session_state["auth_logged_in"] = False
        st.session_state["role"] = "user"
        st.session_state["user_fio"] = "Гость"
        st.query_params.clear()
        st.rerun()

    # 3. Проверка авторизации
    if not st.session_state["auth_logged_in"]:
        auth_page() # Вызываем форму входа, если еще не авторизованы
        st.stop()
        
    # Загрузка информационной панели вверху страницы
    info_panel()
    
    
    # ==============================================================================
    # РАБОЧАЯ ЗОНА СИСТЕМЫ (Открывается только после авторизации)
    # ==============================================================================
    # Возвращаем широкую разметку для больших таблиц данных
    st.html("<style>.stMainBlockContainer { max-width: 100% !important; padding-top: 35px !important; }</style>")
    

    
    
    # Создание шапки
    # app_header()
        
    # Создание главных вкладок
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["ТЕХНИКА", "РАБОТЫ", "ИНСТРУМЕНТЫ", "ДОКУМЕНТЫ", "НАСТРОЙКИ"], default="РАБОТЫ")
           
    with tab1:
        # Наполнение вкладки Техника
        equipment_tab()
        
    with tab2:
        # Наполнение вкладки Работы
        works_tab()
  
    with tab3:
        tools_tab()
        
    with tab4:
        docs_tab()
        
    with tab5:
        settings_tab()

    app_footer()
    
    
if __name__ == "__main__":
    main()