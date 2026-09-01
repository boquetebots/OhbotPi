# Guía de construcción — Yobot en Raspberry Pi 5

**Clubhouse Rincón · Construye tu propio robot desde cero**

Esta guía te lleva desde una tarjeta SD vacía hasta un robot que mueve la
cabeza, escucha y habla. No necesitas saber Linux. Solo sigue los pasos en
orden y lee lo que aparece en la pantalla.

> **Los comandos están en inglés.** Todo lo que escribes en la terminal y todo
> lo que la computadora te responde está en inglés — así es el sistema. Las
> explicaciones están en español. Copia los comandos exactamente como están,
> incluyendo los guiones y los puntos.

---

## Antes de empezar

### Lo que necesitas en la mesa

| Cosa | Detalle |
|---|---|
| Raspberry Pi 5 | Con su fuente de poder oficial (27W USB-C) |
| Tarjeta microSD | 32 GB o más, y un lector de tarjetas para la computadora |
| Cabeza Ohbot | Con su cable USB |
| Micrófono Neewer USB de solapa | Tiene entrada de micrófono y salida de audífonos |
| Parlante amplificado pequeño | Se conecta al conector de audífonos del Neewer |
| Una computadora | Mac o Windows, en el mismo WiFi que el Pi |
| WiFi del Clubhouse | Nombre de la red y contraseña |

### El nombre de tu robot

Cada Pi necesita un **nombre único** en la red. Ya existe uno llamado
`yobot1`. Los siguientes son:

- `yobot2`
- `yobot3`

**Escoge el tuyo ahora y anótalo aquí:** `yobot____`

Cada vez que veas `yobot2` en esta guía, escribe el tuyo en su lugar.

> **¿Por qué importa?** Si dos Pi tienen el mismo nombre, la red se confunde y
> no puedes conectarte a ninguno de los dos. Es como dos personas con el mismo
> número de cédula.

### Una advertencia sobre el parlante

El conector de audífonos del micrófono Neewer es para **monitoreo** — está
diseñado para audífonos pequeños, no para llenar un salón de sonido. Por eso
necesitas un parlante **amplificado** (uno que tenga su propia batería o
enchufe). Un parlante pasivo no va a sonar.

> **¿Por qué el micrófono da el sonido de salida?** El Raspberry Pi 5 **no
> tiene** conector de audífonos. Raspberry Pi lo eliminó en este modelo. El
> Neewer resuelve las dos cosas con un solo cable USB: entra el micrófono y
> sale el audio.

---

## Parte 1 — Grabar la tarjeta SD

Aquí es donde le pones el nombre al Pi. **Este es el paso más importante de
toda la guía**, porque el nombre se define ahora y cambiarlo después es
complicado.

### 1.1 Instala Raspberry Pi Imager

Descárgalo en tu computadora desde <https://www.raspberrypi.com/software/> e
instálalo.

### 1.2 Mete la tarjeta SD en la computadora

Usa el lector de tarjetas. Si la computadora pregunta si quieres formatearla,
di que **no** — el Imager lo hace solo.

### 1.3 Escoge las tres opciones

Abre Raspberry Pi Imager. Verás tres botones:

1. **Choose device** → `Raspberry Pi 5`
2. **Choose OS** → `Raspberry Pi OS (64-bit)`
   *(el primero de la lista, el de escritorio completo)*
3. **Choose storage** → tu tarjeta SD

> **Cuidado:** asegúrate de que en "Choose storage" salga la tarjeta SD y no el
> disco duro de la computadora. Si escoges mal, borras la computadora. Fíjate
> en el tamaño: la tarjeta dice 32 GB o similar.

### 1.4 Configura antes de grabar — NO te saltes esto

Haz clic en **NEXT**. Aparece una ventana que pregunta
*"Would you like to apply OS customisation settings?"*

Haz clic en **EDIT SETTINGS**.

**Pestaña GENERAL:**

