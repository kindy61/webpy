import web
from web.resty import json_encode, json_decode

def run_test(d):
    """test resty api"""
    
    def index():
        return 'index'

    urls = (
        "/", index,
    )
    app = web.application(urls)
    
    web.config.debug = False
    web.db = web.database(dbn='sqlite', db='../demo/db.sqlite3')
    web.config.resty_db = web.db

    web.register_resty(app)
    
    req = app.request
    
    t_op = {
        'json_m': lambda g, p: g == json_encode(p),
    }
    
    print '-- test start --'
    for idx, t in enumerate(d):
        idx += 1
        t = web.storage(t)
        m, url = t.req
    
        # request(localpart='/',method='GET',data=None,host="0.0.0.0:8080",headers=None):
        
        r = req(url, m)
        
        resp = t.resp
        op = t_op.get(resp[0])
        p = resp[1]
        if op:
            tname = 'test %04d %%s  %s'%(idx, t.get('name', 'test %d'%idx))
            if op(getattr(r, p) if p else r, *resp[2:]):
                print tname%'ok'
            else:
                print tname%'not ok'
    
    print '-- test done --'
    

main_test = [
{
    'name': '',
    'req': ('GET', '/=/model/pp/id/2'),
    'resp': ('json_m', 'data', [{"body": None, "id": 2, "title": "p2"}]),
},
]
# b.open('/=/')
# b.open('/=/model')
# b.open('/=/model/~')
# b.open('/=/model/pp')
# b.open('/=/model/pp/1')
# b.open('/=/model/~/~')


if __name__ == "__main__":
    run_test(main_test)

