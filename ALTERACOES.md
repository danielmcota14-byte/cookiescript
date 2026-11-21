# Alterações (Cookie AI)

## Pasta site/  (páginas do front-end)
- chat.html: gerar imagens (botão "Criar imagem"), ler imagens e vídeos (5 quadros), memória no Firestore (login anônimo),
  histórico + estado da conversa enviados ao servidor.
- index.html, ad.html: texto atualizado / sem mudanças.

## Servidor (raiz)
- ai_client.py: histórico no pipeline, visão (qwen/qwen3.8-27b), estado da conversa viajando pelo pipeline ([[ESTADO]]).
- cookie_ide_app.py: leitura de histórico/memória do cliente, rota /api/v1/state, visão para imagens.
- memory_store.py: get_history pega as ÚLTIMAS mensagens; export/import de memórias.
- file_analyzer.py: leitura real de PDF (pypdf).
- firestore.rules: regra nova users/{uid}/memories.
- requirements.txt / Dockerfile: pypdf.

## Variáveis de ambiente úteis
GROQ_API_KEY, GROQ_VISION_MODEL (opcional), GROK_API_KEY, OMNIROUTE_URL/OMNIROUTE_API_KEY

## Ordem dos provedores (pipeline)
- 1ª opção: OmniRoute (resposta final + estado da conversa)
- 2ª opção: Groq, só se o OmniRoute falhar (poupa o limite grátis)
- Visão (imagens): continua Groq/Qwen primeiro, depois Grok e OmniRoute

## Limite de 20 mensagens removido
- chat.html: sem CONTEXT_LIMIT fixo; o medidor usa a janela real calculada pelo servidor (orçamento de tokens, até 30 mensagens).
- index.html: textos atualizados (memória no Firestore, estado resumido, imagens e vídeo).

## Fila de entrada (usuário 181 espera)
- **admission.py (novo):** controla quantos usuários estão ativos. "Ativo" = mandou algo nos últimos 10 min. Cabem 180; os seguintes entram numa fila FIFO. Quem espera precisa manter a aba aberta (se parar de responder por 30 s sai da fila). Vaga reservada não assumida em 45 s passa para o próximo.
- **cookie_ide_app.py:** novas rotas `POST /api/queue/join`, `POST /api/queue/leave` e `GET /api/queue/status`; `/api/chat` devolve 429 com posição e estimativa se o usuário não tem vaga.
- **site/chat.html:** antes de enviar, o chat entra na fila e mostra "Você é o Nº da fila · espera estimada". O tempo limite de 120 s só começa depois que a vez chega. O botão parar tira da fila.
- **Configuração (Render):** os padrões já são 180 vagas e 10 min de inatividade, então nada é obrigatório. Para mudar, crie as variáveis de ambiente `MAX_ACTIVE_USERS` e `ACTIVE_TTL_SECONDS` no painel do Render (`MAX_ACTIVE_USERS=0` desliga a fila). Os valores no fly.toml só valem se você usar o Fly.
- Limitação: a contagem fica na memória. Ao reiniciar o servidor ela zera, e se o Render rodar mais de uma instância cada uma conta separado (no plano grátis é uma só).

## Modo de voz: ditado, transcrição de áudio e conversa por voz
- **site/chat.html (único arquivo alterado; o servidor não muda):**
  - Botão de microfone ao lado do enviar: grava, transcreve e coloca o texto na caixa de mensagem. "Concluir" deixa revisar; "Concluir e enviar" manda direto.
  - Anexar um arquivo de áudio (mp3, wav, m4a, ogg, opus, flac…) transcreve para texto na caixa de mensagem (até 1 hora; o áudio não vai para o servidor).
  - Botão de ondas sonoras: conversa por voz em tela cheia (ouve, detecta o fim da fala, envia pelo mesmo pipeline com memória e estado, lê a resposta em voz alta, volta a ouvir). Dá para interromper falando por cima, silenciar, pular a fala e ajustar idioma, qualidade, pausa e velocidade.
  - Fala → texto: Whisper (transformers.js 4.3.2) em Web Worker, no aparelho da pessoa, com detecção automática de idioma. O modelo baixa uma vez (CDN jsDelivr + Hugging Face) e fica no cache do navegador.
  - Texto → fala: vozes do próprio aparelho (speechSynthesis), no idioma da resposta.
  - Reserva: se o Whisper não carregar, usa o reconhecimento do navegador (Chrome, Edge, Safari).
  - No modo conversa, o chat acrescenta à mensagem uma instrução para a IA responder curto, sem markdown e no idioma da pessoa.
- Custo para o site: zero (tudo roda no navegador de quem usa).
