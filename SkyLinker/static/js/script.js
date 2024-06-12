let menu = document.querySelector('#menu-icon');
let navlist = document.querySelector('.navlist');

menu.onclick = () => {
  menu.classList.toggle('bx-x');
  navlist.classList.toggle('open');
}

window.addEventListener('scroll', function () {
  var header = document.querySelector('header');
  if (window.scrollY > 50) { // Adjust this value based on your needs
    header.classList.add('scrolled');
  } else {
    header.classList.remove('scrolled');
  }
});
