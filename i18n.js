/* ===========================================================================
   i18n.js — the one and only place Ohbot's on-screen wording lives.
   ===========================================================================

   WHAT THIS IS (plain English)
   ----------------------------
   Every word you see on the Launcher, the Sequence Builder, the Timeline and
   the Calibration page comes from the two big lists below: one English, one
   Spanish. The pages themselves no longer contain any wording — they contain
   little name tags like "btn.save", and this file swaps in the real words.

   Change a word here and it changes on every page at once.

   HOW A PAGE USES IT
   ------------------
   1. In the page's <head>:      a script tag pointing at /i18n.js
   2. On a piece of fixed text:  <h1 data-i18n="launcher.title">Ohbot Launcher</h1>
      (the English left inside the tag is just a fallback if this file fails
      to load — normally it gets replaced the instant the page opens)
   3. On a tooltip:              data-i18n-title="calib.link.tip"
   4. On grey hint text in a box: data-i18n-placeholder="seq.name.ph"
   5. Inside JavaScript:         toast(t('toast.sent'))
      With a value slotted in:   t('toast.saved', {name: 'Wave Hello'})

   ADDING A NEW WORD LATER
   -----------------------
   Add the same key to BOTH the en and es lists below. If you forget the
   Spanish one, the page quietly falls back to the English rather than
   showing a broken blank — and the browser console logs which key is missing
   so it's easy to find.

   THE LANGUAGE PICKER
   -------------------
   A small 🌐 dropdown is added to the top-right corner of every page
   automatically. The choice is saved in the browser AND posted to the Pi
   (into ohbotData/language.txt) so the Python side can read it later when we
   give Ohbot a Spanish speaking voice.
   =========================================================================== */

