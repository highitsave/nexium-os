import sys
from nexium_launchers import LauncherStore, ENGINES, make_url, chooser
from PySide6.QtWidgets import QComboBox, QMessageBox
from pathlib import Path
from urllib.parse import quote_plus

from PySide6.QtCore import Qt, QUrl, QTimer, Signal, QObject, Slot
from PySide6.QtGui import QColor, QPainter, QBrush, QShortcut, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QTabWidget,
    QToolButton,
    QFrame,
    QLabel,
    QMenu,
    QSizePolicy,
    QProgressBar,
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import (
    QWebEngineProfile,
    QWebEnginePage,
    QWebEngineUrlRequestInterceptor,
)





class NexiumLogo(QWidget):
    """Original dot-art Nexium emblem with a symmetrical sci-fi/HUD feel."""

    def __init__(self, parent=None, size=58):
        super().__init__(parent)
        self.size = size
        self.setFixedSize(size, size)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor("#b58cff")))

        s = self.size
        c = s / 2

        # Original mirrored dot pattern.
        pattern = [
            (0, -25), (0, -20), (0, -15), (0, -10), (0, -5),
            (-7, -20), (-13, -16), (-19, -10), (-24, -3),
            (-27, 3), (-21, 10), (-15, 16), (-8, 21),
            (7, -20), (13, -16), (19, -10), (24, -3),
            (27, 3), (21, 10), (15, 16), (8, 21),
            (-10, -3), (-6, -8), (6, -8), (10, -3),
            (-10, 3), (-6, 8), (6, 8), (10, 3),
            (-5, 0), (0, 0), (5, 0),
            (0, 10), (0, 15), (0, 20), (0, 25),
        ]

        scale = s / 58.0
        radius = max(1.45, 2.0 * scale)

        for x, y in pattern:
            x *= scale
            y *= scale
            painter.drawEllipse(
                c + x - radius,
                c + y - radius,
                radius * 2,
                radius * 2,
            )


class BootScreen(QWidget):
    ready = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Nexium Browser")
        self.setMinimumSize(650, 430)
        self.setObjectName("boot")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(10)

        layout.addStretch(2)

        logo_row = QHBoxLayout()
        logo_row.addStretch()
        logo_row.addWidget(NexiumLogo(self, 110))
        logo_row.addStretch()
        layout.addLayout(logo_row)

        title = QLabel("Nexium Browser")
        title.setObjectName("bootTitle")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        self.status = QLabel("Loading...")
        self.status.setObjectName("bootStatus")
        self.status.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(8)
        layout.addSpacing(18)
        layout.addWidget(self.progress)

        self.ready_label = QLabel("✓ Ready")
        self.ready_label.setObjectName("readyLabel")
        self.ready_label.setAlignment(Qt.AlignCenter)
        self.ready_label.hide()
        layout.addWidget(self.ready_label)

        self.credit = QLabel("Made with the founder of Nexium<br>and GPT")
        self.credit.setObjectName("credit")
        self.credit.setAlignment(Qt.AlignCenter)
        self.credit.hide()
        layout.addWidget(self.credit)

        layout.addStretch(3)

        self.setStyleSheet("""
            QWidget#boot {
                background: #0b0a12;
            }
            QLabel#bootTitle {
                color: #f4efff;
                font-size: 34px;
                font-weight: 700;
                margin-top: 10px;
            }
            QLabel#bootStatus {
                color: #b58cff;
                font-size: 15px;
            }
            QProgressBar {
                background: #211c2d;
                border: 1px solid #332b46;
                border-radius: 4px;
            }
            QProgressBar::chunk {
                background: #a879ff;
                border-radius: 4px;
            }
            QLabel#readyLabel {
                color: #c9a9ff;
                font-size: 22px;
                font-weight: 700;
                margin-top: 12px;
            }
            QLabel#credit {
                color: #888092;
                font-size: 13px;
                line-height: 150%;
            }
        """)

        self.progress_value = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.advance)
        self.timer.start(35)

    def advance(self):
        self.progress_value += 2
        self.progress.setValue(min(self.progress_value, 100))

        if self.progress_value >= 100:
            self.timer.stop()
            self.status.hide()
            self.progress.hide()
            self.ready_label.show()
            self.credit.show()
            QTimer.singleShot(1150, self.finish)

    def finish(self):
        self.ready.emit()


