import sys,tempfile,json,unittest,os
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'browser'))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from nexium_launchers import LauncherStore,validate_url,make_url
class ModelTests(unittest.TestCase):
    def test_urls(self):
        self.assertEqual(validate_url('example.com'),'https://example.com')
        for value in ('','garbage','not a url','javascript:alert(1)','ftp://example.com','https://','https://bad_host.com','https://x:password@example.com','https://example.com:bad'):
            with self.assertRaises(ValueError,msg=value):validate_url(value)
    def test_restart_remove_search(self):
        with tempfile.TemporaryDirectory() as home:
            old=os.environ.get('HOME');os.environ['HOME']=home
            try:
                a=LauncherStore();a.add('example.com');b=LauncherStore();self.assertEqual(b.sites[0]['url'],'https://example.com')
                self.assertIn('duckduckgo.com',make_url('two search words'))
                b.set_engine('Bing');self.assertIn('bing.com',make_url('two search words'))
                b.remove(0);self.assertEqual(LauncherStore().sites,[])
                self.assertEqual(LauncherStore().engine,'Bing')
                self.assertEqual(a.path.stat().st_mode & 0o777,0o600)
            finally:
                if old is None:os.environ.pop('HOME',None)
                else:os.environ['HOME']=old
if '--qt' not in sys.argv:unittest.main()
else:
    from PySide6.QtWidgets import QApplication,QInputDialog,QPushButton,QComboBox,QListWidget
    from unittest.mock import patch
    import nexium_browser
    app=QApplication([]);window=nexium_browser.NexiumBrowser();window.show()
    dialog=window.show_chooser();app.processEvents()
    assert dialog.findChild(QPushButton,'addSite') and window.findChild(QComboBox,'searchEngine').currentText()=='DuckDuckGo'
    with patch.object(QInputDialog,'getText',return_value=('example.com',True)):
        dialog.findChild(QPushButton,'addSite').click();app.processEvents()
    assert LauncherStore().sites[-1]['url']=='https://example.com'
    items=dialog.findChild(QListWidget,'launcherList');items.setCurrentRow(items.count()-1)
    dialog.findChild(QPushButton,'removeSite').click();app.processEvents();assert not LauncherStore().sites
    window.search_engine.setCurrentText('Bing');assert LauncherStore().engine=='Bing'
    window.search_engine.setCurrentText('DuckDuckGo')
    print('PASS real Qt chooser Add site/remove clicks, persistent reopen and DDG/Bing selection',flush=True)
    window.close()
