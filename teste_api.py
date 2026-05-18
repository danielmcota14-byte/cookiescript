from flask import Flask, request, jsonify
import json

app = Flask(__name__)

# Configurações
HOST = "localhost"
PORT = 3000


@app.route("/status", methods=["GET"])
def status_api():
    # Rota: GET /status
    # Implementar lógica aqui
    return jsonify({"message": "Rota /status executada"})


if __name__ == "__main__":
    print(f"Serviço api_teste rodando em http://{HOST}:{PORT}")
    app.run(host=HOST, port=PORT, debug=True)
