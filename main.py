from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.slider import Slider
from kivy.uix.image import Image
from kivy.uix.widget import Widget
from kivy.uix.textinput import TextInput
from kivy.graphics import Color, Ellipse
from kivy.animation import Animation
from kivy.clock import Clock
from kivy.core.window import Window
import threading
import json
import sqlite3
from datetime import datetime
from vosk import Model, KaldiRecognizer
import pyaudio
from plyer import tts
import pyttsx3
import socket

# ====================== ПАМЯТЬ ======================
class ZenitMemory:
    def __init__(self):
        self.conn = sqlite3.connect('zenit_memory.db')
        self.conn.execute('''CREATE TABLE IF NOT EXISTS profile (key TEXT PRIMARY KEY, value TEXT)''')
        self.conn.execute('''CREATE TABLE IF NOT EXISTS history (id INTEGER PRIMARY KEY, timestamp TEXT, command TEXT, response TEXT)''')
        self.conn.execute('''CREATE TABLE IF NOT EXISTS preferences (id INTEGER PRIMARY KEY, item TEXT, value TEXT)''')
        self.conn.commit()

    def get_profile(self):
        cursor = self.conn.execute("SELECT value FROM profile WHERE key='owner_profile'")
        row = cursor.fetchone()
        return json.loads(row[0]) if row else {"title": "Сэр"}

    def save_profile(self, profile):
        self.conn.execute("REPLACE INTO profile (key, value) VALUES (?, ?)", ('owner_profile', json.dumps(profile)))
        self.conn.commit()

    def save_preference(self, item, value):
        self.conn.execute("INSERT INTO preferences (item, value) VALUES (?, ?)", (item, value))
        self.conn.commit()

    def get_preferences(self):
        cursor = self.conn.execute("SELECT item, value FROM preferences")
        return cursor.fetchall()

    def save_history(self, command, response):
        self.conn.execute("INSERT INTO history (timestamp, command, response) VALUES (?, ?, ?)",
                          (datetime.now().isoformat(), command, response))
        self.conn.commit()

memory = ZenitMemory()

# ====================== ORB ======================
class ListeningOrb(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (220, 220)
        with self.canvas:
            Color(0.05, 0.75, 1, 0.9)
            self.circle = Ellipse(pos=self.pos, size=self.size)
        self.bind(pos=self.update, size=self.update)

    def update(self, *args):
        self.circle.pos = self.pos
        self.circle.size = self.size

    def start_listening(self):
        anim = Animation(size=(280, 280), duration=0.6) + Animation(size=(220, 220), duration=0.6)
        anim.repeat = True
        anim.start(self)

    def stop_listening(self):
        Animation.cancel_all(self)

# ====================== ПРОФИЛЬ ======================
class ProfileScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = FloatLayout()
        Window.clearcolor = (0.03, 0.03, 0.08, 1)
        title = Label(text='Давайте познакомимся!\nКак мне к вам обращаться?', pos_hint={'center_x': 0.5, 'top': 0.85}, font_size='22sp', color=(0, 0.8, 1, 1))
        layout.add_widget(title)
        self.name_input = TextInput(text='Сэр', multiline=False, pos_hint={'center_x': 0.5, 'top': 0.65}, size_hint=(0.7, 0.08))
        layout.add_widget(self.name_input)
        gender = BoxLayout(orientation='horizontal', pos_hint={'center_x': 0.5, 'top': 0.5}, size_hint=(0.7, 0.1))
        self.male_btn = Button(text='Мужчина (Сэр)', background_color=(0, 0.6, 1, 1))
        self.female_btn = Button(text='Женщина (Мэм)', background_color=(0.1, 0.1, 0.15, 1))
        gender.add_widget(self.male_btn)
        gender.add_widget(self.female_btn)
        layout.add_widget(gender)
        save = Button(text='Сохранить', pos_hint={'center_x': 0.5, 'y': 0.2}, size_hint=(0.6, 0.1), background_color=(0, 0.7, 1, 1))
        save.bind(on_press=self.save_profile)
        layout.add_widget(save)
        self.add_widget(layout)

    def save_profile(self, instance):
        profile = {"title": "Сэр" if self.male_btn.background_color[0] > 0.5 else "Мэм"}
        memory.save_profile(profile)
        self.manager.current = 'dashboard'

# ====================== ДАШБОРД ======================
class DashboardScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = FloatLayout()
        Window.clearcolor = (0.03, 0.03, 0.08, 1)
        self.profile = memory.get_profile()
        self.title_label = Label(text=f'SYSTEM: ONLINE\nДОБРОЕ УТРО, {self.profile["title"]}\nЗЕНИТ', pos_hint={'top': 0.95}, font_size='24sp', color=(0, 0.8, 1, 1))
        self.layout.add_widget(self.title_label)

        voice_btn = Button(text='🎤 ГОВОРИТЕ КОМАНДУ', pos_hint={'center_x': 0.5, 'y': 0.15}, size_hint=(0.6, 0.1), background_color=(0, 0.7, 1, 1))
        voice_btn.bind(on_press=self.start_voice)
        self.layout.add_widget(voice_btn)

        self.add_widget(self.layout)
        self.orb = None

    def start_voice(self, instance):
        if self.orb: return
        self.orb = ListeningOrb(pos_hint={'center_x': 0.5, 'y': 0.02})
        self.add_widget(self.orb)
        self.orb.start_listening()
        threading.Thread(target=self.listen, daemon=True).start()

    def listen(self):
        p = pyaudio.PyAudio()
        stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=8000)
        rec = KaldiRecognizer(Model("model"), 16000)
        while True:
            data = stream.read(4000, exception_on_overflow=False)
            if rec.AcceptWaveform(data):
                result = json.loads(rec.Result())
                text = result.get("text", "").lower()
                if text:
                    Clock.schedule_once(lambda dt, t=text: self.process_command(t))
                    break
        stream.stop_stream()
        stream.close()
        p.terminate()
        Clock.schedule_once(self.stop_voice)

    def stop_voice(self, dt):
        if self.orb:
            self.orb.stop_listening()
            self.remove_widget(self.orb)
            self.orb = None

    def process_command(self, text):
        title = memory.get_profile()["title"]
        response = f"Принято, {title}! {text}"
        self.speak(response)
        memory.save_history(text, response)

    def speak(self, text):
        try: tts.speak(text)
        except:
            engine = pyttsx3.init()
            engine.say(text)
            engine.runAndWait()

