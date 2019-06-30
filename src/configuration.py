import configparser
import os

from utils.logger import get_logger

logger = get_logger(__name__)


class ConfigurationModel(object):
    """Contains all needed data stored in configuration file."""

    def __init__(self, cfg_file_path):
        self.configuration = configparser.ConfigParser()
        self.configuration.read(cfg_file_path)

    @property
    def packt_login_credentials(self):
        """Return Packt user login credentials."""
        return self.configuration.get('LOGIN_DATA', 'email'), self.configuration.get('LOGIN_DATA', 'password')

    @property
    def anticaptcha_api_key(self):
        """Return AntiCaptcha API key."""
        return self.configuration.get("ANTICAPTCHA_DATA", 'key')

    @property
    def config_download_data(self):
        """Return download configuration data."""
        download_path = self.configuration.get("DOWNLOAD_DATA", 'download_folder_path')
        if not os.path.exists(download_path):
            message = "Download folder path: '{}' doesn't exist".format(download_path)
            logger.error(message)
            raise ValueError(message)
        download_formats = tuple(form.replace(' ', '') for form in
                                 self.configuration.get("DOWNLOAD_DATA", 'download_formats').split(','))
        return download_path, download_formats
