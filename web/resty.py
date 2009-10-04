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

try: from simplejson import dumps as json_encode, loads as json_decode
except ImportError: pass
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

debug = web.config.get('debug')

def json_it(fn):
    def f(*args, **kw):
        x = fn(*args, **kw)
        web.header('Content-Type', 'text/plain; charset=UTF-8')
        try:
            if x and (type(x) is not dict) \
                 and ((hasattr(x, '__iter__') or hasattr(x, 'next'))):
                x = list(x)

            yield json_encode(x)
        except:
            yield 'not json :(\n'
            yield x

    return f


class RestyError(Exception):
    def __init__(self, msg):
        self.msg = msg


class http_handler(object):
    # def __init__(self):
    #     pass

    @json_it
    def process(self, url):
        # web.debug('='*10)

        try:
            ctx = web.ctx
            
            if not url:
                raise RestyError('the url <%s> is not valid'%ctx.path)
            
            urlbits = url.split('/', 4)

            if (not urlbits) or ('' in urlbits):
                raise RestyError('the url <%s> is not valid'%ctx.path)
            
            query = cgi.parse_qs(ctx.env.get('QUERY_STRING', ''))\
                if ctx.query else {}

            if '_method' in query:
                ctx.method = query.pop('_method')[0]

            if ctx.method not in ('POST', 'GET', 'PUT', 'DELETE', 'HEAD'):
                raise RestyError('the method [%s] not allowed'%ctx.method)

            _callback = query.pop('_callback')[0]\
                if '_callback' in query else None

            cls_ = handlers.get(urlbits[0])

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


    GET = process
    POST = process
    PUT = process
    DELETE = process
    HEAD = process


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
                self.data = json_decode(_data)
                del _data
            else:
                self.data = None
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

        sql_what = '*'
        sql_where = []
        if urlbits[-2] != '~' and urlbits[-1] != '~':
            sql_where.append(tuple(urlbits[-2:]))

        if op_mode:
            sql_where = process_sql_op(sql_where, op_mode)
        else:
            sql_where = ['%s=%s'%s for s in sql_where if s]

        sql_where = ' AND '.join(['(%s)'%s for s in sql_where])

        return db.select(model, what=sql_what, where=sql_where or None, _test=True if '_t' in query else False)

    def POST_model_row(self):
        data = self.data

        if type(data) is dict:
            data = [data]

        if type(data) is not list:
            raise RestyError('data <%s> must be list or dict'%json_encode(data))

        for idx, d in enumerate(data):
            if 'id' in d:
                del d['id']
            if not d:
                del data[idx]

        return self.db.multiple_insert(self.model, data, seqname='id', _test=True if '_t' in self.query else False)


    def PUT_model_row(self):
        pass

    def DELETE_model_row(self):
        pass


handlers['model'] = Handler_model



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