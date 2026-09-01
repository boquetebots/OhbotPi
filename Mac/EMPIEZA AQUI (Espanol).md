# Yobot en la Mac

> La versión en inglés de esta guía es **`START HERE.md`**, en esta misma carpeta.

Yobot es una cabeza de robot que escucha, piensa y te contesta. Esta guía lo
pone a funcionar en una Mac.

Necesitas:

- Una Mac
- Yobot, su fuente de poder y su cable USB
- Internet — la voz y el cerebro de Yobot viven en línea
- Una cuenta gratis de **Microsoft Azure**, para la voz — mira el Paso 3
- Una cuenta con **una** empresa de inteligencia artificial, *solo* si quieres
  que Yobot mantenga una conversación. Sirven varias, y el Paso 3 las lista

---

## Lo que estás instalando

**Una sola instalación.** Este proyecto es Yobot mismo — los motores, la voz,
la boca que se mueve, y un panel de control que manejas desde un navegador web.
Todo lo que sigue instala eso, y es igual para todo el mundo.

Dos cosas se montan encima. Ninguna cambia la instalación:

- **Ajedrez.** Un segundo proyecto que toma prestada la voz y los motores de
  este para que Yobot juegue una partida en voz alta contra un invitado.
  Agrégalo cuando quieras — hay una sección corta cerca del final de esta
  página. No pide ninguna cuenta propia.
- **La conversación.** Yobot escuchando y contestando. El código ya está aquí;
  necesita una cuenta de inteligencia artificial para encenderse, y el Paso 3
  te dice cómo. Puedes agregarla después sin repetir nada.

**Azure es la única cuenta que de verdad necesitas**, porque Azure es la voz.
Sin ella Yobot igual se mueve — solo que lo hace en silencio.

---

## Paso 1 — Consigue los archivos de Yobot

Abre la Terminal y pega estas tres líneas:

```
mkdir -p ~/Projects
cd ~/Projects
git clone https://github.com/boquetebots/OhbotPi.git OhbotPi2
```

**¿No tienes git?** Abre <https://github.com/boquetebots/OhbotPi>, usa el botón
verde **Code** (Código) y **Download ZIP** (Descargar ZIP), descomprímelo en
`~/Projects`, y cambia el nombre de la carpeta de `OhbotPi-main` a `OhbotPi2`.

> **¿Por qué justo en ese lugar?** El proyecto de ajedrez encuentra a este
> mirando en la carpeta de al lado, así que tener `~/Projects/OhbotPi2` junto a
> `~/Projects/Chess` significa que no hay nada que configurar. Aunque nunca
> agregues el ajedrez, ponerlo ahí no te cuesta nada y te ahorra mudarlo
> después.

---

## Paso 2 — Preparación de la Mac, una sola vez

**Paso 1 — Crea el entorno de Python (venv) propio de Yobot.** Es una caja
privada solo para los paquetes de Yobot — evita por completo los reclamos de la
Mac sobre "externally-managed-environment". Abre la Terminal y pega estas dos
líneas:

```
python3 -m venv ~/yobot-venv
~/yobot-venv/bin/pip install pyserial lxml httpx flask openai azure-cognitiveservices-speech
```

De ahora en adelante, siempre corre Yobot con `~/yobot-venv/bin/python3` en vez
de `python3` a secas — ese es todo el truco, no hay que "activar" nada. (Los
comandos de abajo ya están escritos así.)

**Paso 2 — Permiso del micrófono.** La primera vez que Yobot escuche, macOS te
va a mostrar un aviso: *"Terminal would like to access the microphone"* (La
Terminal quiere usar el micrófono) — haz clic en **Allow** (Permitir). Si por
accidente le das a **Don't Allow** (No permitir), arréglalo en System Settings →
Privacy & Security → Microphone (Ajustes del sistema → Privacidad y seguridad →
Micrófono) y enciende Terminal.

---

## Paso 3 — Consigue tus llaves

