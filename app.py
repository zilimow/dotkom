# app.py
import streamlit as st
from datetime import datetime
import pandas as pd
# Импортируем все необходимые функции
from database.db_manager import (
    init_db, add_record, load_data_as_df, update_db_from_df,
    add_machine, load_machinery_registry, update_machinery_registry
)

# Настройка страницы
st.set_page_config(page_title="Учет работ техники", layout="wide")

def local_css(file_name):
    with open(file_name, "r", encoding="utf-8") as f:
        st.html(f"<style>{f.read()}</style>")

local_css("data/style.css")
init_db()

# Загрузка актуальных данных
df_logs = load_data_as_df()
df_machines = load_machinery_registry()

# Шапка главной страницы
st.title("Система управления парком техники")
st.divider()

# Создаем глобальные вкладки для разделения системы
tab_logs, tab_registry = st.tabs(["📋 Журнал учета работ", "🚜 Справочник техники (Паспорта)"])


# =====================================================================
# ВКЛАДКА 1: ЖУРНАЛ УЧЕТА РАБОТ
# =====================================================================
with tab_logs:
    # (Здесь остается ваш логический блок по вводу работ и таблице поиска работ)
    # Конфигурация колонок работ
    rus_logs_config = {
        "id": None, "date": st.column_config.DateColumn("Дата работы", format="DD.MM.YYYY"),
        "tech_type": st.column_config.TextColumn("Тип техники"), "model": st.column_config.TextColumn("Модель / Номер"),
        "work_done": st.column_config.TextColumn("Описание работ"), "hours": st.column_config.NumberColumn("Часы", format="%.1f"),
        "driver": st.column_config.TextColumn("Машинист"), "status": st.column_config.TextColumn("Статус")
    }
    
    with st.expander("Добавить новую запись о работе техники", expanded=False):
        with st.form("add_record_form", clear_on_submit=True):
            col_date, col_type, col_model, col_hours = st.columns(4)
            with col_date: input_date = st.date_input("Дата работы:", datetime.now(), key="log_date")
            with col_type: input_type = st.selectbox("Тип техники:", ["Экскаватор", "Самосвал", "Бульдозер", "Погрузчик", "Другое"], key="log_type")
            with col_model: input_model = st.text_input("Модель / Номер машины:", placeholder="например, CAT 320", key="log_model")
            with col_hours: input_hours = st.number_input("Моточасы / Часы работы:", min_value=0.0, step=0.5, key="log_hours")
            
            col_driver, col_status = st.columns(2)
            with col_driver: input_driver = st.text_input("ФИО Машиниста:", placeholder="Иванов И.И.", key="log_driver")
            with col_status: input_status = st.selectbox("Статус техники:", ["В работе (Исправна)", "Требует ТО", "В ремонте"], key="log_status")
            
            input_work = st.text_area("Описание проделанной работы:", placeholder="Что именно было сделано...", key="log_work")
            if st.form_submit_button("Сохранить в базу данных"):
                if input_model.strip() and input_work.strip():
                    add_record(input_date.strftime("%Y-%m-%d"), input_type, input_model, input_work, input_hours, input_driver, input_status)
                    st.success("Запись успешно добавлена!")
                    st.rerun()

    st.subheader("Поиск и редактирование журнала работ")
    if df_logs.empty:
        st.info("В журнале работ пока нет записей.")
    else:
        # Фильтры журнала
        l_col1, l_col2 = st.columns(2)
        with l_col1:
            filter_types_l = st.multiselect("Фильтр по типу:", options=df_logs["tech_type"].unique(), default=df_logs["tech_type"].unique(), key="f_type_l")
        with l_col2:
            search_query_l = st.text_input("Поиск по тексту работы или модели:", placeholder="Введите текст...", key="f_search_l")
            
        filtered_logs = df_logs[df_logs["tech_type"].isin(filter_types_l)]
        if search_query_l:
            filtered_logs = filtered_logs[filtered_logs["model"].str.contains(search_query_l, case=False) | filtered_logs["work_done"].str.contains(search_query_l, case=False)]
            
        df_logs_display = filtered_logs.iloc[::-1]
        edited_logs = st.data_editor(df_logs_display, num_rows="dynamic", use_container_width=True, hide_index=True, column_config=rus_logs_config, key="logs_editor")
        
        if st.button("Зафиксировать изменения в Журнале", type="primary"):
            final_logs = df_logs.copy()
            final_logs = final_logs[~final_logs['id'].isin(df_logs_display['id'])]
            final_logs = pd.concat([final_logs, edited_logs], ignore_index=True)
            update_db_from_df(final_logs)
            st.success("Журнал работ обновлен!")
            st.rerun()


