[app]
title = Zenit — ИИ Ассистент
package.name = zenit
package.domain = org.zenitapp
source.dir = .
source.include_exts = py,png,jpg,kv,ttf
version = 1.0
requirements = python3,kivy==2.3.0,plyer,vosk,pyaudio,numpy,pyttsx3
orientation = portrait
fullscreen = 0

[android]
android.permissions = INTERNET,RECORD_AUDIO,CAMERA,WAKE_LOCK,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE
android.api = 33
android.minapi = 21
android.ndk_api = 21
android.arch = arm64-v8a,armeabi-v7a

[buildozer]
log_level = 2
warn_on_root = 1

Add buildozer.spec for Android build
