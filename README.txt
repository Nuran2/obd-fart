СБОРКА APK (Linux / WSL / Google Colab):
  sudo apt install -y python3-pip git zip unzip openjdk-17-jdk autoconf libtool pkg-config zlib1g-dev libncurses5-dev libffi-dev libssl-dev
  pip install buildozer cython
  cd obdfart
  buildozer android debug
APK появится в папке bin/. Скопируй на телефон и установи
(разреши установку из неизвестных источников).

ИСПОЛЬЗОВАНИЕ:
  1. Подключи телефон к WiFi адаптера OBD2.
  2. Отключи мобильный интернет, иначе Android может гнать трафик мимо адаптера.
  3. Включи зажигание, открой приложение, нажми СТАРТ.
  Приложение должно оставаться открытым на экране.
