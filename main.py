import time
import re
import math
import requests
from bs4 import BeautifulSoup
from flask import Flask
from threading import Thread

# --- CONFIGURAÇÕES DO SERVIDOR WEB (Para o Render achar que é um site e rodar de graça) ---
app = Flask('')

@app.route('/')
def home():
    return "Bot Mu Domix Rodando com Sucesso!"

def run_web():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_web)
    t.start()
# ------------------------------------------------------------------------------------------

# CONFIGURAÇÕES DO BOT:
URL_PERSONAGEM = "https://mudomix.com/profile/character/uCria"
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1563566611129180301/C_utyhcoH4w1O2fIy93mCyXkX7Ph2c2ZlhzZD3DWAzxLwTZJ0DyyzGE7Sgffn--SzL3x" # <-- Lembre de colocar seu link aqui

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}

TOLERANCIA_BLOCO = 4

base_mapa = None
base_x = None
base_y = None
primeira_execucao = True

def enviar_alerta_discord(mensagem):
    payload = {
        "content": f"🚨 **ALERTA MU DOMIX** 🚨\n{mensagem}"
    }
    try:
        requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=5)
    except Exception as e:
        print(f"Erro ao enviar webhook: {e}")

def monitorar():
    global base_mapa, base_x, base_y, primeira_execucao
    
    try:
        resposta = requests.get(URL_PERSONAGEM, headers=HEADERS, timeout=10)
        
        if resposta.status_code != 200:
            print(f"[-] Erro ao acessar o site. Status: {resposta.status_code}")
            return

        soup = BeautifulSoup(resposta.text, "html.parser")
        texto_pagina = soup.get_text()
        
        mapa_atual = None
        coord_x = None
        coord_y = None
        
        match_coords = re.search(r'(\d{1,3})\s*[/,]\s*(\d{1,3})', texto_pagina)
        
        if match_coords:
            coord_x = int(match_coords.group(1))
            coord_y = int(match_coords.group(2))

        mapas_conhecidos = ["KantruLand", "Lorencia", "Devias", "Noria", "Elbeland", "Aida", "Crywolf", "Icarus", "Tarkane", "Kanturu", "Barracks", "Refuge"]
        for m in mapas_conhecidos:
            if m.lower() in texto_pagina.lower():
                mapa_atual = m
                break
        
        if not mapa_atual:
            mapa_atual = "Mapa Desconhecido"

        if coord_x is not None and coord_y is not None:
            print(f"[+] Status atual -> Mapa: {mapa_atual} | Coordenadas: ({coord_x}, {coord_y})")
            
            if primeira_execucao:
                base_mapa = mapa_atual
                base_x = coord_x
                base_y = coord_y
                primeira_execucao = False
                print(f"[📍] ÂNCORA DEFINIDA! Monitorando a partir de: {base_mapa} em ({base_x}, {base_y}) com tolerância de {TOLERANCIA_BLOCO} blocos.")
                return

            if mapa_atual != base_mapa:
                msg = f"⚠️ **SEU PERSONAGEM SAIU DO MAPA!**\nFoi de `{base_mapa}` para **`{mapa_atual}`** (Coords: {coord_x}, {coord_y}). Provavelmente morreu ou foi movido!"
                print(f"[!] MUDANÇA DE MAPA DETECTADA!")
                enviar_alerta_discord(msg)
                base_mapa = mapa_atual
                base_x = coord_x
                base_y = coord_y
                return

            distancia = math.sqrt((coord_x - base_x)**2 + (coord_y - base_y)**2)
            
            if distancia > TOLERANCIA_BLOCO:
                msg = f"⚠️ **MOVIMENTAÇÃO FORA DA ÁREA!**\nSaiu da base ({base_x}, {base_y}) e foi para **({coord_x}, {coord_y})** em {mapa_atual}. (Distância: {round(distancia, 1)} blocos)."
                print(f"[!] LIMITE DE MARGEM EXCEDIDO!")
                enviar_alerta_discord(msg)
                base_x = coord_x
                base_y = coord_y
        else:
            print("[-] Coordenadas não encontradas nesta leitura.")

    except Exception as e:
        print(f"[-] Erro durante a verificação: {e}")

# Loop principal do monitor (roda em paralelo)
def loop_monitoramento():
    time.sleep(10) # Espera o servidor web subir
    print("==========================================")
    print(" Bot Mu Domix Iniciado (30s) ")
    print("==========================================")
    while True:
        monitorar()
        time.sleep(30)

if __name__ == "__main__":
    # Inicia o monitor em segundo plano
    t_monitor = Thread(target=loop_monitoramento)
    t_monitor.start()
    
    # Inicia o servidor web do Flask
    keep_alive()