#!/usr/bin/env python
from __future__ import (absolute_import, division, print_function, unicode_literals)

import argparse
import datetime as dt
import logging
import os
import re
import sys
import time
from collections import OrderedDict
import configparser
import requests
from bs4 import BeautifulSoup
from python_anticaptcha import AnticaptchaClient, NoCaptchaTaskProxylessTask

from utils.logger import get_logger

logger = get_logger(__name__)
logging.getLogger("requests").setLevel(logging.WARNING)  # downgrading logging level for requests

DATE_FORMAT = "%Y/%m/%d"

SUCCESS_EMAIL_SUBJECT = "{} New free Packt ebook: \"{}\""
SUCCESS_EMAIL_BODY = "A new free Packt ebook \"{}\" was successfully grabbed. Enjoy!"
FAILURE_EMAIL_SUBJECT = "{} Grabbing a new free Packt ebook failed"
FAILURE_EMAIL_BODY = "Today's free Packt ebook grabbing has failed with exception: {}!\n\nCheck this out!"


class ConfigurationModel(object):
    """Contains all needed urls, passwords and packtpub account data stored in .cfg file"""

    def __init__(self, cfg_file_path):
        self.cfg_file_path = cfg_file_path
        self.cfg_folder_path = os.path.dirname(cfg_file_path)
        self.configuration = configparser.ConfigParser()
        if not self.configuration.read(self.cfg_file_path):
            raise configparser.Error('{} file not found'.format(self.cfg_file_path))
        self.book_infodata_log_file = self._get_config_ebook_extrainfo_log_filename()
        self.anticaptcha_clientkey = self.configuration.get("ANTICAPTCHA_DATA", 'key')
        self.packtpub_url = "https://www.packtpub.com"
        self.my_books_url = "https://www.packtpub.com/account/my-ebooks"
        self.login_url = "https://www.packtpub.com/register"
        self.freelearning_url = "https://www.packtpub.com/packt/offers/free-learning"
        self.req_headers = {'Connection': 'keep-alive',
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 '
                                          '(KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36'}
        self.my_packt_email, self.my_packt_password = self._get_config_login_data()
        self.download_folder_path, self.download_formats, self.download_book_titles = self._get_config_download_data()
        if not os.path.exists(self.download_folder_path):
            message = "Download folder path: '{}' doesn't exist".format(self.download_folder_path)
            logger.error(message)
            raise ValueError(message)

    def _get_config_ebook_extrainfo_log_filename(self):
        """Gets the filename of the ebook metadata log file."""
        return self.configuration.get("DOWNLOAD_DATA", 'ebook_extra_info_log_file_path')

    def _get_config_login_data(self):
        """Gets user login credentials."""
        email = self.configuration.get("LOGIN_DATA", 'email')
        password = self.configuration.get("LOGIN_DATA", 'password')
        return email, password

    def _get_config_download_data(self):
        """Downloads ebook data from the user account."""
        download_path = self.configuration.get("DOWNLOAD_DATA", 'download_folder_path')
        download_formats = tuple(form.replace(' ', '') for form in
                                 self.configuration.get("DOWNLOAD_DATA", 'download_formats').split(','))
        download_book_titles = None
        try:
            download_book_titles = [title.strip(' ') for title in
                                    self.configuration.get("DOWNLOAD_DATA", 'download_book_titles').split(',')]
            if len(download_book_titles) is 0:
                download_book_titles = None
        except configparser.Error:
            pass
        return download_path, download_formats, download_book_titles

    @staticmethod
    def convert_book_title_to_valid_string(title):
        """removes all unicodes and chars only valid in pathnames on Linux/Windows OS"""
        if title is not None:
            return re.sub(r'(?u)[^-\w.#]', '', title.strip().replace(' ', '_'))  # format valid pathname
        return None