| Campo | Qué escribir |
|---|---|
| Set hostname | `yobot2` ← **tu nombre, sin `.local`** |
| Set username | `yobot` |
| Password | La que te dé Michael (la misma en los tres Pi) |
| Configure wireless LAN → SSID | El nombre del WiFi del Clubhouse |
| Configure wireless LAN → Password | La contraseña del WiFi |
| Wireless LAN country | `PA` |
| Set locale → Time zone | `America/Panama` |
| Set locale → Keyboard layout | `us` |

**Pestaña SERVICES:**

- Marca ✅ **Enable SSH**
- Escoge **Use password authentication**

> **¿Qué es SSH?** Es la forma de escribirle comandos al Pi desde tu
> computadora, sin necesidad de conectarle un monitor y un teclado. Sin esto
> activado no puedes hacer nada.

Haz clic en **SAVE**, luego en **YES** para aplicar la configuración, y otra
vez **YES** para confirmar que quieres borrar la tarjeta.

### 1.5 Espera

El Imager escribe y después verifica. Toma entre 5 y 15 minutos. Cuando diga
**"Write Successful"**, saca la tarjeta.

- [ ] Tarjeta grabada con el nombre `yobot____`

---

## Parte 2 — Primer arranque

### 2.1 Arma el Pi

1. Mete la tarjeta SD en el Raspberry Pi 5 (la ranura está debajo de la placa)
2. Conecta el **cable USB de la cabeza Ohbot** a un puerto USB del Pi
3. Conecta el **micrófono Neewer** a otro puerto USB
4. Conecta el **parlante amplificado** al conector de audífonos del Neewer
5. Conecta la fuente de poder de último

La luz verde va a parpadear mucho durante el primer arranque. Eso es normal.
**Espera 3 minutos completos** antes de intentar conectarte — el primer
arranque hace trabajo extra que solo se hace una vez.

### 2.2 Conéctate desde tu computadora

En tu computadora abre la **Terminal** (en Mac: Aplicaciones → Utilidades →
Terminal. En Windows: busca "Terminal" o "PowerShell").

Escribe esto y presiona Enter:

```
ssh yobot@yobot2.local
```

La primera vez te va a decir algo así:

```
The authenticity of host 'yobot2.local' can't be established.
ED25519 key fingerprint is SHA256:xxxxxxxxxxxx
Are you sure you want to continue connecting (yes/no/[fingerprint])?
```

Escribe `yes` y presiona Enter. Después te pide la contraseña.

> **La contraseña no se ve mientras la escribes.** No aparecen ni asteriscos.
> Es normal en Linux — escríbela completa a ciegas y presiona Enter.

Cuando funcione verás algo como:

```
yobot@yobot2:~ $
```

Eso significa: *estás dentro del Pi*. Todo lo que escribas de ahora en
adelante le habla al Pi, no a tu computadora.

- [ ] Conectado por SSH

### Si no conecta

| Lo que dice | Qué hacer |
|---|---|
| `ssh: Could not resolve hostname` | El Pi no está en la red todavía. Espera 2 minutos más e intenta de nuevo. Revisa que escribiste bien el WiFi en el Imager. |
| `Permission denied` | Contraseña equivocada. Cuidado con las mayúsculas. |
| `REMOTE HOST IDENTIFICATION HAS CHANGED` | Tu computadora recuerda otro Pi con ese nombre. Corre `ssh-keygen -R yobot2.local` y vuelve a intentar. |

---

## Parte 3 — Preparar el sistema

Ahora le instalamos al Pi los programas que Yobot necesita.

### 3.1 Actualiza la lista de programas

```
sudo apt update
```

> **¿Qué es `sudo`?** Significa "hazlo como administrador". Te va a pedir la
> contraseña la primera vez. `apt` es el instalador de programas de Linux.

### 3.2 Instala lo que falta

```
sudo apt install -y espeak-ng git python3-venv
```

