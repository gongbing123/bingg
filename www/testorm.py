#!/usr/bin/env python3
#-*- coding:utf-8 -*-
import asyncio
import orm
from config import configs
from Models import User,Blog,Comment
async def test(loop):
    await orm.create_pool(loop,**configs.db)
    u = User(name='gc', email='834718026@qq.com', passwd='abc123456', image='about:blank', id='115')
    #await u.save()
    await u.remove()
async def find(loop):
    await orm.create_pool(loop,**configs.db)
    a={'orderBy':'email','limit':(0,3)}
    ra=await User.findAll(**a)
    rs = await User.findNum('count(id)')
    print('查找测试： %s' % ra)
    print('查找测试： %s' % rs)

loop = asyncio.get_event_loop()
loop.run_until_complete(test(loop))
#loop.run_until_complete(find(loop))
loop.run_forever()
