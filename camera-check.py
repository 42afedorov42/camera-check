#!/usr/bin/python3
import os
from pathlib import Path
from datetime import datetime
import time
import cv2
import numpy
import pymysql.cursors
from loguru import logger
from dotenv import load_dotenv


def main():
    logging()

    load_dotenv('.env')
    CHERRY_USER_DB = os.getenv('CHERRY_USER_DB')
    CHERRY_PASSWORD_DB = os.getenv('CHERRY_PASSWORD_DB')
    CHERRY_USER = os.getenv('CHERRY_USER')
    CHERRY_PASSWORD = os.getenv('CHERRY_PASSWORD')
    CHERRY_IP = os.getenv('CHERRY_IP')
    stream_template = f'https://{CHERRY_USER}:{CHERRY_PASSWORD}@{CHERRY_IP}\
                        :7001/media/mjpeg?multipart=true&id='
    exceptions = [
        f'https://{CHERRY_USER}:{CHERRY_PASSWORD}@{CHERRY_IP}\
        :7001/media/mjpeg?multipart=true&id=000049',
    ]

    now = datetime.now()
    year_folder = now.strftime("%Y")
    month_folder = now.strftime("%m")
    day_folder = now.strftime("%d")
    day_of_week_today = now.strftime("%A")
    hour_now = now.strftime("%H")
    date_now = now.strftime("%d-%m-%Y_%H-%M")
    hour_of_week_now = get_hour_of_week(day_of_week_today)

    connection = pymysql.connect(
        host='localhost',
        user=CHERRY_USER_DB,
        password=CHERRY_PASSWORD_DB,
        db='bluecherry'
    )

    for id_, cam_name, cam_schedule_override_global, cam_sched in cherry_cams(connection):
        cams_rec_path = f"/mnt/video/{year_folder}/{month_folder}/{day_folder}/{id_}"
        check_analyzed_frame_path(cams_rec_path)
        if recording_mode_continuous(hour_of_week_now, connection, cam_schedule_override_global, cam_sched) is True:
            if cam_rec_directory_check(cams_rec_path, cam_name) is True:
                if cam_rec_size_check(cams_rec_path, cam_name) is True:
                    cam_stream = stream_template + id_
                    if cam_stream in exceptions:
                        logger.info("Camera ("+cam_name+") added to exception")
                    capture = cv2.VideoCapture(cam_stream)
                    ret, frame = capture.read()
                    analyzed_frame_path = f"{cams_rec_path}_frames/frame_{cam_name}_{date_now}.jpg"
                    cv2.imwrite(analyzed_frame_path, frame)
                    analyzed_frame = cv2.imread(analyzed_frame_path)
                    color_definition(analyzed_frame, cam_name)
                    sharpness_rating(frame, cam_name)
    return None


def logging():
    """Adding logging.

    """
    log_path = '/var/log/bluecherry_cams/'
    if os.path.exists("log_path") is False:
        Path(log_path).mkdir(parents=True, exist_ok=True)
    logger.remove()
    logger.add(log_path+'cams_check.log',
                format="<green>{time:MMM DD HH:mm:ss}</green> {message}",
                rotation="500 MB",
                compression="gz")
    logger.info("The script is running.")
    return None


def check_analyzed_frame_path(cams_rec_path):
    """Сreating a directory for analyzed frames if it does not exist
    in the videotapes directory.

    """
    if os.path.exists(f"{cams_rec_path}_frames/") is False:
        Path(cams_rec_path).mkdir(parents=True, exist_ok=True)
    return None


def cherry_cams(connection):
    """Get all cameras from the BlueCherry database for analysis.
    Since recordings from cameras in the title use a camera id with 6 characters,
    then when forming the list of camera ids, add zeros up to 6 characters.
    
    """
    cams_id = []
    cams_names = []
    scheds_over_glob = []
    schedulers = []
    with connection.cursor() as cursor:
        cursor.execute(
            'SELECT \
                id, \
                device_name, \
                schedule_override_global, \
                schedule \
            FROM Devices;'
        )

        for row in cursor:
            cams_id.append(str(row[0]).rjust(6, '0'))
            cams_names.append(str(row[1]))
            scheds_over_glob.append(str(row[2]))
            schedulers.append(str(row[3]))
        logger.info("Database connection has been established. Camera info received.")
    cams = zip(cams_id, cams_names, scheds_over_glob, schedulers)
    return cams


