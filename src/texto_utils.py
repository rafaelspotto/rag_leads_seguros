from __future__ import annotations

import re
from typing import List, Tuple


def limpar_texto(texto: str) -> str:
    texto = texto.replace("\r\n", "\n").replace("\r", "\n")
    texto = re.sub(r"[ \t]+", " ", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    return texto.strip()


def separar_secoes(texto: str) -> List[Tuple[str, str]]:
    linhas = [linha.strip() for linha in texto.split("\n")]
    secoes: List[Tuple[str, str]] = []
    titulo_atual = "Sem titulo"
    linhas_atuais: List[str] = []

    def flush():
        nonlocal linhas_atuais, titulo_atual
        conteudo = "\n".join([l for l in linhas_atuais if l])
        if conteudo:
            secoes.append((titulo_atual, conteudo))
        linhas_atuais = []

    heading_re = re.compile(
        r"^(clausula|capitulo|secao|titulo)\b", re.IGNORECASE
    )

    for linha in linhas:
        if not linha:
            linhas_atuais.append("")
            continue
        e_titulo = bool(heading_re.match(linha)) or (
            len(linha) <= 80 and linha.isupper()
        )
        if e_titulo:
            flush()
            titulo_atual = linha
        else:
            linhas_atuais.append(linha)

    flush()
    return secoes or [("Sem titulo", texto)]


def fatiar_secoes(
    secoes: List[Tuple[str, str]],
    max_caracteres: int = 1200,
    sobreposicao: int = 200,
) -> List[dict]:
    chunks: List[dict] = []
    buffer = ""
    buffer_titulo = ""

    def flush():
        nonlocal buffer
        if buffer.strip():
            chunks.append(
                {"title": buffer_titulo or "Sem titulo", "text": buffer.strip()}
            )
            if sobreposicao > 0 and len(buffer) > sobreposicao:
                buffer = buffer[-sobreposicao:]
            else:
                buffer = ""

    for titulo, conteudo in secoes:
        paragrafos = [p.strip() for p in re.split(r"\n{2,}", conteudo) if p.strip()]
        for p in paragrafos:
            candidato = (buffer + "\n\n" + p).strip() if buffer else p
            if len(candidato) > max_caracteres:
                flush()
                if len(p) > max_caracteres:
                    for i in range(0, len(p), max_caracteres - sobreposicao):
                        parte = p[i : i + max_caracteres]
                        chunks.append({"title": titulo, "text": parte})
                    buffer = ""
                else:
                    buffer = p
                    buffer_titulo = titulo
            else:
                buffer = candidato
                buffer_titulo = titulo

    flush()
    return chunks
