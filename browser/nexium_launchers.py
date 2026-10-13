"""Small user-owned launcher/search config; no account, shell or network service."""
import json,os,re,shutil,subprocess,ipaddress
from pathlib import Path
from urllib.parse import urlsplit,urlunsplit,quote_plus
ENGINES={'DuckDuckGo':('https://duckduckgo.com/','https://duckduckgo.com/?q='),'Bing':('https://www.bing.com/','https://www.bing.com/search?q=')}
BUILTINS=(('Nexium Browser',None),('Firefox','firefox-esr'),('Brave','brave-browser'))
def validate_url(value):
    value=value.strip()
    if not value or re.search(r'[\s\x00-\x1f\x7f]',value):raise ValueError('Enter a valid website URL without spaces.')
    if '://' not in value:value='https://'+value
    try:
        p=urlsplit(value);host=p.hostname;port=p.port
        if p.scheme not in ('https','http') or not host or p.username or p.password:raise ValueError()
        if host!='localhost':
            try:ipaddress.ip_address(host)
            except ValueError:
                ascii_host=host.encode('idna').decode('ascii')
                labels=ascii_host.split('.')
                if len(labels)<2 or not all(re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?',x) for x in labels) or len(labels[-1])<2:raise ValueError()
        return urlunsplit(p)
    except (ValueError,UnicodeError):raise ValueError('Use an http(s) website address, such as example.com.')
class LauncherStore:
    def __init__(self,path=None):
        self.path=Path(path) if path else Path.home()/'.config/nexium-browser/launchers.json'
        self.engine='DuckDuckGo';self.sites=[]
        if self.path.exists():
            data=json.loads(self.path.read_text())
            self.engine=data.get('search_engine','DuckDuckGo')
            if self.engine not in ENGINES:self.engine='DuckDuckGo'
            for entry in data.get('sites',[]):
                try:self.sites.append({'name':str(entry['name'])[:100],'url':validate_url(entry['url'])})
                except (ValueError,KeyError,TypeError):continue
    def save(self):
        self.path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
        tmp=self.path.with_suffix('.tmp');tmp.write_text(json.dumps({'version':1,'search_engine':self.engine,'sites':self.sites},indent=2)+'\n');tmp.chmod(0o600);os.replace(tmp,self.path)
    def add(self,url):
        url=validate_url(url)
        if any(s['url']==url for s in self.sites):return
        self.sites.append({'name':urlsplit(url).hostname,'url':url});self.save()
    def remove(self,index):
        self.sites.pop(index);self.save()
    def set_engine(self,engine):
        if engine not in ENGINES:raise ValueError('Unsupported search engine')
        self.engine=engine;self.save()
def make_url(text):
    text=text.strip();engine=LauncherStore().engine
    if not text:return ENGINES[engine][0]
    try:return validate_url(text)
    except ValueError:return ENGINES[engine][1]+quote_plus(text)
def chooser(owner):
    from PySide6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QListWidget,QPushButton,QInputDialog,QMessageBox,QLabel
    dialog=QDialog(owner);dialog.setWindowTitle('Nexium Browser chooser');dialog.resize(580,420)
    layout=QVBoxLayout(dialog);layout.addWidget(QLabel('Browsers and saved sites — websites open in Nexium Browser.'))
    items=QListWidget();items.setObjectName('launcherList');layout.addWidget(items)
    row=QHBoxLayout();buttons={}
    for name in ('Open','Add browser / Add site','Remove','Close'):
        b=QPushButton(name);row.addWidget(b);buttons[name]=b
    buttons['Add browser / Add site'].setObjectName('addSite');buttons['Remove'].setObjectName('removeSite');layout.addLayout(row)
    def refresh():
        items.clear()
        for name,exe in BUILTINS:items.addItem(name+(' (not installed)' if exe and not shutil.which(exe) else ''))
        for entry in owner.launchers.sites:items.addItem(entry['name']+' — '+entry['url'])
        items.setCurrentRow(0)
    def state():
        i=items.currentRow();buttons['Remove'].setEnabled(i>=len(BUILTINS))
        buttons['Open'].setEnabled(i>=0 and (i>=len(BUILTINS) or not BUILTINS[i][1] or bool(shutil.which(BUILTINS[i][1]))))
    def opened():
        i=items.currentRow()
        if i<0:return
        try:
            if i>=len(BUILTINS):owner.add_web_tab(owner.launchers.sites[i-len(BUILTINS)]['url'])
            elif BUILTINS[i][1]:subprocess.Popen([shutil.which(BUILTINS[i][1])],start_new_session=True)
            else:owner.add_home_tab()
            dialog.accept()
        except OSError as e:QMessageBox.warning(dialog,'Could not open browser',str(e))
    def added():
        value,ok=QInputDialog.getText(dialog,'Add browser / Add site','Website URL (https:// is added when missing):')
        if not ok:return
        try:owner.launchers.add(value);refresh()
        except (ValueError,OSError) as e:QMessageBox.warning(dialog,'Invalid site',str(e))
    def removed():
        i=items.currentRow()-len(BUILTINS)
        if i<0:return
        try:owner.launchers.remove(i);refresh()
        except OSError as e:QMessageBox.warning(dialog,'Could not save',str(e))
    items.currentRowChanged.connect(state);items.itemDoubleClicked.connect(opened)
    buttons['Open'].clicked.connect(opened);buttons['Add browser / Add site'].clicked.connect(added);buttons['Remove'].clicked.connect(removed);buttons['Close'].clicked.connect(dialog.reject)
    refresh();owner.chooser_dialog=dialog;dialog.show();return dialog