Esto instala tres cosas:

- **espeak-ng** — una voz de respaldo, por si Azure no está disponible
- **git** — para bajar el código del proyecto
- **python3-venv** — para crear un espacio aislado de Python

Toma unos minutos.

### 3.3 Revisa que puedes hablarle a la cabeza

El robot se comunica por el cable USB. Tu usuario necesita permiso para usarlo.

```
groups
```

Busca la palabra `dialout` en la respuesta. Si **está**, sigue adelante.

Si **no está**, corre esto:

```
sudo usermod -aG dialout $USER
```

...y después **cierra la sesión y vuelve a entrar** (escribe `exit`, y luego
otra vez `ssh yobot@yobot2.local`). El permiso solo se activa al volver a
entrar.

### 3.4 Confirma que el Pi ve la cabeza Ohbot

```
ls /dev/ttyACM*
```

Debe responder algo como `/dev/ttyACM0`.

Si dice `No such file or directory`, la cabeza no está conectada o el cable
está flojo. Desconéctalo y vuélvelo a conectar.

- [ ] Sistema preparado y la cabeza detectada

---

## Parte 4 — Bajar el proyecto

```
mkdir -p ~/Projects
cd ~/Projects
git clone https://github.com/boquetebots/OhbotPi.git Ohbot
cd Ohbot
```

Línea por línea:

- `mkdir -p ~/Projects` — crea una carpeta llamada Projects
- `cd ~/Projects` — entra a esa carpeta
- `git clone ...` — descarga todo el código de Yobot desde internet
- `cd Ohbot` — entra a la carpeta que se acaba de crear

Para confirmar que llegó todo:

```
ls
```

Debes ver muchos archivos, entre ellos `install.sh`, `launcher_server.py` y
`ohbot_chat.py`.

- [ ] Proyecto descargado

---

## Parte 5 — Instalar Yobot

Este es el paso largo. Corre el instalador:

```
bash install.sh
```

Va paso por paso solo. **Va a hacerte cuatro preguntas.** Estas son las
respuestas:

### Pregunta 1 — "Press Enter to begin"

Presiona **Enter**.

### Pregunta 2 — Las llaves de API (Step 7)

Te va a pedir tres cosas:

```
Paste your OpenAI key (or Enter to skip/keep):
Paste your Azure Speech key (or Enter to skip/keep):
Enter region [default: eastus]:
```

**Presiona Enter en las tres.** No escribas nada.

Va a mostrar dos advertencias amarillas diciendo que sin llaves la voz no va a
funcionar. **Está bien, es lo esperado.** Las llaves se ponen al final, en la
Parte 10.

> **¿Qué son las llaves de API?** Son contraseñas que le dan a Yobot acceso a
> los servicios de voz e inteligencia artificial en internet. Se pagan por
> uso: unos centavos si el robot trabaja un rato al día. Cada quien pone las
> suyas — no vienen dentro de esta descarga, a propósito.

### Pregunta 3 — El sistema de archivos "overlay" (Step 10)

```
Enable overlay filesystem now? (y/N):
```

Escribe **`N`** y presiona Enter.

> **¿Por qué N?** El modo overlay protege la tarjeta SD, pero también hace que
> **todo cambio que hagas se pierda al reiniciar**. Todavía te falta calibrar
> el robot, así que no lo queremos activado ahora. Se activa al final, cuando
> el robot ya quedó como lo quieres.

### Pregunta 4 — "Start the launcher right now?"

Escribe **`y`** y presiona Enter.

### La espera

El paso 6 (`Installing Python packages`) es el más lento — puede tomar de 10 a
25 minutos según cómo esté el internet del Clubhouse. La pantalla se ve
detenida y no pasa nada. **Es normal. No cierres la ventana ni presiones
Ctrl-C.**

Cuando termine verás:

```
  ╔══════════════════════════════════════════════════╗
  ║   ✅  Installation complete!                     ║
  ╚══════════════════════════════════════════════════╝
```

