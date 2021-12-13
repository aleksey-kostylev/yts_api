# YouTube Studio API Module

YouTube Studio API Module - это скрипт для формирования удобного excel отчета о всех видео на вашем YouTube канале.

После отработки скрипт предложит ввести email для получения отчета на почту. 

Каждая строка в отчете - это видео, которое размещено на канале. 

В качестве столбцов отчета выступают:

- 0 (код видео на канале, по которому можно найти видео добавив его к ссылке 'https://www.youtube.com/watch?v=')
- Заголовок видео
- Дата
- Длительность (уже пересчитанная в часы, по желанию можно изменить расчет, чтобы результат был в минутах) - 276 строка
- Просмотры
- Лайки
- Дизлайки
- Избранное
- Комментарии
- Ссылка (полноценная ссылка для перехода)

**Для запуска скрипта понадобится:**
- Установить Python 3 или выше
- Установить все необходимые для работы библиотеки
- Создать транзитный email на gmail для пересылки отчетов (при запуске скрипт попросит ввести логин и пароль, которые затем будут сохранены в корневой папке в .txt)
- Получить token для YouTube Studio API (скрипт также попросит ввести token, который будет записан в .txt файл)

## Проверить версию Python:
```
python --version
```

## Проверить наличие установленных библиотек:

```
pip install numpy
pip install pandas
pip install getpass
pip install requests
pip install tqdm
```

## Материалы

Оригинал кода был взят из https://github.com/python-engineer/youtube-analyzer

Узнать больше подключении к YouTube API можно на канале Python Engineer (https://www.youtube.com/playlist?list=PLqnslRFeH2UpC8EqlF2aax9A-VLiPDwxP)

Чтобы скрипт работал с GMAIL необходимо в настройках этой почты разрешить достпу к сторонни приложениям (https://www.google.com/settings/security/lesssecureapps). Скрипт будет выдавать ошибку как раз по причине того, что GMAIL иногда сам отключает эту опцию. 

Узнать больше о модулях для работы с email можно по ссылкам:
- https://realpython.com/python-send-email/
- https://defpython.ru/otpravka_poczty_s_pomosczu_smtplib

## Termux

Скрипт также можно запускать на мобильном (android) Linux терминале под названием Termux (https://play.google.com/store/apps/details?id=com.termux)
