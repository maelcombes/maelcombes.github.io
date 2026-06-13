/* ══════════════════════════════════════════════
   main.js — Maël Combes Peirache Portfolio
══════════════════════════════════════════════ */

/* ── Curseur custom ── */
const dot  = document.getElementById('cursor-dot');
const ring = document.getElementById('cursor-ring');
if (dot && ring) {
  let mx = 0, my = 0, rx = 0, ry = 0;
  document.addEventListener('mousemove', e => { mx = e.clientX; my = e.clientY; });
  const tick = () => {
    rx += (mx - rx) * .15; ry += (my - ry) * .15;
    dot.style.left  = mx + 'px'; dot.style.top  = my + 'px';
    ring.style.left = rx + 'px'; ring.style.top = ry + 'px';
    requestAnimationFrame(tick);
  };
  tick();
  document.querySelectorAll('a, button, .proj-card, .hcard, .mission, .formation-item').forEach(el => {
    el.addEventListener('mouseenter', () => document.body.classList.add('cursor-grow'));
    el.addEventListener('mouseleave', () => document.body.classList.remove('cursor-grow'));
  });
}

/* ── Reveal au scroll ── */
const reveals = document.querySelectorAll('.reveal');
if (reveals.length) {
  const obs = new IntersectionObserver(entries => {
    entries.forEach(e => { if (e.isIntersecting) { e.target.classList.add('visible'); obs.unobserve(e.target); } });
  }, { threshold: .1 });
  reveals.forEach(r => obs.observe(r));
}

/* ── Navbar shadow au scroll ── */
const nav = document.getElementById('navbar');
if (nav) {
  window.addEventListener('scroll', () => {
    nav.style.boxShadow = window.scrollY > 8 ? '0 4px 28px rgba(0,0,0,.45)' : 'none';
  }, { passive: true });
}

/* ── Menu burger (mobile) ── */
const burger = document.getElementById('burger');
if (burger) {
  burger.addEventListener('click', () => document.body.classList.toggle('nav-mobile-open'));
  document.querySelectorAll('.nav-links a').forEach(l => l.addEventListener('click', () => document.body.classList.remove('nav-mobile-open')));
}

/* ── Année footer ── */
const yr = document.getElementById('year');
if (yr) yr.textContent = new Date().getFullYear();
