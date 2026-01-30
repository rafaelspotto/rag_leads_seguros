from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from flask import Flask, jsonify, render_template_string, request

from consultar import buscar, gerar_resposta, montar_fontes

app = Flask(__name__)


HTML = """
<!doctype html>
<html lang="pt-br">
  <head>
    <meta charset="utf-8">
    <title>Chat RAG</title>
    <style>
      body { font-family: Arial, sans-serif; margin: 24px; }
      #chat { border: 1px solid #ddd; padding: 12px; height: 420px; overflow-y: auto; }
      .msg { margin: 8px 0; }
      .user { font-weight: bold; }
      .bot { color: #0b5394; }
      #form { margin-top: 12px; display: flex; gap: 8px; }
      #pergunta { flex: 1; padding: 8px; }
      #enviar { padding: 8px 16px; }
      .fonte { font-size: 12px; color: #555; margin-left: 12px; }
    </style>
  </head>
  <body>
    <h2>Chat RAG</h2>
    <div id="chat"></div>
    <form id="form">
      <input id="pergunta" placeholder="Digite sua pergunta..." autocomplete="off" />
      <button id="enviar" type="submit">Enviar</button>
    </form>
    <script>
      const chat = document.getElementById("chat");
      const form = document.getElementById("form");
      const input = document.getElementById("pergunta");

      function addMsg(text, cls) {
        const div = document.createElement("div");
        div.className = "msg " + cls;
        div.textContent = text;
        chat.appendChild(div);
        chat.scrollTop = chat.scrollHeight;
      }

      function addFonte(fonte) {
        const div = document.createElement("div");
        div.className = "fonte";
        div.textContent = `[${fonte.arquivo}] ${fonte.titulo} - ${fonte.trecho}`;
        chat.appendChild(div);
        chat.scrollTop = chat.scrollHeight;
      }

      form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const texto = input.value.trim();
        if (!texto) return;
        addMsg("Voce: " + texto, "user");
        input.value = "";
        const resp = await fetch("/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ mensagem: texto })
        });
        const data = await resp.json();
        if (data.erro) {
          addMsg("Erro: " + data.erro, "bot");
          return;
        }
        addMsg("Resposta: " + data.resposta, "bot");
        (data.fontes || []).forEach(addFonte);
      });
    </script>
  </body>
</html>
"""


def limpar_saida(texto: str) -> str:
    return texto.replace("\uFFFD", "").replace("�", "")


@app.get("/")
def home() -> str:
    return render_template_string(HTML)


@app.post("/chat")
def chat() -> Any:
    payload: Dict[str, Any] = request.get_json(force=True) or {}
    mensagem = str(payload.get("mensagem", "")).strip()
    if not mensagem:
        return jsonify({"erro": "Mensagem vazia."}), 400

    try:
        documentos = buscar(
            mensagem,
            Path("index"),
            "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
            5,
        )
        resposta = gerar_resposta(mensagem, documentos, None)
        fontes = montar_fontes(documentos)
        return jsonify(
            {
                "resposta": limpar_saida(resposta),
                "fontes": fontes,
            }
        )
    except Exception as exc:
        return jsonify({"erro": str(exc)}), 500


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
