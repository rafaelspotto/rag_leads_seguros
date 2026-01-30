from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict


def registrar_evento(evento: str, **campos: Any) -> None:
    registro: Dict[str, Any] = {"evento": evento, "ts": time.time()}
    registro.update(campos)

    pasta_logs = Path("logs")
    pasta_logs.mkdir(parents=True, exist_ok=True)
    arquivo_metricas = pasta_logs / "metrics.jsonl"

    with arquivo_metricas.open("a", encoding="utf-8") as f:
        f.write(json.dumps(registro, ensure_ascii=True) + "\n")
