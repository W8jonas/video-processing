# LEDs dos dedos e alimentação do cluster

## Montagem confirmada

Em 02/11/2026, o usuário confirmou troca do quarto LED de D3 para D7 e remoção
do DHT de D2. Configuração local habilitada em `leds_config.h`, ignorado pelo
Git; o exemplo distribuído permanece desabilitado.

| Dedo | Pino | GPIO |
|---|---|---|
| Indicador · 1 | D0 | 16 |
| Médio · 2 | D1 | 5 |
| Anelar · 3 | D2 | 4 |
| Mindinho · 4 | D7 | 13 |

Foi orientado um resistor individual de 470 Ω por LED, ânodo após o resistor
e cátodo em GND. Resistência, polaridade e corrente reais não foram medidas
remotamente. O usuário confirmou as conexões e a liberação de D2.

## Alimentação após ligar o cluster

Consultas SSH com chave conhecida confirmaram pi3, pi4 e pi5 ligados e com
`vcgencmd get_throttled` igual a **0x0**. A busca no journal do kernel do boot
por subtensão, sobrecorrente e avisos de fonte não retornou entradas. O uptime
estava abaixo de um minuto nas consultas iniciais.

No Pi 5, `vcgencmd pmic_read_adc EXT5V_V` indicou inicialmente 5,06252 V.
Oito amostras a intervalos de três segundos (janela de cerca de 21 s) variaram
entre **5,0384 e 5,0518 V**, sempre com `throttled=0x0`.

Nos Pi 3/4, `pmic_read_adc` não está disponível; não houve medição de tensão
de entrada nesses modelos. Segundo a
[documentação oficial](https://www.raspberrypi.com/documentation/computers/os.html),
os bits 0 e 16 de `get_throttled` registram subtensão atual e passada, e o ADC
do PMIC do Pi 5 permite consultar sua entrada EXT5V. O zero observado significa
ausência desses registros neste boot, não prova de inexistência de qualquer
transiente elétrico. Os relógios dos nós ainda diferiam durante a inicialização;
o levantamento usa boot atual, uptime e identidade de boot, não alinhamento de
horários entre nós.

## Firmware e ensaio das saídas

O firmware **WIFI OTA HTTP DEDOS LED V5** foi compilado para
`esp8266:esp8266:nodemcuv2`, core 3.1.2 e Arduino CLI 1.5.1, com saídas habilitadas.
Foram executados 91 testes automatizados, todos aprovados. A atualização OTA
autenticada foi confirmada após reboot; `/health` informou OTA ativo, API 1 e
`finger_leds_enabled=true`.

Com renovação automática pelo cliente Python, os seguintes níveis foram lidos
de volta dos GPIOs por `digitalRead`:

| Dedos solicitados | GPIO16 / GPIO5 / GPIO4 / GPIO13 | Entrada Pi 5 |
|---|---|---|
| 1 | 1 / 0 / 0 / 0 | 5,04912 V |
| 2 | 0 / 1 / 0 / 0 | 5,04778 V |
| 3 | 0 / 0 / 1 / 0 | 5,04778 V |
| 4 | 0 / 0 / 0 / 1 | 5,04912 V |
| 1 + 4 | 1 / 0 / 0 / 1 | 5,05046 V |
| 1 + 2 + 3 + 4 | 1 / 1 / 1 / 1 | 5,03706 V |

Incluindo a amostra anterior e três leituras adicionais com os quatro GPIOs
em HIGH, a entrada do Pi 5 variou entre **5,03706 e 5,05448 V**.
`get_throttled` permaneceu 0x0 e o UUID de boot do Pi 5 não mudou durante o teste.
O estado final foi neutro, com os quatro GPIOs em LOW.

Um ensaio separado enviou `[1,4]` e parou de renovar o estado. Após espera de
2,8 s, o ESP informou `expirado=true`, idade 2.865 ms e os quatro GPIOs em LOW.
Foi enviado um estado neutro explícito ao terminar.

São confirmações de níveis lógicos e da telemetria de alimentação. Não houve
observação óptica dos LEDs nem medição de corrente, do trilho 3,3 V na protoboard
ou de picos rápidos de sobretensão. Esses pontos exigem observação local e, para
medições elétricas, instrumentos apropriados.

## Disponibilidade posterior de Pi 3 e Pi 4

Na conferência final, pi5 permaneceu acessível e voltou a informar
`throttled=0x0`. Pi 3 e Pi 4, que tinham respondido com 0x0 após o boot,
deixaram de responder. Tentativas pelo Mac, por `.local` e pelos IPs reservados
192.168.0.103/pi3 e 192.168.0.101/pi4, falharam. A partir do Pi 5, tanto o TCP/22
quanto o ping desses dois IPs também falharam; a tabela de vizinhos mostrou
ambos como `FAILED`, mantendo roteador e Mac acessíveis.

Isso não identifica a causa como subtensão: não houve acesso aos registros dos
dois nós após a perda de rede. Foi solicitado ao usuário conferir alimentação,
LEDs de energia e cabos de Pi 3/4, ou informar se os desligou de propósito.
Portanto, não declarar o cluster inteiro estável com base apenas na consulta
inicial. Pi 5 e ESP permaneceram operacionais; saídas dos quatro LEDs ficaram
em LOW no término dos testes.

O usuário esclareceu em seguida que desligou Pi 3 e Pi 4 de propósito. A perda
de acesso desses nós ficou explicada; não há diagnóstico pendente de falha de
alimentação deles neste ensaio. O escopo ativo passa a ser Pi 5 + ESP8266 e o
programa de câmera `hand-esp` para testar os quatro LEDs ao vivo.

## Confirmação funcional do usuário

Após o teste com a câmera, o usuário confirmou que o reconhecimento funcionou
e que o ESP8266 acendeu os quatro LEDs conforme os dedos. Essa é uma confirmação
visual/funcional local relatada pelo operador, sem estudo quantitativo de
acurácia ou latência. Ao terminar, solicitou desligar todos os Raspberrys; pi3,
pi4 e pi5 aceitaram o comando e deixaram de responder por SSH.
