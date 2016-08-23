#!/usr/bin/env python

from __future__ import print_function, unicode_literals, division, absolute_import  # We require Python 2.6 or later

__author__ = "Lukasz Uszko, Daniel van Dorp"
__copyright__ = "Copyright 2016"
__license__ = "MIT"
__version__ = "1.0.0"
__email__ = "lukasz.uszko@gmail.com, daniel@vandorp.biz"

import sys
PY2 = sys.version_info[0] == 2
if PY2:
    from future import standard_library
    standard_library.install_aliases()
    from builtins import *
    from builtins import str
    reload(sys)
    sys.setdefaultencoding('utf8')
import requests
import os
import configparser
from bs4 import BeautifulSoup


if __name__ == '__main__':
    '''connection parameters'''
    config =configparser.ConfigParser()
    
    try:        
        if(not config.read("configFile.cfg")):
            raise configparser.Error('config file not found')       
        email= config.get("LOGIN_DATA",'email')
        password= config.get("LOGIN_DATA",'password')
        downloadBooksAfterClaim= config.get("DOWNLOAD_DATA",'downloadBookAfterClaim')
    except configparser.Error as e:
        print("[ERROR] loginData.cfg file incorrect or doesn't exist! : "+str(e))
        sys.exit(1)
        
    freeLearningUrl= "https://www.packtpub.com/packt/offers/free-learning"
    packtpubUrl= 'https://www.packtpub.com'
    reqHeaders= {'Content-Type':'application/x-www-form-urlencoded',
             'Connection':'keep-alive',
             'User-Agent' : 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36'
             }
    formData= {'email':email,
                'password':password,
                'op':'Login',
                'form_build_id':'',
                'form_id':'packt_user_login_form'}
    print("start grabbing eBook...")
    
    try:
        r = requests.get(freeLearningUrl, headers=reqHeaders,timeout=10)
        if(r.status_code is 200):
            html = BeautifulSoup(r.text, 'html.parser')
            loginBuildId= html.find(attrs={'name':'form_build_id'})['id']
            claimUrl= html.find(attrs={'class':'twelve-days-claim'})['href']
            bookTitle= html.find('div',{'class':'dotd-title'}).find('h2').next_element.replace('\t','').replace('\n','').strip(' ')
            if(loginBuildId is None or claimUrl is None or bookTitle is None ):
                print("[ERROR] - cannot get login data" ) 
                sys.exit(1)                
        else: 
            raise requests.exceptions.RequestException("http GET status codec != 200")
    except TypeError as typeError:
        print("[ERROR] - Type error occured %s "%typeError )
        sys.exit(1)
    except requests.exceptions.RequestException as exception:
        print("[ERROR] - Exception occured %s "%exception )
        sys.exit(1)
    
    formData['form_build_id']=loginBuildId
    session = requests.Session()
    
    try:
        rPost = session.post(freeLearningUrl, headers=reqHeaders,data=formData)
        if(rPost.status_code is not 200):
            raise requests.exceptions.RequestException("login failed! ")  
        print(packtpubUrl+claimUrl)
        r = session.get(packtpubUrl+claimUrl,headers=reqHeaders,timeout=10)
    except TypeError as typeError:
        print("[ERROR] - Type error occured %s "%typeError, file=sys.stderr)
        sys.exit(1)
    except requests.exceptions.RequestException as exception:
        print("[ERROR] - Exception occured %s "%exception, file=sys.stderr)
        sys.exit(1)
        
    if(r.status_code is 200):
        print("[SUCCESS] - eBook: '" + bookTitle +"' has been succesfully grabbed !")
        if downloadBooksAfterClaim=="YES":
            from packtFreeBookDownloader import MyPacktPublishingBooksDownloader
            downloader = MyPacktPublishingBooksDownloader(session)
            downloader.getDataOfAllMyBooks()
            downloader.downloadBooks([bookTitle], downloader.downloadFormats)            
    else:
        print("[ERROR] - eBook: '" + bookTitle +"' has not been grabbed, respCode: "+str(r.status_code), file=sys.stderr)
