import sys
import os
import webbrowser
import threading
import time
import logging

# 添加backend目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
from app import create_app
from config import Config

def open_browser():
    """延迟打开浏览器"""
    time.sleep(2)  # 等待服务器启动
    webbrowser.open('http://localhost:5002')

app = create_app()

if __name__ == '__main__':
    print("正在启动密码重置应用...")
    print("服务器将在 http://0.0.0.0:5002 启动")
    print("请在浏览器中访问上述地址来使用密码重置功能")
    print("按 Ctrl+C 停止服务器")
    
    # 在新线程中打开浏览器（仅开发环境）
    if Config.FLASK_ENV == 'development':
        browser_thread = threading.Thread(target=open_browser)
        browser_thread.daemon = True
        browser_thread.start()
    
    try:
        # 使用 Waitress 生产级 WSGI 服务器（跨平台）
        from waitress import serve
        
        print("\n使用 Waitress WSGI 服务器")
        print("=" * 50)
        
        serve(
            app,
            host='0.0.0.0',
            port=5002,
            threads=6,              # 并发线程数
            channel_timeout=120,    # 请求超时（秒）
            backlog=2048,          # 连接队列大小
            connection_limit=1000, # 最大并发连接数
            cleanup_interval=30,   # 清理间隔（秒）
            # url_scheme='https'   # 如果在反向代理后面使用 HTTPS，取消注释
        )
    except ImportError:
        # 如果 Waitress 未安装，回退到 Flask 开发服务器（仅用于测试）
        logging.warning("Waitress 未安装，使用 Flask 开发服务器（不推荐生产环境）")
        logging.warning("请运行: pip install waitress")
        app.run(host='0.0.0.0', port=5002, debug=False, use_reloader=False)
    except KeyboardInterrupt:
        print("\n服务器已停止")