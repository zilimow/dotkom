import streamlit as st
import datetime
import sqlite3

# ==========================================
# 💾 DATABASE CONTROLLER LAYER
# ==========================================
DB_FILE = "fleet_operations.db"

def init_db():
    """Initializes standard local hardware infrastructure logging tables."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        
        # 1. Main Equipment Inventory Tracking Registry
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS equipment (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                status TEXT,
                motohours REAL,
                location TEXT
            )
        """)
        
        # Seed default Komatsu units if data does not exist
        cursor.execute("SELECT COUNT(*) FROM equipment")
        if cursor.fetchone()[0] == 0:
            cursor.executemany("INSERT INTO equipment (name, status, motohours, location) VALUES (?, ?, ?, ?)", [
                ("Excavator Komatsu PC210", "Operational", 1240.5, "North Quarry"),
                ("Bulldozer Komatsu D65EX", "Maintenance Required", 3150.2, "South Garage"),
                ("Wheel Loader Komatsu WA380", "Operational", 850.0, "Main Yard")
            ])
            
        # 2. Shared Operator Log entries, shift data, and notes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                daypart TEXT, -- 'Day' or 'Night' shift tracking
                author TEXT,
                content TEXT
            )
        """)
        conn.commit()

def run_query(query, params=()):
    """Helper framework to cleanly run and close SQLite connections safely."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        return cursor.fetchall()

# Initialize localized asset records database tables
init_db()

