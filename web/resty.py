"""
REST the DB&maybe more resource
(idea from openresty)
"""

__all__ = [
  "register_resty", 
]

import cgi #, sys, os, threading, urllib, urlparse
# Table, Column, Index from trac <trac.edgewall.org>
from trac.db.schema import Table, Column, Index

from simplejson import dumps as json_encode, loads as json_decode
from yaml import dump as _yaml_encode, load as yaml_decode
yaml_encode = lambda d, default_flow_style=False: _yaml_encode(d, default_flow_style=default_flow_style)
import net, utils, webapi as web

config = web.config
"""
 * resty_db - default resty db
 * resty_allow_get_do_all_method - allow get to do 
    GET/HEAD/POST/PUT/DELETE? default is False
"""


def register_resty(app, url=None):
    """register the resty on an application"""
    if url is None:
        url = '='

    urlp = r'/%s/(.*)$'%url
    # web.debug('+'*10, register_resty, url, urlp)
    app.add_mapping(urlp, http_handler)

debug = config.get('debug', False)

get_encoder = lambda t: {'j': json_encode, 'json': json_encode, 'y': yaml_encode, 'yaml': yaml_encode}.get(t, json_encode)

def output_it(fn):
    def f(*args, **kw):
        x = fn(*args, **kw)
        web.header('Content-Type', 'text/plain; charset=UTF-8')
        try:
            if x and (type(x) is not dict) \
                 and ((hasattr(x, '__iter__') or hasattr(x, 'next'))):
                x = list(x)

            yield get_encoder(web.ctx._out_format)(x)
        except:
            yield 'not json :(\n'
            yield x

    return f


class RestyError(Exception):
    def __init__(self, msg):
        self.msg = msg


@output_it
def http_handler(url):
    try:
        ctx = web.ctx
        
        if not url:
            raise RestyError('the url <%s> is not valid'%ctx.path)
        
        urlbits = url.strip('/').split('/', 3)
        
        if (not urlbits) or ('' in urlbits):
            raise RestyError('the url <%s> is not valid'%ctx.path)
        
        lstBit = urlbits[-1]
        if lstBit and '.' in lstBit:
            urlbits[-1], ctx._out_format = lstBit.rsplit('.', 1)
        else:
            ctx._out_format = 'j'

        query = cgi.parse_qs(ctx.env.get('QUERY_STRING', ''))\
            if ctx.query else {}

        if '_method' in query:
            ctx.method = query.pop('_method')[0]

        if ctx.method not in ('POST', 'GET', 'PUT', 'DELETE', 'HEAD'):
            raise RestyError('the method [%s] not allowed'%ctx.method)

        _callback = query.pop('_callback')[0]\
            if '_callback' in query else None

        cls_ = handlers.get(urlbits[0])
        
        if not cls_:
            raise RestyError('module <%s> not exist'%urlbits[0])

        hdl = cls_(ctx, query, urlbits, web.config.get('resty_db'))

        return hdl.run()

    except RestyError, ex:
        return { 'success': False, 'error': ex.msg }
    
    except:
        if debug:
            import debugerror
            raise debugerror.debugerror()
        else:
            return { 'success': False, 'error': 'unknow' }


handlers = {}

