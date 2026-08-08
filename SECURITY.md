# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| latest  | sim       |

## Reporting a Vulnerability

Não abra issue pública para vulnerabilidades. Envie email descrevendo o problema, passos para reproduzir e impacto estimado. Resposta em até 72 horas.

## Security Measures

### API Keys
- Nunca hardcodadas no código. Sempre via `.env` (gitignored) com `python-dotenv`.
- Validação de presença de env vars no startup (fail fast).
- Nunca logar API keys, secrets, ou saldo completo.

### Trading Real
- Kill switch obrigatório em todo bot de trading real.
- Paper trading mínimo 30 dias antes de real.
- Capital inicial máximo $100 (configurável, mas começar baixo).
- `LiveBroker` começa com `enabled=False, dry_run=True`. Nunca envia ordens sem `enabled=True`.
- Nunca assumir fill de ordem: sempre confirmar via WebSocket.

### Backtest
- Nunca usar dados futuros (look-ahead bias).
- Separação in-sample/out-of-sample obrigatória.
- Reportar métricas OOS, não IS.
- Se Sharpe IS > 3.0, suspeitar de overfit e investigar.

### Dados
- Nunca simular ou fabricar dados de preço.
- Validar integridade dos dados baixados (checksum, contagem de linhas, gaps).
- Dados de teste: gerar com seed fixo e marcar como sintéticos.

### Dependencies
- Todas as dependências pinadas em `requirements.txt`.
- Rodar `pip-audit` ou `safety check` regularmente.
