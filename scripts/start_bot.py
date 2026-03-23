#!/usr/bin/env python3
import sys, os
sys.path.insert(0, '/opt/AiComic/scripts')
os.chdir('/opt/AiComic/scripts')
exec(open('bot_http_server_v2.py').read())
