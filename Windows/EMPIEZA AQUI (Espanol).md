# Yobot en Windows

> La versión en inglés de esta guía es **`START HERE.md`**, en esta misma carpeta.

Yobot es una cabeza de robot que escucha, piensa y te contesta. Esta guía lo
pone a funcionar en una laptop con Windows.

Necesitas:

- Una laptop con Windows
- Yobot, su fuente de poder y su cable USB
- Internet — la voz y el cerebro de Yobot viven en línea
- Una cuenta gratis de **Microsoft Azure**, para la voz — ve el Paso 4
- Una cuenta con **una** empresa de inteligencia artificial, *solo* si quieres
  que Yobot mantenga una conversación. Varias sirven, y el Paso 4 las lista

Nada de esto necesita el Raspberry Pi, y no necesitas saber nada de código.

---

## Qué es lo que vas a instalar

**Una sola instalación.** Este proyecto es Yobot mismo — los motores, la voz,
la boca que se mueve, y un panel de control que manejas desde un navegador de
internet. Todo lo que sigue instala eso, y es igual para todo el mundo.

Dos cosas se montan encima. Ninguna cambia la instalación:

- **Ajedrez.** Un segundo proyecto que toma prestada la voz y los motores de
  este para que Yobot juegue una partida en voz alta contra un invitado.
  Agrégalo cuando quieras — hay una sección corta cerca del final de esta
  página. No pide ninguna cuenta propia.
- **La conversación.** Yobot escuchando y contestando. El código ya está aquí;
  solo necesita una cuenta de inteligencia artificial para encenderse, y el
  Paso 4 te dice cómo. Puedes agregarla después sin rehacer nada.

**Azure es la única cuenta que de verdad necesitas**, porque Azure es la voz.
Sin ella Yobot igual se mueve — nada más lo hace en silencio.

---

## Paso 1 — Consigue los archivos de Yobot

Hay dos maneras. Cualquiera sirve.

**Desde GitHub** — siempre la versión más nueva:

1. Ve a **https://github.com/boquetebots/OhbotPi**
2. Haz clic en el botón verde **Code** (Código) y luego en **Download ZIP**
   (Descargar ZIP)
3. Busca el ZIP en tus Descargas, haz clic derecho sobre él → **Extract All**
   (Extraer todo)
4. Ponlo en **`C:\Projects\OhbotPi2`** — crea primero la carpeta
   `C:\Projects` si no existe, y después **cámbiale el nombre** a la carpeta
   extraída, de `OhbotPi-main` a `OhbotPi2`

No hace falta ninguna cuenta, y no hay nada que instalar.

> **¿Por qué exactamente en ese lugar?** El proyecto de ajedrez encuentra a
> este buscando en la carpeta de al lado, así que con `C:\Projects\OhbotPi2`
> junto a `C:\Projects\Chess` no hay nada que configurar. Aunque nunca
> agregues el ajedrez, ponerlo ahí no te cuesta nada y te ahorra moverlo
> después.

**Desde el ZIP que te mandó Michael** — descárgalo, haz clic derecho →
**Extract All** (Extraer todo), y pon la carpeta en `C:\Projects\OhbotPi2` de
la misma manera.

> ⚠️ **Extrae el ZIP de verdad.** Windows te deja asomarte adentro de un ZIP
> como si fuera una carpeta, y las cosas funcionan a medias si corres Yobot
> desde ahí. Primero haz clic derecho → **Extract All** (Extraer todo), y
> después trabaja en la carpeta real.

---

## Paso 2 — Instala Python

Yobot está escrito en Python, así que la laptop lo necesita.

Ve a **https://www.python.org/downloads/** y haz clic en el botón amarillo
grande de descarga.

> ⚠️ En la **primera pantalla** del instalador, marca la casilla
> **"Add python.exe to PATH"** antes de hacer clic en Install.
> Es una casilla pequeña, cerca de abajo, y es facilísimo pasarla por alto.
> Sin ella, nada más en esta guía funciona.

Esa es la única decisión en todo el instalador. Todo lo demás, dale siguiente.

---

## Paso 3 — Instala Yobot

