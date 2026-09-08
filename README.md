# Ofertas de Hardware → Discord

Automação gratuita em GitHub Actions, com Python sem dependências externas.
Fonte inicial: https://t.me/s/peperaiohardware — ofertas nacionais e do AliExpress.
Publica somente um título curto, preço anunciado e link para a publicação original com crédito.
Não verifica descontos nem preço final na loja. Cupons e condições ficam na fonte.

## Configurar para Condizion

1. Crie https://github.com/new com nome `ofertas-discord`, visibilidade **Public**.
   Runners padrão do GitHub Actions são gratuitos em repositórios públicos.
2. Envie os arquivos desta pasta à raiz do repositório, incluindo
   `.github/workflows/ofertas.yml`. Não envie somente o ZIP.
   Se a pasta oculta `.github` não aparecer ao enviar pelo navegador, use
   **Add file → Create new file**, digite `.github/workflows/ofertas.yml`
   e cole o conteúdo do arquivo correspondente.
3. Discord: engrenagem do canal → Integrações → Webhooks → Novo webhook → Copiar URL.
4. Repositório → Settings → Secrets and variables → Actions → New repository secret.
   Nome: `DISCORD_WEBHOOK_URL`. Valor: URL copiada. Não coloque essa URL em arquivo público.
5. Actions → Ofertas de Hardware → Run workflow. Marque `testar_webhook` para enviar
   uma única mensagem de teste ao canal. Depois execute novamente com a opção desmarcada
   para inicializar o histórico. Essa inicialização não envia ofertas antigas.
6. As execuções seguintes procuram novas ofertas a cada 8 minutos. Veja os resultados
   na aba Actions. Para parar: Ofertas de Hardware → menu ⋯ → Disable workflow.

## Personalizar

Edite `config.json`. `keywords` filtra o título do produto; `exclude` exclui termos.
`channels` aceita nomes de canais públicos com prévia web disponível.
Inicialmente inclui GPUs, CPUs, placas-mãe, memória, SSD, fontes, gabinetes,
refrigeração, monitores, periféricos, áudio, notebooks e rede.
Até 8 mensagens por execução, ofertas com até 6 horas e até 3 páginas por fonte.
Anúncios só em imagem ou sem nome do produto no texto podem não passar no filtro.
Quando a publicação contém uma foto pública, ela aparece no card do Discord.
Não há classificação garantida de loja quando o anúncio usa link encurtado.

## Limitações de operação

- GitHub pode atrasar ou descartar execuções agendadas. Não serve como alerta instantâneo.
- O histórico é salvo em `state.json` por commit. Ele contém apenas IDs públicos.
  Não apague esse arquivo; apagá-lo reinicializa o histórico sem publicar o passado.
- Falha entre envio e gravação do histórico pode produzir repetição. Erros HTTP interrompem
  o envio e aparecem como execução com falha; limites HTTP 429 têm espera e nova tentativa.
- Mudanças no HTML ou bloqueios da página pública podem exigir manutenção do leitor.
  Nenhum login de Telegram ou token de usuário é usado.
- Períodos offline longos ou volume alto podem deixar ofertas fora das 3 páginas consultadas.
- Agendamentos de repositórios públicos podem ser desativados após 60 dias sem atividade;
  confira Actions se os alertas pararem.
- Somente teste local de leitura e testes simulados são possíveis antes de configurar o webhook.

## Testar localmente

Dentro da pasta, execute `python -m unittest -v`.
Para testar uma página HTML salva sem enviar mensagens:
`python bot.py --preview caminho/telegram.html`.

## Referências

- https://docs.github.com/en/billing/concepts/product-billing/github-actions
- https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule
- https://docs.discord.com/developers/resources/webhook#execute-webhook
