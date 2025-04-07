import tkinter as tk
from tkinter import ttk, messagebox
import json
from datetime import datetime
import os
import shutil
import logging
from logging.handlers import RotatingFileHandler
import sys
import traceback

class TodoApp:
    def __init__(self, root):
        try:
            self.root = root
            self.root.title("Список задач")
            
            # Create data directory if it doesn't exist
            self.data_dir = os.path.join(os.path.expanduser("~"), "todo_app_data")
            os.makedirs(self.data_dir, exist_ok=True)
            
            # Setup logging first
            self.setup_logging()
            self.logger.info("Приложение запущено")
            
            # Define file paths
            self.tasks_file = os.path.join(self.data_dir, "tasks.json")
            self.backup_file = os.path.join(self.data_dir, "tasks.json.backup")
            self.logger.debug(f"Пути к файлам: tasks_file={self.tasks_file}, backup_file={self.backup_file}")

            # Initialize window properties
            self.root.geometry("300x400")
            
            # Create and configure style
            self.style = ttk.Style()
            self.style.configure("Custom.TEntry", padding=5)
            self.style.configure("Custom.TButton", padding=5)
            
            # Initialize window state variables
            self.normal_geometry = None
            self.is_expanded = False
            self.is_transparent = False
            self.is_minimized = False
            
            # Create title bar first (before setting overrideredirect)
            self.create_title_bar()
            
            # Now set window properties
            self.root.overrideredirect(True)
            self.root.attributes('-alpha', 0.9)
            self.root.attributes('-topmost', True)
            
            # Load window position
            self.load_window_position()
            
            # Load tasks
            self.tasks = []
            self.load_tasks()
            
            # Create main interface
            self.create_main_interface()
            
            # Refresh task list
            self.refresh_task_list()
            
            # Bind global hotkey for showing window
            self.root.bind_all('<Alt-s>', self.show_window)
            
        except Exception as e:
            self.show_error_and_exit("Ошибка при инициализации приложения", e)

    def create_title_bar(self):
        """Создание заголовка окна"""
        self.title_bar = ttk.Frame(self.root)
        self.title_bar.pack(fill=tk.X, expand=False)
        
        # Кнопка сворачивания
        self.minimize_button = ttk.Button(
            self.title_bar,
            text="−",
            width=3,
            command=self.minimize_window
        )
        self.minimize_button.pack(side=tk.RIGHT)
        
        # Кнопка разворачивания
        self.expand_button = ttk.Button(
            self.title_bar,
            text="□",
            width=3,
            command=self.toggle_expand
        )
        self.expand_button.pack(side=tk.RIGHT)
        
        # Кнопка настройки прозрачности
        self.opacity_button = ttk.Button(
            self.title_bar,
            text="○",
            width=3,
            command=self.toggle_opacity
        )
        self.opacity_button.pack(side=tk.RIGHT)
        
        # Привязываем события перетаскивания
        self.title_bar.bind('<Button-1>', self.start_move)
        self.title_bar.bind('<B1-Motion>', self.do_move)

    def create_main_interface(self):
        """Создание основного интерфейса"""
        # Create main frame
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Task input
        self.task_var = tk.StringVar()
        self.task_entry = ttk.Entry(
            self.main_frame,
            textvariable=self.task_var,
            style="Custom.TEntry",
            width=40
        )
        self.task_entry.pack(side=tk.LEFT, padx=(0, 5), fill=tk.X, expand=True)
        self.task_entry.bind("<Return>", lambda e: self.add_task())

        # Add button
        self.add_button = ttk.Button(
            self.main_frame,
            text="Добавить",
            command=self.add_task,
            style="Custom.TButton"
        )
        self.add_button.pack(side=tk.LEFT)

        # Create task list
        self.task_frame = ttk.Frame(self.root, padding="10")
        self.task_frame.pack(fill=tk.BOTH, expand=True)

        # Create treeview
        self.tree = ttk.Treeview(
            self.task_frame,
            columns=("Status", "Task", "Date"),
            show="headings",
            height=10
        )

        # Configure columns
        self.tree.heading("Status", text="Статус")
        self.tree.heading("Task", text="Задача")
        self.tree.heading("Date", text="Дата")
        
        self.tree.column("Status", width=50, anchor=tk.CENTER)
        self.tree.column("Task", width=400, anchor=tk.W)
        self.tree.column("Date", width=100, anchor=tk.CENTER)

        # Add scrollbar
        scrollbar = ttk.Scrollbar(self.task_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        # Pack tree and scrollbar
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Bind events
        self.tree.bind("<Double-1>", self.toggle_task_status)
        self.tree.bind("<Button-3>", self.show_context_menu)

        # Create context menu
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Редактировать", command=self.edit_task)
        self.context_menu.add_command(label="Удалить", command=self.delete_task)

        # Delete button
        self.delete_button = ttk.Button(
            self.root,
            text="Удалить выбранное",
            command=self.delete_task,
            style="Custom.TButton"
        )
        self.delete_button.pack(pady=10)

    def show_error_and_exit(self, message, error):
        """Показ ошибки и выход из приложения"""
        error_text = f"{message}:\n{str(error)}\n\nПолный текст ошибки:\n{traceback.format_exc()}"
        try:
            if hasattr(self, 'logger'):
                self.logger.error(error_text)
            messagebox.showerror("Критическая ошибка", error_text)
        except:
            print(error_text, file=sys.stderr)
        sys.exit(1)

    def setup_logging(self):
        """Настройка системы логирования"""
        self.logger = logging.getLogger('todo_app')
        self.logger.setLevel(logging.DEBUG)

        # Создаем форматтер для логов
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

        # Настраиваем файловый обработчик с ротацией (максимум 5 файлов по 1MB)
        log_file = os.path.join(self.data_dir, 'todo_app.log')
        file_handler = RotatingFileHandler(log_file, maxBytes=1024*1024, backupCount=5, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

    def add_task(self):
        task_text = self.task_var.get().strip()
        if task_text:
            if len(task_text) > 100:
                self.logger.warning(f"Попытка добавить слишком длинную задачу: {len(task_text)} символов")
                messagebox.showwarning("Предупреждение", "Задача слишком длинная! Максимум 100 символов.")
                return
            current_time = datetime.now().strftime("%Y-%m-%d")
            self.tasks.append({
                "text": task_text,
                "completed": False,
                "date": current_time
            })
            self.task_var.set("")
            self.logger.info(f"Добавлена новая задача: {task_text}")
            self.save_tasks()
            self.refresh_task_list()
        else:
            self.logger.warning("Попытка добавить пустую задачу")
            messagebox.showwarning("Предупреждение", "Задача не может быть пустой!")

    def toggle_task_status(self, event):
        selected_item = self.tree.selection()
        if selected_item:
            item = selected_item[0]
            index = self.tree.index(item)
            task = self.tasks[index]
            task["completed"] = not task["completed"]
            status = "выполнена" if task["completed"] else "не выполнена"
            self.logger.info(f"Изменен статус задачи '{task['text']}': {status}")
            self.save_tasks()
            self.refresh_task_list()

    def delete_task(self):
        selected_item = self.tree.selection()
        if selected_item:
            if messagebox.askyesno("Подтверждение", "Вы уверены, что хотите удалить выбранную задачу?"):
                item = selected_item[0]
                index = self.tree.index(item)
                deleted_task = self.tasks[index]
                del self.tasks[index]
                self.logger.info(f"Удалена задача: {deleted_task['text']}")
                self.save_tasks()
                self.refresh_task_list()

    def edit_task(self):
        selected_item = self.tree.selection()
        if selected_item:
            item = selected_item[0]
            index = self.tree.index(item)
            old_text = self.tasks[index]["text"]
            
            # Create edit window
            edit_window = tk.Toplevel(self.root)
            edit_window.title("Редактировать задачу")
            edit_window.geometry("400x100")
            
            edit_var = tk.StringVar(value=old_text)
            edit_entry = ttk.Entry(edit_window, textvariable=edit_var, width=40)
            edit_entry.pack(pady=10)
            
            def save_edit():
                new_text = edit_var.get().strip()
                if new_text:
                    if len(new_text) > 100:
                        self.logger.warning(f"Попытка сохранить слишком длинную задачу при редактировании: {len(new_text)} символов")
                        messagebox.showwarning("Предупреждение", "Задача слишком длинная! Максимум 100 символов.")
                        return
                    self.tasks[index]["text"] = new_text
                    self.logger.info(f"Задача отредактирована: '{old_text}' -> '{new_text}'")
                    self.save_tasks()
                    self.refresh_task_list()
                    edit_window.destroy()
                else:
                    self.logger.warning("Попытка сохранить пустую задачу при редактировании")
                    messagebox.showwarning("Предупреждение", "Задача не может быть пустой!")
            
            save_button = ttk.Button(edit_window, text="Сохранить", command=save_edit)
            save_button.pack(pady=5)

    def show_context_menu(self, event):
        if self.tree.selection():
            self.context_menu.post(event.x_root, event.y_root)

    def refresh_task_list(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Sort tasks by date and completion status
        sorted_tasks = sorted(self.tasks, key=lambda x: (x["completed"], x["date"]))
        
        for task in sorted_tasks:
            status = "✓" if task["completed"] else "○"
            self.tree.insert("", tk.END, values=(status, task["text"], task["date"]))

    def save_tasks(self):
        try:
            # Create backup of existing file if it exists
            if os.path.exists(self.tasks_file):
                try:
                    shutil.copy2(self.tasks_file, self.backup_file)
                    self.logger.debug("Создана резервная копия файла задач")
                except Exception as e:
                    error_msg = f"Не удалось создать резервную копию: {str(e)}"
                    self.logger.error(error_msg)
                    messagebox.showwarning("Предупреждение", error_msg)
            
            # Ensure the directory exists
            os.makedirs(self.data_dir, exist_ok=True)
            
            # Write to a temporary file first
            temp_file = os.path.join(self.data_dir, "tasks_temp.json")
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(self.tasks, f, ensure_ascii=False, indent=2)
            
            # If successful, rename the temp file to the actual file
            if os.path.exists(self.tasks_file):
                os.remove(self.tasks_file)
            os.rename(temp_file, self.tasks_file)
            self.logger.debug("Задачи успешно сохранены")
            
        except PermissionError as e:
            error_msg = "Нет прав доступа для сохранения файла. Попробуйте запустить программу от имени администратора."
            self.logger.error(f"Ошибка прав доступа при сохранении: {str(e)}")
            messagebox.showerror("Ошибка", error_msg)
        except Exception as e:
            error_msg = f"Не удалось сохранить задачи: {str(e)}"
            self.logger.error(f"Ошибка при сохранении задач: {str(e)}")
            messagebox.showerror("Ошибка", error_msg)

    def load_tasks(self):
        try:
            if os.path.exists(self.tasks_file):
                with open(self.tasks_file, "r", encoding="utf-8") as f:
                    self.tasks = json.load(f)
                    self.logger.info(f"Загружено {len(self.tasks)} задач из основного файла")
            elif os.path.exists(self.backup_file):
                # Try to load from backup if main file is corrupted
                with open(self.backup_file, "r", encoding="utf-8") as f:
                    self.tasks = json.load(f)
                    self.logger.info(f"Загружено {len(self.tasks)} задач из резервной копии")
                messagebox.showinfo("Восстановление", "Данные восстановлены из резервной копии.")
        except PermissionError as e:
            self.logger.error(f"Ошибка прав доступа при загрузке: {str(e)}")
            messagebox.showerror("Ошибка", "Нет прав доступа для чтения файла.")
            self.tasks = []
        except json.JSONDecodeError as e:
            self.logger.error(f"Ошибка формата JSON при загрузке: {str(e)}")
            messagebox.showerror("Ошибка", "Файл с задачами поврежден. Создан новый список задач.")
            self.tasks = []
        except Exception as e:
            self.logger.error(f"Непредвиденная ошибка при загрузке задач: {str(e)}")
            messagebox.showerror("Ошибка", f"Не удалось загрузить задачи: {str(e)}")
            self.tasks = []

    def start_move(self, event):
        """Начало перетаскивания окна"""
        self.x = event.x
        self.y = event.y

    def do_move(self, event):
        """Перетаскивание окна"""
        deltax = event.x - self.x
        deltay = event.y - self.y
        x = self.root.winfo_x() + deltax
        y = self.root.winfo_y() + deltay
        self.root.geometry(f"+{x}+{y}")
        self.save_window_position()

    def minimize_window(self):
        """Сворачивание окна"""
        try:
            if not self.is_minimized:
                self.last_geometry = self.root.geometry()
                self.root.withdraw()
                self.is_minimized = True
                # Создаем маленькое окно в трее
                self.create_tray_window()
        except Exception as e:
            self.logger.error(f"Ошибка при сворачивании окна: {str(e)}")
            messagebox.showerror("Ошибка", "Не удалось свернуть окно")

    def create_tray_window(self):
        """Создание окна в трее"""
        self.tray = tk.Toplevel(self.root)
        self.tray.overrideredirect(True)
        self.tray.geometry("32x32")
        
        # Размещаем окно в правом нижнем углу
        screen_width = self.tray.winfo_screenwidth()
        screen_height = self.tray.winfo_screenheight()
        self.tray.geometry(f"+{screen_width-40}+{screen_height-40}")
        
        # Создаем кнопку для восстановления
        btn = ttk.Button(self.tray, text="↑", width=3, command=self.show_window)
        btn.pack(expand=True, fill='both')
        
        # Делаем окно поверх остальных
        self.tray.attributes('-topmost', True)
        
        # Привязываем двойной клик к восстановлению окна
        self.tray.bind('<Double-Button-1>', lambda e: self.show_window())

    def show_window(self, event=None):
        """Восстановление окна из трея"""
        try:
            if self.is_minimized:
                if hasattr(self, 'tray'):
                    self.tray.destroy()
                self.root.deiconify()
                if self.last_geometry:
                    self.root.geometry(self.last_geometry)
                self.is_minimized = False
                self.root.attributes('-topmost', True)
                self.root.update()
                self.root.after(10, lambda: self.root.attributes('-topmost', False))
        except Exception as e:
            self.logger.error(f"Ошибка при восстановлении окна: {str(e)}")
            messagebox.showerror("Ошибка", "Не удалось восстановить окно")

    def toggle_expand(self):
        """Разворачивание/сворачивание окна"""
        if not self.is_expanded:
            self.normal_geometry = self.root.geometry()
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            self.root.geometry(f"400x600+{screen_width-420}+{screen_height-620}")
            self.expand_button.configure(text="❐")
            self.is_expanded = True
        else:
            self.root.geometry(self.normal_geometry)
            self.expand_button.configure(text="□")
            self.is_expanded = False
        self.save_window_position()

    def toggle_opacity(self):
        """Переключение прозрачности"""
        if not self.is_transparent:
            self.root.attributes('-alpha', 0.5)
            self.opacity_button.configure(text="●")
            self.is_transparent = True
        else:
            self.root.attributes('-alpha', 0.9)
            self.opacity_button.configure(text="○")
            self.is_transparent = False

    def save_window_position(self):
        """Сохранение позиции окна"""
        try:
            position = {
                'geometry': self.root.geometry(),
                'is_expanded': self.is_expanded,
                'normal_geometry': self.normal_geometry
            }
            with open(os.path.join(self.data_dir, 'window_position.json'), 'w') as f:
                json.dump(position, f)
        except Exception as e:
            self.logger.error(f"Ошибка при сохранении позиции окна: {str(e)}")

    def load_window_position(self):
        """Загрузка последней позиции окна"""
        try:
            position_file = os.path.join(self.data_dir, 'window_position.json')
            if os.path.exists(position_file):
                with open(position_file, 'r') as f:
                    position = json.load(f)
                    self.root.geometry(position['geometry'])
                    self.is_expanded = position['is_expanded']
                    self.normal_geometry = position['normal_geometry']
            else:
                # Устанавливаем окно в правый верхний угол при первом запуске
                screen_width = self.root.winfo_screenwidth()
                self.root.geometry(f"300x400+{screen_width-320}+20")
        except Exception as e:
            self.logger.error(f"Ошибка при загрузке позиции окна: {str(e)}")
            # Устанавливаем окно в правый верхний угол при ошибке
            screen_width = self.root.winfo_screenwidth()
            self.root.geometry(f"300x400+{screen_width-320}+20")

if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = TodoApp(root)
        root.mainloop()
    except Exception as e:
        try:
            messagebox.showerror("Критическая ошибка", f"Не удалось запустить приложение:\n{str(e)}\n\nПолный текст ошибки:\n{traceback.format_exc()}")
        except:
            print(f"Критическая ошибка: {str(e)}\n{traceback.format_exc()}", file=sys.stderr)
        sys.exit(1) 