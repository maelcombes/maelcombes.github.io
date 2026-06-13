/* ══════════════════════════════════════════════
   main.js — Scripts communs à toutes les pages
══════════════════════════════════════════════ */

/* ── Curseur custom ── */
const dot  = document.getElementById('cursor-dot');
const ring = document.getElementById('cursor-ring');

if (dot && ring) {
  let mx = 0, my = 0, rx = 0, ry = 0;

  document.addEventListener('mousemove', e => {
    mx = e.clientX;
    my = e.clientY;
  });

  const animCursor = () => {
    rx += (mx - rx) * .15;
    ry += (my - ry) * .15;
    dot.style.left  = mx + 'px';
    dot.style.top   = my + 'px';
    ring.style.left = rx + 'px';
    ring.style.top  = ry + 'px';
    requestAnimationFrame(animCursor);
  };
  animCursor();

  document.querySelectorAll('a, button, .project-card, .hnav-card, .mission-card, .alt-card').forEach(el => {
    el.addEventListener('mouseenter', () => document.body.classList.add('cursor-grow'));
    el.addEventListener('mouseleave', () => document.body.classList.remove('cursor-grow'));
  });
}

/* ── Reveal au scroll ── */
const revealEls = document.querySelectorAll('.reveal');
if (revealEls.length) {
  const revealObs = new IntersectionObserver(entries => {
    entries.forEach(e => {
      if (e.isIntersecting) {
        e.target.classList.add('visible');
        revealObs.unobserve(e.target);
      }
    });
  }, { threshold: .12 });
  revealEls.forEach(r => revealObs.observe(r));
}

/* ── Navbar : scroll shadow ── */
const navbar = document.getElementById('navbar');
if (navbar) {
  window.addEventListener('scroll', () => {
    navbar.style.boxShadow = window.scrollY > 10
      ? '0 4px 24px rgba(0,0,0,.4)'
      : 'none';
  }, { passive: true });
}

/* ── Menu burger (mobile) ── */
const burger = document.getElementById('burger');
if (burger) {
  burger.addEventListener('click', () => {
    document.body.classList.toggle('nav-mobile-open');
  });
  // Fermer si on clique sur un lien
  document.querySelectorAll('.nav-links a').forEach(link => {
    link.addEventListener('click', () => {
      document.body.classList.remove('nav-mobile-open');
    });
  });
}

/* ── Année footer ── */
const yearEl = document.getElementById('year');
if (yearEl) yearEl.textContent = new Date().getFullYear();
