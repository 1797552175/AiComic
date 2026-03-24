#!/usr/bin/env python3
"""
Bot 启动包装脚本 - 设置 SO_REUSEADDR + 崩溃自重启
由 watchdog 调用，不直接修改 bot 源码

用法: python3 bot_wrapper.py <bot_name> <port>
"""
import socket
import subprocess
import sys
import time
import os
import signal

BOT_NAME = sys.argv[1] if len(sys.argv) > 1 else "unknown"
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 8001
LOG_DIR = "/opt/AiComic/状态报告"
MAX_RESTARTS = 10
RESTART_COOLDOWN = 10  # 秒


class ReuseAddrHTTPServer:
    """在绑定前设置 SO_REUSEADDR 的 HTTP 服务器"""
    def __init__(self, server_address, RequestHandlerClass):
        self.server_address = server_address
        self.RequestHandlerClass = RequestHandlerClass
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(server_address)
        self.socket.listen(5)

    def serve_forever(self, handler):
        while True:
            self.socket.settimeout(None)
            conn, addr = self.socket.accept()
            # 每个连接一个线程处理
            import threading
            t = threading.Thread(target=self._handle, args=(conn, handler))
            t.daemon = True
            t.start()

    def _handle(self, conn, handler):
        import http.server
        h = handler(conn, None, None)
        try:
            h.handle()
        finally:
            conn.close()


def wait_for_port(port, timeout=30):
    """等待端口可访问"""
    for _ in range(timeout):
        try:
            s = socket.socket()
            s.settimeout(1)
            s.connect(("127.0.0.1", port))
            s.close()
            return True
        except:
            time.sleep(1)
    return False


def main():
    import importlib.util
    script_path = "/opt/AiComic/scripts/bot_http_server_v2.py"

    # 先等待端口释放（防止旧进程还没退出）
    print(f"[{BOT_NAME}] wrapper: 等待端口 {PORT} 释放...")
    for attempt in range(10):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)
            s.connect(("127.0.0.1", PORT))
            s.close()
            # 端口还被占用，等着
            time.sleep(2)
        except:
            # 端口空闲
            break

    print(f"[{BOT_NAME}] wrapper: 启动 bot (port={PORT})...")

    # 加载 bot 模块
    spec = importlib.util.spec_from_file_location("bot_module", script_path)
    bot_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bot_module)

    # 设置环境变量让 bot 知道自己的类型和端口
    os.environ["BOT_TYPE"] = BOT_NAME
    os.environ["BOT_PORT"] = str(PORT)

    restarts = 0
    while restarts < MAX_RESTARTS:
        try:
            # 直接调用 bot 的 run()，但先 hack 掉 HTTPServer
            import http.server
            from http.server import HTTPServer

            orig_init = HTTPServer.__init__
            def patched_init(self, address, handler):
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.socket.bind(address)
                self.socket.listen(5)
            HTTPServer.__init__ = patched_init

            bot_module.run()
        except Exception as e:
            print(f"[{BOT_NAME}] wrapper: bot 退出 ({e})，", end="")
            restarts += 1
            if restarts < MAX_RESTARTS:
                print(f"{RESTART_COOLDOWN}秒后第 {restarts}/{MAX_RESTARTS} 次重启...")
                time.sleep(RESTART_COOLDOWN)
            else:
                print(f"已达最大重启次数 ({MAX_RESTARTS})，退出")
                break

    sys.exit(1)


if __name__ == "__main__":
    main()
