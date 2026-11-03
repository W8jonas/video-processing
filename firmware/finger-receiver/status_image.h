#pragma once
#include <Arduino.h>

// SVG autocontido, servido diretamente da flash sem filesystem ou CDN.
const char kStatusImage[] PROGMEM = R"SVG(<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 640" role="img" aria-labelledby="title desc">
<title id="title">SmartHome conectado</title>
<desc id="desc">Uma casa conectada por Wi-Fi ao ESP8266. Imagem servida pelo próprio microcontrolador.</desc>
<defs>
  <linearGradient id="bg" x2="1" y2="1"><stop stop-color="#071728"/><stop offset="1" stop-color="#153c42"/></linearGradient>
  <linearGradient id="home" x2="0" y2="1"><stop stop-color="#64f1ba"/><stop offset="1" stop-color="#25bba9"/></linearGradient>
</defs>
<rect width="960" height="640" fill="url(#bg)"/>
<circle cx="745" cy="90" r="250" fill="#61e9b4" opacity=".035"/>
<circle cx="150" cy="570" r="270" fill="#61e9b4" opacity=".035"/>
<rect x="48" y="48" width="864" height="544" rx="30" fill="#0e2533" stroke="#31515a"/>
<g font-family="system-ui,sans-serif">
  <text x="88" y="111" fill="#a6bcc6" font-size="16" letter-spacing="4">SMARTHOME / LAB</text>
  <rect x="734" y="82" width="136" height="36" rx="18" fill="#163f38"/>
  <circle cx="757" cy="100" r="5" fill="#72ffc1"/>
  <text x="773" y="106" fill="#9fffd4" font-size="15">ONLINE</text>
  <text x="88" y="179" fill="#f4fbff" font-size="40" font-weight="700">Uma casa. Muitas possibilidades.</text>
  <text x="88" y="216" fill="#9eb8c6" font-size="19">Essa imagem veio de um ESP8266.</text>
</g>
<g stroke="url(#home)" stroke-width="9" stroke-linecap="round" stroke-linejoin="round" fill="none">
  <path d="M250 380 365 280 480 380"/>
  <path d="M275 363v117h180V363M340 480v-78h50v78"/>
  <path d="M322 296q43-39 86 0M299 268q66-61 132 0" stroke-width="6"/>
</g>
<path d="M504 400h70" fill="none" stroke="#4b858d" stroke-width="3" stroke-dasharray="5 9"/>
<g stroke="#6a94a1" stroke-width="4">
  <path d="M606 324h-20m20 25h-20m20 25h-20m20 25h-20m20 25h-20m20 25h-20m20 25h-20M718 324h20m-20 25h20m-20 25h20m-20 25h20m-20 25h20m-20 25h20m-20 25h20"/>
</g>
<rect x="604" y="306" width="116" height="190" rx="12" fill="#164638" stroke="#5bd4a5" stroke-width="3"/>
<rect x="625" y="340" width="74" height="88" rx="5" fill="#b0c7c7"/>
<path d="M640 320v10h10v-10h10v10h10v-10h15" stroke="#9af5ce" stroke-width="3" fill="none"/>
<rect x="648" y="474" width="28" height="27" rx="3" fill="#627b87"/>
<circle cx="685" cy="449" r="5" fill="#79ffbc"/>
<g font-family="system-ui,sans-serif" text-anchor="middle">
  <text x="662" y="464" fill="#aeecd7" font-size="11">ESP8266</text>
  <text x="480" y="550" fill="#82a9b7" font-size="16" letter-spacing="2">WI-FI · HTTP · OTA</text>
</g>
</svg>)SVG";
