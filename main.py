
import os
import time
import re
import logging
import threading
import requests

from bs4 import BeautifulSoup
from flask import Flask

# ==================================================
# CONFIGURAÇÕES
# ==================================================

NOME_PERSONAGEM = "uCria"
URL_PERSONAGEM = (
    f"https://mudomix.com/profile/character/{NOME_PERSONAGEM}"
)

# Configure DISCORD_WEBHOOK_URL nas variáveis de ambiente do Render.
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()

INTERVALO_SEGUNDOS = 30
TIMEOUT_SEGUNDOS = 15

app = Flask(__name__)

# Logs com horário e saída imediata no Render.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    force=True,
)
log = logging.getLogger("mu_monitor")

sessao = requests.Session()
sessao.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,"
              "application/xml;q=0.9,*/*;q=0.8",
})

# ==================================================
# SERVIDOR WEB
# ==================================================

@app.route("/")
def home():
    return "Bot Mu Domix: servidor ativo.", 200


@app.route("/health")
def health():
    return {
        "servidor": "ativo",
        "personagem": NOME_PERSONAGEM,
        "monitoramento": "thread iniciada",
    }, 200


# ==================================================
# DISCORD
# ==================================================

def enviar_alerta_discord(mensagem):
    if not DISCORD_WEBHOOK_URL:
        log.error(
            "Webhook não configurado. "
            "Defina DISCORD_WEBHOOK_URL no Render."
        )
        return False

    try:
        resposta = requests.post(
            DISCORD_WEBHOOK_URL,
            json={"content": mensagem},
            timeout=TIMEOUT_SEGUNDOS,
        )

        if resposta.status_code in (200, 204):
            log.info("Discord: mensagem enviada com sucesso.")
            return True

        log.error(
            "Discord retornou HTTP %s: %s",
            resposta.status_code,
            resposta.text[:500],
        )
        return False

    except requests.RequestException:
        log.exception("Falha ao enviar mensagem ao Discord.")
        return False


# ==================================================
# DIAGNÓSTICO DO PERFIL
# ==================================================

def monitorar():
    log.info("=" * 55)
    log.info("INICIANDO VERIFICAÇÃO DO PERSONAGEM: %s",
             NOME_PERSONAGEM)
    log.info("URL consultada: %s", URL_PERSONAGEM)

    inicio = time.monotonic()

    try:
        resposta = sessao.get(
            URL_PERSONAGEM,
            timeout=TIMEOUT_SEGUNDOS,
            allow_redirects=True,
        )

        log.info(
            "Resposta HTTP: %s | Tempo: %.2fs | URL final: %s",
            resposta.status_code,
            time.monotonic() - inicio,
            resposta.url,
        )

        if resposta.status_code != 200:
            log.error(
                "O site não retornou HTTP 200. "
                "Não será feita nenhuma conclusão sobre o personagem."
            )
            return

        soup = BeautifulSoup(resposta.text, "html.parser")
        titulo = soup.title.get_text(" ", strip=True) if soup.title else "(sem título)"
        texto = soup.get_text(" ", strip=True)
        texto_limpo = re.sub(r"\s+", " ", texto).strip()

        log.info("Título da página: %s", titulo)
        log.info("Tamanho do HTML: %s caracteres", len(resposta.text))
        log.info("Tamanho do texto extraído: %s caracteres", len(texto_limpo))
        log.info("Trecho do conteúdo: %s", texto_limpo[:1200])

        if not texto_limpo:
            log.warning(
                "A página não contém texto extraível. "
                "Pode depender de JavaScript ou de outra requisição."
            )
            return

        # Diagnóstico apenas: não confundir números aleatórios
        # da página com as coordenadas reais do personagem.
        padrao = r"(?<!\d)(\d{1,3})\s*[/,]\s*(\d{1,3})(?!\d)"
        candidatos = re.findall(padrao, texto_limpo)

        log.info(
            "Pares numéricos candidatos a coordenadas: %s",
            candidatos[:20] if candidatos else "nenhum",
        )

        palavras_status = re.findall(
            r".{0,60}\b(?:online|offline)\b.{0,100}",
            texto_limpo,
            flags=re.IGNORECASE,
        )

        log.info(
            "Trechos contendo online/offline: %s",
            palavras_status[:10] if palavras_status else "nenhum",
        )

        log.info(
            "VERIFICAÇÃO CONCLUÍDA em %.2f segundos.",
            time.monotonic() - inicio,
        )
        log.info(
            "Este modo é diagnóstico: ainda não confirma "
            "mapa, coordenadas nem status real."
        )

    except requests.Timeout:
        log.error(
            "TIMEOUT: o site demorou mais de %s segundos.",
            TIMEOUT_SEGUNDOS,
        )

    except requests.RequestException:
        log.exception("ERRO DE CONEXÃO ao consultar o perfil.")

    except Exception:
        log.exception("ERRO INESPERADO durante o diagnóstico.")

    finally:
        log.info("FIM DO CICLO DE VERIFICAÇÃO.")


# ==================================================
# LOOP DE MONITORAMENTO
# ==================================================

def loop_monitoramento():
    log.info("Loop de monitoramento iniciado.")
    log.info("Intervalo configurado: %s segundos.", INTERVALO_SEGUNDOS)

    enviar_alerta_discord(
        f"🟢 **BOT DE DIAGNÓSTICO INICIADO**\n"
        f"Personagem: **{NOME_PERSONAGEM}**\n"
        f"Intervalo: {INTERVALO_SEGUNDOS} segundos."
    )

    while True:
        inicio = time.monotonic()

        try:
            monitorar()
        except Exception:
            log.exception("Erro não tratado no ciclo.")

        # Mantém aproximadamente 30 segundos entre os inícios
        # dos ciclos, sem sobrepor consultas.
        duracao = time.monotonic() - inicio
        espera = max(1, INTERVALO_SEGUNDOS - duracao)

        log.info("Próxima verificação em %.1f segundos.", espera)
        time.sleep(espera)


# ==================================================
# INICIALIZAÇÃO
# ==================================================

if __name__ == "__main__":
    log.info("Inicializando Bot Mu Domix...")

    monitor_thread = threading.Thread(
        target=loop_monitoramento,
        name="mu-monitor",
        daemon=True,
    )
    monitor_thread.start()

    log.info("Thread de monitoramento iniciada.")
    log.info("Iniciando servidor Flask...")

    porta = int(os.environ.get("PORT", "10000"))

    app.run(
        host="0.0.0.0",
        port=porta,
        debug=False,
        use_reloader=False,
    )
