from __future__ import annotations

from pathlib import Path
from typing import Dict


def carregar_propriedades(caminho: Path = Path("config.properties")) -> Dict[str, str]:
    if not caminho.exists():
        return {}

    propriedades: Dict[str, str] = {}
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        propriedades[chave.strip()] = valor.strip()
    return propriedades