(function (global) {
  'use strict';

  // ==========================================================================
  // ENGLISH
  // ==========================================================================
  const EN = {

    // ── Shared across pages ────────────────────────────────────────────────
    'lang.label'            : 'Language',
    'lang.en'               : 'English',
    'lang.es'               : 'Español',

    'motor.HEADNOD'         : 'Head Nod',
    'motor.HEADTURN'        : 'Head Turn',
    'motor.EYETURN'         : 'Eye Turn',
    'motor.LIDBLINK'        : 'Lid / Blink',
    'motor.TOPLIP'          : 'Top Lip',
    'motor.BOTTOMLIP'       : 'Bottom Lip',
    'motor.EYETILT'         : 'Eye Tilt',
    'motor.HEADROLL'        : 'Head Roll',

    'led.off'               : 'Off',
    'led.red'               : 'Red',
    'led.green'             : 'Green',
    'led.blue'              : 'Blue',
    'led.yellow'            : 'Yellow',
    'led.cyan'              : 'Cyan',
    'led.purple'            : 'Purple',
    'led.white'             : 'White',
    'led.iceblue'           : 'Ice Blue',

    'common.loading'        : 'Loading…',
    'common.saving'         : 'Saving…',
    'common.error'          : 'Error',
    'common.noserver'       : 'Could not reach the server',
    'common.noserver.detail': 'Could not reach the server: {msg}',
    'common.speed'          : 'Move Speed',
    'common.livemode'       : 'Live mode — send as you slide',
    'common.eyecolour'      : 'Eye Colour (LED)',
    'common.seqname.ph'     : 'Sequence name…',
    'common.seqdesc.ph'     : 'Description (optional)',
    'common.new'            : '＋ New',
    'common.save'           : '💾 Save',
    'common.capture'        : '📸 Capture Keyframe',

    // ── LAUNCHER PAGE ──────────────────────────────────────────────────────
    'launcher.pagetitle'    : '🤖 Ohbot Launcher',
    'launcher.title'        : 'Ohbot Launcher',
    'launcher.subtitle'     : "Choose what you'd like to do",
    'launcher.running.some' : 'Something is running',
    'launcher.badge.running': 'Running',

    'launcher.greeter.name' : 'Greeter Bot',
    'launcher.greeter.desc' : 'Voice-activated conversation mode. Ohbot listens, talks, and chats with visitors.',
    'launcher.gui.name'     : 'Sequence Builder',
    'launcher.gui.desc'     : 'Web GUI for controlling motors, setting emotions, and building animation sequences.',

    'launcher.stop'         : '⏹ Stop Current Service',
    'launcher.opengui'      : 'Open GUI ↗',
    'launcher.restart'      : '↺ Restart Pi',
    'launcher.shutdown'     : '⏻ Shut Down Pi',

    'launcher.calib'        : '🔧 Motor Calibration',
    'launcher.calib.tip'    : 'Stop the current service first',
    'launcher.calib.failed' : 'Could not start calibration.',

    'launcher.robot.title'  : '🤖 Which robot are you using?',
    'launcher.robot.hint'   : 'Load its calibration here before starting the Greeter or the GUI.<br>Robots are saved by name when you finish a motor calibration.',
    'launcher.robot.hint.none': 'Nothing saved yet. Run <strong>Motor Calibration</strong>, and when you save it will ask for a robot name.<br>That robot will then appear here.',
    'launcher.robot.load'   : 'Load calibration',
    'launcher.robot.savecur': '💾 Save current calibration as a robot…',
    'launcher.robot.none'   : 'No robots saved yet',
    'launcher.robot.readfail': 'Could not read the saved robots.',
    'launcher.robot.active' : 'Currently loaded: <strong>{name}</strong>',
    'launcher.robot.active.none': 'Currently loaded: <strong>—</strong>',
    'launcher.robot.active.unnamed': 'Currently loaded: <strong>—</strong> (the live motor file has not been saved under a robot name yet)',
    'launcher.robot.cal3pt' : '{n} motors 3-point',
    'launcher.robot.cal2pt' : 'older 2-point calibration',
    'launcher.robot.badfile': ' — FILE PROBLEM',
    'launcher.robot.option' : '{name} — saved {saved} ({cal}){bad}',
    'launcher.robot.locked' : 'Can\'t switch robots while the {running} is running — it already has the current robot\'s numbers loaded. Press "Stop Current Service" first.',

    'launcher.save.prompt'  : 'Save the calibration currently in use as a robot.\n\nThis takes the motor numbers the robot is using right now and files them under a name, so you can load them back later.\n\nNothing about the robot changes — it just gets remembered.\n\nRobot name:',
    'launcher.save.noname'  : 'No name typed, so nothing was saved.',
    'launcher.save.exists'  : '"{name}" already has a saved calibration.\n\nReplace it with the one in use right now?\n\n(The old one is kept as a .bak file, so it isn\'t lost.)',
    'launcher.save.nothing' : 'Nothing was saved.',
    'launcher.save.cal3pt'  : ' It has {n} three-point calibrated motors.',
    'launcher.save.cal2pt'  : ' Note: it has no measured centres — the older two-point style.',
    'launcher.save.ok'      : 'Saved as "{name}".{cal}',
    'launcher.save.fail'    : 'Could not save.',

    'launcher.load.note2pt' : '\n\nNote: this one has the older two-point calibration (no measured centres), so it will behave the old way until you re-calibrate it.',
    'launcher.load.confirm' : 'Load {name}\'s calibration?\n\nThis copies its saved numbers over the live motor file, so the Greeter and the GUI will drive {name} from now on.\n\nThe current motor file is backed up first, so this can be undone.{note}',
    'launcher.load.backup'  : ' The previous motor file was kept as {backup}.',
    'launcher.load.ok'      : '{name} is loaded. Start the Greeter or the GUI now and it will use this calibration.{kept}',
    'launcher.load.fail'    : 'Could not load that robot.',

    'launcher.status.greeter': 'Greeter Bot is running',
    'launcher.status.gui'    : 'Sequence Builder is running',
    'launcher.status.calib'  : 'Motor Calibration is running',

    'launcher.switch.confirm': 'Stop the {other} and switch to the {target}?',
    'launcher.stop.confirm'  : 'Stop the current service?',
    'launcher.power.shutdown.confirm': 'Are you sure you want to shut down the Pi?',
    'launcher.power.restart.confirm' : 'Are you sure you want to restart the Pi?',
    'launcher.power.shutdown.title'  : 'Shutting down…',
    'launcher.power.restart.title'   : 'Restarting…',
    'launcher.power.shutdown.msg'    : 'You can safely unplug the power after the light goes out.',
    'launcher.power.shutdown.msg2'   : 'You can safely unplug the power after the lights go out.',
    'launcher.power.restart.msg'     : 'The page will reload when the Pi is back online.',
    'launcher.footer'                : 'Ohbot Web Launcher — ',

    // ── SEQUENCE BUILDER (gui/index.html) ──────────────────────────────────
    'gui.pagetitle'         : '🤖 Ohbot Sequence Builder',
    'gui.title'             : '🤖 Ohbot Sequence Builder',
    'gui.connecting'        : 'Connecting…',
    'gui.badge.demo'        : '✨ DEMO RUNNING',
    'gui.badge.playing'     : '▶ PLAYING',
    'gui.demo.stop'         : '⏹ Stop Demo',
    'gui.demo.start'        : '✨ Show me what you can do!',
    'gui.link.timeline'     : '🎬 Timeline',
    'gui.link.launcher'     : '⬅ Launcher',

    'gui.motorcontrols'     : 'Motor Controls',
    'gui.emotions'          : '🎭 Emotion Presets',
    'gui.emotion.happy'     : '😊 Happy',
    'gui.emotion.sad'       : '😢 Sad',
    'gui.emotion.surprised' : '😮 Surprised',
    'gui.emotion.thinking'  : '🤔 Thinking',
    'gui.emotion.sleeping'  : '😴 Sleeping',

    'gui.speech.title'      : '🔊 Speech (with lip sync)',
    'gui.speech.ph'         : 'Type what Ohbot should say…',
    'gui.speech.say'        : '🔊 Say It Now',
    'gui.speech.clear'      : '✕ Clear',
    'gui.speech.clear.tip'  : 'Clear text',
    'gui.speech.speaking'   : '🎙 Speaking…',

    'gui.sendrobot'         : '📡 Send to Robot',
    'gui.reset'             : '↩ Reset',

    'gui.empty'             : 'No keyframes yet.<br>Use the <strong>motor sliders</strong> on the left to pose Ohbot,<br>then click <strong>📸 Capture Keyframe</strong> to save that pose.<br>Repeat to build a sequence!',

    'gui.play'              : '▶ Play',
    'gui.stop'              : '⏹ Stop',
    'gui.loadsaved'         : '📂 Load saved…',
    'gui.clear'             : '🗑 Clear',

    'gui.chat.title'        : '💬 LLM Chat',
    'gui.chat.greeting'     : 'Hi! I\'m Ohbot 🤖 Type a message and I\'ll respond — check "Speak" to hear me say it!',
    'gui.chat.ph'           : 'Ask Ohbot something…',
    'gui.chat.speak'        : '🔊 Speak',
    'gui.chat.send'         : 'Send',
    'gui.chat.clear'        : '↺ Clear',
    'gui.chat.clear.tip'    : 'Clear conversation',
    'gui.chat.cleared'      : 'Conversation cleared — let\'s start fresh! 🤖',
    'gui.chat.thinking'     : 'Thinking…',
    'gui.chat.toast.cleared': 'Chat cleared',
    'gui.chat.switched'     : 'Personality switched to {name}! 🎭',
    'gui.chat.personality.tip' : 'Ohbot\'s personality',
    'gui.pers.friendly'     : '😊 Friendly',
    'gui.pers.comedian'     : '😄 Comedian',
    'gui.pers.pirate'       : '🏴‍☠️ Pirate',
    'gui.pers.professor'    : '🎓 Grumpy Prof',
    'gui.pers.shy'          : '😳 Shy',
    'gui.pers.friendly.long' : '😊 Friendly Robot',
    'gui.pers.comedian.long' : '😄 Comedian',
    'gui.pers.pirate.long'   : '🏴‍☠️ Pirate',
    'gui.pers.professor.long': '🎓 Grumpy Professor',
    'gui.pers.shy.long'      : '😳 Shy Robot',
    'gui.chat.persfail'     : 'Could not change personality',

    'gui.kf.speed.tip'      : 'Native Ohbot ramp speed for this keyframe\'s move (1=slow/smooth, 10=fast)',
    'gui.kf.prewait.tip'    : 'Pre-wait: seconds to hold after THIS move is sent before the NEXT keyframe\'s move is sent. Tune by watching the robot — this should cover this move\'s real travel time plus any extra pause you want.',
    'gui.kf.label.ph'       : 'Label…',
    'gui.kf.label.tip'      : 'Optional label for this keyframe',
    'gui.kf.up.tip'         : 'Move earlier in the sequence',
    'gui.kf.down.tip'       : 'Move later in the sequence',
    'gui.kf.preview.tip'    : 'Preview this pose on robot',
    'gui.kf.delete.tip'     : 'Delete this keyframe',
    'gui.kf.speech.ph'      : 'What Ohbot says at this moment… (leave blank for silence)',

    'gui.toast.sent'        : 'Sent to robot ✓',
    'gui.toast.reset'       : 'Reset to neutral ✓',
    'gui.toast.resetfail'   : 'Reset failed',
    'gui.toast.preview'     : 'Previewing frame {id} ✓',
    'gui.toast.previewfail' : 'Preview failed',
    'gui.toast.captured'    : 'Keyframe {id} captured (#{count} in sequence){speech}',
    'gui.toast.cleared'     : 'Timeline cleared',
    'gui.toast.newseq'      : 'New sequence started',
    'gui.toast.nothingplay' : 'Nothing to play — capture some keyframes first!',
    'gui.toast.playing'     : '▶ Playing…',
    'gui.toast.playfail'    : 'Playback failed',
    'gui.toast.stopped'     : '⏹ Stopped',
    'gui.toast.needname'    : 'Give the sequence a name first!',
    'gui.toast.nokf'        : 'No keyframes to save!',
    'gui.toast.saved'       : '💾 Saved as "{name}" ✓',
    'gui.toast.savefail'    : 'Save failed',
    'gui.toast.noserver'    : 'Could not reach server',
    'gui.toast.loadedold'   : 'Loaded "{name}" — old-format timing reset to defaults (speed {speed}, {wait}s wait). Re-tune each keyframe as needed.',
    'gui.toast.loaded'      : 'Loaded "{name}" ({count} frames) ✓',
    'gui.toast.loadfail'    : 'Load failed',
    'gui.toast.needspeech'  : 'Type something for Ohbot to say first!',
    'gui.toast.speaking'    : '🔊 Speaking…',
    'gui.toast.speechfail'  : 'Speech failed',
    'gui.toast.playdone'    : 'Playback complete ✓',
    'gui.toast.demodone'    : '✨ Demo complete!',
    'gui.toast.demostart'   : '✨ Demo starting…',
    'gui.toast.demofail'    : 'Could not start demo',
    'gui.toast.demostopped' : 'Demo stopped',
    'gui.toast.emotionfail' : 'Emotion failed',

    'gui.confirm.clear'     : 'Clear all keyframes? This cannot be undone.',
    'gui.confirm.new'       : 'Start a new sequence? Unsaved keyframes will be lost.',
    'gui.confirm.load'      : 'Load a saved sequence? Unsaved changes will be lost.',
    'gui.confirm.overwrite' : 'A sequence named "{name}" already exists ({count} keyframes).\n\nOverwrite it?',

    'gui.status.connected'  : 'Ohbot connected',
    'gui.status.notfound'   : 'Robot not found (sliders still work)',
    'gui.status.unreachable': 'Server unreachable',
    'gui.seq.frames'        : '{name} ({count} frames)',
    'gui.speechnote'        : ' + 🔊 speech',

    // ── TIMELINE (gui/timeline.html) ───────────────────────────────────────
    'tl.pagetitle'          : '🎬 Ohbot Timeline',
    'tl.title'              : '🎬 Ohbot Timeline',
    'tl.phase'              : 'PHASE 2B — LIVE CAPTURE',
    'tl.checking'           : 'Checking robot…',
    'tl.badge.playing'      : '▶ PLAYING',
    'tl.pickone'            : 'Pick a sequence on the left to preview it.',
    'tl.link.builder'       : '← Sequence Builder',

    'tl.saved'              : 'Saved Sequences',
    'tl.leftHint'           : 'Click a sequence to open it (replaces what\'s on the timeline now). Use <b>Insert at playhead</b> to splice its keyframes into what you\'re currently building instead.',
    'tl.empty'              : 'Select a saved sequence on the left, or pose Ohbot with the<br>panel on the right and click <strong>📸 Capture Keyframe</strong> to start a new one.',
    'tl.hintbar'            : 'Click the ruler or track to move the playhead — new keyframes (and inserted sequences) land there. Press spacebar to play from there (the playhead travels along as it plays), press again to stop. Hover a clip to delete it.',

    'tl.pose'               : 'Pose & Capture',
    'tl.speech'             : 'Speech',
    'tl.speech.ph'          : 'What Ohbot says at this keyframe…',
    'tl.speech.hint'        : 'Saved as text with the keyframe — not spoken during playback here (use the Sequence Builder for that). The button above lets you hear it now.',
    'tl.speech.preview'     : '🔊 Hear This Line',
    'tl.speech.preview.tip' : 'Say this line now, in the language selected top-right. Nothing is saved and no keyframe changes.',
    'tl.toast.nospeech'     : 'Nothing typed in the Speech box yet',
    'tl.toast.speaking'     : '🗣 Speaking…',
    'tl.toast.speakfail'    : 'Could not speak — is the robot connected?',
    'tl.sendpose'           : '📡 Send Pose to Robot',
    'tl.resetpose'          : '↩ Reset Pose',

    'tl.clip.delete.tip'    : 'Delete this keyframe',
    'tl.clip.overflow.tip'  : 'Estimated move may take longer than this keyframe\'s pre-wait',
    'tl.insert'             : '⬇ Insert at playhead',
    'tl.insert.tip'         : 'Insert this sequence\'s keyframes into the timeline you\'re building, at the playhead — doesn\'t replace what\'s already there',

    'tl.nosaved'            : 'No saved sequences found yet. Build one in the Sequence Builder first.',
    'tl.listfail'           : 'Couldn\'t load sequence list: {msg}',
    'tl.loadfail'           : 'Error loading sequence: {msg}',
    'tl.nokf'               : 'This sequence has no keyframes yet.',
    'tl.newseq'             : 'New sequence — not saved yet.',

    'tl.toast.playdone'     : 'Playback finished',
    'tl.toast.pickfirst'    : 'Pick a sequence first.',
    'tl.toast.playfail'     : 'Couldn\'t start playback: {msg}',
    'tl.toast.unknownerr'   : 'unknown error',
    'tl.toast.noserver'     : 'Couldn\'t reach the timeline server: {msg}',
    'tl.toast.posesent'     : 'Pose sent to robot',
    'tl.toast.reset'        : 'Robot reset to neutral pose',
    'tl.toast.resetfail'    : 'Reset failed: {msg}',
    'tl.toast.stopfirst'    : 'Stop playback before editing the timeline.',
    'tl.toast.stopfirstnew' : 'Stop playback before starting a new sequence.',
    'tl.toast.captured'     : 'Keyframe captured (position {pos} of {total}){speech}',
    'tl.toast.deleted'      : 'Keyframe deleted',
    'tl.toast.nokfinsert'   : '"{name}" has no keyframes to insert.',
    'tl.toast.inserted'     : 'Inserted {n} keyframes from "{name}"',
    'tl.toast.inserted.one' : 'Inserted 1 keyframe from "{name}"',
    'tl.toast.insertfail'   : 'Insert failed: {msg}',
    'tl.toast.startednew'   : 'Started a new sequence',
    'tl.toast.needname'     : 'Type a sequence name first.',
    'tl.toast.nothingsave'  : 'Nothing to save yet — capture a keyframe first.',
    'tl.toast.saved'        : 'Saved as {name}',
    'tl.toast.savefail'     : 'Save failed: {msg}',

    'tl.untitled'           : 'Untitled',
    'tl.loadedinfo'         : '<b>{name}</b> — {count} keyframes',
    'tl.loadedinfo.one'     : '<b>{name}</b> — 1 keyframe',
    'tl.loadedinfo.saved'   : '<b>{name}</b> — {count} keyframes (saved)',
    'tl.loadedinfo.saved.one': '<b>{name}</b> — 1 keyframe (saved)',
    'tl.seqmeta'            : '{count} keyframes',
    'tl.seqmeta.one'        : '1 keyframe',
    'tl.totalduration'      : 'Estimated real playback time: ~{secs}s — driven by each keyframe\'s pre-wait, same as actual playback. Clip-move boxes are shown for reference, capped to fit inside their pre-wait.',
    'tl.tip.motors'         : 'Motors: {list}',
    'tl.tip.speech'         : 'Speech: "{text}"',
    'tl.tip.speed'          : 'Speed: {n}',
    'tl.tip.prewait'        : 'Pre-wait: {n}s',
    'tl.tip.est'            : 'Estimated move time: {n}s (visual estimate only)',
    'tl.tip.overflow'       : '⚠ Estimated move may take longer than this pre-wait — consider raising the pre-wait.',
    'tl.unknownerror'       : 'Unknown error',

    'tl.status.connected'   : 'Robot connected',
    'tl.status.notfound'    : 'Robot not found (preview still works)',
    'tl.status.unreachable' : 'Timeline server unreachable',
    'tl.speechnote'         : ' + 🔊 speech',

    // ── CALIBRATION (calibration/index.html) ───────────────────────────────
    'cal.pagetitle'         : '🔧 Ohbot Motor Calibration',
    'cal.title'             : 'Ohbot Motor Calibration',
    'cal.subtitle'          : 'Find min, max, and center for each motor, then save a new motor definitions file.',
    'cal.checking'          : 'Checking connection…',
    'cal.connected'         : 'Ohbot connected',
    'cal.notfound'          : 'Ohbot not found — sliders will not move anything',

    'cal.defaultpose'       : 'Set Default Pose (500 / lips 900·800, speed 2)',
    'cal.defaultpose.fail'  : 'Could not set default pose.',
    'cal.save'              : '💾 Save Calibration',
    'cal.exit'              : '⏹ Stop & Exit',
    'cal.footer'            : 'All calibration moves happen at a fixed slow speed. Saving backs up the current motor file as MD_old_N.omd before writing the new one. "Stop & Exit" shuts down the calibration service so the USB cable is free again — do this once you\'ve saved and are done, not between motors.',

    'cal.readout'           : 'raw {raw} / 1000',
    'cal.btn.center'        : 'Center OK',
    'cal.btn.center.toplip' : 'Top Lip CLOSED (just touching) OK',
    'cal.btn.center.botlip' : 'Bottom Lip CLOSED (just touching) OK',
    'cal.btn.min'           : 'Min OK',
    'cal.btn.max'           : 'Max OK',
    'cal.btn.clear'         : 'Clear',
    'cal.reversed'          : 'Reversed?',
    'cal.cap.center'        : 'Center',
    'cal.cap.min'           : 'Min',
    'cal.cap.max'           : 'Max',
    'cal.cap.needmore'      : '{v} (need one more)',
    'cal.markfail'          : 'Could not record that value.',

    'cal.robot.prompt'      : 'Which robot is this calibration for?\n\nType a name (e.g. Goldie, Blue Boy) and it will be saved under that name so you can load it back from the launcher page.\n\nLeave blank to just update the live motor file without filing a named copy.{list}',
    'cal.robot.already'     : '\n\nAlready saved: {names}',
    'cal.robot.first'       : '\n\nNo robots saved yet — this will be the first.',
    'cal.robot.exists'      : '"{name}" already has a saved calibration.\n\nReplace it with what you\'ve just measured?\n\n(The old one is kept as a .bak file, so it isn\'t lost.)',
    'cal.save.named'        : 'Save calibration and file it under "{name}"?',
    'cal.save.unnamed'      : 'Save calibration without a robot name?\n\nThe live motor file will be updated, but there will be no named copy to load back later.',
    'cal.save.backupnote'   : '{what}\n\nThe current motor file is backed up first.',
    'cal.save.d3pt'         : ' 3-point (full travel kept): {list}.',
    'cal.save.dfull'        : ' Full travel, no centre: {list}.',
    'cal.save.dtrim'        : ' Centred/trimmed as before: {list}.',
    'cal.save.duntouched'   : ' Left exactly as they were: {list}.',
    'cal.save.filed'        : ' Filed as robot "{name}"',
    'cal.save.filed.replaced': ' (replaced the previous one).',
    'cal.save.filed.end'    : '.',
    'cal.save.ok'           : 'Saved! Old file backed up as {backup}.{named}{detail}',
    'cal.save.halfdone'     : 'NOT saved — only partly measured: {list}. Each motor needs all three of Min OK, Center OK and Max OK before it can be saved. These were left unchanged in the file.',
    'cal.save.roboterr'     : 'The robot is calibrated and the live motor file IS saved — but the named copy could not be filed: {msg}',
    'cal.save.fail'         : 'Save failed.',

    'cal.exit.confirm'      : 'Stop the calibration service and close this page? Make sure you\'ve saved first — this frees up the USB cable for the Greeter or the GUI.',
    'cal.exit.done'         : 'Calibration service stopped. You can close this tab now.',
  };

  // ==========================================================================
  // SPANISH
  // ==========================================================================
  const ES = {

    // ── Shared across pages ────────────────────────────────────────────────
    'lang.label'            : 'Idioma',
    'lang.en'               : 'English',
    'lang.es'               : 'Español',

    'motor.HEADNOD'         : 'Cabeza arriba/abajo',
    'motor.HEADTURN'        : 'Cabeza izq./der.',
    'motor.EYETURN'         : 'Ojos izq./der.',
    'motor.LIDBLINK'        : 'Párpados / parpadeo',
    'motor.TOPLIP'          : 'Labio superior',
    'motor.BOTTOMLIP'       : 'Labio inferior',
    'motor.EYETILT'         : 'Ojos arriba/abajo',
    'motor.HEADROLL'        : 'Inclinación de cabeza',

    'led.off'               : 'Apagado',
    'led.red'               : 'Rojo',
    'led.green'             : 'Verde',
    'led.blue'              : 'Azul',
    'led.yellow'            : 'Amarillo',
    'led.cyan'              : 'Cian',
    'led.purple'            : 'Morado',
    'led.white'             : 'Blanco',
    'led.iceblue'           : 'Azul hielo',

    'common.loading'        : 'Cargando…',
    'common.saving'         : 'Guardando…',
    'common.error'          : 'Error',
    'common.noserver'       : 'No se pudo conectar con el servidor',
    'common.noserver.detail': 'No se pudo conectar con el servidor: {msg}',
    'common.speed'          : 'Velocidad de movimiento',
    'common.livemode'       : 'Modo en vivo — enviar al mover',
    'common.eyecolour'      : 'Color de los ojos (LED)',
    'common.seqname.ph'     : 'Nombre de la secuencia…',
    'common.seqdesc.ph'     : 'Descripción (opcional)',
    'common.new'            : '＋ Nueva',
    'common.save'           : '💾 Guardar',
    'common.capture'        : '📸 Capturar pose',

    // ── LAUNCHER PAGE ──────────────────────────────────────────────────────
    'launcher.pagetitle'    : '🤖 Lanzador de Ohbot',
    'launcher.title'        : 'Lanzador de Ohbot',
    'launcher.subtitle'     : 'Elige lo que quieres hacer',
    'launcher.running.some' : 'Algo está en marcha',
    'launcher.badge.running': 'Activo',

    'launcher.greeter.name' : 'Robot Recepcionista',
    'launcher.greeter.desc' : 'Modo de conversación por voz. Ohbot escucha, habla y charla con los visitantes.',
    'launcher.gui.name'     : 'Creador de Secuencias',
    'launcher.gui.desc'     : 'Interfaz web para controlar los motores, elegir emociones y crear secuencias de animación.',

    'launcher.stop'         : '⏹ Detener el servicio actual',
    'launcher.opengui'      : 'Abrir la interfaz ↗',
    'launcher.restart'      : '↺ Reiniciar la Pi',
    'launcher.shutdown'     : '⏻ Apagar la Pi',

    'launcher.calib'        : '🔧 Calibración de motores',
    'launcher.calib.tip'    : 'Detén primero el servicio actual',
    'launcher.calib.failed' : 'No se pudo iniciar la calibración.',

    'launcher.robot.title'  : '🤖 ¿Qué robot estás usando?',
    'launcher.robot.hint'   : 'Carga su calibración aquí antes de iniciar el Recepcionista o la interfaz.<br>Los robots se guardan por nombre cuando terminas una calibración de motores.',
    'launcher.robot.hint.none': 'Todavía no hay nada guardado. Ejecuta la <strong>Calibración de motores</strong> y, al guardar, te pedirá un nombre de robot.<br>Ese robot aparecerá aquí después.',
    'launcher.robot.load'   : 'Cargar calibración',
    'launcher.robot.savecur': '💾 Guardar la calibración actual como un robot…',
    'launcher.robot.none'   : 'Todavía no hay robots guardados',
    'launcher.robot.readfail': 'No se pudieron leer los robots guardados.',
    'launcher.robot.active' : 'Cargado ahora: <strong>{name}</strong>',
    'launcher.robot.active.none': 'Cargado ahora: <strong>—</strong>',
    'launcher.robot.active.unnamed': 'Cargado ahora: <strong>—</strong> (el archivo de motores en uso todavía no se ha guardado con un nombre de robot)',
    'launcher.robot.cal3pt' : '{n} motores de 3 puntos',
    'launcher.robot.cal2pt' : 'calibración antigua de 2 puntos',
    'launcher.robot.badfile': ' — PROBLEMA CON EL ARCHIVO',
    'launcher.robot.option' : '{name} — guardado {saved} ({cal}){bad}',
    'launcher.robot.locked' : 'No se puede cambiar de robot mientras {running} está en marcha: ya tiene cargados los números del robot actual. Presiona «Detener el servicio actual» primero.',

    'launcher.save.prompt'  : 'Guardar como robot la calibración que se está usando.\n\nEsto toma los números de motor que el robot usa en este momento y los archiva bajo un nombre, para que puedas volver a cargarlos más adelante.\n\nNada cambia en el robot: simplemente queda registrado.\n\nNombre del robot:',
    'launcher.save.noname'  : 'No escribiste un nombre, así que no se guardó nada.',
    'launcher.save.exists'  : '«{name}» ya tiene una calibración guardada.\n\n¿Reemplazarla por la que está en uso ahora?\n\n(La anterior se conserva como archivo .bak, así que no se pierde.)',
    'launcher.save.nothing' : 'No se guardó nada.',
    'launcher.save.cal3pt'  : ' Tiene {n} motores calibrados con tres puntos.',
    'launcher.save.cal2pt'  : ' Nota: no tiene centros medidos; es el estilo antiguo de dos puntos.',
    'launcher.save.ok'      : 'Guardado como «{name}».{cal}',
    'launcher.save.fail'    : 'No se pudo guardar.',

    'launcher.load.note2pt' : '\n\nNota: este tiene la calibración antigua de dos puntos (sin centros medidos), así que se comportará a la antigua hasta que lo vuelvas a calibrar.',
    'launcher.load.confirm' : '¿Cargar la calibración de {name}?\n\nEsto copia sus números guardados sobre el archivo de motores en uso, así que el Recepcionista y la interfaz manejarán a {name} de ahora en adelante.\n\nPrimero se hace una copia de seguridad del archivo actual, así que se puede deshacer.{note}',
    'launcher.load.backup'  : ' El archivo de motores anterior se conservó como {backup}.',
    'launcher.load.ok'      : '{name} está cargado. Inicia el Recepcionista o la interfaz y usará esta calibración.{kept}',
    'launcher.load.fail'    : 'No se pudo cargar ese robot.',

    'launcher.status.greeter': 'El Robot Recepcionista está en marcha',
    'launcher.status.gui'    : 'El Creador de Secuencias está en marcha',
    'launcher.status.calib'  : 'La Calibración de motores está en marcha',

    'launcher.switch.confirm': '¿Detener {other} y cambiar a {target}?',
    'launcher.stop.confirm'  : '¿Detener el servicio actual?',
    'launcher.power.shutdown.confirm': '¿Seguro que quieres apagar la Pi?',
    'launcher.power.restart.confirm' : '¿Seguro que quieres reiniciar la Pi?',
    'launcher.power.shutdown.title'  : 'Apagando…',
    'launcher.power.restart.title'   : 'Reiniciando…',
    'launcher.power.shutdown.msg'    : 'Puedes desconectar la corriente sin problema cuando se apague la luz.',
    'launcher.power.shutdown.msg2'   : 'Puedes desconectar la corriente sin problema cuando se apaguen las luces.',
    'launcher.power.restart.msg'     : 'La página se recargará cuando la Pi vuelva a estar en línea.',
    'launcher.footer'                : 'Lanzador web de Ohbot — ',

    // ── SEQUENCE BUILDER (gui/index.html) ──────────────────────────────────
    'gui.pagetitle'         : '🤖 Creador de Secuencias de Ohbot',
    'gui.title'             : '🤖 Creador de Secuencias de Ohbot',
    'gui.connecting'        : 'Conectando…',
    'gui.badge.demo'        : '✨ DEMO EN MARCHA',
    'gui.badge.playing'     : '▶ REPRODUCIENDO',
    'gui.demo.stop'         : '⏹ Detener demo',
    'gui.demo.start'        : '✨ ¡Muéstrame lo que sabes hacer!',
    'gui.link.timeline'     : '🎬 Línea de tiempo',
    'gui.link.launcher'     : '⬅ Lanzador',

    'gui.motorcontrols'     : 'Controles de motores',
    'gui.emotions'          : '🎭 Emociones predefinidas',
    'gui.emotion.happy'     : '😊 Feliz',
    'gui.emotion.sad'       : '😢 Triste',
    'gui.emotion.surprised' : '😮 Sorprendido',
    'gui.emotion.thinking'  : '🤔 Pensativo',
    'gui.emotion.sleeping'  : '😴 Dormido',

    'gui.speech.title'      : '🔊 Habla (con sincronización de labios)',
    'gui.speech.ph'         : 'Escribe lo que Ohbot debe decir…',
    'gui.speech.say'        : '🔊 Decirlo ahora',
    'gui.speech.clear'      : '✕ Borrar',
    'gui.speech.clear.tip'  : 'Borrar el texto',
    'gui.speech.speaking'   : '🎙 Hablando…',

    'gui.sendrobot'         : '📡 Enviar al robot',
    'gui.reset'             : '↩ Restablecer',

    'gui.empty'             : 'Todavía no hay poses.<br>Usa los <strong>controles de motores</strong> de la izquierda para posicionar a Ohbot,<br>y luego pulsa <strong>📸 Capturar pose</strong> para guardarla.<br>¡Repite para crear una secuencia!',

    'gui.play'              : '▶ Reproducir',
    'gui.stop'              : '⏹ Detener',
    'gui.loadsaved'         : '📂 Cargar guardada…',
    'gui.clear'             : '🗑 Vaciar',

    'gui.chat.title'        : '💬 Chat con IA',
    'gui.chat.greeting'     : '¡Hola! Soy Ohbot 🤖 Escribe un mensaje y te respondo. Marca «Hablar» para oírme decirlo.',
    'gui.chat.ph'           : 'Pregúntale algo a Ohbot…',
    'gui.chat.speak'        : '🔊 Hablar',
    'gui.chat.send'         : 'Enviar',
    'gui.chat.clear'        : '↺ Borrar',
    'gui.chat.clear.tip'    : 'Borrar la conversación',
    'gui.chat.cleared'      : 'Conversación borrada. ¡Empecemos de nuevo! 🤖',
    'gui.chat.thinking'     : 'Pensando…',
    'gui.chat.toast.cleared': 'Chat borrado',
    'gui.chat.switched'     : '¡Personalidad cambiada a {name}! 🎭',
    'gui.chat.personality.tip' : 'La personalidad de Ohbot',
    'gui.pers.friendly'     : '😊 Amable',
    'gui.pers.comedian'     : '😄 Comediante',
    'gui.pers.pirate'       : '🏴‍☠️ Pirata',
    'gui.pers.professor'    : '🎓 Profe gruñón',
    'gui.pers.shy'          : '😳 Tímido',
    'gui.pers.friendly.long' : '😊 Robot amable',
    'gui.pers.comedian.long' : '😄 Comediante',
    'gui.pers.pirate.long'   : '🏴‍☠️ Pirata',
    'gui.pers.professor.long': '🎓 Profesor gruñón',
    'gui.pers.shy.long'      : '😳 Robot tímido',
    'gui.chat.persfail'     : 'No se pudo cambiar la personalidad',

    'gui.kf.speed.tip'      : 'Velocidad de rampa propia de Ohbot para el movimiento de esta pose (1 = lento y suave, 10 = rápido)',
    'gui.kf.prewait.tip'    : 'Espera previa: segundos que se mantiene esta pose después de enviarla, antes de enviar el movimiento de la SIGUIENTE. Ajústalo mirando al robot: debe cubrir el tiempo real de este movimiento más cualquier pausa extra que quieras.',
    'gui.kf.label.ph'       : 'Etiqueta…',
    'gui.kf.label.tip'      : 'Etiqueta opcional para esta pose',
    'gui.kf.up.tip'         : 'Mover antes en la secuencia',
    'gui.kf.down.tip'       : 'Mover después en la secuencia',
    'gui.kf.preview.tip'    : 'Ver esta pose en el robot',
    'gui.kf.delete.tip'     : 'Eliminar esta pose',
    'gui.kf.speech.ph'      : 'Lo que Ohbot dice en este momento… (déjalo en blanco para silencio)',

    'gui.toast.sent'        : 'Enviado al robot ✓',
    'gui.toast.reset'       : 'Restablecido a la posición neutra ✓',
    'gui.toast.resetfail'   : 'No se pudo restablecer',
    'gui.toast.preview'     : 'Mostrando la pose {id} ✓',
    'gui.toast.previewfail' : 'No se pudo mostrar la pose',
    'gui.toast.captured'    : 'Pose {id} capturada (n.º {count} de la secuencia){speech}',
    'gui.toast.cleared'     : 'Secuencia vaciada',
    'gui.toast.newseq'      : 'Nueva secuencia iniciada',
    'gui.toast.nothingplay' : 'No hay nada que reproducir: captura algunas poses primero.',
    'gui.toast.playing'     : '▶ Reproduciendo…',
    'gui.toast.playfail'    : 'Falló la reproducción',
    'gui.toast.stopped'     : '⏹ Detenido',
    'gui.toast.needname'    : '¡Primero ponle un nombre a la secuencia!',
    'gui.toast.nokf'        : '¡No hay poses que guardar!',
    'gui.toast.saved'       : '💾 Guardada como «{name}» ✓',
    'gui.toast.savefail'    : 'No se pudo guardar',
    'gui.toast.noserver'    : 'No se pudo conectar con el servidor',
    'gui.toast.loadedold'   : 'Se cargó «{name}». Los tiempos del formato antiguo se restablecieron a los valores por defecto (velocidad {speed}, espera de {wait} s). Vuelve a ajustar cada pose según haga falta.',
    'gui.toast.loaded'      : 'Se cargó «{name}» ({count} poses) ✓',
    'gui.toast.loadfail'    : 'No se pudo cargar',
    'gui.toast.needspeech'  : '¡Escribe primero algo para que Ohbot lo diga!',
    'gui.toast.speaking'    : '🔊 Hablando…',
    'gui.toast.speechfail'  : 'Falló el habla',
    'gui.toast.playdone'    : 'Reproducción terminada ✓',
    'gui.toast.demodone'    : '✨ ¡Demo terminada!',
    'gui.toast.demostart'   : '✨ Iniciando la demo…',
    'gui.toast.demofail'    : 'No se pudo iniciar la demo',
    'gui.toast.demostopped' : 'Demo detenida',
    'gui.toast.emotionfail' : 'Falló la emoción',

    'gui.confirm.clear'     : '¿Borrar todas las poses? Esto no se puede deshacer.',
    'gui.confirm.new'       : '¿Empezar una secuencia nueva? Se perderán las poses sin guardar.',
    'gui.confirm.load'      : '¿Cargar una secuencia guardada? Se perderán los cambios sin guardar.',
    'gui.confirm.overwrite' : 'Ya existe una secuencia llamada «{name}» ({count} poses).\n\n¿Reemplazarla?',

    'gui.status.connected'  : 'Ohbot conectado',
    'gui.status.notfound'   : 'No se encontró el robot (los controles siguen funcionando)',
    'gui.status.unreachable': 'No se puede conectar con el servidor',
    'gui.seq.frames'        : '{name} ({count} poses)',
    'gui.speechnote'        : ' + 🔊 habla',

    // ── TIMELINE (gui/timeline.html) ───────────────────────────────────────
    'tl.pagetitle'          : '🎬 Línea de tiempo de Ohbot',
    'tl.title'              : '🎬 Línea de tiempo de Ohbot',
    'tl.phase'              : 'FASE 2B — CAPTURA EN VIVO',
    'tl.checking'           : 'Comprobando el robot…',
    'tl.badge.playing'      : '▶ REPRODUCIENDO',
    'tl.pickone'            : 'Elige una secuencia de la izquierda para verla.',
    'tl.link.builder'       : '← Creador de Secuencias',

    'tl.saved'              : 'Secuencias guardadas',
    'tl.leftHint'           : 'Haz clic en una secuencia para abrirla (reemplaza lo que hay ahora en la línea de tiempo). Usa <b>Insertar en el cursor</b> para intercalar sus poses en lo que estás construyendo.',
    'tl.empty'              : 'Elige una secuencia guardada a la izquierda, o posiciona a Ohbot con el<br>panel de la derecha y pulsa <strong>📸 Capturar pose</strong> para empezar una nueva.',
    'tl.hintbar'            : 'Haz clic en la regla o en la pista para mover el cursor: las poses nuevas (y las secuencias insertadas) aparecen ahí. Pulsa la barra espaciadora para reproducir desde ese punto (el cursor avanza mientras suena) y púlsala otra vez para detener. Pasa el ratón por encima de un clip para eliminarlo.',

    'tl.pose'               : 'Posicionar y capturar',
    'tl.speech'             : 'Habla',
    'tl.speech.ph'          : 'Lo que Ohbot dice en esta pose…',
    'tl.speech.hint'        : 'Se guarda como texto junto con la pose; aquí no se dice durante la reproducción (usa el Constructor de Secuencias para eso). El botón de arriba te deja escucharlo ahora.',
    'tl.speech.preview'     : '🔊 Escuchar Esta Frase',
    'tl.speech.preview.tip' : 'Dice esta frase ahora, en el idioma seleccionado arriba a la derecha. No se guarda nada ni se modifica ninguna pose.',
    'tl.toast.nospeech'     : 'Todavía no has escrito nada en el cuadro de Habla',
    'tl.toast.speaking'     : '🗣 Hablando…',
    'tl.toast.speakfail'    : 'No se pudo hablar — ¿está conectado el robot?',
    'tl.sendpose'           : '📡 Enviar la pose al robot',
    'tl.resetpose'          : '↩ Restablecer la pose',

    'tl.clip.delete.tip'    : 'Eliminar esta pose',
    'tl.clip.overflow.tip'  : 'El movimiento estimado puede tardar más que la espera previa de esta pose',
    'tl.insert'             : '⬇ Insertar en el cursor',
    'tl.insert.tip'         : 'Inserta las poses de esta secuencia en la línea de tiempo que estás construyendo, en la posición del cursor; no reemplaza lo que ya hay',

    'tl.nosaved'            : 'Todavía no hay secuencias guardadas. Crea una primero en el Creador de Secuencias.',
    'tl.listfail'           : 'No se pudo cargar la lista de secuencias: {msg}',
    'tl.loadfail'           : 'Error al cargar la secuencia: {msg}',
    'tl.nokf'               : 'Esta secuencia todavía no tiene poses.',
    'tl.newseq'             : 'Secuencia nueva — sin guardar todavía.',

    'tl.toast.playdone'     : 'Reproducción terminada',
    'tl.toast.pickfirst'    : 'Elige una secuencia primero.',
    'tl.toast.playfail'     : 'No se pudo iniciar la reproducción: {msg}',
    'tl.toast.unknownerr'   : 'error desconocido',
    'tl.toast.noserver'     : 'No se pudo conectar con el servidor de la línea de tiempo: {msg}',
    'tl.toast.posesent'     : 'Pose enviada al robot',
    'tl.toast.reset'        : 'Robot restablecido a la pose neutra',
    'tl.toast.resetfail'    : 'No se pudo restablecer: {msg}',
    'tl.toast.stopfirst'    : 'Detén la reproducción antes de editar la línea de tiempo.',
    'tl.toast.stopfirstnew' : 'Detén la reproducción antes de empezar una secuencia nueva.',
    'tl.toast.captured'     : 'Pose capturada (posición {pos} de {total}){speech}',
    'tl.toast.deleted'      : 'Pose eliminada',
    'tl.toast.nokfinsert'   : '«{name}» no tiene poses que insertar.',
    'tl.toast.inserted'     : 'Se insertaron {n} poses de «{name}»',
    'tl.toast.inserted.one' : 'Se insertó 1 pose de «{name}»',
    'tl.toast.insertfail'   : 'Falló la inserción: {msg}',
    'tl.toast.startednew'   : 'Se empezó una secuencia nueva',
    'tl.toast.needname'     : 'Escribe primero un nombre para la secuencia.',
    'tl.toast.nothingsave'  : 'Todavía no hay nada que guardar: captura una pose primero.',
    'tl.toast.saved'        : 'Guardada como {name}',
    'tl.toast.savefail'     : 'No se pudo guardar: {msg}',

    'tl.untitled'           : 'Sin título',
    'tl.loadedinfo'         : '<b>{name}</b> — {count} poses',
    'tl.loadedinfo.one'     : '<b>{name}</b> — 1 pose',
    'tl.loadedinfo.saved'   : '<b>{name}</b> — {count} poses (guardada)',
    'tl.loadedinfo.saved.one': '<b>{name}</b> — 1 pose (guardada)',
    'tl.seqmeta'            : '{count} poses',
    'tl.seqmeta.one'        : '1 pose',
    'tl.totalduration'      : 'Tiempo real de reproducción estimado: ~{secs} s. Lo marca la espera previa de cada pose, igual que la reproducción real. Los bloques de movimiento se muestran como referencia, recortados para caber dentro de su espera previa.',
    'tl.tip.motors'         : 'Motores: {list}',
    'tl.tip.speech'         : 'Habla: «{text}»',
    'tl.tip.speed'          : 'Velocidad: {n}',
    'tl.tip.prewait'        : 'Espera previa: {n} s',
    'tl.tip.est'            : 'Tiempo de movimiento estimado: {n} s (solo una estimación visual)',
    'tl.tip.overflow'       : '⚠ El movimiento estimado puede tardar más que esta espera previa; considera aumentarla.',
    'tl.unknownerror'       : 'Error desconocido',

    'tl.status.connected'   : 'Robot conectado',
    'tl.status.notfound'    : 'No se encontró el robot (la vista previa sigue funcionando)',
    'tl.status.unreachable' : 'No se puede conectar con el servidor de la línea de tiempo',
    'tl.speechnote'         : ' + 🔊 habla',

    // ── CALIBRATION (calibration/index.html) ───────────────────────────────
    'cal.pagetitle'         : '🔧 Calibración de motores de Ohbot',
    'cal.title'             : 'Calibración de motores de Ohbot',
    'cal.subtitle'          : 'Encuentra el mínimo, el máximo y el centro de cada motor, y luego guarda un archivo nuevo de definiciones de motores.',
    'cal.checking'          : 'Comprobando la conexión…',
    'cal.connected'         : 'Ohbot conectado',
    'cal.notfound'          : 'No se encontró a Ohbot: los controles no moverán nada',

    'cal.defaultpose'       : 'Poner la pose por defecto (500 / labios 900·800, velocidad 2)',
    'cal.defaultpose.fail'  : 'No se pudo poner la pose por defecto.',
    'cal.save'              : '💾 Guardar la calibración',
    'cal.exit'              : '⏹ Detener y salir',
    'cal.footer'            : 'Todos los movimientos de calibración se hacen a una velocidad lenta fija. Al guardar se hace una copia de seguridad del archivo de motores actual como MD_old_N.omd antes de escribir el nuevo. «Detener y salir» apaga el servicio de calibración para liberar el cable USB: hazlo cuando ya hayas guardado y terminado, no entre un motor y otro.',

    'cal.readout'           : 'bruto {raw} / 1000',
    'cal.btn.center'        : 'Centro OK',
    'cal.btn.center.toplip' : 'Labio superior CERRADO (apenas tocando) OK',
    'cal.btn.center.botlip' : 'Labio inferior CERRADO (apenas tocando) OK',
    'cal.btn.min'           : 'Mínimo OK',
    'cal.btn.max'           : 'Máximo OK',
    'cal.btn.clear'         : 'Borrar',
    'cal.reversed'          : '¿Invertido?',
    'cal.cap.center'        : 'Centro',
    'cal.cap.min'           : 'Mínimo',
    'cal.cap.max'           : 'Máximo',
    'cal.cap.needmore'      : '{v} (falta uno más)',
    'cal.markfail'          : 'No se pudo registrar ese valor.',

    'cal.robot.prompt'      : '¿Para qué robot es esta calibración?\n\nEscribe un nombre (por ejemplo, Goldie o Blue Boy) y se guardará con ese nombre para que puedas cargarlo después desde la página del lanzador.\n\nDéjalo en blanco para solo actualizar el archivo de motores en uso, sin archivar una copia con nombre.{list}',
    'cal.robot.already'     : '\n\nYa guardados: {names}',
    'cal.robot.first'       : '\n\nTodavía no hay robots guardados; este será el primero.',
    'cal.robot.exists'      : '«{name}» ya tiene una calibración guardada.\n\n¿Reemplazarla por lo que acabas de medir?\n\n(La anterior se conserva como archivo .bak, así que no se pierde.)',
    'cal.save.named'        : '¿Guardar la calibración y archivarla como «{name}»?',
    'cal.save.unnamed'      : '¿Guardar la calibración sin nombre de robot?\n\nSe actualizará el archivo de motores en uso, pero no quedará una copia con nombre para cargar más adelante.',
    'cal.save.backupnote'   : '{what}\n\nPrimero se hace una copia de seguridad del archivo de motores actual.',
    'cal.save.d3pt'         : ' De 3 puntos (recorrido completo conservado): {list}.',
    'cal.save.dfull'        : ' Recorrido completo, sin centro: {list}.',
    'cal.save.dtrim'        : ' Centrados/recortados como antes: {list}.',
    'cal.save.duntouched'   : ' Se dejaron exactamente como estaban: {list}.',
    'cal.save.filed'        : ' Archivada como el robot «{name}»',
    'cal.save.filed.replaced': ' (reemplazó a la anterior).',
    'cal.save.filed.end'    : '.',
    'cal.save.ok'           : '¡Guardado! El archivo anterior se respaldó como {backup}.{named}{detail}',
    'cal.save.halfdone'     : 'NO se guardaron (medidos solo en parte): {list}. Cada motor necesita los tres: Mínimo OK, Centro OK y Máximo OK, antes de poder guardarse. Estos quedaron sin cambios en el archivo.',
    'cal.save.roboterr'     : 'El robot está calibrado y el archivo de motores en uso SÍ se guardó, pero no se pudo archivar la copia con nombre: {msg}',
    'cal.save.fail'         : 'No se pudo guardar.',

    'cal.exit.confirm'      : '¿Detener el servicio de calibración y cerrar esta página? Asegúrate de haber guardado primero: esto libera el cable USB para el Recepcionista o la interfaz.',
    'cal.exit.done'         : 'Servicio de calibración detenido. Ya puedes cerrar esta pestaña.',
  };

  // ==========================================================================
  // The machinery. You shouldn't need to touch anything below this line.
  // ==========================================================================

  const DICTS   = { en: EN, es: ES };
  const STORAGE = 'ohbot_lang';
  const missing = new Set();

  let lang = 'en';
  try {
    const saved = localStorage.getItem(STORAGE);
    if (saved && DICTS[saved]) lang = saved;
  } catch (e) { /* private browsing — just stay on English */ }

  /** Look up a phrase. `vars` fills in any {placeholders}. */
  function t(key, vars) {
    let s = DICTS[lang][key];
    if (s === undefined) {
      s = EN[key];
      if (s === undefined) {
        if (!missing.has(key)) {
          missing.add(key);
          console.warn('[i18n] no such phrase:', key);
        }
        return key;
      }
      if (lang !== 'en' && !missing.has(lang + '|' + key)) {
        missing.add(lang + '|' + key);
        console.warn('[i18n] not translated to ' + lang + ' yet:', key);
      }
    }
    if (vars) {
      for (const k in vars) {
        s = s.split('{' + k + '}').join(vars[k]);
      }
    }
    return s;
  }

  /** The 8 motor names, translated. Falls back to whatever the server sent. */
  function motorLabel(key, serverLabel) {
    const k = 'motor.' + key;
    return DICTS[lang][k] || serverLabel || key;
  }

  /**
   * Walk the page and translate everything tagged with a data-i18n attribute.
   *   data-i18n              → replaces the element's text
   *   data-i18n-html         → replaces its inner HTML (for text with <br> etc.)
   *   data-i18n-title        → the hover tooltip
   *   data-i18n-placeholder  → the grey hint inside a typing box
   *   data-i18n-pagetitle    → the browser tab title (put on <body>)
   * Safe to call as often as you like.
   */
  function apply(root) {
    const scope = root || document;

    scope.querySelectorAll('[data-i18n]').forEach(el => {
      el.textContent = t(el.getAttribute('data-i18n'));
    });
    scope.querySelectorAll('[data-i18n-html]').forEach(el => {
      el.innerHTML = t(el.getAttribute('data-i18n-html'));
    });
    scope.querySelectorAll('[data-i18n-title]').forEach(el => {
      el.setAttribute('title', t(el.getAttribute('data-i18n-title')));
    });
    scope.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
      el.setAttribute('placeholder', t(el.getAttribute('data-i18n-placeholder')));
    });

    const titleKey = document.body && document.body.getAttribute('data-i18n-pagetitle');
    if (titleKey) document.title = t(titleKey);
    document.documentElement.setAttribute('lang', lang);
  }

  /**
   * Switch language. Re-translates the page, tells the Pi (so Python can read
   * the choice later), and fires an 'ohbot-lang-change' event so each page can
   * redraw the parts it built itself with JavaScript.
   */
  function setLang(next) {
    if (!DICTS[next] || next === lang) return;
    lang = next;
    try { localStorage.setItem(STORAGE, lang); } catch (e) {}

    // Best effort — if the server doesn't have the /lang route the page still
    // works perfectly, the Python side just won't know about the choice.
    try {
      fetch('/lang', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ lang })
      }).catch(() => {});
    } catch (e) {}

    apply();
    const sel = document.getElementById('ohbot-lang-select');
    if (sel) sel.value = lang;
    window.dispatchEvent(new CustomEvent('ohbot-lang-change', { detail: { lang } }));
  }

  /** Drops the little 🌐 dropdown into the top-right corner of the page. */
  function mountSwitcher() {
    if (document.getElementById('ohbot-lang-switch')) return;

    const css = document.createElement('style');
    css.textContent = `
      #ohbot-lang-switch {
        position: fixed; top: 10px; right: 12px; z-index: 99999;
        display: flex; align-items: center; gap: 6px;
        background: rgba(0,0,0,0.45);
        border: 1px solid rgba(255,255,255,0.18);
        border-radius: 20px; padding: 4px 10px 4px 12px;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        font-size: 0.78rem; color: #eaeaea;
        backdrop-filter: blur(4px);
      }
      #ohbot-lang-switch .globe { font-size: 0.95rem; line-height: 1; }
      #ohbot-lang-select {
        background: transparent; color: inherit; border: none;
        font: inherit; cursor: pointer; padding: 2px 2px; outline: none;
      }
      #ohbot-lang-select option { background: #16213e; color: #eaeaea; }
      @media print { #ohbot-lang-switch { display: none; } }
    `;
    document.head.appendChild(css);

    const wrap = document.createElement('div');
    wrap.id = 'ohbot-lang-switch';
    wrap.innerHTML =
      '<span class="globe">🌐</span>' +
      '<select id="ohbot-lang-select" aria-label="Language / Idioma">' +
      '  <option value="en">English</option>' +
      '  <option value="es">Español</option>' +
      '</select>';
    document.body.appendChild(wrap);

    const sel = wrap.querySelector('#ohbot-lang-select');
    sel.value = lang;
    sel.addEventListener('change', e => setLang(e.target.value));
  }

  function init() {
    mountSwitcher();
    apply();
    window.dispatchEvent(new CustomEvent('ohbot-lang-ready', { detail: { lang } }));
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  /**
   * Adds the current language onto anything the page is about to POST to the
   * Pi, so the robot speaks and listens in the language on screen.
   *
   *   body: JSON.stringify(langBody({ text: 'Hola' }))
   *   → {"text":"Hola","lang":"es"}
   *
   * Called with nothing, it just sends the language on its own:
   *
   *   body: JSON.stringify(langBody())   → {"lang":"es"}
   *
   * Why send it every time instead of letting Python read language.txt? The
   * dropdown writes that file in the background, and a request fired a split
   * second later could beat the write. Sending the language with the request
   * removes the race entirely — the robot always uses the language you can
   * see on the page right now.
   */
  function langBody(obj) {
    return Object.assign({}, obj || {}, { lang: lang });
  }

  global.OhbotI18n = {
    t, apply, setLang, motorLabel, langBody,
    get lang() { return lang; },
    STRINGS: DICTS
  };
  // Short aliases so page code can just write t('some.key') / langBody({...})
  global.t = t;
  global.langBody = langBody;

})(window);