class NexiumRequestInterceptor(QWebEngineUrlRequestInterceptor):
    """
    Lightweight built-in network filter.

    It blocks a conservative set of common third-party ad/tracking hosts and
    known advertising request patterns. It intentionally does not attempt to
    defeat YouTube's DRM, authentication, or anti-abuse systems.
    """

    BLOCKED_HOST_PARTS = {
        "doubleclick.net",
        "googlesyndication.com",
        "googleadservices.com",
        "adservice.google.com",
        "ads.youtube.com",
        "pagead2.googlesyndication.com",
        "imasdk.googleapis.com",
        "adnxs.com",
        "adsrvr.org",
        "taboola.com",
        "outbrain.com",
    }

    BLOCKED_URL_PARTS = (
        "/pagead/",
        "/adsystem/",
        "/adservice/",
        "/doubleclick/",
        "/advertising/",
        "/tracking/",
    )

    def interceptRequest(self, info):
        url = info.requestUrl()
        host = url.host().lower()
        full_url = url.toString().lower()

        if any(part in host for part in self.BLOCKED_HOST_PARTS):
            info.block(True)
            return

        if any(part in full_url for part in self.BLOCKED_URL_PARTS):
            info.block(True)


class BrowserPage(QWidget):
    def __init__(self, url, profile):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.web = QWebEngineView()
        self.page = QWebEnginePage(profile, self.web)
        self.web.setPage(self.page)

        self.web.setUrl(QUrl(url))
        layout.addWidget(self.web)

class NexiumHome(QWidget):
    """Custom Nexium New Tab page."""

    def __init__(self, navigate_callback, theme_callback, login_callback, dark_mode=False):
        super().__init__()
        self.navigate_callback = navigate_callback
        self.theme_callback = theme_callback
        self.login_callback = login_callback
        self.dark_mode = dark_mode
        self.setObjectName("nexiumHome")

        root = QVBoxLayout(self)
        root.setContentsMargins(55, 35, 55, 55)
        root.setSpacing(0)

        # Top-right controls.
        top = QHBoxLayout()
        top.addStretch()

        self.shortcuts_btn = QPushButton("Shortcuts")
        self.shortcuts_btn.clicked.connect(self.open_shortcuts)
        top.addWidget(self.shortcuts_btn)

        self.theme_btn = QPushButton("☾ Theme")
        self.theme_btn.clicked.connect(self.theme_callback)
        top.addWidget(self.theme_btn)

        self.sign_in_btn = QPushButton("Browsers / Add site")
        self.sign_in_btn.clicked.connect(self.login_callback)
        top.addWidget(self.sign_in_btn)

        top.addWidget(NexiumLogo(self, 42))
        root.addLayout(top)

        root.addStretch(2)

        # Large centered logo.
        logo_row = QHBoxLayout()
        logo_row.addStretch()
        logo_row.addWidget(NexiumLogo(self, 112))
        logo_row.addStretch()
        root.addLayout(logo_row)

        title = QLabel("Nexium")
        title.setAlignment(Qt.AlignCenter)
        title.setObjectName("nexiumTitle")
        root.addWidget(title)

        subtitle = QLabel("Search the web with Nexium")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setObjectName("nexiumSubtitle")
        root.addWidget(subtitle)

        root.addSpacing(26)

        search_row = QHBoxLayout()
        search_row.addStretch()

        self.search = QLineEdit()
        self.search.setObjectName("homeSearch")
        self.search.setPlaceholderText("Search or type a URL")
        self.search.setMinimumWidth(620)
        self.search.setMaximumWidth(760)
        self.search.setMinimumHeight(52)
        self.search.returnPressed.connect(self.search_web)
        search_row.addWidget(self.search)

        search_row.addStretch()
        root.addLayout(search_row)

        root.addSpacing(18)

        buttons = QHBoxLayout()
        buttons.addStretch()

        search_btn = QPushButton("Nexium Search")
        search_btn.setObjectName("homeButton")
        search_btn.clicked.connect(self.search_web)
        buttons.addWidget(search_btn)

        search_home_btn = QPushButton("Open search engine")
        search_home_btn.setObjectName("homeButton")
        search_home_btn.clicked.connect(lambda: self.navigate_callback(make_url("")))
        buttons.addWidget(search_home_btn)

        buttons.addStretch()
        root.addLayout(buttons)

        root.addStretch(3)
        self.apply_theme(dark_mode)

    def search_web(self):
        text = self.search.text().strip()
        if text:
            self.navigate_callback(make_url(text))

    def open_shortcuts(self):
        menu = QMenu(self)
        menu.addAction("DuckDuckGo", lambda: self.navigate_callback(make_url("")))
        menu.addAction("Bing", lambda: self.navigate_callback("https://www.bing.com/"))
        menu.addSeparator()
        menu.addSeparator()
        menu.addAction("Terms of Service", self.show_terms)
        menu.exec(self.shortcuts_btn.mapToGlobal(self.shortcuts_btn.rect().bottomLeft()))

    def show_terms(self):
        dialog = NexiumTermsDialog(self.window())
        dialog.show()
        self.terms_dialog = dialog

    def apply_theme(self, dark_mode):
        self.dark_mode = dark_mode
        self.theme_btn.setText("☀ Theme" if dark_mode else "☾ Theme")


