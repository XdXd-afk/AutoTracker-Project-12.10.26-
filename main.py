import sys
import os
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QDialog, QVBoxLayout, QHBoxLayout, 
    QTableWidget, QTableWidgetItem, QPushButton, QLabel, QLineEdit, 
    QTextEdit, QComboBox, QDateEdit, QDoubleSpinBox, QSpinBox, 
    QMessageBox, QFileDialog, QHeaderView
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QPixmap, QKeySequence, QShortcut

# Импортируем наш модуль базы данных
from database import Database


class AddRecordDialog(QDialog):
    """Вторая форма: Окно добавления новой записи в журнал ТО."""
    def __init__(self, db_instance, parent=None):
        super().__init__(parent)
        self.db = db_instance
        self.image_path = ""
        
        self.setWindowTitle("Добавить запись обслуживания")
        self.setFixedSize(450, 500)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()

        # Выбор даты
        layout.addWidget(QLabel("Дата проведения работ:"))
        self.date_edit = QDateEdit()
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        layout.addWidget(self.date_edit)

        # Выбор типа работ (связь с таблицей service_types)
        layout.addWidget(QLabel("Тип обслуживания:"))
        self.combo_type = QComboBox()
        self.load_service_types()
        layout.addWidget(self.combo_type)

        # Пробег (км)
        layout.addWidget(QLabel("Пробег автомобиля (км):"))
        self.spin_mileage = QSpinBox()
        self.spin_mileage.setMaximum(2000000)
        self.spin_mileage.setSingleStep(1000)
        self.spin_mileage.setValue(50000)
        layout.addWidget(self.spin_mileage)

        # Стоимость (руб)
        layout.addWidget(QLabel("Стоимость (руб.):"))
        self.spin_cost = QDoubleSpinBox()
        self.spin_cost.setMaximum(1000000.0)
        self.spin_cost.setValue(1000.0)
        layout.addWidget(self.spin_cost)

        # Комментарий
        layout.addWidget(QLabel("Комментарий / Заметки:"))
        self.input_comment = QTextEdit()
        self.input_comment.setMaximumHeight(80)
        layout.addWidget(self.input_comment)

        # Выбор файла (картинки чека / запчасти)
        file_layout = QHBoxLayout()
        self.lbl_file = QLabel("Файл не выбран")
        btn_choose = QPushButton("Выбрать чек/фото")
        btn_choose.clicked.connect(self.choose_file)
        file_layout.addWidget(self.lbl_file)
        file_layout.addWidget(btn_choose)
        layout.addLayout(file_layout)

        # Кнопка сохранения
        btn_save = QPushButton("Сохранить запись")
        btn_save.clicked.connect(self.save_record)
        btn_save.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 8px;")
        layout.addWidget(btn_save)

        self.setLayout(layout)

    def load_service_types(self):
        types = self.db.get_service_types()
        for t_id, name in types:
            self.combo_type.addItem(name, userData=t_id)

    def choose_file(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Выберите фото или чек", "", "Картинки (*.png *.jpg *.jpeg)"
        )
        if file_name:
            self.image_path = file_name
            self.lbl_file.setText(os.path.basename(file_name))

    def save_record(self):
        date = self.date_edit.date().toString("yyyy-MM-dd")
        type_id = self.combo_type.currentData()
        mileage = self.spin_mileage.value()
        cost = self.spin_cost.value()
        comment = self.input_comment.toPlainText()

        if mileage <= 0 or cost < 0:
            QMessageBox.warning(self, "Ошибка", "Проверьте правильность введенных чисел!")
            return

        self.db.add_record(type_id, date, mileage, cost, comment, self.image_path)
        QMessageBox.information(self, "Успех", "Запись успешно добавлена!")
        self.accept()