- [ ] Instalación completa

---

## Parte 6 — El micrófono

Ahora revisamos que el Pi encuentre el micrófono Neewer.

### 6.1 Pregúntale a Linux qué micrófonos ve

```
arecord -l
```

La respuesta se ve así (los números pueden ser distintos en tu Pi):

```
**** List of CAPTURE Hardware Devices ****
card 1: Device [USB Audio Device], device 0: USB Audio [USB Audio]
```

**Anota el número de `card`:** ______

Si la lista sale vacía, el Neewer no está conectado. Revísalo.

### 6.2 Deja que Yobot lo busque solo

Yobot tiene un programa que encuentra el micrófono por su **nombre**, no por
su número — porque los números cambian cada vez que reinicias el Pi. Pruébalo:

```
cd ~/Projects/Ohbot
python3 ohbot_mic.py
```

Debe responder algo como:

```
🎤 Microphones found: 1
     card 1: Device [USB Audio] → plughw:1,0
🎤 Auto-detected USB microphone: plughw:1,0
```

**Si dice que encontró el micrófono, ya terminaste con este paso.** No hay
que configurar nada más.

> Esta detección automática existe por una razón: el 10 de agosto de 2026, en
> este mismo Clubhouse, Yobot saludó a la gente y después se quedó mudo. El
> código buscaba la tarjeta número 3 y el micrófono estaba en la 2. No dio
> ningún error — simplemente se quedó esperando para siempre. Ahora busca por
> nombre.

### 6.3 Revisa que el parlante suene

Primero mira qué salidas de audio hay:

```
aplay -l
```

Vas a ver el Neewer y también `vc4hdmi0` y `vc4hdmi1` — esas dos son el HDMI
del monitor, no sirven aquí. Fíjate en el número de `card` del USB (debería
ser el mismo que anotaste arriba).

Ahora prueba el sonido, **cambiando el `1` por tu número de card**:

```
speaker-test -D plughw:1,0 -t wave -c 2 -l 1
```

Debe salir una voz diciendo "front left, front right" por el parlante.
Presiona **Ctrl-C** para detenerlo.

Si no se oye nada, revisa en este orden:

1. ¿El parlante está encendido y tiene batería o corriente?
2. ¿Está conectado al conector de **audífonos** del Neewer, no al de
   micrófono?
3. ¿El volumen del parlante está arriba?
4. Sube el volumen del sistema: `alsamixer` (con `F6` escoges la tarjeta USB,
   flechas ↑↓ para el volumen, `Esc` para salir)
5. ¿Le pusiste el número de card equivocado al comando?

> Recuerda: el parlante tiene que ser **amplificado**. Esa salida del Neewer
> es de monitoreo y no tiene fuerza para mover un parlante pasivo.

- [ ] Micrófono detectado y parlante sonando

---

## Parte 7 — Abrir el Launcher

El Launcher es una página web que corre **dentro del Pi**. Desde ahí manejas
todo el robot sin escribir comandos.

En tu computadora, abre el navegador y ve a:

```
http://yobot2.local:5000
```

*(con tu nombre, y sin olvidar los `:5000` al final)*

Debe aparecer la página del Launcher con botones para escoger qué quieres
correr.

> **Si la página no abre:** vuelve a la Terminal y corre
> `systemctl --user status ohbot-launcher`. Si dice `active (running)`, el
> problema es la red o el nombre. Prueba con el número IP: corre
> `hostname -I` en el Pi y usa ese número, por ejemplo
> `http://192.168.50.132:5000`.

**En esa misma página hay un enlace que dice `⚙ Settings & Keys`**
(Ajustes y llaves). Es la manera fácil de hacer la Parte 10: desde ahí pegas
tu llave de Azure, escoges qué compañía de inteligencia artificial le presta
el cerebro al robot, y hay un botón que prueba cada llave y te dice si sirve.
Todo desde el navegador, sin comandos.

