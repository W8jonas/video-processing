# Mãos, Libras e geometria interativa em Python

Novo programa: **vídeo processado para o Google Meet** com câmera virtual.
Execute `.venv/bin/hand-effects --camera 1` após autorizar a extensão do OBS.
[Preparação e comandos](docs/hand_effects.md). A primeira etapa foi implementada;
o usuário confirmou a seleção da câmera virtual e as marcações no Meet.
Agora é possível capturar o fundo com **B**, confirmar com **Enter** e
desaparecer/reaparecer com **I**. **R** retorna ao vivo imediatamente.
Esta primeira versão mostra a foto inteira do cenário; remoção seletiva da
pessoa e controle por gesto seguem no [roadmap em etapas](docs/roadmap_video_effects.md).

Protótipo local com webcam, MediaPipe Tasks e OpenCV. Desenha 21 articulações por
mão, acompanha até duas mãos, estima quais dedos estão estendidos e permite
cadastrar e reconhecer configurações estáticas de algumas letras.

O detector de mãos vem pronto. O reconhecedor de letras **precisa dos seus exemplos**:
neste repositório não há dataset nem classificador de Libras pré-treinado.

## Dedos individuais para o ESP8266

Novo programa independente, conectado ao receptor em `192.168.0.105`:

```sh
.venv/bin/hand-esp --camera 1
```

Os IDs são **1 indicador, 2 médio, 3 anelar e 4 mindinho**. O polegar é ignorado.
Indicador e mindinho enviam `[1,4]`; indicador, médio e anelar enviam `[1,2,3]`.
Mostre uma única mão. A janela exibe os dedos individualmente e a confirmação
recebida do ESP. **Q/Esc** encerra e tenta liberar o estado.

O receptor V5 foi instalado por OTA com LEDs em **D0, D1, D2 e D7**, correspondendo
aos dedos 1, 2, 3 e 4. Cada LED usa seu próprio resistor em série e retorna ao
GND. O DHT foi desconectado de D2. Os serviços anteriores continuam disponíveis,
e os LEDs são liberados ao perder o rastreamento ou expirar o estado em 2,5 s.
As leituras dos GPIOs foram verificadas, e o usuário confirmou o funcionamento
físico dos quatro LEDs no teste ao vivo.
[Ensaio de alimentação e saídas](docs/experimentos/2026-11-02-leds-e-alimentacao.md).

Use `--dry-run` para testar sem rede, `--hand right` para selecionar apenas a
mão direita e `--check` para consultar o ESP sem abrir a câmera. Protocolo,
firmware e evidências estão em [docs/esp8266.md](docs/esp8266.md).

## Construir figuras pelas pontas dos dedos

Neste modo, a quantidade de dedos escolhe a construção e as pontas controlam
seus vértices. Feche a janela anterior e execute:

```sh
.venv/bin/hand-math --camera 1 --scene draw
```

| Dedos em cada mão | Construção |
|---|---|
| 2 + 1 ou 1 + 2 | Triângulo: três pontas, três vértices |
| 2 + 2 | Retângulo/quadrilátero: quatro pontas, quatro vértices |
| 3 + 1 ou 1 + 3 | Pirâmide triangular: três pontas na base e uma no ápice |
| 3 + 3 | Cubo livre: três cantos por face e dois vértices calculados |

Comece com **indicador** para um dedo, **polegar + indicador** para dois e
**polegar + indicador + médio** para três. Outros conjuntos de dedos também são
aceitos, mas precisam formar cantos separados na imagem. Deixe os demais dedos
recolhidos e as duas mãos inteiras visíveis. A contagem de cada mão aparece na
tela; mantenha a combinação por 0,3 segundo para confirmar uma nova figura.

O modo de desenho avalia os landmarks 3D com uma regra própria, mais tolerante a
dedos naturalmente curvados e específica para o polegar. Cada dedo tem filtragem
temporal, limiares distintos para abrir/fechar e confirmação de mudanças, para não
alterar a contagem por uma leitura isolada. Isso melhora a seleção das pontas;
não recupera landmarks que o detector não conseguiu localizar.

Todas as cinco pontas ficam marcadas, mesmo quando não entram na figura:
**anel verde** significa dedo ativo, **cinza** recolhido e **laranja** mudança em
confirmação. A lista de dedos de cada mão e o aviso explicam se falta uma mão,
se a contagem é incompatível ou se os cantos estão próximos/alinhados. **H**
mostra também as 21 articulações.

