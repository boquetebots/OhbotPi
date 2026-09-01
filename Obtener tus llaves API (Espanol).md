# Obtener tus llaves API — Azure Speech y (opcional) el cerebro

> La versión en inglés de esta guía es **`Getting your API keys.md`**.

Esta guía te lleva paso a paso a conseguir las llaves que Yobot necesita para
la voz y, si quieres, para la conversación.

**No necesitas saber programar para hacer esto.** Solo sigue los pasos.

---

## ¿Qué son las llaves API y por qué las necesitas?

Una llave API es como una contraseña que le permite a Yobot hablar con un
servicio de afuera.

- **La llave de Azure Speech** — hace que Yobot hable en voz alta
  (texto a voz) y entienda lo que le dices por el micrófono. **Esta es la
  única que de verdad necesitas.**
- **Una llave del cerebro** (OpenAI, Anthropic, Google Gemini, Groq...) —
  **es opcional**. Solo sirve para que Yobot sostenga una conversación. La
  puedes agregar después, cuando quieras, sin volver a hacer nada de lo demás.

> **Sin ninguna llave:** los controles de motores, los deslizadores, el
> selector de LED, el constructor de secuencias y el ajedrez funcionan igual
> de bien. Las llaves solo hacen falta para la voz y para la conversación.

**En resumen: haz la Parte 1 (Azure). La Parte 2 la puedes dejar para otro
día.**

---

## ⚠️ Aviso honesto sobre Azure

El sitio web de Azure de Microsoft está hecho para departamentos de
informática de empresas grandes. **No** es amigable para principiantes. Está
lleno de menús confusos, palabras de oficina y opciones que nunca vas a usar.
No dejes que te intimide — solo tienes que encontrar dos cosas: una **key**
(llave) y una **region** (región). Esta guía te lleva directo a ellas.

---

## Parte 1 — La llave de Azure Speech (la voz)

### Paso 1 — Crea una cuenta gratis en Azure