Como cualquiera que esté en el mismo WiFi puede abrir el Launcher, la primera
vez que entres a Settings te va a ofrecer ponerle una contraseña. Mientras no
le pongas una, queda abierto — así una instalación nueva no te deja afuera de
la misma página donde tienes que ponerla.

- [ ] Launcher abierto en el navegador

---

## Parte 8 — Cargar un robot

**Este paso no se puede saltar.** Un Pi recién instalado **no tiene** archivo
de calibración — el archivo con las medidas de los motores no viene incluido
en la descarga, a propósito.

> **¿Por qué a propósito?** Cada cabeza Ohbot es físicamente distinta. Los
> motores no quedan exactamente iguales de una a otra. Si el archivo viniera
> incluido, tu robot movería la boca con las medidas de otro robot y se vería
> raro o se forzarían los motores.

En la página del Launcher, busca la sección que dice
**🤖 Which robot are you using?** — ahí sale una lista con los robots que ya
existen:

| Robot | Quién es |
|---|---|
| `Lester` | |
| `Rubia` | La hermana de Lester — la de `yobot1` |
| `TallMan` | El del Clubhouse |
| `BlueBoy` | |
| `Goldie` | |

**Escoge el que se parezca más a tu cabeza** — pregúntale a Michael cuál — y
presiona **Load calibration**. Eso copia sus medidas al archivo vivo y los
motores empiezan a funcionar.

Arriba te va a decir **"Currently loaded:"** con el nombre del robot que
cargaste.

- [ ] Robot cargado y la cabeza responde

---

## Parte 9 — Calibrar tu robot

Ahora ajustas los motores a **tu** cabeza y le pones su propio nombre.

1. En el Launcher, haz clic en **🔧 Motor Calibration**
2. Ajusta los ocho motores hasta que se vea bien:
   - **HeadTurn** — la cabeza mira al frente
   - **HeadNod** — la cabeza derecha, ni mirando arriba ni abajo
   - **HeadRoll** — la cabeza no está inclinada hacia un lado
   - **EyeTurn** y **EyeTilt** — los ojos al centro
   - **TopLip** y **BottomLip** — la boca cerrada pero sin apretar
   - **LidBlink** — los párpados abiertos
3. Cuando quede bien, guárdalo con un **nombre nuevo** — el nombre de tu robot

> Si necesitas guardar la calibración sin pasar por la página de ajuste, en el
> Launcher hay un botón que dice **💾 Save current calibration as a robot…**

> **Ve despacio con los motores.** Si algo hace un ruido de forcejeo o se
> traba, **detente y devuélvelo**. Los servos son de plástico y se rompen.

> **Regla de oro:** guarda con un nombre **nuevo**. No sobreescribas a Rubia
> ni a TallMan — esos son los robots de otras personas.

- [ ] Robot calibrado y guardado como: ______________

---

## Parte 10 — Poner las llaves

Son dos cuentas, y **solo una hace falta**.

**Microsoft Azure — la voz. Esta sí la necesitas.** Es lo que le da voz al
robot. Sin ella se mueve, pero en silencio. Se saca en
<https://portal.azure.com>: crea un recurso de **Speech**, escoge una región
(`eastus` sirve), y copia la **KEY 1** y el nombre de la región.

**El cerebro — la conversación. Esta es opcional y puede esperar.** Es lo que
hace que Yobot te conteste cuando le hablas. Nada más la usa: ni los motores,
ni la página de control, ni el ajedrez. Escoge **una sola** compañía:

| Compañía | Dónde sacar la llave | Vale saber |
|---|---|---|
| **OpenAI** | platform.openai.com → API keys | La de siempre, la que trae por defecto. |
| **Anthropic** | console.anthropic.com → API keys | Claude. |
| **Google Gemini** | aistudio.google.com/apikey | Tiene plan gratis. |
| **Groq** | console.groq.com → API keys | Corre modelos abiertos en su propio equipo: rápido y muy barato. |
| **Ollama** | no hay que registrarse | Corre en tu propia red. Sin cuenta, sin cobro, y lo que piensa el robot no sale del edificio. |

