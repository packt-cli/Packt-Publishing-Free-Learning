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
requests.packages.urllib3.disable_warnings() # Disable Request Warning
import os
import configparser
import argparse
import re
from collections import OrderedDict
from bs4 import BeautifulSoup
import logging


import utils.logger as log_manager
logger = log_manager.get_logger(__name__)
# downgrading logging level for requests
logging.getLogger("requests").setLevel(logging.WARNING)

#################################-MAIN CLASSES-###########################################
class PacktAccountData(object):
    """Contains all needed urls, creates a http session and logs int your account"""

    def __init__(self, cfgFilePath):
        self.cfgFilePath = cfgFilePath
        self.configuration = configparser.ConfigParser()
        if not self.configuration.read(self.cfgFilePath):
            raise configparser.Error('{} file not found'.format(self.cfgFilePath))
        self.bookInfoDataLogFile = self.__getEbookExtraInfoLogFilename()
        self.packtPubUrl = "https://www.packtpub.com"
        self.myBooksUrl = "https://www.packtpub.com/account/my-ebooks"
        self.loginUrl = "https://www.packtpub.com/register"
        self.freeLearningUrl = "https://www.packtpub.com/packt/offers/free-learning"
        self.reqHeaders = {'Connection': 'keep-alive',
                           'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 '
                                         '(KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36'}
        self.myPacktEmail, self.myPacktPassword = self.__getLoginData()
        self.downloadFolderPath, self.downloadFormats, self.downloadBookTitles = self.__getDownloadData()
        if not os.path.exists(self.downloadFolderPath):
            message = "Download folder path: '{}' doesn't exist".format(self.downloadFolderPath)
            logger.error(message)
            raise ValueError(message)
        self.session = self.createSession()

    def __getEbookExtraInfoLogFilename(self):
        """Gets the filename of the ebook metadata log file."""
        return self.configuration.get("DOWNLOAD_DATA", 'ebookExtraInfoLogFilePath')

    def __getLoginData(self):
        """Gets user login credentials."""
        email = self.configuration.get("LOGIN_DATA", 'email')
        password = self.configuration.get("LOGIN_DATA", 'password')
        return email, password

    def __getDownloadData(self):
        """Downloads ebook data from the user account."""
        downloadPath = self.configuration.get("DOWNLOAD_DATA", 'downloadFolderPath')
        downloadFormats = tuple(form.replace(' ', '') for form in
                                self.configuration.get("DOWNLOAD_DATA", 'downloadFormats').split(','))
        downloadBookTitles = None
        try:
            downloadBookTitles = [title.strip(' ') for title in
                                  self.configuration.get("DOWNLOAD_DATA", 'downloadBookTitles').split(',')]
            if len(downloadBookTitles) is 0:
                downloadBookTitles = None
        except configparser.Error as e:
            pass
        return downloadPath, downloadFormats, downloadBookTitles

    def createSession(self):
        """Creates the session"""
        formData = {'email': self.myPacktEmail,
                    'password': self.myPacktPassword,
                    'op': 'Login',
                    'form_build_id': '',
                    'form_id': 'packt_user_login_form'}
        # to get form_build_id
        logger.info("Creating session...")
        r = requests.get(self.loginUrl, headers=self.reqHeaders, timeout=10)
        content = BeautifulSoup(str(r.content), 'html.parser')
        formBuildId = [element['value'] for element in
                       content.find(id='packt-user-login-form').find_all('input', {'name': 'form_build_id'})]
        formData['form_build_id'] = formBuildId[0]
        session = requests.Session()
        rPost = session.post(self.loginUrl, headers=self.reqHeaders, data=formData)
        if rPost.status_code is not 200:
            message = "Login failed!"
            logger.error(message)
            raise requests.exceptions.RequestException(message)
        logger.info("Session created, logged in successfully!")
        return session


