from __future__ import annotations

import argparse
import time
from pathlib import Path
from typing import List

from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document

from configuracao import carregar_propriedades
from observabilidade import registrar_evento


def buscar(
    consulta: str,
    pasta_indice: Path,
    modelo_embeddings: str,
    limite: int,
) -> List[Document]:
    inicio = time.time()
    registrar_evento(
        "consulta_inicio",
        pasta_indice=str(pasta_indice),
        modelo_embeddings=modelo_embeddings,
        limite=limite,
    )

    embeddings = HuggingFaceEmbeddings(model_name=modelo_embeddings)
    indice = FAISS.load_local(
        str(pasta_indice), embeddings, allow_dangerous_deserialization=True
    )
    recuperador = indice.as_retriever(search_kwargs={"k": limite})
    documentos = recuperador.invoke(consulta)

    registrar_evento(
        "consulta_fim",
        pasta_indice=str(pasta_indice),
        modelo_embeddings=modelo_embeddings,
        limite=limite,
        resultados=len(documentos),
        duracao_seg=round(time.time() - inicio, 3),
    )
    return documentos


def formatar_fontes(documentos: List[Document]) -> str:
    linhas = []
    for i, doc in enumerate(documentos, start=1):
        trecho = doc.page_content[:400].replace("\n", " ").strip()
        arquivo = doc.metadata.get("arquivo", "desconhecido")
        titulo = doc.metadata.get("titulo", "Sem titulo")
        linhas.append(f"[{i}] {arquivo} | {titulo}")
        linhas.append(f"    {trecho}")
    return "\n".join(linhas)


def montar_fontes(documentos: List[Document]) -> List[dict]:
    fontes = []
    for doc in documentos:
        trecho = doc.page_content[:400].replace("\n", " ").strip()
        fontes.append(
            {
                "arquivo": doc.metadata.get("arquivo", "desconhecido"),
                "titulo": doc.metadata.get("titulo", "Sem titulo"),
                "trecho": trecho,
            }
        )
    return fontes


def gerar_resposta(
    consulta: str,
    documentos: List[Document],
    modelo_llm: str | None,
) -> str:
    propriedades = carregar_propriedades()
    api_key = propriedades.get("GEMINI_API_KEY", "").strip()
    modelo = (modelo_llm or propriedades.get("GEMINI_MODEL", "")).strip()
    temperatura = propriedades.get("TEMPERATURA", "0.2").strip()

    if not api_key:
        raise RuntimeError("GEMINI_API_KEY nao encontrado em config.properties.")
    if not modelo:
        raise RuntimeError("GEMINI_MODEL nao definido em config.properties.")

    try:
        temperatura_float = float(temperatura)
    except ValueError:
        temperatura_float = 0.2

    fontes = []
    for i, doc in enumerate(documentos, start=1):
        fontes.append(f"[{i}] {doc.page_content}")

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Voce e um assistente de RAG. Responda em portugues simples.",
            ),
            (
                "user",
                "Responda usando apenas as fontes. Se nao houver evidencia, "
                "diga que nao encontrou.\n\nPergunta: {consulta}\n\nFontes:\n{fontes}",
            ),
        ]
    )

    llm = ChatGoogleGenerativeAI(
        google_api_key=api_key, model=modelo, temperature=temperatura_float
    )
    mensagem = prompt.format_messages(consulta=consulta, fontes="\n\n".join(fontes))
    resposta = llm.invoke(mensagem)
    return resposta.content.strip()


def ler_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Consulta RAG simples")
    parser.add_argument("--index-dir", default="index", help="Pasta do indice")
    parser.add_argument(
        "--model",
        default="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        help="Modelo de embeddings",
    )
    parser.add_argument("--consulta", required=True)
    parser.add_argument("--limite", type=int, default=5)
    parser.add_argument("--modelo-llm", default="")
    return parser.parse_args()


def main() -> None:
    args = ler_args()
    documentos = buscar(args.consulta, Path(args.index_dir), args.model, args.limite)
    resposta = gerar_resposta(args.consulta, documentos, args.modelo_llm)
    print(resposta)
    print("\nFontes:\n" + formatar_fontes(documentos))


if __name__ == "__main__":
    main()