Copia la llave apenas aparezca — casi todas se enseñan una sola vez.

### La manera fácil: desde el navegador

En la página del Launcher, entra a **`⚙ Settings & Keys`** (Ajustes y llaves),
pega las llaves ahí y presiona el botón que las prueba. Listo. Es lo mismo que
hace el archivo, pero sin comandos y avisándote si algo está mal escrito.

### La otra manera: editando el archivo

```
nano ~/Projects/Ohbot/.env
```

Con estas dos líneas ya tienes un archivo completo que funciona — el robot se
mueve, habla y juega ajedrez:

```
AZURE_SPEECH_KEY=tu llave de Azure
AZURE_SPEECH_REGION=eastus
```

Para prender la conversación son dos líneas más — cuál compañía, y su llave:

```
LLM_PROVIDER=openai
OPENAI_API_KEY=tu llave
```

Cambia el nombre por el que escogiste: `anthropic` con `ANTHROPIC_API_KEY`,
`gemini` con `GEMINI_API_KEY`, `groq` con `GROQ_API_KEY`, u `ollama`, que no
lleva llave. Si dejas `LLM_PROVIDER` afuera, asume OpenAI, como siempre fue.

Guarda con **Ctrl-O**, Enter, y sale con **Ctrl-X**. Después reinicia:

```
systemctl --user restart ohbot-launcher
```

- [ ] Llave de Azure puesta y probada
- [ ] Llave del cerebro puesta, o dejada para después a propósito

---

## Parte 11 — La prueba final

1. En el Launcher, presiona el botón **Greeter Bot**
2. Espera unos 15 segundos — hay una pausa programada mientras arranca
3. Háblale al micrófono

Si te responde con voz y mueve la boca al hablar: **terminaste.** 🎉

### Prueba de reinicio

Lo último: comprueba que el robot arranca solo después de un apagón.

```
sudo reboot
```

Espera 2 minutos y vuelve a abrir `http://yobot2.local:5000`. Si la página
carga sin que nadie haya iniciado sesión en el Pi, quedó bien.

- [ ] Prueba de reinicio pasada

---

## Apéndice D — Agregar el ajedrez

El ajedrez es un segundo proyecto que le presta la voz y los motores a este,
para que Yobot juegue una partida hablando en voz alta. Un Pi normalmente
maneja un robot mientras otra computadora corre el juego, pero un Pi puede
correr todo él solo — y **no necesita pantalla**, porque el tablero es una
página web que abres desde una laptop o una tablet.

Cuando el robot ya salude, es poca cosa:

```
cd ~/Projects
git clone https://github.com/boquetebots/YobotChess.git Chess
cd Chess
bash install.sh
```

Después abre **`EMPIEZA AQUI - Raspberry Pi (Espanol).md`** adentro de esa
carpeta y sigue esa guía. No pide ninguna llave propia: usa la voz de Azure
que pusiste en la Parte 10, y nunca toca la llave de la conversación.

---

## Apéndice A — Cuando algo sale mal

### Yobot saluda y después se queda mudo

Es el micrófono. Corre:

```
cd ~/Projects/Ohbot
python3 ohbot_mic.py
```

Si no encuentra el micrófono, desconecta y reconecta el Neewer y reinicia el
Pi.

### El robot no se mueve / "robot not found"

El cable USB. Desconéctalo, vuelve a conectarlo, y desde el Launcher detén y
vuelve a arrancar lo que estabas usando.

> **Importante:** el Greeter, el GUI y la Calibración **comparten el mismo
> cable USB**, así que solo uno puede correr a la vez. El Launcher se encarga
> de eso, pero si arrancas algo por fuera del Launcher vas a tener conflictos.