class FreeEBookGrabber(object):
    """Claims a daily ebook, retrieving its title"""

    def __init__(self, accountData):
        self.accountData = accountData
        self.session = self.accountData.session
        self.bookTitle = ""

    def __writeEbookInfoData(self, data):
        """
        Write result to file
        :param data: the data to be written down
        """
        with open(self.accountData.bookInfoDataLogFile, "a") as output:
            output.write('\n')
            for key, value in data.items():
                output.write('{} --> {}\n'.format(key.upper(), value))
        logger.info("Complete information for '{}' have been saved".format(data["title"]))

    def getEbookInfoData(self, r):
        """
        Log grabbed book information to log file
        :param r: the previous response got when book has been successfully added to user library
        :return: the data ready to be written to the log file
        """
        logger.info("Retrieving complete information for '{}'".format(self.bookTitle))
        r = self.session.get(self.accountData.freeLearningUrl,
                             headers=self.accountData.reqHeaders, timeout=10)
        resultHtml = BeautifulSoup(r.text, 'html.parser')
        lastGrabbedBook = resultHtml.find('div', {'class': 'dotd-main-book-image'})
        bookUrl = lastGrabbedBook.find('a').attrs['href']
        bookPage = self.session.get(self.accountData.packtPubUrl + bookUrl,
                                    headers=self.accountData.reqHeaders, timeout=10).text
        page = BeautifulSoup(bookPage, 'html.parser')

        resultData = OrderedDict()
        resultData["title"] = self.bookTitle
        resultData["description"] = page.find('div', {'class': 'book-top-block-info-one-liner'}).text.strip()
        author = page.find('div', {'class': 'book-top-block-info-authors'})
        resultData["author"] = author.text.strip().split("\n")[0]
        resultData["date_published"] = page.find('time').text
        codeDownloadUrl = page.find('div', {'class': 'book-top-block-code'}).find('a').attrs['href']
        resultData["code_files_url"] = self.accountData.packtPubUrl + codeDownloadUrl
        resultData["downloaded_at"] = time.strftime("%d-%m-%Y %H:%M")
        logger.success("Info data retrieved for '{}'".format(self.bookTitle))
        self.__writeEbookInfoData(resultData)
        return resultData

    def grabEbook(self, logEbookInfodata = False):
        """Grabs the ebook"""
        logger.info("Start grabbing eBook...")
        r = self.session.get(self.accountData.freeLearningUrl,
                             headers=self.accountData.reqHeaders, timeout=10)
        if r.status_code is not 200:
            raise requests.exceptions.RequestException("http GET status code != 200")
        html = BeautifulSoup(r.text, 'html.parser')
        claimUrl = html.find(attrs={'class': 'twelve-days-claim'})['href']
        self.bookTitle = html.find('div', {'class': 'dotd-title'}).find('h2').next_element. \
            replace('\t', '').replace('\n', '').strip(' ')
        r = self.session.get(self.accountData.packtPubUrl + claimUrl,
                             headers=self.accountData.reqHeaders, timeout=10)
        if r.status_code is 200:
            logger.success("eBook: '{}' has been successfully grabbed!".format(self.bookTitle))
            if logEbookInfodata:
                self.getEbookInfoData(r)
        else:
            message = "eBook: {} has not been grabbed~! ,http GET status code != 200".format(self.bookTitle)
            logger.error(message)
            raise requests.exceptions.RequestException(message)