1. Entra a [https://azure.microsoft.com/free](https://azure.microsoft.com/free)
2. Haz clic en **Start free** (Empezar gratis)
3. Inicia sesión con una cuenta de Microsoft (o crea una — sirve Outlook,
   Hotmail o cualquier cuenta de Microsoft)
4. Te va a pedir una tarjeta de crédito. Azure la exige para verificar tu
   identidad, pero **el nivel gratis no te va a cobrar** a menos que tú mismo
   subas de plan. Un uso ligero de pasatiempo se queda muy por debajo de los
   límites gratuitos.

> **El nivel gratis incluye:** 5 horas de voz a texto y 500,000 caracteres de
> texto a voz por mes. Para un robot de pasatiempo, eso es prácticamente
> ilimitado.

---

### Paso 2 — Crea un recurso de Speech

Aquí es donde Azure se pone confuso. Sigue estos pasos tal cual.

1. Ya con la sesión iniciada, vas a llegar a la página principal del Azure
   Portal, en [https://portal.azure.com](https://portal.azure.com)
   - Se ve abrumadora. Ignora casi todo.

2. En la barra de búsqueda de hasta arriba, escribe **Speech** y presiona
   Enter

3. En los resultados busca **Speech services** (puede decir "Cognitive
   Services" debajo — eso es normal). Haz clic ahí.

4. Haz clic en el botón **+ Create** (Crear) — es el botón azul, arriba a la
   izquierda

5. Vas a ver un formulario. Llénalo así:

   | Campo | Qué poner |
   |-------|--------------|
   | **Subscription** | Déjalo como está (tu suscripción gratis) |
   | **Resource group** | Haz clic en "Create new" y escribe cualquier nombre, por ejemplo `ohbot-keys` |
   | **Region** | Escoge la región más cercana a ti (mira la nota abajo) |
   | **Name** | Escribe cualquier nombre, por ejemplo `ohbot-speech` |
   | **Pricing tier** | Escoge **Free F0** |

   > **La región importa para la velocidad.** Escoge la que quede
   > geográficamente más cerca de donde va a estar tu Pi. Opciones comunes:
   > `East US`, `West Europe`, `Australia East`, `Southeast Asia`. **Anota
   > exactamente cuál escogiste** — la vas a necesitar más adelante.

6. Haz clic en **Review + create**, y después en **Create**

7. Espera unos 30 segundos mientras Azure lo prepara. Luego haz clic en **Go
   to resource** (Ir al recurso).

---

### Paso 3 — Encuentra tu llave y tu región

Ya estás en la página de tu recurso de Speech. Sigue viéndose confusa — aquí
está lo que tienes que buscar:

1. En la barra lateral izquierda busca **Keys and Endpoint** (Llaves y punto
   final) y haz clic
   - Si no lo ves, busca **Resource Management** en el menú de la izquierda y
     ábrelo

2. Vas a ver dos llaves: **KEY 1** y **KEY 2**. Son idénticas — solo
   necesitas una. Haz clic en el ícono de copiar que está junto a **KEY 1**.

3. Pégala en algún lugar seguro (un archivo de texto, una nota en tu
   teléfono — donde no se te vaya a perder).

4. En esa misma página busca el campo **Location/Region**. Va a decir algo
   como `eastus` o `westeurope` — todo en minúsculas y sin espacios. Cópialo
   también.

**Con eso ya terminaste Azure.** Ahora tienes:
- ✅ `AZURE_SPEECH_KEY` — la cadena larga de letras y números de KEY 1
- ✅ `AZURE_SPEECH_REGION` — el código corto de región, como `eastus`

**Si solo quieres que Yobot hable y escuche, aquí puedes parar** y saltar a la
Parte 3.

---

## Parte 2 — Una llave para el cerebro (opcional)

Esta parte es **solo si quieres que Yobot converse contigo**. Si la saltas,
Yobot habla, escucha, mueve la cabeza y juega ajedrez sin ningún problema.

### Paso 1 — Escoge UNO de estos

No los necesitas todos. **Escoge uno solo**, el que te caiga mejor:

| Servicio | Dónde se sacan las llaves | Nota |
|---|---|---|
| **OpenAI** | [platform.openai.com](https://platform.openai.com) | El más conocido; se paga por uso |
| **Anthropic** | [console.anthropic.com](https://console.anthropic.com) | Se paga por uso |
| **Google Gemini** | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) | Tiene un nivel gratis generoso |
| **Groq** | [console.groq.com](https://console.groq.com) | Muy rápido; tiene nivel gratis |
| **Ollama** | Corre en tu propia computadora | **No necesita cuenta ni tarjeta** |

> **Si no quieres dar una tarjeta:** empieza con **Google Gemini** o **Groq**,
> o instala **Ollama** en tu propia computadora, que no necesita cuenta.

En los tres casos el procedimiento es el mismo: creas una cuenta, entras a la
sección de llaves del sitio, creas una llave nueva y la copias. Después le
dices a Yobot cuál escogiste con la variable `LLM_PROVIDER`, y pegas la llave
en la variable que le corresponde.

### Paso 2 — Sácale la llave al que escogiste

Abajo está el ejemplo de OpenAI, porque es el más común. Los otros sitios
funcionan casi igual: busca la sección que diga **API keys** y crea una.

1. Entra a [https://platform.openai.com](https://platform.openai.com)
   - Ojo: esta es la **plataforma para desarrolladores**, no la página normal
     de ChatGPT. Es otro lugar.

2. Haz clic en **Sign up** (Registrarse) y crea una cuenta, o inicia sesión si
   ya tienes una

3. Agrega una forma de pago: tu ícono de cuenta (arriba a la derecha) →
   **Billing** (Facturación) → **Add payment method**. Puedes ponerle un
   **límite mensual de gasto** — con $5 sobra para empezar.

4. En la barra lateral izquierda haz clic en **API keys**, o entra directo a
   [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys)

5. Haz clic en **+ Create new secret key**

6. Ponle un nombre como `ohbot` (es opcional, pero ayuda)

7. Haz clic en **Create secret key**

8. **Copia la llave de una vez** — OpenAI solo te la muestra una vez. Si se te
   pasa, tienes que crear otra.

   La llave empieza con `sk-` seguido de una cadena larga de caracteres.

> **¿Qué tan barato es de verdad?** Una conversación corta típica cuesta una
> fracción de centavo. Tendrías que conversar miles de veces para gastar
> aunque sea $1.

**Con eso ya tienes el cerebro.** Ahora tienes:
- ✅ `OPENAI_API_KEY` — la cadena que empieza con `sk-`
  (o la variable que le toque al servicio que escogiste)

---

## Parte 3 — Poner las llaves en tu Pi

### La forma más fácil: el navegador

**Lo más sencillo es no tocar ningún archivo.** Cuando Yobot ya está
corriendo, abre la página del Launcher en tu navegador y haz clic en el enlace
**Settings & Keys** (Ajustes y llaves): ahí pegas cada llave, la guardas, y
además puedes **probar cada una** para ver si sirve. Hace exactamente lo mismo
que todo lo que sigue en esta parte, pero sin terminal.

Si prefieres hacerlo a mano, o si Yobot todavía no arranca, sigue leyendo.

### Entrar a tu Pi

Necesitas una conexión de terminal a tu Pi. Usa el método que te sirva:

**En una computadora Mac o Linux — usa SSH:**

Abre la aplicación Terminal y escribe:

```bash
ssh YOUR_USERNAME@YOUR.PI.IP.ADDRESS
```

Por ejemplo: `ssh pi@192.168.1.42`

Para averiguar la dirección IP de tu Pi puedes revisar la lista de aparatos de
tu router, o, si tu Pi tiene pantalla conectada, correr `hostname -I` en él.

**En una computadora con Windows — usa PuTTY:**

1. Descarga PuTTY (es gratis) de [https://www.putty.org](https://www.putty.org)
2. Abre PuTTY
3. En el campo **Host Name** escribe la dirección IP de tu Pi (por ejemplo
   `192.168.1.42`)
4. Asegúrate de que **Port** sea `22` y que **Connection type** sea `SSH`
5. Haz clic en **Open**
6. Entra con el usuario y la contraseña de tu Pi cuando te los pida

Ya que estés conectado vas a ver una línea de comandos del Pi. Ahora crea el
archivo `.env`:

```bash
cd ~/Projects/Ohbot
nano .env
```

Escribe (o pega) lo siguiente, cambiando el texto de relleno por tus llaves de
verdad:

```
AZURE_SPEECH_KEY=paste_your_azure_key_here
AZURE_SPEECH_REGION=paste_your_region_here
OPENAI_API_KEY=paste_your_openai_key_here
```

Las dos primeras líneas son la voz, y son las que hacen falta. La tercera es
el cerebro: si todavía no tienes esa llave, simplemente no pongas esa línea.

Guarda y sal de nano: presiona **Ctrl+X**, después **Y**, después **Enter**.

---

## Comprobar que sirve

Después de guardar el archivo `.env`, arranca el servidor de la interfaz:

```bash
cd ~/Projects/Ohbot
source venv/bin/activate
python3 gui_server.py
```

Abre la interfaz en tu navegador. Si las llaves están bien:
- La caja de **Text-to-Speech** debe funcionar — escribe algo y haz clic en
  Speak
- El panel de **AI Chat** debe contestarte cuando le mandes un mensaje (esto
  solo si pusiste la llave del cerebro)

Si algo no funciona, revisa dos veces:
1. Que el archivo `.env` esté en la carpeta correcta (`~/Projects/Ohbot/.env`)
2. Que no haya espacios de más alrededor del signo `=`
3. Que el código de región esté en minúsculas y sin espacios (por ejemplo
   `eastus`, no `East US`)

---

## Cuida tus llaves

- **Nunca compartas tu archivo `.env`** — cualquiera que tenga tus llaves
  puede usar tus cuentas y generarte cobros
- **Nunca pegues tus llaves en un chat, un correo o un documento**
- El archivo `.gitignore` de este proyecto ya protege al `.env` para que no se
  suba a GitHub por accidente
- Si crees que una llave quedó expuesta, entra a Azure (o al servicio del
  cerebro), bórrala, y crea una nueva

---

## Referencia rápida

| Qué necesitas | Dónde se saca | Costo |
|---|---|---|
| `AZURE_SPEECH_KEY` **(necesaria)** | portal.azure.com → tu recurso de Speech → Keys and Endpoint | Hay nivel gratis (5 h de voz a texto + 500K caracteres de texto a voz al mes) |
| `AZURE_SPEECH_REGION` **(necesaria)** | La misma página — el campo Location/Region | — |
| La llave del cerebro *(opcional)* | OpenAI, Anthropic, Google Gemini, Groq — o ninguna, si usas Ollama | Se paga por uso, más o menos $1–3 al mes para pasatiempo; Gemini, Groq y Ollama tienen opción sin costo |
