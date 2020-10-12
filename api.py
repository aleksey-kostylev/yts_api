#! /usr/bin/env python
# -*- coding: utf-8 -*-

# Загружаем модули
import email, smtplib, ssl # Модули для отправки email, модуль для smtp соединения и ssl модуль для шифрования
from email import encoders # Модуль для работы с кодировками (например ASCII) в рамках отправки email
from email.mime.base import MIMEBase # Модули для работы с email отправкой
from email.mime.multipart import MIMEMultipart # Модули для работы с email отправкой
from email.mime.text import MIMEText # Модули для работы с email отправкой
import getpass # Модуль для безопасного ввода пароля
import json # Модуль для JSON файлов (YouTube API по факту предоставляет нам JSON файл)
import numpy as np # Модуль для работы с данными
import os.path # Модуль для работы с файлами в рамках ОС
import pandas as pd # Модуль для работы с данными (создание таблиц/датафреймов)
import re # Модуль для работы с регулярными выражаниями (нужен для преоразования данных)
import requests # Модуль для url запросов (нужен для заспроса к API)
from tqdm import tqdm # Модуль для отображения прогресс бара при выполнении кода

# Оригинал кода был взят отсюда:
# https://github.com/python-engineer/youtube-analyzer
# Видео по написанию можно найти на YouTube канале Python Engineer, ссылка на плэйлист ниже:
# https://www.youtube.com/playlist?list=PLqnslRFeH2UpC8EqlF2aax9A-VLiPDwxP
# Хочу выразить огромную благодарность данному каналу. Именно благодаря ему написание всего моего скрипта стало возможным.

# Создаём класс для статистики по YouTube:
class YTstats:

    def __init__(self, api_key, channel_id):
        self.api_key = api_key
        self.channel_id = channel_id
        self.channel_statistics = None
        self.video_data = None

    def extract_all(self):
        self.get_channel_statistics()
        self.get_channel_video_data()

    def get_channel_statistics(self):
        """Выгрузка статистики по каналу"""
        print('get channel statistics...')
        url = f'https://www.googleapis.com/youtube/v3/channels?part=statistics&id={self.channel_id}&key={self.api_key}'
        pbar = tqdm(total=1)

        json_url = requests.get(url)
        data = json.loads(json_url.text)
        try:
            data = data['items'][0]['statistics']
        except KeyError:
            print('Could not get channel statistics')
            data = {}

        self.channel_statistics = data
        pbar.update()
        pbar.close()
        return data

    def get_channel_video_data(self):
        "Выгрузка информации по всем видео на канале"
        print('get video data...')
        channel_videos, channel_playlists = self._get_channel_content(limit=50)

        parts=["snippet","statistics","contentDetails"]
        for video_id in tqdm(channel_videos):
            for part in parts:
                data = self._get_single_video_data(video_id, part)
                channel_videos[video_id].update(data)

        self.video_data = channel_videos
        return channel_videos

    def _get_single_video_data(self, video_id, part):
        """
        Выгрузка следующей информации для каждого конкретного видео:
        'snippet', 'statistics', 'contentDetails'
        """
        url = f"https://www.googleapis.com/youtube/v3/videos?part={part}&id={video_id}&key={self.api_key}"
        json_url = requests.get(url)
        data = json.loads(json_url.text)
        try:
            data = data['items'][0][part]
        except KeyError as e:
            print(f'Error! Could not get {part} part of data: \n{data}')
            data = dict()
        return data

    def _get_channel_content(self, limit=None, check_all_pages=True):
        """
        Выгрузка всех видео и плейлистов, проверяя все доступные страницы:
        channel_videos = videoId: title, publishedAt
        channel_playlists = playlistId: title, publishedAt
        return channel_videos, channel_playlists
        """
        url = f"https://www.googleapis.com/youtube/v3/search?key={self.api_key}&channelId={self.channel_id}&part=snippet,id&order=date"
        if limit is not None and isinstance(limit, int):
            url += "&maxResults=" + str(limit)

        vid, pl, npt = self._get_channel_content_per_page(url)
        idx = 0
        while(check_all_pages and npt is not None and idx < 10):
            nexturl = url + "&pageToken=" + npt
            next_vid, next_pl, npt = self._get_channel_content_per_page(nexturl)
            vid.update(next_vid)
            pl.update(next_pl)
            idx += 1

        return vid, pl

    def _get_channel_content_per_page(self, url):
        """
        Выгрузка всех видео и плейлистов на странице:
        return channel_videos, channel_playlists, nextPageToken
        """
        json_url = requests.get(url)
        data = json.loads(json_url.text)
        channel_videos = dict()
        channel_playlists = dict()
        if 'items' not in data:
            print('Error! Could not get correct channel data!\n', data)
            return channel_videos, channel_videos, None

        nextPageToken = data.get("nextPageToken", None)

        item_data = data['items']
        for item in item_data:
            try:
                kind = item['id']['kind']
                published_at = item['snippet']['publishedAt']
                title = item['snippet']['title']
                if kind == 'youtube#video':
                    video_id = item['id']['videoId']
                    channel_videos[video_id] = {'publishedAt': published_at, 'title': title}
                elif kind == 'youtube#playlist':
                    playlist_id = item['id']['playlistId']
                    channel_playlists[playlist_id] = {'publishedAt': published_at, 'title': title}
            except KeyError as e:
                print('Error! Could not extract data from item:\n', item)

        return channel_videos, channel_playlists, nextPageToken

    def dump(self):
        """Окончательная выгрузка всех данных по статистике канала и видео в единый JSON файл"""
        if self.channel_statistics is None or self.video_data is None:
            print('data is missing!\nCall get_channel_statistics() and get_channel_video_data() first!')
            return

        fused_data = {self.channel_id: {"channel_statistics": self.channel_statistics,
                              "video_data": self.video_data}}

        filename = 'YT_data.json'
        with open(filename, 'w') as f:
            json.dump(fused_data, f, indent=4)

        print('Данные выгружены в файл', filename)