class MainWindow(QMainWindow):
    """Главная форма приложения: Список ТО, поиск, фильтры, сортировка, статистика."""
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.current_sort_column = 2  # По умолчанию сортировка по дате
        self.sort_order = Qt.DescendingOrder

        self.setWindowTitle("Учёт обслуживания автомобиля (Бортовой журнал)")
        self.resize(1000, 700)
        self.init_ui()
        self.load_data()

    def init_ui(self):
        central_widget = QLabel() 
        main_layout = QHBoxLayout()

        # Левая колонка: Панель фильтрации, Таблица и кнопки управления
        left_layout = QVBoxLayout()

        # 1. Панель поиска, фильтрации и кнопки сброса
        search_layout = QHBoxLayout()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Поиск по комментарию...")
        self.search_input.textChanged.connect(self.load_data)
        
        self.combo_filter_type = QComboBox()
        self.combo_filter_type.addItem("Все категории", userData=0)
        self.load_filter_service_types()
        self.combo_filter_type.currentIndexChanged.connect(self.load_data)

        # Кнопка сброса сортировки
        btn_reset_sort = QPushButton("🔄 Сбросить сортировку")
        btn_reset_sort.clicked.connect(self.reset_sorting)

        search_layout.addWidget(QLabel("Поиск:"))
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(QLabel("Категория:"))
        search_layout.addWidget(self.combo_filter_type)
        search_layout.addWidget(btn_reset_sort)
        
        left_layout.addLayout(search_layout)

        # 2. Виджет таблицы (QTableWidget)
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "ID", "Тип работ", "Дата", "Пробег (км)", "Стоимость", "Комментарий", "Чек"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        
        # Интерактивная сортировка при клике на заголовки столбцов
        self.table.horizontalHeader().sectionClicked.connect(self.on_header_clicked)

        # Умный двойной клик по конкретной ячейке
        self.table.cellDoubleClicked.connect(self.on_cell_double_clicked)
        left_layout.addWidget(self.table)

        # 3. Панель управляющих кнопок
        btn_layout = QHBoxLayout()
        btn_add = QPushButton("Добавить запись")
        btn_add.clicked.connect(self.open_add_dialog)
        
        btn_delete = QPushButton("Удалить выбранное")
        btn_delete.clicked.connect(self.delete_selected_record)
        btn_delete.setStyleSheet("background-color: #f44336; color: white;")

        btn_refresh = QPushButton("Обновить")
        btn_refresh.clicked.connect(self.load_data)

        btn_layout.addWidget(btn_add)
        btn_layout.addWidget(btn_delete)
        btn_layout.addWidget(btn_refresh)
        left_layout.addLayout(btn_layout)

        main_layout.addLayout(left_layout, stretch=3)

        # Правая колонка: Картинка авто и общая статистика
        right_layout = QVBoxLayout()

        self.lbl_car_image = QLabel()
        self.lbl_car_image.setAlignment(Qt.AlignCenter)
        self.lbl_car_image.setMaximumSize(250, 200)
        self.lbl_car_image.setStyleSheet("border: 1px solid #ccc; background-color: #f9f9f9;")
        self.load_car_image("assets/car_logo.png")
        right_layout.addWidget(self.lbl_car_image)

        self.lbl_stats = QLabel("Статистика загружается...")
        self.lbl_stats.setStyleSheet("font-size: 14px; font-weight: bold; margin-top: 20px;")
        right_layout.addWidget(self.lbl_stats)

        right_layout.addStretch()
        main_layout.addLayout(right_layout, stretch=1)

        self.setCentralWidget(central_widget)
        central_widget.setLayout(main_layout)

        # Горячие клавиши
        self.shortcut_delete = QShortcut(QKeySequence(Qt.Key_Delete), self)
        self.shortcut_delete.activated.connect(self.delete_selected_record)
        self.shortcut_add = QShortcut(QKeySequence("Ctrl+N"), self)
        self.shortcut_add.activated.connect(self.open_add_dialog)

    def reset_sorting(self):
        """Сброс сортировки и фильтров в исходное состояние (по дате убывания)."""
        self.current_sort_column = 2  # Возвращаем колонку "Дата" по умолчанию
        self.sort_order = Qt.DescendingOrder
        self.search_input.clear()
        self.combo_filter_type.setCurrentIndex(0)
        self.load_data()


        # Умный двойной клик по конкретной ячейке
        self.table.cellDoubleClicked.connect(self.on_cell_double_clicked)
        left_layout.addWidget(self.table)

        # 3. Панель управляющих кнопок
        btn_layout = QHBoxLayout()
        btn_add = QPushButton("Добавить запись")
        btn_add.clicked.connect(self.open_add_dialog)
        
        btn_delete = QPushButton("Удалить выбранное")
        btn_delete.clicked.connect(self.delete_selected_record)
        btn_delete.setStyleSheet("background-color: #f44336; color: white;")

        btn_refresh = QPushButton("Обновить")
        btn_refresh.clicked.connect(self.load_data)

        btn_layout.addWidget(btn_add)
        btn_layout.addWidget(btn_delete)
        btn_layout.addWidget(btn_refresh)
        left_layout.addLayout(btn_layout)

        main_layout.addLayout(left_layout, stretch=3)

        # Правая колонка: Картинка авто и общая статистика
        right_layout = QVBoxLayout()

        self.lbl_car_image = QLabel()
        self.lbl_car_image.setAlignment(Qt.AlignCenter)
        self.lbl_car_image.setMaximumSize(250, 200)
        self.lbl_car_image.setStyleSheet("border: 1px solid #ccc; background-color: #f9f9f9;")
        self.load_car_image("assets/car_logo.png")
        right_layout.addWidget(self.lbl_car_image)

        self.lbl_stats = QLabel("Статистика загружается...")
        self.lbl_stats.setStyleSheet("font-size: 14px; font-weight: bold; margin-top: 20px;")
        right_layout.addWidget(self.lbl_stats)

        right_layout.addStretch()
        main_layout.addLayout(right_layout, stretch=1)

        self.setCentralWidget(central_widget)
        central_widget.setLayout(main_layout)

        # Горячие клавиши
        self.shortcut_delete = QShortcut(QKeySequence(Qt.Key_Delete), self)
        self.shortcut_delete.activated.connect(self.delete_selected_record)
        self.shortcut_add = QShortcut(QKeySequence("Ctrl+N"), self)
        self.shortcut_add.activated.connect(self.open_add_dialog)

    def load_filter_service_types(self):
        """Заполнение выпадающего списка категорий для фильтрации."""
        types = self.db.get_service_types()
        for t_id, name in types:
            self.combo_filter_type.addItem(name, userData=t_id)

    def load_car_image(self, path):
        if hasattr(sys, '_MEIPASS'):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.abspath(".")
            
        for ext in [".png", ".jpg", ".jpeg"]:
            full_path = os.path.join(base_path, "assets", f"car_logo{ext}")
            if os.path.exists(full_path):
                pixmap = QPixmap(full_path)
                self.lbl_car_image.setPixmap(pixmap.scaled(240, 190, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                return

        self.lbl_car_image.setText("Нет картинки авто\n(положите car_logo.png\nв папку assets)")

    def load_data(self):
        """Загрузка данных из БД с учетом текстового поиска, фильтра категорий и сортировки."""
        search_query = self.search_input.text() if hasattr(self, 'search_input') else ""
        category_id = self.combo_filter_type.currentData() if hasattr(self, 'combo_filter_type') else 0
        
        records = self.db.get_filtered_records(search_query, category_id, self.current_sort_column, self.sort_order)
        
        self.table.setRowCount(len(records))
        total_cost = 0.0
        max_mileage = 0

        for row_idx, row_data in enumerate(records):
            for col_idx, value in enumerate(row_data):
                item = QTableWidgetItem(str(value if value is not None else ""))
                self.table.setItem(row_idx, col_idx, item)
            
            if row_data[4]: 
                total_cost += float(row_data[4])
            if row_data[3] and row_data[3] > max_mileage:
                max_mileage = row_data[3]

        self.lbl_stats.setText(
            f"📊 Общая статистика:\n\n"
            f"• Всего записей: {len(records)}\n"
            f"• Суммарные затраты:\n  {total_cost:,.2f} руб.\n"
            f"• Текущий пробег:\n  {max_mileage:,} км"
        )

    def on_header_clicked(self, logical_index):
        """Обработка клика по заголовку таблицы для сортировки."""
        if self.current_sort_column == logical_index:
            self.sort_order = Qt.AscendingOrder if self.sort_order == Qt.DescendingOrder else Qt.DescendingOrder
        else:
            self.current_sort_column = logical_index
            self.sort_order = Qt.DescendingOrder
        self.load_data()

    def on_cell_double_clicked(self, row, column):
        """Умный двойной клик по конкретной ячейке таблицы."""
        record_id = self.table.item(row, 0).text()
        work_type = self.table.item(row, 1).text()
        date = self.table.item(row, 2).text()
        mileage = self.table.item(row, 3).text()
        cost = self.table.item(row, 4).text()
        comment = self.table.item(row, 5).text()
        image_path = self.table.item(row, 6).text()

        if column == 3:  # Клик по пробегу
            QMessageBox.information(self, "Информация о пробеге", 
                f"🚗 Зафиксированный пробег:\n{mileage} км\nДата: {date}")
        elif column == 4:  # Клик по стоимости
            QMessageBox.information(self, "Информация о затратах", 
                f"💰 Стоимость услуги «{work_type}»:\n{cost} руб.")
        elif column == 5:  # Клик по комментарию
            QMessageBox.information(self, "Комментарий к записи", 
                f"📝 Заметка:\n{comment if comment else 'Комментарий отсутствует'}")
        else:
            info_text = f"📋 Запись №{record_id}\nТип: {work_type}\nДата: {date}\nПробег: {mileage} км\nСтоимость: {cost} руб."
            if comment:
                info_text += f"\nКомментарий: {comment}"
            if image_path and os.path.exists(image_path):
                info_text += f"\n\nПрикрепленный файл чека:\n{image_path}"
            QMessageBox.information(self, "Детали записи", info_text)

    def open_add_dialog(self):
        dialog = AddRecordDialog(self.db, self)
        if dialog.exec() == QDialog.Accepted:
            self.load_data()

    def delete_selected_record(self):
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Внимание", "Выберите строку в таблице для удаления!")
            return

        reply = QMessageBox.question(
            self, "Подтверждение", "Вы действительно хотите удалить выбранную запись?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            row = selected_rows[0].row()
            record_id = int(self.table.item(row, 0).text())
            self.db.delete_record(record_id)
            self.load_data()

    def closeEvent(self, event):
        self.db.close()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())