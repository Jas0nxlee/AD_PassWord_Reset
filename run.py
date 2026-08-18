import os
import sys
import threading
import time
import webbrowser

from waitress import serve

sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from app import create_app
from config import Config


def open_browser():
    time.sleep(1)
    webbrowser.open(f'http://{Config.SERVER_HOST}:{Config.SERVER_PORT}')


app = create_app()


if __name__ == '__main__':
    print(f'密码重置服务正在 http://{Config.SERVER_HOST}:{Config.SERVER_PORT} 启动')
    if Config.OPEN_BROWSER and Config.SERVER_HOST in {'127.0.0.1', 'localhost', '::1'}:
        browser_thread = threading.Thread(target=open_browser, daemon=True)
        browser_thread.start()
    serve(
        app,
        host=Config.SERVER_HOST,
        port=Config.SERVER_PORT,
        threads=6,
        channel_timeout=30,
        backlog=128,
        connection_limit=100,
        cleanup_interval=30,
    )