class PacktPublishingFreeEbook(object):
    """Contains some methods to claim, download or send a free daily ebook"""

    download_formats = ('pdf', 'mobi', 'epub', 'code')
    session = None

    def __init__(self, cfg):
        self.cfg = cfg
        self.book_title = ""

    def login_required(func, *args, **kwargs):
        def login_decorated(self, *args, **kwargs):
            if self.session is None:
                self.__create_http_session()
            return func(self, *args, **kwargs)
        return login_decorated

    def __create_http_session(self):
        """Creates the http session"""
        form_data = {'email': self.cfg.my_packt_email,
                     'password': self.cfg.my_packt_password,
                     'op': 'Login',
                     'form_build_id': '',
                     'form_id': 'packt_user_login_form'}
        # to get form_build_id
        logger.info("Creating session...")
        self.session = requests.Session()
        self.session.headers.update(self.cfg.req_headers)
        r = self.session.get(self.cfg.login_url, timeout=10)
        content = BeautifulSoup(str(r.content), 'html.parser')
        form_build_id = [element['value'] for element in
                         content.find(id='packt-user-login-form').find_all('input', {'name': 'form_build_id'})]
        form_data['form_build_id'] = form_build_id[0]
        self.session.post(self.cfg.login_url, data=form_data)
        # check once again if we are really logged into the server
        r = self.session.get(self.cfg.my_books_url, timeout=10)
        if r.status_code is not 200 or r.text.find("register-page-form") != -1:
            message = "Login failed!"
            logger.error(message)
            raise requests.exceptions.RequestException(message)
        logger.info("Session created, logged in successfully!")

    def __claim_ebook_captchaless(self, url, html):
        claim_url = html.find(attrs={'class': 'twelve-days-claim'})['href']
        return self.session.get(self.cfg.packtpub_url + claim_url, timeout=10)

    def __claim_ebook_captchafull(self, url, html):
        key_pattern = re.compile("Packt.offers.onLoadRecaptcha\(\'(.+?)\'\)")
        website_key = key_pattern.search(html.find(text=key_pattern)).group(1)

        client = AnticaptchaClient(self.cfg.anticaptcha_clientkey)
        task = NoCaptchaTaskProxylessTask(url, website_key)
        job = client.createTask(task)
        job.join()
        captcha_solved_id = job.get_solution_response()

        claim_url = html.select_one('.free-ebook form')['action']
        return self.session.post(self.cfg.packtpub_url + claim_url,
                                 timeout=10,
                                 data={'g-recaptcha-response': captcha_solved_id})

    def __write_ebook_infodata(self, data):
        """
        Write result to file
        :param data: the data to be written down
        """
        info_book_path = os.path.join(self.cfg.cfg_folder_path, self.cfg.book_infodata_log_file)
        with open(info_book_path, "a") as output:
            output.write('\n')
            for key, value in data.items():
                output.write('{} --> {}\n'.format(key.upper(), value))
        logger.info("Complete information for '{}' have been saved".format(data["title"]))

    def __get_ebook_infodata(self, r):
        """
        Log grabbed book information to log file
        :param r: the previous response got when book has been successfully added to user library
        :return: the data ready to be written to the log file
        """
        logger.info("Retrieving complete information for '{}'".format(self.book_title))
        r = self.session.get(self.cfg.freelearning_url, timeout=10)
        result_html = BeautifulSoup(r.text, 'html.parser')
        last_grabbed_book = result_html.find('div', {'class': 'dotd-main-book-image'})
        book_url = last_grabbed_book.find('a').attrs['href']
        book_page = self.session.get(self.cfg.packtpub_url + book_url, timeout=10).text
        page = BeautifulSoup(book_page, 'html.parser')

        result_data = OrderedDict()
        result_data["title"] = self.book_title
        result_data["description"] = page.find('div', {'class': 'book-top-block-info-one-liner'}).text.strip()
        author = page.find('div', {'class': 'book-top-block-info-authors'})
        result_data["author"] = author.text.strip().split("\n")[0]
        result_data["date_published"] = page.find('time').text
        code_download_url = page.find('div', {'class': 'book-top-block-code'}).find('a').attrs['href']
        result_data["code_files_url"] = self.cfg.packtpub_url + code_download_url
        result_data["downloaded_at"] = time.strftime("%d-%m-%Y %H:%M")
        logger.success("Info data retrieved for '{}'".format(self.book_title))
        self.__write_ebook_infodata(result_data)
        return result_data

    def __get_my_all_books_data(self):
        """Gets data from all available ebooks"""
        logger.info("Getting data of all your books...")
        r = self.session.get(self.cfg.my_books_url, timeout=10)
        if r.status_code is not 200:
            message = "Cannot open {}, http GET status code != 200".format(self.cfg.my_books_url)
            logger.error(message)
            raise requests.exceptions.RequestException(message)
        logger.info("Opened '{}' successfully!".format(self.cfg.my_books_url))

        self.book_data = []
        my_books_html = BeautifulSoup(r.text, 'html.parser')
        all = my_books_html.find_all('div', {'class': 'product-line'})
        for line in all:
            if not line.get('nid'):
                continue
            title = line.find('div', {'class': 'title'}).getText().strip(' ').replace(' [eBook]', '')
            download_urls = {}
            for a in line.find_all('a'):
                url = a.get('href')
                for fm in self.download_formats:
                    if url.find(fm) != -1:
                        download_urls[fm] = url
            self.book_data.append({'title': title, 'download_urls': download_urls})

    @login_required
    def grab_ebook(self, log_ebook_infodata=False):
        """Grabs the ebook"""
        logger.info("Start grabbing eBook...")
        url = self.cfg.freelearning_url
        r = self.session.get(self.cfg.freelearning_url, timeout=10)
        if r.status_code is not 200:
            raise requests.exceptions.RequestException("http GET status code != 200")
        html = BeautifulSoup(r.text, 'html.parser')
        if 'href' not in html.find(attrs={'class': 'twelve-days-claim'}):
            logger.info("Captcha detected. Trying to solve it using anti-captcha.com.")
            r = self.__claim_ebook_captchafull(url, html)
        else:
            logger.info("No captcha detected.")
            r = self.__claim_ebook_captchaless(url, html)
        self.book_title = ConfigurationModel.convert_book_title_to_valid_string(
            html.find('div', {'class': 'dotd-title'}).find('h2').next_element)
        if r.status_code is 200 and r.text.find('My eBooks') != -1:
            logger.success("eBook: '{}' has been successfully grabbed!".format(self.book_title))
            if log_ebook_infodata:
                self.__get_ebook_infodata(r)
        else:
            message = "eBook: {} has not been grabbed!, does this promo exist yet? visit the page and check!".format(
                self.book_title)
            logger.error(message)
            raise requests.exceptions.RequestException(message)

    @login_required
    def download_books(self, titles=None, formats=None, into_folder=False):
        """
        Downloads the ebooks.
        :param titles: list('C# tutorial', 'c++ Tutorial') ;
        :param formats: tuple('pdf','mobi','epub','code');
        """
        # download ebook
        self.__get_my_all_books_data()
        if formats is None:
            formats = self.cfg.download_formats
            if formats is None:
                formats = self.download_formats
        if titles is not None:
            temp_book_data = [data for data in self.book_data
                              if any(ConfigurationModel.convert_book_title_to_valid_string(data['title']) ==
                                     ConfigurationModel.convert_book_title_to_valid_string(title) for title in
                                     titles)]
        else:  # download all
            temp_book_data = self.book_data
        if len(temp_book_data) == 0:
            logger.info("There is no books with provided titles: {} at your account!".format(titles))
        nr_of_books_downloaded = 0
        is_interactive = sys.stdout.isatty()
        for i, book in enumerate(temp_book_data):
            for form in formats:
                if form in list(temp_book_data[i]['download_urls'].keys()):
                    if form == 'code':
                        file_type = 'zip'
                    else:
                        file_type = form
                    title = ConfigurationModel.convert_book_title_to_valid_string(
                        temp_book_data[i]['title'])  # format valid pathname
                    logger.info("Title: '{}'".format(title))
                    if into_folder:
                        target_download_path = os.path.join(self.cfg.download_folder_path, title)
                        if not os.path.isdir(target_download_path):
                            os.mkdir(target_download_path)
                    else:
                        target_download_path = os.path.join(self.cfg.download_folder_path)
                    full_file_path = os.path.join(target_download_path,
                                                  "{}.{}".format(title, file_type))
                    if os.path.isfile(full_file_path):
                        logger.info("'{}.{}' already exists under the given path".format(title, file_type))
                    else:
                        if form == 'code':
                            logger.info("Downloading code for eBook: '{}'...".format(title))
                        else:
                            logger.info("Downloading eBook: '{}' in .{} format...".format(title, form))
                        try:
                            r = self.session.get(
                                self.cfg.packtpub_url + temp_book_data[i]['download_urls'][form],
                                timeout=100,
                                stream=True
                            )
                            if r.status_code is 200:
                                with open(full_file_path, 'wb') as f:
                                    total_length = int(r.headers.get('content-length'))
                                    num_of_chunks = (total_length / 1024) + 1
                                    for num, chunk in enumerate(r.iter_content(chunk_size=1024)):
                                        if chunk:
                                            if is_interactive:
                                                PacktPublishingFreeEbook.update_download_progress_bar(
                                                    num / num_of_chunks
                                                )
                                            f.write(chunk)
                                            f.flush()
                                    if is_interactive:
                                        PacktPublishingFreeEbook.update_download_progress_bar(-1)  # add end of line
                                if form == 'code':
                                    logger.success("Code for eBook: '{}' downloaded successfully!".format(title))
                                else:
                                    logger.success("eBook: '{}.{}' downloaded successfully!".format(title, form))
                                nr_of_books_downloaded += 1
                            else:
                                message = "Cannot download '{}'".format(title)
                                logger.error(message)
                                raise requests.exceptions.RequestException(message)
                        except Exception as e:
                            logger.error(e)
        logger.info("{} eBooks have been downloaded!".format(str(nr_of_books_downloaded)))

    @staticmethod
    def update_download_progress_bar(current_work_done):
        """Prints progress bar, current_work_done should be float value in range {0.0 - 1.0}, else prints '\n'"""
        if 0.0 <= current_work_done <= 1.0:
            print(
                "\r[PROGRESS] - [{0:50s}] {1:.1f}% ".format('#' * int(current_work_done * 50), current_work_done * 100),
                end="", )
        else:
            print("")


