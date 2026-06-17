'use strict';
/*
 * Merito (PEP's Swiss SA) — superviseur uvicorn sur Jelastic NodeJS.
 * Robustesse :
 *  - libère le port AVANT de spawn (tue les workers orphelins → fin du "Address already in use")
 *  - spawn uvicorn dans son propre groupe de process (kill propre de tout l'arbre)
 *  - relance avec backoff plafonné ; reset si l'app a tenu > 60s
 *  - arrêt propre sur SIGTERM/SIGINT (restart plateforme = pas d'orphelins)
 */
const { spawn, execSync } = require('child_process');

const PORT = parseInt(process.env.PORT || '3000', 10);
const APP_DIR = process.env.APP_DIR || '/home/jelastic/umbra/backend';
const HOME = process.env.HOME || '/home/jelastic';
const WORKERS = String(process.env.UVICORN_WORKERS || '2');
const BACKOFF_MAX = 30000;

const env = Object.assign({}, process.env, {
  PATH: HOME + '/.local/bin:' + (process.env.PATH || ''),
  PORT: String(PORT),
});

let child = null, shuttingDown = false, backoff = 2000, startedAt = 0;
const log = (m) => console.log(`[merito-launcher ${new Date().toISOString()}] ${m}`);

function freePort() {
  try { execSync(`fuser -k -9 ${PORT}/tcp`, { stdio: 'ignore' }); log(`port ${PORT} libéré`); }
  catch (e) { /* rien n'écoutait : normal */ }
}

function start() {
  if (shuttingDown) return;
  freePort();
  log(`démarrage uvicorn :${PORT} (workers=${WORKERS}, cwd=${APP_DIR})`);
  startedAt = Date.now();
  child = spawn('python3',
    ['-m', 'uvicorn', 'umbra_main:app', '--host', '0.0.0.0', '--port', String(PORT), '--workers', WORKERS],
    { cwd: APP_DIR, env, stdio: 'inherit', detached: true });

  child.on('exit', (code, signal) => {
    if (shuttingDown) return;
    if (Date.now() - startedAt > 60000) backoff = 2000; // l'app a tenu → reset
    log(`uvicorn arrêté (code=${code} signal=${signal}) — relance dans ${backoff / 1000}s`);
    setTimeout(start, backoff);
    backoff = Math.min(backoff * 2, BACKOFF_MAX);
  });
  child.on('error', (err) => log(`erreur spawn: ${err.message}`));
}

function shutdown(sig) {
  shuttingDown = true;
  log(`signal ${sig} — arrêt propre`);
  if (child && child.pid) {
    try { process.kill(-child.pid, 'SIGTERM'); } catch (e) {}
    setTimeout(() => {
      try { process.kill(-child.pid, 'SIGKILL'); } catch (e) {}
      freePort();
      process.exit(0);
    }, 8000);
  } else { process.exit(0); }
}
process.on('SIGTERM', () => shutdown('SIGTERM'));
process.on('SIGINT', () => shutdown('SIGINT'));

log('Merito launcher démarré');
start();
