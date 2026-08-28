# DREDGE — Platina Definitiva (PT-BR)

Guia de platina completo de **DREDGE** em português, empacotado como plugin do
[Streamer Sidekick](https://github.com/ricardothezouro-debug) na categoria
`platina` (aba **Platinas**).

É a conversão fiel do guia HTML *“DREDGE — Platina Definitiva PT-BR”*: **nada foi
resumido ou removido**. Todo o conteúdo, incluindo as imagens, está no plugin.

| Conteúdo | Qtd. |
|---|---:|
| Passos cronológicos (walkthrough por fase) | 90 |
| Itens no localizador “Onde está...?” | 23 |
| Missões secundárias / Figuras (Pursuits) | 14 |
| Espécies do jogo base | 67 |
| Santuários | 4 |
| Docas (15 cais nomeados + 4 de compatibilidade) | 19 |
| Troféus com nomes PT-BR | 40 |
| Itens na ordem de pesquisa | 8 |
| Mapas / screenshots de referência | 12 |
| Fontes consultadas | 5 |
| **Itens marcáveis no total** | **309** |

## As 10 abas

| # | Aba | O que tem |
|---|-----|-----------|
| 01 | Passo a passo | Os 90 passos em ordem, agrupados em 9 fases recolhíveis. Cada passo traz *Quando*, *Faça exatamente*, *Por que agora*, o local e (quando existe) a imagem do guia. |
| 02 | Onde está...? | As 23 relíquias e itens de missão com tipo, região, coordenada, como chegar e pré-requisito. Filtro por texto e por região. |
| 03 | Missões / Figuras | As 14 Pursuits opcionais com onde começam, o que fazer e a rota das entregas. |
| 04 | 67 Peixes | Região, nome PT-BR e inglês, tipo de água, horário, método, melhor ponto e uso em missão. Duas caixas por espécie: a normal e a **anômala**. Filtro por texto, região e “só pendentes”. |
| 05 | Santuários | Os 4 altares: oferta, como obter, recompensa e o mapa de cada um. |
| 06 | Docas | Os 15 cais nomeados e os 4 acampamentos de compatibilidade. |
| 07 | 40 Troféus | Nome PT-BR, tier, requisito e atalho. Filtro por texto e “só pendentes”. Alimenta o contador do card. |
| 08 | Pesquisa | A ordem de compra do equipamento para não travar a rota (62 Pontos de Pesquisa no total). |
| 09 | Mapas / Imagens | As 12 imagens de referência com legenda e fonte. |
| 10 | Fontes | Os 5 guias cruzados na elaboração da rota, com link. |

## Recursos

- **Busca global** no topo: procura ao mesmo tempo em passos, itens, peixes e
  missões, ignorando acentuação e maiúsculas. Digite `Caixa de Música`, `E12` ou
  `Peixe-remo` e pule direto para a aba certa.
- **Progresso salvo automaticamente** em
  `%APPDATA%\StreamerSidekick\platinas\dredge\progress.json` — fora da pasta do
  plugin, então **sobrevive a atualizações**.
- **Exportar / Importar progresso** em JSON, para levar a run para outro PC.
  O importador também aceita o arquivo exportado pelo guia HTML original
  (converte as chaves antigas de troféu automaticamente).
- **Imagens com cache em disco**: baixadas uma vez e reaproveitadas — depois da
  primeira visita, funcionam offline.

## Atenção às DLCs

A platina continua ligada aos 39 troféus do jogo base. Mas se uma expansão
estiver instalada **antes** de você liberar *Mestre Pescador* / *Atraindo
Anomalias*, o jogo pode incorporar as espécies da expansão ao requisito desses
dois troféus. Para a rota mais curta, libere os dois **antes** de adicionar
*Pale Reach* ou *Iron Rig*.

## Instalação

Pelo Streamer Sidekick: aba **Platinas** → card **“+”** → **DREDGE — Platina
Definitiva**.

## Rodar standalone (sem o Sidekick)

```bash
pip install -r requirements.txt
set PYTHONPATH=src
python -m platina_dredge
```

## Entrada para o `platinas.json` do Sidekick

Também disponível no arquivo [`platinas-entry.json`](platinas-entry.json):

```json
{
  "id": "dredge",
  "name": "DREDGE — Platina Definitiva",
  "description": "Guia PT-BR completo: rota de 90 passos, 67 peixes, localizador de itens, santuários, docas e os 40 troféus.",
  "repo": "ricardothezouro-debug/Assistente-de-platina-Dredge",
  "ref": "main",
  "version": "1.0.0",
  "src_subdir": "src",
  "module": "platina_dredge.module",
  "accent": "#73AAA5",
  "icon": "src/platina_dredge/assets/brand/icon.png",
  "min_sidekick_version": "0.6.0",
  "changelog": "Primeira versão: as 10 abas do guia PT-BR completo, com imagens e progresso exportável."
}
```

## Estrutura

```
src/platina_dredge/
  __init__.py
  module.py          contrato do plugin: module_info() / build_page() / help_text()
  page.py            a página: as 10 abas, busca global, filtros e progresso
  guide_data.py      TODO o conteúdo do guia (único arquivo específico do jogo)
  progress.py        formato das chaves de progresso e import do formato antigo
  storage.py         progresso em %APPDATA% (genérico do template)
  image_loader.py    download de imagens com cache em disco (genérico do template)
  __main__.py        execução standalone
  assets/brand/icon.png
```

### Diferenças em relação aos arquivos genéricos do template

Duas mudanças em `image_loader.py`, ambas necessárias para este guia:

1. **Cabeçalhos de navegador** nas requisições. Com o `User-Agent` genérico do
   template, o GameFAQs devolve **403** e 16 das 17 imagens do guia não
   carregavam. Com `Referer`/`Sec-Fetch-*` (o `Referer` é a raiz do próprio host
   da imagem), as 17 baixam normalmente.
2. **`ImageLoader.shutdown()`**, chamado no `aboutToQuit` e no `closeEvent` da
   página. Sem isso, fechar o app com um download em andamento destrói um
   `QThread` ainda rodando e o Qt aborta o processo.

`page.py` também é próprio: o template genérico renderiza uma lista simples de
troféus, o que descartaria 9 das 10 abas deste guia. O contrato do
`PLUGIN_STANDARD.md` (`module_info()` / `build_page()`) e os `objectName`s do
design system são respeitados.

## Créditos

Guia não oficial, sem vínculo com a Black Salt Games. As imagens são de
terceiros e estão creditadas na aba **Mapas / Imagens**; as fontes da rota estão
na aba **Fontes**.