Abre la carpeta de Yobot, entra a la carpeta **`Windows`**, y **haz doble clic
en `SETUP.bat`**.

> Todo lo que alguna vez vas a necesitar en Windows para hacerle doble clic
> vive en esa única carpeta. El resto del proyecto lo puedes ignorar.

Se abre una ventana negra e instala todo lo que Yobot necesita. Toma unos
minutos — el paquete de voz es grande. Déjalo terminar.

Cuando acabe te dice si todavía falta algo. Espera que te diga que falta el
`.env` — eso es el Paso 4.

---

## Paso 4 — Consigue tus llaves

La voz de Yobot y su cerebro son servicios en línea. Necesitan tus propias
cuentas — los archivos que descargaste a propósito no traen las llaves de
nadie.

Tienen planes gratis o muy baratos. Usarlo poco cuesta centavos.

**La de Azure sí la necesitas.** Es la voz. Sin ella Yobot se mueve en
silencio, y el ajedrez tampoco tiene con qué hablar.

**El cerebro es opcional, y puede esperar.** Es lo que le permite a Yobot
mantener una conversación. Nada más lo usa — ni los motores, ni el panel de
control, ni el ajedrez.

**Microsoft Azure — la voz y la escucha**

1. Regístrate en **https://azure.microsoft.com/free**
2. En el portal de Azure, crea un recurso de **Speech** (busca "Speech" y
   sigue las indicaciones — el plan gratis está bien)
3. Cuando esté creado, ábrelo y busca **Keys and Endpoint** (Llaves y punto de
   conexión)
4. Copia la **KEY 1** y anota la **Location/Region** (algo como `eastus`)

**El cerebro — la conversación** *(opcional; el que puede esperar)*

Yobot no está amarrado a una sola empresa de inteligencia artificial. Escoge
**una** de estas, consigue una llave con ella, y con eso ya está todo:

| Empresa | De dónde sale la llave | Bueno saber |
|---|---|---|
| **OpenAI** | platform.openai.com → API keys | La opción por defecto, y la que Yobot siempre ha usado. |
| **Anthropic** | console.anthropic.com → API keys | Claude. |
| **Google Gemini** | aistudio.google.com/apikey | Tiene plan gratis. |
| **Groq** | console.groq.com → API keys | Corre modelos abiertos en su propio equipo — rápido y muy barato. |
| **Ollama** | no hay que registrarse en nada | Corre en tu propia computadora o red. Sin cuenta, sin factura, y el pensamiento nunca sale del edificio. |

Escojas la que escojas: copia la llave apenas aparezca — casi todas se
muestran una sola vez — y cuenta con ponerle un poco de crédito a la cuenta.

**Ponlas en el archivo**

En la carpeta **principal** de Yobot — un nivel arriba de `Windows` — hay un
archivo que se llama **`.env.example`**. Haz una copia de él, y cámbiale el
nombre a la copia para que quede exactamente **`.env`** — sin `.example`, sin
`.txt`. Ábrelo en Notepad y llena tus dos valores de Azure:

```
AZURE_SPEECH_KEY=la llave que copiaste de Azure
AZURE_SPEECH_REGION=eastus
```

Guárdalo. **Ese es un archivo completo y funcional.** Con esas dos líneas
Yobot se mueve, habla y juega ajedrez.

**Encender la conversación** son dos líneas más — cuál empresa, y su llave:

```
LLM_PROVIDER=openai
OPENAI_API_KEY=la llave que copiaste
```

Cambia según la que escogiste: `anthropic` con `ANTHROPIC_API_KEY`, `gemini`
con `GEMINI_API_KEY`, `groq` con `GROQ_API_KEY`, u `ollama`, que no necesita
llave del todo. Si dejas `LLM_PROVIDER` por fuera, Yobot asume OpenAI, tal
como siempre lo hizo. `.env.example` las lista todas con su dirección de
internet.

**O sáltate este archivo por completo.** La página del Launcher tiene un
enlace **Settings & Keys** (Ajustes y llaves) que hace todo lo anterior desde
el navegador, y puede probarte cada llave. Está descrito más abajo, en *Cómo
usar a Yobot*. Editar el `.env` a mano sigue funcionando y es como siempre se
ha hecho.

