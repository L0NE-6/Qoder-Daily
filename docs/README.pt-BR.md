# 🧭 Qoder Daily

**Recompensas diárias para contas Qoder China e Global, com autorização de dispositivo, UMID específico por região, várias contas e rotação de token recuperável.**

[简体中文](../README.md) | [English](README.en.md) | [繁體中文](README.zh-Hant.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Português (BR)](README.pt-BR.md)

> A documentação chinesa completa está em [../README.md](../README.md).

## Visão geral

O Qoder Daily lê as campanhas de benefícios atuais e coleta os Credits diários disponíveis para contas Qoder China e Global. As duas regiões exigem a identidade oficial do dispositivo correspondente. O script resolve a identidade por variáveis de ambiente, componente runtime-info, cliente ou CLI local, ou pacote oficial verificado. Sem a identidade, ele informa um estado neutro em vez de declarar o check-in concluído.

O `qoder_login.py` usa o fluxo oficial de autorização de dispositivo. Depois de confirmar uma vez no navegador, ele gera um access token e, quando emitido, um refresh token. O caminho normal de login não exige SMS nem captura manual de tráfego.

## Recursos principais

- Coleta apenas campanhas classificadas como Credits diários; benefícios limitados a modelos, Sonus e SOTA são excluídos.
- Separa a identidade Qoder CN / `qoderclicn` da identidade Qoder / `qodercli`.
- Tenta novamente entre 10:00 e 11:00 no horário de Pequim.
- Rotaciona refresh tokens e restaura o estado entre execuções.
- Diferencia quota esgotada, limite diário de cobrança e sessão inválida.
- Processa Pro somente quando a campanha realmente aparece e o valor pode ser verificado.
- Envia notificações opcionais por PushPlus, Bark, WeCom, DingTalk ou Qinglong.

## Obter um token

```bash
python qoder_login.py
python qoder_login.py --region global
```

O comando padrão atende o Qoder China. Use `--region global` para o serviço internacional. A ferramenta abre a página oficial, aguarda a confirmação, valida o token na lista de campanhas e imprime:

```text
access_token|refresh_token
```

Use `QODER_TOKENS` para a conta China e `QODER_GLOBAL_TOKENS` para a conta Global.

## Configuração mínima no Qinglong

1. Execute `pip3 install requests`.
2. Envie `qoder_daily.py`.
3. Configure `QODER_TOKENS` e/ou `QODER_GLOBAL_TOKENS`.
4. Crie uma tarefa agendada:

```bash
task qoder_daily.py
```

Cron sugerido:

```cron
5 10 * * *
```

A campanha abre às 10:00 no horário de Pequim. Se a linha da campanha ainda não apareceu, o script continua tentando durante a janela de uma hora.

## Configuração mínima no GitHub Actions

Adicione estes Secrets em **Settings → Secrets and variables → Actions**:

| Secret | Obrigatório | Finalidade |
| :--- | :---: | :--- |
| `QODER_TOKENS` | para China | Credenciais da conta China |
| `QODER_GLOBAL_TOKENS` | para Global | Credenciais da conta Global |
| `QODER_CACHE_KEY` | recomendado | Chave longa e aleatória para criptografar o cache de tokens |
| `QODER_MACHINE_TOKEN` / `QODER_MACHINE_CODE` / `QODER_MACHINE_TYPE` | condicional | Trio de identidade quando não há runtime-info |
| `QODERCN_RUNTIME_INFO` / `QODER_RUNTIME_INFO` / `QODER_UMID_PATH` | opcional | Substituições de caminho de componente |
| Secrets de notificação | opcional | `PUSHPLUS_TOKEN`, `BARK_URL`, `WECOM_WEBHOOK`, `DINGTALK_WEBHOOK`, `DINGTALK_SECRET` |

O workflow incluído é manual por padrão. Execute **Actions → Qoder Daily → Run workflow** primeiro. Para ativar a agenda, remova o comentário:

```yaml
schedule:
  - cron: "5 2 * * *"
```

O cron usa UTC e corresponde a 10:05 no horário de Pequim. GitHub pode manter scheduled workflows de um fork desativados até que sejam habilitados em Actions. O schedule só roda no branch padrão.

## Estado do token no Actions

