"""Sputnik Public — local Jackbox moderator via Selenium only.

No Telegram, Discord, TikTok, AI APIs, tokens, webhooks, or telemetry.
"""

from __future__ import annotations

import json
import queue
import re
import sys
import threading
import time
import unicodedata
import webbrowser
from dataclasses import asdict, dataclass
from pathlib import Path
from tkinter import BOTH, END, LEFT, RIGHT, X, BooleanVar, StringVar, Text, Tk
from tkinter import messagebox, ttk

from selenium import webdriver
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    WebDriverException,
)
from selenium.webdriver.common.by import By


APP_NAME = "Sputnik Public"
APP_VERSION = "1.0.0"
COMMUNITY_URL = "https://t.me/JackboxTiktok"


def app_dir() -> Path:
    """Use the executable folder when frozen, otherwise the script folder."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


ROOT = app_dir()
CONFIG_PATH = ROOT / "config.json"


@dataclass
class Config:
    browser: str = "Edge"
    moderator_url: str = "https://jackbox.ru/moderator"
    image_policy: str = "Принимать"
    poll_interval: float = 0.45

    @classmethod
    def load(cls) -> "Config":
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            allowed = {field for field in cls.__dataclass_fields__}
            return cls(**{key: value for key, value in data.items() if key in allowed})
        except (OSError, ValueError, TypeError):
            return cls()

    def save(self) -> None:
        CONFIG_PATH.write_text(
            json.dumps(asdict(self), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


LEET_MAP = {
    "0": "о", "1": "и", "3": "е", "4": "а", "5": "с",
    "6": "б", "7": "т", "8": "в", "9": "г", "@": "а", "$": "с",
}
LATIN_TO_CYRILLIC = {
    "a": "а", "b": "в", "c": "с", "e": "е", "f": "ф", "g": "г",
    "h": "н", "k": "к", "l": "л", "m": "м", "n": "н", "o": "о",
    "p": "р", "r": "р", "t": "т", "u": "и", "v": "в", "w": "в",
    "x": "х", "y": "у", "z": "з",
}


def normalize_evasions(text: str) -> str:
    """Normalize common attempts to bypass a word filter."""
    normalized = unicodedata.normalize("NFKC", text or "").casefold()
    normalized = "".join(
        LEET_MAP.get(char, LATIN_TO_CYRILLIC.get(char, char))
        for char in normalized
    )
    normalized = "".join(
        char
        for char in unicodedata.normalize("NFD", normalized)
        if unicodedata.category(char) != "Mn"
    )
    return re.sub(r"[^а-яa-z0-9]", "", normalized)


class Blacklists:
    def __init__(self, log) -> None:
        self.log = log
        self.words: list[str] = []
        self.names: set[str] = set()
        self.regexes: list[re.Pattern[str]] = []

    @staticmethod
    def _lines(filename: str) -> list[str]:
        path = ROOT / filename
        try:
            return [
                line.strip()
                for line in path.read_text(encoding="utf-8-sig").splitlines()
                if line.strip() and not line.lstrip().startswith("#")
            ]
        except FileNotFoundError:
            return []

    def load(self) -> None:
        self.words = [normalize_evasions(word) for word in self._lines("blacklist.txt")]
        self.names = {normalize_evasions(name) for name in self._lines("blacklist_names.txt")}
        self.regexes = []
        for pattern in self._lines("blacklist_regex.txt"):
            try:
                self.regexes.append(re.compile(pattern, re.IGNORECASE | re.UNICODE))
            except re.error as error:
                self.log(f"Некорректное регулярное выражение: {pattern} ({error})", "ERROR")
        self.log(
            f"Загружено: слов — {len(self.words)}, имён — {len(self.names)}, "
            f"шаблонов — {len(self.regexes)}."
        )

    def should_reject(self, user: str, message: str) -> tuple[bool, str]:
        if normalize_evasions(user) in self.names:
            return True, "ник в чёрном списке"

        normalized_message = normalize_evasions(message)
        for word in self.words:
            if word and word in normalized_message:
                return True, "запрещённое слово"

        for pattern in self.regexes:
            if pattern.search(message):
                return True, "запрещённый шаблон"

        return False, "сообщение чистое"


class Moderator:
    def __init__(self, config: Config, events: queue.Queue[tuple[str, str]]) -> None:
        self.config = config
        self.events = events
        self.stop_event = threading.Event()
        self.driver: webdriver.Remote | None = None
        self.blacklists = Blacklists(self.log)

    def log(self, text: str, level: str = "INFO") -> None:
        self.events.put(("log", f"[{time.strftime('%H:%M:%S')}] [{level}] {text}"))

    def status(self, text: str) -> None:
        self.events.put(("status", text))

    def stop(self) -> None:
        self.stop_event.set()
        self.status("Останавливается…")

    def _create_driver(self) -> webdriver.Remote:
        # Selenium Manager automatically finds/downloads a matching driver.
        if self.config.browser == "Firefox":
            return webdriver.Firefox(options=webdriver.FirefoxOptions())
        return webdriver.Edge(options=webdriver.EdgeOptions())

    def run(self) -> None:
        self.blacklists.load()
        self.status("Запуск браузера…")
        try:
            self.log(f"Запускаю {self.config.browser} через Selenium Manager…")
            self.driver = self._create_driver()
            self.driver.get(self.config.moderator_url)
            self.status("Введите код комнаты в браузере")
            self.log(f"Открыта страница: {self.config.moderator_url}")

            game_name = ""
            while not self.stop_event.is_set():
                game_name = self._read_game_name()
                if game_name:
                    break
                self.stop_event.wait(0.5)
            if self.stop_event.is_set():
                return

            self.status(f"Работает · {game_name}")
            self.log(f"Обнаружена игра: {game_name}. Модерация запущена.")
            self._moderation_loop()
        except WebDriverException as error:
            self.log(f"Ошибка Selenium: {error.msg or error}", "ERROR")
            self.status("Ошибка браузера")
        except Exception as error:
            if not self.stop_event.is_set():
                self.log(f"Ошибка: {error}", "ERROR")
                self.status("Ошибка")
        finally:
            if self.driver is not None:
                try:
                    self.driver.quit()
                except Exception:
                    pass
            self.driver = None
            self.events.put(("stopped", "Остановлен"))

    def _read_game_name(self) -> str:
        if self.driver is None:
            return ""
        try:
            return self.driver.find_element(By.CSS_SELECTOR, "span.status").text.strip()
        except (NoSuchElementException, StaleElementReferenceException):
            return ""

    def _moderation_loop(self) -> None:
        processed: set[str] = set()
        while not self.stop_event.is_set() and self.driver is not None:
            try:
                containers = self.driver.find_elements(By.CSS_SELECTOR, "div.item.pending")
                for container in containers:
                    if self.stop_event.is_set():
                        break
                    try:
                        if not container.is_displayed() or container.id in processed:
                            continue

                        user = container.find_element(By.CSS_SELECTOR, "p.name span").text.strip()
                        message = ""
                        is_image = False
                        try:
                            message = container.find_element(By.CSS_SELECTOR, "p.value").text.strip()
                        except NoSuchElementException:
                            try:
                                container.find_element(By.CSS_SELECTOR, "div.stage img")
                                is_image = True
                            except NoSuchElementException:
                                pass

                        if is_image:
                            reject = self.config.image_policy == "Отклонять"
                            reason = f"рисунок: политика «{self.config.image_policy.lower()}»"
                        else:
                            reject, reason = self.blacklists.should_reject(user, message)

                        selector = "button.reject" if reject else "button.accept"
                        container.find_element(By.CSS_SELECTOR, selector).click()
                        processed.add(container.id)
                        verdict = "ОТКЛОНЕНО" if reject else "ПРИНЯТО"
                        content = "[РИСУНОК]" if is_image else f"«{message}»"
                        self.log(f"{verdict} · {user}: {content} ({reason})")
                    except (NoSuchElementException, StaleElementReferenceException):
                        continue

                if len(processed) > 5000:
                    processed.clear()
                self.stop_event.wait(max(0.1, float(self.config.poll_interval)))
            except WebDriverException as error:
                if not self.stop_event.is_set():
                    self.log(f"Сбой чтения страницы: {error.msg or error}", "ERROR")
                    self.stop_event.wait(1.0)


class App:
    def __init__(self) -> None:
        self.root = Tk()
        self.root.title(f"{APP_NAME} {APP_VERSION}")
        self.root.geometry("640x560")
        self.root.minsize(540, 470)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        self.config = Config.load()
        self.events: queue.Queue[tuple[str, str]] = queue.Queue()
        self.moderator: Moderator | None = None
        self.worker: threading.Thread | None = None

        self.browser = StringVar(value=self.config.browser)
        self.url = StringVar(value=self.config.moderator_url)
        self.image_policy = StringVar(value=self.config.image_policy)
        self.status_text = StringVar(value="Остановлен")
        self.always_on_top = BooleanVar(value=False)

        self._build_ui()
        self.root.after(100, self._drain_events)

    def _build_ui(self) -> None:
        style = ttk.Style(self.root)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        style.configure("Title.TLabel", font=("Segoe UI Semibold", 20))
        style.configure("Status.TLabel", font=("Segoe UI Semibold", 10))
        style.configure("Community.TLabel", foreground="#2468b4", font=("Segoe UI", 9, "underline"))
        style.configure("TButton", padding=(12, 8))

        shell = ttk.Frame(self.root, padding=18)
        shell.pack(fill=BOTH, expand=True)

        header = ttk.Frame(shell)
        header.pack(fill=X, pady=(0, 12))
        ttk.Label(header, text="Sputnik Public", style="Title.TLabel").pack(side=LEFT)
        ttk.Label(header, textvariable=self.status_text, style="Status.TLabel").pack(side=RIGHT)

        community = ttk.Label(
            shell,
            text="Разрабатывается сообществом «Союз джекбоксеров»",
            style="Community.TLabel",
            cursor="hand2",
        )
        community.pack(anchor="w", pady=(0, 10))
        community.bind("<Button-1>", lambda _event: webbrowser.open(COMMUNITY_URL))

        settings = ttk.LabelFrame(shell, text="Настройки", padding=12)
        settings.pack(fill=X, pady=(0, 10))
        settings.columnconfigure(1, weight=1)

        ttk.Label(settings, text="Браузер").grid(row=0, column=0, sticky="w", padx=(0, 10), pady=4)
        ttk.Combobox(
            settings,
            textvariable=self.browser,
            values=("Edge", "Firefox"),
            state="readonly",
            width=16,
        ).grid(row=0, column=1, sticky="ew", pady=4)

        ttk.Label(settings, text="Страница модератора").grid(row=1, column=0, sticky="w", padx=(0, 10), pady=4)
        ttk.Entry(settings, textvariable=self.url).grid(row=1, column=1, sticky="ew", pady=4)

        ttk.Label(settings, text="Рисунки без ИИ").grid(row=2, column=0, sticky="w", padx=(0, 10), pady=4)
        ttk.Combobox(
            settings,
            textvariable=self.image_policy,
            values=("Принимать", "Отклонять"),
            state="readonly",
            width=16,
        ).grid(row=2, column=1, sticky="ew", pady=4)

        controls = ttk.Frame(shell)
        controls.pack(fill=X, pady=(0, 10))
        self.start_button = ttk.Button(controls, text="Запустить модерацию", command=self.start)
        self.start_button.pack(side=LEFT, fill=X, expand=True, padx=(0, 5))
        self.stop_button = ttk.Button(controls, text="Остановить", command=self.stop, state="disabled")
        self.stop_button.pack(side=LEFT, fill=X, expand=True, padx=(5, 0))

        options = ttk.Frame(shell)
        options.pack(fill=X, pady=(0, 8))
        ttk.Checkbutton(
            options,
            text="Поверх других окон",
            variable=self.always_on_top,
            command=lambda: self.root.attributes("-topmost", self.always_on_top.get()),
        ).pack(side=LEFT)
        ttk.Button(options, text="Сохранить настройки", command=self.save).pack(side=RIGHT)

        log_frame = ttk.LabelFrame(shell, text="Журнал", padding=8)
        log_frame.pack(fill=BOTH, expand=True)
        self.log_box = Text(
            log_frame,
            height=12,
            wrap="word",
            font=("Cascadia Mono", 9),
            relief="flat",
            padx=8,
            pady=8,
        )
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_box.yview)
        self.log_box.configure(yscrollcommand=scrollbar.set, state="disabled")
        scrollbar.pack(side=RIGHT, fill="y")
        self.log_box.pack(side=LEFT, fill=BOTH, expand=True)
        self._append_log("Готово. Выберите браузер и нажмите «Запустить модерацию».")

    def _current_config(self) -> Config:
        return Config(
            browser=self.browser.get(),
            moderator_url=self.url.get().strip() or Config.moderator_url,
            image_policy=self.image_policy.get(),
        )

    def save(self) -> None:
        self.config = self._current_config()
        try:
            self.config.save()
            self._append_log("Настройки сохранены в config.json.")
        except OSError as error:
            messagebox.showerror(APP_NAME, f"Не удалось сохранить настройки:\n{error}")

    def start(self) -> None:
        if self.worker is not None and self.worker.is_alive():
            return
        self.save()
        self.moderator = Moderator(self.config, self.events)
        self.worker = threading.Thread(target=self.moderator.run, daemon=True)
        self.worker.start()
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")

    def stop(self) -> None:
        if self.moderator is not None:
            self.moderator.stop()
        self.stop_button.configure(state="disabled")

    def _drain_events(self) -> None:
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == "log":
                    self._append_log(value)
                elif kind == "status":
                    self.status_text.set(value)
                elif kind == "stopped":
                    self.status_text.set(value)
                    self.start_button.configure(state="normal")
                    self.stop_button.configure(state="disabled")
        except queue.Empty:
            pass
        self.root.after(100, self._drain_events)

    def _append_log(self, line: str) -> None:
        self.log_box.configure(state="normal")
        self.log_box.insert(END, line + "\n")
        self.log_box.see(END)
        self.log_box.configure(state="disabled")

    def close(self) -> None:
        if self.moderator is not None:
            self.moderator.stop()
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    App().run()
