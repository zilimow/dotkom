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


        
def app_header():
    """Отображение шапки приложения с шестеренкой."""
    gear_class = "icon-admin" if st.session_state.get("role") == "admin" else "icon-guest"
    
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

    # Создание информационной строки под логотипом
    divider = "|"
    base_meta = (
        f":material/calendar_month: {current_date}"
        f"&emsp;{divider}&emsp;"
        f":material/schedule: {current_time}"
        f"&emsp;{divider}&emsp;"
        f":green[:material/database:] Соединение установлено "
        f"&emsp;{divider}&emsp;"
        f":yellow[:material/front_loader:] Всего техники: **{total_equipment}**"
    )
    st.caption(base_meta, unsafe_allow_html=True)
    
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
    
    # Выделяем выбранную пользователем строку из состояния таблицы
    selected_row_index = None
    if "w_table_selection" in st.session_state:
        selected_rows = st.session_state["w_table_selection"].get("selection", {}).get("rows", [])
        if selected_rows:
            selected_row_index = selected_rows[0] # Берем первую выбранную строку
            
    act_col1, act_col2, act_col3, act_col4 = st.columns(4)
    
    with act_col1:
        # Кнопка просмотра активна для ЛЮБОГО пользователя, если выбрана строка
        btn_view = st.button(":material/insert_drive_file: Открыть задание", use_container_width=True, key="w_view_action_btn", disabled=selected_row_index is None)
        if btn_view and selected_row_index is not None:
            row_data = df_to_display.iloc[selected_row_index]
            open_view_modal(row_data) # Вызов окна просмотра

                   
        # Ограничиваем остальные кнопки ролью администратора
    if st.session_state.get("role") == "admin":
        with act_col2:
            # ИСПРАВЛЕНО: Убран on_click и st.rerun(), диалог вызывается напрямую внутри тела кнопки
            if st.button("➕ Добавить", use_container_width=True, key="w_add_action_btn"):
                # 1. Принудительно очищаем кэш полей ввода перед открытием формы
                clear_add_workflow_cache() 
                
                # 2. Подгружаем актуальный список техники из базы данных
                df_equipment_raw = db.load_equipment()
                
                # 3. Мгновенно открываем модальное окно добавления
                manual_add_work_modal(df_equipment_raw)
        with act_col3:
            btn_edit = st.button("✏️ Изменить", use_container_width=True, key="w_edit_action_btn", disabled=selected_row_index is None)
            if btn_edit and selected_row_index is not None:
                row_data = df_to_display.iloc[selected_row_index]
                open_edit_modal(row_data)
        with act_col4:
            btn_del = st.button("🗑️ Удалить", use_container_width=True, key="w_del_action_btn", disabled=selected_row_index is None)
            if btn_del and selected_row_index is not None:
                row_data = df_to_display.iloc[selected_row_index]
                open_delete_modal(
                    record_id=row_data.get("id"),
                    eq_date=row_data.get("eq_date"),
                    eq_board=row_data.get("eq_board"),
                    eq_task=row_data.get("eq_task"),
                    eq_executor=row_data.get("eq_executor")
                )
    else:
        # Если зашел не админ, пустые три колонки справа заполняем заглушкой, чтобы интерфейс не съезжал
        with act_col2: st.write("")
        with act_col3: st.write("")
        with act_col4: st.write("")
        
    st.write(" ")
                

    # Конфигурация отображения колонок
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

    if df_to_display.empty:
        display_df = pd.DataFrame(columns=display_cols)
        selection_mode = []
    else:
        display_df = df_to_display[display_cols].copy()
        selection_mode = "single-row" # Разрешаем выбирать строго одну строку для Изменения/Удаления

    # Отрисовка таблицы
    
    st.caption("Список работ")
    st.dataframe(
        display_df,
        column_config=column_config,
        width='stretch',
        hide_index=True,
        height="content",
        on_select="rerun", # Включаем интерактивный выбор строк
        selection_mode=selection_mode,
        key="w_table_selection" # Состояние выбора пишется сюда
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
            work_executor = st.text_input("Исполнитель (ФИО) *", placeholder="Например: Каекбердин", key="w_add_modal_executor").strip()

        work_desc = st.text_area("Описание выполненных работ *", placeholder="Что конкретно было сделано...", height=80, key="w_add_modal_desc").strip()
        work_notes = st.text_area("Примечание (технические замеры, нюансы)", placeholder="Например: закачали 7 МПа...", height=80, key="w_add_modal_notes").strip()

        st.write(" ")
        form_status = st.container()
        submitted = st.form_submit_button("Сохранить запись в журнал", use_container_width=True)

        if submitted:
            if not work_executor or not work_desc:
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
                            work_executor=work_executor,
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
    """Модальное окно для редактирования существующей записи журнала работ."""
    st.write(f"📝 Редактирование записи для машины с бортовым номером: **{row_data.get('eq_board')}**")
    
    # Форма с предзаполненными данными из row_data
    with st.form("modal_edit_work_form"):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            # Преобразуем строку даты обратно в объект date для календаря
            try:
                current_date = datetime.datetime.strptime(row_data.get("eq_date", ""), "%d.%m.%Y").date()
            except Exception:
                try:
                    # На случай, если в БД дата лежит в ISO формате (ГГГГ-ММ-ДД)
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
            work_executor = st.text_input("Исполнитель (ФИО) *", value=str(row_data.get("eq_executor", ""))).strip()

        work_desc = st.text_area("Описание выполненных работ *", value=str(row_data.get("eq_desc", "")), height=80).strip()
        work_notes = st.text_area("Примечание", value=str(row_data.get("eq_notes", "")), height=80).strip()

        st.write(" ")
        form_status = st.container()
        
        submitted = st.form_submit_button("Сохранить изменения", use_container_width=True)

        if submitted:
            if not work_executor or not work_desc:
                form_status.error("❌ Поля Исполнитель и Описание работ обязательны!")
            elif t_start == t_end:
                form_status.error("❌ Время начала и окончания не могут совпадать!")
            else:
                try:
                    # Собираем данные для отправки в БД
                    str_start = t_start.strftime("%H:%M")
                    str_end = t_end.strftime("%H:%M")
                    str_date = work_date.strftime("%d.%m.%Y")
                    
                    # ИСПРАВЛЕНО: Извлекаем системный ID самой записи журнала работ напрямую из переданной строки таблицы
                    record_id = int(row_data.get("id"))

                    # Вызываем вашу функцию обновления в бэкенде
                    db.update_work_order(
                        record_id=record_id,
                        work_date=str_date,
                        work_task=work_task,
                        work_desc=work_desc,
                        work_hours=float(work_hours),
                        time_start=str_start,
                        time_end=str_end,
                        work_executor=work_executor,
                        work_notes=work_notes,
                    )

                    form_status.success("✅ Изменения успешно сохранены!")
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
                
                # Вызываем функцию из бэкенда
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
        st.metric(label="Наработка (моточасы)", value=f"{int(row_data.get('eq_hours', 0))} м/ч")
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
    st.info("Раздел в разработке")


def docs_tab():
    """Функция вкладки Документы"""
    st.info("Раздел в разработке")
    

def settings_tab():
    """Render settings and authentication tab with document templates."""
    st.write("")
    col1, col2 = st.columns([4, 2])
    with col1:    
        st.write("")        
    with col2:        
        if st.session_state.role == "admin":
            if st.button("Завершить сеанс", type="primary", width='stretch'):
                st.session_state.role = "guest"
                st.rerun()
        else:
            password = st.text_input(
                "Пароль",                    
                placeholder="", 
                label_visibility="collapsed",
                width="stretch"
            )
            if password:
                try:
                    if password.strip() == st.secrets["credentials"]["admin_password"]:
                        st.session_state.role = "admin"
                        st.rerun()
                    else:
                        st.error("Неверный пароль")
                except KeyError:
                    st.error("Ошибка конфигурации. Обратитесь к администратору.")
                    logger.error("Secrets configuration missing admin_password")



# --- ГЛАВНАЯ ФУНКЦИЯ ---

def main():
    """Main application entry point."""
    # Page configuration
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
    
    # Создание шапки
    app_header()
        
    # Создание главных вкладок
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["ТЕХНИКА", "РАБОТЫ", "ИНСТРУМЕНТЫ", "ДОКУМЕНТЫ", "НАСТРОЙКИ"])
           
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
            # # Initialize session state
        if "role" not in st.session_state:
            st.session_state.role = "guest"
        # Наполнение вкладки Настройки
        settings_tab()

if __name__ == "__main__":
    main()