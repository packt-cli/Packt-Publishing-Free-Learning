#!/usr/bin/env python

from __future__ import print_function, unicode_literals, division, absolute_import  # We require Python 2.6 or later

__author__ = "Lukasz Uszko, Daniel van Dorp"
__copyright__ = "Copyright 2016"
__license__ = "MIT"
__version__ = "1.0.0"
__email__ = "lukasz.uszko@gmail.com, daniel@vandorp.biz"

import sys
import time

PY2 = sys.version_info[0] == 2
if PY2:
    from future import standard_library
    standard_library.install_aliases()
    from builtins import *
    from builtins import str
    from builtins import map
    from builtins import object
    reload(sys)
    sys.setdefaultencoding('utf8')
    
import requests
import os
import configparser
import argparse
import re
from collections import OrderedDict
from bs4 import BeautifulSoup

class PacktAccountData(object):
    ''' Contains all needed urls, creates a http session and logs int your account '''
    
    def __init__(self,cfgFilePath):
        self.cfgFilePath= cfgFilePath
        self.configuration = configparser.ConfigParser()
        if(not self.configuration.read(self.cfgFilePath)):
            raise configparser.Error(self.cfgFilePath+ ' file not found')
        self.log_file = self.__get_log_filename()
        self.packtPubUrl= "https://www.packtpub.com"
        self.myBooksUrl= "https://www.packtpub.com/account/my-ebooks"
        self.loginUrl= "https://www.packtpub.com/register"
        self.freeLearningUrl= "https://www.packtpub.com/packt/offers/free-learning"
        self.reqHeaders={'Connection':'keep-alive',
                    'User-Agent' : 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36'}
        self.myPacktEmail, self.myPacktPassword= self.__getLoginData()
        self.downloadFolderPath,self.downloadFormats,self.downloadBookTitles= self.__getDownloadData()
        if(not os.path.exists(self.downloadFolderPath)):
            raise ValueError("[ERROR] Download folder path: '"+self.downloadFolderPath+ "' doesn't exist" )
        self.session = self.createSession()

    def write_result(self, data):
        """
        Write result to file
        :param data: the data to be writted down
        """
        with open(self.log_file, "a") as output:
            output.write('\n')
            for key, value in data.items():
                output.write('%s --> %s\n' % (key.upper(), value))
        print("[INFO] Complete informations for '%s' have been saved" % data["title"])

    def __get_log_filename(self):
        return self.configuration.get("DOWNLOAD_DATA", 'logFile')

    def __getLoginData(self):
        email= self.configuration.get("LOGIN_DATA",'email')
        password= self.configuration.get("LOGIN_DATA",'password')
        return (email,password)


    def __getDownloadData(self):
        downloadPath= self.configuration.get("DOWNLOAD_DATA",'downloadFolderPath')
        downloadFormats= tuple(format.replace(' ', '') for format in self.configuration.get("DOWNLOAD_DATA",'downloadFormats').split(','))
        downloadBookTitles= None
        try:
            downloadBookTitles= [title.strip(' ') for title in self.configuration.get("DOWNLOAD_DATA",'downloadBookTitles').split(',')]
            if len(downloadBookTitles)is 0:
                downloadBookTitles= None
        except configparser.Error as e:
            pass
        return (downloadPath,downloadFormats,downloadBookTitles)
    
    def createSession(self):
        formData= {'email':self.myPacktEmail,
                'password':self.myPacktPassword,
                'op':'Login',
                'form_build_id':'',
                'form_id':'packt_user_login_form'}
        #to get form_build_id
        print("[INFO] - Creates session ...")
        r = requests.get(self.loginUrl,headers=self.reqHeaders,timeout=10)
        content = BeautifulSoup(str(r.content), 'html.parser')
        formBuildId = [element['value'] for element in content.find(id='packt-user-login-form').find_all('input',{'name':'form_build_id'})]
        formData['form_build_id']=formBuildId[0]               
        session = requests.Session()
        rPost = session.post(self.loginUrl, headers=self.reqHeaders,data=formData)
        if(rPost.status_code is not 200):
            raise requests.exceptions.RequestException("login failed! ")
        print("[INFO] - Session created, logged succesfully!" ) 
        return session
 


 
class FreeEBookGrabber(object):
    ''' Claims a daily ebook, retrieving its title'''
    
    def __init__(self, accountData):
        self.accountData = accountData
        self.session = self.accountData.session
        self.bookTitle = ""

    def get_info(self, r):
        """
        Log grabbed book information to log file
        :param r: the previous response got when book has been successufully added to user library
        :return: the data ready to be written to the log file
        """
        print("[INFO] Retrieving complete informations for '%s'" % self.bookTitle)
        result_html = BeautifulSoup(r.text, 'html.parser')
        last_grabbed_book = result_html.find('div', {'id': 'product-account-list'}).find('div')
        book_url = last_grabbed_book.find('a').attrs['href']
        book_page = self.session.get('http://www.packtpub.com%s' % book_url, headers=self.accountData.reqHeaders,
                                     timeout=10).text
        page = BeautifulSoup(book_page, 'html.parser')

        result_data = OrderedDict()
        result_data["title"] = self.bookTitle
        result_data["description"] = page.find('div', {'class': 'book-top-block-info-one-liner'}).text.strip()
        author = page.find('div', {'class': 'book-top-block-info-authors'})
        result_data["author"] = author.text.strip().split("\n")[0]
        result_data["time"] = author.find('time').attrs["datetime"]
        result_data["downloaded_at"] = time.strftime("%d-%m-%Y %H:%M")
        print("[SUCCESS] Saved all infos about '%s'" % self.bookTitle)
        return result_data

    def grabEbook(self, log=False):
        print("[INFO] - start grabbing eBook...")           
        r = self.session.get(self.accountData.freeLearningUrl, headers=self.accountData.reqHeaders,timeout=10)
        if(r.status_code is not 200):
            raise requests.exceptions.RequestException("http GET status code != 200")
        html = BeautifulSoup(r.text, 'html.parser')
        claimUrl= html.find(attrs={'class':'twelve-days-claim'})['href']
        self.bookTitle= html.find('div',{'class':'dotd-title'}).find('h2').next_element.replace('\t','').replace('\n','').strip(' ')
        r = self.session.get(self.accountData.packtPubUrl+claimUrl,headers=self.accountData.reqHeaders,timeout=10)
        if(r.status_code is 200):
            print("[SUCCESS] - eBook: '" + self.bookTitle +"' has been succesfully grabbed !")
            if log:
                self.get_info(r)
        else:
            raise requests.exceptions.RequestException("eBook:" + self.bookTitle +" has not been grabbed~! ,http GET status code != 200")

        

class BookDownloader(object):
    ''' Downloads already claimed ebooks from your account '''
    
    def __init__(self, accountData):
        self.accountData = accountData
        self.session= self.accountData.session
        
    def getDataOfAllMyBooks(self):
        print("[INFO] - Getting data of all your books...")
        r = self.session.get(self.accountData.myBooksUrl,headers=self.accountData.reqHeaders,timeout=10)
        if(r.status_code is not 200):
            raise requests.exceptions.RequestException("Cannot open " + self.accountData.myBooksUrl +", http GET status code != 200")    
        print("[INFO] - opened  '"+ self.accountData.myBooksUrl+"' succesfully!")
        myBooksHtml = BeautifulSoup(r.text, 'html.parser')
        all =  myBooksHtml.find(id='product-account-list').find_all('div', {'class':'product-line unseen'})
        self.bookData= [ {'title': re.sub(r'\s*\[e\w+\]\s*','',attr['title'], flags=re.I ).strip(' '), 'id':attr['nid']}   for attr in all]
        for i,div in enumerate(myBooksHtml.find_all('div', {'class':'product-buttons-line toggle'})):
            downloadUrls= {}
            for a_href in div.find_all('a'):
                m = re.match(r'^(/[a-zA-Z]+_download/(\w+)(/(\w+))*)',a_href.get('href'))
                if m:
                    if m.group(4) is not None:
                       downloadUrls[m.group(4)]= m.group(0)
                    else:
                        downloadUrls['code']= m.group(0)
            self.bookData[i]['downloadUrls']=downloadUrls
            
            
    def downloadBooks(self,titles=None): #titles= list('C# tutorial', 'c++ Tutorial') ; format=tuple('pdf','mobi','epub','code')
        #download ebook
        formats = self.accountData.downloadFormats
        if formats is None:
            formats=('pdf','mobi','epub','code')   
        if titles is not None:
            tempBookData = [data for i,data in enumerate(self.bookData) if any(data['title']==title for title in titles) ]
        else:
            tempBookData=self.bookData
        nrOfBooksDownloaded=0
        for i, book in enumerate(tempBookData):
            for format in formats:
                if format in list(tempBookData[i]['downloadUrls'].keys()):
                    if format == 'code':
                        fileType='zip'
                    else:
                        fileType = format
                    forbiddenChars = ['?',':','*','/','<','>','"','|','\\']
                    for ch in forbiddenChars:
                        if ch in tempBookData[i]['title'] :
                            tempBookData[i]['title'] = tempBookData[i]['title'].replace(ch,' ')
                    title = tempBookData[i]['title']
                    try:
                        print("[INFO] - Title: "+ title)
                    except Exception as e: 
                        title = str(title.encode('utf_8',errors='ignore'))  # if contains some unicodes
                    fullFilePath=os.path.join(self.accountData.downloadFolderPath,tempBookData[i]['title'] +'.'+fileType)
                    if(os.path.isfile(fullFilePath)):
                        print("[INFO] -"+ title+'.'+fileType+ " already exists under the given path")
                        pass
                    else:
                        if format == 'code':
                            print("[INFO] - downloading code for eBook: "+title+ "...")                           
                        else:
                            print("[INFO] - downloading eBook: "+title+" in ."+format+ " format...")
                        r = self.session.get(self.accountData.packtPubUrl+tempBookData[i]['downloadUrls'][format],headers=self.accountData.reqHeaders,timeout=100)
                        if(r.status_code is 200):
                            with open(fullFilePath,'wb') as f:
                                f.write(r.content)
                            if format == 'code':
                                print("[SUCCESS] code for eBook: "+title+" downloaded succesfully!")                           
                            else:
                                print("[SUCCESS] eBook: "+title+'.'+format+" downloaded succesfully!")      
                            nrOfBooksDownloaded=i+1
                        else:
                            raise requests.exceptions.RequestException("Cannot download "+title)                            
        print("[INFO] - " + str(nrOfBooksDownloaded)+" eBooks have been downloaded !")          



            
if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument("-g","--grab", help="grabs daily ebook",action="store_true")
    parser.add_argument("-gl", "--grabl", help= "grabs and log data", action="store_true")
    parser.add_argument("-gd","--grabd", help="grabs daily ebook and downloads the title afterwards",action="store_true")
    parser.add_argument("-da","--dall", help="downloads all ebooks from your account",action="store_true")
    parser.add_argument("-dc","--dchosen", help="downloads chosen titles described in [downloadBookTitles] field",action="store_true")
    args = parser.parse_args()
    cfgFilePath= os.path.join(os.getcwd(),"configFile.cfg")
    try:
        myAccount = PacktAccountData(cfgFilePath)
        if args.grabl:
            grabber = FreeEBookGrabber(myAccount)
            grabber.grabEbook(log=True)
        if args.grab or args.grabd:
            grabber =FreeEBookGrabber(myAccount)
            grabber.grabEbook()
        if args.grabd or args.dall or args.dchosen:
            downloader = BookDownloader(myAccount)
            downloader.getDataOfAllMyBooks()
        if args.grabd:          
            downloader.downloadBooks([grabber.bookTitle])     
        elif args.dall:
            downloader.downloadBooks()
        elif args.dchosen:
            downloader.downloadBooks(myAccount.downloadBookTitles)
        print("[SUCCESS] - good, looks like all went well! :-)")            
    except Exception as e:
        print("[ERROR] - Exception occured %s"% e)            