# Main
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
    parser.add_argument("-dc", "--dchosen", help="downloads chosen titles described in [download_book_titles] field",
                        action="store_true")
    parser.add_argument("-sgd", "--sgd", help="sends the grabbed eBook to google drive",
                        action="store_true")
    parser.add_argument("-m", "--mail", help="send download to emails defined in config file", default=False,
                        action="store_true")
    parser.add_argument("-sm", "--status_mail", help="send fail report email when script somehow failed", default=False,
                        action="store_true")
    parser.add_argument("-f", "--folder", help="downloads eBook into a folder", default=False,
                        action="store_true")
    parser.add_argument("-c", "--cfgpath", help="select folder where config file can be found",
                        default=os.path.join(os.getcwd(), "configFile.cfg"))
    parser.add_argument("--noauth_local_webserver", help="set if you want auth google_drive without local browser",
                        action="store_true")

    args = parser.parse_args()
    cfg_file_path = args.cfgpath
    into_folder = args.folder

    try:
        cfg = ConfigurationModel(cfg_file_path)
        ebook = PacktPublishingFreeEbook(cfg)

        # Grab the newest book
        if args.grab or args.grabl or args.grabd or args.sgd or args.mail:
            ebook.grab_ebook(log_ebook_infodata=args.grabl)

            # Send email about successful book grab. Do it only when book
            # isn't going to be emailed as we don't want to send email twice.
            if args.status_mail and not args.mail:
                from utils.mail import MailBook
                mb = MailBook(cfg_file_path)
                mb.send_info(
                    subject=SUCCESS_EMAIL_SUBJECT.format(
                        dt.datetime.now().strftime(DATE_FORMAT),
                        ebook.book_title
                    ),
                    body=SUCCESS_EMAIL_BODY.format(ebook.book_title)
                )

        # Download book(s) into proper location
        if args.grabd or args.dall or args.dchosen or args.sgd or args.mail:
            if args.dall:
                ebook.download_books(into_folder=into_folder)
            elif args.dchosen:
                ebook.download_books(cfg.download_book_titles, into_folder=into_folder)
            elif args.grabd:
                ebook.download_books([ebook.book_title], into_folder=into_folder)
            else:
                cfg.download_folder_path = os.getcwd()
                ebook.download_books([ebook.book_title], into_folder=into_folder)

        # Send downloaded book(s) by mail or to google_drive
        if args.sgd or args.mail:
            paths = [
                os.path.join(cfg.download_folder_path, path)
                for path in os.listdir(cfg.download_folder_path)
                if os.path.isfile(path) and ebook.book_title in path
            ]
            if args.sgd:
                from utils.google_drive import GoogleDriveManager
                google_drive = GoogleDriveManager(cfg_file_path)
                google_drive.send_files(paths)
            else:
                from utils.mail import MailBook
                mb = MailBook(cfg_file_path)
                pdf_path = None
                mobi_path = None
                try:
                    pdf_path = [path for path in paths if path.endswith('.pdf')][-1]
                    mobi_path = [path for path in paths if path.endswith('.mobi')][-1]
                except IndexError:
                    pass
                if pdf_path:
                    mb.send_book(pdf_path)
                if mobi_path:
                    mb.send_kindle(mobi_path)
            for path in paths:
                os.remove(path)

        logger.success("Good, looks like all went well! :-)")
    except Exception as e:
        logger.error("Exception occurred {}".format(e))
        if args.status_mail:
            from utils.mail import MailBook
            mb = MailBook(cfg_file_path)
            mb.send_info(
                subject=FAILURE_EMAIL_SUBJECT.format(dt.datetime.now().strftime(DATE_FORMAT)),
                body=FAILURE_EMAIL_BODY.format(str(e))
            )
        sys.exit(2)
