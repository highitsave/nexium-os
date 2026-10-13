import sys,json,os
from pathlib import Path
sys.path.insert(0,'/usr/local/lib/nexium')
from PySide6.QtWidgets import QApplication,QPushButton,QInputDialog,QListWidget,QMessageBox
from unittest.mock import patch
from nexium_launchers import LauncherStore
from nexium_browser import NexiumBrowser,BrowserPage
stage=sys.argv[1];app=QApplication([]);window=NexiumBrowser();window.show();app.processEvents()
config=Path.home()/'.config/nexium-browser/launchers.json'
assert os.getuid()!=0 and str(config).startswith('/home/nexium/')
source=Path('/usr/local/lib/nexium/nexium_browser.py').read_text()
for bad in ['GOOGLE_HOME','GOOGLE_SEARCH','google.com/search','accounts.google.com']:
    assert bad not in source,bad
dialog=window.show_chooser();app.processEvents();items=dialog.findChild(QListWidget,'launcherList')
if stage=='add':
    assert window.launchers.engine=='DuckDuckGo' and window.search_engine.currentText()=='DuckDuckGo'
    for bad in ['','garbage','javascript:alert(1)']:
        with patch.object(QInputDialog,'getText',return_value=(bad,True)),patch.object(QMessageBox,'warning') as warning:
            dialog.findChild(QPushButton,'addSite').click();app.processEvents();assert warning.called
    with patch.object(QInputDialog,'getText',return_value=('example.com/nexium-persistence-test',True)):
        dialog.findChild(QPushButton,'addSite').click();app.processEvents()
    assert LauncherStore().sites[-1]['url']=='https://example.com/nexium-persistence-test'
    window.search_engine.setCurrentText('Bing');assert LauncherStore().engine=='Bing'
    print('PASS actual Add-site click and validation; https prefix; home config saved; Bing selected',flush=True)
elif stage=='restart-remove':
    assert window.launchers.sites[-1]['url']=='https://example.com/nexium-persistence-test'
    assert window.search_engine.currentText()=='Bing'
    # Same saved site opens as a new in-app BrowserPage, never shell execution.
    window.add_web_tab(window.launchers.sites[-1]['url']);assert isinstance(window.current(),BrowserPage)
    assert window.current().web.url().toString()=='https://example.com/nexium-persistence-test'
    items.setCurrentRow(items.count()-1);dialog.findChild(QPushButton,'removeSite').click();app.processEvents()
    assert not LauncherStore().sites
    window.search_engine.setCurrentText('DuckDuckGo')
    print('PASS new app process loaded saved site and Bing; new in-app tab; actual Remove click persisted',flush=True)
else:
    assert not window.launchers.sites and window.search_engine.currentText()=='DuckDuckGo'
    print('PASS second restart confirms deletion and DuckDuckGo; no Google default',flush=True)
window.close();app.processEvents()
# Assertions have completed; avoid QtWebEngine profile teardown ordering noise in test driver.
sys.stdout.flush();sys.stderr.flush();os._exit(0)
