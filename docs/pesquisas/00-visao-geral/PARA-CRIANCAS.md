# Para Crianças: O que e o crypto-correl-bot?

**Data:** 2026-07-15
**Publico:** qualquer pessoa, sem conhecimento de programacao ou financas
**Promessa:** depois de ler isso, voce vai saber o que o sistema faz

## A ideia em 1 frase

O crypto-correl-bot e um "programa de computador que olha o mercado de cripto
o tempo todo, entende quem esta comprando e quem esta vendendo, e ajuda a
decidir quando comprar ou vender moedas digitais como Bitcoin.

## Analogia: o mercadao de cripto e como uma praca de comida

Imagine uma praca de comida grande, com varias barracas:
- uma barraca vende Bitcoin (BTC),
- outra vende Ethereum (ETH),
- outra vende Solana (SOL),
- e mais 25 barracas, cada uma com uma moeda diferente.

Cada barraca tem um cartaz com o preco do dia. Os precos sobem e descem o
tempo todo. As pessoas chegam na praca, olham os precos, e decidem comprar
ou vender.

O **crypto-correl-bot** e um robozinho que fica sentado na praca o dia inteiro
anotando tudo:

1. **Quanto cada barraca esta cobrando** (preco).
2. **Quantas pessoas estao na fila** (volume).
3. **Se a fila e de compradores ou vendedores** (order flow).
4. **Se as barracas estao subindo ou descendo juntas** (correlacao).
5. **Se alguem foi expulso da fila porque ficou sem dinheiro** (liquidacao).

Com essas anotacoes, o robo tenta descobrir padroes. Tipo: "sempre que a
barraca do Bitcoin sobe, a do Ethereum tambem sobe 5 minutos depois". Isso
e **correlacao**. Sabendo disso, da para "prever" que o Ethereum vai subir
antes de todo mundo perceber.

## O que o robo ja consegue fazer hoje

### 1. Anotar tudo que acontece na praca (camada de dados)

O robo tem "olhinhos" conectados na Binance (a maior praca de cripto do
mundo). Ele anota:

- Os precos de cada moeda desde 2017 ( tipo uma enciclopedia gigante).
- Os precos em tempo real, atualizando varias vezes por segundo.
- A "fila de oferta": quem quer comprar a quanto, quem quer vender a quanto.
- Taxas que os traders pagam para manter posicoes abertas (funding rate).
- Quando alguem e forçado a vender porque ficou sem dinheiro (liquidacao).

Tudo isso e guardado em "arquivos super-comprimidos" chamados Parquet.
Pense como arquivos ZIP super-organizados. Hoje ele ja tem 45.500
anotacoes de preços em 120 arquivos.

### 2. Entender quem e amigo de quem (grafos de correlacao)

O robo desenha um mapa de amizades entre as moedas:

```
        Bitcoin ----alta amizade---- Ethereum
            |                          |
            |                          |
        Solana ----media amizade---- Cardano
```

- Se duas moedas sobem e descem juntas, sao "amigas" (correlacao alta).
- O robo detecta "grupos de amigos" (comunidades):
  - Grupo 1: BTC, ETH, SOL, BNB, ADA (as grandes)
  - Grupo 2: AVAX, DOGE, DOT, XRP, LINK (as mid / meme)

Sabendo os grupos, o robo pode perceber quando uma moeda sai do padrao.
Tipo: "Cardano caiu mas todas as amigas dela subiram. Cardano provavelmente
vai subir tambem para voltar ao grupo". Isso vira uma dica de compra.

### 3. Entender o sentimento da praca (analise estatistica)

O robo calcula coisas avancadas:

- **Hurst**: sera que a praca esta "tendendo" (todo mundo subindo junto) ou
  "voltando" (precos voltam para a media)? Tipo ver se o vento esta
  empurrando ou puxando os precos.
- **Volatilidade (GARCH)**: o quao nervosa a praca esta hoje? Precos
  pulando muito = praca nervosa = cuidado.
- **Regime (HMM)**: em qual "estacao" estamos? Calma, agitada, ou caotica?
  Se caotica, o robo para de operar.
