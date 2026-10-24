import time
import re
import math
import requests
from bs4 import BeautifulSoup
from flask import Flask
from threading import Thread
import os

# --- SERVIDOR WEB PARA O RENDER ---
app = Flask('')

@app.route('/')
def home():
    return "Bot Mu Domix Online!"

# CONFIGURAÇÕES:
NOME_PERSONAGEM = "uCria" 
URL_PERSONAGEM = f"https://mudomix.com/profile/character/{NOME_PERSONAGEM}"
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1563566611129180301/C_utyhcoH4w1O2fIy93mCyXkX7Ph2c2ZlhzZD3DWAzxLwTZJ0DyyzGE7Sgffn--SzL3x"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}

TOLERANCIA_BLOCO = 4

base_mapa = None
base_x = None
base_y = None
primeira_execucao = True
ultimo_status_online = None

def enviar_alerta_discord(mensagem):
    payload = {
        "content": f"🚨 **ALERTA MU DOMIX — [{NOME_PERSONAGEM.upper()}]** 🚨\n{mensagem}"
    }
    try:
        res = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=5)
        print(f"[+] Alerta enviado para o Discord! Status: {res.status_code}")
    except Exception as e:
        print(f"[-] Erro ao enviar webhook: {e}")

def monitorar():
    global base_mapa, base_x, base_y, primeira_execucao, ultimo_status_online
    
    print(f"[*] A aceder ao perfil de {NOME_PERSONAGEM}...")
    try:
        resposta = requests.get(URL_PERSONAGEM, headers=HEADERS, timeout=10)
        
        if resposta.status_code != 200:
            print(f"[-] Erro ao aceder ao site. Status: {resposta.status_code}")
            return

        soup = BeautifulSoup(resposta.text, "html.parser")
        texto_pagina = soup.get_text()
        
        # --- VERIFICAÇÃO DE ONLINE / OFFLINE ---
        status_atual = "Online"
        if "offline" in texto_pagina.lower():
            status_atual = "Offline"
        
        if ultimo_status_online is not None and ultimo_status_online == "Online" and status_atual == "Offline":
            msg = f"⚠️ **PERSONAGEM OFFLINE!**\nO personagem **{NOME_PERSONAGEM}** desconectou ou fechou o jogo!"
            enviar_alerta_discord(msg)
        
        ultimo_status_online = status_atual
        print(f"[+] Status detetado: {status_atual}")

        if status_atual == "Offline":
            return

        # --- BUSCA DE MAPA E COORDENADAS ---
        mapa_atual = None
        coord_x = None
        coord_y = None
        
        match_coords = re.search(r'(\d{1,3})\s*[/,\-]\s*(\d{1,3})', texto_pagina)
        
        if match_coords:
            coord_x = int(match_coords.group(1))
            coord_y = int(match_coords.group(2))

        mapas_conhecidos = ["KantruLand", "Kantruland", "Lorencia", "Devias", "Noria", "Elbeland", "Aida", "Crywolf", "Icarus", "Tarkane", "Kanturu", "Barracks", "Refuge"]
        for m in mapas_conhecidos:
            if m.lower() in texto_pagina.lower():
                mapa_atual = m
                break
        
        if not mapa_atual:
            mapa_atual = "Mapa Desconhecido"

        print(f"[VERIFICAÇÃO] Mapa: {mapa_atual} | Coordenadas: X={coord_x}, Y={coord_y}")

        if coord_x is not None and coord_y is not None:
            if primeira_execucao:
                base_mapa = mapa_atual
                base_x = coord_x
                base_y = coord_y
                primeira_execucao = False
                print(f"[📍] ÂNCORA INICIAL DEFINIDA: {base_mapa} ({base_x}, {base_y})")
                enviar_alerta_discord(f"📍 **ÂNCORA DEFINIDA!**\nMonitorando o personagem **{NOME_PERSONAGEM}** no mapa **{base_mapa}** nas coordenadas **({base_x}, {base_y})**.")
                return

            if mapa_atual != base_mapa:
                msg = f"⚠️ **MUDANÇA DE MAPA!**\nO personagem **{NOME_PERSONAGEM}** foi de `{base_mapa}` para **`{mapa_atual}`** (Coords: {coord_x}, {coord_y})."
                enviar_alerta_discord(msg)
                base_mapa = mapa_atual
                base_x = coord_x
                base_y = coord_y
                return

            distancia = math.sqrt((coord_x - base_x)**2 + (coord_y - base_y)**2)
            print(f" -> Distância atual da base: {round(distancia, 1)} blocos (Limite: {TOLERANCIA_BLOCO})")
            
            if distancia > TOLERANCIA_BLOCO:
                msg = f"⚠️ **MOVIMENTAÇÃO FORA DA ÁREA!**\nO personagem **{NOME_PERSONAGEM}** saiu da base ({base_x}, {base_y}) e foi para **({coord_x}, {coord_y})** em {mapa_atual}."
                enviar_alerta_discord(msg)
                base_x = coord_x
                base_y = coord_y
        else:
            print("[-] Coordenadas não encontradas nesta leitura.")

    except Exception as e:
        print(f"[-] Erro durante a verificação: {e}")

def loop_monitoramento():
    print(f"==========================================")
    print(f" Bot Mu Domix ({NOME_PERSONAGEM}) Iniciado em Loop! ")
    print(f"==========================================")
    
    # Envia o aviso de ligação inicial
    try:
        payload = {
            "content": f"🟢 **BOT LIGADO COM SUCESSO!**\nO monitoramento para o personagem **{NOME_PERSONAGEM}** já está ativo e pronto."
        }
        requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=5)
    except:
        pass
    
    while True:
        monitorar()
        time.sleep(30)

# Dispara a thread de monitoramento garantindo que ela não adormeça
t_monitor = Thread(target=loop_monitoramento)
t_monitor.daemon = True
t_monitor.start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