> ⚠️ **Windows esconde las extensiones de los archivos**, y aquí es
> justamente donde eso te muerde. Un archivo que se ve como `.env` puede en
> realidad llamarse `.env.txt`, y entonces Yobot no lo encuentra. En el
> Explorador de archivos activa **View → Show → File name extensions** (Ver →
> Mostrar → Extensiones de nombre de archivo), y después revisa que el nombre
> sea solo `.env`.

Guárdate estas llaves para ti — cualquiera que las tenga puede gastar tu
dinero.

Corre `SETUP.bat` otra vez y ahora debería reportar que sí encontró el `.env`.

---

## Paso 5 — El archivo de ajustes de los motores

Los motores de cada robot son un poco distintos, así que cada uno tiene su
propio archivo de ajustes, terminado en **`.omd`**. Va en la carpeta
**`ohbotData`**, dentro de la carpeta principal de Yobot.

- **Si Michael armó tu robot**, pídele su archivo `.omd` y déjalo ahí
- **Si tu robot nunca ha sido calibrado**, sáltate esto por ahora. Yobot igual
  se mueve, solo que con ajustes genéricos — te lo avisa cuando arranca. Lo
  puedes calibrar después desde la página de Motor Calibration.

---

## Paso 6 — Conecta a Yobot y pruébalo

1. Conecta el cable USB a la laptop
2. Enciende la fuente de poder de Yobot
3. **Haz doble clic en `yobot-test.bat`**

Yobot debería voltear la cabeza, asentir, parpadear, abrir la boca y cambiar
el color de los ojos.

**Si eso funcionó, ya terminaste de instalar.**

Si dice *Robot not found* (Robot no encontrado), ve a Solución de problemas al
final.

---

## Cómo usar a Yobot

**Haz doble clic en `yobot-launcher.bat`.**

Se abre una ventana negra y tu navegador abre una página con botones. Esa
página es el control remoto. No toques la ventana negra — si la cierras,
apagas a Yobot.

La página ofrece tres cosas, y **solo una puede correr a la vez**, porque
todas comparten el único cable USB:

| Botón | Qué hace |
|--------|-------------|
| **Greeter** | La conversación. Yobot escucha, contesta en voz alta y se mueve mientras habla. |
| **Sequence Builder** | Diseña tus propios movimientos y reprodúcelos. |
| **Motor Calibration** | Ajusta con precisión los límites de cada motor. Solo se necesita de vez en cuando. |

Presiona **Stop** (Detener) antes de cambiarte a otro — o simplemente presiona
el que quieres y él se cambia solo.

### La página de ajustes

En esa misma página hay un enlace **`⚙ Settings & Keys`** (Ajustes y llaves),
y es la manera fácil de hacer todo lo del Paso 4. Te deja pegar tu llave de
Azure, escoger cuál empresa de inteligencia artificial usa el cerebro, elegir
un modelo, y presionar un botón que revisa que cada una de verdad responda —
todo desde el navegador, sin Notepad y sin andar buscando extensiones de
archivo escondidas.

Cualquiera en el mismo WiFi puede abrir el Launcher, así que la primera vez
que uses Settings te ofrece ponerle una contraseña. Mientras no le pongas una,
queda sin candado, para que una instalación nueva no te deje por fuera de la
misma página donde tienes que ponerla.

### Hablar con Yobot

Arranca el **Greeter** y se abre una segunda ventana negra. Esa es la ventana
propia de Yobot — muestra lo que escuchó y lo que está diciendo.

Simplemente háblale. Te contesta.

Si nadie habla por un rato, Yobot se queda dormido para ahorrar dinero en el
servicio de voz. Para despertarlo: haz clic en **Wake** (Despertar) en la
página web, o presiona **Enter** en la ventana propia de Yobot.

### Para terminar

Presiona **Stop** (Detener) en la página web, y después cierra las ventanas
negras.

Si una ventana no cierra o algo parece trabado, **haz doble clic en
`yobot-stop.bat`** — apaga cualquier cosa que Yobot haya dejado corriendo.

