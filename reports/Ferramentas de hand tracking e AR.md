# Python valida, a web encanta, Swift ensina

Para reproduzir num Mac Apple Silicon os demos virais em que as mãos desenham um retângulo filtrado ou seguram um cubo 3D, a escolha que mais pesa é o modelo, bem mais do que a linguagem. O **MediaPipe Hand Landmarker** do Google (21 pontos por mão, coordenadas métricas "world", lateralidade e rastreamento entre frames) está por trás de praticamente todas as reproduções públicas, seja em TouchDesigner, Python ou navegador, e os mesmos modelos existem em Python, JavaScript e C. O efeito em si é geometria simples. As pontas do polegar (landmark 4) e do indicador (8) das duas mãos formam um quadrilátero, e o filtro vale só dentro dele. O cubo sai de três pontas de dedo ortogonalizadas por Gram–Schmidt. O que separa o demo "mágico" do protótipo trêmulo é a suavização (filtro One Euro) e uma máquina de estados de gestos com histerese. A recomendação tem três etapas. Comece com **Python 3.12 + MediaPipe Tasks + OpenCV**: testado nesta sessão no seu M2 Pro, ele infere duas mãos em **~3–5 ms por frame via GPU/Metal**. Passe para **TypeScript + `@mediapipe/tasks-vision` + Three.js** quando quiser shaders, 3D real e um link compartilhável. Deixe **Swift + AVFoundation + Vision + Metal** (ou Rust com wgpu) para aprender o pipeline de vídeo de baixo nível. Três armadilhas recentes decidem o que funciona hoje. A API `mp.solutions`, usada pela maioria dos tutoriais, **foi removida em dezembro de 2025**. O **`mediapipe` 1.0.1 aborta no caminho de CPU do macOS**: fixe a 1.0.0 ou a 0.10.35, ou use o delegate de GPU com imagens SRGBA. E o **OpenGL do macOS está congelado na versão 4.1**.

> **De onde vem cada informação.** Os trechos marcados **[teste local]** foram verificados nesta sessão no seu próprio Mac: Apple M2 Pro, macOS 26.6.2, CPython 3.12.6 arm64, com pacotes instalados via `uv` em ambientes descartáveis. Os benchmarks repetem uma imagem estática de 640×480 em modo VIDEO e medem só a inferência, sem captura de câmera nem desenho. **O FPS real de webcam, de ponta a ponta, não foi medido.** Todo o resto vem de documentação oficial, repositórios, release notes e registros PyPI/npm consultados em 27/09/2026, sem execução local: stack web, Swift/Vision, C++, Rust, frameworks criativos e modelos alternativos. Números que vêm de uma única fonte de terceiros estão sinalizados como tal.

## Quatro pontas de dedo e um modelo do Google explicam os demos virais