- **VaR**: "se eu colocar 100 reais, qual a chance de perder X reais em
  um dia ruim?"

### 4. Olhar quem esta agredindo quem (microestrutura)

Na fila da barraca, tem dois tipos de gente:

- **Compradores impacientes**: chegam e gritam "compro AGORA pelo preco que
  estiver!". Eles "batem" na fila dos vendedores. Isso empurra o preco
  para cima.
- **Vendedores impacientes**: gritam "vendo AGORA!". Eles batem na fila
  dos compradores. Isso empurra o preco para baixo.

O robo conta quem esta batendo mais. Se todo mundo so quer comprar, o
preco provavelmente vai subir. Isso se chama **order flow**.

O robo tambem calcula:

- **CVD (Cumulative Volume Delta)**: saldo de quem agrediu o dia inteiro.
  Se CVD positivo, compradores estao ganhando.
- **Kyle's Lambda**: se eu coloco uma ordem grande, quanto o preco se mexe?
  Se mexe muito = praca iliquida = cuidado com ordens grandes.
- **Volume Profile**: em quais precos aconteceram mais negocios? Isso
  vira "suporte" e "resistencia" natural.

### 5. Testar estrategias antes de usar de verdade (backtest)

O robo tem um "simulador do passado". Ele pega todo o historico de 2017
ate 2024 e finge que esta operando. Em vez de arriscar dinheiro real,
ele testa: "se eu tivesse comprado Bitcoin toda vez que X, teria
lucrado ou perdido?"

Isso e **backtest**. O robo faz isso de forma rigorosa:

- **Walk-forward**: treina em 6 meses, testa nos 2 meses seguintes que
  ele nao viu. Repete. Assim ele nao "cola" (overfit).
- **Metricas honestas**: Sharpe (retorno ajustado ao risco), Max Drawdown
  (maior queda), Profit Factor (lucro / perda).

Hoje o robo ja tem **5 estrategias testaveis**:

1. **Mean Reversion por Correlacao**: comprar quem caiu mas o grupo subiu.
2. **Momentum**: comprar quem ja esta subindo com forca.
3. **Statistical Arbitrage**: pares que andam juntos, quando se separam,
   apostar que vao voltar.
4. **Entropy / Regime**: so o "filtro" que decide se e dia de operar ou nao.
5. *(+ 4 estrategias planejadas, ainda nao programadas)*

### 6. Gerar relatorios bonitos (dashboards)

O robo produz:

- Um mapa visual das amizades entre moedas (HTML interativo, da para
  clicar e arrastar as bolinhas).
- Um terminal de trading cheio de numeros coloridos, como os
  profissionais usam em Wall Street (estilo Bloomberg).
- Um relatorio cientifico de 580 linhas com cada moeda analisada em
  40 metricas diferentes.

## O que o robo AINDA NAO faz

### Nao opera sozinho

Ele analisa, mas nao aperta o botao de "comprar". Hoje um humano precisa
olhar o relatorio e decidir. Falta programar a "parte muscular":

- **Bot engine**: o loop que fica rodando 24/7.
- **Risk manager**: para o robo se ele comecar a perder muito.
- **Paper broker**: simulador que "finge" operar para treinar.
- **Live broker**: o que aperta o botao de verdade na Binance.

### Nao manda mensagens no Telegram

Se o robo ver uma oportunidade, nao avisa no celular. Falta programar
o "Telegram bot" que manda mensagens tipo "BTC caiu fora do grupo, possivel
oportunidade de compra".

### Nao tem dados de tudo que queria

Hoje so tem dados de 10 moedas, 6 meses. Para ser confiavel, precisa de
30 moedas, 3 anos. Tambem faltam dados historicos de funding rate,
liquidacoes e order book (so tem em tempo real, nao tem passado).

## O sonho (roadmap)

1. **Fase 4 (em breve)**: robo operando sozinho mas com "dinheiro de
   mentira" (paper trading) por 30 dias. Para ver se a teoria funciona
   na pratica.
