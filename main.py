from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.uix.popup import Popup
from kivy.graphics import Color, Rectangle, Line
from kivy.core.text import LabelBase
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from datetime import datetime
from kivy.uix.button import Button
import os
import json
import glob

from CircleTimer import CircleTimer

Window.size = (360, 640)
LabelBase.register(name="Roboto", fn_regular="Roboto-Regular.ttf")

DATA_FILE = "data.json"
SOUNDS_FOLDER = "sounds"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"user": {}, "meditation": [], "sleep": []}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def get_sound_files():
    if not os.path.exists(SOUNDS_FOLDER):
        os.makedirs(SOUNDS_FOLDER)
    sounds = []
    for ext in ['*.mp3', '*.wav']:
        sounds.extend(glob.glob(os.path.join(SOUNDS_FOLDER, ext)))
    return [os.path.splitext(os.path.basename(f))[0] for f in sounds]

class DarkOverlay(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas:
            Color(0, 0, 0, 0.4)
            self.rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self.update_rect, size=self.update_rect)

    def update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size

class NavigationButton(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint_y = None
        self.height = dp(50)
        self.spacing = dp(2)
        self.padding = dp(2)
        
        with self.canvas.before:
            Color(0.1, 0.1, 0.1, 1)
            self.rect = Rectangle(pos=self.pos, size=self.size)
        
        self.bind(pos=self.update_rect, size=self.update_rect)
        
    def update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size

class MeditationScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.paused = False
        self.pause_time = 0
        self.pause_button = None

    def on_kv_post(self, base_widget):
        self.spinner_hours = self.ids.spinner_hours
        self.spinner_minutes = self.ids.spinner_minutes
        self.spinner_seconds = self.ids.spinner_seconds
        self.start_button = self.ids.start_button
        self.circle_timer = self.ids.circle_timer
        self.sound_spinner = self.ids.sound_spinner
        self.timer_event = None
        self.remaining_seconds = 0
        self.total_seconds = 0
        self.sound = None
        self.update_sound_list()
        self.pause_button = None

    def update_sound_list(self):
        sounds = get_sound_files()
        self.sound_spinner.values = sounds
        if sounds:
            self.sound_spinner.text = sounds[0]
        else:
            self.sound_spinner.text = "Нет звуков"

    def update_time_label(self):
        h = self.remaining_seconds // 3600
        m = (self.remaining_seconds % 3600) // 60
        s = self.remaining_seconds % 60
        self.circle_timer.time_text = f"{h:02}:{m:02}:{s:02}"

    def timer_tick(self, dt):
        if self.remaining_seconds > 0:
            self.remaining_seconds -= 1
            self.circle_timer.progress = self.remaining_seconds / self.total_seconds
            self.update_time_label()
        else:
            self.stop_session()
            self.save_session()

    def toggle_navigation(self, enable):
        root = App.get_running_app().root
        for screen in root.screens:
            if hasattr(screen, 'nav_button'):
                screen.nav_button.disabled = not enable
                screen.nav_button.background_color = (0.2, 0.2, 0.2, 1) if not enable else (0.2, 0.6, 0.2, 1)

    def start_stop_session(self):
        if self.start_button.text == "Начать фокус-сессию":
            h = int(self.spinner_hours.text)
            m = int(self.spinner_minutes.text)
            s = int(self.spinner_seconds.text)
            self.total_seconds = h * 3600 + m * 60 + s
            if self.total_seconds == 0:
                self.circle_timer.time_text = "Установи ненулевое время"
                return
            
            # Start playing sound
            sound_name = self.sound_spinner.text
            if sound_name != "Нет звуков":
                sound_path = os.path.join(SOUNDS_FOLDER, sound_name + ('.mp3' if os.path.exists(os.path.join(SOUNDS_FOLDER, sound_name + '.mp3')) else '.wav'))
                self.sound = SoundLoader.load(sound_path)
                if self.sound:
                    self.sound.loop = True
                    self.sound.play()

            self.remaining_seconds = self.total_seconds
            self.update_time_label()
            self.circle_timer.progress = 1.0

            self.spinner_hours.opacity = 0
            self.spinner_minutes.opacity = 0
            self.spinner_seconds.opacity = 0
            self.sound_spinner.opacity = 0

            self.start_button.text = "Пауза"
            self.timer_event = Clock.schedule_interval(self.timer_tick, 1)
            
            self.pause_button = Button(
                text="Завершить", 
                size_hint=(0.3, None), 
                height=dp(50),
                background_color=(0.8, 0.2, 0.2, 1),
                background_normal=''
            )
            self.pause_button.bind(on_press=self.show_confirmation_dialog)
            self.ids.button_box.add_widget(self.pause_button)
            
            self.toggle_navigation(False)
            
        elif self.start_button.text == "Пауза":
            self.pause_session()
        elif self.start_button.text == "Продолжить":
            self.resume_session()

    def pause_session(self):
        if self.timer_event:
            self.timer_event.cancel()
            self.timer_event = None
            self.pause_time = datetime.now()
            self.start_button.text = "Продолжить"
            if self.sound:
                self.sound.stop()

    def resume_session(self):
        if self.pause_time:
            pause_duration = (datetime.now() - self.pause_time).total_seconds()
            self.remaining_seconds += int(pause_duration)
        
        self.start_button.text = "Пауза"
        self.timer_event = Clock.schedule_interval(self.timer_tick, 1)
        if self.sound:
            self.sound.play()

    def show_confirmation_dialog(self, instance):
        box = BoxLayout(orientation='vertical', spacing=dp(10))
        box.add_widget(Label(text="Завершить сессию?", font_size='18sp'))
        btn_box = BoxLayout(spacing=dp(5))
        yes_btn = Button(text="Да", background_color=(0.8, 0.2, 0.2, 1))
        no_btn = Button(text="Нет", background_color=(0.2, 0.6, 0.2, 1))
        
        def finish_session(btn):
            self.stop_session()
            self.save_session()
            popup.dismiss()
        
        yes_btn.bind(on_press=finish_session)
        no_btn.bind(on_press=lambda x: popup.dismiss())
        
        btn_box.add_widget(yes_btn)
        btn_box.add_widget(no_btn)
        box.add_widget(btn_box)
        
        popup = Popup(
            title="Подтверждение", 
            content=box, 
            size_hint=(0.7, 0.4),
            separator_color=(0.2, 0.6, 0.2, 1)
        )
        popup.open()

    def stop_session(self):
        if self.timer_event:
            self.timer_event.cancel()
            self.timer_event = None
        
        if self.pause_button:
            self.ids.button_box.remove_widget(self.pause_button)
            self.pause_button = None
        
        if self.sound:
            self.sound.stop()
            self.sound = None

        self.start_button.text = "Начать фокус-сессию"
        self.spinner_hours.opacity = 1
        self.spinner_minutes.opacity = 1
        self.spinner_seconds.opacity = 1
        self.sound_spinner.opacity = 1
        self.circle_timer.progress = 1.0
        self.toggle_navigation(True)

    def save_session(self):
        duration = self.total_seconds / 3600
        data = load_data()
        data["meditation"].append({
            "datetime": datetime.now().isoformat(),
            "duration": duration,
            "sound": self.sound_spinner.text if self.sound_spinner.text != "Нет звуков" else None
        })
        save_data(data)

class SleepScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.paused = False
        self.pause_time = 0
        self.pause_duration = 0

    def on_kv_post(self, base_widget):
        self.sleeping = False
        self.timer = 0
        self.timer_event = None
        self.sound_timer_event = None
        self.start_time = None
        self.sound = None
        self.ids.sleep_timer_label.text = ""
        self.sound_spinner = self.ids.sound_spinner
        self.sound_duration_spinner = self.ids.sound_duration_spinner
        self.update_sound_list()
        
        self.sound_duration_spinner.values = ["Без звука", "1 мин", "5 мин", "10 мин", "15 мин", "30 мин", "1 час"]
        self.sound_duration_spinner.text = "10 мин"
        self.pause_button = None

    def toggle_navigation(self, enable):
        root = App.get_running_app().root
        for screen in root.screens:
            if hasattr(screen, 'nav_button'):
                screen.nav_button.disabled = not enable
                screen.nav_button.background_color = (0.2, 0.2, 0.2, 1) if not enable else (0.2, 0.6, 0.2, 1)

    def update_sound_list(self):
        sounds = get_sound_files()
        self.sound_spinner.values = sounds
        if sounds:
            self.sound_spinner.text = sounds[0]
        else:
            self.sound_spinner.text = "Нет звуков"
            self.sound_duration_spinner.text = "Без звука"

    def toggle_sleep(self):
        if not self.sleeping:
            self.start_sleep()
        else:
            if self.ids.sleep_button.text == "Пауза":
                self.pause_sleep()
            elif self.ids.sleep_button.text == "Продолжить":
                self.resume_sleep()

    def start_sleep(self):
        self.sleeping = True
        self.timer = 0
        self.start_time = datetime.now()
        self.ids.sleep_button.text = "Пауза"
        self.ids.sleep_label.text = "Сон начался..."
        self.ids.sleep_timer_label.text = "00:00:00"
        
        # Запуск звука (если выбран)
        sound_duration = self.sound_duration_spinner.text
        if sound_duration != "Без звука" and self.sound_spinner.text != "Нет звуков":
            sound_name = self.sound_spinner.text
            sound_path = os.path.join(SOUNDS_FOLDER, sound_name + ('.mp3' if os.path.exists(os.path.join(SOUNDS_FOLDER, sound_name + '.mp3')) else '.wav'))
            self.sound = SoundLoader.load(sound_path)
            if self.sound:
                self.sound.loop = True
                self.sound.play()
                
                duration_mapping = {
                    "1 мин": 60,
                    "5 мин": 300,
                    "10 мин": 600,
                    "15 мин": 900,
                    "30 мин": 1800,
                    "1 час": 3600
                }
                sound_duration_sec = duration_mapping.get(sound_duration, 0)
                if sound_duration_sec > 0:
                    self.sound_timer_event = Clock.schedule_once(self.stop_sound, sound_duration_sec)
        
        self.timer_event = Clock.schedule_interval(self.update_timer, 1)
        self.sound_spinner.opacity = 0
        self.sound_duration_spinner.opacity = 0
        
        # Add stop button
        if not self.pause_button:
            self.pause_button = Button(
                text="Завершить", 
                size_hint=(0.3, None), 
                height=dp(50),
                background_color=(0.8, 0.2, 0.2, 1),
                background_normal='',
                pos_hint={'center_x': 0.5}
            )
            self.pause_button.bind(on_press=self.show_confirmation_dialog)
            self.ids.sleep_button_box.add_widget(self.pause_button)
        
        self.toggle_navigation(False)

    def pause_sleep(self):
        if self.timer_event:
            self.timer_event.cancel()
            self.timer_event = None
            self.pause_time = datetime.now()
            self.ids.sleep_button.text = "Продолжить"
            if self.sound:
                self.sound.stop()

    def resume_sleep(self):
        if self.pause_time:
            self.pause_duration += (datetime.now() - self.pause_time).total_seconds()
        
        self.ids.sleep_button.text = "Пауза"
        self.timer_event = Clock.schedule_interval(self.update_timer, 1)
        if self.sound:
            self.sound.play()

    def stop_sound(self, dt):
        if self.sound:
            self.sound.stop()
            self.sound = None

    def update_timer(self, dt):
        self.timer += 1
        h = self.timer // 3600
        m = (self.timer % 3600) // 60
        s = self.timer % 60
        self.ids.sleep_timer_label.text = f"{h:02}:{m:02}:{s:02}"

    def show_confirmation_dialog(self, instance):
        box = BoxLayout(orientation='vertical', spacing=dp(10))
        box.add_widget(Label(text="Завершить сон?", font_size='18sp'))
        btn_box = BoxLayout(spacing=dp(5))
        yes_btn = Button(text="Да", background_color=(0.8, 0.2, 0.2, 1))
        no_btn = Button(text="Нет", background_color=(0.2, 0.6, 0.2, 1))
        
        def finish_session(btn):
            self.end_sleep()
            popup.dismiss()
        
        yes_btn.bind(on_press=finish_session)
        no_btn.bind(on_press=lambda x: popup.dismiss())
        
        btn_box.add_widget(yes_btn)
        btn_box.add_widget(no_btn)
        box.add_widget(btn_box)
        
        popup = Popup(
            title="Подтверждение", 
            content=box, 
            size_hint=(0.7, 0.4),
            separator_color=(0.2, 0.6, 0.2, 1)
        )
        popup.open()

    def end_sleep(self):
        if self.timer_event:
            self.timer_event.cancel()
        if self.sound_timer_event:
            self.sound_timer_event.cancel()
        
        self.stop_sound(None)
        self.sleeping = False
        end_time = datetime.now()
        
        # Adjust for pause time
        actual_duration = self.timer - self.pause_duration
        h = actual_duration // 3600
        m = (actual_duration % 3600) // 60
        s = actual_duration % 60

        data = load_data()
        data["sleep"].append({
            "start": self.start_time.isoformat(),
            "end": end_time.isoformat(),
            "duration": actual_duration / 3600,
            "sound": self.sound_spinner.text if (self.sound_spinner.text != "Нет звуков" and 
                                             self.sound_duration_spinner.text != "Без звука") else None,
            "sound_duration": self.sound_duration_spinner.text if self.sound_duration_spinner.text != "Без звука" else None
        })
        save_data(data)

        self.ids.sleep_label.text = f"Вы спали {h} ч {m} мин {s} сек"
        self.ids.sleep_timer_label.text = ""
        self.ids.sleep_button.text = "Начать сон"
        self.sound_spinner.opacity = 1
        self.sound_duration_spinner.opacity = 1
        
        if self.pause_button:
            self.ids.sleep_button_box.remove_widget(self.pause_button)
            self.pause_button = None
        
        self.pause_duration = 0
        self.toggle_navigation(True)

class ReportScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.report_container = None
        
    def on_kv_post(self, base_widget):
        self.report_container = self.ids.report_container
        self.update_report("meditation")
        self.highlight_button("meditation")

    def update_report(self, report_type):
        if not hasattr(self, 'report_container') or not self.report_container:
            return
            
        data = load_data()
        report_data = data.get(report_type, [])
        self.report_container.clear_widgets()
        
        if not report_data:
            no_data_label = Label(
                text="Нет данных" if report_type == "meditation" else "Нет данных о сне",
                font_size='18sp',
                color=(0.8, 0.8, 0.8, 1),
                size_hint_y=None,
                height=dp(100),
                valign='middle'
            )
            self.report_container.add_widget(no_data_label)
            return
            
        grid = GridLayout(
            cols=3,
            size_hint_y=None,
            spacing=dp(5),
            padding=dp(10),
            row_default_height=dp(50),
            row_force_default=True
        )
        grid.bind(minimum_height=grid.setter('height'))
        
        header_style = {
            'font_size': '16sp',
            'bold': True,
            'size_hint_y': None,
            'height': dp(40),
            'halign': 'center',
            'valign': 'middle'
        }
        
        data_style = {
            'font_size': '14sp',
            'size_hint_y': None,
            'height': dp(40),
            'halign': 'center',
            'valign': 'middle',
            'text_size': (None, None)
        }
        
        grid.add_widget(Label(text="Дата", **header_style))
        grid.add_widget(Label(text="Длительность", **header_style))
        grid.add_widget(Label(text="Звук", **header_style))
        
        try:
            sorted_data = sorted(
                report_data,
                key=lambda x: x.get("datetime" if report_type == "meditation" else "start") or "",
                reverse=True
            )
        except:
            sorted_data = report_data
        
        def format_time(total_seconds):
            total_seconds = int(total_seconds)
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        
        for entry in sorted_data:
            date_str = entry.get("datetime" if report_type == "meditation" else "start", "")[:10]
            
            if report_type == "meditation":
                duration_seconds = entry["duration"] * 3600
            else:
                duration_seconds = entry["duration"] * 3600
            
            sound = entry.get("sound", "-") or "-"
            if report_type == "sleep":
                sound_duration = entry.get("sound_duration")
                if sound_duration:
                    sound = f"{sound} ({sound_duration})"
            
            grid.add_widget(Label(text=date_str, **data_style))
            grid.add_widget(Label(text=format_time(duration_seconds), **data_style))
            grid.add_widget(Label(text=sound, **data_style))
        
        scroll = ScrollView(
            size_hint=(1, 1),
            bar_width=dp(10),
            bar_color=(0.5, 0.5, 0.5, 0.5),
            bar_inactive_color=(0.5, 0.5, 0.5, 0.2),
            scroll_type=['bars', 'content']
        )
        scroll.add_widget(grid)
        
        self.report_container.clear_widgets()
        self.report_container.add_widget(scroll)
        
        total_seconds = sum(entry["duration"] * 3600 for entry in report_data)
        total_sessions = len(report_data)
        
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = int(total_seconds % 60)
        
        self.ids.stats_label.text = (
            f"Всего сеансов: {total_sessions}\n"
            f"Общее время: {hours} ч {minutes} мин {seconds} сек"
        )

    def highlight_button(self, active):
        self.ids.med_button.background_color = (0.1, 0.1, 0.1, 1) if active == "meditation" else (0.2, 0.6, 0.2, 1)
        self.ids.sleep_button.background_color = (0.1, 0.1, 0.1, 1) if active == "sleep" else (0.2, 0.6, 0.2, 1)

    def on_meditation_press(self):
        self.update_report("meditation")
        self.highlight_button("meditation")

    def on_sleep_press(self):
        self.update_report("sleep")
        self.highlight_button("sleep")

class InfoScreen(Screen):
    def on_pre_enter(self):
        data = load_data()
        self.ids.age_spinner.text = str(data["user"].get("age", "17"))

    def save_info(self):
        try:
            age = int(self.ids.age_spinner.text)
            data = load_data()
            data["user"]["age"] = age
            save_data(data)
            self.ids.info_label.text = "Сохранено!"
        except ValueError:
            self.ids.info_label.text = "Ошибка в данных"

class AboutScreen(Screen):
    pass

class RootWidget(ScreenManager):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.transition = SlideTransition()
        
    def switch_to(self, screen):
        current_index = self.screen_names.index(self.current)
        new_index = self.screen_names.index(screen)
        
        if new_index < current_index:
            self.transition.direction = 'right'
        else:
            self.transition.direction = 'left'
            
        self.current = screen
        self.set_active_tab(screen)
    
    def set_active_tab(self, tab_name):
        for screen in self.screens:
            if hasattr(screen, 'nav_button'):
                screen.nav_button.background_color = (0.1, 0.1, 0.1, 1) if screen.name == tab_name else (0.2, 0.6, 0.2, 1)

class FocusApp(App):
    def build(self):
        return Builder.load_file("focus.kv")

if __name__ == "__main__":
    FocusApp().run()