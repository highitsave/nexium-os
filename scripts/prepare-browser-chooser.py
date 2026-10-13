import re,ast
from pathlib import Path
p=Path('browser/nexium_browser.py');s=p.read_text()
if 'from nexium_launchers import' not in s:
    s=s.replace('import sys','import sys\nfrom nexium_launchers import LauncherStore, ENGINES, make_url, chooser\nfrom PySide6.QtWidgets import QComboBox, QMessageBox',1)
    s=re.sub(r'^GOOGLE_(?:HOME|SEARCH|ACCOUNT) = .*\n','',s,flags=re.M)
    s=re.sub(r'class NexiumSearchPage\(QWebEnginePage\):.*?(?=class BrowserPage)', '',s,flags=re.S)
    s=s.replace('        self.web.loadFinished.connect(self.inject_nexium_search_ui)\n','')
    s=re.sub(r'    def inject_nexium_search_ui\(self, ok\):.*?(?=class NexiumHome)', '',s,flags=re.S)
    s=re.sub(r'def make_url\(text\):.*?(?=class )','',s,flags=re.S)
    s=s.replace('"Nexium Search uses Google to obtain web results while Nexium controls "\n            "the presentation layer. Search results may therefore be subject "\n            "to Google\'s availability and policies.<br><br>"','"Nexium Search uses DuckDuckGo by default, with Bing as an optional engine. "\n            "Search results remain subject to the selected provider\'s policies.<br><br>"')
    s=s.replace('self.sign_in_btn = QPushButton("Sign in")','self.sign_in_btn = QPushButton("Browsers / Add site")')
    s=s.replace('google_btn','search_home_btn').replace('QPushButton("Open Google")','QPushButton("Open search engine")')
    s=s.replace('self.navigate_callback(GOOGLE_HOME)','self.navigate_callback(make_url(""))')
    s=s.replace('menu.addAction("Google",','menu.addAction("DuckDuckGo",')
    s=s.replace('self.open_url(GOOGLE_HOME)','self.open_url("https://duckduckgo.com/")')
    s=s.replace('menu.addAction("YouTube", lambda: self.navigate_callback("https://www.youtube.com"))','menu.addAction("Bing", lambda: self.navigate_callback("https://www.bing.com/"))')
    s=s.replace('menu.addAction("YouTube", lambda: self.open_url("https://www.youtube.com"))','menu.addAction("Bing", lambda: self.open_url("https://www.bing.com/"))')
    s='\n'.join(line for line in s.splitlines() if 'menu.addAction("Gmail"' not in line)+'\n'
    s=s.replace('        self.dark_mode = False','        self.launchers = LauncherStore()\n        self.dark_mode = False',1)
    s=s.replace('self.shortcuts_button = QPushButton("Shortcuts")','self.shortcuts_button = QPushButton("Browsers / Add site")')
    s=s.replace('self.shortcuts_button.clicked.connect(self.show_shortcuts)','self.shortcuts_button.clicked.connect(self.show_chooser)')
    needle='        nav_layout.addWidget(self.shortcuts_button)'
    s=s.replace(needle,needle+'\n        self.search_engine = QComboBox()\n        self.search_engine.setObjectName("searchEngine")\n        self.search_engine.addItems(list(ENGINES))\n        self.search_engine.setCurrentText(self.launchers.engine)\n        self.search_engine.currentTextChanged.connect(self.change_engine)\n        nav_layout.addWidget(self.search_engine)')
    s=s.replace('        nav_layout.addWidget(self.sign_in)','        self.sign_in.hide()')
    s=s.replace('            self.sign_in_clicked,','            self.show_chooser,')
    s=re.sub(r'    def sign_in_clicked\(self\):.*?(?=    def profile_clicked)', '    def sign_in_clicked(self):\n        self.show_chooser()\n\n',s,flags=re.S)
    needle='    def make_tool_button(self, text, callback, tooltip):'
    s=s.replace(needle,'    def show_chooser(self):\n        return chooser(self)\n\n    def change_engine(self, engine):\n        try:self.launchers.set_engine(engine)\n        except OSError as e:QMessageBox.warning(self,"Could not save search engine",str(e))\n\n'+needle)
    s=s.replace('            app.nexium_window = window','            app.nexium_window = window\n            if "--chooser" in sys.argv:window.show_chooser()')
assert 'GOOGLE_' not in s and 'google.com/search' not in s and 'accounts.google.com' not in s and 'mail.google.com' not in s
assert 'class NexiumBrowser' in s and 'class NexiumHome' in s
ast.parse(s);compile(s,str(p),'exec');p.write_text(s)
print('PASS chooser/search source syntax; no Google home/search/account default')
