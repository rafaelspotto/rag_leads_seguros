from __future__ import annotations

import re
from typing import Dict, List, Optional

import requests


def extrair_id_pasta(url: str) -> str:
    padrao = r"/folders/([a-zA-Z0-9_-]+)"
    match = re.search(padrao, url)
    if not match:
        raise RuntimeError("URL de pasta do Drive invalida.")
    return match.group(1)


def listar_arquivos_pasta(pasta_id: str) -> List[Dict[str, str]]:
    base = "https://www.googleapis.com/drive/v3/files"
    params = {
        "q": f"'{pasta_id}' in parents and trashed=false",
        "fields": "nextPageToken, files(id, name, mimeType)",
        "pageSize": 1000,
    }
    arquivos: List[Dict[str, str]] = []
    pagina = None
    while True:
        if pagina:
            params["pageToken"] = pagina
        resposta = requests.get(base, params=params, timeout=60)
        if resposta.status_code == 403:
            raise RuntimeError("Acesso negado ao Drive para listagem publica.")
        resposta.raise_for_status()
        dados = resposta.json()
        arquivos.extend(dados.get("files", []))
        pagina = dados.get("nextPageToken")
        if not pagina:
            break
    return arquivos


def baixar_arquivo(arquivo_id: str) -> bytes:
    url = f"https://www.googleapis.com/drive/v3/files/{arquivo_id}"
    params = {"alt": "media"}
    resposta = requests.get(url, params=params, timeout=120)
    if resposta.status_code == 403:
        return baixar_arquivo_publico(arquivo_id)
    resposta.raise_for_status()
    conteudo = resposta.content
    content_type = resposta.headers.get("content-type", "")
    prefixo = conteudo[:200].lstrip().lower()
    if "text/html" in content_type or prefixo.startswith(b"<!doctype html") or prefixo.startswith(b"<html"):
        return baixar_arquivo_publico(arquivo_id)
    return conteudo


def baixar_arquivo_publico(arquivo_id: str) -> bytes:
    url = "https://drive.google.com/uc"
    params = {"export": "download", "id": arquivo_id}
    resposta = requests.get(url, params=params, timeout=120)
    if resposta.status_code != 200:
        resposta.raise_for_status()

    if "text/html" in resposta.headers.get("content-type", ""):
        token = None
        for chave, valor in resposta.cookies.items():
            if chave.startswith("download_warning"):
                token = valor
                break
        if not token:
            try:
                html = resposta.text
                match = re.search(r"confirm=([0-9A-Za-z_]+)", html)
                if match:
                    token = match.group(1)
            except Exception:
                token = None
        if token:
            params["confirm"] = token
            resposta = requests.get(url, params=params, timeout=120)
            resposta.raise_for_status()
    if "text/html" in resposta.headers.get("content-type", ""):
        raise RuntimeError(
            "Resposta HTML recebida no download publico do Drive. "
            "Verifique se o arquivo e publico ou use GOOGLE_API_KEY/OAuth."
        )
    return resposta.content


def exportar_texto_plano(arquivo_id: str) -> str:
    url = f"https://www.googleapis.com/drive/v3/files/{arquivo_id}/export"
    params = {"mimeType": "text/plain"}
    resposta = requests.get(url, params=params, timeout=120)
    if resposta.status_code == 403:
        raise RuntimeError("Acesso negado ao export publico do Drive.")
    resposta.raise_for_status()
    return resposta.text
