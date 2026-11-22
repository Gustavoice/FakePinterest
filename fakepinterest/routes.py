
from flask import render_template, url_for, redirect, abort
from fakepinterest import app, database, bcrypt
from flask_login import login_required, login_user, logout_user, current_user
from fakepinterest.forms import FormLogin, FormCriarConta, FormFoto
from fakepinterest.models import Usuario, Foto
import os
from werkzeug.utils import secure_filename


@app.route("/", methods=["GET", "POST"])
def homepage():
    form_login = FormLogin()

    if form_login.validate_on_submit():
        usuario = Usuario.query.filter_by(
            email=form_login.email.data
        ).first()

        if usuario and bcrypt.check_password_hash(
            usuario.senha,
            form_login.senha.data
        ):
            login_user(usuario)

            return redirect(
                url_for("perfil", id_usuario=usuario.id)
            )

    return render_template(
        "homepage.html",
        form=form_login
    )


@app.route("/criarconta", methods=["GET", "POST"])
def criarconta():
    form_criarconta = FormCriarConta()

    if form_criarconta.validate_on_submit():

        senha_criptografada = bcrypt.generate_password_hash(
            form_criarconta.senha.data
        )

        usuario = Usuario(
            username=form_criarconta.username.data,
            email=form_criarconta.email.data,
            senha=senha_criptografada
        )

        database.session.add(usuario)
        database.session.commit()

        login_user(usuario, remember=True)

        return redirect(
            url_for("perfil", id_usuario=usuario.id)
        )

    return render_template(
        "criarconta.html",
        form=form_criarconta
    )


@app.route("/perfil/<id_usuario>", methods=["GET", "POST"])
@login_required
def perfil(id_usuario):

    if int(id_usuario) == int(current_user.id):

        # Usuário está vendo o próprio perfil
        form_foto = FormFoto()

        if form_foto.validate_on_submit():

            # Pegar o arquivo enviado pelo formulário
            arquivo = form_foto.foto.data

            # Criar um nome seguro para o arquivo
            nome_seguro = secure_filename(arquivo.filename)

            # Caminho completo para salvar a foto
            caminho_arquivo = os.path.join(
                os.path.abspath(os.path.dirname(__file__)),
                app.config["UPLOAD_FOLDER"],
                nome_seguro
            )

            # Salvar o arquivo na pasta fotos_post
            arquivo.save(caminho_arquivo)

            # Registrar a foto no banco de dados
            foto = Foto(
                imagem=nome_seguro,
                id_usuario=current_user.id
            )

            database.session.add(foto)
            database.session.commit()

        return render_template(
            "perfil.html",
            usuario=current_user,
            form=form_foto
        )

    else:

        # Usuário está vendo o perfil de outra pessoa
        usuario = Usuario.query.get(int(id_usuario))

        return render_template(
            "perfil.html",
            usuario=usuario,
            form=None
        )


@app.route("/logout")
@login_required
def logout():

    logout_user()

    return redirect(
        url_for("homepage")
    )


@app.route("/feed")
@login_required
def feed():
    fotos = Foto.query.order_by(Foto.data_criacao.desc()).all()#[:100] se quiser limitar
    return render_template("feed.html", fotos = fotos)


@app.route("/apagar_foto/<int:id_foto>", methods=["POST"])
@login_required
def apagar_foto(id_foto):

    # Buscar a publicação no banco de dados
    foto = Foto.query.get_or_404(id_foto)

    # Verificar se a publicação pertence ao usuário logado
    if int(foto.id_usuario) != int(current_user.id):
        abort(403)

    # Montar o caminho da imagem
    nome_arquivo = os.path.basename(foto.imagem)

    caminho_arquivo = os.path.join(
        os.path.abspath(os.path.dirname(__file__)),
        app.config["UPLOAD_FOLDER"],
        nome_arquivo
    )

    # Apagar a publicação do banco de dados
    database.session.delete(foto)
    database.session.commit()

    # Apagar o arquivo físico da pasta
    if os.path.isfile(caminho_arquivo):
        os.remove(caminho_arquivo)

    # Retornar ao perfil do usuário
    return redirect(
        url_for("perfil", id_usuario=current_user.id)
    )