Os clipes virais vêm de dois mundos. Artistas e "creative technologists" usam o **TouchDesigner com o plugin MediaPipe de Torin Blankensmith e Dom Scott**. O plugin roda o MediaPipe web dentro de um Chromium embutido e devolve os landmarks por WebSocket. O próprio README avisa que isso impõe **latência mínima de 3 frames e entrada limitada a 720p** ([torinmb/mediapipe-touchdesigner](https://github.com/torinmb/mediapipe-touchdesigner)).

O projeto "Hand-Held Noise Portal" mostra a receita crua. Um Corner Pin TOP fica preso às pontas dos polegares (cantos inferiores) e dos indicadores (cantos superiores) das duas mãos. Dentro do painel, um Lookup TOP com ruído animado recolore cada pixel pelo brilho. A confiança de detecção foi baixada para 0,2 para o painel não "sumir" ([neempata/Noise-Portal-Handtracking-Touchdesigner](https://github.com/neempata/Noise-Portal-Handtracking-Touchdesigner)).

Desenvolvedores chegam ao mesmo resultado em código:

- **Eureka0w0v0/manual-tracking**, em Python puro com MediaPipe e OpenCV, reproduz a "glass box" (um cuboide entre as mãos com um filtro diferente em cada face) e a "folha espelhada". O autor credita o criador "manualtracking / AM" do Douyin e diz ter medido cores e geometria pixel a pixel a partir do vídeo ([Eureka0w0v0/manual-tracking](https://github.com/Eureka0w0v0/manual-tracking)).
- **hand-filter-window** faz a janela entre polegares e indicadores, com filtros térmico, cartoon, bordas, negativo e pop-color ([Ali533-blip/hand-filter-window](https://github.com/Ali533-blip/hand-filter-window)).
- No navegador há dezenas de demos Three.js + MediaPipe, como o **barehands**, com cerca de mil estrelas ([jaredrhod/barehands](https://github.com/jaredrhod/barehands)).

O **Meta Spark foi desligado em 14/01/2025**, e os efeitos de terceiros saíram do Instagram ([Meta Spark](https://spark.meta.com/learn/publishing/spark-ar-review-policies/)). Por isso, os clipes de 2025–2026 são quase certamente gravações de tela de TouchDesigner ou de código próprio, e não filtros do app. Lens Studio e Effect House continuam como as rotas sem código dentro dos apps ([Lens Studio](https://developers.snap.com/lens-studio/features/ar-tracking/hand/hand-tracking-templates/3d-hand-tracking); [Effect House](https://effecthouse.tiktok.com/learn/guides/technical-guides/objects/ar-tracking/3d-hand-tracker)).

Em todos esses casos o motor é o mesmo. O Hand Landmarker combina um detector de palma com um modelo de landmarks. Em modo de vídeo, ele só roda o detector de novo quando perde a mão, e é esse rastreamento que o deixa rápido ([Hand Landmarker](https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker)). Ele entrega dois sistemas de coordenadas, e você vai usar os dois o tempo todo:

- **Landmarks normalizados**: x e y em [0,1] pela largura e altura da imagem; z relativo ao pulso, mais ou menos na mesma escala de x.
- **World landmarks em metros**: origem no centro aproximado da mão, e não na câmera.

A lateralidade (mão esquerda/direita) assume uma imagem espelhada, de selfie ([hands.md legado](https://github.com/google-ai-edge/mediapipe/blob/master/docs/solutions/hands.md)). O Face Landmarker devolve **478 landmarks, 52 blendshapes e uma matriz 4×4** para ancorar efeitos no rosto ([Face Landmarker](https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker)). O Gesture Recognizer classifica sete gestos prontos (Closed_Fist, Open_Palm, Pointing_Up, Thumb_Down, Thumb_Up, Victory, ILoveYou) e aceita gestos treinados por você ([Gesture Recognizer](https://developers.google.com/edge/mediapipe/solutions/vision/gesture_recognizer)).

A única alternativa nativa de nível comparável para mãos é o Apple Vision. Ele também dá 21 pontos por mão, com lateralidade, mas **só em 2D**, e o rosto tem **apenas 76 pontos**, esparso demais para uma malha ([WWDC20 10653](https://developer.apple.com/videos/play/wwdc2020/10653/); [WWDC21 10040](https://developer.apple.com/videos/play/wwdc2021/10040/)). Daí a tese central deste relatório: **escolha a stack pelo que ela te ensina e pela facilidade de renderizar, porque o rastreador vai ser o MediaPipe em quase qualquer caminho.**

## Python, web e nativo usam o mesmo modelo, mas a experiência muda muito

### Python roda duas mãos em 3 a 5 ms no seu M2 Pro, se a versão for a certa

A API clássica `mp.solutions.hands` é a que aparece em quase todo vídeo do YouTube. O suporte a ela acabou em 01/03/2023, e ela **saiu do pacote a partir da versão 0.10.30, em dezembro de 2025**. Um mantenedor escreveu: "We have removed support for MediaPipe Solutions. Please migrate to MediaPipe Tasks" ([issue #6192](https://github.com/google-ai-edge/mediapipe/issues/6192)).

**[teste local]** No 1.0.1, o módulo `mediapipe` expõe apenas `Image`, `ImageFormat` e `tasks`. O `mp.solutions` só existe até a 0.10.21, que está congelada e limitada a CPython ≤3.12.

O código novo usa `mediapipe.tasks.python.vision`, com as classes `HandLandmarker`, `FaceLandmarker`, `GestureRecognizer`, `PoseLandmarker` e `HolisticLandmarker`. Os utilitários de desenho voltaram ao namespace Tasks na 0.10.32 ([release v0.10.32](https://github.com/google-ai-edge/mediapipe/releases/tag/v0.10.32)).

O problema mais sério é recente. O **`mediapipe` 1.0.1, de 14/08/2026**, é a versão que o `pip install` entrega hoje. No macOS, ele aborta com SIGABRT (`Check failed: service_ Service is unavailable`) ao abrir qualquer grafo com o delegate de CPU. A bisseção mostrou a 0.10.35 e a 1.0.0 funcionando e a 1.0.1 quebrada. A correção foi mesclada em 17/09/2026, mas **em 27/09/2026 ainda não havia versão posterior à 1.0.1 no PyPI** ([issue #6356](https://github.com/google-ai-edge/mediapipe/issues/6356); [PyPI mediapipe](https://pypi.org/project/mediapipe/)).

**[teste local]** O crash se repetiu no seu Mac com HandLandmarker, FaceLandmarker e GestureRecognizer, nos modos IMAGE e VIDEO, com entrada SRGB e SRGBA. A saída é o **delegate de GPU (Metal)**, que funciona tanto na 0.10.35 quanto na 1.0.1, **desde que a imagem venha em SRGBA**: na 1.0.1, SRGB com GPU aborta com `unsupported ImageFrame format: 1`.

Os números medidos no seu Mac (média de 200 iterações, 640×480, modo VIDEO, só inferência) mostram o tamanho da diferença:

| Versão | Tarefa | CPU (XNNPACK) | GPU (Metal, SRGBA) |
|---|---|---|---|
| 0.10.35 | HandLandmarker, 2 mãos | 23,9 ms (~42 fps) | 4,25 ms (~235 fps) |
| 0.10.35 | FaceLandmarker | 7,5 ms (~133 fps) | 4,4 ms (~227 fps) |
| 0.10.35 | GestureRecognizer, 2 mãos | 24,2 ms (~41 fps) | 5,0 ms (~201 fps) |
| 1.0.1 | HandLandmarker, 2 mãos | aborta | 3,16 ms (~317 fps) |
| 1.0.1 | FaceLandmarker (blendshapes + matriz) | aborta | 4,79 ms (~209 fps) |
| 1.0.1 | GestureRecognizer, 2 mãos | aborta | 4,96 ms (~202 fps) |

*Fonte: [teste local]. O Google não publica números para Mac; os únicos oficiais são os do Pixel 6, com 17,12 ms em CPU e 12,27 ms em GPU para mãos ([Hand Landmarker](https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker)).*

A leitura prática é esta. Na CPU, os ~24 ms para duas mãos dão conta de uma webcam a 30 fps, mas não a 60. Com GPU, o rastreador deixa de ser gargalo, e o limite passa a ser a captura e a renderização.

O modo de execução também importa. No modo VIDEO, a chamada `detect_for_video` é síncrona e recebe um timestamp crescente. É o padrão mais simples para um demo, porque o resultado pertence exatamente ao frame que você desenha. No LIVE_STREAM, a chamada é assíncrona e **descarta em silêncio os frames que chegam enquanto o modelo está ocupado** ([guia Python](https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker/python)). **[teste local]** De 300 chamadas `detect_async` feitas em 0,69 s, só 116 geraram callback.

O trecho abaixo mostra o contorno do crash. Os nomes da API foram conferidos nesta sessão contra o pacote 1.0.1 instalado, mas o trecho não foi executado com câmera:

```python
import cv2, mediapipe as mp
from mediapipe.tasks.python import BaseOptions, vision

opts = vision.HandLandmarkerOptions(
    base_options=BaseOptions(model_asset_path="hand_landmarker.task",
                             delegate=BaseOptions.Delegate.GPU),  # CPU aborta no 1.0.1/macOS
    running_mode=vision.RunningMode.VIDEO, num_hands=2)
hands = vision.HandLandmarker.create_from_options(opts)
rgba = cv2.cvtColor(cv2.flip(frame, 1), cv2.COLOR_BGR2RGBA)      # GPU exige SRGBA
res = hands.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGBA, data=rgba), ts_ms)
```

O OpenCV cuida da captura, do desenho 2D e dos filtros. A versão **5.0 saiu em 06/06/2026**, com wheels arm64 ([OpenCV 5](https://opencv.org/opencv-5/); [PyPI opencv-python](https://pypi.org/project/opencv-python/)). **[teste local]** O `cv2` 5.0.0 no seu Mac tem o backend AVFoundation e todas as primitivas do efeito: `fillPoly`, `warpPerspective`, `getPerspectiveTransform`, `solvePnP`, `projectPoints`, `applyColorMap` e `FaceDetectorYN`.

Três detalhes do macOS costumam custar horas:

- O app de terminal (Terminal, iTerm, VS Code) precisa de permissão de câmera em Privacidade e Segurança ([opencv-python #291](https://github.com/opencv/opencv-python/issues/291)).
- O `cv2.imshow` precisa rodar na thread principal ([opencv #22602](https://github.com/opencv/opencv/issues/22602)).
- Só pode haver uma variante do OpenCV no ambiente. O `mediapipe` já puxa o `opencv-contrib-python`, então não instale o `opencv-python` junto ([PyPI mediapipe](https://pypi.org/pypi/mediapipe/json)).

Para o 3D, o OpenCV basta para um "falso 3D": você projeta os vértices e pinta as faces em ordem. Mas ele não tem depth buffer, iluminação nem texturas. Para uma GPU de verdade, lembre que o OpenGL do macOS está **congelado na 4.1 desde o Mojave** ([AppleInsider](https://appleinsider.com/articles/18/06/28/why-macos-mojave-requires-metal----and-deprecates-opengl)). **[teste local]** O `moderngl` 5.12 cria no seu Mac um contexto "4.1 Metal – 90.5", e pedir OpenGL 4.5 gera `ValueError`, então qualquer tutorial que exija GL 4.5/4.6 quebra no Mac.

Há três opções, em ordem de preferência:

- **moderngl + glfw** é o caminho mais simples: um quad em tela cheia com a textura da webcam e, por cima, uma malha em perspectiva. Não há wheel para Python 3.14 ([PyPI moderngl](https://pypi.org/project/moderngl/)).
- **pygfx** roda sobre wgpu, direto em Metal (**[teste local]**: o adaptador wgpu reporta Metal no M2 Pro). Ainda é pré-1.0 e o próprio README pede para fixar a versão ([pygfx](https://github.com/pygfx/pygfx)).
- O **pyrender** não tem release desde 2021 e deve ser evitado ([PyPI pyrender](https://pypi.org/project/pyrender/)).

Os demos da comunidade ainda usam PyGame + PyOpenGL de função fixa, como o gist de sherbondy ([gist](https://gist.github.com/sherbondy/58bdd1d8983d9ba96043fea57f9e7429)). Isso serve para ideias, não como arquitetura.

Um aviso sobre o **cvzone**, popular nos cursos do Murtaza's Workshop. A versão 2.0.0, de 08/06/2026, migrou em silêncio para a Tasks API. **[teste local]**, por inspeção do wheel: ele só usa CPU, sem opção de delegate, ignora parâmetros como `detectionCon` e descarta os world landmarks. Na 1.0.1 do macOS, portanto, cai no crash. Além disso, o repositório no GitHub ainda usa `mp.solutions` ([PyPI cvzone](https://pypi.org/project/cvzone/); [GitHub cvzone](https://github.com/cvzone/cvzone)). Use o HandLandmarker direto e copie só os utilitários de que precisar, como `fingersUp` e `findDistance`.

A estrutura de loop recomendada tem duas threads. Uma thread de captura guarda só o frame mais recente, conselho clássico do PyImageSearch, de 2015 ([PyImageSearch](https://pyimagesearch.com/2015/12/21/increasing-webcam-fps-with-python-and-opencv/)). A thread principal faz o resto: espelhar, converter, inferir em modo VIDEO, calcular a geometria, desenhar e chamar `imshow`.

### O navegador ganha em shaders e compartilhamento, mas infere via WebGL2

O pacote `@mediapipe/tasks-vision` chegou à **1.0.0 em 28/07/2026** (hoje está na 1.0.1) e traz as mesmas tarefas do Python ([npm @mediapipe/tasks-vision](https://www.npmjs.com/package/@mediapipe/tasks-vision)). Mas "GPU" na web significa **WebGL2, não WebGPU**: o parâmetro `delegate` só aceita `"CPU"` ou `"GPU"` ([vision.d.ts](https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@1.0.1/vision.d.ts)). A issue que pede WebGPU segue aberta desde janeiro de 2025. Nela, um engenheiro do Google explicou que o suporte a WebGPU está "focused on our LLM Inference API" ([issue #5826](https://github.com/google-ai-edge/mediapipe/issues/5826)). Outra issue mediu **mais de 10 ms em `glReadPixels`** mesmo no backend de CPU ([issue #5377](https://github.com/google-ai-edge/mediapipe/issues/5377)).

A única medição em Mac vem de **uma fonte única de terceiros**: cerca de **20 ms por frame** para mãos num M1 Max com Chrome 148. A reimplementação em WebGPU/ONNX do mesmo autor fica em ~5–8 ms ([Sonified/webgpu-vision](https://github.com/Sonified/webgpu-vision)). Isso sugere 30–50 inferências por segundo, o suficiente para um demo fluido se a inferência rodar num worker e a renderização interpolar entre os resultados.

Essa arquitetura é, aliás, a oficial. A documentação avisa que `detectForVideo` é síncrono e bloqueia a interface, e recomenda web workers ([Face Landmarker web](https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker/web_js)). O repositório oficial **mediapipe-samples-web**, criado em 30/03/2026, segue esse padrão. Ele tem um worker de módulo por tarefa. Um loop `requestAnimationFrame` transfere um `createImageBitmap(video)` para o worker. O worker tenta a GPU e cai sozinho para CPU se ela falhar ([mediapipe-samples-web](https://github.com/google-ai-edge/mediapipe-samples-web); [base-worker.ts](https://github.com/google-ai-edge/mediapipe-samples-web/blob/main/src/workers/base-worker.ts)).

No macOS, quase tudo está disponível nos dois navegadores. O WebGPU chegou ao Safari 26 em 15/09/2025 ([WebKit](https://webkit.org/blog/17333/webkit-features-in-safari-26-0/)), e o `requestVideoFrameCallback` existe desde o Chrome 83 e o Safari 15.4 ([MDN](https://developer.mozilla.org/en-US/docs/Web/API/HTMLVideoElement/requestVideoFrameCallback)). A exceção é o `MediaStreamTrackProcessor`. No Safari ele só existe dentro de um DedicatedWorker; no Chrome, só na Window ([MDN](https://developer.mozilla.org/en-US/docs/Web/API/MediaStreamTrackProcessor); [Mozilla](https://blog.mozilla.org/webrtc/unbundling-mediastreamtrackprocessor-and-videotrackgenerator/)). O caminho portável é mandar ImageBitmaps para o worker.

Na renderização, o padrão é o **Three.js r186** (`three@0.186.1`, de 24/09/2026) ([npm three](https://www.npmjs.com/package/three)). Um detalhe muda o que você deve estudar: o manual ainda chama o `WebGPURenderer` de experimental. Ele **não suporta `ShaderMaterial`, `RawShaderMaterial`, `onBeforeCompile` nem `EffectComposer`**, e o pós-processamento passa por nós TSL e `RenderPipeline` ([manual WebGPURenderer](https://github.com/mrdoob/three.js/blob/dev/manual/pages/webgpurenderer.html)). O `THREE.PostProcessing` está obsoleto desde a r183 ([PostProcessing.js](https://github.com/mrdoob/three.js/blob/dev/src/renderers/common/PostProcessing.js)). A biblioteca pmndrs `postprocessing` 6.39.5 funciona com o `WebGLRenderer`, mas a beta v7 exige three < 0.184 e, portanto, **não funciona com a r186** ([postprocessing releases](https://github.com/pmndrs/postprocessing/releases)).

A conclusão prática: faça o primeiro demo com **`WebGLRenderer` + `ShaderMaterial` em GLSL**, que tem mais tutoriais e itera mais rápido. Migre para `WebGPURenderer` + TSL quando quiser compute shaders. O próprio repositório do Three.js tem exemplos de webcam, de `VideoFrame`, de recorte por stencil e de máscara, nas versões WebGL e WebGPU ([exemplos three.js](https://github.com/mrdoob/three.js/tree/dev/examples)). Para o rosto, a matriz de transformação do Face Landmarker assume uma câmera em perspectiva com **FOV vertical de 63°, near de 1 cm e far de 100 m**, em centímetros. Basta configurar a câmera do Three.js igual ([face_geometry_from_landmarks_graph.cc](https://github.com/google-ai-edge/mediapipe/blob/master/mediapipe/tasks/cc/vision/face_geometry/face_geometry_from_landmarks_graph.cc)). Isso não foi verificado em código rodando.

O atalho criativo **p5.js 2.3.4 + ml5.js 1.4.0** é o jeito mais rápido de rabiscar uma ideia e tem os vídeos didáticos do Coding Train ([Coding Train](https://thecodingtrain.com/tracks/ml5js-beginners-guide/ml5/hand-pose/)). Por padrão, porém, o `ml5.handPose` roda o modelo MediaPipe Hands sobre o runtime do TensorFlow.js, ou então carrega o `@mediapipe/hands` legado. Ele não usa o tasks-vision ([código do ml5 HandPose](https://github.com/ml5js/ml5-next-gen/blob/main/src/HandPose/index.js)). O TF.js está na 4.22.0, de janeiro de 2025 ([npm @tensorflow/tfjs](https://www.npmjs.com/package/@tensorflow/tfjs)). A conclusão de que ele está em modo de manutenção vem do histórico de commits, não de um anúncio oficial.

Três runtimes novos servem para modelos *extras*, como profundidade ou segmentação, e não para mãos:

- **LiteRT.js**, anunciado em 09/07/2026 ([Google Developers Blog](https://developers.googleblog.com/en/litertjs-googles-high-performance-web-ai-inference/)).
- **ONNX Runtime Web 1.30** com WebGPU ([ORT WebGPU](https://onnxruntime.ai/docs/tutorials/web/ep-webgpu.html)). A página ainda diz que o WebGPU do Safari é só Technology Preview, o que ficou desatualizado com o Safari 26.
- **transformers.js v4** ([Hugging Face](https://huggingface.co/blog/transformersjs-v4)).

Usar qualquer um deles para mãos significaria reimplementar o pipeline de múltiplos estágios do MediaPipe.

### Swift, C++ e Rust ensinam o pipeline, mas oferecem menos modelos prontos

**Swift + Vision** é a rota nativa de menor atrito:

- 21 pontos por mão, com confiança por ponto.
- `maximumHandCount` padrão de 2.
- Lateralidade desde 2021.
- Coordenadas normalizadas com origem no canto inferior esquerdo.

A sessão WWDC20 mostra o pipeline completo. Um `AVCaptureVideoDataOutput` alimenta o `VNImageRequestHandler(cmSampleBuffer:)`, que lê as pontas do polegar e do indicador e descarta pontos com confiança ≤0,3. A pinça é detectada por uma distância de ~40 px mais um "contador de evidência" de 3 frames ([WWDC20 10653](https://developer.apple.com/videos/play/wwdc2020/10653/)).

Desde o macOS 15 existe uma API Swift assíncrona nova (`DetectHumanHandPoseRequest`), e a Apple diz que **novos recursos de Vision sairão só em Swift** ([WWDC24 10163](https://developer.apple.com/videos/play/wwdc2024/10163/)). No WWDC25, a Apple trocou o modelo de mão por um menor e mais preciso, cujas **juntas ficam em posições diferentes das do anterior**. Por isso, classificadores treinados no Create ML precisam ser re-treinados ([WWDC25 272](https://developer.apple.com/videos/play/wwdc2025/272/)). Um fórum de outubro de 2025 aponta que não há constante de revisão documentada para esse modelo, e a questão segue sem resposta ([Apple Forums 803595](https://developer.apple.com/forums/thread/803595)). O WWDC26 não mudou nada em mão, rosto ou corpo ([WWDC26 237](https://developer.apple.com/videos/play/wwdc2026/237/)).

Não existe pose 3D de mão no Vision. E o ARKit no Mac não faz rastreamento pela webcam: ele existe só para renderizar para o Vision Pro ([WWDC25 317](https://developer.apple.com/videos/play/wwdc2025/317/)).

Na renderização, o SceneKit foi **soft-deprecated em junho de 2025** em favor do RealityKit ([WWDC25 288](https://developer.apple.com/videos/play/wwdc2025/288/)). O ganho didático está no Metal. O `CVMetalTextureCache` embrulha o `CVPixelBuffer` da câmera, em formato NV12, como `MTLTexture` sem cópia, e você converte YCbCr para RGB num shader ([CVMetalTextureCache](https://developer.apple.com/documentation/corevideo/cvmetaltexturecache-q3j)). A Apple não publica latência do Vision. Dá para chamar o Vision do Python via `pyobjc-framework-Vision`, mas os exemplos que existem são todos em Swift ([PyPI pyobjc-framework-Vision](https://pypi.org/project/pyobjc-framework-Vision/)).

**MediaPipe em C++** é o caminho mais penoso. O build usa Bazel e C++20. O guia de instalação para macOS ainda manda compilar com `MEDIAPIPE_DISABLE_GPU=1`, porque a "desktop GPU is currently not supported" ([guia de instalação](https://developers.google.com/edge/mediapipe/framework/getting_started/install)). Existe uma Tasks C API no repositório ([tasks/c/vision](https://github.com/google-ai-edge/mediapipe/tree/master/mediapipe/tasks/c/vision)), mas o hand landmarker dela não tem GPU, e o pedido para isso segue aberto desde 2024 ([issue #5712](https://github.com/google-ai-edge/mediapipe/issues/5712)).

Há vários sinais de fragilidade:

- No macOS Tahoe, o Bazel 6.5.0 quebrou com `missing LC_UUID` ([homuler #1428](https://github.com/homuler/MediaPipeUnityPlugin/issues/1428)).
- O ofxMediaPipe precisa corrigir um OpenCV 3 fixado num prefixo Homebrew de Intel ([ofxMediaPipe](https://github.com/n1ckfg/ofxMediaPipe)).
- As notas da 1.0.0 dizem "Remove MacOS prebuilts" ([v1.0.0](https://github.com/google-ai-edge/mediapipe/releases/tag/v1.0.0)).

Há uma ironia útil aqui: o wheel Python tem delegate Metal funcional (**[teste local]**), mas o C++ de desktop, segundo a documentação, só usa CPU.

O **OpenCV C++ 5.0** ganhou um motor DNN novo, e a cobertura de operadores ONNX subiu de ~22% para mais de 80%. Ele também tem um modo que delega ao ONNX Runtime (`ENGINE_ORT`) e caminhos de CPU otimizados para Arm via KleidiCV ([CNX Software](https://www.cnx-software.com/2026/06/10/opencv-5-release-new-dnn-engine-with-enhanced-onnx-and-llm-vlm-support-intel-arm-and-risc-v-hardware-optimizations/)). Mas não traz modelo de mão, e ensina só o lado CPU do vídeo.

Em **Rust**, a stack completa existe:

- `nokhwa` 0.10.11: captura via AVFoundation com saída direta para textura wgpu ([nokhwa](https://github.com/l1npengtul/nokhwa)).
- `ort` 2.0: ainda **release candidate** (rc.13). A busca ainda devolve documentação da 1.x, cuja API é diferente ([ort releases](https://github.com/pykeio/ort/releases)).
- `objc2-vision`: só as classes `VN*`, sem a API Swift nova ([docs.rs](https://docs.rs/objc2-vision/latest/objc2_vision/)).
- `nannou` 0.20: reconstruído como plugin do Bevy ([nannou releases](https://github.com/nannou-org/nannou/releases)).

Não há crate de MediaPipe. Você mesmo teria de portar âncoras, NMS, recorte da região de interesse e reprojeção dos landmarks. É a curva mais íngreme, e também a que mais ensina.

Os frameworks criativos escondem justamente o que você quer aprender:

- **openFrameworks** 0.12.1 roda sobre o OpenGL 4.1 ([releases oF](https://github.com/openframeworks/openFrameworks/releases)). O addon ofxMediaPipe tem 1 estrela e ainda não embrulha o rosto.
- **Cinder** lançou a 0.9.3 em novembro de 2025, a primeira versão desde 2020 ([Cinder](https://github.com/cinder/Cinder/releases)).
- **Processing** 4.5.7 é ativo, mas não há biblioteca nativa de MediaPipe mantida para ele.
- **Unity**, com o plugin homuler v0.16.3, suporta arm64 ([homuler releases](https://github.com/homuler/MediaPipeUnityPlugin/releases)).

### Modelos alternativos servem como extensão, não como rastreador principal

O ONNX Runtime 1.30 traz o CoreML Execution Provider nos wheels oficiais de macOS ([ORT CoreML EP](https://onnxruntime.ai/docs/execution-providers/CoreML-ExecutionProvider.html)). **[teste local]** Chamar `get_available_providers()` no seu Mac retorna `CoreMLExecutionProvider`. Já o antigo `onnxruntime-silicon` está parado desde 2024 ([PyPI onnxruntime-silicon](https://pypi.org/project/onnxruntime-silicon/)). Para trazer seu próprio modelo, as opções são estas:

| Modelo | O que entrega | Restrição principal |
|---|---|---|
| **rtmlib** | RTMPose-hand (21 pontos, Apache-2.0); com `device='mps'`, usa o CoreML EP ([rtmlib](https://github.com/Tau-J/rtmlib)) | Precisa de um detector de mão separado |
| **YOLO26-pose** | Pose por keypoints | A Ultralytics não publica pesos pré-treinados para mão; o dataset é CC BY-NC-SA e a biblioteca, AGPL-3.0 ([Ultralytics hand-keypoints](https://docs.ultralytics.com/datasets/pose/hand-keypoints/)) |
| **HaMeR** | Malha 3D de mão | Backbone ViT-H pesado ([HaMeR](https://github.com/geopavlakos/hamer)) |
| **fasterhamer** | Diz rodar ~30 FPS com duas mãos num M4 Air, via Core ML na Neural Engine | Repositório com 0 estrelas e alegação não verificada ([fasterhamer](https://github.com/VimalMollyn/fasterhamer)) |
| **WiLoR** | Reconstrução de mão | O artigo não informa FPS ponta a ponta ([WiLoR](https://arxiv.org/html/2409.12259v2)) |
| **Depth Anything V2 small** | Profundidade da cena, para oclusão; na conversão Core ML da própria Apple, **32,80 ms no M1 Max e 24,58 ms no M3 Max** na Neural Engine ([apple/coreml-depth-anything-v2-small](https://huggingface.co/apple/coreml-depth-anything-v2-small)) | Nenhuma de peso para este uso |

Os modelos de malha dependem do MANO, cuja licença é não comercial. Não existe comparação direta, no mesmo Mac, entre Vision, MediaPipe, YOLO e RTMPose. Qualquer ranking de precisão ou tremor entre eles é qualitativo.

A tabela a seguir resume as stacks. As notas são uma síntese das fontes citadas, não medições:

| Stack | Mãos | Rosto | 3D / render | Curva | No Apple Silicon | Ensina vídeo de baixo nível |
|---|---|---|---|---|---|---|
| Python + MediaPipe Tasks + OpenCV | 21 pts + world métrico + gestos | 478 pts + 52 blendshapes + 4×4 | pseudo-3D no OpenCV; moderngl (GL 4.1) ou pygfx | Baixa | Metal, 3–5 ms/frame **[teste local]** | Baixo a médio (lado CPU) |
| TypeScript + tasks-vision + Three.js | idem | idem | Three.js completo, GLSL/TSL | Baixa a média | WebGL2, ~20 ms/frame (fonte única) | Médio (shaders) |
| p5 + ml5 | MediaPipe Hands legado via TF.js | FaceMesh legado | p5 WEBGL | Muito baixa | sem números | Baixo |
| Swift + AVFoundation + Vision + Metal | 21 pts, só 2D | 76 pts | Metal / RealityKit | Média | nativo, sem números publicados | **Alto** |
| MediaPipe C/C++ (Bazel) | completo | completo | livre | Alta (build) | só CPU no desktop | Médio |
| OpenCV C++ 5 + ONNX | via RTMPose/YOLO | YuNet (5 pts) | solvePnP / pseudo-3D | Média | CPU (KleidiCV) | Médio (lado CPU) |
| Rust: nokhwa + ort + wgpu | via ONNX ou objc2-vision | idem | wgpu sobre Metal | Muito alta | CoreML EP + Metal | **Alto** |
| openFrameworks + ofxMediaPipe | MediaPipe (C API) | não embrulhado | OpenGL 4.1 | Média a alta | CPU | Médio |

## A matemática do efeito se resume a geometria, filtro, suavização e estados

### O retângulo: ordenar quatro pontos e filtrar só dentro

O quadrilátero é `P = [L4, L8, R8, R4]`: polegar esquerdo, indicador esquerdo, indicador direito e polegar direito, convertidos para pixels com `x·W` e `y·H`. Espelhe o frame *antes* da inferência. Assim, a visão de selfie e a lateralidade concordam, porque o MediaPipe assume entrada espelhada ([hands.md](https://github.com/google-ai-edge/mediapipe/blob/master/docs/solutions/hands.md)).

Há duas ordenações úteis, cada uma com seu papel:

- A **semântica** (polegares embaixo, indicadores em cima, como no TouchDesigner) mantém a textura sempre na mesma orientação. Ela também permite que o painel "torça" quando as mãos se cruzam, e a folha espelhada do Eureka explora exatamente isso ([Eureka](https://github.com/Eureka0w0v0/manual-tracking)).
- A **angular**, que ordena por `atan2` em torno do centroide, garante um polígono sem autointerseção para a máscara.

Não confie só em `convexHull`. Quando uma ponta de dedo cai dentro das outras três, ele devolve um triângulo e quebra a homografia de quatro pontos.

Na CPU, a composição segue cinco passos:

1. Recorte o `boundingRect` do quadrilátero.
2. Aplique o filtro só nesse recorte.
3. Rasterize a máscara com `fillConvexPoly`, que é "much faster" que o `fillPoly`. O `fillPoly` só é necessário se o polígono puder se autointerceptar.
4. Suavize a borda da máscara com um blur gaussiano.
5. Misture o recorte filtrado com o original usando a máscara ([OpenCV imgproc.hpp](https://github.com/opencv/opencv/blob/4.x/modules/imgproc/include/opencv2/imgproc.hpp)).

O cardápio de filtros sai quase pronto:

- **Térmico:** `applyColorMap` com INFERNO ou TURBO.
- **Negativo:** `255 − roi`.
- **Pixelado:** reduzir e ampliar com `INTER_NEAREST`.
- **Bordas:** `Canny`.
- **Cartoon:** `bilateralFilter`.

Para colar uma imagem ou um vídeo *dentro* do quadrilátero, use `getPerspectiveTransform`, que exige exatamente quatro pares de pontos, seguido de `warpPerspective`. A inversa "retifica" a região, criando o efeito de zoom através da moldura ([LearnOpenCV homografia](https://learnopencv.com/homography-examples-using-opencv-python-c/)).

Na GPU, o caminho mais curto é desenhar o próprio quadrilátero (quatro vértices em coordenadas normalizadas de tela, sob uma câmera ortográfica). O fragment shader dele amostra a textura da webcam em `gl_FragCoord.xy / resolução`. Só os pixels cobertos pelo quad são afetados, e nenhuma máscara é necessária. Quando o "dentro" precisa mostrar outra cena, como num portal, use stencil. Lembre que o `WebGLRenderer` vem com `stencil: false` por padrão ([WebGLRenderer.js](https://github.com/mrdoob/three.js/blob/dev/src/renderers/WebGLRenderer.js)). Como referência de custo, o pinch-vision relata **2 a 15 ms por efeito em 720p no WebGL**, entre térmico, glitch, ASCII e halftone ([pinch-vision](https://github.com/andres-ferreiro/pinch-vision)).

### O cubo: três dedos viram uma base ortonormal

Com três pontas de dedo A, B e C, o paralelepípedo sai em três passos:

1. Monte a base: `u = normalize(B−A)`, `v = normalize((C−A) − ((C−A)·u)·u)` e `n = u × v`.
2. Gere os oito vértices: `A + a·s·u + b·h·v + c·d·n`, com a, b, c ∈ {0,1}, onde s, h e d são os comprimentos das arestas.
3. Projete cada vértice com `x = fx·X/Z + cx`.

No Three.js, o equivalente é montar uma `Matrix4` com essa base e aplicá-la a um `BoxGeometry` unitário.

O problema difícil é a profundidade. Modelos monoculares "don't directly say anything about the hand's absolute depth relative to the camera" ([Collabora](https://www.collabora.com/news-and-blog/blog/2022/05/31/monado-hand-tracking-hand-waving-our-way-towards-a-first-attempt/)). Há três saídas, em ordem crescente de esforço:

1. **O z normalizado:** serve para saber qual mão está mais perto, não para medir distância.
2. **Semelhança de triângulos:** `Z ≈ f·|W0−W9|world / |P0−P9|px`, com `f = (W/2)/tan(HFOV/2)`. O tutorial da Codrops faz uma variante disso com a distância entre o pulso e o dedo médio ([Codrops 2024](https://tympanus.net/codrops/2024/10/24/creating-a-3d-hand-controller-using-a-webcam-with-mediapipe-and-three-js/)).
3. **`solvePnP` com SQPNP** nas 21 correspondências entre world landmarks e pixels. O gist de sherbondy estima a focal como `0,75·largura`, põe o ponto principal no centro e usa só a translação ([gist sherbondy](https://gist.github.com/sherbondy/58bdd1d8983d9ba96043fea57f9e7429)).

As três herdam a escala de mão que o MediaPipe assume e o seu chute de focal. O Z absoluto pode sair errado por um fator constante, enquanto o movimento relativo é confiável. Até a origem dos world landmarks é ambígua: a documentação atual fala no pulso, a legada no centro da mão ([Hand Landmarker](https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker)).

Por isso os builds virais *constroem* a rigidez em vez de corrigi-la. A glass box do Eureka não prende vértices aos dedos. Nas palavras do autor: "The hands do not pin vertices, they only supply a few low-noise parameters... The cuboid is built in 3D and projected with weak perspective, so rigidity and two-point perspective are constructed rather than corrected" ([Eureka](https://github.com/Eureka0w0v0/manual-tracking)). A lição vale para qualquer stack: prender oito vértices a três pontos ruidosos faz o sólido tremer e girar sozinho.

Para desenhar no OpenCV, use o algoritmo do pintor: ordene as faces pelo Z médio e pinte da mais distante para a mais próxima, com `fillConvexPoly` + `addWeighted`. O sinal do produto vetorial 2D identifica as faces de trás. Cada face visível pode reutilizar o pipeline do retângulo com um filtro próprio, exatamente como a glass box faz. No Three.js, faces transparentes somem porque a ordenação é por objeto, não por triângulo. Para sólidos convexos, a solução é renderizar o mesmo mesh duas vezes, primeiro `BackSide` e depois `FrontSide` ([threejsfundamentals](https://github.com/gfxfundamentals/threejsfundamentals/blob/master/threejs/lessons/threejs-transparency.md)).

### Suavização e máquina de estados fazem o efeito parecer mágico

O filtro **One Euro** (Casiez, Roussel e Vogel, CHI 2012) é o padrão para tremor de landmarks. É um passa-baixa cuja frequência de corte cresce com a velocidade: `fc = fcmin + β·|Ẋ|`. O ajuste tem dois passos:

1. Com β = 0 e a mão parada, ajuste `fcmin` até o tremor sumir.
2. Com a mão se movendo rápido, aumente β até o atraso sumir.

No artigo, `fcmin` = 1 Hz e β = 0,007 "made the lag almost imperceivable", com menos atraso que a média móvel e o Kalman ([Casiez et al.](https://gery.casiez.net/publications/CHI2012-casiez.pdf)). O próprio MediaPipe usa `min_cutoff 0.05, beta 80, derivate_cutoff 1.0` em coordenadas normalizadas para pose ([pose_landmark_filtering.pbtxt](https://github.com/google-ai-edge/mediapipe/blob/master/mediapipe/modules/pose_landmark/pose_landmark_filtering.pbtxt)). A diferença entre os dois β mostra que **o β depende da unidade**: pixels e coordenadas normalizadas diferem por um fator de ~1000.

Três práticas completam a suavização:

- Filtre os cantos derivados (quatro a oito pontos), não os 42 landmarks.
- Identifique cada mão por identidade, e não pela posição na lista, que pode trocar.
- Use o intervalo de tempo real entre frames.

Isso importa porque o atraso destrói a ilusão. Com 75 ms de atraso, o tempo de movimento do mouse subiu 16% no estudo de MacKenzie citado no artigo. A ZoopTools resume: "if the portal lags behind your gesture by even a few frames, the whole illusion falls apart" ([ZoopTools](https://www.zooptools.com/hand-portal-filter)).

Os gestos seguem três regras:

- **Distâncias invariantes à escala.** Divida tudo pelo tamanho da mão `S = |P0 − P9|` (pulso até a base do dedo médio).
- **Histerese.** Use limiares diferentes para entrar e sair de um estado. O pinch-vision fecha a pinça a 0,42·S e abre a 0,55·S ([pinch-vision](https://github.com/andres-ferreiro/pinch-vision)). Outro projeto entra a 25% e sai a 35% ([Sander de Snaijer](https://www.sanderdesnaijer.com/blog/gesture-controls-openlayers-mediapipe)).
- **Tempos.** O mesmo projeto exige 80 ms de gesto sustentado, dá 150 ms de tolerância antes de voltar ao repouso e espera 3 frames estáveis da segunda mão.

Com isso, a máquina de estados natural para o retângulo tem cinco estados:

1. **Repouso.**
2. **Armando:** as duas mãos fazem a pose em "L" por alguns frames.
3. **Ativo:** o painel segue os cantos filtrados.
4. **Travado:** as duas mãos fazem pinça, ou os cantos ficam parados por mais de ~500 ms.
5. **Liberado:** as mãos somem por mais tempo que a tolerância.

Para modos grosseiros, como Open_Palm para resetar ou Victory para trocar de filtro, use o Gesture Recognizer. Um gesto próprio, como a pose em "L", pode ser treinado com o Model Maker. O dataset precisa ter uma classe `none`, e o gesto customizado tem prioridade sobre os prontos ([Model Maker](https://developers.google.com/edge/mediapipe/solutions/customization/gesture_recognizer)). A importância da "sensação" aparece no próprio Eureka, que mantém um script com 27 asserções de *feel* só para o cubo flutuante.

### A malha de rosto é a próxima camada, e só o MediaPipe a entrega densa

Detecção e landmarking resolvem problemas diferentes. A detecção dá uma caixa, o bastante para um adesivo que segue o rosto. O landmarking é necessário para pintura facial, deformações e máscaras. Na malha, os landmarks de cada frame viram vértices, e as coordenadas UV e os triângulos vêm do modelo canônico do MediaPipe ([face_mesh.md](https://github.com/google-ai-edge/mediapipe/blob/master/docs/solutions/face_mesh.md)).

Um tutorial da Codrops de setembro de 2026 detalha a montagem em Three.js ([Codrops 2026](https://tympanus.net/codrops/2026/09/06/building-a-real-time-3d-face-mask-with-mediapipe-threlte-and-three-js/)):

- Usa 880 triângulos, vindos da triangulação do TF.js.
- Usa só os primeiros 468 dos 478 pontos.
- Aloca os buffers uma única vez.
- Reproduz o recorte `object-cover` do CSS e o espelhamento.

As blendshapes (boca aberta, piscada) viram gatilhos com a mesma histerese dos gestos. Para estilizar só o rosto dentro da moldura dos dedos, intercepte a máscara do quadrilátero com o contorno convexo da malha.

## Quinze armadilhas datadas invalidam a maioria dos tutoriais

O ecossistema está numa janela de transição: MediaPipe 1.0, Three.js migrando para WebGPU, Vision passando a ser Swift-only e `ort` ainda em RC. Por isso, a data de um tutorial pesa tanto quanto a qualidade dele. A tabela reúne as armadilhas encontradas, com o que fazer em cada caso:

| Armadilha | Desde | Sintoma | O que fazer |
|---|---|---|---|
| `mp.solutions` removido ([#6192](https://github.com/google-ai-edge/mediapipe/issues/6192); **[teste local]**) | 0.10.30, dez/2025 | `AttributeError: module 'mediapipe' has no attribute 'solutions'` | Usar a Tasks API. Trate como legado qualquer código com `mp.solutions.hands.Hands`, `multi_hand_landmarks` ou `landmark_pb2` |
| Crash de CPU no `mediapipe` 1.0.1 no macOS ([#6356](https://github.com/google-ai-edge/mediapipe/issues/6356); **[teste local]**) | 14/08/2026 | SIGABRT "Service is unavailable" ao criar o landmarker | Fixar a 1.0.0 ou a 0.10.35, ou usar GPU + SRGBA; atualizar quando sair uma versão acima da 1.0.1 |
| GPU exige SRGBA (**[teste local]**) | 1.0.1 | `unsupported ImageFrame format: 1` | Converter com `cv2.COLOR_BGR2RGBA` |
| Exemplo oficial desatualizado ([detect.py](https://github.com/google-ai-edge/mediapipe-samples/blob/main/examples/hand_landmarker/raspberry_pi/detect.py)) | ainda hoje | O script `raspberry_pi` de mãos ainda importa `mp.solutions` | Preferir os notebooks Python atualizados e o mediapipe-samples-web |
| Tutoriais de cvzone 1.x ([GitHub cvzone](https://github.com/cvzone/cvzone)) | 2.0.0, jun/2026 | O GitHub difere do PyPI; a 2.0 só usa CPU | Usar o HandLandmarker diretamente |
| OpenGL 4.1 no macOS ([AppleInsider](https://appleinsider.com/articles/18/06/28/why-macos-mojave-requires-metal----and-deprecates-opengl); **[teste local]**) | macOS 10.14 | Pedir contexto 4.5/4.6 falha | Usar GLSL 330/410, ou Metal/wgpu |
| Docs do MediaPipe mudaram de endereço ([guia](https://developers.google.com/edge/mediapipe/solutions/guide)) | 2026 | Links ai.google.dev redirecionam (301) | Usar developers.google.com/edge/mediapipe |
| `WebGPURenderer` do Three.js ([manual](https://github.com/mrdoob/three.js/blob/dev/manual/pages/webgpurenderer.html)) | r183+ | `ShaderMaterial` e `EffectComposer` não funcionam; `THREE.PostProcessing` está obsoleto | Usar `WebGLRenderer` para GLSL, ou `RenderPipeline` + TSL |
| pmndrs postprocessing v7 beta ([releases](https://github.com/pmndrs/postprocessing/releases)) | fev/2026 | Exige three < 0.184 | Ficar na 6.x com `WebGLRenderer` |
| ml5 e tfjs-models ([ml5 HandPose](https://github.com/ml5js/ml5-next-gen/blob/main/src/HandPose/index.js)) | tfjs 4.22, jan/2025 | Rodam os runtimes MediaPipe legados | Usar só para rascunhos; tasks-vision direto no projeto |
| Novo modelo de mão do Vision ([WWDC25 272](https://developer.apple.com/videos/play/wwdc2025/272/)) | jun/2025 | As juntas mudaram de posição | Re-treinar classificadores do Create ML |
| SceneKit soft-deprecated ([WWDC25 288](https://developer.apple.com/videos/play/wwdc2025/288/)) | jun/2025 | Só recebe correções críticas | Usar RealityKit ou Metal |
| `ort` do Rust ainda em RC ([ort releases](https://github.com/pykeio/ort/releases)) | 2026 | A busca devolve docs da 1.x, com API diferente | Seguir a documentação da 2.0 |
| MediaPipe C++ de desktop ([guia de instalação](https://developers.google.com/edge/mediapipe/framework/getting_started/install)) | doc atual | GPU desktop sem suporte; "Remove MacOS prebuilts" na 1.0.0 | Compilar a C API como dylib, ou usar Python |
| Meta Spark encerrado ([Meta Spark](https://spark.meta.com/learn/publishing/spark-ar-review-policies/)) | 14/01/2025 | Tutoriais de Spark AR ficaram inúteis | Usar Lens Studio ou Effect House se quiser filtro dentro do app |

## Caminho recomendado: protótipo em Python, efeito final no navegador

A ordem proposta segue uma lógica simples. **Python primeiro**, porque é a única stack verificada no seu hardware, porque cada operação de pixel fica explícita em NumPy/OpenCV e porque os repositórios que reproduzem exatamente esses efeitos estão em Python. **Navegador depois**, porque é onde estão os shaders, o 3D maduro do Three.js, a malha de rosto em tempo real e um link que qualquer pessoa abre. **Swift ou Rust por último**, e de forma opcional, porque é onde se aprende de fato o pipeline de baixo nível (buffers de pixel, YCbCr, texturas sem cópia, filas separadas) a um custo maior de iteração.

| Etapa | Stack | O que construir | Referências |
|---|---|---|---|
| 1. Rastreamento (1–2 dias) | Python 3.12 via `uv`; `mediapipe==1.0.0` (ou 0.10.35); OpenCV que vem como dependência | HandLandmarker com duas mãos em modo VIDEO; desenhar os landmarks; medir o FPS real da câmera, que ainda não foi medido | [guia Python](https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker/python); notebooks em [mediapipe-samples](https://github.com/google-ai-edge/mediapipe-samples) |
| 2. Retângulo filtrado | + NumPy | Quadrilátero ordenado, máscara, 3 a 5 filtros, `warpPerspective`, One Euro nos cantos, máquina de estados | [hand-filter-window](https://github.com/Ali533-blip/hand-filter-window); [pinch-vision](https://github.com/andres-ferreiro/pinch-vision); [hand-ar-portal](https://github.com/Bibashsitoula0/hand-ar-portal); [1€](https://gery.casiez.net/1euro/) |
| 3. Cubo | OpenCV (`projectPoints` + algoritmo do pintor); opcionalmente moderngl | Base de Gram–Schmidt, `solvePnP`, cuboide paramétrico em perspectiva fraca | [gist sherbondy](https://gist.github.com/sherbondy/58bdd1d8983d9ba96043fea57f9e7429); [Eureka](https://github.com/Eureka0w0v0/manual-tracking) |
| 4. GPU e web | Vite + TypeScript; `@mediapipe/tasks-vision@1.0.1` num worker; `three@0.186` com `WebGLRenderer` + GLSL | Filtros como fragment shaders; cubo como `Matrix4`; FaceLandmarker com blendshapes e matriz | [mediapipe-samples-web](https://github.com/google-ai-edge/mediapipe-samples-web); [The Book of Shaders](https://thebookofshaders.com/); [Codrops 2026](https://tympanus.net/codrops/2026/09/06/building-a-real-time-3d-face-mask-with-mediapipe-threlte-and-three-js/) |
| 5. Baixo nível (opcional) | Swift + AVFoundation + Vision + Metal, ou Rust (nokhwa + ort + wgpu) | Captura em NV12, `CVMetalTextureCache`, shader YCbCr→RGB, filas separadas de captura, inferência e render | [WWDC20 10653](https://developer.apple.com/videos/play/wwdc2020/10653/); [WWDC24 10163](https://developer.apple.com/videos/play/wwdc2024/10163/) |
| 6. Extensões | ONNX Runtime + CoreML EP | Depth Anything V2 para oclusão; HaMeR/WiLoR para malha de mão | [ORT CoreML EP](https://onnxruntime.ai/docs/execution-providers/CoreML-ExecutionProvider.html); [Depth Anything Core ML](https://huggingface.co/apple/coreml-depth-anything-v2-small) |

As linguagens que valem o investimento são, nesta ordem:

1. **Python com NumPy**, para geometria e prototipagem.
2. **GLSL**, que é a habilidade que atravessa todas as stacks. O mesmo raciocínio de fragment shader vale para WGSL/TSL no navegador, Metal Shading Language no Swift e WGSL no Rust.
3. **TypeScript**, para a versão compartilhável.
4. **Swift ou Rust**, só depois.

Há dois contra-argumentos legítimos. Se você já domina JavaScript, começar direto no navegador é defensável: os modelos são os mesmos, e a pesquisa sobre a stack web conclui que ela basta para um demo a 30–60 fps. Se o objetivo fosse só o visual, e não o código, o TouchDesigner com o plugin do Torin seria o atalho, e a masterclass dele de fevereiro de 2025 mostra o processo ([Derivative](https://derivative.ca/community-post/tutorial/hand-tracking-master-class-touchdesigner-mediapipe/71352)). Como você pediu código, ele serve só como referência visual. Começar por Swift ou C++ não compensa: o Vision não tem world landmarks nem malha densa de rosto, e o MediaPipe C++ custa dias de Bazel para rodar só em CPU.

## Conclusão

Com a GPU do seu Mac, o rastreador deixou de ser o gargalo: 3 a 5 ms por frame sobram diante dos 33 ms de uma webcam a 30 fps. A qualidade percebida de um demo desses passa a depender de três coisas que nenhuma biblioteca entrega pronta. A primeira é a latência de ponta a ponta entre captura e tela. A segunda é o filtro de suavização ajustado às suas unidades. A terceira é uma máquina de estados com histerese e tolerâncias. O fato de um autor manter 27 asserções de *feel* para um único cubo diz onde está o trabalho de verdade. Também muda o que vale estudar: menos APIs de ML, que estão mudando neste exato momento, e mais geometria projetiva, shaders e arquitetura de pipeline, que se transferem entre Python, web, Swift e Rust.

A segunda lição é sobre o 3D. Nenhuma stack que rode numa webcam comum dá profundidade métrica confiável. `solvePnP`, semelhança de triângulos e world landmarks acertam o movimento relativo e erram a distância absoluta por um fator que você não controla. Os efeitos virais contornam isso por design: tiram poucos parâmetros estáveis das mãos e *constroem* um sólido rígido em perspectiva fraca. Projetar o seu cubo assim desde o início, em vez de tentar prender vértices a dedos ruidosos, vai poupar mais tempo do que qualquer escolha de linguagem. Um cuidado final de manutenção: quando sair um `mediapipe` acima de 1.0.1, a correção do crash de CPU já estará incluída, e vale refazer o teste local antes de soltar a versão fixada.
