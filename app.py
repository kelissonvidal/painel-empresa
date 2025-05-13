
from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, jsonify
import os, json
from datetime import datetime

app = Flask(__name__)
app.secret_key = "chave_secreta_simples"

CONFIG_DIR = "configs"
USERS_FILE = "usuarios.json"
AUDIO_DIR = "audios"
os.makedirs(CONFIG_DIR, exist_ok=True)
os.makedirs(AUDIO_DIR, exist_ok=True)

@app.route("/")
def home():
    if "usuario" in session:
        return redirect(url_for("painel"))
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        senha = request.form["senha"]
        if os.path.exists(USERS_FILE):
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                usuarios = json.load(f)
            for user in usuarios:
                if user["email"] == email and user["senha"] == senha:
                    session["usuario"] = user["empresa"]
                    return redirect(url_for("painel"))
        return "Login inválido"
    return render_template("login.html")

@app.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    if request.method == "POST":
        novo = {
            "empresa": request.form["empresa"],
            "email": request.form["email"],
            "senha": request.form["senha"]
        }
        usuarios = []
        if os.path.exists(USERS_FILE):
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                usuarios = json.load(f)
        usuarios.append(novo)
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(usuarios, f, indent=2, ensure_ascii=False)
        return redirect(url_for("login"))
    return render_template("cadastro.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/painel")
def painel():
    if "usuario" not in session:
        return redirect(url_for("login"))
    return render_template("form.html")

@app.route("/ver_logs")
def ver_logs():
    if "usuario" not in session:
        return redirect(url_for("login"))
    empresa = session["usuario"].lower().replace(" ", "_")
    log_path = f"logs/{empresa}/log.json"
    registros = []
    if os.path.exists(log_path):
        with open(log_path, "r", encoding="utf-8") as f:
            registros = json.load(f)
    return render_template("ver_logs.html", registros=registros)

@app.route("/salvar", methods=["POST"])
def salvar():
    if "usuario" not in session:
        return redirect(url_for("login"))
    dados = request.form.to_dict()
    nome_arquivo = session["usuario"].lower().replace(" ", "_") + ".json"

    config = {
        "empresa": dados.get("empresa"),
        "numero_zapi": dados.get("numero_zapi"),
        "consultor": {
            "nome": dados.get("nome_consultor"),
            "numero": dados.get("numero_consultor")
        },
        "cor": dados.get("cor"),
        "atendente": dados.get("atendente"),
        "mensagens": {
            "saudacao": dados.get("saudacao"),
            "coleta_nome": dados.get("coleta_nome"),
            "encerramento": dados.get("encerramento")
        },
        "fluxo": {
            "interesse": [dados.get("interesse1"), dados.get("interesse2")],
            "pagamento": [dados.get("pagamento1"), dados.get("pagamento2")],
            "avista_detalhe": [
                dados.get("avista1"),
                dados.get("avista2"),
                dados.get("avista3"),
                dados.get("avista4")
            ],
            "entrada": [
                dados.get("entrada1"),
                dados.get("entrada2"),
                dados.get("entrada3"),
                dados.get("entrada4"),
                dados.get("entrada5")
            ],
            "parcelas": [
                dados.get("parcelas1"),
                dados.get("parcelas2"),
                dados.get("parcelas3"),
                dados.get("parcelas4")
            ]
        },
        "config_avancada": {
            "tempo_bloco": int(dados.get("tempo_bloco", 3)),
            "palavras_por_bloco": int(dados.get("palavras_por_bloco", 12)),
            "usar_audios": dados.get("usar_audios") == "on"
        }
    }

    with open(os.path.join(CONFIG_DIR, nome_arquivo), "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    return redirect(url_for("painel"))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