Se a contagem automática ainda oscilar, teste as pontas fixas do cubo:

```sh
.venv/bin/hand-math --camera 1 --scene draw --drawing-shape cube
```

Esse modo usa diretamente polegar, indicador e médio de cada mão, mesmo que a
avaliação de extensão erre. A figura deixa de depender da contagem, mas continua
exigindo duas mãos rastreadas e cantos não alinhados. `--drawing-shape` também
aceita `rectangle` (2+2), `triangle` (2+1) e `pyramid` (3+1); nas combinações
assimétricas fixas, a mão à esquerda da tela fornece dois/três dedos e a direita
fornece o indicador. O padrão `auto` mantém a troca de figura pelos dedos.

As pontas são suavizadas e viram os vértices medidos, não apenas controles de
posição de uma forma pronta. No cubo, cada trio completa um paralelogramo: o
canto ausente é a soma dos dois cantos adjacentes menos o canto compartilhado.
Os dois cantos inferidos ficam marcados com **\***. Os seis vértices medidos
continuam ligados às seis pontas. O bloco pode se deformar, e os quatro cantos
do retângulo também podem produzir um quadrilátero sem ângulos retos.

Para pirâmide e cubo, a profundidade é virtual e a projeção mantém os vértices
medidos sobre as pontas na imagem. Não usamos o `z` relativo de mãos diferentes
como se estivesse no mesmo referencial. Pontas colineares ou bases muito pequenas
não geram a figura; separe os dedos para abrir a construção.

Os comandos deste modo são independentes dos gestos do laboratório anterior:

- **Duas mãos fechadas por 0,8 s:** trocar a aparência.
- **Duas mãos abertas, cinco dedos em cada, por 0,8 s:** fixar/soltar a figura.
- Volte a uma pose de desenho entre comandos para liberar a próxima ação.
- **0–3** alternam aparência; **G** alterna grade; **H** mostra articulações;
  **Espaço** fixa/solta; **R** reinicia; **Q/Esc** encerra.

Para fixar por gesto, faça isso logo após desenhar: o programa guarda a última
figura válida por até dois segundos enquanto as duas mãos executam o comando.
A figura fixa permanece mesmo ao retirar as mãos. Nos polígonos 2D, área e
perímetro são medidos em pixels. Os modos `portal` e `cube` continuam disponíveis.

## Brincar com matemática

Feche a janela de Libras antes de abrir o novo experimento:

```sh
.venv/bin/hand-math --camera 1
```

Mostre **as duas mãos**, com os indicadores em cima e os polegares embaixo,
formando os quatro cantos de uma moldura. Um filtro aparece dentro do quadrilátero.
Mova os dedos para explorar área, perímetro, comprimentos e ângulos em tempo real.
São medidas em pixels da imagem, não em centímetros.

- **0/1/2/3**: imagem original, negativo, térmico ou bordas.
- **G**: mostrar/esconder a grade projetiva; **H**: mostrar/esconder articulações.
- **Espaço**: fixar/soltar a moldura; **R**: reiniciar; **Q/Esc**: sair.

O quadrilátero precisa ser convexo, sem cruzamento dos cantos. A suavização limpa
o estado quando uma mão desaparece; no modo fixo, a moldura permanece na tela.
Se necessário, use `--width 640 --height 480`, como no protótipo de Libras.
Este experimento reutiliza o detector e não lê nem modifica os cadastros de letras.

### Cubo 3D

Para iniciar diretamente no cubo, feche a janela anterior e execute:

```sh
.venv/bin/hand-math --camera 1 --scene cube
```

Use a mesma moldura de duas mãos. O cubo acompanha seu centro; afastar as mãos
aumenta sua escala. Inclinar a linha entre as mãos gira o eixo Z. Variar a
abertura polegar–indicador de uma mão em relação à outra controla o giro Y;
variar a largura superior em relação à inferior controla o giro X. Há uma
inclinação inicial para mostrar três faces.

Os oito vértices pertencem a um cubo rígido unitário. Uma única rotação preserva
as arestas e os ângulos, e uma câmera virtual faz a projeção em perspectiva.
Faces voltadas à câmera recebem cores e sombreamento; arestas ocultas aparecem
tracejadas. As aparências são **cristal, neon, sólido e aramado**. O controle da
mão esquerda troca a aparência; o da direita fixa/solta o cubo; ambas alternam
a grade. As medidas `6 u²` e `1 u³` pertencem ao cubo virtual unitário: as mãos
controlam seu desenho, sem reconstruir profundidade métrica da webcam.

