import unittest
import sqlite3
from app import DBManager

class TestEventManagement(unittest.TestCase):
    def setUp(self):
        # Hər test üçün izolyasiya olunmuş yaddaş bazası yaradırıq (in-memory)
        self.db = DBManager(db_name=":memory:")
        self.db.execute_query("INSERT INTO categories (name) VALUES ('Test Kateqoriya')")
        
    def test_01_yeni_tedbir_yaradilmasi(self):
        # Ssenari 1: Uğurlu tədbir yaradılması
        self.db.execute_query("""
            INSERT INTO events (title, event_date, event_time, location, max_participants, category_id)
            VALUES ('Python Təlimi', '2026-12-01', '14:00', 'Otaq 101', 50, 1)
        """)
        result = self.db.execute_query("SELECT title FROM events WHERE title='Python Təlimi'").fetchone()
        self.assertIsNotNone(result)

    def test_02_istifadeci_qeydiyyati_ugurlu(self):
        # Ssenari 2: İstifadəçinin tədbirə uğurlu qeydiyyatı
        self.db.execute_query("INSERT INTO users (fullname, email) VALUES ('Əli Əliyev', 'ali@test.com')")
        self.db.execute_query("INSERT INTO events (title, event_date, event_time, location, max_participants, category_id) VALUES ('Test Tədbir', '2026-12-01', '14:00', 'Otaq', 5, 1)")
        self.db.execute_query("INSERT INTO registrations (user_id, event_id) VALUES (1, 1)")
        count = self.db.execute_query("SELECT COUNT(*) FROM registrations").fetchone()[0]
        self.assertEqual(count, 1)

    def test_03_tekrar_qeydiyyat_xetasi(self):
        # Ssenari 3: Eyni tədbirə ikinci dəfə yazılmağın bloklanması (UNIQUE constraint)
        self.db.execute_query("INSERT INTO users (fullname, email) VALUES ('Vəli Vəliyev', 'vali@test.com')")
        self.db.execute_query("INSERT INTO events (title, event_date, event_time, location, max_participants, category_id) VALUES ('Test 2', '2026-12-01', '14:00', 'Otaq', 5, 1)")
        self.db.execute_query("INSERT INTO registrations (user_id, event_id) VALUES (1, 1)")
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute_query("INSERT INTO registrations (user_id, event_id) VALUES (1, 1)")

    def test_04_limitin_oxunmasi_ve_yoxlanilmasi(self):
        # Ssenari 4: Limit yoxlaması məntiqinin testi
        self.db.execute_query("INSERT INTO events (title, event_date, event_time, location, max_participants, category_id) VALUES ('Kiçik Təlim', '2026-12-01', '14:00', 'Otaq', 1, 1)")
        self.db.execute_query("INSERT INTO users (fullname, email) VALUES ('User 1', 'u1@test.com')")
        self.db.execute_query("INSERT INTO registrations (user_id, event_id) VALUES (1, 1)")
        
        current_regs = self.db.execute_query("SELECT COUNT(*) FROM registrations WHERE event_id = 1").fetchone()[0]
        max_limit = self.db.execute_query("SELECT max_participants FROM events WHERE id = 1").fetchone()[0]
        self.assertEqual(current_regs, max_limit) # Limit dolub yoxlaması (Backend-də bura qədər icazə verilir)
        
    def test_05_qeydiyyatin_legvi(self):
        # Ssenari 5: İstifadəçi qeydiyyatı ləğv etdikdə silinməsi
        self.db.execute_query("INSERT INTO users (fullname, email) VALUES ('User 2', 'u2@test.com')")
        self.db.execute_query("INSERT INTO events (title, event_date, event_time, location, max_participants, category_id) VALUES ('Silinəcək Tədbir', '2026-12-01', '14:00', 'Otaq', 10, 1)")
        self.db.execute_query("INSERT INTO registrations (user_id, event_id) VALUES (1, 1)")
        self.db.execute_query("DELETE FROM registrations WHERE user_id = 1 AND event_id = 1")
        
        count = self.db.execute_query("SELECT COUNT(*) FROM registrations").fetchone()[0]
        self.assertEqual(count, 0)

if __name__ == '__main__':
    unittest.main()