# Модуль паролей (если файлов с паролями нет, то алгоритм его создаст и сохранит)
# При повторном запуске пароли вводить не требуется
# Если надо ввести новый токен, канал и транзитную почту, то можно просто удалить txt файлы и запустить файл снова.

# API_KEY (токен для YouTube студии):
if os.path.isfile('API_KEY.txt') == False: # Проверяем наличие файла в директории
    API_KEY = getpass.getpass(prompt='Введите YouTube API_KEY: ', stream=None) # Вводим API_KEY
    sourceFile = open('API_KEY.txt', 'w') # Создаём и открываем txt файл в режиме записи
    print(API_KEY, file = sourceFile) # Выводим данные API_KEY в txt
    sourceFile.close() # Сохраняем данные закрывая файл
    API_KEY = open('API_KEY.txt', 'r') # Присваиваем переменной API_KEY данные из txt файла
    API_KEY = API_KEY.read().strip("\n") # Делаем переприсваивание, чтобы избавится от перевода строки \n

else: # Если файл в директории есть, то будет произведено сразу считывание файла
    API_KEY = open('API_KEY.txt', 'r')
    API_KEY = API_KEY.read().strip("\n")

# channel_id (можно найти в url ссылке канала):
if os.path.isfile('channel_id.txt') == False: # Проверяем наличие файла в директории
    channel_id = getpass.getpass(prompt='Введите ID YouTube канала: ', stream=None) # Вводим channel_id
    sourceFile = open('channel_id.txt', 'w') # Создаём и открываем txt файл в режиме записи
    print(channel_id, file = sourceFile) # Выводим данные channel_id в txt
    sourceFile.close() # Сохраняем данные закрывая файл
    channel_id = open('channel_id.txt', 'r') # Присваиваем переменной channel_id данные из txt файла
    channel_id = channel_id.read().strip("\n") # Делаем переприсваивание, чтобы избавится от перевода строки \n

