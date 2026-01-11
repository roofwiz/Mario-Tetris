from http.server import HTTPServer, SimpleHTTPRequestHandler
import sys

class CORSRequestHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cross-Origin-Opener-Policy', 'same-origin')
        self.send_header('Cross-Origin-Embedder-Policy', 'require-corp')
        self.send_header('Access-Control-Allow-Origin', '*')
        # Add MIME types for WASM if missing
        if self.path.endswith('.wasm'):
            self.send_header('Content-Type', 'application/wasm')
        super().end_headers()

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8001
    print(f"Serving on port {port} with COOP/COEP headers...")
    HTTPServer(('', port), CORSRequestHandler).serve_forever()
