# -*- coding: utf-8 -*-


'''
    Mrknow Add-on
    Copyright (C) 2017 mrknow

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''
from __future__ import unicode_literals

import urlparse,base64,urllib
import re, time, datetime
import json,sys
import datetime, time
import requests

from resources.lib.libraries import control
from resources.lib.libraries import client

mainUrl = 'http://wizja.tv/'
userstatusUrl = 'http://wizja.tv/users/index.php'
HOST = {'User-Agent': 'Specto for Kodi'}

headers = {'User-Agent': 'Specto for Kodi', 'ContentType': 'application/x-www-form-urlencoded'}
#"__cfduid=df35c1fb15873ee570360c686596e4b701492685327;
# expires=Fri, 20-Apr-18 10:48:47 GMT; path=/; domain=.wizja.tv; HttpOnly
# PHPSESSID=uompj09djkq68lihk58ds2mkm6; path=/"

def wizja_check_staus():
    if getWizjaCredentialsInfo() == False:
        if control.yesnoDialog(control.lang(40005).encode('utf-8'), control.lang(30481).encode('utf-8'), '',
                               'Wizja', control.lang(30483).encode('utf-8'),
                               control.lang(30482).encode('utf-8')):
            control.openSettings('0.1')
        return False
        #raise Exception()
    us =  wizja_userstatus()
    if us == 'NIEZALOGOWANY':
        #nie zalogowany, jedziemy z logowaniem tylko raz
        if not wizja_login():
            control.log('PROBLEM Z LOGOWANIEM')
            return False
        us = wizja_userstatus()
    elif us == 'FREE':
        control.log('NIE MA PREMIUM')

    return True

def wizja_userstatus():
    s = webClient()
    r = s.get('http://wizja.tv/users/index.php').text

    #print ('result :#%s#' % r)
    if 'login_input_username' in r:
        control.log('NIEZALOGOWANY')
        return 'NIEZALOGOWANY'

    if 'Zalogowany jako' in r:
        control.log('ZALOGOWANY')
        # no premium
        if '<font color=ff0000>Brak premium' in r:
            control.log('WIZJA.TV FREE PREMIUM: %s' % '')
            control.infoDialog(control.lang(30490).encode('utf-8'), time=6000)
            control.dialog.ok(control.addonInfo('name') + ' - WIZJA TV', control.lang(30490).encode('utf-8'), '')
            return 'FREE'
        else:
            try:
                premium = re.findall('Premium aktywne do (\d{4}.*?)</font>', r)[0]
                control.set_setting('wizja.expire', premium)
                control.infoDialog('Premium Wizja.tv do: ' + premium.encode('utf-8'), time=2000)
                return 'PREMIUM%s' % premium
            except:
                pass
                return 'PREMIUM%s'

    return True

def wizja_login():
    try:
        control.log('LOGUJE SIE DO KONTA')
        params = {}
        url = userstatusUrl
        #result, headers, content, cookie = client.request(url, output='extended')

        params['login']='zaloguj'
        params['user_name'] = control.get_setting('wizja.user')
        params['user_password'] = control.get_setting('wizja.pass')


        #login to site
        s = webClient()
        #login to site
        r  = s.post(url, data=params)
        r = r.text.encode('utf-8')
        desession = s.__getstate__()
        control.save_session_obj(desession)
        #wrong login

        login_pass = len(re.findall('<font color="#FF0000">(B.+dne has.+o\.\.)</font>',r))
        login_login = len(re.findall('<font color="#FF0000">(B.+dny u.+ytkownik lub has.+o\.)</font>',r))
        login_times = len(re.findall('<font color="#FF0000">(Wpisa.+ b.+dne has.+o du.+o razy.+)</font>',r))

        if login_pass > 0: #zly login
            control.log('WIZJA.TV ZLY LOGIN1: %s' % '')
            control.infoDialog(control.lang(30497).encode('utf-8'),time=6000)
            control.dialog.ok(control.addonInfo('name') + ' - WIZJA TV',control.lang(30497).encode('utf-8'), '')
            control.openSettings('0.1')
            raise Exception()
        elif login_login > 0: #zly login
            control.log('WIZJA.TV ZLY LOGIN2: %s' % '')
            control.infoDialog(control.lang(30486).encode('utf-8'),time=6000)
            control.dialog.ok(control.addonInfo('name') + ' - WIZJA TV',control.lang(30486).encode('utf-8'), '')

            raise Exception()

        #account locked - wait 60 minutes
        elif login_times:
            control.log('WIZJA.TV zbyt wiele razy pobowales - poczekaj 60 minut: %s' % '')
            control.infoDialog(control.lang(30487).encode('utf-8'),time=6000)
            control.dialog.ok(control.addonInfo('name') + ' - WIZJA TV',control.lang(30487).encode('utf-8'), '')

            raise Exception('zbyt wiele razy pobowales - poczekaj 60 minut')
        #Other error
        #else:
        #    control.log('WIZJA.TV inny blad: %s' % '')
        #    control.infoDialog(control.lang(30488).encode('utf-8'), time=6000)
        #    raise Exception('Inny bład: '+ r)

        return True

    except Exception as e:
        control.log('Error wizja.login %s' % e)
        return False

def getstream(id):
    try:

        if wizja_check_staus():
            s = webClient()
            ref='http://wizja.tv/watch.php?id=%s' % id
            result =  s.get(ref)
            #print "Result", result, result.text.encode('utf-8')
            #exit()

            url = 'http://wizja.tv/porter.php?ch=%s' % id
            r = s.get(url)
            result = r.text
            ref = r.url

            mylink = re.compile('src: "(.*?)"').findall(result)
            mykill = re.compile('<a href="killme.php\?id=(.*?)" target="_top">').findall(result)
            print ('MYLINK')
            print mylink
            if len(mylink)>0:
                rtmp2 = urllib.unquote(mylink[0]).decode('utf8')
                rtmp1 = re.compile('rtmp://(.*?)/(.*?)/(.*?)\?(.*?)\&streamType').findall(rtmp2)
                #rtmp = 'rtmp://' + rtmp1[0][0] + '/' + rtmp1[0][1] +'/' +rtmp1[0][2]+ '?'+ rtmp1[0][3]+ ' app=' + rtmp1[0][1] + '?' +rtmp1[0][3]+' swfVfy=1 flashver=WIN\\2020,0,0,306 timeout=25 swfUrl=http://wizja.tv/player/StrobeMediaPlayback_v4.swf live=true pageUrl='+ref
                #rtmpdump
                # -r "rtmp://77.123.139.45:1955/haYequChasp4T3eT?event=50&token=qBftHGnOVwU365c074vS8JFLKTjZrb&user=mrknow"
                # -a "haYequChasp4T3eT?event=50&token=qBftHGnOVwU365c074vS8JFLKTjZrb&user=mrknow"
                # -f "LNX 25,0,0,127"
                # -W "http://wizja.tv/player/StrobeMediaPlayback_v4.swf"
                # -p "http://wizja.tv/player.php?target=epona_p&ch=50"
                # -y "pHe7repheT?event=50&token=qBftHGnOVwU365c074vS8JFLKTjZrb&user=mrknow"
                rtmp = 'rtmp://' + rtmp1[0][0] + '/' + rtmp1[0][1] + '?' + rtmp1[0][3] + \
                       ' app=' + rtmp1[0][1] + '?' + rtmp1[0][3] + \
                       ' playpath=' + rtmp1[0][2] + '?'+ rtmp1[0][3] + \
                       ' swfVfy=1 flashver=LNX\\25,0,0,12 timeout=25 ' \
                       'swfUrl=http://wizja.tv/player/StrobeMediaPlayback_v4.swf live=true ' \
                       'pageUrl=' + ref

                print "RTMP", rtmp
                return rtmp
            #kill other sessions
            #elif len(mykill)>0:
            #    control.log('Error KILL %s' % mykill)
            #    urlkill = 'http://wizja.tv/killme.php?id=%s' % mykill[0]
            #    result = client.request(urlkill , headers=HOST, cookie=cookie)
            #    control.sleep(300)
            #    url = 'http://wizja.tv/porter.php?ch=%s' % id
            #    result = client.request(url, headers=HOST, cookie=cookie)
            #    mylink = re.compile('src: "(.*?)"').findall(result)
            #    if len(mylink)>0:
            #        rtmp2 = urllib.unquote(mylink[0]).decode('utf8')
            #        rtmp1 = re.compile('rtmp://(.*?)/(.*?)/(.*?)\?(.*?)\&streamType').findall(rtmp2)
            #        #rtmp = 'rtmp://' + rtmp1[0][0] + '/' + rtmp1[0][1] +'/' +rtmp1[0][2]+ '?'+ rtmp1[0][3]+ ' app=' + rtmp1[0][1] + '?' +rtmp1[0][3]+' swfVfy=1 flashver=WIN\\2020,0,0,306 timeout=25 swfUrl=http://wizja.tv/player/StrobeMediaPlayback_v4.swf live=true pageUrl='+ref
            #        rtmp = 'rtmp://' + rtmp1[0][0] + '/' + rtmp1[0][1] + '/' + rtmp1[0][2] + '?' + rtmp1[0][
            #            3] + ' app=' + rtmp1[0][1] + '?' + rtmp1[0][
            #                   3] + ' swfVfy=1 flashver=WIN\\2020,0,0,306 timeout=25 swfUrl=http://wizja.tv/player/StrobeMediaPlayback_v4.swf live=true pageUrl=' + ref
            #        return rtmp
            else:
                raise Exception('WWW: '+result)
        else:
            return
    except Exception as e:
        control.log('Error wizja.getstream %s' % e)

def getWizjaCredentialsInfo():
    user = control.setting('wizja.user').strip()
    password = control.setting('wizja.pass')
    if (user == '' or password == ''): return False
    return True

def wizjachanels():
    try:
        print "XXX-1"
        if wizja_check_staus() == False: raise ValueError('wizja_check_staus ERROR')
        print "XXX-2"

        items = []
        url = 'http://wizja.tv/'
        s= webClient()
        result = s.get(url).text.encode('utf-8')
        print "XXX-3.0", type(result)
        #print "XXX-3.1", result.encode('utf-8')
        result = client.parseDOM(result, 'table', attrs={'width':'75%'})[0]
        result = client.parseDOM(result, 'td')
        print "XXX-4", result

        for i in result:
            item = {}
            try:
                result2 = re.findall("""href=['"](.*?)['"]""",i)
                result3 = re.findall("""src=['"](.*?)['"]""",i)
                item['img'] = 'http://wizja.tv/' + result3[0]
                item['img'] = item['img'].encode('utf-8')
                item['id'] = result2[0].replace('watch.php?id=','')
                item['id'] = item['id'].encode('utf-8')
                item['title'] = result3[0].replace('ch_logo/','').replace('.png','')
                item['title'] = item['title'].capitalize().encode('utf-8')
                items.append(item)
            except Exception as e:
                control.log('Error wizja.wizjachanels for %s' % e)
                pass
        return items
    except Exception as e:
        control.log('Error wizja.wizjachanels %s' % e)

def webClient():
    s = requests.Session()
    try:
        s.__setstate__(control.load_session_obj())
    except Exception as e:
        print "F: client() ERROR: %s" % e
        pass
    s.headers.update(HOST)
    s.encoding = 'utf-8'

    return s


