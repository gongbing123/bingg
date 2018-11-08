#!/usr/bin/env python3
#-*- coding:utf-8 -*-


from coroweb import get
from Models import User, Comment, Blog, next_id



@get('/')
async def index(request):
    users = await User.findAll()
    return {
        '__template__': 'test.html',
        'users': users
    }