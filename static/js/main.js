const toggle = document.querySelector('.menu-toggle');
const nav = document.querySelector('.site-header nav');

if (toggle && nav) {
  toggle.addEventListener('click', () => {
    const isOpen = nav.classList.toggle('is-open');
    toggle.setAttribute('aria-expanded', String(isOpen));
  });
  nav.querySelectorAll('a').forEach((link) => {
    link.addEventListener('click', () => nav.classList.remove('is-open'));
  });
}

document.querySelectorAll('.toast').forEach((toast) => {
  setTimeout(() => toast.remove(), 3000);
});
