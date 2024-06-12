$(document).ready(function(){
    // Select all links with hashes within #navbar
    $('#navbar a[href*="#"]').on('click', function(e) {
        // Prevent default anchor click behavior
        e.preventDefault();

        // Store hash
        var target = this.hash;
        var $target = $(target);

        // Scroll and show the section smoothly
        $('html, body').animate({
            'scrollTop': $target.offset().top
        }, 1000, 'swing', function () {
            window.location.hash = target;
        });
    });
});

document.addEventListener('DOMContentLoaded', function() {
    const navbar = document.getElementById('navbar');
    const footer = document.querySelector('footer');

    function adjustNavbarPosition() {
        const scrollPosition = window.pageYOffset;
        const navbarHeight = navbar.offsetHeight;
        const footerTop = footer.offsetTop;
        const distanceFromTopOfFooterToTopOfNavbar = footerTop - navbarHeight - 100;
        const viewportWidth = window.innerWidth;

        // Check if the viewport width is greater than 768px
        if (viewportWidth > 768) {
            // Apply fixed or absolute positioning based on scroll position
            if (scrollPosition > distanceFromTopOfFooterToTopOfNavbar) {
                navbar.style.position = 'absolute';
                navbar.style.top = `${distanceFromTopOfFooterToTopOfNavbar}px`;
            } else {
                navbar.style.position = 'fixed';
                navbar.style.top = '0';
            }
        } else {
            // Reset positioning for smaller viewports
            navbar.style.position = 'static';
        }
    }

    window.addEventListener('scroll', adjustNavbarPosition);
    window.addEventListener('resize', adjustNavbarPosition);
});
