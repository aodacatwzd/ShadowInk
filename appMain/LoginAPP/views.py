from django.shortcuts import render

# Create your views here.
# -*- coding:utf-8 -*-

import logging
import json
import time
import random
import os
from django.http import *
from django.template import loader
from django.contrib.auth import login
from ShadowInk import settings
from . import models
from . import mysqlConnector
from qcloudsms_py import SmsSingleSender
from qcloudsms_py.httpclient import HTTPError

logger = logging.getLogger(__name__)

# '/'目录，显示主页
def showMainPage(request):
    logging.info('Accessing Page / with showMainPage')
    return HttpResponseRedirect('/login/login')

# '/<slug>'目录，分别处理，对于未知的slug返回none
def showPages(request, path):
    logging.info('Accessing Page /%s with showPages'%(path))
    if path=='explore':
        with open('./static/my.html', encoding='UTF-8') as f:
            html = f.read()
        return HttpResponse(html)
    '''
        template = loader.get_template('../static/my.html')
        return HttpResponse(template.render({},request))
    '''


    if path=='login':
        name = request.POST.get('name')
        password = request.POST.get('password')
        if name == None and password == None:
            # 未提交任何请求，或者用户名密码未输入
            template = loader.get_template('login.html')
            context = {}
        else:
            checkResult = mysqlConnector.checkPassword(name, password)
            if not checkResult['success']:
                # 登录失败，失败原因在checkResult['message']中
                template = loader.get_template('loginFail.html')
            else :
                # 登陆成功，成功提示也在...中
                template = loader.get_template('loginSuccess.html')
                login(request,checkResult['user'])
            context = {
                'HelloMessage': checkResult['message'],
            }
        return HttpResponse(template.render(context, request))

    if path=='register':
        name = request.POST.get('name')
        password = request.POST.get('password')
        vcode = request.POST.get('vcode')
        context = {}
        if name == None and password == None:
            template = loader.get_template('register.html')
        else:
            # 如果验证码错误 (pass是测试用的后门)
            if vcode != 'pass' and vcode != request.session.get('vcode',''):
                template = loader.get_template('registerFail.html')
                context = {
                    'HelloMessage': '验证码错误！请重新输入，或者尝试重新发送。',
                }
            # 尝试向数据库中插入用户，并返回成功与否
            else:
                insertResult = mysqlConnector.insertUser(name, password)
                if insertResult['success']:# 用户注册成功
                    template = loader.get_template('loginFail.html')
                    context = {
                        'HelloMessage': insertResult['message'],
                    }
                else:# 用户注册失败
                    template = loader.get_template('registerFail.html')
                    context = {
                        'HelloMessage': insertResult['message'],
                    }
        return HttpResponse(template.render(context, request))

    # 动态显示首页上的内容
    # TODO: 需要对文章进行排序并处理
    if path=='pContent':
        articles = mysqlConnector.getArticles()
        template = loader.get_template('pContent.html')
        context = {
            'articles' : articles
        }
        return HttpResponse(template.render(context, request))

    if path=='pPostArticle':
        title = request.POST.get("title")
        content = request.POST.get("content")
        pic = request.FILES.get("picture")
        # username = request.session.get("username", None)
        # userid = request.session.get("userid", None)
        username = 'aodacat'
        userid = 4
        if not username or not userid:
            result = {
                'success' : 'False',
                'message' : '登录状态错误，请保存你输入的内容，然后刷新页面重试。'
            }
            return HttpResponse(json.dumps(result))
        if not title :
            pass
        filename = username + "_" + str(int(time.time())) + pic.name[-4:]
        url = os.path.join(settings.MEDIA_URL, filename)
        urlSave = os.path.join(settings.MEDIA_ROOT, filename)
        with open(urlSave,"wb") as fPic:
            for chunk in pic.chunks():
                fPic.write(chunk)
        insertResult = mysqlConnector.insertArticle(userid,title,url,content)
        result = {
            'success' : 'True',
            'message' : '发表文章成功！'
        }
        return HttpResponse(json.dumps(result))

    if path=='eat':
        user_list = mysqlConnector.getUsers()
        template = loader.get_template('back.html')
        context = {
            'user_list' : user_list,
        }
        return HttpResponse(template.render(context, request))

    if path=='test':
        return HttpResponse('Ok')

    if path=='sendSMS':
        phone_number = request.POST.get("phone_number")
        identify_code = str(random.randint(1000,9999))
        request.session['vcode'] = identify_code
        logging.info("Phone number: " + phone_number + " , Identify_code: " + identify_code)
        result = {}

        appid = 1400143065
        appkey = "5299b5d8357ef27f451132f858784a6e"
        phone_numbers = [phone_number]
        template_id = 196454
        sms_sign = "小司机科技"
        ssender = SmsSingleSender(appid, appkey)
        params = [identify_code]
        result = ssender.send_with_param(86, phone_numbers[0],
            template_id, params, sign=sms_sign, extend="", ext="")
        logging.info(result)

        return HttpResponse(json.dumps(result))

    return HttpResponse('No Page Here.')

# '/<path>'目录，一般是请求资源或者静态网页，直接分类别发送
def showPath(request, path):
    logging.info('Accessing Page /%s with showPath'%(path))

    if path.endswith('jpg'):
        with open('./static/'+path, mode="rb") as f:
            html = f.read()
        return HttpResponse(html, content_type="image/jpg")

    if path.endswith('png'):
        with open('./static/'+path, mode="rb") as f:
            html = f.read()
        return HttpResponse(html, content_type="image/png")

    if path.endswith('ico'):
        with open('./static/image/'+path, mode="rb") as f:
            html = f.read()
        return HttpResponse(html, content_type="image/x-icon")

    if path.endswith('css'):
        with open('./static/'+path, encoding='UTF-8') as f:
            html = f.read()
        return HttpResponse(html, content_type="text/css")

    with open('./static/'+path, encoding='UTF-8') as f:
        html = f.read()
    return HttpResponse(html)

# '/media/...'目录，请求静态资源等。若部署nginx等服务器时可以转移控制权
def showMedia(request, path):
    logging.info('Accessing Page /%s with showPath'%(path))

    if path.endswith('jpg'):
        with open('./media/'+path, mode="rb") as f:
            html = f.read()
        return HttpResponse(html, content_type="image/jpg")

    if path.endswith('png'):
        with open('./media/'+path, mode="rb") as f:
            html = f.read()
        return HttpResponse(html, content_type="image/png")
