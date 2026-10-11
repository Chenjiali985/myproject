// 移动端导航折叠
document.getElementById('nav-toggle')?.addEventListener('click', () => {
  document.getElementById('site-nav').classList.toggle('open');
});

// 点击后自动收起
document.querySelectorAll('#site-nav a').forEach((link) => {
  link.addEventListener('click', () => {
    document.getElementById('site-nav')?.classList.remove('open');
  });
});
