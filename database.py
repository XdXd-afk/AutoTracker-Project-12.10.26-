import sqlite3


class Database:
    """Класс для управления базой данных учета обслуживания автомобиля."""

    def __init__(self, db_name="auto_tracker.db"):
        self.db_name = db_name
        self.conn = None
        self.cursor = None
        self.connect()
        self.create_tables()

    def connect(self):
        """Установка соединения с базой данных SQLite."""
        self.conn = sqlite3.connect(self.db_name)
        self.cursor = self.conn.cursor()

    def create_tables(self):
        """Создание таблиц, если они еще не существуют."""
        # Таблица №1: Справочник видов работ
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS service_types (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL
            )
        """)

        # Таблица №2: Журнал записей обслуживания (связана с service_types)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS maintenance_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type_id INTEGER,
                date TEXT NOT NULL,
                mileage INTEGER NOT NULL,
                cost REAL NOT NULL,
                comment TEXT,
                image_path TEXT,
                FOREIGN KEY (type_id) REFERENCES service_types (id) 
                ON DELETE CASCADE
            )
        """)
        self.conn.commit()

        # Заполняем справочник работ по умолчанию, если он пуст
        self.cursor.execute("SELECT COUNT(*) FROM service_types")
        if self.cursor.fetchone()[0] == 0:
            default_types = [
                ("Замена масла и фильтров",),
                ("Ремонт ходовой части",),
                ("Замена тормозных колодок",),
                ("Шиномонтаж",),
                ("Покупка запчастей / расходников",),
            ]
            self.cursor.executemany(
                "INSERT INTO service_types (name) VALUES (?)", default_types
            )
            self.conn.commit()

    def get_all_records(self):
        """Получение всех записей из журнала вместе с названиями типов работ."""
        self.cursor.execute("""
            SELECT r.id, st.name, r.date, r.mileage, r.cost, r.comment, r.image_path
            FROM maintenance_records r
            JOIN service_types st ON r.type_id = st.id
            ORDER BY r.date DESC
        """)
        return self.cursor.fetchall()

    def get_service_types(self):
        """Получение списка всех видов работ для заполнения ComboBox."""
        self.cursor.execute("SELECT id, name FROM service_types")
        return self.cursor.fetchall()

    def add_record(
        self, type_id, date, mileage, cost, comment, image_path=""
    ):
        """Добавление новой записи в журнал."""
        self.cursor.execute(
            """
            INSERT INTO maintenance_records (type_id, date, mileage, cost, comment, image_path)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (type_id, date, mileage, cost, comment, image_path),
        )
        self.conn.commit()

    def delete_record(self, record_id):
        """Удаление записи по ее ID."""
        self.cursor.execute(
            "DELETE FROM maintenance_records WHERE id = ?", (record_id,)
        )
        self.conn.commit()

    def close(self):
        """Закрытие соединения с базой данных."""
        if self.conn:
            self.conn.close()

    def get_filtered_records(self, search_query="", category_id=0, sort_column=2, sort_order=0):
        """Получение записей с учетом поиска, фильтра по категории и сортировки."""
        cursor = self.conn.cursor()
        
        # Связываем индексы колонок таблицы с полями базы данных
        columns_map = {
            0: "r.id",
            1: "st.name",
            2: "r.date",
            3: "r.mileage",
            4: "r.cost",
            5: "r.comment",
            6: "r.image_path"
        }
        order_field = columns_map.get(sort_column, "r.date")
        direction = "DESC" if sort_order != 0 else "ASC"

        # Базовый SQL-запрос с поддержкой текстового поиска
        query = f"""
            SELECT r.id, st.name, r.date, r.mileage, r.cost, r.comment, r.image_path
            FROM maintenance_records r
            JOIN service_types st ON r.type_id = st.id
            WHERE (r.comment LIKE ? OR st.name LIKE ?)
        """
        params = [f"%{search_query}%", f"%{search_query}%"]

        # Дополнительная фильтрация по конкретной категории, если она выбрана
        if category_id and category_id > 0:
            query += " AND r.type_id = ?"
            params.append(category_id)

        query += f" ORDER BY {order_field} {direction}"
        
        cursor.execute(query, params)
        return cursor.fetchall()