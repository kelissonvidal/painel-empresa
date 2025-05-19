
from flask import Flask, request, jsonify
import os, json, time
import redis
import urllib.parse
import requests

app = Flask(__name__)

CONSULTOR_NUMERO = "553734490005"
ZAPI_INSTANCE_ID = os.getenv("ZAPI_INSTANCE_ID")
ZAPI_INSTANCE_TOKEN = os.getenv("ZAPI_INSTANCE_TOKEN")
ZAPI_CLIENT_TOKEN = os.getenv("ZAPI_CLIENT_TOKEN")

# Redis
redis_url = os.getenv("REDIS_URL")
parsed_url = urllib.parse.urlparse(redis_url)
redis_client = redis.Redis(
    host=parsed_url.hostname,
    port=parsed_url.port,
    password=parsed_url.password,
    ssl=True
)

# Leitura do arquivo config.json
with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

def enviar_mensagem(numero, texto):
    url = f"https://api.z-api.io/instances/{ZAPI_INSTANCE_ID}/token/{ZAPI_INSTANCE_TOKEN}/send-text"
    headers = {"Client-Token": ZAPI_CLIENT_TOKEN}
    payload = {"phone": numero, "message": texto}
    print(f"📤 Enviando para {numero}: {texto}")
    try:
        response = requests.post(url, json=payload, headers=headers)
        print("✅ Status:", response.status_code)
        print("📬 Resposta:", response.text)
    except Exception as e:
        print("❌ Erro no envio:", e)

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    print("📩 Payload recebido:")
    print(json.dumps(data, indent=2, ensure_ascii=False))

    if data.get("type") != "ReceivedCallback" or data.get("fromApi", False):
        print("⛔ Ignorado: não é mensagem recebida de cliente.")
        return jsonify({"status": "ignored"})

    mensagem = data.get("text", {}).get("message", "").strip()
    numero = data.get("phone", "").replace("+", "").replace(" ", "")
    redis_key = f"user:{numero}"

    try:
        user_data = redis_client.hgetall(redis_key)
    except Exception as e:
        print(f"❌ Erro ao acessar Redis para {numero}: {e}")
        return jsonify({"status": "erro redis"})

    if not user_data or b"etapa" not in user_data:
        etapa = 0
        redis_client.hset(redis_key, "etapa", 0)
    else:
        etapa = int(user_data[b"etapa"].decode())

    print(f"👣 Etapa atual de {numero}: {etapa}")

    if etapa >= 6:
        print("⛔ Lead já finalizado. Nenhuma ação será tomada.")
        return jsonify({"status": "finalizado"})

    if etapa == 0:
        enviar_mensagem(numero, config["saudacao"])
        time.sleep(1)
        enviar_mensagem(numero, config["coleta_nome"])
        redis_client.hset(redis_key, "etapa", 1)

    elif etapa == 1:
        redis_client.hset(redis_key, mapping={"nome": mensagem, "etapa": 2})
        nome = mensagem
        time.sleep(2)
        enviar_mensagem(numero, config["resposta_nome"].replace("{nome}", nome))
        time.sleep(2)
        enviar_mensagem(numero, config["pergunta_interesse"])

    elif etapa == 2:
        redis_client.hset(redis_key, mapping={"interesse": mensagem, "etapa": 3})
        time.sleep(2)
        enviar_mensagem(numero, config["pergunta_pagamento"])

    elif etapa == 3:
        redis_client.hset(redis_key, mapping={"forma_pagamento": mensagem, "etapa": 4})
        time.sleep(2)
        enviar_mensagem(numero, config["pergunta_forma"])

    elif etapa == 4:
        redis_client.hset(redis_key, mapping={"tipo_pagamento": mensagem, "etapa": 5})
        time.sleep(2)
        enviar_mensagem(numero, config["pergunta_info"])

    elif etapa == 5:
        redis_client.hset(redis_key, mapping={"info_extra": mensagem, "etapa": 6})
        nome = redis_client.hget(redis_key, "nome").decode()
        interesse = redis_client.hget(redis_key, "interesse").decode()
        forma = redis_client.hget(redis_key, "forma_pagamento").decode()
        tipo = redis_client.hget(redis_key, "tipo_pagamento").decode()
        extra = mensagem
        resumo = (
            "Novo lead captado:\n"
            f"Nome: {nome}\n"
            f"Interesse: {interesse}\n"
            f"Forma de pagamento: {forma}\n"
            f"Tipo de pagamento: {tipo}\n"
            f"Mais informações: {extra}\n"
            f"Contato: {numero}"
        )
        time.sleep(2)
        enviar_mensagem(numero, config["encerramento"].replace("{nome}", nome))
        time.sleep(1)
        enviar_mensagem(CONSULTOR_NUMERO, resumo)

    return jsonify({"status": "ok"})
