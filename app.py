import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date

# --- OOP və Verilənlər Bazası İdarəetməsi (Backend) ---
class DBManager:
    def __init__(self, db_name="university_events.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        
        # İstifadəçilər
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fullname TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL
            )
        """)
        
        # Kateqoriyalar
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
        """)
        
        # Tədbirlər
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                category_id INTEGER,
                event_date DATE NOT NULL,
                event_time TIME NOT NULL,
                location TEXT NOT NULL,
                max_participants INTEGER NOT NULL,
                FOREIGN KEY(category_id) REFERENCES categories(id)
            )
        """)
        
        # Qeydiyyatlar
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS registrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                event_id INTEGER,
                registration_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(event_id) REFERENCES events(id),
                UNIQUE(user_id, event_id)
            )
        """)
        
        # İlkin kateqoriyaları əlavə etmək
        cursor.execute("INSERT OR IGNORE INTO categories (name) VALUES ('Elmi Konfrans'), ('Seminar'), ('Təlim'), ('Müsabiqə')")
        self.conn.commit()

    def execute_query(self, query, params=()):
        cursor = self.conn.cursor()
        try:
            cursor.execute(query, params)
            self.conn.commit()
            return cursor
        except sqlite3.IntegrityError as e:
            raise e

    def fetch_data(self, query, params=()):
        return pd.read_sql_query(query, self.conn, params=params)

db = DBManager()

# --- Frontend və Biznes Məntiqi (Streamlit) ---
st.set_page_config(page_title="Universitet Tədbirlər Sistemi", layout="wide")

st.sidebar.title("📌 Menyu")
menu = st.sidebar.radio("Keçid edin:", ["İdarəetmə Paneli", "Tədbirlər (Axtarış)", "Yeni Tədbir Yarat", "Qeydiyyat & Ləğv"])

if menu == "İdarəetmə Paneli":
    st.title("📊 İdarəetmə Paneli və Statistika")
    
    col1, col2, col3 = st.columns(3)
    total_events = db.execute_query("SELECT COUNT(*) FROM events").fetchone()[0]
    total_regs = db.execute_query("SELECT COUNT(*) FROM registrations").fetchone()[0]
    
    col1.metric("Ümumi Tədbirlər", total_events)
    col2.metric("Ümumi Qeydiyyatlar", total_regs)
    
    st.subheader("Fərdi Əlavə Tapşırıq: Kateqoriyalar üzrə Tədbir Statistikası (Qrafik)")
    cat_stats = db.fetch_data("""
        SELECT c.name as Kateqoriya, COUNT(e.id) as Say
        FROM categories c
        LEFT JOIN events e ON c.id = e.category_id
        GROUP BY c.id
    """)
    st.bar_chart(cat_stats.set_index("Kateqoriya"))

    st.subheader("Tədbir İştirakçılarını Fayla İxrac Et (CSV)")
    events_df = db.fetch_data("SELECT id, title FROM events")
    if not events_df.empty:
        selected_event_export = st.selectbox("Tədbiri seçin", events_df['title'])
        if st.button("İştirakçı Siyahısını Yüklə"):
            ev_id = events_df[events_df['title'] == selected_event_export]['id'].values[0]
            participants = db.fetch_data("""
                SELECT u.fullname, u.email, r.registration_date 
                FROM registrations r 
                JOIN users u ON r.user_id = u.id 
                WHERE r.event_id = ?
            """, (ev_id,))
            
            csv = participants.to_csv(index=False)
            st.download_button(label="CSV kimi yüklə", data=csv, file_name=f"{selected_event_export}_istirakcilar.csv", mime="text/csv")

elif menu == "Tədbirlər (Axtarış)":
    st.title("🔍 Tədbirlərin Siyahısı və Axtarış")
    
    col1, col2, col3 = st.columns(3)
    search_title = col1.text_input("Tədbirin adı")
    
    categories = db.fetch_data("SELECT name FROM categories")
    cat_list = ["Bütün"] + categories['name'].tolist()
    search_cat = col2.selectbox("Kateqoriya", cat_list)
    
    status = col3.selectbox("Zaman", ["Bütün", "Gələcək tədbirlər", "Keçmiş tədbirlər"])
    
    query = """
        SELECT e.id, e.title as 'Ad', c.name as 'Kateqoriya', e.event_date as 'Tarix', 
               e.location as 'Məkan', e.max_participants as 'Limit',
               (SELECT COUNT(*) FROM registrations WHERE event_id = e.id) as 'Qeydiyyatdan keçən'
        FROM events e
        JOIN categories c ON e.category_id = c.id
        WHERE 1=1
    """
    params = []
    
    if search_title:
        query += " AND e.title LIKE ?"
        params.append(f"%{search_title}%")
    if search_cat != "Bütün":
        query += " AND c.name = ?"
        params.append(search_cat)
        
    current_date = date.today().isoformat()
    if status == "Gələcək tədbirlər":
        query += " AND e.event_date >= ?"
        params.append(current_date)
    elif status == "Keçmiş tədbirlər":
        query += " AND e.event_date < ?"
        params.append(current_date)
        
    df = db.fetch_data(query, params)
    
    if df.empty:
        st.warning("Axtarışınıza uyğun tədbir tapılmadı.")
    else:
        st.dataframe(df, use_container_width=True)

