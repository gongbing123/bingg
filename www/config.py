#!/usr/bin/env python3
#-*- coding:utf-8 -*-

import config_default

configs=config_default.configs
class Dict(dict):
    def __init(self,name=(),value=(),**kw):
        super().__init__(**kw)
        for k,v in zip(name,value):
            self[k]=v
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError('object has no attribute:%s'%key)
    def __setattr__(self, key, value):
        self[key]=value
def toDict(d):
    D=Dict()
    for k,v in d.items():
        D[k]=toDict(v)if isinstance(v,dict)else v
    return D
def merge(default,override):
    b={}
    for k,v in default.items():
        if k in override:
                b[k]=merge(v,override[k])if isinstance(v,dict)else override[k]
        else:
            b[k]=v
    return b
try:
    import config_override
    configs=merge(configs,config_override.configs)
except ImportError:
    pass
configs=toDict(configs)