Para alternar entre portal e cubo sem teclado, junte **polegar e indicador nas
duas mãos**, com os outros dedos recolhidos, por 0,8 segundo. Depois, reabra a
moldura e espere **Gestos prontos** antes do próximo comando. O atalho de teclado
equivalente é **C**. O modo padrão continua sendo o portal.

### Laboratório de sólidos

Além do cubo, agora há **tetraedro, octaedro e icosaedro**. Para começar no
icosaedro com giro automático:

```sh
.venv/bin/hand-math --camera 1 --scene cube --shape icosahedron --spin
```

No modo 3D, com médio, anelar e mínimo recolhidos:

- **Pinça na mão à esquerda da tela por 0,8 s:** próximo sólido.
- **Pinça na mão à direita por 0,8 s:** ligar/desligar giro automático.
- **Pinças nas duas mãos:** alternar 2D/3D, como antes.

Reabra os dedos entre comandos. Durante uma pinça, a última moldura válida fica
visível por até três segundos, desde que as duas mãos continuem detectadas.
O giro pausa quando o objeto está fixo, as mãos somem ou o modo 2D está ativo.
Os atalhos opcionais são **S** para forma, **A** para giro e **R** para reiniciar
sem giro automático. `--shape` aceita `cube`, `tetrahedron`, `octahedron` e
`icosahedron`; `--scene cube` continua sendo o nome do modo 3D por compatibilidade.

| Sólido | Vértices | Arestas | Faces | V − A + F |
|---|---:|---:|---:|---:|
| Cubo | 8 | 12 | 6 | 2 |
| Tetraedro | 4 | 6 | 4 | 2 |
| Octaedro | 6 | 12 | 8 | 2 |
| Icosaedro | 12 | 30 | 20 | 2 |

A tela calcula a relação de Euler, área e volume de cada malha. Todos os sólidos
cabem na mesma esfera virtual de raio √3/2; o cubo mantém aresta unitária.
As faces são trianguladas para somar suas áreas e volumes orientados. São medidas
da geometria virtual: aumentar o objeto na imagem altera a escala da projeção,
mantendo as unidades e proporções do modelo.

### Controles por gestos

Forme a moldura com polegar e indicador e deixe os outros três dedos recolhidos
nas duas mãos por um instante, até aparecer **Gestos prontos**. Sem desfazer os
cantos da moldura, estenda médio, anelar e mínimo por **0,8 segundo**:

- Na mão **à esquerda da tela**: próximo filtro.
- Na mão **à direita da tela**: fixar ou soltar o portal.
- Nas **duas mãos**: mostrar ou esconder a grade.
- **Pinça nas duas mãos**, com os outros dedos recolhidos: alternar portal/cubo.
- No 3D, **pinça esquerda** troca a forma e **pinça direita** alterna o giro.

As direções se referem à imagem espelhada. A tela mostra o progresso do comando.
Depois de cada ação, recolha os três dedos nas duas mãos por pelo menos 0,25
segundo para liberar outra ação. Manter a mão aberta não repete comandos; a perda
de rastreamento não conta como liberação. Para fixar, mantenha uma moldura válida.
O portal fixo permite retirar as mãos e também usar o teclado, se preferir.
Os testes desses controles usam poses simuladas; o conforto e a detecção dos
gestos ainda precisam de experimentação ao vivo.

Libras continua disponível com `.venv/bin/hand-libras --camera 1`. Uma cópia
congelada do protótipo que funcionou foi salva em
`snapshots/libras-20261020-184628.zip`, incluindo código, testes, exemplos de letras,
modelo e manifesto SHA-256. O arquivo é local e não inclui o ambiente `.venv`.

## Instalação e execução

