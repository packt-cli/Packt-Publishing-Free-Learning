#!/usr/bin/env python
import sys
import requests
import os
import configparser
import argparse
import httplib2
import io
import oauth2client
from oauth2client import client
from oauth2client import tools
import apiclient
from apiclient import discovery
from apiclient.http import MediaFileUpload
from apiclient.http import MediaIoBaseDownload

from utils import *
logger = log_manager.get_logger(__name__)

####################################-GOOGLE DRIVE MANAGER############################################

SCOPES = 'https://www.googleapis.com/auth/drive'
CLIENT_SECRET_FILE = 'client_secret.json'
FILE_TYPE=frozenset(["FILE","FOLDER"])

class GoogleDriveManager():
    """Allows to upload and download new content to Google Drive"""
    
    def __init__(self, cfg_file_path):
        self.__set_config_data(cfg_file_path)
        self._root_folder= GoogleDriveFile(self.folder_name)
        self._credentials = self.__get_credentials()
        self._http_auth = self._credentials.authorize(httplib2.Http())
        self._service = discovery.build('drive', 'v3', http=self._http_auth)
        self._root_folder.id=self.check_if_file_exist_create_new_one(self._root_folder.name)
        self._mimetypes = {'pdf':'application/pdf', 'zip':'application/zip', 'mobi':'application/x-mobipocket-ebook', 'epub':'application/epub+zip'}
        # downgrading logging level for google api
        logging.getLogger("apiclient").setLevel(logging.WARNING)


    def __set_config_data(self, cfg_file_path):
        """Sets all the config data for Google drive manager"""
        configuration = configparser.ConfigParser()
        if not configuration.read(cfg_file_path):
            raise configparser.Error('{} file not found'.format(cfg_file_path))
        self.app_name = configuration.get("GOOGLE_DRIVE_DATA", 'gdAppName')
        self.folder_name = configuration.get("GOOGLE_DRIVE_DATA", 'gdFolderName')
	        
    def __get_credentials(self):
        '''Gets valid user credentials from storage.
        If nothing has been stored, or if the stored credentials are invalid,
        the OAuth2 flow is completed to obtain the new credentials.
        Returns: the obtained credentials.
        '''
        home_dir = self.cfg_file_path
        credential_dir = os.path.join(home_dir, '.credentials')
        if not os.path.exists(credential_dir):
            os.makedirs(credential_dir)
        credential_path = os.path.join(credential_dir, self.app_name+'.json')
        store = oauth2client.file.Storage(credential_path)
        credentials = store.get()
        if not credentials or credentials.invalid:
            flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
            flow.user_agent = self.app_name
            try:
                import argparse
                parser = argparse.ArgumentParser(description=__doc__,
                         formatter_class=argparse.RawDescriptionHelpFormatter,
                         parents=[tools.argparser])
                flags = parser.parse_args(sys.argv[2:])  
            except ImportError:
                flags = None
            if flags:
                credentials = tools.run_flow(flow, store, flags)
            else: # To be compatible with 2.6
                credentials = tools.run(flow, store)
            logger.success('Storing credentials to ' + credential_path)
        return credentials
       
    def __find_folder_or_file_by_name(self,file_name,parent_id=None):
        if(file_name ==None or len(file_name)==0):
            return False
        page_token = None
        if parent_id is not None:
            query=("name = '%s' and '%s' in parents"%(file_name,parent_id))
        else:
            query=("name = '%s'"%file_name)
        while True:
            response = self._service.files().list(q=query,spaces='drive',fields='nextPageToken, files(id, name, parents)',pageToken=page_token).execute()
            for file in response.get('files', []):
                logger.debug('Found file: %s (%s) %s' % (file.get('name'), file.get('id'),file.get('parents')))
                return file.get('id')
            page_token = response.get('nextPageToken', None)
            if page_token is None:
                return False;
        
    def check_if_file_exist_create_new_one(self,file_name,file_type="FOLDER",parent_id=None):
        if file_type not in FILE_TYPE:
            raise ValueError("Incorrect file_type arg. Allowed types are: %s"%(', '.join(list(FILE_TYPE))))
        id = self.__find_folder_or_file_by_name(file_name,parent_id)
        if id:
            logger.debug(file_name + " exists")
        else:
            logger.debug(file_name + " does not exist")
            if file_type is "FILE":
                pass #TODO
            else: #create new folder
                id=self.__create_new_folder(file_name,parent_id)

        return id
        
    
    def list_all_files_in_main_folder(self):
        results = self._service.files().list().execute()
        items = results.get('files', [])
        if not items:
            logger.debug('No files found.')
        else:
            logger.debug('Files:')
            for item in items:
                logger.debug('{0} ({1})'.format(item['name'], item['id']))
        
    def __create_new_folder(self,folder_name,parent_folders_id =None):
        parent_id= parent_folders_id if parent_folders_id is None else [parent_folders_id]
        file_metadata = {
            'name' : folder_name,
            'mimeType' : 'application/vnd.google-apps.folder',
            'parents': parent_id
        }
        file = self._service.files().create(body=file_metadata, fields='id').execute()
        logger.success('Created Folder ID: %s' % file.get('id'))
        return file.get('id')
    

    def __extract_filename_ext_and_mimetype_from_path(self, path):
        splitted_path= os.path.split(path)
        file_name = splitted_path[-1]
        file_extension = file_name.split('.')[-1]
        mime_type = None
        if  file_extension in self._mimetypes:
            mime_type = self._mimetypes[file_extension]
        return file_name, file_extension, mime_type

    def __insert_file_into_folder(self, file_name, path, parent_folder_id, file_mime_type=None):
        parent_id= parent_folders_id if parent_folder_id is None else [parent_folder_id]
        file_metadata = {
          'name' : file_name,
          'parents': parent_id
        }
        media = MediaFileUpload(path,mimetype=file_mime_type,  # if None, it will be guessed 
                                resumable=True)
        file = self._service.files().create(body=file_metadata,media_body=media,fields='id').execute()
        logger.debug('File ID: {}'.format(file.get('id')))
        return file.get('id') 
       
    def send_files(self, file_paths):
        if file_paths is None or len(file_paths)==0:
            raise ValueError("Incorrect file paths argument format")
        for path in file_paths:
            if os.path.exists(path):
                try:
                    file_attrs = self.__extract_filename_ext_and_mimetype_from_path(path)
                    if not self.__find_folder_or_file_by_name(file_attrs[0], self._root_folder.id):
                        self.__insert_file_into_folder(file_attrs[0], path, self._root_folder.id, file_attrs[2])
                        logger.success('File {} succesfully sent to Google Drive'.format(file_attrs[0]))
                    else:
                        logger.info('File {} already exists on Google Drive'.format(file_attrs[0]))
                except Exception as e:
                        logger.error('Error {} occurred while sending file: {} to Google Drive'.format(e, file_attrs[0]))
                               
    def download_file(self,file_name,file_id):
        request = self._service.files().get_media(fileId=file_id)
        fh = io.FileIO(file_name, 'wb')
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
            logger.debug("Download %d%%." % int(status.progress() * 100))
               
class GoogleDriveFile():
    ''' Helper class that describes File or Folder stored on GoogleDrive server'''
    def __init__(self,file_name):
        self.name= file_name
        self.id =None
        self.parent_id=''

