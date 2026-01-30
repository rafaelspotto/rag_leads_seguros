Implementacao em Python

Stack escolhida
- Python
- LangChain para orquestracao
- sentence-transformers para embeddings
- FAISS para base vetorial local (via LangChain)
- python-docx para leitura de .docx
- textract para extrair texto de .doc baixados do Drive
- beautifulsoup4 para tratar arquivos .doc que sao HTML
- Gemini como LLM

Como executar
0) Instale as dependencias:
   - pip install -r requirements.txt

1) Configure a LLM e a URL do Drive:
   - Edite config.properties e informe GEMINI_API_KEY e DRIVE_URL
   - Opcional: ajuste GEMINI_MODEL e TEMPERATURA (ex.: models/gemini-2.5-flash)

2) Baixar documentos:
   python src/pipeline.py baixar --output data/raw

3) Indexar:
   python src/pipeline.py indexar --input data/raw

4) Inicie o servidor de chat:
   python src/web.py

5) Acesse:
   http://127.0.0.1:5000

Observacao:
- Se os arquivos no Drive forem documentos do Google, a API exporta texto puro automaticamente.
- Se forem .doc/.docx, o sistema baixa o arquivo e tenta extrair o texto localmente.
