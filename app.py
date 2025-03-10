# import os
# from typing import List, Dict, Any
# import requests
# from flask import Flask, render_template, request, send_file, abort
# from dotenv import load_dotenv
# import logging
# import urllib.parse
#
# load_dotenv()
#
# app = Flask(__name__)
# app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your_secret_key') # Важно для безопасности сессий, если используете сессии
#
# # Настройка логирования
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
#
# YANDEX_DISK_API_URL = "https://cloud-api.yandex.net/v1/disk/public/resources"
# DOWNLOAD_FOLDER = os.path.join('static', 'downloads')
# os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)
# app.config['DOWNLOAD_FOLDER'] = DOWNLOAD_FOLDER
#
#
# def get_yandex_disk_files(public_key: str) -> List[Dict[str, Any]]:
#     """
#     Получает список файлов и папок с Яндекс.Диска по публичной ссылке.
#
#     Args:
#         public_key: Публичная ссылка на папку на Яндекс.Диске.
#
#     Returns:
#         Список словарей, представляющих файлы и папки.  Возвращает пустой список в случае ошибки.
#     """
#     try:
#         encoded_public_key = urllib.parse.quote_plus(public_key)
#         url = f"{YANDEX_DISK_API_URL}?public_key={encoded_public_key}"
#         response = requests.get(url)
#         response.raise_for_status()  # Raises HTTPError for bad responses (4xx or 5xx)
#         data = response.json()
#
#         if "_embedded" in data and "items" in data["_embedded"]:
#             return data["_embedded"]["items"]
#         else:
#             logging.warning(f"No items found in response for public_key: {public_key}")
#             return []
#     except requests.exceptions.RequestException as e:
#         logging.error(f"Error fetching files from Yandex.Disk: {e}")
#         return []
#     except Exception as e:
#         logging.exception(f"An unexpected error occurred: {e}")
#         return []
#
# def download_file_from_yandex_disk(download_url: str, filename: str) -> str:
#     """
#     Скачивает файл с Яндекс.Диска по URL и сохраняет его локально.
#
#     Args:
#         download_url: URL для скачивания файла.
#         filename: Имя файла для сохранения.
#
#     Returns:
#         Путь к скачанному файлу. Возвращает None в случае ошибки.
#     """
#     try:
#         response = requests.get(download_url, stream=True)
#         response.raise_for_status()
#
#         filepath = os.path.join(app.config['DOWNLOAD_FOLDER'], filename)
#         with open(filepath, 'wb') as f:
#             for chunk in response.iter_content(chunk_size=8192):
#                 f.write(chunk)
#
#         return filepath
#     except requests.exceptions.RequestException as e:
#         logging.error(f"Error downloading file: {e}")
#         return None
#     except Exception as e:
#         logging.exception(f"An unexpected error occurred: {e}")
#         return None
#
#
# @app.route('/', methods=['GET', 'POST'])
# def index():
#     """
#     Главная страница приложения.
#     """
#     files = []
#     error_message = None
#
#     if request.method == 'POST':
#         public_key = request.form.get('public_key')
#         if not public_key:
#             error_message = "Пожалуйста, введите публичную ссылку."
#         else:
#             files = get_yandex_disk_files(public_key)
#             if not files:
#                 error_message = "Не удалось получить список файлов. Проверьте ссылку."
#
#     return render_template('index.html', files=files, error_message=error_message)
#
#
# @app.route('/download', methods=['POST'])
# def download():
#     """
#     Обрабатывает запрос на скачивание файла.
#     """
#     download_url = request.form.get('download_url')
#     filename = request.form.get('filename')
#
#     if not download_url or not filename:
#         abort(400, "Не указан URL для скачивания или имя файла.")
#
#     filepath = download_file_from_yandex_disk(download_url, filename)
#
#     if filepath:
#         try:
#             return send_file(filepath, as_attachment=True, download_name=filename)
#         except Exception as e:
#             logging.error(f"Error sending file: {e}")
#             abort(500, "Ошибка при отправке файла.")
#         finally:
#             # Clean up the downloaded file
#             try:
#                 os.remove(filepath)
#             except OSError as e:
#                 logging.warning(f"Could not delete file {filepath}: {e}")
#
#     else:
#         abort(500, "Не удалось скачать файл с Яндекс.Диска.")
#
#
# @app.errorhandler(400)
# def bad_request(error):
#     return render_template('error.html', error_message=error.description), 400
#
# @app.errorhandler(500)
# def internal_server_error(error):
#     return render_template('error.html', error_message=error.description), 500
#
# if __name__ == '__main__':
#     app.run(debug=True)


import os
import io
import zipfile
from typing import List, Dict, Any
import requests
from flask import Flask, render_template, request, send_file, abort
from dotenv import load_dotenv
import logging
import urllib.parse

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your_secret_key') # Важно для безопасности сессий, если используете сессии

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

