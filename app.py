# app.py
import streamlit as st
from datetime import datetime
import pandas as pd
# Импортируем все необходимые функции
from database.db_manager import (
    init_db, add_record, load_data_as_df, update_db_from_df,
    add_machine, load_machinery_registry, update_machinery_registry,
    add_mechanic, load_mechanics, update_mechanics
)

# Настройка страницы
st.set_page_config(page_title="Учет работ техники", layout="wide")


def local_css(file_name):
    """Загрузка """
    try:
        with open(file_name, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning(f"Файл {file_name} не найден. Используются стандартные стили.")

# Проверка наличия CSS файла
try:
    local_css("data/style.css")
except:
    pass


init_db()

# Загрузка актуальных данных
df_logs = load_data_as_df()
df_machines = load_machinery_registry()

# Конвертируем дату для правильного отображения календаря
if not df_logs.empty and 'date' in df_logs.columns:
    df_logs['date'] = pd.to_datetime(df_logs['date'])

# Шапка главной страницы
st.title("Система управления парком техники")

# Создаем глобальные вкладки для разделения системы
tab_logs, tab_equipment, tab_tools, tab_parts, tab_mechanics = st.tabs(["Работы", "Техника", "Инструменты", "Запчасти", "Механики"])


# =====================================================================
# ВКЛАДКА 1: ЖУРНАЛ УЧЕТА РАБОТ
# =====================================================================
with tab_logs:
       # Конфигурация колонок работ
    rus_logs_config = {
        "id": None, 
        "date": st.column_config.DateColumn("Дата работы", format="DD.MM.YYYY", step="day"),
        "tech_type": st.column_config.TextColumn("Тип техники"), 
        "model": st.column_config.TextColumn("Модель / Номер"),
        "work_done": st.column_config.TextColumn("Описание работ"), 
        "hours": st.column_config.NumberColumn("Часы", format="%.0f"),
        "driver": st.column_config.TextColumn("Машинист"), 
        "status": st.column_config.TextColumn("Статус")
    }
    
    with st.expander("Добавить новую запись о работе техники", expanded=False):
        with st.form("add_record_form", clear_on_submit=True):
            col_date, col_type, col_model, col_hours = st.columns(4)
            
            with col_date: input_date = st.date_input("Дата работы:", datetime.now(), format="DD.MM.YYYY", key="log_date", )
            with col_type: input_type = st.selectbox("Тип техники:", ["Экскаватор", "Самосвал", "Бульдозер", "Погрузчик", "Другое"], key="log_type")
            with col_model: input_model = st.text_input("Модель / Номер машины:", placeholder="например, CAT 320", key="log_model")
            with col_hours: input_hours = st.number_input("Моточасы / Часы работы:", min_value=0.0, step=0.5, key="log_hours")
            
            col_driver, col_status = st.columns(2)
            with col_driver: 
                # Получаем список механиков
                df_mechanics = load_mechanics()
                mechanics_list = df_mechanics['name'].tolist() if not df_mechanics.empty else []

                input_driver = st.selectbox(
                    "ФИО Механика:", 
                    options=mechanics_list,
                    placeholder="Начните вводить имя механика...",
                    key="log_driver"
    )
    
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
            # КОНВЕРТАЦИЯ ЗДЕСЬ - перед сохранением
            if 'date' in final_logs.columns:
                final_logs['date'] = pd.to_datetime(final_logs['date']).dt.strftime("%Y-%m-%d")

            st.success("Журнал работ обновлен!")
            st.rerun()




# =====================================================================
# ВКЛАДКА 2: ТЕХНИКА
# =====================================================================
with tab_equipment:
        
    # Настройка русских заголовков для новой таблицы справочника
    rus_machinery_config = {
        "id": None,
        "board_number": st.column_config.TextColumn("Бортовой номер"),
        "tech_type": st.column_config.TextColumn("Тип техники"),
        "model": st.column_config.TextColumn("Модель техники"),
        "serial_number": st.column_config.TextColumn("Серийный номер (VIN)"),        
        "prod_year": st.column_config.NumberColumn("Год производства", format="%d"),
        "engine_model": st.column_config.TextColumn("Модель двигателя"),
        "engine_number": st.column_config.TextColumn("Номер двигателя"),
        "linkone_code": st.column_config.TextColumn("Код LinkOne")
    }

    # 1. Меню добавления новой единицы техники (Expander)
    with st.expander("Внести новую единицу в справочник по технике", expanded=False):   
        with st.form("add_machine_form", clear_on_submit=True):
            
            # Строка 1: Основные параметры в процентах [20%, 30%, 35%, 15%]
            m_col1, m_col2, m_col3, m_col4, m_col5 = st.columns([10, 30, 35, 15, 10])
            with m_col1:
                m_board = st.text_input("Бортовой номер:", placeholder="например, 38")
            with m_col2:
                m_type = st.selectbox("Тип техники:", ["Экскаватор", "Самосвал", "Бульдозер", "Погрузчик", "Другое"], key="reg_type_select")
            with m_col3:
                # m_model = st.text_input("Модель техники:", placeholder="например, HD785-7")
            # Получаем уникальные модели из базы
                df_machines = load_machinery_registry()
                models = df_machines['model'].unique().tolist() if not df_machines.empty else []
        
                m_model = st.selectbox(
                    "Модель техники:", 
                    options=models,
                    placeholder="Выберите или введите новую модель",
                    index=None  # Не выбирать ничего по умолчанию
                )
                
                # Если нужно сохранить введенное значение
                if m_model is None:
                    m_model = st.text_input("Или введите новую модель:", placeholder="например, Новая модель")    
                    
                    
            with m_col4:
                m_serial = st.text_input("Серийный номер:")
            with m_col5:
                m_year = st.number_input("Год производства:", min_value=1950, max_value=datetime.now().year, step=1, value=2020)
                
            # Строка 2: Двигатель и классификация [20%, 30%, 30%, 20%]
            m_col5, m_col6, m_col7, m_col8 = st.columns([20, 30, 30, 20])
            
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
        


# =====================================================================
# ВКЛАДКА 2: МЕХАНИКИ
# =====================================================================
# with tab_mechanics:
#     | first_name | last_name | position | crew | expertise | phone | hire_date | experience |
with tab_mechanics:
    st.subheader("Справочник механиков")
    
    # Форма добавления
    with st.expander("Добавить механика", expanded=False):
        with st.form("add_mechanic_form", clear_on_submit=False):
            col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
            
            with col1:
                mech_name = st.text_input("ФИО механика:*", key="mech_name")
            with col2:
                mech_position = st.text_input("Должность:")
            with col3:
                mech_crew = st.text_input("Бригада:")
            with col4:
                mech_expertise = st.text_input("Специализация:")
            
            col5, col6, col7 = st.columns([4, 1, 1])
            
            with col5:
                mech_phone = st.text_input("Телефон:")                
            with col6:
                mech_date = st.date_input("Дата приема:", value=datetime.now(), format="DD.MM.YYYY")
            with col7:
                mech_experience = st.text("Стаж работы:")
            
     
            # Две кнопки в одной строке
            btn_col1, btn_col2, _, _, _= st.columns([1,1,1,1,1])
            
            with btn_col1:
                submitted = st.form_submit_button("Добавить механика", use_container_width=True)
            
            with btn_col2:
                clear = st.form_submit_button("Очистить поля", use_container_width=True)
            
            if submitted:
                if mech_name.strip():
                    add_mechanic(mech_name, mech_position, mech_crew, mech_shift, 
                                mech_specialty, mech_phone, mech_date.strftime("%Y-%m-%d"))
                    st.success(f"Механик {mech_name} добавлен!")
                    # Очищаем после успешного добавления
                    for key in ["name_input", "position_input", "crew_input", "shift_input", 
                            "specialty_input", "phone_input"]:
                        if key in st.session_state:
                            st.session_state[key] = ""
                    st.rerun()
                else:
                    st.error("ФИО обязательно")
            
            if clear:
                # Очищаем все поля
                for key in ["name_input", "position_input", "crew_input", "shift_input", 
                        "specialty_input", "phone_input"]:
                    if key in st.session_state:
                        st.session_state[key] = ""
                st.rerun()
                
    with st.expander("Редактировать механика", expanded=False):
        with st.form("edit_mechanic_form"):
            # Выбор механика для редактирования
            df_mechanics = load_mechanics()
            mechanic_list = df_mechanics['name'].tolist() if not df_mechanics.empty else []
            
            selected_mechanic = st.selectbox("Выберите механика:", mechanic_list, key="edit_select")
            
            if selected_mechanic:
                # Загружаем данные выбранного механика
                mechanic_data = df_mechanics[df_mechanics['name'] == selected_mechanic].iloc[0]
                
                # Поля для редактирования
                edit_name = st.text_input("ФИО:", value=mechanic_data['name'])
                edit_phone = st.text_input("Телефон:", value=mechanic_data.get('phone', ''))
                
                if st.form_submit_button("Сохранить изменения"):
                    # Логика обновления
                    st.success("Изменения сохранены!")
                    st.rerun()


    # Таблица механиков
    df_mechanics = load_mechanics()
    if df_mechanics.empty:
        st.info("Список механиков пуст")
    else:
        if "hire_date" in df_mechanics.columns:
            df_mechanics["hire_date"] = pd.to_datetime(df_mechanics["hire_date"]).dt.date

        edited_mechanics = st.data_editor(
            df_mechanics,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            column_config={
                "id": None,
                "name": "ФИО механика",
                "specialty": "Специализация",
                "phone": "Телефон",
                "hire_date": st.column_config.DateColumn("Дата приема", format="DD.MM.YYYY")
            },
            key="mechanics_editor"
        )
        
        if st.button("Сохранить изменения", key="save_mechanics"):
            if "hire_date" in edited_mechanics.columns:
                edited_mechanics["hire_date"] = edited_mechanics["hire_date"].astype(str)
            update_mechanics(edited_mechanics)
            st.success("Список механиков обновлен!")
            st.rerun()
            
            
