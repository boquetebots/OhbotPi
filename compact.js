// ============================================================================
//  compact.js — small-screen support, shared by all the web pages
// ============================================================================
//
//  WHAT THIS IS FOR
//  ----------------
//  The pages are used on a Lenovo Legion Tab 8.8". Its panel is 2560x1600,
//  but Android draws everything at 2.5x so the text isn't microscopic, and
//  then Chrome's address bar, its tab strip and Android's task bar take a
//  further bite. What the page actually gets is:
//
//      1024 x 455   normal
//      1024 x 640   full screen        <- the ⛶ button, worth 185px
//
//  455 pixels is less than half a laptop screen. Every page in this project
//  is built as one screen that never scrolls (height:100vh, overflow:hidden),
//  so on the tablet the bottom of each column was simply chopped off with no
//  way to reach it. Things looked "missing" — they were there, just cut off.
//
//  WHAT THIS FILE DOES
//  -------------------
//  It puts classes on <body> and nothing else. Each page's own stylesheet
//  decides what those classes should look like, because each page has a
//  different layout. One file, four pages, no copy-paste.
//
//    compact   the window is too small to show everything at once.
//              Turn the columns into something that scrolls.
//              (touch screen, OR width < 1000, OR height < 720)
//
//    touch     this is a finger, not a mouse. Make the sliders and buttons
//              bigger. Deliberately separate from "compact", so shrinking a
//              window on the Mac reflows the page without going thumb-sized.
//              (pointer: coarse)
//
//    short     compact AND under 560 tall. The tablet in landscape, not in
//              full screen. Trim every bar and border to the bone.
//
//    narrow    compact AND under 900 wide. Portrait. Stack the columns.
//
//  ADDRESS-BAR OPTIONS
//  -------------------
//    ?compact=1   force the small layout on   (test it from a desktop)
//    ?compact=0   force it off
//    ?size=1      show a live readout of the real numbers, bottom right
//    ?kiosk=1     first tap anywhere goes full screen — for the Clubhouse
//
//  A NOTE ON "ADD TO HOME SCREEN"
//  ------------------------------
//  It won't help. Chrome only lets a page install as a proper app over HTTPS
//  or from localhost, and the tablet reaches these pages over plain http at a
//  wifi address. The shortcut just reopens Chrome with all its bars. The ⛶
//  button is the real answer.
// ============================================================================

(function () {
  'use strict';

  function isTouch() {
    return window.matchMedia('(pointer: coarse)').matches;
  }

  function param(name) {
    return new URLSearchParams(location.search).get(name);
  }

  function wantsCompact() {
    const forced = param('compact');
    if (forced === '1') return true;
    if (forced === '0') return false;
    return isTouch()
        || window.innerWidth  < 1000
        || window.innerHeight < 720;
  }

  // ── The ⛶ button ──────────────────────────────────────────────────────
  // Any page can have one: give a button id="fullscreen-btn". If the page
  // hasn't got one, nothing happens and nothing breaks.
  //
  // Browsers refuse to go full screen on their own — it has to come from a
  // real tap or click, or every dodgy web page in the world would do it to
  // you. That's why this can't just happen on load.
  function toggleFullscreen() {
    if (document.fullscreenElement) {
      document.exitFullscreen();
      return;
    }
    const el = document.documentElement;
    const go = el.requestFullscreen
            || el.webkitRequestFullscreen
            || el.mozRequestFullScreen;
    if (!go) { say('This browser has no full screen', true); return; }
    Promise.resolve(go.call(el)).catch(() => say('Full screen was refused', true));
  }

  // Use the page's own toast if it has one, otherwise stay quiet.
  function say(msg, isError) {
    if (typeof window.toast === 'function') window.toast(msg, isError);
    else console.warn(msg);
  }

  // ── The classes ───────────────────────────────────────────────────────
  function applyLayout() {
    const b = document.body;
    if (!b) return;
    const compact = wantsCompact();
    b.classList.toggle('compact', compact);
    b.classList.toggle('touch',   isTouch());
    b.classList.toggle('short',   compact && window.innerHeight < 560);
    b.classList.toggle('narrow',  compact && window.innerWidth  < 900);
  }

  // ── The ?size=1 readout ───────────────────────────────────────────────
  function sizeReadout() {
    if (param('size') === null) return;
    let box = document.getElementById('size-readout');
    if (!box) {
      box = document.createElement('div');
      box.id = 'size-readout';
      box.style.cssText = 'position:fixed;right:8px;bottom:8px;z-index:9999;' +
        'background:#000c;color:#0f9;border:1px solid #0f9;border-radius:6px;' +
        'padding:6px 10px;font:12px/1.5 monospace;pointer-events:none;' +
        'white-space:pre;';
      document.body.appendChild(box);
    }
    box.textContent =
      'CSS    ' + window.innerWidth + ' x ' + window.innerHeight + '\n' +
      'screen ' + screen.width + ' x ' + screen.height + '\n' +
      'ratio  ' + window.devicePixelRatio + '\n' +
      'touch  ' + isTouch() + '\n' +
      'mode   ' + (document.body.className || '(desktop)');
  }

  function refresh() { applyLayout(); sizeReadout(); }

  // ── Wire it up ────────────────────────────────────────────────────────
  function start() {
    refresh();

    const btn = document.getElementById('fullscreen-btn');
    if (btn) btn.addEventListener('click', toggleFullscreen);

    // Kiosk: the first tap anywhere goes full screen, so a visitor doesn't
    // need to know the ⛶ button exists.
    if (param('kiosk') !== null) {
      const firstTap = function () {
        document.removeEventListener('click', firstTap);
        if (!document.fullscreenElement) toggleFullscreen();
      };
      document.addEventListener('click', firstTap);
    }

    document.addEventListener('fullscreenchange', function () {
      if (btn) btn.classList.toggle('on', !!document.fullscreenElement);
      // Leaving full screen changes the height, so re-measure once it settles.
      setTimeout(refresh, 120);
    });

    window.addEventListener('resize', refresh);
    window.addEventListener('orientationchange', refresh);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', start);
  } else {
    start();
  }

  // Left on the window so a page can call it from an onclick if it prefers.
  window.toggleFullscreen = toggleFullscreen;

})();
