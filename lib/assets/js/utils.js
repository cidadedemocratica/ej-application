
// function that enables fadein/fadeout of lower nav
function enableFadeBottomDiv() {
    $(document).ready(function () {
        var lastScrollTop = 0;

        $("div").scroll(function () {
            var windowWidth = window.innerWidth;
            var st = $(this).scrollTop();
            if (lastScrollTop < st - 3) {
                $('.Header-lowerNav').fadeOut();
                $('.Header-lowerNotLogged').fadeOut();
                if (windowWidth <= 550) {
                    $('.Page').css('padding', '75px 0 0 0');
                } else {
                    $('.Page').css('padding', '100px 0 0 0');
                }
            }
            else if (lastScrollTop > st + 3) {
                $('.Header-lowerNav').fadeIn();
                $('.Header-lowerNotLogged').fadeIn();
                if (windowWidth <= 550) {
                    $('.Page').css('padding', '75px 0 70px 0');
                } else {
                    $('.Page').css('padding', '100px 0 70px 0');
                }
            }
            lastScrollTop = st;
        });
    });
}
enableFadeBottomDiv();