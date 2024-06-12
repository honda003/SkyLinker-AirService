(function() {
  const menu = document.querySelector('#menu-icon');
  const navlist = document.querySelector('.navlist');

  const checkMenuVisibility = () => {
    const actualWidth = window.innerWidth || document.documentElement.clientWidth;
    if (actualWidth > 990) {
      menu.style.display = 'none';
      navlist.classList.remove('open');
    } else {
      menu.style.display = 'block';
    }
  };

  menu.onclick = () => {
    menu.classList.toggle('bx-x');
    navlist.classList.toggle('open');
  };

  window.addEventListener('scroll', () => {
    const header = document.querySelector('header');
    if (window.scrollY > 50) {
      header.classList.add('scrolled');
    } else {
      header.classList.remove('scrolled');
    }
  });

  window.addEventListener('resize', checkMenuVisibility);
  checkMenuVisibility(); // Initial check on load
})();