YANDEX_DISK_API_URL = "https://cloud-api.yandex.net/v1/disk/public/resources"
DOWNLOAD_FOLDER = os.path.join('static', 'downloads')
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)
app.config['DOWNLOAD_FOLDER'] = DOWNLOAD_FOLDER

# Кэш для списка файлов
file_cache: Dict[str, List[Dict[str, Any]]] = {}


def get_yandex_disk_files(public_key: str) -> List[Dict[str, Any]]:
    """
    Получает список файлов и папок с Яндекс.Диска по публичной ссылке.

    Args:
        public_key: Публичная ссылка на папку на Яндекс.Диске.

    Returns:
        Список словарей, представляющих файлы и папки.  Возвращает пустой список в случае ошибки.
    """
    try:
        encoded_public_key = urllib.parse.quote_plus(public_key)
        url = f"{YANDEX_DISK_API_URL}?public_key={encoded_public_key}"
        response = requests.get(url)
        response.raise_for_status()  # Raises HTTPError for bad responses (4xx or 5xx)
        data = response.json()

        if "_embedded" in data and "items" in data["_embedded"]:
            return data["_embedded"]["items"]
        else:
            logging.warning(f"No items found in response for public_key: {public_key}")
            return []
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching files from Yandex.Disk: {e}")
        return []
    except Exception as e:
        logging.exception(f"An unexpected error occurred: {e}")
        return []

def download_file_from_yandex_disk(download_url: str, filename: str) -> bytes:
    """
    Скачивает файл с Яндекс.Диска по URL и возвращает его содержимое в виде bytes.

    Args:
        download_url: URL для скачивания файла.
        filename: Имя файла.

    Returns:
        Содержимое файла в виде bytes. Возвращает None в случае ошибки.
    """
    try:
        response = requests.get(download_url, stream=True)
        response.raise_for_status()
        return response.content
    except requests.exceptions.RequestException as e:
        logging.error(f"Error downloading file {filename}: {e}")
        return None
    except Exception as e:
        logging.exception(f"An unexpected error occurred: {e}")
        return None


@app.route('/', methods=['GET', 'POST'])
def index():
    """
    Главная страница приложения.
    """
    files = []
    error_message = None

    if request.method == 'POST':
        public_key = request.form.get('public_key')
        filter_type = request.form.get('filter_type')

        if not public_key:
            error_message = "Пожалуйста, введите публичную ссылку."
        else:
            # Кэширование: проверяем, есть ли список файлов в кэше
            if public_key in file_cache:
                all_files = file_cache[public_key]
                logging.info(f"Список файлов для '{public_key}' получен из кэша.")
            else:
                all_files = get_yandex_disk_files(public_key)
                if all_files:
                    file_cache[public_key] = all_files  # Кэшируем список
                    logging.info(f"Список файлов для '{public_key}' загружен с Яндекс.Диска и закэширован.")
                else:
                    error_message = "Не удалось получить список файлов. Проверьте ссылку."
                    return render_template('index.html', files=files, error_message=error_message)

            # Фильтрация файлов
            if filter_type:
                files = [f for f in all_files if f['type'] == filter_type]
            else:
                files = all_files

    return render_template('index.html', files=files, error_message=error_message)


@app.route('/download', methods=['POST'])
def download():
    """
    Обрабатывает запрос на скачивание нескольких файлов.
    """
    selected_files = request.form.getlist('selected_files')  # Получаем список выбранных файлов

    if not selected_files:
        abort(400, "Не выбрано ни одного файла для скачивания.")

    # Создаем zip-архив в памяти
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_data in selected_files:
            try:
                filename, download_url = file_data.split("||")  # Разделяем filename и download_url
                file_content = download_file_from_yandex_disk(download_url, filename)
                if file_content:
                    zipf.writestr(filename, file_content)  # Добавляем файл в zip
                else:
                    logging.error(f"Не удалось скачать файл {filename} и добавить в архив.")
            except Exception as e:
                logging.exception(f"Ошибка при обработке файла для скачивания: {e}")
                abort(500, f"Ошибка при скачивании одного из файлов: {e}")

    memory_file.seek(0)  # Перематываем указатель в начало файла

    # Отдаем zip-архив пользователю
    try:
        return send_file(memory_file, as_attachment=True, download_name="archive.zip", mimetype="application/zip")
    except Exception as e:
        logging.error(f"Ошибка при отправке zip-архива: {e}")
        abort(500, "Ошибка при отправке архива.")



@app.errorhandler(400)
def bad_request(error):
    return render_template('error.html', error_message=error.description), 400

@app.errorhandler(500)
def internal_server_error(error):
    return render_template('error.html', error_message=error.description), 500

if __name__ == '__main__':
    app.run(debug=True)