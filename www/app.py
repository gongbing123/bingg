#!/usr/bin/env python3
#-*- coding:utf-8 -*-
import logging;logging.basicConfig(level=logging.INFO)
import asyncio,os,orm,time,json

from aiohttp import web
from jinja2 import Environment,FileSystemLoader
from config import configs
from coroweb import add_routes
from datetime import datetime

async def logger_factory(app,handler):
    async def logger(request):
        logging.info('Request:%s %s'%(request.method,request.path))
        return await handler(request)
    return logger

async def response_factory(app,handler):
    async def response(request):
        r=await handler(request)
        if isinstance(r,web.StreamResponse):
            return r
        if isinstance(r,bytes):
            resp=web.Response(body=r)
            resp.content_type='application/octet-stream'
            return resp
        if isinstance(r,str):
            if r.startswith('redirect:'):
                return web.HTTPFound(r[9:])
            resp=web.Response(body=r.encode('utf-8'))
            resp.content_type='text/html;charset=utf-8'
            return resp
        if isinstance(r,int)and r>=100 and r<600:
            resp=web.Response(r)
            return resp
        if isinstance(r,tuple)and len(r)==2:
            a,b=r
            if isinstance(a,int)and a>=100 and a<600:
                resp=web.Response(a,str(b))
                return resp
        if isinstance(r,dict):
            template=r.get('__template__')
            if template is None:
                resp=web.Response(body=json.dump(r,ensure_ascii=False,default=lambda o:o.__dict__).encode('utf-8'))
                resp.content_type='application/json;charset=utf-8'
            else:
                resp=web.Response(body=app['__templating__'].get_template(template).render(**r).encode('utf-8'))
                resp.content_type='text/html;charset=utf-8'
                return resp
        resp=web.Response(body=str(r).encode('utf-8'))
        resp.content_type='text/plain;charset=utf-8'
        return resp
    return response

def init_jinja2(app,**kw):
    logging.info('init jinja2')
    options=dict(
        autoescape=kw.get('autoescape',True),
        block_start_string=kw.get('block_start_string','{%'),
        block_end_string=kw.get('block_end_string','%}'),
        variable_start_string=kw.get('variable_start_string','{{'),
        variable_end_string=kw.get('variable_end_string','}}'),
        auto_reload=kw.get('auto_reload',True)
    )
    path=kw.get('path',None)
    if path is None:
        path=os.path.join(os.path.dirname(os.path.abspath(__file__)),'templates')
    logging.info('set jinja2 template path:%s'%path)
    env=Environment(loader=FileSystemLoader(path),**options)
    filters=kw.get('filters',None)
    if filters is not None:
        for k,v in filters.items():
            env.filters[k]=v
    app['__templating__']=env
def datetime_filter(delta):
    t=int(time.time()-delta)
    if t<60:
        return u'1 minute ago'
    if t<3600:
        return u'1 minute ago'
    if t<86400:
        return u'1 minute ago'
    if t<604800:
        return u'1 minute ago'
    dt=datetime.fromtimestamp(delta)
    return u'%s-%s-%s'%(dt.year,dt.month,dt.day)
async def init(loop):
    await orm.create_pool(loop,**configs.db)
    app=web.Application(loop=loop,middlewares=[logger_factory, response_factory])
    init_jinja2(app,filters=dict(datetime=datetime_filter))
    add_routes(app,'handlers')

    srv=await loop.create_server(app._make_handler(),'127.0.0.1',9000)
    logging.info('server started at 127.0.0.1:9000...')
    return srv

loop=asyncio.get_event_loop()
loop.run_until_complete(init(loop))
loop.run_forever()