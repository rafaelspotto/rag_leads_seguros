Parte 1 - Arquitetura da Solucao

Visao geral

Objetivo: criar uma pipeline RAG que leia documentos .doc do Google Drive, extraia trechos relevantes sobre obrigacoes ligadas a seguros, indexe em base vetorial e responda com citacoes.

Componentes principais

1. Ingestao de arquivos
- Conector para Google Drive (API ou download manual em lote)
- Controle de versoes e data da coleta

2. Parsing de .doc
- Conversao para texto (ex.: antiword ou python-docx para .doc)
- Normalizacao de encoding e limpeza de cabecalhos/rodapes

3. Pre-processamento e chunking
- Segmentacao por clausulas e titulos quando possivel
- Fallback para chunking por tamanho (ex.: 800 a 1200 caracteres) com sobreposicao
- Metadados por chunk: sindicato, categoria, data, arquivo, pagina/posicao

4. Embeddings e indexacao vetorial
- Geracao de embeddings por chunk
- Base vetorial (ex.: FAISS local para PoC; Qdrant/Weaviate para producao)
- Persistencia de metadados para filtros

5. Camada de consulta e geracao
- Retriever com filtros (segmento, categoria, sindicato)
- Reranking opcional para melhor precisao
- Geracao de resposta com citacoes (trechos e fonte)

6. Observabilidade e monitoramento
- Logs de consultas, tempo de resposta e fontes usadas
- Contagem de falhas de parsing e documentos invalidados
- Amostragem para revisao humana

Decisoes tecnicas

Modelo de embedding
- Para portugues e texto juridico: modelos do tipo text-embedding-3-large ou bge-m3
- Na PoC, priorizar custo baixo e boa cobertura de portugues

Estrategia de chunking
- Preferir clausulas e secoes, pois refletem obrigacoes legais
- Se nao houver marcacao clara, usar tamanho fixo com sobreposicao
- Guardar o titulo da secao como contexto do chunk

Tratamento de documentos longos e repetitivos
- Remover cabecalhos e rodapes repetidos
- Deduplicar trechos muito semelhantes (hash de n-gram)
- Limitar numero de chunks por documento para evitar ruido

Rastreabilidade e citacoes
- Cada chunk recebe id unico e referencia do arquivo
- Resposta final inclui trechos e metadados do documento
- Armazenar caminho e data do arquivo para auditoria

Arquitetura sugerida (diagrama em Markdown)

[Google Drive] -> [Ingestao] -> [.doc Parser] -> [Pre-processamento e Chunking]
   -> [Embeddings] -> [Base Vetorial] -> [Retriever + Reranker]
   -> [LLM Gerador] -> [Resposta com citacoes]

Observabilidade acompanha todas as etapas com logs e metricas.