Use Python 3.12 no Mac Apple Silicon. Na raiz do projeto:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/hand-libras --download-model
.venv/bin/hand-libras
```

Alternativa com `uv`:

```sh
uv sync --python 3.12
uv run hand-libras --download-model
uv run hand-libras
```

O download explícito obtém o modelo Hand Landmarker do Google (~8 MB). Depois
disso, a câmera e a classificação funcionam localmente. Os frames não são salvos;
a coleta grava somente coordenadas normalizadas, letra e identificador de sessão
em `data/poses.jsonl`.

Se a câmera não abrir, autorize o terminal ou aplicativo em **Ajustes do Sistema →
Privacidade e Segurança → Câmera** e reinicie-o. Experimente `--camera 1` se houver
mais de uma câmera. A CPU é o padrão; `--delegate gpu` habilita Metal no Mac.
O programa usa a resolução padrão do dispositivo e tenta recuperar leituras
temporariamente indisponíveis. Para solicitar outro modo de captura, execute
`hand-libras --camera 1 --width 640 --height 480`. Após 20 leituras consecutivas
sem imagem, a captura é encerrada. Uma falha de captura interrompe a coleta ativa;
reinicie-a com Espaço quando a imagem voltar.
A entrada é RGBA para ambos os caminhos. A versão `mediapipe==0.10.35` é a base
fixada, já registrada nos testes históricos da pesquisa; não pressupõe que seja
a versão mais recente.

## Primeiro experimento: três letras

Comece com **A, L e V**, consultando as configurações no
[alfabeto manual do INES](https://www.gov.br/ines/pt-br/central-de-conteudos/publicacoes-1/todas-as-publicacoes/alfabeto-manual-e-configuracao-de-maos).

1. Mostre uma única mão inteira, com boa iluminação e fundo simples.
2. Pressione a letra desejada no teclado da janela.
3. Pressione **Espaço**: há um segundo de preparação e três segundos de coleta,
   até dez amostras por segundo. Mantenha a letra, variando um pouco a posição.
4. Repita para cada letra. São necessárias pelo menos dez amostras em cada uma
   de duas classes para ativar a classificação.
5. Encerre a coleta, retire a mão e refaça as letras para testar o reconhecimento.
   **Enter** adiciona uma letra estável ao texto; **Backspace** apaga; **Q/Esc** sai.

As amostras persistem entre execuções. O subconjunto inicial é
`A B C D E F I L O S U V W`; isso indica as etiquetas aceitas, não precisão
garantida. Para recomeçar sem apagar a coleta anterior, use
`--data data/nova_sessao.jsonl`. Não mude de letra durante uma coleta.

## Como funciona e limites

- A geometria remove posição e escala e espelha a mão esquerda para comparação.
  A orientação na câmera é preservada, pois pode distinguir configurações.
- A extensão dos dedos usa ângulos e distâncias 3D; é uma indicação heurística.
- A classificação compara cada pose com as três amostras mais próximas de cada
  letra. Distância alta ou classes próximas produzem resultado desconhecido.
  A letra só aparece após uma janela de estabilidade; a perda da mão limpa o estado.
- Quando as duas primeiras candidatas são A/S ou U/V, a comparação combina a
  pose geral com medidas locais: posição do polegar em relação às bases dos
  dedos, ou distância e abertura entre indicador e médio. As medidas são
  comparadas com os exemplos cadastrados e não exigem recadastro. Ambiguidades
  continuam sendo rejeitadas; a tela mostra candidatas, margem e motivo da rejeição.
- `--threshold 0.18` e `--margin 0.035` controlam a rejeição. A distância exibida
  **não é probabilidade nem medida de acurácia**. Poses desconhecidas ainda podem
  parecer uma letra cadastrada.
- A detecção acompanha duas mãos, mas cadastro e reconhecimento ao vivo exigem
  uma. Este baseline é pessoal e sensível a oclusão, iluminação e ponto de vista.
- Movimentos não são modelados. O protótipo não reconhece o alfabeto completo,
  frases ou Libras como língua. A expansão exige sequências temporais e revisão
  das etiquetas com alguém fluente em Libras.

## Validação

Em 20/10/2026, os 21 testes automatizados passaram, incluindo comparação local
de A/S e U/V com geometrias sintéticas, recuperação de
falhas temporárias de captura e encerramento após falhas persistentes em testes
com câmera simulada. Também foi verificada a
integração entre o tipo de resultado do MediaPipe, a extração de features e o
desenho OpenCV com dados sintéticos, usando Python 3.12.6, MediaPipe 0.10.35 e
OpenCV 4.11.0. O projeto foi instalado em `.venv/` com dependências do cache local.
Após liberar as permissões, o modelo oficial foi baixado e a inferência real
detectou duas mãos, com 21 pontos cada, na
[imagem de exemplo do MediaPipe](https://storage.googleapis.com/mediapipe-assets/woman_hands.jpg).
O download usa o pacote de certificados `certifi` quando disponível para
verificar HTTPS no Python do macOS. Após o ajuste da captura, a câmera USB no
índice 1 processou 100 frames, com FPS final suavizado do loop de 20,4 e nenhuma
falha de leitura. Nenhuma mão foi detectada nesse teste; reconhecimento ao vivo de
mãos e letras continua pendente de validação. Os avisos do MediaPipe também
apareceram na captura bem-sucedida. O MediaPipe precisa de acesso ao contexto gráfico
do macOS, mesmo com inferência por CPU; neste ambiente, a execução dentro do
sandbox abortou e os testes reais exigiram execução fora dele.

Com o experimento de matemática, a suíte passou a 26 testes. Os cinco novos
testes cobrem área, perímetro, soma dos ângulos, rejeição de polígonos inválidos,
identidade dos cantos e suavização temporal. O desenho dos quatro filtros e da
grade foi verificado com uma imagem sintética.

Os controles por gestos ampliam a suíte para 34 testes, incluindo temporização,
liberação obrigatória, perda de rastreamento e ações na aplicação sem teclas.

Com o cubo, são 43 testes: rigidez das arestas e ângulos, projeção, normais,
visibilidade e ordem das faces, controles de rotação e escala, pinça dupla e
uso dos gestos no modo 3D. Os quatro materiais foram renderizados com dados
sintéticos; o comportamento completo com mãos reais ainda precisa ser testado.

O laboratório amplia a suíte para **53 testes**, incluindo topologia fechada,
arestas regulares, medidas conhecidas, invariância de área/volume por rotação,
velocidade de giro, pausa ao fixar e controles por pinça sem perder o objeto.
As 16 combinações dos quatro sólidos com os quatro materiais e grade foram
renderizadas com dados sintéticos. Os novos comandos ainda precisam de uso ao vivo.

O modo de construção amplia a suíte para **64 testes**. Os testes verificam as
quatro combinações nas duas orientações, reprojeção de cada vértice medido na sua
ponta, dois cantos inferidos no cubo, topologia fechada, rejeição de pontos
degenerados, suavização, troca automática de figura e fixação por gesto. As 16
combinações de construção/material foram desenhadas com o OpenCV real e pontas
sintéticas. A detecção completa com mãos reais ainda precisa ser experimentada.

A seleção de dedos foi ampliada para **74 testes**, cobrindo dedos relaxados,
mudanças persistentes, leitura isolada ruim, perda de rastreamento, polegar,
perfis com pontas fixas e diagnóstico das rejeições. A integração com o modelo
real também foi executada na imagem pública do MediaPipe, sem abrir a webcam.
Esses testes não medem a precisão nas poses ao vivo do usuário.

Os testes de geometria, persistência, rejeição e estabilidade usam apenas Python:

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
.venv/bin/hand-libras --image caminho/mao.jpg
.venv/bin/hand-libras --headless --max-frames 100
```