O workflow arquiva `qoder_tokens.json` e `qoder_machine_id`, criptografa o pacote com `QODER_CACHE_KEY` e salva em `actions/cache`. Sem a chave de cache, a execução continua, mas o refresh token rotacionado pode ser perdido. Entradas de cache podem ser removidas; se o estado e o refresh token antigo não forem mais válidos, será necessário autorizar novamente.

## Variáveis de ambiente principais

| Variável | Formato ou padrão | Descrição |
| :--- | :--- | :--- |
| `QODER_TOKENS` | `access` / `access\|refresh` / `observação\|access\|refresh` | Contas China |
| `QODER_GLOBAL_TOKENS` | mesmo formato, com `\|uid` opcional | Contas Global. O UID pode ser omitido; o script lê o valor da lista de campanhas. |
| `QODER_MACHINE_TOKEN` / `QODER_MACHINE_CODE` / `QODER_MACHINE_TYPE` | três valores | Identidade manual do dispositivo |
| `QODERCN_RUNTIME_INFO` | caminho | Componente runtime-info China |
| `QODER_RUNTIME_INFO` | caminho | Componente runtime-info Global |
| `QODER_UMID_PATH` | caminho | Substituição de componente geral |
| `QODER_UMID_NO_INSTALL` | `1` | Desativa extração automática do pacote oficial |
| `QODER_WINDOW_RETRY` | padrão `1` | Ativa novas tentativas na janela |
| `QODER_WINDOW_RETRY_MAX` | padrão do script `6` | Máximo de tentativas, limitado internamente a 6 |
| `QODER_WINDOW_RETRY_GAP` | padrão do script `600` | Segundos entre tentativas |
| `QODER_CACHE_KEY` | string aleatória | Exclusivo para criptografia do cache no Actions |

O workflow atual substitui o máximo e o intervalo por `16` e `90` segundos, mas o script limita o número de tentativas a seis; portanto, o máximo efetivo continua sendo seis.

## Opções de linha de comando

| Opção | Efeito |
| :--- | :--- |
| nenhuma | Executa todas as contas China e Global |
| `--only N` | Executa somente a N-ésima conta da lista combinada |
| `--no-notify` | Desativa notificações |
| `--refresh-only` | Apenas renova tokens e salva o estado, sem coletar |

## Semântica de sucesso

A conta só é reportada como concluída quando a campanha aparece e o claim é bem-sucedido. Identidade ausente, janela fechada ou lista vazia permanecem como estado neutro para nova tentativa. O código `112` ou `pricingUrl` aplica cerca de 30 minutos de resfriamento por quota; `110` aplica o limite diário de cobrança e resfria até a meia-noite local, limitado a seis horas. Somente 401/403 sem relação com quota ou os códigos `105` / `10019901001` entram no caminho de renovação.

## Privacidade

Tokens e identificadores de dispositivo vêm de variáveis de ambiente ou Secrets. `qoder_tokens.json`, `qoder_machine_id`, o cache descriptografado e cabeçalhos de autorização são sensíveis. Não faça commit de arquivos de token, não envie artifacts sem criptografia, não cole um token completo em uma Issue e não exponha a chave de cache em logs públicos.

## Limites de uso e redistribuição

O repositório oficial, os scripts, as instruções de implantação e as Releases permanecem gratuitos e públicos. Sem autorização escrita explícita do autor, não empacote este projeto como recurso pago, serviço de implantação paga ou serviço de atualização paga; não remova a atribuição para alegar autoria original; não se passe pelo autor; e não use a identidade, o nome, o avatar ou os QR codes de pagamento do autor para sugerir endosso oficial. Também não republique o projeto em contas, grupos, canais ou plataformas pagas sem relação com ele para ganhar seguidores, desviar tráfego ou revender. Em caso de violação, o autor pode solicitar a remoção e pode pausar atualizações, arquivar ou excluir o repositório. Consulte as regras completas em [NOTICE.md](../NOTICE.md).

## Links

- [Releases](https://github.com/L0NE-6/Qoder-Daily/releases)
- [Issues](https://github.com/L0NE-6/Qoder-Daily/issues)
- [README em chinês](../README.md)
- [Histórico de alterações](../CHANGELOG.md)

## Aviso

Este projeto é destinado a aprendizado pessoal e automação. Respeite os termos do Qoder e serviços relacionados. O uso é por sua conta e risco.
