from flask import Flask, render_template, request, redirect, url_for, session, send_file
from datetime import datetime
import sqlite3
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

app = Flask(__name__)
app.secret_key = "sua_chave_secreta"  # Chave para criptografar a sessão

# Dicionário de salários médios
salarios_medios = {
    "TI": 7_431,  # Engenheiros de Computação
    "Design": 7_347,  # Autores roteiristas
    "Fotografia": 4_213,  # Desenhista Industrial de Calçados
    "Consultoria": 7_524,  # Arquitetos e Engenheiros
    "Educação": 3_726,  # Professores de Artesanato
    "Trabalhos Manuais": 3_726,  # Professores de Artesanato
    "Saúde": 4_000  # Média estimada para profissionais da saúde
}

# Dados de usuários (simulado)
usuarios = {}

# Configuração do banco de dados
def init_db():
    conn = sqlite3.connect('calculadora.db')
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS usuarios (
                  email TEXT PRIMARY KEY,
                  senha TEXT)''')

    c.execute('''CREATE TABLE IF NOT EXISTS calculos (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  usuario TEXT,
                  area TEXT,
                  valor_hora REAL,
                  data TEXT)''')

    conn.commit()
    conn.close()

init_db()  # Garante que o banco é inicializado ao iniciar o Flask

# Rota principal (login)
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        email = request.form.get("email")
        senha = request.form.get("senha")

        conn = sqlite3.connect('calculadora.db')
        c = conn.cursor()
        c.execute("SELECT * FROM usuarios WHERE email = ? AND senha = ?", (email, senha))
        user = c.fetchone()
        conn.close()

        if user:
            session["usuario"] = email  # Mantém sessão ativa
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

        conn = sqlite3.connect('calculadora.db')
        c = conn.cursor()
        c.execute("SELECT * FROM usuarios WHERE email = ?", (email,))
        if c.fetchone():
            return render_template("cadastro.html", erro="E-mail já cadastrado.")

        c.execute("INSERT INTO usuarios (email, senha) VALUES (?, ?)", (email, senha))
        conn.commit()
        conn.close()

        session["usuario"] = email  # Armazena sessão
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

    return render_template("area.html", areas=salarios_medios.keys())

# Rota de resultado (exibe o valor por hora)
@app.route("/resultado")
def resultado():
    if "usuario" not in session or "area" not in session or "valor_hora" not in session:
        return redirect(url_for("index"))

    # Obtém os valores da sessão
    area = session["area"]
    valor_hora = session["valor_hora"]

    # Renderiza o template com os valores
    return render_template("resultado.html", area=area, valor_hora=valor_hora)

# Rota de logout
@app.route("/logout")
def logout():
    session.pop("usuario", None)
    session.pop("area", None)
    session.pop("valor_hora", None)
    return redirect(url_for("index"))

# Rota do formulário principal
@app.route("/formulario", methods=["GET", "POST"])
def formulario():
    if "usuario" not in session or "area" not in session:
        return redirect(url_for("index"))

    if request.method == "POST":
        tipo_servico = request.form.get("tipo_servico")
        session["tipo_servico"] = tipo_servico

        # Redireciona para a rota específica com base no tipo de serviço
        if tipo_servico == "frequente":
            return redirect(url_for("calcular_frequente"))
        elif tipo_servico == "demanda":
            return redirect(url_for("calcular_demanda"))
        elif tipo_servico == "pontual":
            return redirect(url_for("calcular_pontual"))

    # Obtém a remuneração média da área selecionada
    area = session["area"]
    remuneracao_media = salarios_medios.get(area, 0)
    return render_template("formulario.html", remuneracao_media=remuneracao_media)

# Rota para cálculo de serviço frequente
@app.route("/calcular_frequente", methods=["GET", "POST"])
def calcular_frequente():
    if "usuario" not in session or "area" not in session:
        return redirect(url_for("index"))

    if request.method == "POST":
        horas_mes = request.form.get("horas_mes")

        if not horas_mes:
            return render_template("calcular_frequente.html", erro="Preencha as horas!")

        try:
            horas_mes = float(horas_mes)

            if horas_mes <= 0:  # Evita divisão por zero
                return render_template("calcular_frequente.html", erro="As horas devem ser maiores que zero!")

            remuneracao_media = salarios_medios.get(session["area"], 50000)
            valor_hora = remuneracao_media / max(horas_mes, 1)  # Garante que horas_mes seja pelo menos 1

            session["valor_hora"] = round(valor_hora, 2)  # Armazena resultado na sessão arredondado
            return redirect(url_for("resultado"))
        except ValueError:
            return render_template("calcular_frequente.html", erro="Digite um número válido!")

    return render_template("calcular_frequente.html")

# Rota para cálculo de serviço por demanda
@app.route("/calcular_demanda", methods=["GET", "POST"])
def calcular_demanda():
    if "usuario" not in session or "area" not in session or "tipo_servico" not in session:
        return redirect(url_for("index"))

    if request.method == "POST":
        horas_demanda = float(request.form.get("horas_demanda"))
        remuneracao_media = salarios_medios.get(session["area"], 50000)  # Usa o dicionário de salários
        valor_hora = remuneracao_media / horas_demanda
        session["valor_hora"] = valor_hora
        return redirect(url_for("resultado"))

    return render_template("calcular_demanda.html")

# Rota para cálculo de serviço pontual
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
        return render_template("compartilhas.html", calculo=calculo)
    else:
        return redirect(url_for("extras", erro="Cálculo não encontrado."))

# Inicialização do app
if __name__ == "__main__":
    app.run(debug=True)