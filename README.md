# Sputnik Public

[Русский](#русский) · [English](#english)

A local, privacy-friendly Jackbox answer moderator powered by Selenium.

---

## Русский

### Возможности

- автоматически принимает или отклоняет ответы на странице модератора Jackbox;
- проверяет текст, ники и регулярные выражения по локальным спискам;
- распознаёт часть обходов фильтра: подмену кириллицы латиницей, цифры и разделители;
- работает с Microsoft Edge и Mozilla Firefox;
- самостоятельно подбирает драйвер браузера через Selenium Manager;
- позволяет выбрать единое правило для рисунков: принимать или отклонять;
- хранит настройки только локально в `config.json`.

В проекте нет Telegram, Discord, TikTok, внешней ИИ-модерации, токенов,
вебхуков, телеметрии или отправки пользовательских данных.

### Быстрый запуск на Windows

1. Скачайте репозиторий через **Code → Download ZIP** и распакуйте архив.
2. Дважды нажмите `START.bat`.
3. При отсутствии Python скрипт установит его через стандартный Windows Package Manager (`winget`).
4. При первом запуске будет создано изолированное окружение `.venv` и установлен Selenium.
5. В приложении выберите Edge или Firefox и нажмите **«Запустить модерацию»**.
6. В открывшемся браузере войдите в комнату на странице модератора Jackbox.

Не запускайте `msedgedriver` или `geckodriver` вручную и не настраивайте порты:
Selenium Manager делает это автоматически.

### Настройка фильтров

- `blacklist.txt` — запрещённые слова и фрагменты;
- `blacklist_names.txt` — запрещённые ники;
- `blacklist_regex.txt` — регулярные выражения Python.

Каждое правило размещается на отдельной строке. Пустые строки и строки,
начинающиеся с `#`, игнорируются. После изменения списков перезапустите
модерацию.

Внимание: файлы чёрных списков содержат оскорбительные и нежелательные слова,
поскольку они нужны для работы фильтра.

### Рисунки

Публичная версия не отправляет изображения внешним ИИ-сервисам. В настройках
можно выбрать безопасное общее поведение: автоматически принимать либо
отклонять все рисунки.

### Если приложение не запускается

- убедитесь, что архив полностью распакован;
- проверьте подключение к интернету при первом запуске;
- установите обновления Windows и браузера;
- снова запустите `START.bat` — повторный запуск безопасен и не переустанавливает готовые зависимости.

---

## English

### Features

- automatically accepts or rejects answers on the Jackbox moderator page;
- checks messages, player names, and regular expressions against local lists;
- detects common filter bypasses such as Latin/Cyrillic substitutions, digits, and separators;
- supports Microsoft Edge and Mozilla Firefox;
- selects the matching browser driver automatically through Selenium Manager;
- provides a global accept/reject policy for drawings;
- stores settings locally in `config.json`.

The project contains no Telegram, Discord, TikTok, external AI moderation,
tokens, webhooks, telemetry, or user-data uploads.

### Quick start on Windows

1. Download the repository using **Code → Download ZIP**, then extract it.
2. Double-click `START.bat`.
3. If Python is missing, the launcher installs it through Windows Package Manager (`winget`).
4. On the first run, it creates an isolated `.venv` and installs Selenium.
5. Select Edge or Firefox and click **Start moderation**.
6. Join your room in the Jackbox moderator page opened by the browser.

Do not start `msedgedriver` or `geckodriver` manually and do not configure
ports. Selenium Manager handles the driver automatically.

### Filter configuration

- `blacklist.txt` — blocked words and fragments;
- `blacklist_names.txt` — blocked player names;
- `blacklist_regex.txt` — Python regular expressions.

Place one rule on each line. Empty lines and lines beginning with `#` are
ignored. Restart moderation after editing a list.

Warning: the blacklist files contain offensive and unwanted terms because they
are required for the filter to function.

### Drawings

The public edition never uploads drawings to an external AI service. Choose a
safe global policy in the settings to accept or reject every drawing.

### Troubleshooting

- make sure the downloaded archive has been fully extracted;
- check the internet connection during the first launch;
- install current Windows and browser updates;
- run `START.bat` again — repeated launches are safe and reuse installed dependencies.

## Privacy and scope

All moderation decisions happen locally. The application only controls the
browser page configured by the user. Review and customize the blacklist files
before using the moderator in a public stream.

## License

Released under the [MIT License](LICENSE).
