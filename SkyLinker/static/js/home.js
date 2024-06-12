document.addEventListener('DOMContentLoaded', () => {
  const scrollToBottomBtn = document.getElementById('scroll-to-bottom');
  const scrollIcon = scrollToBottomBtn.querySelector('i');

  // Function to toggle the scroll button and its action
  function toggleScrollButton() {
    if ((window.innerHeight + window.scrollY) >= document.body.offsetHeight - 1) {
      scrollIcon.classList.remove('fa-caret-down');
      scrollIcon.classList.add('fa-caret-up');
    } else {
      scrollIcon.classList.remove('fa-caret-up');
      scrollIcon.classList.add('fa-caret-down');
    }
  }

  // Scroll to the bottom or top when the button is clicked
  scrollToBottomBtn.addEventListener('click', (event) => {
    event.preventDefault();

    if (scrollIcon.classList.contains('fa-caret-up')) {
      window.scrollTo({
        top: 0,
        behavior: 'smooth'
      });
    } else {
      window.scrollTo({
        top: document.body.scrollHeight,
        behavior: 'smooth'
      });
    }
  });

  // Check scroll position and toggle the button accordingly
  window.addEventListener('scroll', toggleScrollButton);
  toggleScrollButton();  // Initialize button state

  // Intersection Observer for animations on scroll
  const observer = new IntersectionObserver((entries, observer) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        observer.unobserve(entry.target);
      }
    });
  }, {
    threshold: 0.1
  });

  const elements = document.querySelectorAll('.animated');
  elements.forEach(el => observer.observe(el));
});