def get_hour_of_week(day_of_week_today):
    """BlueCherry uses a table that indicates at what time
    and in what mode the camera will record.
    The time in this table is the hour of the week.
    Countdown starts from Sunday.

    """
    hour_of_week_now = {
        'Sunday':hour_now,
        'Monday':24 + int(hour_now),
        'Tuesday':48 + int(hour_now),
        'Wednesday':72 + int(hour_now),
        'Thursday':96 + int(hour_now),
        'Friday':120 + int(hour_now),
        'Saturday':148 + int(hour_now)
    }[day_of_week_today]
    return hour_of_week_now


def recording_mode_continuous(connection, hour_of_week_now, cam_schedule_override_global, cam_sched):
    """Define the recording mode of the camera.
    If the mode !="Continuous", the camera recording on motion
    and does not need to be checked.

    """
    global_sсheduler = []
    with connection.cursor() as cursor:
        cursor.execute(
            'SELECT value \
            FROM GlobalSettings \
            WHERE parameter = "G_DEV_SCED";'
        )

        for row in cursor:
            global_sсheduler.append(str(row[0]))
    logger.info('Database connection has been established. \
                Global sheduler info received.')

    recording_mode = ''
    hour_of_week_now = get_hour_of_week(day_of_week_today)
    if cam_schedule_override_global == '0':
        recording_mode = str(global_sсheduler[0][hour_of_week_now])
    recording_mode = str(cam_sched[hour_of_week_now])
    logger.info('Recording mode was detecteed: '+recording_mode)
    if recording_mode == 'C':
        return True
    return False


def cam_rec_directory_check(cams_rec_path, cam_name):
    """BlueCherry creates a new directory for camera recordings every day at 00:00.
    If the directory is not created, then the camera has stopped recording.

    """
    if os.path.exists(cams_rec_path) is False:
        logger.error("Camera ("+cam_name+") does not record! \
                    ("+cams_rec_path+") directory is missing.")
        return False
    logger.info("Camera ("+cam_name+") The directory ("+cams_rec_path+") exists.")
    return True


def cam_rec_size_check(cams_rec_path, cam_name):
    """Checking the size of the directory with camera records at 2 second intervals.
    If the size does not change, then the camrea does not recording.

    """
    check_size_folder_cam = os.popen(f"du -sb {cams_rec_path}").read()
    time.sleep(2)
    check_size_folder_cam_new = os.popen(f"du -sb {cams_rec_path}").read()
    if check_size_folder_cam == check_size_folder_cam_new:
        logger.error("Camera ("+cam_name+") does not record! Directory size \
                    ("+cams_rec_path+") hasn't changed after 2 seconds.")
        return False
    logger.info("Camera ("+cam_name+") is recording. \
                The directory size increases ("+cams_rec_path+").")
    return True


def color_definition(analyzed_frame, cam_name):
    """Find the average value of the RGB color.
    If values < 10, then the camera records a black image.
    If values < 200, then the camera records a blown out image.

    """
    per_row = numpy.average(analyzed_frame, axis=0)
    color_rgb = numpy.average(per_row, axis=0)
    if color_rgb[0] < 10 and color_rgb[1] < 10 and color_rgb[2] < 10:
        logger.error("Camera ("+cam_name+") black image recording! "+str(color_rgb))
    elif color_rgb[0] > 200 and color_rgb[1] > 200 and color_rgb[2] > 200:
        logger.error("Camera ("+cam_name+") white image recording! "+str(color_rgb))
    return None


def sharpness_rating(frame, cam_name):
    """Definition of sharpness.

    """
    img = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    lap = cv2.Laplacian(img, cv2.CV_16S)
    mean, stddev = cv2.meanStdDev(lap)
    sharpness_tolerance = 15
    if stddev[0,0] < sharpness_tolerance:
        logger.error("Camera ("+cam_name+") \
                    blurry image recording! Sharoness: "+str(stddev[0,0]))
    logger.info("Camera ("+cam_name+") \
                normal image recording! Sharoness: "+str(stddev[0,0]))
    return None


if __name__ == '__main__':
    main()
