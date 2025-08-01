import http.server
import socketserver
import threading
import base64
import time

# Global variable to hold the QR code and the HTTP server instance
current_qr_base64 = None
httpd = None
last_request_time = time.time()

def update_qr_code(qr_image_bytes):
    """Updates the global QR code variable."""
    global current_qr_base64
    current_qr_base64 = base64.b64encode(qr_image_bytes).decode('utf-8')

def show_qr_window(qr_image_bytes):
    """
    Muestra un QR en una página web simple con actualización en tiempo real.
    """
    update_qr_code(qr_image_bytes)

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
            <script>
                function refreshQR() {{
                    fetch('/qr')
                        .then(response => response.text())
                        .then(data => {{
                            document.getElementById('qr-img').src = "data:image/png;base64," + data;
                        }});
                }}
                setInterval(refreshQR, 1000);
            </script>
        </head>
        <body>
            <img id="qr-img" src="data:image/png;base64,{current_qr_base64}" alt="QR Code">
        </body>
    </html>
    """

    class Handler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            global last_request_time
            last_request_time = time.time()
            if self.path == '/':
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(html_content.encode('utf-8'))
            elif self.path == '/qr':
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(current_qr_base64.encode('utf-8'))
            else:
                super().do_GET()

    PORT = 8000
    
    def start_server():
        global httpd
        # Bind to 0.0.0.0 to make it accessible from the public IP
        with socketserver.TCPServer(("0.0.0.0", PORT), Handler) as httpd_server:
            httpd = httpd_server
            print(f"Servidor iniciado en http://0.0.0.0:{PORT}")
            httpd.serve_forever()

    server_thread = threading.Thread(target=start_server)
    server_thread.daemon = True
    server_thread.start()

def close_qr_window():
    global httpd
    if httpd:
        httpd.shutdown()