elif menu == "Yeni Tədbir Yarat":
    st.title("➕ Yeni Tədbir Yarat")
    
    with st.form("event_form"):
        title = st.text_input("Tədbirin Adı*")
        desc = st.text_area("Təsviri")
        
        cats = db.fetch_data("SELECT id, name FROM categories")
        cat_dict = dict(zip(cats['name'], cats['id']))
        category = st.selectbox("Kateqoriya*", list(cat_dict.keys()))
        
        col1, col2 = st.columns(2)
        ev_date = col1.date_input("Tarix*")
        ev_time = col2.time_input("Saat*")
        
        location = st.text_input("Keçirilmə yeri*")
        max_limit = st.number_input("Maksimum iştirakçı sayı*", min_value=1, value=50)
        
        submitted = st.form_submit_button("Tədbiri Yarat")
        
        if submitted:
            if not title or not location:
                st.error("Məcburi sahələri doldurun!")
            elif ev_date < date.today():
                st.error("Tədbirin tarixi keçmiş ola bilməz!")
            else:
                db.execute_query("""
                    INSERT INTO events (title, description, category_id, event_date, event_time, location, max_participants)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (title, desc, cat_dict[category], ev_date, ev_time.strftime("%H:%M"), location, max_limit))
                st.success("Tədbir uğurla yaradıldı!")

elif menu == "Qeydiyyat & Ləğv":
    st.title("✅ İştirakçı Qeydiyyatı")
    
    action = st.radio("Əməliyyat növü", ["Qeydiyyatdan keç", "Qeydiyyatı ləğv et"])
    events = db.fetch_data("SELECT id, title, max_participants FROM events WHERE event_date >= ?", (date.today().isoformat(),))
    
    if events.empty:
        st.info("Aktiv tədbir yoxdur.")
    else:
        ev_dict = dict(zip(events['title'], events['id']))
        selected_event = st.selectbox("Tədbiri seçin", list(ev_dict.keys()))
        event_id = ev_dict[selected_event]
        
        with st.form("reg_form"):
            fullname = st.text_input("Ad və Soyad*")
            email = st.text_input("E-poçt ünvanı*")
            submit = st.form_submit_button(action)
            
            if submit:
                if not fullname or not email:
                    st.error("Məlumatları tam daxil edin.")
                else:
                    # İstifadəçini yoxla və ya yarat
                    try:
                        db.execute_query("INSERT INTO users (fullname, email) VALUES (?, ?)", (fullname, email))
                    except sqlite3.IntegrityError:
                        pass # İstifadəçi artıq var
                    
                    user_id = db.execute_query("SELECT id FROM users WHERE email = ?", (email,)).fetchone()[0]
                    
                    if action == "Qeydiyyatdan keç":
                        current_regs = db.execute_query("SELECT COUNT(*) FROM registrations WHERE event_id = ?", (event_id,)).fetchone()[0]
                        max_limit = events[events['id'] == event_id]['max_participants'].values[0]
                        
                        if current_regs >= max_limit:
                            st.error("Bu tədbir üçün limit dolub!")
                        else:
                            try:
                                db.execute_query("INSERT INTO registrations (user_id, event_id) VALUES (?, ?)", (user_id, event_id))
                                st.success("Qeydiyyat uğurla tamamlandı!")
                            except sqlite3.IntegrityError:
                                st.error("Siz artıq bu tədbirə qeydiyyatdan keçmisiniz!")
                    
                    elif action == "Qeydiyyatı ləğv et":
                        cursor = db.execute_query("DELETE FROM registrations WHERE user_id = ? AND event_id = ?", (user_id, event_id))
                        if cursor.rowcount > 0:
                            st.success("Qeydiyyatınız ləğv edildi.")
                        else:
                            st.warning("Bu tədbir üçün qeydiyyatınız tapılmadı.")