else: # Если файл в директории есть, то будет произведено сразу считывание файла
    channel_id = open('channel_id.txt', 'r')
    channel_id = channel_id.read().strip("\n")

# login (логин для gmail почты):
if os.path.isfile('email_login.txt') == False: # Проверяем наличие файла в директории
    login = getpass.getpass('Введите потчу gmail: ', stream=None) # Вводим email_login
    sourceFile = open('email_login.txt', 'w') # Создаём и открываем txt файл в режиме записи
    print(login, file = sourceFile) # Выводим данные email_login в txt
    sourceFile.close() # Сохраняем данные закрывая файл
    login = open('email_login.txt', 'r') # Присваиваем переменной email_login данные из txt файла
    login = login.read().strip("\n") # Делаем переприсваивание, чтобы избавится от перевода строки \n

else: # Если файл в директории есть, то будет произведено сразу считывание файла
    login = open('email_login.txt', 'r')
    login = login.read().strip("\n")

# password (пароль для gmail почты):
if os.path.isfile('email_password.txt') == False: # Проверяем наличие файла в директории
    password = getpass.getpass('Введите пароль для gmail почты: ', stream=None) # Вводим email_password
    sourceFile = open('email_password.txt', 'w') # Создаём и открываем txt файл в режиме записи
    print(password, file = sourceFile) # Выводим данные email_password в txt
    sourceFile.close() # Сохраняем данные закрывая файл
    password = open('email_password.txt', 'r') # Присваиваем переменной email_password данные из txt файла
    password = password.read().strip("\n") # Делаем переприсваивание, чтобы избавится от перевода строки \n

else: # Если файл в директории есть, то будет произведено сразу считывание файла
    password = open('email_password.txt', 'r')
    password = password.read().strip("\n")

# Процедура запуска класса функций для импорта статистики
yt = YTstats(API_KEY, channel_id)
yt.extract_all()
yt.dump() # Создаём JSON файл для последующей работы с ним при помощи pandas

# Открываем наш JSON файл
with open('YT_data.json', 'r') as infile:
    data = json.load(infile)

# В этом разделе начинаем парсить JSON файл и собирать из него свой датафрейм,
# после чего сохраняем его как Excel файл.

# Находим список всех параметров видео на YouTube:
video_codes = data[channel_id]['video_data'].keys() # Коды видео

# Создаём пустые списки для дальнейшей конкатенации
v_codes = [] # Пустой список для кодов (будем брать из списка video_codes)
v_title = [] # Пустой список для заголовков
v_publishedAt = [] # Пустой список для даты публикации видео
v_duration = [] # Пустой список для длительности видео
v_viewCount = [] # Пустой список для количества просмотров
v_likeCount = [] # Пустой список для количества лайков
v_dislikeCount = [] # Пустой список для количества дизлайков
v_favoriteCount = [] # Пустой список для добавлений в избранное
v_commentCount = [] # Пустой список для подсчета количества комментариев

# Начинаем выгружать все значение, но лишь по заданым нами параметрам:
for i in video_codes:
    v_codes.append(i)
    v_title.append(data[channel_id]['video_data'].get(i)['title']) # Заголовок
    v_publishedAt.append(data[channel_id]['video_data'].get(i)['publishedAt']) # Дата публикации
    v_duration.append(data[channel_id]['video_data'].get(i)['duration']) # Длительность видео
    v_viewCount.append(data[channel_id]['video_data'].get(i)['viewCount']) # Количество просмотров
    v_likeCount.append(data[channel_id]['video_data'].get(i)['likeCount']) # Количество лайков
    v_dislikeCount.append(data[channel_id]['video_data'].get(i)['dislikeCount']) # Количество дизлайков
    v_favoriteCount.append(data[channel_id]['video_data'].get(i)['favoriteCount']) # Количество добавлений в избранное
    v_commentCount.append(data[channel_id]['video_data'].get(i)['commentCount']) # Количество комментариев