class Handler_model(object):

    def __init__(self, ctx, query, urlbits, db=None):
        utils.autoassign(self, locals())
        self.model = urlbits[1]
        self.op_mode = int(query.pop('_op', ['0'])[0])
        
        if ctx.method in ('POST', 'PUT'):
            if '_data' in query:
                # web.debug('~', query.get('_data'))
                _data = query.pop('_data')[0]
            else:
                _data = web.data()
            if _data:
                try: self.data = json_decode(_data)
                except: raise RestyError('data is invalid')
                del _data
            else:
                raise RestyError('no data!')
        else:
            self.data = None

    def run(self):
        lvl = ['model_list', 'model', 'model_column', \
            'model_row'][(len(self.urlbits) - 1):]

        if not lvl:
            raise RestyError('have no method match url %s'%('/'.join(self.urlbits)))

        lvl = lvl[0]

        method_name = '%s_%s'%(self.ctx.method, lvl)

        if not hasattr(self, method_name):
            raise RestyError('have no %s method match url %s'%(self.ctx.method, '/'.join(self.urlbits)))

        method = getattr(self, method_name)
        # web.debug('match method %s.%s'%(self.__class__, method_name))
        return method()

    def DELETE_model_list(self):
        pass

    def GET_model_list(self):
        pass

    def GET_model(self):
        pass

    def POST_model(self):
        pass

    def DELETE_model(self):
        pass

    def GET_model_column(self):
        pass

    def POST_model_column(self):
        pass

    def PUT_model_column(self):
        pass

    def DELETE_model_column(self):
        pass

    def GET_model_row(self):
        urlbits = self.urlbits
        query = self.query
        db = self.db

        model = self.model
        op_mode = self.op_mode

        if urlbits[-2] != '~' and urlbits[-1] != '~':
            query.setdefault(urlbits[-2], []).insert(0, urlbits[-1])

        return db.select_with_op(model, query, op_mode=op_mode)


    def POST_model_row(self):
        data = self.data
        query = self.query

        if type(data) is dict:
            data = [data]

        if type(data) is not list:
            raise RestyError('data <%s> must be list or dict'%json_encode(data))

        _test = False
        if '_test' in query:
            _test = query.pop('_test')[0]
        
        data_ = []
        for idx, d in enumerate(data):
            d = dict([(str(k),v) for k,v in d.items()])
            
            if 'id' in d:
                del d['id']
            if d:
                data_.append(d)
        del data
        
        if not data_:
            raise RestyError('data is invalid')

        return self.db.multiple_insert(self.model, data_, seqname='id', _test=_test)


    def PUT_model_row(self):
        data = self.data
        query = self.query
        db = self.db
        urlbits = self.urlbits
        
        if urlbits[-2] != '~' and urlbits[-1] != '~':
            query.setdefault(urlbits[-2], []).insert(0, urlbits[-1])

        where = {}
        for k in query.keys():
            if k and k[0] != '_':
                where[k] = query.pop(k)
        if where:
            where = db._op_expand_where(where, op_mode=self.op_mode)
        if not where:
            raise RestyError('you must give the where')

        if type(data) is list:
            data = data[0]

        if type(data) is not dict:
            raise RestyError('data <%s> must be dict or 1 item list'%json_encode(data))

        _test = False
        if '_test' in query:
            _test = query.pop('_test')[0]

        data = dict([(str(k),v) for k,v in data.items() if str(k)!='id'])
        
        if not data:
            raise RestyError('data is invalid')

        return db.update(self.model, where=where, _test=_test, **data)


    def DELETE_model_row(self):
        query = self.query
        db = self.db
        urlbits = self.urlbits
        
        if urlbits[-2] != '~' and urlbits[-1] != '~':
            query.setdefault(urlbits[-2], []).insert(0, urlbits[-1])

        where = {}
        for k in query.keys():
            if k and k[0] != '_':
                where[k] = query.pop(k)
        if where:
            where = db._op_expand_where(where, op_mode=self.op_mode)
        if not where:
            raise RestyError('you must give the where')

        _test = False
        if '_test' in query:
            _test = query.pop('_test')[0]

        return db.delete(self.model, where=where, _test=_test)


handlers['model'] = Handler_model


"""
ok(exp, name=None)
is(got, expected, name=None)
isnt(got, expected, name=None)
like(got, expected, name=None) use expect as regex
unlike(got, expected, name=None)
cmp_ok(got, op, expected, name=None);
can_ok()
    ~ hasattr_ok()
isa_ok()
    ~ isinstance_ok()
new_ok()
subtest(function, name)
    function contain the tests
pass ~ ok(1)
fail ~ ok(0)
use_ok()
    ~ import_ok(package, module=None, name=None)
is_deeply(got, expected, name=None) compare by walk through
diag(*msgs)
? note(*msgs)
explain(obj)
    ~ just like repr

if XX: skip(why, how_many)
todo
todo_skip
"""

"""
== API

GET/HEAD
POST/PUT/DELETE

method can be modify by _method, 
by default, only HEAD&DELETE can be send by GET use _method, 
PUT&POST must be send by POST unless webapi.config.resty_get_allow_method is setup.


web.resty
web.ctx.resty

magic query param:
 * _method  - change http method
 * _data    - setup the post data in query, post data will be ignore
 * _callback
 
 * _charset
 * _job
 * _callback_tpl
 * _use_cookie
 * _session

- model row special:
 * _cols
 * _order_by
 * _group_by
 * _limit


handlers:
 * model - select/insert/update/delete single table
    _maybe_ multi-table select
 * query - user-define sql, just excuted with vars
    just use web.db.query's $xx for var define
 
 * batch
    ????? how ?????


 * request dispatcher
 * sql select where builder
"""