### Cambié algo y no se ve ningún cambio

Casi siempre es el navegador mostrando una página vieja guardada en memoria.
Recarga forzando:

- Mac: **Cmd + Shift + R**
- Windows: **Ctrl + Shift + R**

### Una página se ve rara o falta un botón

Fíjate arriba a la derecha — ahí siempre está fija la pastilla del idioma 🌐.
Cualquier cosa que se ponga en esa esquina queda tapada.

### Ver qué está pasando por dentro

```
journalctl --user -u ohbot-launcher -f
```

Muestra en vivo lo que hace el Launcher. **Ctrl-C** para salir.

Cambia `ohbot-launcher` por `ohbot-server` o `ohbot-conversation` para ver los
otros.

### El Pi se quedó congelado

Está protegido: el *watchdog* de hardware lo reinicia solo después de 15
segundos si se congela por completo. Espera medio minuto antes de desconectar
el cable de poder.

---

## Apéndice B — El botón de despertar (opcional)

En el Raspberry Pi 5 el botón físico de despertar **no funciona todavía**.

La librería que lee los botones (`RPi.GPIO`) se instala sin dar error, pero
falla cuando el robot la usa. El código lo detecta, imprime
`GPIO setup failed` y sigue funcionando sin botón. **No es una falla tuya y no
rompe nada.**

Si quieres intentar arreglarlo:

```
sudo apt install -y swig python3-dev
cd ~/Projects/Ohbot
venv/bin/pip uninstall -y RPi.GPIO
venv/bin/pip install rpi-lgpio
```

La librería `lgpio` no tiene versión lista para Python 3.13, así que se tiene
que compilar desde cero — de ahí `swig`. Toma varios minutos. **Consulta con
Michael antes de hacerlo.**

---

## Apéndice C — Comandos útiles

Todos se corren dentro del Pi, después de entrar por SSH.

| Para qué | Comando |
|---|---|
| Entrar al Pi | `ssh yobot@yobot2.local` |
| Salir del Pi | `exit` |
| Ir a la carpeta del proyecto | `cd ~/Projects/Ohbot` |
| Ver si el Launcher está vivo | `systemctl --user status ohbot-launcher` |
| Reiniciar el Launcher | `systemctl --user restart ohbot-launcher` |
| Detener todo | `systemctl --user stop ohbot-launcher ohbot-server ohbot-conversation ohbot-gui` |
| Ver el registro en vivo | `journalctl --user -u ohbot-launcher -f` |
| Ver el número IP del Pi | `hostname -I` |
| Ver los micrófonos | `arecord -l` |
| Ver las salidas de audio | `aplay -l` |
| Probar el micrófono de Yobot | `python3 ohbot_mic.py` |
| Apagar el Pi bien | `sudo shutdown -h now` |
| Reiniciar el Pi | `sudo reboot` |

> **Nunca desconectes el cable de poder sin apagar primero** con
> `sudo shutdown -h now` o con el botón del Launcher. Cortarle la corriente de
> golpe puede dañar la tarjeta SD.

---

## Las cinco partes de Yobot

Para que entiendas qué está corriendo. Cada una es un programa aparte:

| Programa | Qué hace | Puerto |
|---|---|---|
| `ohbot-launcher` | La página principal. Arranca sola al encender. | 5000 |
| `ohbot-gui` | Constructor de secuencias y línea de tiempo | 5001 |
| `ohbot-server` | El cerebro del Greeter | 5002 |
| `ohbot-conversation` | El micrófono, la voz y los motores | — |
| `ohbot-calibration` | Ajuste de motores | 5003 |

Solo el Launcher arranca solo. Los demás los enciendes y apagas desde su
página.

---

*Guía escrita para el Clubhouse Rincón · Raspberry Pi 5 · Raspberry Pi OS
(Trixie) · Python 3.13*
