import http.server
import json
import sys

class SimpleHandler(http.server.BaseHTTPRequestHandler):
    # Armazenamento simples na memória (dicionário de classe)
    store = {}

    def do_POST(self):
        if self.path == '/input':
            # Ler conteúdo do POST
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            data = json.loads(body)  # assume que é JSON

            # Guardar os dados em "store"
            self.__class__.store['value'] = data

            # Resposta HTTP 201 + JSON
            self.send_response(201)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            response = {'status': 'ok', 'received_data': data}
            self.wfile.write(json.dumps(response).encode('utf-8'))
        else:
            self.send_error(404, "Endpoint não encontrado")

    def do_GET(self):
        if self.path == '/output':
            if 'value' in self.__class__.store:
                data = self.__class__.store['value']
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()

                # Envia o que guardamos em /input
                self.wfile.write(json.dumps(data).encode('utf-8'))
            else:
                self.send_response(404)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Nenhum dado encontrado'}).encode('utf-8'))
        else:
            self.send_error(404, "Endpoint não encontrado")


if __name__ == '__main__':
    # Se houver argumento na linha de comando, usamos como porta; senão, default = 8000
    port = 8000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print("Uso: python server.py [porta]")
            sys.exit(1)

    server_address = ('', port)
    httpd = http.server.HTTPServer(server_address, SimpleHandler)
    print(f"Servidor rodando na porta {port}...")
    httpd.serve_forever()