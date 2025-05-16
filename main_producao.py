
from flask import Flask, request, jsonify
import os, json, requests

app = Flask(__name__)

USERS_FILE = "usuarios.json"
CONSULTOR_NUMERO = "553734490005"
ZAPI_INSTANCE_ID = os.getenv("ZAPI_INSTANCE_ID")
ZAPI_INSTANCE_TOKEN = os.getenv("ZAPI_INSTANCE_TOKEN")
ZAPI_CLIENT_TOKEN = os.getenv("ZAPI_CLIENT_TOKEN")

def carregar_dados():
    try:
        if os.path.exists(USERS_FILE):
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
                else:
                    print("⚠️ usuarios.json contém estrutura inválida (esperado dict, recebido list).")
    except Exception as e:
        print("⚠️ Erro ao carregar usuarios.json:", e)
    return {}

def salvar_dados(dados):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=2, ensure_ascii=False)

def enviar_mensagem(numero, texto):
    url = f"https://api.z-api.io/instances/{ZAPI_INSTANCE_ID}/token/{ZAPI_INSTANCE_TOKEN}/send-text"
    headers = {"Client-Token": ZAPI_CLIENT_TOKEN}
    payload = {
        "phone": numero,
        "message": texto
    }
    requests.post(url, json=payload, headers=headers)

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    print("📩 Payload recebido:")
    print(json.dumps(data, indent=2, ensure_ascii=False))

    if data.get("type") != "ReceivedCallback":
        return jsonify({"status": "ignored"})

    mensagem = data.get("text", {}).get("message", "").strip()
    numero = data.get("phone", "").replace("+", "").replace(" ", "")
    usuarios = carregar_dados()

    if numero not in usuarios:
        usuarios[numero] = {"etapa": 0}
    
    etapa = usuarios[numero]["etapa"]

    if etapa == 0:
        enviar_mensagem(numero, "Olá! Seja muito bem-vindo. Qual é o seu nome, por favor?")
        usuarios[numero]["etapa"] = 1

    elif etapa == 1:
        usuarios[numero]["nome"] = mensagem
        enviar_mensagem(numero, f"{mensagem}, me diga por favor: você está buscando um lote para investimento ou para montar a sede da sua empresa?")
        usuarios[numero]["etapa"] = 2

    elif etapa == 2:
        usuarios[numero]["interesse"] = mensagem
        enviar_mensagem(numero, "Perfeito! Agora me diz: pretende pagar à vista ou parcelado?")
        usuarios[numero]["etapa"] = 3

    elif etapa == 3:
        usuarios[numero]["forma_pagamento"] = mensagem
        enviar_mensagem(numero, "Certo. Como pretende fazer esse pagamento? Cartão, Pix, financiamento, consórcio?")
        usuarios[numero]["etapa"] = 4

    elif etapa == 4:
        usuarios[numero]["tipo_pagamento"] = mensagem
        enviar_mensagem(numero, "Gostaria de saber mais sobre localização, metragem, infraestrutura ou prefere falar direto com o consultor?")
        usuarios[numero]["etapa"] = 5

    elif etapa == 5:
        usuarios[numero]["info_extra"] = mensagem
        resumo = (
            "Novo lead captado:\n"
            f"Nome: {usuarios[numero].get('nome')}\n"
            f"Interesse: {usuarios[numero].get('interesse')}\n"
            f"Forma de pagamento: {usuarios[numero].get('forma_pagamento')}\n"
            f"Tipo de pagamento: {usuarios[numero].get('tipo_pagamento')}\n"
            f"Mais informações: {usuarios[numero].get('info_extra')}\n"
            f"Contato: {numero}"
        )

        enviar_mensagem(numero, "Obrigado! Vou te encaminhar agora para um consultor que vai continuar seu atendimento.")
        enviar_mensagem(CONSULTOR_NUMERO, resumo)

        usuarios[numero]["etapa"] = 6

    salvar_dados(usuarios)
    return jsonify({"status": "ok"})
