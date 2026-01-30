from __future__ import annotations

import argparse
from pathlib import Path

from configuracao import carregar_propriedades
from drive_api import baixar_arquivo, extrair_id_pasta, listar_arquivos_pasta
from observabilidade import registrar_evento


def baixar_pasta_drive(url_pasta: str, pasta_saida: Path) -> None:
    pasta_saida.mkdir(parents=True, exist_ok=True)
    pasta_id = extrair_id_pasta(url_pasta)
    arquivos = listar_arquivos_pasta(pasta_id)

    registrar_evento(
        "download_inicio",
        url_pasta=url_pasta,
        pasta_saida=str(pasta_saida),
        total=len(arquivos),
    )

    for item in arquivos:
        nome = item.get("name", "")
        arquivo_id = item.get("id", "")
        if not nome or not arquivo_id:
            continue
        extensao = Path(nome).suffix.lower()
        if extensao not in {".doc", ".docx"}:
            continue
        destino = pasta_saida / nome
        conteudo = baixar_arquivo(arquivo_id)
        destino.write_bytes(conteudo)

    registrar_evento(
        "download_fim",
        url_pasta=url_pasta,
        pasta_saida=str(pasta_saida),
    )


def ler_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Baixar documentos do Drive")
    parser.add_argument("--folder-url", default="", help="URL da pasta do Drive")
    parser.add_argument("--output", default="data/raw", help="Pasta de destino")
    return parser.parse_args()


def main() -> None:
    args = ler_args()
    propriedades = carregar_propriedades()
    url_pasta = args.folder_url.strip() or propriedades.get("DRIVE_URL", "").strip()
    if not url_pasta:
        raise RuntimeError("DRIVE_URL nao configurada em config.properties.")
    baixar_pasta_drive(url_pasta, Path(args.output))


if __name__ == "__main__":
    main()
