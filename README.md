[![Version](https://img.shields.io/pypi/v/packt.svg)](https://pypi.org/project/packt/)
[![Python Versions](https://img.shields.io/pypi/pyversions/packt.svg)](https://pypi.org/project/packt/)
[![Build Status](https://travis-ci.org/luk6xff/Packt-Publishing-Free-Learning.svg?branch=master)](https://travis-ci.org/igbt6/Packt-Publishing-Free-Learning)

## Free Learning Packt Publishing script

`packt-cli` is a Python script that allows to automatically grab and download a daily Free
Learning Packt ebook from https://www.packtpub.com/packt/offers/free-learning.
You can also use it to download already claimed ebooks from your Packt
account.

The script uses [anti-captcha.com](https://anti-captcha.com/) service to bypass
the Recaptcha captcha to function fully automatically. Anti Captcha employs
people to solve captcha tests. The service costs about $2 per thousand captcha
test, allowing you to operate for a few dollars over the years.

### Installation

To install current version of script simply run
```
pip install packt --upgrade
```

You may want to install it inside new [virtualenv](http://docs.python-guide.org/en/latest/dev/virtualenvs/).

### Usage

The `packt-cli` script might be executed with several optional arguments.

- Option *-g* [--grab] - claims (grabs) a daily eBook into your account
```
packt-cli -g
```

- Option *-gd* [--grabd] - claims (grabs) a daily ebook and downloads the title afterwards to the location specified under *[download_folder_path]* field (configFile.cfg file)
```
packt-cli -gd
```

- Option *-da* [--dall] - downloads all ebooks from your account
```
packt-cli -da
```

- Option *-sgd* [--sgd] - claims and uploads a book to *[gdFolderName]* folder onto Google Drive (more about that in Google Drive API Setup section)
```
packt-cli -sgd
```

- Option *-m* [--mail] - claims and sends an email with the newest book in PDF format (and MOBI if is also downloaded; see mail options confguration under [MAIL] path in *configFile.cfg*)
```
packt-cli -m
```

- SubOption *-sm* [--status_mail] - sends fail report email whether script execution was successful
```
packt-cli -gd -sm
```

- SubOption *-f* [--folder] - downloads an ebook into a created folder, named as ebook's title
```
packt-cli -gd -f
```

- SubOption *-c* [--cfgpath] - selects folder where config file can be found (default: cwd)
```
packt-cli -gd -c /home/usr/
```

#### Example

Download all ebooks in all available formats  (pdf, epub, mobi) with zipped source code file from your Packt account.

To download all ebooks in all available formats from your Packt account, you have to prepare your config file as shown below:

```
[LOGIN_DATA]
email: youremail@youremail.com
password: yourpassword

[DOWNLOAD_DATA]
download_folder_path: C:\Users\me\Desktop\myEbooksFromPackt
download_formats: pdf, epub, mobi, code

[GOOGLE_DRIVE_DATA]
gd_app_name: GoogleDriveManager
gd_folder_name: PACKT_EBOOKS
```
run:
```
  packt-cli -da
```

### Scheduled script execution setup

#### Debian

On Debian (and any Debian-based Linux distribution) you may use [cron](https://help.ubuntu.com/community/CronHowto) job to schedule script execution. To do this run `crontab -e` and add the following line to crontab file.

```
0 12 * * * path/to/virtualenv/bin/packt-cli -gd > path/to/log/file 2>&1
```

Adjust execution time and paths according to your setup. To verify if cron executes the script as expected, run
```
$ sudo grep CRON /var/log/syslog
```

#### Windows

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

### Google Drive API Setup

Full info about the Google Drive Python API can be found [here](https://developers.google.com/drive/v3/web/quickstart/python).

1. Turn on the Google Drive API
  - Use [this wizard](https://console.developers.google.com/flows/enableapi?apiid=drive) to create or select a project in the Google Developers Console and automatically turn on the API. Click `Continue`, then `Go to credentials`.
  - On the `Add credentials to your project page`, click the `Cancel` button.
  - At the top of the page, select the `OAuth consent screen` tab. Select an email address, enter a product name if not already set, and click the Save button.
  - Select the `Credentials` tab, click the `Create credentials` button and select `OAuth client ID`.
  - Select the application type `Other`, enter the name `GoogleDriveManager`, and click the `Create` button.
  - Click `OK` to dismiss the resulting dialog.
  - Click the file_download (`Download JSON`) button to the right of the client ID.
  - Move this file next to the config file and rename it to `client_secret.json`.

2. Create credentials folder:
  - Simply, just fire up the script with `-sgd` argument; During first launch you will see a prompt in your browser asking for permissions, click then *allow*
  ```
  packt-cli -sgd
  ```
  - Or if you're unable to launch browser locally (e.g. you're connecting through SSH without X11 forwarding) use this command once, follow instructions and give permission and later you can use normal command (without `--noauth_local_webserver`).
  ```
  packt-cli -c /path/to/config/file.cfg -sgd --noauth_local_webserver
  ```
  The command parameters number and their order is important!

3. Already done!
  - Run the same command as above to claim and upload the eBook to Google Drive.


In case of any questions feel free to ask, happy grabbing!
