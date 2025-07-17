import sys
import os
import webbrowser
import threading
import time

# 添加backend目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
from app import create_app
from config import Config

def open_browser():
    """延迟打开浏览器"""
    time.sleep(2)  # 等待服务器启动
    webbrowser.open('http://localhost:5000')

app = create_app()

if __name__ == '__main__':
    print("正在启动密码重置应用...")
    print("服务器将在 http://localhost:5000 启动")
    print("请在浏览器中访问上述地址来使用密码重置功能")
    print("按 Ctrl+C 停止服务器")
    
    # 在新线程中打开浏览器
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()
    
    try:
        # 生产环境设置，不使用调试模式和重载器
        app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
    except KeyboardInterrupt:
        print("\n服务器已停止")