---

## Los cuatro botones, en corto

Los cuatro están en la carpeta **`Windows`**.

| Haz doble clic en esto | Para hacer esto |
|-------------------|-----------|
| `SETUP.bat` | Instalar Yobot. Una vez, al principio. |
| `yobot-test.bat` | Revisar que el robot se mueve. Cada vez que algo se sienta raro. |
| `yobot-launcher.bat` | **Usar a Yobot.** Este es el de todos los días. |
| `yobot-stop.bat` | Apagar todo si se traba. |

---

## Agregar el ajedrez

El show de ajedrez es un segundo proyecto que toma prestada la voz y los
motores de este. Una vez que `yobot-test.bat` funciona, es un salto corto:

1. Ve a **https://github.com/boquetebots/YobotChess**
2. Botón verde **Code** (Código), luego **Download ZIP** (Descargar ZIP), y
   extrae dentro de `C:\Projects`
3. **Cámbiale el nombre** a la carpeta, de `YobotChess-main` a `Chess`, para
   que te quede `C:\Projects\Chess` junto a `C:\Projects\OhbotPi2`
4. Abre **`START HERE - Windows.md`** que está adentro y sigue esa guía

No pide llaves propias. Usa la voz de Azure que configuraste en el Paso 4, y
nunca toca la llave de la conversación.

---

## Solución de problemas

**"Robot not found" (Robot no encontrado)**

1. Desconecta el cable USB, cuenta hasta cinco, y vuélvelo a conectar
2. Revisa que la fuente de poder de Yobot esté de verdad encendida
3. Prueba `yobot-test.bat` otra vez

¿Sigue trabado? Abre PowerShell en la carpeta `Windows` y corre
`.\yobot.bat ports`. Eso lista lo que la laptop alcanza a ver. Si **no**
aparece nada, a Windows le falta el controlador de la tarjeta del robot — abre
el **Device Manager** (Administrador de dispositivos) y busca un triángulo
amarillo de advertencia. El nombre que está al lado te dice cuál controlador
buscar, normalmente **CH340** o **CP210x**. Eso se instala una sola vez.

**No hay sonido**

Revisa que la laptop no esté en silencio, y que el parlante correcto esté
escogido en **Settings → System → Sound** (Configuración → Sistema → Sonido).
Yobot usa lo que Windows tenga puesto.

Los parlantes Bluetooth funcionan pero se atrasan un poquito, así que los
movimientos de la boca se desfasan de la voz. Un parlante de cable, o el de la
misma laptop, se ve mejor.

**Yobot habla pero no te escucha**

Revisa **Settings → System → Sound → Input** (Configuración → Sistema →
Sonido → Entrada) — habla, y la barra de nivel debería moverse. Después revisa
**Settings → Privacy & security → Microphone** (Configuración → Privacidad y
seguridad → Micrófono) y asegúrate de que las aplicaciones de escritorio
tengan permiso de usarlo.

**Windows pregunta por el firewall la primera vez**

Haz clic en **Allow access** (Permitir acceso). Con redes privadas es
suficiente. La página de control de Yobot funciona como un pequeño sitio web
local, y por eso Windows pregunta.

**"Python is not recognized" (Python no se reconoce)**

Python se instaló sin marcar la casilla de PATH. Vuelve a correr el instalador
de Python, escoge **Modify** (Modificar), y márcala. Después corre `SETUP.bat`
otra vez.

**La primera palabra de cada frase suena cortada**

Ya debería estar resuelto — Yobot agrega un momento de silencio antes de
hablar, porque Windows apaga el parlante cuando está sin uso y se traga la
primera fracción de segundo. Si aun así te pasa en tu laptop, abre el `.env`
en Notepad y agrega esta línea, subiendo el número hasta que se oiga limpio:

```
AUDIO_LEAD_IN_MS=550
```

---

## Una última cosa

Solo una computadora puede manejar a Yobot a la vez — se pelearían por el
cable. Si Yobot normalmente está conectado a otra cosa, detenlo allá primero y
pásate el cable USB.
