from __future__ import annotations

import argparse
import io
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import List

import time
from tqdm import tqdm

from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

from configuracao import carregar_propriedades
from drive_api import baixar_arquivo, extrair_id_pasta, listar_arquivos_pasta
from texto_utils import limpar_texto, separar_secoes, fatiar_secoes
from observabilidade import registrar_evento


def extrair_texto_docx(caminho: Path) -> str:
    from docx import Document

    doc = Document(str(caminho))
    return "\n".join(p.text for p in doc.paragraphs)


def extrair_texto_docx_bytes(conteudo: bytes) -> str:
    from docx import Document

    doc = Document(io.BytesIO(conteudo))
    return "\n".join(p.text for p in doc.paragraphs)


def extrair_texto_word(caminho: Path) -> str | None:
    if os.name != "nt":
        return None

    try:
        import win32com.client  # type: ignore
    except Exception:
        return None

    word = None
    documento = None
    try:
        word = win32com.client.Dispatch("Word.Application")
        word.Visible = False
        documento = word.Documents.Open(str(caminho))
        texto = documento.Content.Text
        return texto
    except Exception:
        return None
    finally:
        if documento is not None:
            documento.Close(False)
        if word is not None:
            word.Quit()


def extrair_texto(caminho: Path) -> str:
    sufixo = caminho.suffix.lower()
    if sufixo == ".docx":
        return extrair_texto_docx(caminho)

    if sufixo == ".doc":
        texto_word = extrair_texto_word(caminho)
        if texto_word:
            return texto_word
        caminho_antiword = shutil.which("antiword")
        if caminho_antiword is None:
            caminhos_possiveis = [
                r"C:\msys64\mingw64\bin\antiword.exe",
                r"C:\msys64\ucrt64\bin\antiword.exe",
                r"C:\msys64\usr\bin\antiword.exe",
            ]
            for candidato in caminhos_possiveis:
                if Path(candidato).exists():
                    caminho_antiword = candidato
                    break
        if caminho_antiword is None:
            raise RuntimeError(
                "Microsoft Word nao encontrado para leitura via pywin32 e "
                "antiword nao esta instalado. Instale o Word, instale "
                "antiword ou converta os .doc para .docx."
            )
        try:
            resultado = subprocess.run(
                [caminho_antiword, str(caminho)],
                check=True,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError as exc:  # pragma: no cover - external tool error
            raise RuntimeError(
                "antiword nao encontrado. Instale o antiword "
                "ou converta os .doc para .docx manualmente."
            ) from exc
        except subprocess.CalledProcessError as exc:  # pragma: no cover
            raise RuntimeError("Falha ao ler .doc com antiword.") from exc
        return resultado.stdout

    raise RuntimeError("Formato nao suportado. Use .docx ou .doc.")


def extrair_texto_doc_bytes(conteudo: bytes) -> str:
    with tempfile.NamedTemporaryFile(suffix=".doc", delete=False) as tmp:
        tmp.write(conteudo)
        tmp_path = Path(tmp.name)
    try:
        return extrair_texto(tmp_path)
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass


def iterar_documentos(pasta_entrada: Path) -> List[Path]:
    return sorted(
        [p for p in pasta_entrada.rglob("*") if p.suffix.lower() in {".doc", ".docx"}]
    )


def criar_indice(
    pasta_indice: Path,
    modelo: str,
    max_caracteres: int,
    sobreposicao: int,
    drive_url: str = "",
    api_key: str = "",
) -> None:
    pasta_indice.mkdir(parents=True, exist_ok=True)

    modelo_embeddings = HuggingFaceEmbeddings(model_name=modelo)
    todos_chunks = []
    falhas = []
    inicio = time.time()
    registrar_evento(
        "index_inicio",
        pasta_entrada="drive",
        pasta_indice=str(pasta_indice),
        modelo=modelo,
        max_caracteres=max_caracteres,
        sobreposicao=sobreposicao,
    )

    propriedades = carregar_propriedades()
    if not drive_url:
        drive_url = propriedades.get("DRIVE_URL", "").strip()
    if not api_key:
        api_key = propriedades.get("GOOGLE_API_KEY", "").strip()
    if not drive_url:
        raise RuntimeError("DRIVE_URL nao configurada em config.properties.")
    pasta_id = extrair_id_pasta(drive_url)
    arquivos = listar_arquivos_pasta(pasta_id, api_key or None)
    for arquivo in tqdm(arquivos, desc="Lendo documentos do Drive"):
        nome = arquivo.get("name", "")
        arquivo_id = arquivo.get("id", "")
        if not nome or not arquivo_id:
            continue
        extensao = Path(nome).suffix.lower()
        if extensao not in {".doc", ".docx"}:
            continue
        try:
            conteudo = baixar_arquivo(arquivo_id, api_key or None)
            if extensao == ".docx":
                texto = extrair_texto_docx_bytes(conteudo)
            else:
                texto = extrair_texto_doc_bytes(conteudo)
            texto = limpar_texto(texto)
        except Exception as exc:
            falhas.append({"arquivo": nome, "erro": str(exc)})
            continue
        secoes = separar_secoes(texto)
        chunks = fatiar_secoes(
            secoes, max_caracteres=max_caracteres, sobreposicao=sobreposicao
        )
        for i, chunk in enumerate(chunks):
            todos_chunks.append(
                {
                    "id": f"{Path(nome).stem}-{i}",
                    "file_name": nome,
                    "title": chunk["title"],
                    "text": chunk["text"],
                }
            )

    if not todos_chunks:
        registrar_evento("index_vazio", pasta_entrada="drive")
        if falhas:
            registrar_evento(
                "index_falhas",
                pasta_entrada="drive",
                falhas=falhas,
            )
        raise RuntimeError("Nenhum documento indexado. Verifique erros de leitura.")

    textos = [c["text"] for c in todos_chunks]
    metadados = [
        {"arquivo": c["file_name"], "titulo": c["title"], "id": c["id"]}
        for c in todos_chunks
    ]

    indice = FAISS.from_texts(textos, modelo_embeddings, metadados=metadados)
    indice.save_local(str(pasta_indice))

    with open(pasta_indice / "config.json", "w", encoding="utf-8") as f:
        json.dump(
            {
                "modelo": modelo,
                "max_caracteres": max_caracteres,
                "sobreposicao": sobreposicao,
                "total_trechos": len(todos_chunks),
            },
            f,
            ensure_ascii=True,
            indent=2,
        )

    registrar_evento(
        "index_fim",
        pasta_entrada="drive",
        pasta_indice=str(pasta_indice),
        modelo=modelo,
        total_trechos=len(todos_chunks),
        duracao_seg=round(time.time() - inicio, 3),
    )
    if falhas:
        registrar_evento(
            "index_falhas",
            pasta_entrada="drive",
            falhas=falhas,
        )


def ler_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Indexador RAG simples")
    parser.add_argument("--index-dir", default="index", help="Pasta do indice")
    parser.add_argument(
        "--model",
        default="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        help="Modelo de embeddings",
    )
    parser.add_argument("--max-caracteres", type=int, default=1200)
    parser.add_argument("--sobreposicao", type=int, default=200)
    parser.add_argument("--drive-url", default="")
    parser.add_argument("--google-api-key", default="")
    return parser.parse_args()


def main() -> None:
    args = ler_args()
    criar_indice(
        Path(args.index_dir),
        args.model,
        args.max_caracteres,
        args.sobreposicao,
        args.drive_url,
        args.google_api_key,
    )


if __name__ == "__main__":
    main()
