import os
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

def download_file_from_yandex_disk(download_url: str, filename: str) -> str:
    """
    Скачивает файл с Яндекс.Диска по URL и сохраняет его локально.

    Args:
        download_url: URL для скачивания файла.
        filename: Имя файла для сохранения.

    Returns:
        Путь к скачанному файлу. Возвращает None в случае ошибки.
    """
    try:
        response = requests.get(download_url, stream=True)
        response.raise_for_status()

        filepath = os.path.join(app.config['DOWNLOAD_FOLDER'], filename)
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        return filepath
    except requests.exceptions.RequestException as e:
        logging.error(f"Error downloading file: {e}")
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
        if not public_key:
            error_message = "Пожалуйста, введите публичную ссылку."
        else:
            files = get_yandex_disk_files(public_key)
            if not files:
                error_message = "Не удалось получить список файлов. Проверьте ссылку."

    return render_template('index.html', files=files, error_message=error_message)


@app.route('/download', methods=['POST'])
def download():
    """
    Обрабатывает запрос на скачивание файла.
    """
    download_url = request.form.get('download_url')
    filename = request.form.get('filename')

    if not download_url or not filename:
        abort(400, "Не указан URL для скачивания или имя файла.")

    filepath = download_file_from_yandex_disk(download_url, filename)

    if filepath:
        try:
            return send_file(filepath, as_attachment=True, download_name=filename)
        except Exception as e:
            logging.error(f"Error sending file: {e}")
            abort(500, "Ошибка при отправке файла.")
        finally:
            # Clean up the downloaded file
            try:
                os.remove(filepath)
            except OSError as e:
                logging.warning(f"Could not delete file {filepath}: {e}")

    else:
        abort(500, "Не удалось скачать файл с Яндекс.Диска.")


@app.errorhandler(400)
def bad_request(error):
    return render_template('error.html', error_message=error.description), 400

@app.errorhandler(500)
def internal_server_error(error):
    return render_template('error.html', error_message=error.description), 500

if __name__ == '__main__':
    app.run(debug=True)