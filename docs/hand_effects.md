# Vídeo processado no Google Meet

Etapa 1 implementada em 02/11/2026: programa `hand-effects`, independente dos
experimentos de Libras, geometria e ESP8266. A saída mostra a webcam com as
articulações e os dedos 1=indicador, 2=médio, 3=anelar e 4=mindinho.
Verde indica dedo estendido; cinza indica recolhido. As etapas 2/3 acrescentam
captura do fundo e invisibilidade inicial por tecla. Segmentação da pessoa e
controle por gesto seguem no [roadmap](roadmap_video_effects.md).

## Preparação no Mac

OBS 33.0.1 e pyvirtualcam 0.15.0 foram instalados nesta máquina. Em outro ambiente:

```sh
brew install --cask obs
.venv/bin/python -m pip install -e '.[effects]'
```

Uma vez por instalação:

1. Abra OBS e clique em **Iniciar câmera virtual**. O assistente inicial pode
   ser cancelado; não é necessário configurar transmissão nem adicionar webcam.
2. Autorize a extensão do OBS quando o macOS solicitar. Em versões recentes:
   **Ajustes do Sistema → Geral → Itens de Início e Extensões → Extensões de Câmera**.
3. Inicie/pare a câmera virtual e encerre OBS com **Cmd+Q**. O Python será o
   produtor do vídeo; OBS não deve produzir simultaneamente.

Procedimento conferido na documentação do
[pyvirtualcam](https://github.com/letmaik/pyvirtualcam#macos-obs) e do
[OBS](https://obsproject.com/kb/virtual-camera-troubleshooting) em 02/11/2026.
A autorização da extensão requer interação do usuário no macOS.

## Executar

Primeiro, confirme que o dispositivo virtual pode ser aberto. Esse comando
envia um frame de teste e encerra; não mantém uma transmissão:

```sh
.venv/bin/hand-effects --check
```

Para usar a webcam USB já identificada como câmera 1:

```sh
.venv/bin/hand-effects --camera 1
```

Mantenha o programa aberto. No Meet, selecione **Configurações → Vídeo →
Câmera → OBS Virtual Camera**. Escolha o microfone normalmente e desative os
efeitos de fundo do Meet durante a validação. A janela local acrescenta instruções
e o preview da captura; esses controles não são enviados ao Meet. **H** alterna
as marcações; **Q/Esc** sai quando a janela está em foco. No terminal, **Ctrl+C**
também encerra.

## Capturar o fundo e desaparecer

Encerre a versão anterior e execute novamente o mesmo comando. Mantenha a
câmera fixa e a janela do programa em foco para usar as teclas:

1. Pressione **B**. A contagem padrão dá cinco segundos para sair completamente
   do enquadramento. Ela aparece apenas localmente; o vídeo no Meet segue ao vivo.
2. Aguarde a foto do cenário e volte. Confira o preview congelado na janela:
   ele deve mostrar o ambiente sem você e sem marcações de mãos.
3. Pressione **Enter** para confirmar. **B** refaz a foto; **C** descarta a captura.
   A confirmação é manual; não há segmentador verificando se o ambiente está vazio.
4. Pressione **I** para desaparecer. Pressione **I** novamente para reaparecer,
   com transição padrão de meio segundo. **R** retorna imediatamente ao vivo.

O efeito inicial substitui o vídeo inteiro pela foto do fundo: pessoas e objetos
em movimento também ficam congelados. O detector continua lendo a webcam
original enquanto a saída mostra a foto. Remover somente a pessoa e alternar
por gesto são as próximas etapas.

O fundo fica somente na memória e precisa ser capturado em cada execução.
Iniciar nova captura limpa a referência anterior e volta ao vivo. Falha de leitura
ou mudança na resolução também invalida o fundo. Se mudar a câmera de posição,
os móveis ou a iluminação, recapture com **B**; esses casos não são detectados
automaticamente.

```sh
# Mais tempo para sair do enquadramento e transição de um segundo
.venv/bin/hand-effects --camera 1 --countdown 8 --fade 1
```

## Diagnóstico

```sh
# Conferir cores RGB, texto ABC123 e contador, sem abrir a webcam
.venv/bin/hand-effects --test-pattern

# Validar apenas a webcam e as mãos, mesmo sem extensão virtual autorizada
.venv/bin/hand-effects --camera 1 --preview-only

# Saída menor, sem forçar o modo de captura da câmera USB
.venv/bin/hand-effects --camera 1 --width 640 --height 480 --fps 20
```

A saída padrão é 1280×720, limitada a 30 FPS; não é uma promessa de desempenho.
O redimensionamento preserva proporções com barras pretas. A captura usa o modo
padrão da webcam. A orientação original é preservada por padrão; use `--mirror`
se quiser espelhar o vídeo enviado. `--no-mirror` continua aceito explicitamente.
Confirme texto e orientação pela imagem recebida por outro participante, pois o
preview do Meet pode parecer diferente.

Se o dispositivo não aparecer, termine a configuração do OBS e reabra o navegador.
Se houver disputa pela webcam, feche os outros programas que a utilizam.
Não abra duas instâncias de `hand-effects`. O programa não grava vídeo ou fotos
nem envia comandos ao ESP. A publicação aos participantes ocorre pelo Meet.

## Validação

Testes automatizados: proporções e canais BGR, cores do padrão, identificação
individual dos dedos, saída sem webcam, liberação da câmera virtual em falhas,
contagem regressiva, confirmação e cancelamento do fundo, invalidação por mudança
de resolução, transição reversível e inferência no vídeo original durante o
efeito. Comando:

```sh
.venv/bin/python -m unittest discover -s tests -v
```

Ensaio local: webcam 1, modo nativo, saída 1280×720, CPU, 30 frames sem janela,
no Mac Apple M2 Pro com macOS 26.6.2/Python 3.12.6/MediaPipe 0.10.35/OpenCV
4.11.0. Resultado: 30 frames, zero falhas de captura, 9,3 FPS no loop completo
de captura/inferência/composição/limitação, sem publicação virtual. A amostra
é curta e não estabelece desempenho em reunião nem precisão dos dedos.

O usuário confirmou a seleção da câmera virtual OBS no Meet e a exibição das
marcações das mãos. Relatou espelhamento; o programa agora preserva a orientação
original por padrão. Reinicie o processo para aplicar a alteração. A orientação
vista por outro participante e cinco minutos sem travar ainda precisam ser
confirmados; testes automatizados não comprovam esses critérios.

Após a implementação da captura/invisibilidade inicial, os 109 testes passaram.
A integração de teclado, captura, publicação e inferência foi testada com frames
simulados; o efeito novo ainda precisa ser experimentado pelo usuário no ambiente
real e no Meet.