# Создаём датафрейм и добавляем столбцы:
df = pd.DataFrame(v_codes)
df['Заголовок'] = v_title
df['Дата'] = v_publishedAt
df['Длительность'] = v_duration
df['Просмотры'] = v_viewCount
df['Лайки'] = v_likeCount
df['Дизлайки'] = v_dislikeCount
df['Избранное'] = v_favoriteCount
df['Комментарии'] = v_commentCount

# Создаём новый столбец с сылками (используя код видео - это самый первый список video_codes):
df['Ссылка'] = 'https://www.youtube.com/watch?v=' + df[0]

# Делаем замену столбца с датами в нужном для нас формате YYYY-MM-DD:
re_express = re.compile('([\d]{4}).([\d]{2}).([\d]{2}).*') # В рамках модуля регулярных выражений выделяем 3 группы - всё что в круглых скобках внутри функции re.compile()
df['Дата'] = df['Дата'].str.replace(re_express, r'\1-\2-\3') # Собираем из этих 3 групп свой формат

# В рамказ YouTube Studio API формат длительности представлен следующим образом: PT...H...M...S (при уже опубликованном видео)
# где PT - это Pasific Time, H - часы, M - минуты, S - секунды, а "..." - это целые числа.
# В этом скрипте мы заменяем стандартный формат длительности на длительность в часах с округлением до 4 знаков после точки/запятой

# Делаем замену столбца с длительностью видео:
# Создаём пустой список для дальнейшей конкатенации
time_list = []

# Закускаем цикл
for i in df['Длительность']:

    # В рамках доступного фората длительности существует всего 7 вариантов (паттернов)
    # Эти варианты мы описываем при помощи модуля регулярных выражений (import re):
    match_hms = re.fullmatch(r'PT([\d]+)H([\d]+)M([\d]+)S', i) # Патерн - Часы, минуты, секунды
    match_hm = re.fullmatch(r'PT([\d]+)H([\d]+)M', i) # Патерн - Часы и минуты
    match_hs = re.fullmatch(r'PT([\d]+)H([\d]+)S', i) # Патерн - Часы и секунды
    match_ms = re.fullmatch(r'PT([\d]+)M([\d]+)S', i) # Патерн - Минуты и секунды
    match_h = re.fullmatch(r'PT([\d]+)H', i) # Патерн - Часы
    match_m = re.fullmatch(r'PT([\d]+)M', i) # Патерн - Минуты
    match_s = re.fullmatch(r'PT([\d]+)S', i) # Патерн - Секунды

    # В рамках цикла начинаем тестировать каждое значение из столбца df['Длительность'] на варианты:
    if match_hms:

        h = match_hms.group(1) # Извлекаем часы
        m = match_hms.group(2) # Извлекаем минуты
        s = match_hms.group(3) # Извлекаем секунды
        time_hms = round((int(h)*60*60 + int(m)*60 + int(s))/3600, 4) # Переводим в часы
        time_list.append(time_hms)

    elif match_hm:
        h = match_hm.group(1) # Извлекаем часы
        m = match_hm.group(2) # Извлекаем минуты
        time_hm = round((int(h)*60*60 + int(m)*60)/3600, 4) # Переводим в часы
        time_list.append(time_hm)

    elif match_hs:
        h = match_hs.group(1) # Извлекаем часы
        s = match_hs.group(2) # Извлекаем секунды
        time_hs = round((int(h)*60*60 + int(s))/3600, 4) # Переводим в часы
        time_list.append(time_hs)

    elif match_ms:
        m = match_ms.group(1) # Извлекаем минуты
        s = match_ms.group(2) # Извлекаем секунды
        time_ms = round((int(m)*60 + int(s))/3600, 4) # Переводим в часы
        time_list.append(time_ms)

    elif match_h:
        h = match_h.group(1) # Извлекаем часы
        time_h = round(int(h), 4) # Переводим в часы
        time_list.append(time_h)

    elif match_m:
        m = match_m.group(1) # Извлекаем минуты
        time_m = round(int(m)/60, 4) # Переводим в часы
        time_list.append(time_m)

    elif match_s:
        s = match_s.group(1) # Извлекаем секунды
        time_s = round(int(m)/3600, 4) # Переводим в часы
        time_list.append(time_s)

    else:
        time_list.append(i) # Все остальное (то что не удовлетворяет нашим паттернам мы записываем как есть)