class BookDownloader(object):
    """Downloads already claimed ebooks from your account"""

    def __init__(self, accountData):
        self.accountData = accountData
        self.session = self.accountData.session

    def getDataOfAllMyBooks(self):
        """Gets data from all available ebooks"""
        logger.info("Getting data of all your books...")
        r = self.session.get(self.accountData.myBooksUrl,
                             headers=self.accountData.reqHeaders, timeout=10)
        if r.status_code is not 200:
            message = "Cannot open {}, http GET status code != 200".format(self.accountData.myBooksUrl)
            logger.error(message)
            raise requests.exceptions.RequestException(message)
        logger.info("Opened '{}' successfully!".format(self.accountData.myBooksUrl))

        myBooksHtml = BeautifulSoup(r.text, 'html.parser')
        all = myBooksHtml.find(id='product-account-list').find_all('div', {'class': 'product-line unseen'})
        self.bookData = [{'title': re.sub(r'\s*\[e\w+\]\s*', '', attr['title'],
                                          flags=re.I).strip(' '), 'id': attr['nid']} for attr in all]
        for i, div in enumerate(myBooksHtml.find_all('div', {'class': 'product-buttons-line toggle'})):
            downloadUrls = {}
            for a_href in div.find_all('a'):
                m = re.match(r'^(/[a-zA-Z]+_download/(\w+)(/(\w+))*)', a_href.get('href'))
                if m:
                    if m.group(4) is not None:
                        downloadUrls[m.group(4)] = m.group(0)
                    else:
                        downloadUrls['code'] = m.group(0)
            self.bookData[i]['downloadUrls'] = downloadUrls

    def __updateDownloadProgressBar(self, currentWorkDone):
        """Prints progress bar, currentWorkDone should be float value in range {0.0 - 1.0}"""
        print("\r[PROGRESS] - [{0:50s}] {1:.1f}% ".format('#' * int(currentWorkDone * 50), currentWorkDone*100), end="" ,)

    def downloadBooks(self, titles=None, formats=None, intoFolder = False):
        """
        Downloads the ebooks.
        :param titles: list('C# tutorial', 'c++ Tutorial') ;
        :param formats: tuple('pdf','mobi','epub','code');
        """
        # download ebook
        if formats is None:
            formats = self.accountData.downloadFormats
            if formats is None:
                formats = ('pdf', 'mobi', 'epub', 'code')
        if titles is not None:
            tempBookData = [data for i, data in enumerate(self.bookData) if
                            any(data['title'] == title for title in titles)]
        else:
            tempBookData = self.bookData
        nrOfBooksDownloaded = 0
        for i, book in enumerate(tempBookData):
            for form in formats:
                if form in list(tempBookData[i]['downloadUrls'].keys()):
                    if form == 'code':
                        fileType = 'zip'
                    else:
                        fileType = form
                    forbiddenChars = ['?', ':', '*', '/', '<', '>', '"', '|', '\\', '\u2013']
                    for ch in forbiddenChars:
                        if ch in tempBookData[i]['title']:
                            tempBookData[i]['title'] = tempBookData[i]['title'].replace(ch, ' ')
                    title = tempBookData[i]['title']
                    title = title.replace(" ", "_")
                    try:
                        logger.info("Title: '{}'".format(title))
                    except Exception as e:
                        title = str(title.encode('utf_8', errors='ignore'))  # if contains some unicodes
                    if intoFolder:
                        targetDownloadPath = os.path.join(self.accountData.downloadFolderPath, title)
                        if not os.path.isdir(targetDownloadPath):
                            os.mkdir(targetDownloadPath)
                    else:
                        targetDownloadPath = os.path.join(self.accountData.downloadFolderPath)
                    fullFilePath = os.path.join(targetDownloadPath,
                                                "{}.{}".format(tempBookData[i]['title'].replace(" ", "_"), fileType))
                    if os.path.isfile(fullFilePath):
                        logger.info("'{}.{}' already exists under the given path".format(title, fileType))
                    else:
                        if form == 'code':
                            logger.info("Downloading code for eBook: '{}'...".format(title))
                        else:
                            logger.info("Downloading eBook: '{}' in .{} format...".format(title, form))
                        try:
                            r = self.session.get(self.accountData.packtPubUrl + tempBookData[i]['downloadUrls'][form],
                                                 headers=self.accountData.reqHeaders, timeout=100,stream=True)

                            if r.status_code is 200:
                                with open(fullFilePath, 'wb') as f:
                                        totalLength = int(r.headers.get('content-length'))
                                        numOfChunks = (totalLength/1024) + 1
                                        for num, chunk in enumerate(r.iter_content(chunk_size=1024)):
                                            if chunk:
                                                self.__updateDownloadProgressBar(num/numOfChunks)
                                                f.write(chunk)
                                                f.flush()
                                if form == 'code':
                                    logger.success("Code for eBook: '{}' downloaded successfully!".format(title))
                                else:
                                    logger.success("eBook: '{}.{}' downloaded successfully!".format(title, form))
                                nrOfBooksDownloaded += 1
                            else:
                                message = "Cannot download '{}'".format(title)
                                logger.error(message)
                                raise requests.exceptions.RequestException(message)
                        except Exception as e:
                            logger.error(e)
        logger.info("{} eBooks have been downloaded!".format(str(nrOfBooksDownloaded)))


