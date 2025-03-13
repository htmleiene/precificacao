from flask import Flask, render_template, request, redirect, url_for, session, send_file
from datetime import datetime
import requests
import sqlite3
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

app = Flask(__name__)
app.secret_key = "sua_chave_secreta"  # Chave para criptografar a sessão

# Dados de usuários (simulado)
usuarios = {}

# Configuração do banco de dados
def init_db():
    conn = sqlite3.connect('calculadora.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS calculos
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  usuario TEXT,
                  area TEXT,
                  valor_hora REAL,
                  data TEXT)''')
    conn.commit()
    conn.close()

init_db()

# Função para obter remuneração média da API do Adzuna
def obter_remuneracao_adzuna(area, localizacao="Brasil"):
    app_id = "{API_ID}"  # Substitua pelo seu App ID
    app_key = "{API_KEY}"  # Substitua pelo seu App Key
    url = f"https://api.adzuna.com/v1/api/jobs/br/salary_stats"
    params = {
        "app_id": app_id,
        "app_key": app_key,
        "location0": localizacao,
        "what": area,
        "content-type": "application/json"
    }
    try:
        print(f"Consultando API para a área: {area}")  # Log para depuração
        response = requests.get(url, params=params)
        if response.status_code == 200:
            dados = response.json()
            print(f"Dados retornados pela API: {dados}")  # Log para depuração
            # Retorna a remuneração média (em R$/ano)
            return dados.get("mean", 50000) / 12  # Converte para R$/mês
        else:
            print(f"Erro na API: {response.status_code}")
            return 50000 / 12  # Valor padrão em caso de erro
    except Exception as e:
        print(f"Erro ao acessar a API: {e}")
        return 50000 / 12  # Valor padrão em caso de exceção

# Rota principal (login)
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        email = request.form.get("email")
        senha = request.form.get("senha")
        if email in usuarios and usuarios[email] == senha:
            session["usuario"] = email
            return redirect(url_for("area"))
        else:
            return render_template("index.html", erro="Credenciais inválidas.")
    return render_template("index.html")

# Rota de cadastro
@app.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    if request.method == "POST":
        email = request.form.get("email")
        senha = request.form.get("senha")
        if email in usuarios:
            return render_template("cadastro.html", erro="E-mail já cadastrado.")
        usuarios[email] = senha
        session["usuario"] = email
        return redirect(url_for("area"))
    return render_template("cadastro.html")

# Rota de escolha da área
@app.route("/area", methods=["GET", "POST"])
def area():
    if "usuario" not in session:
        return redirect(url_for("index"))

    if request.method == "POST":
        area = request.form.get("area")
        session["area"] = area  # Armazena a área na sessão
        return redirect(url_for("formulario"))

    return render_template("area.html")

# Rota de logout
@app.route("/logout")
def logout():
    session.pop("usuario", None)
    return redirect(url_for("index"))

# Rota do formulário específico da área
@app.route("/formulario", methods=["GET", "POST"])
def formulario():
    if "usuario" not in session or "area" not in session:
        return redirect(url_for("index"))

    if request.method == "POST":
        tipo_servico = request.form.get("tipo_servico")
        session["tipo_servico"] = tipo_servico

        # Redireciona para a próxima etapa com base no tipo de serviço
        if tipo_servico == "frequente":
            return redirect(url_for("calcular_frequente"))
        elif tipo_servico == "demanda":
            return redirect(url_for("calcular_demanda"))
        elif tipo_servico == "pontual":
            return redirect(url_for("calcular_pontual"))

    # Obtém a remuneração média da área selecionada
    area = session["area"]
    remuneracao_media = obter_remuneracao_adzuna(area)  # Usa a API do Adzuna
    return render_template("formulario.html", remuneracao_media=remuneracao_media)

@app.route("/calcular_frequente", methods=["GET", "POST"])
def calcular_frequente():
    if "usuario" not in session or "area" not in session or "tipo_servico" not in session:
        return redirect(url_for("index"))

    if request.method == "POST":
        horas_mes = float(request.form.get("horas_mes"))
        remuneracao_media = obter_remuneracao_adzuna(session["area"])
        valor_hora = remuneracao_media / horas_mes
        session["valor_hora"] = valor_hora
        return redirect(url_for("resultado"))

    return render_template("calcular_frequente.html")

@app.route("/calcular_demanda", methods=["GET", "POST"])
def calcular_demanda():
    if "usuario" not in session or "area" not in session or "tipo_servico" not in session:
        return redirect(url_for("index"))

    if request.method == "POST":
        horas_demanda = float(request.form.get("horas_demanda"))
        remuneracao_media = obter_remuneracao_adzuna(session["area"])
        valor_hora = remuneracao_media / horas_demanda
        session["valor_hora"] = valor_hora
        return redirect(url_for("resultado"))

    return render_template("calcular_demanda.html")

@app.route("/calcular_pontual", methods=["GET", "POST"])
def calcular_pontual():
    if "usuario" not in session or "area" not in session or "tipo_servico" not in session:
        return redirect(url_for("index"))

    if request.method == "POST":
        valor_projeto = float(request.form.get("valor_projeto"))
        horas_projeto = float(request.form.get("horas_projeto"))
        valor_hora = valor_projeto / horas_projeto
        session["valor_hora"] = valor_hora
        return redirect(url_for("resultado"))

    return render_template("calcular_pontual.html")

# Rota de resultado
@app.route("/resultado", methods=["GET", "POST"])
def resultado():
    if "usuario" not in session or "area" not in session:
        return redirect(url_for("index"))

    if request.method == "POST":
        # Captura os dados do formulário
        dados = request.form.to_dict()
        session["dados"] = dados

        # Lógica de cálculo
        try:
            ganho_desejado = float(dados.get("ganho_desejado"))
            custos_fixos = float(dados.get("custos_fixos"))
            horas_trabalhadas = float(dados.get("horas_trabalhadas"))
            if ganho_desejado < 0 or custos_fixos < 0 or horas_trabalhadas <= 0:
                return render_template("formulario.html", erro="Valores inválidos. Insira números positivos.")
            valor_hora = (ganho_desejado + custos_fixos) / horas_trabalhadas
            session["valor_hora"] = valor_hora
        except ValueError:
            return render_template("formulario.html", erro="Por favor, insira valores numéricos válidos.")

        return redirect(url_for("extras"))

    # Verifica se o valor_hora está na sessão
    if "valor_hora" not in session:
        return redirect(url_for("formulario"))

    # Renderiza o template com o valor_hora
    return render_template("resultado.html", valor_hora=session["valor_hora"])

# Rota de funcionalidades extras
@app.route("/extras")
def extras():
    if "usuario" not in session or "valor_hora" not in session:
        return redirect(url_for("index"))

    return render_template("extras.html", valor_hora=session["valor_hora"])

# Rota para salvar cálculo no banco de dados
@app.route("/salvar_calculo")
def salvar_calculo():
    if "usuario" not in session or "valor_hora" not in session:
        return redirect(url_for("index"))

    conn = sqlite3.connect('calculadora.db')
    c = conn.cursor()
    c.execute("INSERT INTO calculos (usuario, area, valor_hora, data) VALUES (?, ?, ?, ?)",
              (session["usuario"], session["area"], session["valor_hora"], datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    conn.close()

    return redirect(url_for("extras", sucesso="Cálculo salvo com sucesso!"))

# Rota para exportar resultado em PDF
@app.route("/exportar_pdf")
def exportar_pdf():
    if "usuario" not in session or "valor_hora" not in session:
        return redirect(url_for("index"))

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    p.drawString(100, 750, f"Usuário: {session['usuario']}")
    p.drawString(100, 730, f"Área: {session['area']}")
    p.drawString(100, 710, f"Valor/Hora: R$ {session['valor_hora']:.2f}")
    p.showPage()
    p.save()

    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="resultado.pdf", mimetype="application/pdf")

# Rota para compartilhar cálculo
@app.route("/compartilhar/<int:calculo_id>")
def compartilhar(calculo_id):
    conn = sqlite3.connect('calculadora.db')
    c = conn.cursor()
    c.execute("SELECT * FROM calculos WHERE id = ?", (calculo_id,))
    calculo = c.fetchone()
    conn.close()

    if calculo:
        return render_template("compartilhar.html", calculo=calculo)
    else:
        return redirect(url_for("extras", erro="Cálculo não encontrado."))

# Inicialização do app
if __name__ == "__main__":
    app.run(debug=True)