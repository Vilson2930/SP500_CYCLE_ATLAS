# ============================================================
# SP500 CYCLE ATLAS
# email_report.py
# ============================================================
#
# Responsável por:
#
# - ler o painel HTML gerado pelo report.py
# - enviar o relatório por e-mail
# - usar credenciais armazenadas em GitHub Secrets
#
# Secrets esperados:
#
# EMAIL_USER
# EMAIL_PASSWORD
# EMAIL_TO
#
# ============================================================

from __future__ import annotations

import os
import smtplib
from pathlib import Path
from email.message import EmailMessage
from email.utils import formataddr
from datetime import datetime


# ============================================================
# CONFIGURAÇÃO
# ============================================================

DATA_DIR = Path("data")

HTML_REPORT_FILE = (
    DATA_DIR
    /
    "current_report.html"
)

TXT_REPORT_FILE = (
    DATA_DIR
    /
    "current_report.txt"
)

SMTP_HOST = "smtp.gmail.com"

SMTP_PORT = 465


# ============================================================
# UTILITÁRIOS
# ============================================================

def _get_required_env(
    name: str,
) -> str:

    value = os.getenv(
        name
    )

    if not value:

        raise RuntimeError(
            f"Variável de ambiente obrigatória não encontrada: {name}"
        )

    return value.strip()


def _load_html_report() -> str:

    if not HTML_REPORT_FILE.exists():

        raise FileNotFoundError(
            f"Relatório HTML não encontrado: "
            f"{HTML_REPORT_FILE}"
        )

    return HTML_REPORT_FILE.read_text(
        encoding="utf-8"
    )


def _load_text_report() -> str:

    if not TXT_REPORT_FILE.exists():

        return (
            "SP500 Cycle Atlas\n\n"
            "O relatório em HTML foi gerado, "
            "mas a versão TXT não foi encontrada."
        )

    return TXT_REPORT_FILE.read_text(
        encoding="utf-8"
    )


# ============================================================
# ASSUNTO DO E-MAIL
# ============================================================

def build_subject() -> str:

    date_str = (
        datetime.now()
        .strftime(
            "%d/%m/%Y"
        )
    )

    return (
        f"SP500 Cycle Atlas | "
        f"Painel de Controle | "
        f"{date_str}"
    )


# ============================================================
# MONTAR MENSAGEM
# ============================================================

def build_email_message(
    email_user: str,
    email_to: str,
    html_report: str,
    text_report: str,
) -> EmailMessage:

    message = EmailMessage()

    message["From"] = formataddr(
        (
            "SP500 Cycle Atlas",
            email_user,
        )
    )

    message["To"] = email_to

    message["Subject"] = (
        build_subject()
    )

    # --------------------------------------------------------
    # Fallback texto
    # --------------------------------------------------------

    message.set_content(
        text_report
    )

    # --------------------------------------------------------
    # Corpo principal HTML
    # --------------------------------------------------------

    message.add_alternative(
        html_report,
        subtype="html"
    )

    return message


# ============================================================
# ENVIO SMTP
# ============================================================

def send_email_report():

    print("=" * 72)
    print("SP500 CYCLE ATLAS — ENVIO DE E-MAIL")
    print("=" * 72)

    # --------------------------------------------------------
    # Secrets / variáveis
    # --------------------------------------------------------

    email_user = (
        _get_required_env(
            "EMAIL_USER"
        )
    )

    email_password = (
        _get_required_env(
            "EMAIL_PASSWORD"
        )
    )

    email_to = (
        _get_required_env(
            "EMAIL_TO"
        )
    )

    print(
        f"Remetente: {email_user}"
    )

    print(
        f"Destinatário: {email_to}"
    )

    # --------------------------------------------------------
    # Relatórios
    # --------------------------------------------------------

    html_report = (
        _load_html_report()
    )

    text_report = (
        _load_text_report()
    )

    print(
        f"HTML carregado: "
        f"{HTML_REPORT_FILE}"
    )

    print(
        f"TXT carregado: "
        f"{TXT_REPORT_FILE}"
    )

    # --------------------------------------------------------
    # Mensagem
    # --------------------------------------------------------

    message = (
        build_email_message(
            email_user=email_user,
            email_to=email_to,
            html_report=html_report,
            text_report=text_report,
        )
    )

    # --------------------------------------------------------
    # Conexão segura
    # --------------------------------------------------------

    print(
        "→ Conectando ao Gmail SMTP..."
    )

    with smtplib.SMTP_SSL(
        SMTP_HOST,
        SMTP_PORT,
        timeout=30,
    ) as smtp:

        print(
            "→ Autenticando..."
        )

        smtp.login(
            email_user,
            email_password,
        )

        print(
            "→ Enviando relatório..."
        )

        smtp.send_message(
            message
        )

    print("")
    print(
        "✅ Relatório enviado por e-mail com sucesso."
    )

    return True


# ============================================================
# EXECUÇÃO
# ============================================================

if __name__ == "__main__":

    try:

        send_email_report()

    except Exception as error:

        print("")
        print("=" * 72)
        print("❌ ERRO NO ENVIO DO E-MAIL")
        print("=" * 72)

        print(
            f"{type(error).__name__}: "
            f"{error}"
        )

        raise