#Main
if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument("-g", "--grab", help="grabs daily ebook",
                        action="store_true")
    parser.add_argument("-gl", "--grabl", help="grabs and log ebook extra info data",
                        action="store_true")
    parser.add_argument("-gd", "--grabd", help="grabs daily ebook and downloads the title afterwards",
                        action="store_true")
    parser.add_argument("-da", "--dall", help="downloads all ebooks from your account",
                        action="store_true")
    parser.add_argument("-dc", "--dchosen", help="downloads chosen titles described in [downloadBookTitles] field",
                        action="store_true")
    parser.add_argument("-sgd", "--sgd", help="sends the grabbed eBook to google drive",
                        action="store_true")
    parser.add_argument("-m", "--mail", help="send download to emails defined in config file", default=False,
                        action="store_true")
    parser.add_argument("-f", "--folder", help="downloads eBook into a folder", default=False,
                        action="store_true")

    args = parser.parse_args()
    cfgFilePath = os.path.join(os.getcwd(), "configFile.cfg")

    try:
        myAccount = PacktAccountData(cfgFilePath)
        grabber = FreeEBookGrabber(myAccount)
        downloader = BookDownloader(myAccount)
        if args.sgd:
            from utils.googleDrive import GoogleDriveManager
            googleDrive= GoogleDriveManager(cfgFilePath)

        if args.grab or args.grabl or args.grabd or args.sgd or args.mail:
            if not args.grabl:
                grabber.grabEbook()
            else:
                grabber.grabEbook(logEbookInfodata=True)

        if args.grabd or args.dall or args.dchosen or args.sgd or args.mail:
            downloader.getDataOfAllMyBooks()
        
        intoFolder = False
        if args.folder:
            intoFolder = True
            
        if args.grabd or args.sgd or args.mail:
            if args.sgd or args.mail:
                myAccount.downloadFolderPath = os.getcwd()
            downloader.downloadBooks([grabber.bookTitle], intoFolder = intoFolder)
            if args.sgd or args.mail:
               paths = [os.path.join(myAccount.downloadFolderPath, path) \
                       for path in os.listdir(myAccount.downloadFolderPath) \
                           if os.path.isfile(path) and path.find(grabber.bookTitle) is not -1]
            if args.sgd:
               googleDrive.send_files(paths)
            elif args.mail:
               from utils.mail import MailBook
               mb = MailBook(cfgFilePath)
               pdfPath = None
               mobiPath = None
               try:
                   pdfPath = [path for path in paths if path.split('.')[-1] == 'pdf'][-1]
                   mobiPath = [path for path in paths if path.split('.')[-1] == 'mobi'][-1]
               except:
                   pass
               if pdfPath:
                   mb.send_book(pdfPath)
               if mobiPath:
                   mb.send_kindle(mobiPath)
            if args.sgd or args.mail:
               [os.remove(path) for path in paths]

        elif args.dall:
            downloader.downloadBooks(intoFolder = intoFolder)

        elif args.dchosen:
            downloader.downloadBooks(myAccount.downloadBookTitles, intoFolder = intoFolder)
        logger.success("Good, looks like all went well! :-)")
    except Exception as e:
        logger.error("Exception occurred {}".format(e))
