import webtest
import web
from web.resty import json_encode, json_decode

class RestyTest(webtest.TestCase):
    def setUp(self):
        def index():
            return 'index'

        urls = (
            "/", index,
        )
        app = web.application(urls)
        
        web.config.debug = True
        web.db = web.database(dbn='sqlite', db='../demo/db.sqlite3')
        web.config.resty_db = web.db

        web.register_resty(app)
        
        self.app = app
        self.browser = app.browser()
    
    def test_index(self):
        b = self.browser
        b.open('/')
        self.assertEquals(b.data, 'index')
    
    def test_resty_root(self):
        b = self.browser
        b.open('/=/')
        self.assert_(not json_decode(b.data).success)
        b.open('/=/model')
        self.assert_(json_decode(b.data).success)
        b.open('/=/model/~')
        b.open('/=/model/pp')
        b.open('/=/model/pp/1')
        b.open('/=/model/~/~')
    
    def test_model_row_get(self):
        b = self.browser
        b.open('/=/model/pp/id/2')
        self.assert_(b.data.startswith('['))

if __name__ == "__main__":
    webtest.main()
