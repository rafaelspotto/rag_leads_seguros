from __future__ import annotations

import argparse
from pathlib import Path

from baixar import baixar_pasta_drive
from consultar import buscar, formatar_fontes, gerar_resposta
from configuracao import carregar_propriedades
from indexar import criar_indice


def ler_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Pipeline RAG simples (baixar, indexar, consultar)"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    baixar_parser = subparsers.add_parser("baixar", help="Baixar documentos")
    baixar_parser.add_argument("--folder-url", default="", help="URL da pasta do Drive")
    baixar_parser.add_argument("--output", default="data/raw", help="Pasta de destino")

    indexar_parser = subparsers.add_parser("indexar", help="Indexar documentos")
    indexar_parser.add_argument("--index-dir", default="index", help="Pasta do indice")
    indexar_parser.add_argument("--input", default="data/raw", help="Pasta com .doc/.docx")
    indexar_parser.add_argument(
        "--model",
        default="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        help="Modelo de embeddings",
    )
    indexar_parser.add_argument("--max-caracteres", type=int, default=1200)
    indexar_parser.add_argument("--sobreposicao", type=int, default=200)
    indexar_parser.add_argument("--drive-url", default="")

    consultar_parser = subparsers.add_parser("consultar", help="Consultar indice")
    consultar_parser.add_argument("--index-dir", default="index", help="Pasta do indice")
    consultar_parser.add_argument(
        "--model",
        default="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        help="Modelo de embeddings",
    )
    consultar_parser.add_argument("--consulta", required=True)
    consultar_parser.add_argument("--limite", type=int, default=5)
    consultar_parser.add_argument("--modelo-llm", default="")

    return parser.parse_args()


def main() -> None:
    args = ler_args()

    if args.command == "baixar":
        propriedades = carregar_propriedades()
        url_pasta = args.folder_url.strip() or propriedades.get("DRIVE_URL", "").strip()
        if not url_pasta:
            raise RuntimeError("DRIVE_URL nao configurada em config.properties.")
        baixar_pasta_drive(url_pasta, Path(args.output))
        return

    if args.command == "indexar":
        criar_indice(
            Path(args.input),
            Path(args.index_dir),
            args.model,
            args.max_caracteres,
            args.sobreposicao,
        )
        return

    if args.command == "consultar":
        resultados = buscar(args.consulta, Path(args.index_dir), args.model, args.limite)
        resposta = gerar_resposta(args.consulta, resultados, args.modelo_llm)
        print(resposta)
        print("\nFontes:\n" + formatar_fontes(resultados))
        return


if __name__ == "__main__":
    main()
