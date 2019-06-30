import click
import datetime as dt
import os
import sys

from api import PacktAPIClient
from claimer import claim_product, get_all_books_data
from configuration import ConfigurationModel
from downloader import download_products, slugify_product_name
from utils.logger import get_logger

logger = get_logger(__name__)

DATE_FORMAT = "%Y/%m/%d"

SUCCESS_EMAIL_SUBJECT = "{} New free Packt ebook: \"{}\""
SUCCESS_EMAIL_BODY = "A new free Packt ebook \"{}\" was successfully grabbed. Enjoy!"
FAILURE_EMAIL_SUBJECT = "{} Grabbing a new free Packt ebook failed"
FAILURE_EMAIL_BODY = "Today's free Packt ebook grabbing has failed with exception: {}!\n\nCheck this out!"

AVAILABLE_DOWNLOAD_FORMATS = ('pdf', 'mobi', 'epub', 'video', 'code')


@click.command()
@click.option(
    '-c',
    '--cfgpath',
    default=os.path.join(os.getcwd(), 'configFile.cfg'),
    type=click.Path(exists=True),
    help='Config file path.'
)
@click.option('-g', '--grab', is_flag=True, help='Grab Free Learning Packt ebook.')
@click.option('-gd', '--grabd', is_flag=True, help='Grab Free Learning Packt ebook and download it afterwards.')
@click.option('-da', '--dall', is_flag=True, help='Download all ebooks from your Packt account.')
@click.option('-sgd', '--sgd', is_flag=True, help='Grab Free Learning Packt ebook and download it to Google Drive.')
@click.option('-m', '--mail', is_flag=True, help='Grab Free Learning Packt ebook and send it by an email.')
@click.option('-sm', '--status_mail', is_flag=True, help='Send an email whether script execution was successful.')
@click.option('-f', '--folder', is_flag=True, default=False, help='Download ebooks into separate directories.')
@click.option(
    '--noauth_local_webserver',
    is_flag=True,
    default=False,
    help='See Google Drive API Setup section in README.'
)
def packt_cli(cfgpath, grab, grabd, dall, sgd, mail, status_mail, folder, noauth_local_webserver):
    config_file_path = cfgpath
    into_folder = folder

    try:
        cfg = ConfigurationModel(config_file_path)
        product_data = None
        api_client = PacktAPIClient(*cfg.packt_login_credentials)

        # Grab the newest book
        if grab or grabd or sgd or mail:
            product_data = claim_product(api_client, cfg.anticaptcha_api_key)

            # Send email about successful book grab. Do it only when book
            # isn't going to be emailed as we don't want to send email twice.
            if status_mail and not mail:
                from utils.mail import MailBook
                mb = MailBook(config_file_path)
                mb.send_info(
                    subject=SUCCESS_EMAIL_SUBJECT.format(
                        dt.datetime.now().strftime(DATE_FORMAT),
                        product_data['title']
                    ),
                    body=SUCCESS_EMAIL_BODY.format(product_data['title'])
                )

        # Download book(s) into proper location.
        if grabd or dall or sgd or mail:
            download_directory, formats = cfg.config_download_data
            download_directory = download_directory if (dall or grabd) else os.getcwd()  # cwd for temporary downloads
            formats = formats or AVAILABLE_DOWNLOAD_FORMATS

            if dall:
                download_products(
                    api_client,
                    download_directory,
                    formats,
                    get_all_books_data(api_client),
                    into_folder=into_folder
                )
            elif grabd:
                download_products(api_client, download_directory, formats, [product_data], into_folder=into_folder)
            else:  # sgd or mail
                download_products(api_client, download_directory, formats, [product_data], into_folder=False)

        # Send downloaded book(s) by mail or to Google Drive.
        if sgd or mail:
            paths = [
                os.path.join(download_directory, path)
                for path in os.listdir(download_directory)
                if os.path.isfile(path) and slugify_product_name(product_data['title']) in path
            ]
            if sgd:
                from utils.google_drive import GoogleDriveManager
                google_drive = GoogleDriveManager(config_file_path)
                google_drive.send_files(paths)
            else:
                from utils.mail import MailBook
                mb = MailBook(config_file_path)
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
        if status_mail:
            from utils.mail import MailBook
            mb = MailBook(config_file_path)
            mb.send_info(
                subject=FAILURE_EMAIL_SUBJECT.format(dt.datetime.now().strftime(DATE_FORMAT)),
                body=FAILURE_EMAIL_BODY.format(str(e))
            )
        sys.exit(2)
