import socket
import pyautogui
import os
import subprocess

HOST = '0.0.0.0'
PORT = 5555

print("🟢 Zenit PC Server запущен. Ожидаю команды от телефона...")

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind((HOST, PORT))
    s.listen()
    while True:
        conn, addr = s.accept()
        with conn:
            data = conn.recv(1024).decode()
            print(f"Получена команда: {data}")
            if data == "lock":
                pyautogui.hotkey('win', 'l')
            elif data == "shutdown":
                os.system("shutdown /s /t 1")
            elif data == "vol_up":
                pyautogui.press('volumeup')
            elif data == "vol_down":
                pyautogui.press('volumedown')
            elif data == "browser":
                subprocess.Popen(['start', 'https://google.com'], shell=True)
            elif data == "screenshot":
                pyautogui.screenshot('zenit_screenshot.png')
        conn.close()