class NexiumBrowser(QMainWindow):
    def __init__(self):
        super().__init__()
        self.launchers = LauncherStore()
        self.dark_mode = False
        self.logged_in = False
        self.setWindowTitle("Nexium Browser")

        # One shared Chromium profile keeps cookies/session data consistent
        # between tabs and lets Nexium apply its network filter centrally.
        storage = Path.home() / ".local/share/nexium-browser"
        cache = Path.home() / ".cache/nexium-browser"
        storage.mkdir(parents=True, exist_ok=True)
        cache.mkdir(parents=True, exist_ok=True)
        self.profile = QWebEngineProfile("nexium", self)
        self.profile.setPersistentStoragePath(str(storage))
        self.profile.setCachePath(str(cache))
        self.profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies)
        self.request_interceptor = NexiumRequestInterceptor(self.profile)
        self.profile.setUrlRequestInterceptor(self.request_interceptor)

        self.resize(1280, 820)
        self.setMinimumSize(900, 600)

        central = QWidget()
        central.setObjectName("central")
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Chrome-style tab strip.
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.setDocumentMode(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.tab_changed)

        # + button for a new tab.
        self.new_tab_button = QToolButton()
        self.new_tab_button.setText("+")
        self.new_tab_button.setToolTip("New tab")
        self.new_tab_button.setAutoRaise(True)
        self.new_tab_button.clicked.connect(self.add_home_tab)
        self.tabs.setCornerWidget(self.new_tab_button, Qt.TopRightCorner)

        root.addWidget(self.tabs)

        # Navigation bar.
        nav = QFrame()
        nav.setObjectName("nav")
        nav_layout = QHBoxLayout(nav)
        nav_layout.setContentsMargins(14, 8, 14, 8)
        nav_layout.setSpacing(5)

        self.back_button = self.make_tool_button("←", self.go_back, "Back")
        self.forward_button = self.make_tool_button("→", self.go_forward, "Forward")
        self.reload_button = self.make_tool_button("⟳", self.reload_page, "Reload")

        nav_layout.addWidget(self.back_button)
        nav_layout.addWidget(self.forward_button)
        nav_layout.addWidget(self.reload_button)

        self.address = QLineEdit()
        self.address.setObjectName("address")
        self.address.setPlaceholderText("Search or type a URL")
        self.address.returnPressed.connect(self.navigate)
        nav_layout.addWidget(self.address, 1)

        self.shortcuts_button = QPushButton("Browsers / Add site")
        self.shortcuts_button.clicked.connect(self.show_chooser)
        nav_layout.addWidget(self.shortcuts_button)
        self.search_engine = QComboBox()
        self.search_engine.setObjectName("searchEngine")
        self.search_engine.addItems(list(ENGINES))
        self.search_engine.setCurrentText(self.launchers.engine)
        self.search_engine.currentTextChanged.connect(self.change_engine)
        nav_layout.addWidget(self.search_engine)

        self.theme_button = QPushButton("☾")
        self.theme_button.setToolTip("Toggle theme")
        self.theme_button.clicked.connect(self.toggle_theme)class NexiumTermsDialog(QWidget):
    """Terms of Service screen shown before first use."""

    accepted = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nexium Browser — Terms of Service")
        self.setWindowModality(Qt.ApplicationModal)
        self.setMinimumSize(720, 570)
        self.setObjectName("terms")

        root = QVBoxLayout(self)
        root.setContentsMargins(34, 30, 34, 30)
        root.setSpacing(14)

        title_row = QHBoxLayout()
        title_row.addWidget(NexiumLogo(self, 52))

        title_box = QVBoxLayout()
        title = QLabel("Nexium Browser")
        title.setStyleSheet("font-size: 26px; font-weight: 700;")
        subtitle = QLabel("Terms of Service")
        subtitle.setStyleSheet("font-size: 14px; color: #77717f;")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        title_row.addLayout(title_box)
        title_row.addStretch()
        root.addLayout(title_row)

        body = QLabel(
            "<b>Welcome to Nexium Browser.</b><br><br>"
            "By using Nexium Browser, you agree to use it lawfully and respect "
            "the terms, policies, and intellectual-property rights of websites "
            "you visit.<br><br>"
            "Nexium Browser is provided as-is. Website content, accounts, search "
            "results, and third-party services remain controlled by their "
            "respective providers.<br><br>"
            "Search engines can be selected in the browser. DuckDuckGo is the "
            "default; Bing is also available. Search results and availability "
            "are controlled by their respective providers.<br><br>"
            "Nexium Browser includes an optional built-in network filter intended "
            "to block common advertising and tracking requests. It is not "
            "guaranteed to block every advertisement, and websites may change "
            "their delivery methods.<br><br>"
            "Do not use Nexium Browser to violate applicable law, compromise "
            "systems, abuse services, or infringe another person's rights."
        )
        body.setWordWrap(True)
        body.setTextInteractionFlags(Qt.TextSelectableByMouse)
        root.addWidget(body, 1)

        notice = QLabel(
            "These terms are a project-level notice and are not legal advice."
        )
        notice.setStyleSheet("color: #8b8494; font-size: 12px;")
        root.addWidget(notice)

        buttons = QHBoxLayout()
        buttons.addStretch()

        decline = QPushButton("Exit")
        decline.clicked.connect(QApplication.quit)

        accept = QPushButton("I Agree")
        accept.setObjectName("termsAccept")
        accept.clicked.connect(self.accept_terms)

        buttons.addWidget(decline)
        buttons.addWidget(accept)
        root.addLayout(buttons)

        self.setStyleSheet("""
            QWidget#terms {
                background: #ffffff;
                color: #202124;
            }
            QPushButton {
                border: 0;
                border-radius: 8px;
                padding: 10px 20px;
                background: #f1edf7;
                color: #3c3150;
            }
            QPushButton:hover {
                background: #e8dff5;
            }
            QPushButton#termsAccept {
                background: #9c72e9;
                color: white;
                font-weight: 700;
            }
            QPushButton#termsAccept:hover {
                background: #895bdc;
            }
        """)

    def accept_terms(self):
        self.accepted.emit()
        self.close()