# ==========================================
# 🛠️ WINDOW ENGINE CONFIGURATIONS & CSS
# ==========================================
st.set_page_config(layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    /* Completely hide the password eye icon */
    [data-testid="stTextInput"] button {
        display: none !important;
    }
    [data-testid="stTextInputPasswordFieldVisibilityToken"] {
        display: none !important;
    }
    
    /* Hide top header deploy and hamburger controls completely */
    header[data-testid="stHeader"] {
        display: none !important;
    }
    
    /* Completely destroy the sidebar frame */
    [data-testid="stSidebar"], [data-testid="stSidebarCollapseButton"] {
        display: none !important;
    }
    
    /* Center canvas breathing padding */
    .block-container {
        padding-top: 2rem !important;
        padding-left: 5rem !important;
        padding-right: 5rem !important;
    }
    
    /* Change tabs font size for workshop screens */
    [data-testid="stBaseButton-tab"] p {
        font-size: 30px !important;   
        font-weight: 600 !important;  
    }
    
    /* APP ICON BASE ANCHORS */
    .header-wrapper {
        display: flex !important;
        align-items: center !important;
        gap: 14px !important;
    }

    /* GUEST MODE STYLE (Muted Flat Slate Gray for Gear Only) */
    .icon-guest {
        fill: #64748b !important;
    }

    /* ADMIN MODE STYLE (Komatsu Blue Gear with Active Yellow Glow Animation) */
    .icon-admin {
        fill: #140A9A !important;
        filter: drop-shadow(0 0 6px rgba(20, 10, 154, 0.4));
        animation: pulse-glow 2s infinite alternate;
    }

    @keyframes pulse-glow {
        0% { filter: drop-shadow(0 0 2px rgba(255, 200, 47, 0.3)); }
        100% { filter: drop-shadow(0 0 8px rgba(255, 200, 47, 0.8)); }
    }

    </style>
""", unsafe_allow_html=True)

# Initialize Session States
if "role" not in st.session_state:
    st.session_state.role = "guest"

# ==========================================
# 🚜 MAIN CONTAINER WORKSPACE INTERFACE (PERMANENT BLUE TITLE)
# ==========================================
if st.session_state.role == "admin":
    # Admin is Online: The Title stays blue, the gear icon lights up and animates
    st.markdown("""
        <div class="header-wrapper">
            <svg class="icon-admin" width="34" height="34" viewBox="0 0 24 24" xmlns="http://w3.org">
                <path d="M19.43 12.98c.04-.32.07-.64.07-.98s-.03-.66-.07-.98l2.11-1.65c.19-.15.24-.42.12-.64l-2-3.46c-.12-.22-.39-.3-.61-.22l-2.49 1c-.52-.4-1.08-.73-1.69-.98l-.38-2.65C14.46 2.18 14.25 2 14 2h-4c-.25 0-.46.18-.49.42l-.38 2.65c-.61.25-1.17.59-1.69.98l-2.49-1c-.23-.09-.49 0-.61.22l-2 3.46c-.13.22-.07.49.12.64l2.11 1.65c-.04.32-.07.65-.07.98s.03.66.07.98l-2.11 1.65c-.19.15-.24.42-.12.64l2 3.46c.12.22.39.3.61.22l2.49-1c.52.4 1.08.73 1.69.98l.38 2.65c.03.24.24.42.49.42h4c.25 0 .46-.18.49-.42l.38-2.65c.61-.25 1.17-.59 1.69-.98l2.49 1c.23.09.49 0 .61-.22l2-3.46c.12-.22.07-.49-.12-.64l-2.11-1.65zM12 15.5c-1.93 0-3.5-1.57-3.5-3.5s1.57-3.5 3.5-3.5 3.5 1.57 3.5 3.5-1.57 3.5-3.5 3.5z"/>
            </svg>
            <h1 style="margin:0; padding:0; font-size:30px; font-weight:800; color:#140A9A;">FLEET OPERATIONS CENTER</h1>
        </div>
    """, unsafe_allow_html=True)
    st.caption(f"System Date: {datetime.date.today()} | Database Status: Connected | 🔐 Session Status: Administrative Mode Enabled")

else:
    # Guest Mode: The Title is still blue, but the gear icon drops down to flat muted gray
    st.markdown("""
        <div class="header-wrapper">
            <svg class="icon-guest" width="34" height="34" viewBox="0 0 24 24" xmlns="http://w3.org">
                <path d="M19.43 12.98c.04-.32.07-.64.07-.98s-.03-.66-.07-.98l2.11-1.65c.19-.15.24-.42.12-.64l-2-3.46c-.12-.22-.39-.3-.61-.22l-2.49 1c-.52-.4-1.08-.73-1.69-.98l-.38-2.65C14.46 2.18 14.25 2 14 2h-4c-.25 0-.46.18-.49.42l-.38 2.65c-.61.25-1.17.59-1.69.98l-2.49-1c-.23-.09-.49 0-.61.22l-2 3.46c-.13.22-.07.49.12.64l2.11 1.65c-.04.32-.07.65-.07.98s.03.66.07.98l-2.11 1.65c-.19.15-.24.42-.12.64l2 3.46c.12.22.39.3.61.22l2.49-1c.52.4 1.08.73 1.69.98l.38 2.65c.03.24.24.42.49.42h4c.25 0 .46-.18.49-.42l.38-2.65c.61-.25 1.17-.59 1.69-.98l2.49 1c.23.09.49 0 .61-.22l2-3.46c.12-.22.07-.49-.12-.64l-2.11-1.65zM12 15.5c-1.93 0-3.5-1.57-3.5-3.5s1.57-3.5 3.5-3.5 3.5 1.57 3.5 3.5-1.57 3.5-3.5 3.5z"/>
            </svg>
            <h1 style="margin:0; padding:0; font-size:30px; font-weight:800; color:#140A9A;">FLEET OPERATIONS CENTER</h1>
        </div>
    """, unsafe_allow_html=True)
    st.caption(f"System Date: {datetime.date.today()} | Database Status: Connected")


# Permanent layout tabs structure
tab_titles = ["Dashboard", "Equipment", "Mechanics", "Logs", "Notes", "Spareparts", "Tools"]
tab_ctrl, tab_eq, tab_mech, tab_logs, tab_notes, tab_spare, tab_tools = st.tabs(tab_titles)


# ==========================================
# TAB 0: DASHBOARD / ADMIN CONTROL
# ==========================================
with tab_ctrl:
    dash_col1, dash_col2, dash_col3 = st.columns([3.5, 4.7, 1.8])
    
    with dash_col1:
        st.subheader("Operations Command Deck")
        
    with dash_col3:
        st.write("") 
        if st.session_state.role == "admin":
            if st.button("Log Out", type="primary", use_container_width=True):
                st.session_state.role = "guest"
                st.rerun()
        else:
            password = st.text_input(
                "admin", 
                type="password", 
                placeholder="admin ",
                label_visibility="collapsed"
            )
            if password:
                if password.strip() == st.secrets["credentials"]["admin_password"]:
                    st.session_state.role = "admin"
                    st.rerun()
                else:
                    st.error("Invalid passkey")

    st.markdown("### Daily System Overview")
    st.write("Welcome to the main station log panel. Use the tab options above to route across asset divisions.")


# ==========================================
# TAB 1: EQUIPMENT REGISTRY
# ==========================================
with tab_eq:
    st.subheader("Equipment Registry")
    
    # Dynamic view: Admin can alter inventory parameters directly
    if st.session_state.role == "admin":
        st.info("Write-access mode enabled for equipment entries.")
        with st.container(border=True):
            st.markdown("**Add Heavy Machine Unit to Registry**")
            c1, c2, c3 = st.columns(3)
            with c1: eq_name = st.text_input("Machine Model Code")
            with c2: eq_hours = st.number_input("Starting Motohours", min_value=0.0, step=1.0)
            with c3: eq_loc = st.selectbox("Site Assignment Location", ["North Quarry", "South Garage", "Main Yard"])
            
            if st.button("Register Hardware", type="primary"):
                if eq_name:
                    try:
                        run_query("INSERT INTO equipment (name, status, motohours, location) VALUES (?, 'Operational', ?, ?)", 
                                  (eq_name, eq_hours, eq_loc))
                        st.success(f"Unit {eq_name} appended to operational fleet.")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Error: A machine with that name profile already exists.")
    else:
        st.caption("Read-only guest view mode active.")
        
    # Shared Asset Tracker Dataframe view
    import pandas as pd
    conn = sqlite3.connect(DB_FILE)
    df_eq = pd.read_sql_query("SELECT id AS 'ID', name AS 'Unit Name', status AS 'Status', motohours AS 'Current Motohours', location AS 'Assignment' FROM equipment", conn)
    conn.close()
    st.dataframe(df_eq, use_container_width=True, hide_index=True)


# ==========================================
# TAB 2: MECHANICS ASSIGNMENTS
# ==========================================
with tab_mech:
    st.subheader("Mechanics Assignments")
    st.write("Duty rosters and tech shift allocations go here.")


# ==========================================
# TAB 3: OPERATION LOGS (Motohours Increments)
# ==========================================
with tab_logs:
    st.subheader("Operation Logs")
    
    # Gather live machines to load select boxes
    raw_machines = run_query("SELECT name FROM equipment")
    machine_names = [m[0] for m in raw_machines]
    
    if st.session_state.role == "admin" and machine_names:
        with st.form("hours_form", clear_on_submit=True):
            st.markdown("**Update Running Metrics**")
            target_unit = st.selectbox("Target Equipment Profile", machine_names)
            added_runtime = st.number_input("Add Shift Motohours Run Today", min_value=0.1, max_value=24.0, step=0.5)
            
            if st.form_submit_button("Commit Runtime Logs"):
                run_query("UPDATE equipment SET motohours = motohours + ? WHERE name = ?", (added_runtime, target_unit))
                st.success(f"Log stored: Updated +{added_runtime} runtime hours for {target_unit}.")
                st.rerun()
    elif not machine_names:
        st.warning("No equipment registered in system inventory data files yet.")
    else:
        st.info("Log tracking metrics write-forms are locked. Log in via Dashboard tab to make entries.")


# ==========================================
# TAB 4: SHIFT HANDOVER NOTES (Day / Night Shift Logic)
# ==========================================
with tab_notes:
    st.subheader("Shift Notes & Handover Instructions")
    
    if st.session_state.role == "admin":
        with st.form("note_form", clear_on_submit=True):
            st.markdown("**Write Shift Handover Entry**")
            # Addressing daypart day/night logic natively in user forms
            selected_shift = st.selectbox("Current Daypart Cycle", ["Day", "Night"])
            handover_text = st.text_area("Write operational notes / instructions here...")
            
            if st.form_submit_button("Publish Instruction Logs"):
                if handover_text.strip():
                    run_query("INSERT INTO notes (daypart, author, content) VALUES (?, 'Admin Mechanic', ?)", 
                              (selected_shift, handover_text))
                    st.success("Log record saved safely to historical system database.")
                    st.rerun()
    
    # Display the historical archive feed globally to everyone
    st.markdown("---")
    st.markdown("##### Historical Handover Archive Log Feed")
    conn = sqlite3.connect(DB_FILE)
    df_notes = pd.read_sql_query("SELECT timestamp AS 'Logged Time', daypart AS 'Shift Daypart', content AS 'Instruction Entry' FROM notes ORDER BY id DESC", conn)
    conn.close()
    st.table(df_notes)


# ==========================================
# TAB 5: SPARE PARTS
# ==========================================
with tab_spare:
    st.subheader("Spare Parts Database")