# =====================================================================
# НОВАЯ ВКЛАДКА 2: СПРАВОЧНИК ТЕХНИКИ
# =====================================================================
with tab_registry:
    st.subheader("Управление реестром машин")
    
    # Настройка русских заголовков для новой таблицы справочника
    rus_machinery_config = {
        "id": None,
        "board_number": st.column_config.TextColumn("Бортовой номер"),
        "serial_number": st.column_config.TextColumn("Серийный номер (VIN)"),
        "model": st.column_config.TextColumn("Модель техники"),
        "prod_year": st.column_config.NumberColumn("Год производства", format="%d"),
        "tech_type": st.column_config.TextColumn("Тип техники"),
        "engine_model": st.column_config.TextColumn("Модель двигателя"),
        "engine_number": st.column_config.TextColumn("Номер двигателя"),
        "linkone_code": st.column_config.TextColumn("Код LinkOne")
    }

    # 1. Меню добавления новой единицы техники (Expander)
    with st.expander("Внести новую единицу техники в справочник", expanded=False):
        with st.form("add_machine_form", clear_on_submit=True):
            
            # Строка 1: Основные параметры в процентах [20%, 30%, 35%, 15%]
            m_col1, m_col2, m_col3, m_col4 = st.columns([20, 30, 35, 15])
            with m_col1:
                m_board = st.text_input("Бортовой номер:", placeholder="например, Э-05, С-12")
            with m_col2:
                m_serial = st.text_input("Серийный номер:")
            with m_col3:
                m_model = st.text_input("Модель техники:", placeholder="например, Komatsu PC300")
            with m_col4:
                m_year = st.number_input("Год производства:", min_value=1950, max_value=datetime.now().year, step=1, value=2020)
                
            # Строка 2: Двигатель и классификация [20%, 30%, 30%, 20%]
            m_col5, m_col6, m_col7, m_col8 = st.columns([20, 30, 30, 20])
            with m_col5:
                m_type = st.selectbox("Тип техники:", ["Экскаватор", "Самосвал", "Бульдозер", "Погрузчик", "Другое"], key="reg_type_select")
            with m_col6:
                m_eng_model = st.text_input("Модель двигателя:")
            with m_col7:
                m_eng_num = st.text_input("Номер двигателя:")
            with m_col8:
                m_linkone = st.text_input("Код LinkOne:", placeholder="Код для каталогов")
                
            if st.form_submit_button("Занести технику в справочник"):
                if m_board.strip() and m_model.strip():
                    add_machine(m_board, m_serial, m_model, int(m_year), m_type, m_eng_model, m_eng_num, m_linkone)
                    st.success(f"Техника {m_board} {m_model} успешно добавлена в справочник!")
                    st.rerun()
                else:
                    st.error("Поля 'Бортовой номер' и 'Модель техники' обязательны для заполнения.")

    st.divider()
    
    # 2. Поиск, вывод и редактирование реестра
    st.write("#### Зарегистрированная техника")
    if df_machines.empty:
        st.info("Справочник пока пуст. Заполните форму выше.")
    else:
        # Панель поиска по коду LinkOne, бортовому или серийному номеру
        reg_col1, reg_col2 = st.columns(2)
        with reg_col1:
            filter_types_r = st.multiselect("Фильтр типов:", options=df_machines["tech_type"].unique(), default=df_machines["tech_type"].unique(), key="f_type_r")
        with reg_col2:
            search_query_r = st.text_input("Поиск по Бортовому / Серийнику / Коду LinkOne:", placeholder="Введите поисковый запрос...", key="f_search_r")
            
        # Применение фильтров
        filtered_machines = df_machines[df_machines["tech_type"].isin(filter_types_r)]
        if search_query_r:
            filtered_machines = filtered_machines[
                filtered_machines["board_number"].str.contains(search_query_r, case=False) |
                filtered_machines["serial_number"].str.contains(search_query_r, case=False) |
                filtered_machines["linkone_code"].str.contains(search_query_r, case=False) |
                filtered_machines["model"].str.contains(search_query_r, case=False)
            ]
            
        st.write(f"Найдено машин: {len(filtered_machines)}")
        
        # Отображение редактируемой таблицы справочника
        edited_machines = st.data_editor(
            filtered_machines,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            column_config=rus_machinery_config,
            key="machinery_registry_editor"
            )
        
    # Кнопка сохранения изменений в реестре
    if st.button("Зафиксировать изменения в Справочнике", type="primary"):
        final_machines = df_machines.copy()
        # Удаляем старые строки и вставляем отредактированные
        final_machines = final_machines[~final_machines['id'].isin(filtered_machines['id'])]
        final_machines = pd.concat([final_machines, edited_machines], ignore_index=True)

        update_machinery_registry(final_machines)
        st.success("Справочник техники успешно обновлен!")
        st.rerun()