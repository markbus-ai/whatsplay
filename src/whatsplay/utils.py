import platform
import subprocess
import tempfile
import os
import http.server
import socketserver
import threading
import base64


def show_qr_window(qr_image_bytes):
    """
    Muestra un QR en una página web simple.
    """
    qr_base64 = base64.b64encode(qr_image_bytes).decode('utf-8')
    html_content = f"""
    <html>
        <head>
            <title>WhatsApp QR Code</title>
            <style>
                body {{
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background-color: #f0f0f0;
                }}
                img {{
                    max-width: 100%;
                    max-height: 100%;
                }}
            </style>
        </head>
        <body>
            <img src="data:image/png;base64,{qr_base64}" alt="QR Code">
        </body>
    </html>
    """

    class Handler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/':
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(html_content.encode('utf-8'))
            else:
                super().do_GET()

    PORT = 8000
    httpd = None

    def start_server():
        nonlocal httpd
        with socketserver.TCPServer(("", PORT), Handler) as httpd_server:
            httpd = httpd_server
            print(f"Servidor iniciado en http://localhost:{PORT}")
            httpd.serve_forever()

    server_thread = threading.Thread(target=start_server)
    server_thread.daemon = True
    server_thread.start()


def close_qr_window():
    global httpd
    if httpd:
        httpd.shutdown()
