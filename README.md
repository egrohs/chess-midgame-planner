# Chess Midgame Planner

Aplicação Streamlit + python-chess para analisar posições de xadrez por critérios
posicionais e sugerir um plano de jogo, com **tabuleiro interativo** e indicadores visuais.

## Funcionalidades

- **Tabuleiro clicável** (Streamlit Custom Component v2): clique para selecionar uma peça
  e clique no destino para jogar; os lances legais aparecem destacados.
- **Modo "Montar posição"**: paleta de peças para colocar/apagar, definir de quem é o lance,
  limpar o tabuleiro ou voltar à posição inicial.
- **Navegação de lances**: início / anterior / próximo / fim, desfazer, slider de lance e
  lista de lances em notação algébrica.
- **Importar FEN e PGN** e **exportar PGN** da linha jogada.
- **Camadas visuais** por critério, que pintam casas e desenham setas no tabuleiro;
  estrutura, casas fracas e outposts aparecem inicialmente.

## Critérios implementados (ordem de implementação)

| # | Critério | O que mede |
|---|----------|------------|
| 1 | Material bruto | Contagem e valor das peças, diferenças por tipo, par de bispos |
| 2 | Maioria de peões | Peões por ala (a-c, d-e, f-h) e onde criar um passado |
| 3 | Desenvolvimento / tempo | Peças menores desenvolvidas, roque, torres conectadas, dama precoce |
| 4 | Centro aberto/fechado | Peões centrais, cadeias travadas e tensão (aberto, fixo, dinâmico, fechado) |
| 5 | Estrutura básica de peões | Isolados, dobrados, atrasados e passados |
| 6 | Casas fracas | Casas da 3ª e 4ª fileiras próprias que os peões não podem mais defender; distingue fraqueza neutralizada de explorável |
| 7 | Outposts | Postos potenciais na metade adversária, apoiados por peão e não expulsáveis por peões; identifica os já ocupados por peça menor |
| 8 | Espaço | Casas ocupadas/controladas na metade adversária sem ataque de peões rivais e mobilidade média das peças (estimativa geométrica, não lances legais) |
| 9 | Atividade das peças | Destinos vazios de cavalos, bispos, torres e damas, ponderados por centralidade, apoio de peão e contestação adversária; média por peça para separar atividade de vantagem material |
| 10 | Segurança do rei | Escudo de peões, colunas próximas sem peão próprio, atacantes na zona do rei, xeque e casas de fuga seguras |
| 11 | Pior peça | Compara peças menores e pesadas de cada lado usando mobilidade útil normalizada por tipo, desenvolvimento, apoio de peão, acesso a colunas e exposição |

Cada critério devolve: veredito, métricas, observações, planos para brancas e pretas,
casas destacadas e setas no tabuleiro. O plano final combina os critérios por peso
(`analysis/plan.py`). O **plano sugerido** usa uma ordem de revisão fixa,
independente dos pesos da avaliação: segurança do rei, material, atividade,
desenvolvimento, pior peça (própria e adversária), estrutura de peões, centro,
casas fracas, outposts, maioria de peões e espaço. Mostra uma ação por critério
para não ocultar temas de menor prioridade. Coordenação e rupturas ficam de
fora até haver análise específica; a ordenação não substitui cálculo tático.
As **camadas visuais** e as abas de **critérios analisados** seguem essa
mesma ordem de prioridades; os números das abas indicam essa ordem, não a
ordem histórica de implementação da tabela acima.

Em **Atividade**, a camada destaca a peça mais ativa de cada lado e, em laranja,
as peças com poucas opções úteis. O índice não calcula lances legais nem a
segurança tática de cada movimento: casas atacadas por peões são descartadas,
e as contestadas por outras peças recebem peso menor.

Em **Segurança do rei**, a camada mostra o escudo, as lacunas à frente do
rei, casas de fuga e setas dos atacantes. Colunas sem peão próprio só pesam
quando ainda há torres ou damas adversárias; a contagem de fugas independe
de quem joga e não substitui o cálculo de mate.

Em **Pior peça**, a camada destaca uma peça de cada lado que mais precisa ser
melhorada. O índice compara peças de tipos diferentes sem equiparar sua
mobilidade bruta e sugere desenvolver, proteger ou abrir uma linha conforme
o motivo da restrição. É uma heurística posicional, não uma análise de trocas.

## Indicadores visuais

| Cor | Significado |
|-----|-------------|
| 🟩 Verde | Vantagem, peça/peão forte, peão passado |
| 🟥 Vermelho | Fraqueza (peão isolado) ou vantagem das pretas no critério de material |
| 🟧 Laranja | Atenção: peões dobrados, atrasados, cadeias travadas, peças não desenvolvidas |
| 🟦 Azul | Tensão de peões, casas de referência e destinos legais |
| 🟨 Amarelo | Casa selecionada e último lance jogado |

## Como rodar

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\streamlit.exe run streamlit_app.py
```

A aplicação abre em <http://localhost:8501>.

## Uso

1. Escolha um exemplo na barra lateral, cole um FEN ou cole um PGN.
2. Em **Mover peças**, clique numa peça e depois no destino. Use os botões e o slider
   para navegar pela partida; escolha a peça de promoção antes de promover um peão.
3. Em **Montar posição**, selecione uma peça na paleta e clique nas casas
   (clicar de novo sobre a mesma peça a apaga). Defina de quem é o lance.
4. Ative as camadas visuais para pintar no tabuleiro os destaques de cada critério.
5. Leia o plano de jogo sugerido e explore as abas de cada critério.

## Testes

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest tests -q
```

Os testes cobrem os critérios de análise, a lógica de partida (navegação, PGN, edição
de posição, cliques) e a interface com `streamlit.testing.v1.AppTest`, sem navegador.

## Estrutura

```
chess-midgame-planner/
├── streamlit_app.py          # interface Streamlit
├── presets.py                # posições de exemplo
├── game.py                   # linha de lances, PGN, edição de posição, cliques
├── components/
│   └── interactive_board.py  # tabuleiro clicável (Custom Component v2)
├── analysis/
│   ├── types.py              # CriterionResult, Metric, paleta de cores
│   ├── board_utils.py        # helpers de casas, alas, peões, roque
│   ├── material.py           # critério 1
│   ├── pawn_majority.py      # critério 2
│   ├── development.py        # critério 3
│   ├── center.py             # critério 4
│   ├── pawn_structure.py     # critério 5
│   ├── weak_squares.py       # critério 6
│   ├── outposts.py           # critério 7
│   ├── space.py              # critério 8
│   ├── piece_activity.py     # critério 9
│   ├── king_safety.py        # critério 10
│   ├── worst_piece.py        # critério 11
│   ├── board_render.py       # SVG com destaques, setas e dicas de lance
│   └── plan.py               # consolidação em plano de jogo
└── tests/
    ├── test_analysis.py
    ├── test_game.py
    └── test_app.py
```

## Próximos critérios (maior complexidade)

Bom vs. mau bispo, colunas abertas e semiabertas, iniciativa e peças
sobrecarregadas.
