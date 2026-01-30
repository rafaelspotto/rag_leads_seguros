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


def listar_arquivos_pasta(
    pasta_id: str, api_key: Optional[str] = None
) -> List[Dict[str, str]]:
    base = "https://www.googleapis.com/drive/v3/files"
    params = {
        "q": f"'{pasta_id}' in parents and trashed=false",
        "fields": "nextPageToken, files(id, name, mimeType)",
        "pageSize": 1000,
    }
    if api_key:
        params["key"] = api_key

    arquivos: List[Dict[str, str]] = []
    pagina = None
    while True:
        if pagina:
            params["pageToken"] = pagina
        resposta = requests.get(base, params=params, timeout=60)
        if resposta.status_code == 403:
            raise RuntimeError(
                "Acesso negado ao Drive. Se necessario, defina GOOGLE_API_KEY."
            )
        resposta.raise_for_status()
        dados = resposta.json()
        arquivos.extend(dados.get("files", []))
        pagina = dados.get("nextPageToken")
        if not pagina:
            break
    return arquivos


def baixar_arquivo(
    arquivo_id: str, api_key: Optional[str] = None
) -> bytes:
    url = f"https://www.googleapis.com/drive/v3/files/{arquivo_id}"
    params = {"alt": "media"}
    if api_key:
        params["key"] = api_key
    resposta = requests.get(url, params=params, timeout=120)
    if resposta.status_code == 403:
        raise RuntimeError(
            "Acesso negado ao arquivo do Drive. Se necessario, defina GOOGLE_API_KEY."
        )
    resposta.raise_for_status()
    return resposta.content