La voz y el cerebro de Yobot son servicios en línea, y los archivos que
descargaste a propósito no traen las llaves de nadie.

**La de Azure sí la necesitas.** Es la voz.

1. Entra a <https://portal.azure.com> y crea una cuenta gratis
2. Busca **Speech** y crea un recurso **Speech** — el nivel gratis sirve
3. Escoge cualquier región (`eastus` está bien) y anótala
4. Abre **Keys and Endpoint** (Llaves y punto de conexión) y copia **KEY 1**

**El cerebro es opcional, y puede esperar.** Es lo que permite que Yobot
mantenga una conversación. Nada más lo usa — ni los motores, ni el panel de
control, ni el ajedrez. Escoge **una** empresa:

| Empresa | De dónde sale la llave | Bueno saberlo |
|---|---|---|
| **OpenAI** | platform.openai.com → API keys | La opción por defecto, y la que Yobot siempre ha usado. |
| **Anthropic** | console.anthropic.com → API keys | Claude. |
| **Google Gemini** | aistudio.google.com/apikey | Tiene nivel gratis. |
| **Groq** | console.groq.com → API keys | Corre modelos abiertos en su propio hardware — rápido y muy barato. |
| **Ollama** | no hay que registrarse en nada | Corre en tu propia Mac o en tu red. Sin cuenta, sin factura. |

**Cómo ponerlas.** En `~/Projects/OhbotPi2` hay un archivo que se llama
`.env.example`. Cópialo a `.env` y ábrelo en TextEdit:

```
cd ~/Projects/OhbotPi2
cp .env.example .env
open -e .env
```

Dos líneas de Azure ya son un archivo completo y funcional — con eso, Yobot se
mueve, habla y juega ajedrez:

```
AZURE_SPEECH_KEY=la llave que copiaste de Azure
AZURE_SPEECH_REGION=eastus
```

Encender la conversación son dos líneas más — cuál empresa, y su llave:

```
LLM_PROVIDER=openai
OPENAI_API_KEY=la llave que copiaste
```

Cambia según la que escogiste: `anthropic` con `ANTHROPIC_API_KEY`, `gemini`
con `GEMINI_API_KEY`, `groq` con `GROQ_API_KEY`, u `ollama`, que no necesita
llave. Si dejas `LLM_PROVIDER` por fuera, Yobot asume OpenAI, igual que siempre.

**O sáltate el archivo por completo** y usa mejor la página de Settings del
Launcher — mira más abajo. Es la forma más fácil, y puede probar cada llave por
ti.

---

## Las páginas web en la Mac

Cada página la sirve su propio programa. Enciende la que quieras, y luego abre
la dirección en el navegador de la Mac. `localhost` solo quiere decir "esta
computadora" — en el Pi usarías la dirección del Pi en su lugar.

| Página | Cómo encenderla | Luego abre |
|------|--------------|-----------|
| **Launcher** (botones para todo lo demás) | `~/yobot-venv/bin/python3 launcher_server.py` | http://localhost:5000 |
| **Sequence Builder** | `~/yobot-venv/bin/python3 gui_server.py` | http://localhost:5001/gui |
| **Timeline** | (el mismo servidor de arriba) | http://localhost:5001/timeline |
| **Calibration** | `~/yobot-venv/bin/python3 calibration_server.py` | http://localhost:5003/calibration |

Córrelos desde la carpeta del proyecto: primero `cd ~/Projects/OhbotPi2`.
Ctrl-C detiene un servidor.

**La página del Launcher es el camino fácil** — enciende solo esa, y sus
botones encienden y apagan las demás por ti.

**También tiene un enlace `⚙ Settings & Keys`** (Ajustes y llaves), que es
donde de verdad pertenecen las llaves del Paso 3. Ahí puedes pegar tu llave de
Azure, escoger cuál empresa de inteligencia artificial usa el cerebro, elegir un
modelo, y apretar un botón que comprueba que cada una contesta de verdad — todo
en el navegador, sin editar archivos. Cualquier persona en el mismo WiFi puede
abrir el Launcher, así que la primera vez que uses Settings te ofrece ponerle una
contraseña; mientras no pongas una, se queda sin llave, para que una instalación
nueva no te deje afuera de la misma página desde donde tienes que ponerla.