2. **Fase 5**: robo operando com dinheiro real, comecando com $50-100.
   So as 4 estrategias mais validadas. Com kill switch: se perder 10%,
   para tudo.
3. **Fase 6 (futuro)**: suportar outras exchanges (Bybit, Hyperliquid),
   IA para ler noticias, dashboard profissional tipo Grafana.

## Mapa mental (visual)

```
                    +-------------------+
                    |  BINANCE (a praca)|
                    +---------+---------+
                              |
                              v
              +---------------+---------------+
              |    ROBOZINHO ANOTANDO TUDO    |
              |     (camada de dados)         |
              +---------------+---------------+
                              |
                              v
              +---------------+---------------+
              |  ENTENDENDO AMIZADES          |
              |  (correlacao + grafos)        |
              +---------------+---------------+
                              |
                              v
              +---------------+---------------+
              |  ENTENDENDO SENTIMENTO        |
              |  (estatistica + regime)       |
              +---------------+---------------+
                              |
                              v
              +---------------+---------------+
              |  ENTENDENDO QUEM AGRADE       |
              |  (microestrutura + order flow)|
              +---------------+---------------+
                              |
                              v
              +---------------+---------------+
              |  TESTANDO ESTRATEGIAS         |
              |  (backtest walk-forward)      |
              +---------------+---------------+
                              |
                              v
              +---------------+---------------+
              |  GERANDO RELATORIOS BONITOS   |
              |  (dashboards HTML)            |
              +---------------+---------------+
                              |
                              v
              +---------------+---------------+
              |  [FALTA] OPERAR SOZINHO       |
              |  (bot engine + broker)        |
              +---------------+---------------+
                              |
                              v
              +---------------+---------------+
              |  [FALTA] AVISAR NO TELEGRAM   |
              |  (notifications)              |
              +---------------+---------------+
                              |
                              v
              +---------------+---------------+
              |  [SONHO] DINHEIRO REAL        |
              |  (Fase 5, $50-100)            |
              +---------------+---------------+
```

## Glossario para criancas

| Palavra dificil | O que significa na pratica |
|---|---|
| Cripto | Dinheiro digital, como Bitcoin. Nao existe fisico. |
| Binance | A maior "praca" de cripto do mundo. |
| Candle | Anotacao de: preco de abertura, maximo, minimo, fechamento, em um periodo. |
| Parquet | Tipo de arquivo super-comprimido para guardar muitos dados. |
| Correlacao | "Amizade": se A e B sobem juntos, tem correlacao alta. |
| Grafo | Mapa de bolinhas ligadas por linhas. Bolinhas = moedas, linhas = amizade. |
| Volatilidade | O quao nervoso o mercado esta. |
| Drawdown | Queda maxima desde o topo. "Do pico ate o fundo". |
| Sharpe | Nota do mercado: lucro dividido pelo risco. Acima de 1 e bom. |
| Funding rate | Taxa que longs pagam para shorts (ou vice-versa) em futuros. |
| Open Interest (OI) | Quantos contratos estao abertos. |
| Liquidacao | Quando alguem e forçado a vender porque ficou sem margem. |
| Order flow | Quem esta agredindo o book: compradores ou vendedores. |
| Backtest | Testar estrategia no passado pra ver se teria dado lucro. |
| Walk-forward | Treinar em 6 meses, testar em 2 meses seguintes, repetir. Evita "cola". |
| Paper trading | Operar com dinheiro de mentira. Treino. |
| Kill switch | Botao de emergencia que para tudo se perder muito. |

## Nota final

O robo nao e bola de cristal. Ninguem consegue prever o mercado com 100%
de certeza. O que o robo faz e **jogar com probabilidades**: se ele acertar
60-70% das vezes e ganhar mais do que perde (R:R bom), no longo prazo
ganha dinheiro. Mas pode perder. Por isso:

- Sempre comeca com paper trading.
- Dinheiro real comeca baixo ($50-100).
- Tem kill switch.
- E para pesquisa, nao para ficar rico rapido.
