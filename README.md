## Free Learning PacktPublishing scripts

**grabPacktFreeBook.py** - script that automatically grabs a daily free eBook from https://www.packtpub.com/packt/offers/free-learning

**packtFreeBookDownloader.py** - script which downloads already claimed eBooks from your account https://www.packtpub.com/account/my-ebooks


### Requirements:
* Install either Python 2.x or 3.x
* Install pip (if you have not installed it yet).
  To install pip, download:  https://bootstrap.pypa.io/get-pip.py ,
  then run the following command:

  ```  
  python get-pip.py
  ```
  
  Once pip has been installed, run the following:
  
  ```
  pip install requests beautifulsoup4

  ```
  
  If you use Python 2.x :
  
  ```  
  pip install future

  ```
  
* change your login credentials in **configFile.cfg** file
  


### Usage:
**[grabPacktFreeBook.py]**
* You can manually run grabPacktFreeBook.py script to get the book:

  ```
  $ python grabPacktFreeBook.py
  ```
* Or set it to be invoked automatically:
  
  **LINUX** (tested on UBUNTU):

  **CRON** setup (more: https://help.ubuntu.com/community/CronHowto) :
  
  ```
  $ sudo crontab -e
  ```
  
  paste (modify all paths correctly according to your setup):
  
  ```
  0 12 * * * cd /home/me/Desktop/PacktScripts/ && /usr/bin/python3 grabPacktFreeBook.py > /home/me/Desktop/PacktScripts/grabPacktFreeBook.log 2>&1
  ```
  
  and save the crontab file. To verify if CRON fires up the script correctly, run a command:
  
  ```
  $ sudo grep CRON /var/log/syslog
  ```
  
  **WINDOWS** (tested on win7):
  
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
  
* To download the already claimed book from your account set field **downloadBookAfterClaim** in **configFile.cfg** to **YES**  and modify **downloadFormats** you want to get


**[packtFreeBookDownloader.py]**
* It can be used to download your books from PacktPublishing

* Just fire up the script to download all your already claimed books in declared formats (look at **downloadFormats** in **configFile.cfg**). To downlaod all books the field: **downloadBookTitles** shall be commented out like shown below:

  ```
  ;downloadBookTitles: Unity 4.x Game AI Programming , Multithreading in C# 5.0 Cookbook
  ```

* To download chosen titles from your account put them into **downloadBookTitles** in **configFile.cfg**
  
  **configFile.cfg** example:
    download **'Unity 4.x Game AI Programming'** and  **'Multithreading in C# 5.0 Cookbook'** books in all available formats (pdf, epub, mobi) with zipped source code file

  ```
  [LOGIN_DATA]
  email= youremail@youremail.com
  password= yourpassword    

  [DOWNLOAD_DATA]
  downloadFolderPath: C:\Users\me\Desktop\myEbooksFromPackt
  downloadBookAfterClaim: YES
  downloadFormats: pdf, epub, mobi, code
  downloadBookTitles: Unity 4.x Game AI Programming , Multithreading in C# 5.0 Cookbook
  
  ```  

In case of any questions feel free to ask, happy grabbing!