Dos diferencias con la versión del Pi:

- **Los botones Shut Down / Restart** (Apagar / Reiniciar) **están escondidos**
  en la Mac (una página web no debería poder apagarte la laptop).
- Encender el **bot de conversación** abre una **ventana nueva de la Terminal**
  para que puedas verlo y apretar Enter para despertarlo. Cierra esa ventana o
  aprieta Ctrl-C dentro de ella para detener el bot.

**Nota sobre los puertos:** la calibración se mudó del 5002 al **5003**. En el
Pi, la calibración y el servidor del cerebro usaban los dos el 5002 y nunca se
dieron cuenta, porque nunca corrían al mismo tiempo. En la Mac sí pueden, así
que ahora tienen puertos separados. Los puertos son: 5000 launcher, 5001
GUI/Timeline, 5002 servidor del cerebro, 5003 calibración.

## Las tres formas de correrlo

```
~/yobot-venv/bin/python3 yobot_mac.py test                     ← solo movimiento, no necesita internet
~/yobot-venv/bin/python3 yobot_mac.py say "Hello from my Mac"  ← prueba de voz y sincronía de labios
~/yobot-venv/bin/python3 yobot_mac.py                          ← el bot de conversación completo
```

Hazlas en ese orden el primer día — cada una prueba un poco más.

En el bot completo: háblale a Yobot normal. Cuando se duerma, **aprieta Enter**
para despertarlo. **Ctrl-C** sale.

## Agregar el ajedrez

El show de ajedrez es un segundo proyecto que toma prestada la voz y los motores
de este para que Yobot juegue una partida en voz alta — contra un invitado, o
contra un segundo robot en otra máquina.

Una vez que `yobot_mac.py test` funcione:

```
cd ~/Projects
git clone https://github.com/boquetebots/YobotChess.git Chess
cd Chess
bash install.sh
```

Después abre **`START HERE - Mac.md`** que está adentro. No pide llaves propias
— usa la voz de Azure del Paso 3, y nunca toca la llave de la conversación.

---

## Solución de problemas

**"Robot not found"** — el mismo viejo amigo, la misma solución: desconecta el
cable USB, espera 5 segundos, vuelve a conectarlo y corre otra vez. Revisa
también que el cable haya entrado en la Mac, no en el Pi.

**No hay sonido** — revisa que la Mac no esté en silencio y que esté escogida la
salida correcta en System Settings → Sound (Ajustes del sistema → Sonido). Yobot
usa el parlante que la Mac tenga por defecto.

**El bot no te escucha** — casi siempre es el permiso del micrófono (mira la
preparación de una sola vez, arriba), o el dispositivo de entrada equivocado en
System Settings → Sound → Input (Ajustes del sistema → Sonido → Entrada).

**"AZURE_SPEECH_KEY not found"** — no hay archivo `.env` donde el programa lo
está buscando. Asegúrate de estar corriendo desde la carpeta del proyecto
(`cd ~/Projects/OhbotPi2`), de que `.env` esté ahí, y de que el nombre sea
exactamente `.env` — el Finder esconde las extensiones, así que un archivo hecho
en TextEdit puede terminar llamándose `.env.txt` sin que te des cuenta. El Paso
3 explica cómo hacerlo.

**El servidor del cerebro no arrancó** — córrelo a mano para ver el error de
verdad: `~/yobot-venv/bin/python3 ohbotchat_server.py`

**Errores de "No module named ..."** — probablemente corriste `python3` a secas
en vez de `~/yobot-venv/bin/python3`. El python del entorno de Python (venv) es
el que tiene todos los paquetes.

---

## Lo que la Mac no hace

