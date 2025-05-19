
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

# Conexão Redis
redis_url = os.getenv("REDIS_URL")
parsed_url = urllib.parse.urlparse(redis_url)
redis_client = redis.Redis(
    host=parsed_url.hostname,
    port=parsed_url.port,
    password=parsed_url.password,
    ssl=True
)

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
        enviar_mensagem(numero, "Olá! Seja muito bem-vindo. Qual é o seu nome, por favor?")
        redis_client.hset(redis_key, "etapa", 1)

    elif etapa == 1:
        redis_client.hset(redis_key, mapping={"nome": mensagem, "etapa": 2})
        time.sleep(2)
        enviar_mensagem(numero, f"{mensagem}, me diga por favor: você está buscando um lote para investimento ou para montar a sede da sua empresa?")

    elif etapa == 2:
        redis_client.hset(redis_key, mapping={"interesse": mensagem, "etapa": 3})
        time.sleep(2)
        enviar_mensagem(numero, "Perfeito! Agora me diz: pretende pagar à vista ou parcelado?")

    elif etapa == 3:
        redis_client.hset(redis_key, mapping={"forma_pagamento": mensagem, "etapa": 4})
        time.sleep(2)
        enviar_mensagem(numero, "Certo. Como pretende fazer esse pagamento? Cartão, Pix, financiamento, consórcio?")

    elif etapa == 4:
        redis_client.hset(redis_key, mapping={"tipo_pagamento": mensagem, "etapa": 5})
        time.sleep(2)
        enviar_mensagem(numero, "Gostaria de saber mais sobre localização, metragem, infraestrutura ou prefere falar direto com o consultor?")

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
        enviar_mensagem(numero, "Obrigado! Vou te encaminhar agora para um consultor que vai continuar seu atendimento.")
        time.sleep(1)
        enviar_mensagem(CONSULTOR_NUMERO, resumo)

    return jsonify({"status": "ok"})
