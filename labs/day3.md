rafael@vm-hermes:~/devops-sprint/tools$ python3 header_echo.py 8091 & curl -sk https://localhost:8443/echo/ping
[1] 413590
{
  "path": "/ping",
  "client": "127.0.0.1",
  "headers": {
    "Host": "localhost",
    "X-Real-IP": "127.0.0.1",
    "X-Forwarded-For": "127.0.0.1",
    "X-Forwarded-Proto": "https",
    "Connection": "close",
    "User-Agent": "curl/7.74.0",
    "Accept": "*/*"

rafael@vm-hermes:~/devops-sprint/tools$ ss -lntp | grep 8443
LISTEN 0      511          0.0.0.0:8443       0.0.0.0:*                           
