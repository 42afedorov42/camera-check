## Script for checking BlueCherry video server cameras
## The script checks:
- Continuous(C)/Motion(M) recording mode  
  If Motion (M), then there are no more checks and a record is added to the log that the camera is recording on motion  
  
  If Continuous (C), then proceed to the following checks:  
  - existence of the directory/mnt/video/current_year/current_month/current_day/id_camera;  
  - increasing the size of the directory/mnt/video/current_year/current_month/current_day/id_camera;  
  - a frame from a stream to a black and white image according to the average color of the RGB table;  
  - the percentage of image sharpness.  

## Installation
1. go as root;  
Create .env file in the script directory  
<pre><code>sudo vim .env</code></pre>  
with your credetionals:  
<pre><code>
CHERRY_USER_DB=your_cherry_user_db  
CHERRY_PASSWORD_DB=your_cherry_password_db  
CHERRY_USER=your_cherry_user_web_user  
CHERRY_PASSWORD=your_cherry_user_web_password  
CHERRY_IP=your_ip_blue_cherry
</code></pre> 
2. install requirements  
<pre><code>pip3 install requirements.txt</code></pre>
3. run script  
<pre><code>python3 camera-check.py</code></pre> 

## Schedule a script to run in cron as root
crontab -e
Example:
<pre><code>16,26,36,46,56 * * * *. $HOME/.bashrc; /usr/bin/ python3/usr/local/bin/camera-check/camera-check.py</code></pre>
It is not advisable to use such an entry:  
*/9 * * * * . $HOME/.bashrc; /usr/bin/python3/ usr/local/bin/camera_check.py  
since the minutes will start from 0 every hour and the scheduled task may fall at 00:00, at this moment the directories with camera recordings may not yet be created.