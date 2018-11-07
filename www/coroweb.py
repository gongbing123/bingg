#!/usr/bin/env python3
#-*- coding:utf-8 -*-
import functools,os
import asyncio,inspect,logging
from aiohttp import web
from apis import APIError
from urllib import parse



def get(path):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args,**kw):
            return func(*args,**kw)
        wrapper.__method__='GET'
        wrapper.__route__=path
        return wrapper
    return decorator

def post(path):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args,**kw):
            return func(*args,**kw)
        wrapper.__method__='POST'
        wrapper.__route__=path
        return wrapper
    return decorator

def has_request_arg(fn):
    sig=inspect.signature(fn)
    params=sig.parameters
    flat=False
    for name,param in params.items():
        if name=='request':
            flat=True
            continue
        if flat and(param.kind!=inspect.Parameter.VAR_POSITIONAL and param.kind!=inspect.Parameter.VAR_KEYWORD and param.kind!=inspect.Parameter.KEYWORD_ONLY):
            raise ValueError('request parameter must be the last named parameter in function: %s%s' % (fn.__name__, str(sig)))
    return flat
def has_var_kw_arg(fn):
    params=inspect.signature(fn).parameters
    for name,param in params.items():
        if param.kind==inspect.Parameter.VAR_KEYWORD:
            return True
def has_named_kw_args(fn):
    params=inspect.signature(fn).parameters
    for name,param in params.items():
        if param.kind==inspect.Parameter.KEYWORD_ONLY:
            return True
def get_named_kw_args(fn):
    args=[]
    params=inspect.signature(fn).parameters
    for name,param in params.items():
        if param.kind==inspect.Parameter.KEYWORD_ONLY:
            args.append(name)
    return tuple(args)
def get_required_kw_args(fn):
    args=[]
    params=inspect.signature(fn).parameters
    for name,param in params.items():
        if param.kind==inspect.Parameter.KEYWORD_ONLY and param.default==inspect.Parameter.empty:
            args.append(name)
    return tuple(args)

class RequestHandler(object):
    def __init__(self,app,fn):
        self._app=app
        self._func=fn
        self._has_request_arg=has_request_arg(fn)
        self._has_var_kw_arg=has_var_kw_arg(fn)
        self._has_named_kw_args=has_named_kw_args(fn)
        self._named_kw_args=get_named_kw_args(fn)
        self._required_kw_args=get_required_kw_args(fn)
    async def __call__(self,request):
        kw=None
        if self._has_var_kw_arg or self._has_named_kw_args:
            if request.method=="POST":
                if not request.content_type:
                    return web.HTTPBadRequest('Missing Content-Type.')
                rs=request.content_type.lower()
                if rs.startwith('application/json'):
                    params=await request.json()
                    if not isinstance(params,dict):
                        return web.HTTPBadRequest('JSON body must be object.')
                    kw=params
                elif rs.startwith('application/x-www-form-urlencoded')or rs.startwith('multipart/form-data'):
                    params=await request.post()
                    kw=dict(**params)
                else:
                    return web.HTTPBadRequest('Unsupported Content-Type: %s' % request.content_type)
            if request.method=="GET":
                rs=request.query_string
                if rs:
                    kw=dict()
                    for k,v in parse.parse_qs(rs,True).items():
                        kw[k]=v[0]
        if kw is None:
            kw=dict(**request.match_info)
        else:
            if not self._has_var_kw_arg and self._named_kw_args:
                copy=dict()
                for name in self._named_kw_args:
                    if name in kw:
                        copy[name]=kw[name]
                kw=copy
            for k,v in request.match_info.items():
                if k in kw:
                    logging.warning('Duplicate arg name in named arg and kw args: %s' % k)
        if self._has_request_arg:
            kw['request']=request
        if self._required_kw_args:
            for name in self._required_kw_args:
                if not name in kw:
                    return web.HTTPBadRequest('Missing arguments: %s' % name)
        logging.info('call with args: %s' % str(kw))
        try:
            r=await self._func(**kw)
            return r
        except APIError as e:
            return dict(error=e.error,data=e.data,message=e.message)

def add_static(app):
    path=os.path.join(os.path.dirname(os.path.abspath(_file__)),'static')
    app.router.add_route('/static/',path)
    logging.info('add static %s=>%s'%('/static/',path))
def add_route(app,fn):
    method=getattr(fn,'__method__',None)
    path=getattr(fn,'__route__',None)
    if method is None or path is None:
        raise ValueError('@get or @post not defined in %s.' % str(fn))
    if not asyncio.iscoroutinefunction(fn)and not inspect.isgeneratorfunction(fn):
        fn=asyncio.coroutine(fn)
    logging.info('add route %s %s => %s(%s)' % (method, path, fn.__name__, ', '.join(inspect.signature(fn).parameters.keys())))
    app.router.add_route(method,path,RequestHandler(app,fn))
def add_routes(app,module_name):
    n=module_name.rfind('.')
    if n==(-1):
        mod=__import__(module_name,globals(),locals())
    else:
        mod=getattr(__import__(module_name[:n],globals(),locals(),[module_name[n+1:]]),module_name[n+1:])
    for attr in dir(mod):
        if attr.startswith('_'):
            continue
        fn=getattr(mod,attr)
        if callable(fn):
            method = getattr(fn, '__method__', None)
            path = getattr(fn, '__route__', None)
            if method and path:
                add_route(app,fn)
