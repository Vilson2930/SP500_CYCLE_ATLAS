# ============================================================
# SP500 CYCLE ATLAS
# email_report.py
# ============================================================
#
# Envia:
#
# 1. Painel HTML no corpo do e-mail
# 2. PDF institucional completo como anexo
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
import mimetypes

from pathlib import Path
from datetime import datetime
from email.message import EmailMessage
from email.utils import formataddr


# ============================================================
# CAMINHOS
# ============================================================

DATA_DIR = Path("data")

REPORTS_DIR = Path("reports")


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


PDF_REPORT_FILE = (
    REPORTS_DIR
    /
    "relatorio_sp500_cycle_atlas.pdf"
)


# ============================================================
# SMTP
# ============================================================

SMTP_HOST = "smtp.gmail.com"

SMTP_PORT = 465


# ============================================================
# VARIÁVEIS DE AMBIENTE
# ============================================================

def _get_required_env(
    name: str,
) -> str:

    value = os.getenv(
        name,
        ""
    ).strip()

    if not value:

        raise RuntimeError(
            f"Variável obrigatória não encontrada: {name}"
        )

    return value


# ============================================================
# CARREGAR HTML
# ============================================================

def _load_html_report() -> str:

    if not HTML_REPORT_FILE.exists():

        raise FileNotFoundError(
            f"Relatório HTML não encontrado: "
            f"{HTML_REPORT_FILE}"
        )

    html_report = (
        HTML_REPORT_FILE
        .read_text(
            encoding="utf-8"
        )
    )

    if not html_report.strip():

        raise RuntimeError(
            "Relatório HTML está vazio."
        )

    return html_report


# ============================================================
# CARREGAR TXT
# ============================================================

def _load_text_report() -> str:

    if not TXT_REPORT_FILE.exists():

        return (
            "SP500 Cycle Atlas\n\n"
            "O painel HTML está disponível, "
            "mas o relatório TXT não foi encontrado."
        )

    text_report = (
        TXT_REPORT_FILE
        .read_text(
            encoding="utf-8"
        )
    )

    if not text_report.strip():

        return (
            "SP500 Cycle Atlas\n\n"
            "Relatório TXT vazio."
        )

    return text_report


# ============================================================
# VALIDAR PDF
# ============================================================

def _validate_pdf_report() -> Path:

    if not PDF_REPORT_FILE.exists():

        raise FileNotFoundError(
            f"PDF não encontrado: "
            f"{PDF_REPORT_FILE}"
        )

    file_size = (
        PDF_REPORT_FILE
        .stat()
        .st_size
    )

    if file_size < 1000:

        raise RuntimeError(
            "O PDF existe, mas parece inválido "
            f"({file_size} bytes)."
        )

    return PDF_REPORT_FILE


# ============================================================
# ASSUNTO
# ============================================================

def build_subject() -> str:

    date_str = (
        datetime.now()
        .strftime(
            "%d/%m/%Y"
        )
    )

    return (
        "SP500 Cycle Atlas | "
        "Painel de Controle | "
        f"{date_str}"
    )


# ============================================================
# ANEXAR PDF
# ============================================================

def attach_pdf(
    message: EmailMessage,
    pdf_path: Path,
):

    mime_type, _ = (
        mimetypes
        .guess_type(
            str(pdf_path)
        )
    )

    if mime_type:

        maintype, subtype = (
            mime_type
            .split(
                "/",
                1
            )
        )

    else:

        maintype = "application"
        subtype = "pdf"

    pdf_bytes = (
        pdf_path
        .read_bytes()
    )

    message.add_attachment(
        pdf_bytes,
        maintype=maintype,
        subtype=subtype,
        filename=pdf_path.name,
    )


# ============================================================
# MONTAR E-MAIL
# ============================================================

def build_email_message(
    email_user: str,
    email_to: str,
    html_report: str,
    text_report: str,
    pdf_path: Path,
) -> EmailMessage:

    message = EmailMessage()

    # --------------------------------------------------------
    # CABEÇALHO
    # --------------------------------------------------------

    message["From"] = (
        formataddr(
            (
                "SP500 Cycle Atlas",
                email_user,
            )
        )
    )

    message["To"] = (
        email_to
    )

    message["Subject"] = (
        build_subject()
    )

    # --------------------------------------------------------
    # TEXTO FALLBACK
    # --------------------------------------------------------

    message.set_content(
        text_report
    )

    # --------------------------------------------------------
    # HTML
    # --------------------------------------------------------

    message.add_alternative(
        html_report,
        subtype="html"
    )

    # --------------------------------------------------------
    # PDF
    # --------------------------------------------------------

    attach_pdf(
        message=message,
        pdf_path=pdf_path,
    )

    return message


# ============================================================
# ENVIO
# ============================================================

def send_email_report():

    print("")
    print("=" * 72)
    print(
        "SP500 CYCLE ATLAS — ENVIO DE E-MAIL"
    )
    print("=" * 72)

    # --------------------------------------------------------
    # CREDENCIAIS
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
        f"Remetente     : {email_user}"
    )

    print(
        f"Destinatário  : {email_to}"
    )

    # --------------------------------------------------------
    # RELATÓRIOS
    # --------------------------------------------------------

    html_report = (
        _load_html_report()
    )

    text_report = (
        _load_text_report()
    )

    pdf_path = (
        _validate_pdf_report()
    )

    print("")
    print(
        f"✅ HTML: "
        f"{HTML_REPORT_FILE}"
    )

    print(
        f"✅ TXT : "
        f"{TXT_REPORT_FILE}"
    )

    print(
        f"✅ PDF : "
        f"{pdf_path}"
    )

    print(
        f"✅ PDF tamanho: "
        f"{pdf_path.stat().st_size / 1024:.1f} KB"
    )

    # --------------------------------------------------------
    # MONTAR MENSAGEM
    # --------------------------------------------------------

    message = (
        build_email_message(
            email_user=email_user,
            email_to=email_to,
            html_report=html_report,
            text_report=text_report,
            pdf_path=pdf_path,
        )
    )

    # --------------------------------------------------------
    # SMTP
    # --------------------------------------------------------

    print("")
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
            "→ Enviando painel HTML + PDF..."
        )

        smtp.send_message(
            message
        )

    print("")
    print("=" * 72)
    print(
        "✅ RELATÓRIO ENVIADO COM SUCESSO"
    )
    print("=" * 72)

    print("")
    print(
        "Conteúdo enviado:"
    )

    print(
        "• Painel HTML no corpo do e-mail"
    )

    print(
        "• Relatório institucional PDF anexado"
    )

    print(
        f"• Arquivo: {pdf_path.name}"
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
        print(
            "❌ ERRO NO ENVIO DO E-MAIL"
        )
        print("=" * 72)

        print(
            f"{type(error).__name__}: "
            f"{error}"
        )

        raise
