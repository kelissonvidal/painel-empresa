
from flask import Flask, request, jsonify
import os, json, time, requests
import redis
import urllib.parse

app = Flask(__name__)

CONSULTOR_NUMERO = "553734490005"
ZAPI_INSTANCE_ID = os.getenv("ZAPI_INSTANCE_ID")
ZAPI_INSTANCE_TOKEN = os.getenv("ZAPI_INSTANCE_TOKEN")
ZAPI_CLIENT_TOKEN = os.getenv("ZAPI_CLIENT_TOKEN")

redis_url = os.getenv("REDIS_URL")
parsed_url = urllib.parse.urlparse(redis_url)
redis_client = redis.Redis(
    host=parsed_url.hostname,
    port=parsed_url.port,
    password=parsed_url.password,
    ssl=True
)

CONFIG_URL = "https://raw.githubusercontent.com/kelissonvidal/painel-empresa/refs/heads/main/config.json"

def carregar_config():
    try:
        r = requests.get(CONFIG_URL)
        if r.status_code == 200:
            return r.json()
        print("❌ Falha ao carregar config.json remoto")
        return {}
    except Exception as e:
        print("❌ Erro ao acessar config.json remoto:", e)
        return {}

def enviar_mensagem(numero, texto):
    url = f"https://api.z-api.io/instances/{ZAPI_INSTANCE_ID}/token/{ZAPI_INSTANCE_TOKEN}/send-text"
    headers = {"Client-Token": ZAPI_CLIENT_TOKEN}
    payload = {"phone": numero, "message": texto}
    try:
        r = requests.post(url, json=payload, headers=headers)
        print(f"📤 Enviando para {numero}: {texto}")
        print("✅ Status:", r.status_code)
        print("📬 Resposta:", r.text)
    except Exception as e:
        print("❌ Erro no envio:", e)

@app.route("/webhook", methods=["POST"])
def webhook():
    config = carregar_config()
    data = request.json

    if data.get("type") != "ReceivedCallback" or data.get("fromApi", False):
        return jsonify({"status": "ignored"})

    mensagem = data.get("text", {}).get("message", "").strip()
    numero = data.get("phone", "").replace("+", "").replace(" ", "")
    redis_key = f"user:{numero}"

    user_data = redis_client.hgetall(redis_key)
    if not user_data or b"etapa" not in user_data:
        etapa = 0
        redis_client.hset(redis_key, "etapa", 0)
    else:
        etapa = int(user_data[b"etapa"].decode())

    print(f"👣 Etapa atual: {etapa}")

    if etapa >= 6:
        return jsonify({"status": "finalizado"})

    if etapa == 0:
        enviar_mensagem(numero, config.get("saudacao", "Olá!"))
        time.sleep(1)
        enviar_mensagem(numero, config.get("coleta_nome", "Qual seu nome?"))
        redis_client.hset(redis_key, "etapa", 1)

    elif etapa == 1:
        redis_client.hset(redis_key, mapping={"nome": mensagem, "etapa": 2})
        nome = mensagem
        time.sleep(2)
        enviar_mensagem(numero, config.get("resposta_nome", "Prazer em te conhecer, {nome}!").replace("{nome}", nome))
        time.sleep(2)
        enviar_mensagem(numero, config.get("pergunta_interesse", "Qual o seu interesse?"))

    elif etapa == 2:
        redis_client.hset(redis_key, mapping={"interesse": mensagem, "etapa": 3})
        time.sleep(2)
        enviar_mensagem(numero, config.get("pergunta_pagamento", "Como pretende pagar?"))

    elif etapa == 3:
        redis_client.hset(redis_key, mapping={"forma_pagamento": mensagem, "etapa": 4})
        time.sleep(2)
        enviar_mensagem(numero, config.get("pergunta_forma", "Qual a forma de pagamento?"))

    elif etapa == 4:
        redis_client.hset(redis_key, mapping={"tipo_pagamento": mensagem, "etapa": 5})
        time.sleep(2)
        enviar_mensagem(numero, config.get("pergunta_info", "Deseja saber mais ou falar com o consultor?"))

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
        enviar_mensagem(numero, config.get("encerramento", "Obrigado, {nome}!").replace("{nome}", nome))
        time.sleep(1)
        enviar_mensagem(CONSULTOR_NUMERO, resumo)

    return jsonify({"status": "ok"})