# ====================== МИ ПУЛЬТ ======================
class RemoteScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = FloatLayout()
        Window.clearcolor = (0.03, 0.03, 0.08, 1)

        tabs = BoxLayout(orientation='horizontal', pos_hint={'top': 0.95}, size_hint=(1, 0.08), spacing=5, padding=10)
        devices = ["TV", "Air Conditioner", "Stereo", "Projector", "PC / Laptop"]
        self.buttons = {}
        for dev in devices:
            btn = Button(text=dev, background_color=(0.1,0.1,0.15,1))
            btn.bind(on_press=self.switch_device)
            tabs.add_widget(btn)
            self.buttons[dev] = btn
        self.layout.add_widget(tabs)

        self.remote_area = FloatLayout(pos_hint={'center_x': 0.5, 'center_y': 0.5}, size_hint=(0.9, 0.7))
        self.brand_logo = Image(pos_hint={'center_x': 0.5, 'top': 0.85}, size_hint=(0.35, 0.2))
        self.remote_area.add_widget(self.brand_logo)

        self.pc_layout = BoxLayout(orientation='vertical', pos_hint={'center_x': 0.5, 'center_y': 0.4}, size_hint=(0.8, 0.5))
        self.pc_ip = TextInput(text='192.168.1.XXX', multiline=False, hint_text='IP вашего ПК')
        self.pc_layout.add_widget(self.pc_ip)

        pc_buttons = [
            ("🔒 Заблокировать ПК", "lock"),
            ("⏻ Выключить ПК", "shutdown"),
            ("🔊 Громкость +", "vol_up"),
            ("🔉 Громкость -", "vol_down"),
            ("🌐 Открыть браузер", "browser"),
            ("📸 Скриншот", "screenshot")
        ]
        for text, cmd in pc_buttons:
            btn = Button(text=text, background_color=(0, 0.6, 1, 1))
            btn.bind(on_press=lambda x, c=cmd: self.send_pc_command(c))
            self.pc_layout.add_widget(btn)

        self.remote_area.add_widget(self.pc_layout)
        self.layout.add_widget(self.remote_area)

        self.add_widget(self.layout)
        self.current_device = "TV"
        self.switch_device(None)

    def switch_device(self, instance):
        if instance: self.current_device = instance.text
        for btn in self.buttons.values():
            btn.background_color = (0, 0.6, 1, 1) if btn.text == self.current_device else (0.1,0.1,0.15,1)
        logos = {"TV": "logos/samsung.png", "Air Conditioner": "logos/daikin.png",
                 "Stereo": "logos/sony.png", "Projector": "logos/epson.png", "PC / Laptop": "logos/pc.png"}
        self.brand_logo.source = logos.get(self.current_device, "logos/samsung.png")
        self.pc_layout.opacity = 1 if self.current_device == "PC / Laptop" else 0

    def send_pc_command(self, command):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(3)
            s.connect((self.pc_ip.text, 5555))
            s.send(command.encode())
            s.close()
            self.speak(f"Команда отправлена")
        except:
            self.speak("Не удалось подключиться к ПК")

    def speak(self, text):
        try: tts.speak(text)
        except: pass

# ====================== ПРИЛОЖЕНИЕ ======================
class ZenitApp(App):
    def build(self):
        sm = ScreenManager()
        if not memory.get_profile().get("title"):
            sm.add_widget(ProfileScreen(name='profile'))
            sm.current = 'profile'
        else:
            sm.add_widget(DashboardScreen(name='dashboard'))
            sm.add_widget(RemoteScreen(name='remote'))
        return sm

if __name__ == '__main__':
    ZenitApp().run()
