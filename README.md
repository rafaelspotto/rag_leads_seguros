Implementacao em Python

Stack escolhida
- Python
- LangChain para orquestracao
- sentence-transformers para embeddings
- FAISS para base vetorial local (via LangChain)
- python-docx para leitura de .docx
- pywin32 (opcional) para extrair texto de .doc via Microsoft Word instalado
- antiword (opcional) como fallback para leitura de .doc
- OpenAI como LLM

Como executar
0) Instale as dependencias:
   - pip install -r requirements.txt

1) Configure a LLM e a URL do Drive:
   - Edite config.properties e informe OPENAI_API_KEY e DRIVE_URL
   - Se a API exigir, informe GOOGLE_API_KEY
   - Opcional: ajuste OPENAI_MODEL e TEMPERATURA

2) Indexar direto do Drive:
   python src/pipeline.py indexar

3) Consulte:
   python src/pipeline.py consultar --consulta "Empresas do setor varejista precisam oferecer plano de saude?"

Opcional: definir modelo por parametro
  python src/pipeline.py consultar --consulta "..." --modelo-llm gpt-4o-mini