# Проводим итоговую замену нашего прежнего столбца на новый:
df['Длительность'] = time_list

# Загружаем файл для работы в Excel или Google таблицах:
df.to_excel("YT_data.xlsx")

# Скрипт был в основном спроектирован для мобильного (android) Linux терминала под названием Termux, ссылка на скачивание ниже:
# https://play.google.com/store/apps/details?id=com.termux
# В рамках стандартной сборки Termux - это терминал без root прав, поэтому в этом скрипте excel-файл мы сразу отправляем по gmail на любую выбранную нами почту
# Для этого надо сперва создать отдельную gmail почту, а затем в настройках этой почты разрешить достпу к сторонни приложениям тут:
# https://www.google.com/settings/security/lesssecureapps
# ВНИМАНИЕ! БЕЗ ЭТОГО ДОСТУПА ОТПРАВКА ПОЧТЫ НЕ БУДЕТ РАБОТАТЬ!

# Начинаем отправку почты с ввода почты получателя
# Информацию о модуле отправки email писем взята отсюда:
# https://realpython.com/python-send-email/
# https://defpython.ru/otpravka_poczty_s_pomosczu_smtplib

# Чтобы письмо по ошибке не ушло не на тот ящик, создадим модуль для проверки
# По умолчанию присваиваем переменной answer состояние 'n'
answer = 'n'

# Пока у нашей переменной answer состояние отличное от состояния 'y' мы всегда будем запрашивать актуальную почту для отправки,
# а также выводить ту самую почту которую написали и запрашивать подтверждение [y/n]

# Если введенная нами почта верна, тогда состояние answer изменится на 'y' и окончательное присвоение будет завершено.
while answer != 'y':
    receiver_email = input('Введите email получателя: ')
    print(f'Вы действительно хотите отправить документ на почту {receiver_email}?')
    answer = input('[y/n]: ')
    if answer == 'y':
        receiver_email = receiver_email # Окончательно присвоение

# Задаём тему письма:
subject = u'redirector'
# Пишем текст письма:
body = u'Данные готовы для анализа'

# Создаём email сообщение:
message = MIMEMultipart()
message["From"] = login
message["To"] = receiver_email
message["Subject"] = subject

# Прикрепляем текст email сообщения
message.attach(MIMEText(body, "plain"))

# Задаём наш выгруженный xlsx файл для дальнейшей отправки
filename = "YT_data.xlsx"

# Open PDF file in binary mode
with open(filename, "rb") as attachment:
    # Add file as application/octet-stream
    # Email client can usually download this automatically as attachment
    part = MIMEBase("application", "octet-stream")
    part.set_payload(attachment.read())

# Кодируем в ASCII для отправки по email:
encoders.encode_base64(part)

# Добавляем header как пару ключ/значение в качестве части вложения:
part.add_header(
    "Content-Disposition",
    f"attachment; filename= {filename}",
)

# Добавляем вложене к email сообщению и конвертируем в строку
message.attach(part)
text = message.as_string()

# Производим подключение к gmail почте используя SMTP соединение:
context = ssl.create_default_context()
with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
    server.login(login, password) # Подключаемся к почте
    server.sendmail(login, receiver_email, text) # Отправляем почту
    server.quit() # Выходим после того как всё отправили

# Проводим чистку памяти, удаляй созданные файлы в ходе работы (txt файлы с паролями остаются)
os.remove('YT_data.xlsx')
os.remove('YT_data.json')
print('Отправка данных завершена!')
