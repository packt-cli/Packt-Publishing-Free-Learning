[![Build Status](https://travis-ci.org/igbt6/Packt-Publishing-Free-Learning.svg?branch=master)](https://travis-ci.org/igbt6/Packt-Publishing-Free-Learning)

## Free Learning PacktPublishing script

**packtPublishingFreeEbook.py** - script that automatically grabs and download a daily free eBook from https://www.packtpub.com/packt/offers/free-learning
  You can use it also to download the already claimed eBooks from your account https://www.packtpub.com/account/my-ebooks

The script uses [anti-captcha.com](https://anti-captcha.com/) service to bypass the Recaptcha captcha to function fully automatically. Anticaptcha.com employs people to solve captcha test use whether or not the user is human. The service costs about $ 2 per thousand captcha test, allowing you to operate for a few dollars over the years.

### Requirements:
* Install either Python 2.7 or 3.x
* Install pip (if you have not installed it yet).
  To install pip, download:  https://bootstrap.pypa.io/get-pip.py ,
  then run the following command:

  ```  
  python get-pip.py
  ```
* Optionally install [*virtualenv*](http://docs.python-guide.org/en/latest/dev/virtualenvs/) (pip install virtualenv)

* Once pip has been installed, run the following command:
  ```
  pip install -r requirements.txt
  ```

* change a name of **configFileTemplate.cfg** to **configFile.cfg**  
* change your login credentials in **configFile.cfg** file
* register on [anti-captcha.com](https://anti-captcha.com/), grab API key and put in **configFile.cfg**

### Usage:
1. The script **[packtPublishingFreeEbook.py]** might be fired up with several arguments:

  - Option *-g* [--grab] - claims (grabs) a daily eBook into your account
  ```
  python packtPublishingFreeEbook.py -g
  ```

  - Option *-gl* [--grabl] - claims (grabs) a daily eBook into your account and save book info to log file specified in config file
  ```
  python packtPublishingFreeEbook.py -gl
  ```

  - Option *-gd* [--grabd] - claims (grabs) a daily ebook and downloads the title afterwards to the location specified under *[download_folder_path]* field (configFile.cfg file)
  ```
  python packtPublishingFreeEbook.py -gd
  ```
  
  - Option *-da* [--dall] - downloads all ebooks from your account
  ```
  python packtPublishingFreeEbook.py -da
  ```

  - SubOption *--date_from* - downloads all books grabbed after this date (inclusive, YYYY/MM/DD format)
  ```
  python packtPublishingFreeEbook.py -da --date_from=2018/03/19 --date_to=2018/03/20
  ```

  - SubOption *--date-to* - downloads all books grabbed before this date (inclusive, YYYY/MM/DD format)
  ```
  python packtPublishingFreeEbook.py -da --date_from=2018/03/19 --date_to=2018/03/20
  ```

  - Option *-sgd* [--sgd] - claims and uploads a book to *[gdFolderName]* folder onto Google Drive (more about setup Google Drive api in GOOGLE_DRIVE_API Setup)  
  ```
  python packtPublishingFreeEbook.py -sgd
  ```
  
  - Option *-m* [--mail] - claims and sends an email with the newest book in PDF format (and MOBI if is also downloaded; see mail options confguration under [MAIL] path in *configFile.cfg*)
  ```
  python packtPublishingFreeEbook.py -m
  ```
  
  - SubOption *-sm* [--status_mail] - sends fail report email whether script execution was successful
  ```
  python packtPublishingFreeEbook.py -gd -sm
  ```
  
  - SubOption *-f* [--folder] - downloads an ebook into a created folder, named as ebook's title
  ```
  python packtPublishingFreeEbook.py -gd -f
  ```
  
  - SubOption *-c* [--cfgpath] - selects folder where config file can be found (default: cwd)
  ```
  python packtPublishingFreeEbook.py -gd -c /home/usr/
  ```
  
2. You can set the script to be invoked automatically:
  
  **LINUX** (tested on UBUNTU 16.04):
  
  modify access permissions of the script:
  
  ```
  $ chmod a+x packtPublishingFreeEbook.py 
  ```
  
  **cron** setup (more: https://help.ubuntu.com/community/CronHowto) :
  
  ```
  $ sudo crontab -e
  ```
  
  paste (modify all paths correctly according to your setup):
  
  ```
  0 12 * * * cd /home/me/Desktop/PacktScripts/ && /usr/bin/python3 packtPublishingFreeEbook.py -gd > /home/me/Desktop/PacktScripts/packtPublishingFreeEbook.log 2>&1
  ```
  
  and save the crontab file. To verify if CRON fires up the script correctly, run a command:
  
  ```
  $ sudo grep CRON /var/log/syslog
  ```
  
  **WINDOWS** (tested on win7,8,10):
  
  **schtasks.exe** setup (more info: https://technet.microsoft.com/en-us/library/cc725744.aspx) :
  
  To create the task that will be called at 12:00 everyday, run the following command in **cmd** (modify all paths according to your setup):
  
  ```
  schtasks /create /sc DAILY /tn "grabEbookFromPacktTask" /tr "C:\Users\me\Desktop\GrabPacktFreeBook\grabEbookFromPacktTask.bat" /st 12:00
  ```
  
  To check if the "grabEbookFromPacktTask" has been added to all scheduled tasks on your computer:
  
  ```
  schtasks /query
  ```
  
  To run the task manually:
  
  ```
  schtasks /run /tn "grabEbookFromPacktTask"
  ```  
  
  To delete the task:
  
  ```
  schtasks /delete /tn "grabEbookFromPacktTask"
  ```
  
  If you want to log all downloads add -l switch to grabEbookFromPacktTask i.e.
  ```
  schtasks /create /sc DAILY /tn "grabEbookFromPacktTask" /tr "C:\Users\me\Desktop\GrabPacktFreeBook\grabEbookFromPacktTask.bat -l" /st 12:00
  ``` 
  
  If you want to additionaly make command line windows stay open after download add -p switch i.e.
  ```
  schtasks /create /sc DAILY /tn "grabEbookFromPacktTask" /tr "C:\Users\me\Desktop\GrabPacktFreeBook\grabEbookFromPacktTask.bat -l -p" /st 12:00
  ``` 

* EXAMPLE: download all ebooks in all available formats (pdf, epub, mobi) with zipped source code file from your packt account
  
  To download all titles from your account prepare your **configFile.cfg** as shown below:
  
  **configFile.cfg** example:
  ```
    [LOGIN_DATA]
    email: youremail@youremail.com
    password: yourpassword    
    
    [DOWNLOAD_DATA]
    download_folder_path: C:\Users\me\Desktop\myEbooksFromPackt
    download_formats: pdf, epub, mobi, code
    ebook_extra_info_log_file_path: eBookMetadata.log
    
    [GOOGLE_DRIVE_DATA]
    gd_app_name: GoogleDriveManager
    gd_folder_name: PACKT_EBOOKS
  ```
  run:
  ```
    python packtPublishingFreeEbook.py -da
  ```

### GOOGLE_DRIVE_API Setup:
Full info about the Google Drive python API can be found [here](https://developers.google.com/drive/v3/web/quickstart/python)  

1. Turn on the Drive API  
  - Use [this wizard](https://console.developers.google.com/flows/enableapi?apiid=drive) to create or select a project in the Google Developers Console and automatically turn on the API. Click Continue, then Go to credentials.
  - On the *Add credentials to your project page*, click the *Cancel* button.
  - At the top of the page, select the OAuth consent screen tab. Select an Email address, enter a *Product name* if not already set, and click the Save button.
  - Select the Credentials tab, click the Create credentials button and select *OAuth client ID*.
  - Select the application type *Other*, enter the name *"GoogleDriveManager"*, and click the Create button.
  - Click *OK* to dismiss the resulting dialog.
  - Click the file_download (Download JSON) button to the right of the client ID.
  - Move this file to your working directory and rename it *"client_secret.json"*

2. Install the Google Client Library
  - Run the following command to install the library using pip:
  ```
  pip install --upgrade google-api-python-client  or pip install --upgrade google-api-python-client-py3
  ``` 

3. Create credentials folder:
  - Simply, just fire up the script with *-sgd* argument; During first launch you will see a prompt in your browser asking for permissions, click then *allow*
  ```
  python packtPublishingFreeEbook.py -sgd
  ```  
  - Or if you're unable to launch browser locally (e.g. you're connecting through SSH without X11 forwarding) use this command once, follow instructions and give permission and later you can use normal command (without *--noauth_local_webserver*).
  ```
  python packtPublishingFreeEbook.py -sgd --noauth_local_webserver
  ```  
4. Already done!
  - Run the same command as above to claim and upload the eBook to Google Drive.


In case of any questions feel free to ask, happy grabbing!