- **Arrancar sola al encender.** Eso es cosa del Pi. En la Mac tú enciendes
  Yobot cuando quieras.

Windows también está soportado — su guía está en la carpeta `Windows`.

## Antecedentes — lo que se construyó para la Mac

*Notas del traslado, de agosto de 2026, guardadas como referencia. Nada de aquí
es un paso.*

| Archivo | Qué es |
|------|-----------|
| `yobot_core.py` | **Nuevo.** La librería compartida del robot. Detecta sola si está en Pi / Mac / Windows y escoge el reproductor de audio, el estilo de puerto serial y los ajustes correctos. Todo el código de motores, LED, ojos y sincronía de labios vive aquí ahora. |
| `ohbot_pi.py` | Ahora es un reenviador de 3 líneas hacia yobot_core. Todos los programas que ya existían en el Pi siguen funcionando, sin cambios. |
| `yobot_mac.py` | **Nuevo.** El lanzador de la Mac — modo de prueba, modo de voz, y el bot de conversación completo. |
| `ohbot_azure.py` | Actualizado: usa automáticamente el **micrófono y el parlante por defecto de la Mac**. En el Pi, el micrófono ahora es un ajuste (`AZURE_MIC_DEVICE` en .env) en vez de estar enterrado en el código. |
| `ohbot_chat.py` | Actualizado: en una Mac, **aprieta Enter para despertar** a un Yobot dormido (reemplaza el botón GPIO). El campanazo suena por el reproductor multiplataforma. |
| `ohbotchat_server.py` | Actualizado: carga las llaves de la API desde .env por su cuenta, así que corre a mano en cualquier máquina. |

La Mac y el Pi corren los mismos archivos. La mayoría de la gente guarda una
copia en cada máquina y hace `git pull` para mantenerlas iguales; también se
puede apuntar la Mac a una carpeta del proyecto compartida desde el Pi por la
red, pero en ese caso el Pi tiene que quedarse encendido para que la Mac pueda
leerla.

---

## Mover a Yobot entre un Pi y la Mac

*Solo si tienes los dos. Solo una computadora puede tener el cable del robot.*

1. Detén lo que el Pi esté corriendo, para que suelte el cable. Si el Pi corre
   Yobot como servicio, eso es:
   ```
   ssh <your-user>@<your-pi-address> "sudo systemctl stop ohbot-server ohbot-conversation"
   ```
2. Desconecta el **cable USB de Yobot del Pi** y conéctalo a la **Mac**.
3. Corre la prueba del hardware (la primera vez, o cada vez que algo se sienta
   raro):
   ```
   cd ~/Projects/OhbotPi2 && ~/yobot-venv/bin/python3 yobot_mac.py test
   ```
   Si la cabeza se mueve y los ojos cambian de color = todo bien.

## Devolverle Yobot al Pi

1. Sal del bot en la Mac (Ctrl-C).
2. Vuelve a conectar el cable USB al Pi.
3. Enciende sus servicios otra vez:
   ```
   ssh <your-user>@<your-pi-address> "sudo systemctl start ohbot-server ohbot-conversation"
   ```

---

## Lo que cambió en el Pi

Nada que tengas que hacer — pero dos archivos se actualizaron y se comportan un
poco distinto:

- **`launcher_server.py`** sigue usando los servicios de systemd en el Pi
  exactamente como antes. Revisa al arrancar si los servicios están instalados y
  solo entonces los usa; al encenderse imprime en qué modo está.
- **`calibration_server.py`** ahora corre en el puerto **5003** en vez del 5002
  (el enlace de calibración de la página del Launcher se actualizó para que
  coincida). Su botón "Stop & Exit" (Detener y salir) sigue deteniendo el
  servicio de systemd en el Pi, y en cualquier otro lado simplemente cierra el
  programa.

Si el Pi tiene un servicio de systemd `ohbot-calibration` que trae el puerto
5002 escrito en algún lado, no importa — el puerto vive en el archivo de Python,
no en el servicio.
