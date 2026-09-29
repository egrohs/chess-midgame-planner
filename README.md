# Chess Midgame Planner

Aplicação Streamlit + python-chess para analisar posições de xadrez por critérios
posicionais e sugerir um plano de jogo, com indicadores visuais no tabuleiro.

## Critérios implementados

| # | Critério | O que mede |
|---|----------|------------|
| 1 | Material bruto | Contagem e valor das peças, diferenças por tipo, par de bispos |
| 2 | Maioria de peões | Peões por ala (a-c, d-e, f-h) e onde criar um passado |
| 3 | Desenvolvimento / tempo | Peças menores desenvolvidas, roque, torres conectadas, dama precoce |
| 4 | Centro aberto/fechado | Peões centrais, cadeias travadas e tensão (aberto, fixo, dinâmico, fechado) |
| 5 | Estrutura básica de peões | Isolados, dobrados, atrasados e passados |

Cada critério devolve: veredito, métricas, observações, planos para brancas e pretas,
casas destacadas e setas no tabuleiro. O plano final combina os critérios por peso
(`analysis/plan.py`) e ordena as ações por relevância.

## Indicadores visuais

| Cor | Significado |
|-----|-------------|
| 🟩 Verde | Vantagem, peça/peão forte, peão passado |
| 🟥 Vermelho | Fraqueza (peão isolado) ou vantagem das pretas no critério de material |
| 🟧 Laranja | Atenção: peões dobrados, atrasados, cadeias travadas, peças não desenvolvidas |
| 🟦 Azul | Tensão de peões e casas de referência |

## Como rodar

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\streamlit.exe run streamlit_app.py
```

A aplicação abre em <http://localhost:8501>.

## Uso

1. Escolha um exemplo na barra lateral ou cole um FEN próprio.
2. Ative as camadas visuais (pills) para pintar no tabuleiro os destaques de cada critério.
3. Leia o plano de jogo sugerido para brancas ou pretas.
4. Explore as abas para ver métricas, observações e o destaque isolado de cada critério.

## Testes

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
```

## Estrutura

```
chess-midgame-planner/
├── streamlit_app.py          # interface Streamlit
├── analysis/
│   ├── types.py              # CriterionResult, Metric, paleta de cores
│   ├── board_utils.py        # helpers de casas, alas, peões, roque
│   ├── material.py           # critério 1
│   ├── pawn_majority.py      # critério 2
│   ├── development.py        # critério 3
│   ├── center.py             # critério 4
│   ├── pawn_structure.py     # critério 5
│   ├── board_render.py       # SVG com destaques e setas
│   └── plan.py               # consolidação em plano de jogo
└── tests/test_analysis.py
```

## Próximos critérios (maior complexidade)

Casas fracas e buracos, bom vs. mau bispo, colunas abertas e semiabertas,
segurança do rei, espaço, iniciativa e peças sobrecarregadas.