O modo imagem imprime JSON sem abrir a câmera; a webcam imprime um resumo ao
encerrar. O FPS do loop inclui captura, inferência e, com janela, desenho/espera;
não mede a latência física entre câmera e tela.

Para avaliar letras, faça uma nova sessão sem coletar mais exemplos e registre
acertos, confusões e poses rejeitadas por letra. Não use frames vizinhos da mesma
coleta como evidência de generalização. Ainda não há acurácia medida em usuários.

## Organização e próximos passos

`src/hand_libras/core.py` contém geometria e classificador; `app.py` contém a
webcam e a interface; `tests/` valida a lógica sem câmera. `models/` e `data/`
recebem arquivos locais ignorados pelo Git. A pesquisa anterior continua em
`reports/` e `research_notes/`.

`src/hand_math/geometry.py` implementa área, perímetro, ângulos, validação convexa
e suavização temporal; `src/hand_math/app.py` desenha o portal e sua grade por
homografia. A entrada independente é `hand-math`.
`src/hand_math/cube.py` contém a rotação rígida, câmera virtual e desenho do cubo.
O renderizador também desenha as malhas regulares de `src/hand_math/solids.py`,
que calcula suas medidas e controla a rotação automática.
`src/hand_math/drawing.py` constrói as figuras a partir dos dedos; `drawing_app.py`
contém a interface independente de `--scene draw`.

Os testes de Libras em sessões separadas e o reconhecimento de movimentos ficam
para uma retomada futura. O experimento de geometria oferece o portal e o cubo;
o próximo refinamento depende dos testes de conforto e estabilidade ao vivo.

Referências consultadas em 20/10/2026:
[Hand Landmarker Python](https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker/python),
[MediaPipe 0.10.35](https://pypi.org/project/mediapipe/0.10.35/) e o material do INES
vinculado acima (a página bloqueou a leitura automatizada; não houve validação
linguística das poses nesta implementação).
