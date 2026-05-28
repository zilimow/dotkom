import streamlit as st
import pandas as pd

# Настройки вкладки программы
st.set_page_config(
    page_title= "Dotkom",
    page_icon= "data/build.svg",
    layout= "wide",
    initial_sidebar_state= "expanded", 
    menu_items={
        "Get Help": "https://google.com",
        "Report a bug": "https://google.com",
        "About": "https://google.com"
    }
    )

with st.sidebar:
    # st.image("data/images.png", width="content")
    # st.title("Dotkom")
    page = st.radio("Выберите раздел:", ["Главная", "Отчеты", "Настройки"])
    
        # The widget returns a list of selected strings
    selected_cities = st.sidebar.multiselect(
        label="Choose cities to analyze:",
        options=["Moscow", "Saint Petersburg", "Novosibirsk", "Ekaterinburg"],

    )


    
page = st.selectbox(
    "Номер машины:",
    ["25", "27", "38"]
)

st.file_uploader("Load excel")