class BrowserPage(QWidget):
        nav_layout.addWidget(self.theme_button)

        self.sign_in = QPushButton("Sign in")
        self.sign_in.clicked.connect(self.sign_in_clicked)
        self.sign_in.hide()

        self.profile_button = QPushButton("●")
        self.profile_button.setObjectName("profile")
        self.profile_button.setToolTip("Nexium profile")
        self.profile_button.setFixedSize(36, 36)
        self.profile_button.clicked.connect(self.profile_clicked)
        self.profile_button.hide()
        nav_layout.addWidget(self.profile_button)

        nav_layout.addWidget(NexiumLogo(self, 38))
        root.addWidget(nav)

        self.setCentralWidget(central)

        # Browser shortcuts.
        QShortcut(QKeySequence("Ctrl+L"), self, activated=self.focus_address)
        QShortcut(QKeySequence("Ctrl+T"), self, activated=self.add_home_tab)
        QShortcut(QKeySequence("Ctrl+W"), self, activated=self.close_current_tab)
        QShortcut(QKeySequence("Ctrl+R"), self, activated=self.reload_page)

        self.apply_theme()
        self.add_home_tab()

    def show_chooser(self):
        return chooser(self)

    def change_engine(self, engine):
        try:self.launchers.set_engine(engine)
        except OSError as e:QMessageBox.warning(self,"Could not save search engine",str(e))

    def make_tool_button(self, text, callback, tooltip):
        button = QToolButton()
        button.setText(text)
        button.setToolTip(tooltip)
        button.setFixedSize(36, 36)
        button.clicked.connect(callback)
        return button

    def add_home_tab(self):
        home = NexiumHome(
            self.open_url,
            self.toggle_theme,
            self.show_chooser,
            self.dark_mode,
        )
        index = self.tabs.addTab(home, "New Tab")
        self.tabs.setCurrentIndex(index)
        self.address.clear()

    def add_web_tab(self, url):
        page = BrowserPage(url, self.profile)
        index = self.tabs.addTab(page, "Loading...")
        self.tabs.setCurrentIndex(index)

        page.web.titleChanged.connect(
            lambda title, p=page: self.update_title(p, title)
        )
        page.web.urlChanged.connect(
            lambda qurl, p=page: self.update_url(p, qurl)
        )
        page.web.loadFinished.connect(
            lambda ok, p=page: self.update_load_state(p, ok)
        )

    def open_url(self, url):
        self.add_web_tab(url)

    def current(self):
        return self.tabs.currentWidget()

    def update_title(self, page, title):
        index = self.tabs.indexOf(page)
        if index >= 0:
            clean_title = (title or "New Tab").strip()
            self.tabs.setTabText(index, clean_title[:28])

    def update_url(self, page, url):
        if page is self.current():
            self.address.setText(url.toString())

    def update_load_state(self, page, ok):
        if not ok:
            self.update_title(page, "Page error")

    def tab_changed(self, index):
        widget = self.current()

        if isinstance(widget, BrowserPage):
            self.address.setText(widget.web.url().toString())
        else:
            self.address.clear()
            if isinstance(widget, NexiumHome):
                widget.apply_theme(self.dark_mode)

        self.update_navigation_buttons()

    def update_navigation_buttons(self):
        widget = self.current()
        is_browser = isinstance(widget, BrowserPage)

        self.back_button.setEnabled(is_browser)
        self.forward_button.setEnabled(is_browser)
        self.reload_button.setEnabled(is_browser)

        if is_browser:
            self.back_button.setEnabled(widget.web.history().canGoBack())
            self.forward_button.setEnabled(widget.web.history().canGoForward())

    def navigate(self):
        text = self.address.text().strip()
        if not text:
            return

        url = make_url(text)
        widget = self.current()

        if isinstance(widget, BrowserPage):
            widget.web.setUrl(QUrl(url))
        else:
            self.open_url(url)

    def focus_address(self):
        self.address.setFocus()
        self.address.selectAll()

    def go_back(self):
        widget = self.current()
        if isinstance(widget, BrowserPage):
            widget.web.back()
            self.update_navigation_buttons()

    def go_forward(self):
        widget = self.current()
        if isinstance(widget, BrowserPage):
            widget.web.forward()
            self.update_navigation_buttons()

    def reload_page(self):
        widget = self.current()
        if isinstance(widget, BrowserPage):
            widget.web.reload()

    def show_shortcuts(self):
        menu = QMenu(self)
        menu.addAction("DuckDuckGo", lambda: self.open_url("https://duckduckgo.com/"))
        menu.addAction("Nexium Search", lambda: self.focus_address())
        menu.addAction("Bing", lambda: self.open_url("https://www.bing.com/"))
        menu.addSeparator()
        menu.addSeparator()
        ad_action = menu.addAction("Built-in ad/tracker blocking: ON")
        ad_action.setEnabled(False)
        menu.addAction("Terms of Service", self.show_terms)
        menu.exec(
            self.shortcuts_button.mapToGlobal(
                self.shortcuts_button.rect().bottomLeft()
            )
        )

    def show_terms(self):
        dialog = NexiumTermsDialog(self)
        dialog.show()
        self.terms_dialog = dialog

    def sign_in_clicked(self):
        self.show_chooser()

    def profile_clicked(self):
        menu = QMenu(self)
        menu.addAction("Nexium Profile")
        menu.addSeparator()
        menu.addAction("Sign out", self.sign_out)
        menu.exec(self.profile_button.mapToGlobal(self.profile_button.rect().bottomLeft()))

    def sign_out(self):
        self.profile.cookieStore().deleteAllCookies()
        self.profile.clearHttpCache()
        self.logged_in = False
        self.profile_button.hide()
        self.sign_in.show()

    def toggle_theme(self):
        self.dark_mode = not self.dark_mode
        self.apply_theme()

        current = self.current()
        if isinstance(current, NexiumHome):
            current.apply_theme(self.dark_mode)

    def close_current_tab(self):
        index = self.tabs.currentIndex()
        if index >= 0:
            self.close_tab(index)

    def close_tab(self, index):
        widget = self.tabs.widget(index)
        if widget is None:
            return

        self.tabs.removeTab(index)
        widget.deleteLater()

        # Always keep at least one tab open.
        if self.tabs.count() == 0:
            self.add_home_tab()

    def apply_theme(self):
        if self.dark_mode:
            self.setStyleSheet("""
                QWidget#central {
                    background: #101018;
                }
                QTabWidget::pane {
                    border: 0;
                    background: #101018;
                }
                QTabBar {
                    background: #0b0b10;
                }
                QTabBar::tab {
                    background: #1d1d27;
                    color: #a7a7b2;
                    padding: 9px 20px;
                    min-width: 125px;
                    border-top-left-radius: 9px;
                    border-top-right-radius: 9px;
                    margin-right: 2px;
                }
                QTabBar::tab:selected {
                    background: #101018;
                    color: #f3f1f8;
                }
                QFrame#nav {
                    background: #101018;
                    border-bottom: 1px solid #2b2b38;
                }
                QLineEdit#address {
                    background: #22222e;
                    border: 1px solid #2c2c39;
                    border-radius: 22px;
                    padding: 9px 17px;
                    color: #f1eff6;
                    font-size: 14px;
                }
                QLineEdit#address:focus {
                    background: #292936;
                    border: 1px solid #62527e;
                }
                QPushButton, QToolButton {
                    background: transparent;
                    border: 0;
                    color: #e9e6ef;
                    padding: 8px 10px;
                    font-size: 13px;
                }
                QPushButton:hover, QToolButton:hover {
                    background: #242431;
                    border-radius: 8px;
                }
                QWidget#nexiumHome {
                    background: #101018;
                }
                QLabel#nexiumTitle {
                    color: #f4f1f8;
                    font-size: 52px;
                    font-weight: 600;
                    margin-top: 8px;
                }
                QLabel#nexiumSubtitle {
                    color: #a4a1ab;
                    font-size: 15px;
                    margin-top: 2px;
                }
                QLineEdit#homeSearch {
                    background: #1d1d27;
                    border: 1px solid #373641;
                    border-radius: 28px;
                    padding: 8px 22px;
                    color: #f1eff6;
                    font-size: 16px;
                }
                QPushButton#homeButton {
                    background: #22222d;
                    border: 1px solid #30303d;
                    border-radius: 7px;
                    padding: 10px 18px;
                    color: #ece9f2;
                    font-size: 14px;
                }
                QPushButton#homeButton:hover {
                    border: 1px solid #66517f;
                    background: #292936;
                }
                QPushButton#profile {
                    border-radius: 18px;
                    background: #2b2140;
                    color: #c9a9ff;
                }
            """)
            self.theme_button.setText("☀")
            self.theme_button.setToolTip("Switch to light mode")
        else:
            self.setStyleSheet("""
                QWidget#central {
                    background: #ffffff;
                }
                QTabWidget::pane {
                    border: 0;
                    background: white;
                }
                QTabBar {
                    background: #101114;
                }
                QTabBar::tab {
                    background: #25262a;
                    color: #b9bbc2;
                    padding: 9px 20px;
                    min-width: 125px;
                    border-top-left-radius: 9px;
                    border-top-right-radius: 9px;
                    margin-right: 2px;
                }
                QTabBar::tab:selected {
                    background: #ffffff;
                    color: #202124;
                }
                QFrame#nav {
                    background: #ffffff;
                    border-bottom: 1px solid #dadce0;
                }
                QLineEdit#address {
                    background: #f1f3f4;
                    border: 1px solid #f1f3f4;
                    border-radius: 22px;
                    padding: 9px 17px;
                    color: #202124;
                    font-size: 14px;
                }
                QLineEdit#address:focus {
                    background: #ffffff;
                    border: 1px solid #c7c7c7;
                }
                QPushButton, QToolButton {
                    background: transparent;
                    border: 0;
                    color: #202124;
                    padding: 8px 10px;
                    font-size: 13px;
                }
                QPushButton:hover, QToolButton:hover {
                    background: #f1f3f4;
                    border-radius: 8px;
                }
                QWidget#nexiumHome {
                    background: #ffffff;
                }
                QLabel#nexiumTitle {
                    color: #202124;
                    font-size: 52px;
                    font-weight: 600;
                    margin-top: 8px;
                }
                QLabel#nexiumSubtitle {
                    color: #70757a;
                    font-size: 15px;
                    margin-top: 2px;
                }
                QLineEdit#homeSearch {
                    background: #ffffff;
                    border: 1px solid #dfe1e5;
                    border-radius: 28px;
                    padding: 8px 22px;
                    color: #202124;
                    font-size: 16px;
                }
                QPushButton#homeButton {
                    background: #f8f9fa;
                    border: 1px solid #f8f9fa;
                    border-radius: 7px;
                    padding: 10px 18px;
                    color: #202124;
                    font-size: 14px;
                }
                QPushButton#homeButton:hover {
                    border: 1px solid #dadce0;
                    background: #f1f3f4;
                }
                QPushButton#profile {
                    border-radius: 18px;
                    background: #ede7ff;
                    color: #7048c8;
                }
            """)
            self.theme_button.setText("☾")
            self.theme_button.setToolTip("Switch to dark mode")

        # Update all existing Nexium home pages.
        for i in range(self.tabs.count()):
            widget = self.tabs.widget(i)
            if isinstance(widget, NexiumHome):
                widget.apply_theme(self.dark_mode)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Nexium Browser")

    # Terms are shown once per launch. The user must explicitly accept them
    # before the browser window is opened.
    terms = NexiumTermsDialog()
    app.nexium_terms = terms

    def start_boot():
        terms.close()

        boot = BootScreen()
        app.nexium_boot = boot
        boot.show()

        def launch_browser():
            boot.close()
            boot.deleteLater()

            window = NexiumBrowser()
            window.show()
            app.nexium_window = window
            if "--chooser" in sys.argv:window.show_chooser()

        boot.ready.connect(launch_browser)

    terms.accepted.connect(start_boot)
    terms.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
