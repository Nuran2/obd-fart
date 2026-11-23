import math
import re
import socket
import threading
import time

import numpy as np
from kivy.app import App
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.slider import Slider
from kivy.uix.textinput import TextInput
from kivy.uix.togglebutton import ToggleButton
from kivy.utils import platform

SR = 22050
BLOCK = 512


class Synth:
    def __init__(self):
        self.target_rpm = 0.0
        self.rpm = 0.0
        self.phase = 0.0
        self.gain = 1.0
        self.amps = np.random.uniform(0.5, 1.0, 256)

    def generate(self):
        self.rpm += (self.target_rpm - self.rpm) * 0.2
        if self.rpm < 100:
            return np.zeros(BLOCK, dtype=np.int16)
        f = self.rpm / 60.0 * 2.0
        phase = self.phase + np.cumsum(np.full(BLOCK, f / SR))
        self.phase = phase[-1] % 256
        frac = phase % 1.0
        idx = phase.astype(int) % 256
        noise = np.random.uniform(-1, 1, BLOCK)
        w = (np.sin(2 * math.pi * frac * 1.5) * np.exp(-4 * frac)
             + 0.45 * noise * np.exp(-6 * frac)) * self.amps[idx]
        vol = min(1.0, 0.5 + self.rpm / 6000.0)
        out = np.tanh(w * 2.5 * self.gain * vol) * 0.8
        return (out * 32767).astype(np.int16)


class Elm327:
    def __init__(self, host, port, timeout=5):
        self.sock = socket.create_connection((host, port), timeout=timeout)
        self.sock.settimeout(timeout)
        for cmd in ("ATZ", "ATE0", "ATL0", "ATS0", "ATH0", "ATSP0"):
            self.send(cmd)

    def send(self, cmd):
        self.sock.sendall((cmd + "\r").encode())
        buf = b""
        while not buf.endswith(b">"):
            chunk = self.sock.recv(1024)
            if not chunk:
                raise ConnectionError("Адаптер закрыл соединение")
            buf += chunk
        return buf.decode(errors="ignore").replace(">", "").strip()

    def read_rpm(self):
        resp = self.send("010C").upper()
        m = re.search(r"410C\s*([0-9A-F]{2})\s*([0-9A-F]{2})", resp)
        if not m:
            return None
        return (int(m.group(1), 16) * 256 + int(m.group(2), 16)) / 4.0

    def close(self):
        try:
            self.sock.close()
        except OSError:
            pass


class Root(BoxLayout):
    def __init__(self, **kw):
        super().__init__(orientation="vertical", padding=20, spacing=12, **kw)
        self.synth = Synth()
        self.running = False

        self.host = TextInput(text="192.168.0.10", multiline=False,
                              size_hint_y=None, height=100, font_size=36)
        self.port = TextInput(text="35000", multiline=False,
                              size_hint_y=None, height=100, font_size=36,
                              input_filter="int")
        self.demo = ToggleButton(text="Демо (без машины)", size_hint_y=None,
                                 height=100, font_size=32)
        self.vol = Slider(min=0.2, max=3.0, value=1.0, size_hint_y=None,
                          height=80)
        self.vol.bind(value=lambda s, v: setattr(self.synth, "gain", v))
        self.btn = Button(text="СТАРТ", size_hint_y=None, height=140,
                          font_size=48)
        self.btn.bind(on_release=self.toggle)
        self.rpm_label = Label(text="0", font_size=120)
        self.status = Label(text="Подключись к WiFi адаптера и нажми СТАРТ",
                            font_size=28, size_hint_y=None, height=120,
                            text_size=(900, None), halign="center")

        for w in (Label(text="IP адаптера", size_hint_y=None, height=50,
                        font_size=28), self.host,
                  Label(text="Порт", size_hint_y=None, height=50,
                        font_size=28), self.port,
                  self.demo,
                  Label(text="Громкость", size_hint_y=None, height=50,
                        font_size=28), self.vol,
                  self.rpm_label, self.status, self.btn):
            self.add_widget(w)

        threading.Thread(target=self.audio_loop, daemon=True).start()

    # ---------- звук ----------
    def audio_loop(self):
        if platform != "android":
            while True:
                time.sleep(1)
        from jnius import autoclass
        AudioTrack = autoclass("android.media.AudioTrack")
        AudioFormat = autoclass("android.media.AudioFormat")
        AudioManager = autoclass("android.media.AudioManager")
        ch = AudioFormat.CHANNEL_OUT_MONO
        enc = AudioFormat.ENCODING_PCM_16BIT
        minbuf = AudioTrack.getMinBufferSize(SR, ch, enc)
        track = AudioTrack(AudioManager.STREAM_MUSIC, SR, ch, enc,
                           max(minbuf, 4096) * 2, AudioTrack.MODE_STREAM)
        track.play()
        while True:
            pcm = self.synth.generate().tolist()
            track.write(pcm, 0, len(pcm))

    # ---------- OBD ----------
    def toggle(self, *_):
        if self.running:
            self.running = False
            return
        self.running = True
        self.btn.text = "СТОП"
        threading.Thread(target=self.obd_loop, daemon=True).start()

    def ui(self, status=None, rpm=None, btn=None):
        def f(dt):
            if status is not None:
                self.status.text = status
            if rpm is not None:
                self.rpm_label.text = str(int(rpm))
            if btn is not None:
                self.btn.text = btn
        Clock.schedule_once(f)

    def obd_loop(self):
        elm = None
        try:
            if self.demo.state != "down":
                self.ui(status="Подключаюсь...")
                elm = Elm327(self.host.text.strip(), int(self.port.text))
                self.ui(status="Подключено")
            else:
                self.ui(status="Демо-режим")
            t0 = time.time()
            while self.running:
                if elm:
                    rpm = elm.read_rpm()
                    if rpm is None:
                        self.ui(status="Нет данных. Зажигание включено?")
                        time.sleep(0.5)
                        continue
                else:
                    rpm = 1500 + 1400 * math.sin((time.time() - t0) / 2.5)
                    time.sleep(0.05)
                self.synth.target_rpm = rpm
                self.ui(rpm=rpm)
        except Exception as e:
            self.ui(status="Ошибка: %s" % e)
        finally:
            if elm:
                elm.close()
            self.running = False
            self.synth.target_rpm = 0.0
            self.ui(btn="СТАРТ")


class ObdFartApp(App):
    def build(self):
        return Root()

    def on_pause(self):
        return True


if __name__ == "__main__":
    ObdFartApp().run()
