// function that enables fadein/fadeout of lower nav
function enableFadeBottomDiv() {
    $(document).ready(function () {
        var lastScrollTop = 0;
        function hideLowerNav(windowWidth) {
            if (windowWidth <= 550) {
                $('.Page').css({'padding': '45px 0 0 0', 'transition': 'padding 0.3s linear'});
            } else {
                $('.Page').css({'padding': '70px 0 0 0', 'transition': 'padding 0.3s linear'});
            }
        }
        function showLowerNav(windowWidth) {
            if (windowWidth <= 550) {
                $('.Page').css({'padding': '45px 0 45px 0', 'transition': 'padding 0.3s linear'});
            } else {
                $('.Page').css({'padding': '70px 0 45px 0', 'transition': 'padding 0.3s linear'});
            }
        }

        $("div").scroll(function () {
            var windowWidth = window.innerWidth;
            var st = $(this).scrollTop();
            if (lastScrollTop < st - 10) {
                $('.Header-lowerNav').fadeOut('fast', hideLowerNav(windowWidth));
                $('.Header-lowerNotLogged').fadeOut('fast', hideLowerNav(windowWidth));
            }

            if (lastScrollTop > st + 10) {
                $('.Header-lowerNav').fadeIn('fast', showLowerNav(windowWidth));
                $('.Header-lowerNotLogged').fadeIn('fast', showLowerNav(windowWidth));
            }
            lastScrollTop = st;
        });
    });
}

function openFileInput() {
  var input = document.querySelector(".FileInput input");
  if (input) {
    input.addEventListener("change", function(event){
      selectedFileElement = document.querySelector(".SelectedFile-name span");
      selectedFileElement.innerText = input.files[0].name;
    });
    input.click();
  }
}

function changeMenuPaletteOnReady() {
	$(document).ready(function () {
		changeMenuPaletteOnClick();
		let menu = document.querySelector("a[href^='/menu/']");
		var paletteNode = document.querySelector("div[class$=Palette]");
		let palette = '';
		if (paletteNode) {
			paletteNode.classList.forEach((_class) => {
				if(/.*--.*(Palette)/.test(_class)) {
					palette = _class.split('--')[1];
				}
			});
		}
		if (palette) {
			menu.href = "/menu/?palette=" + palette;
			console.log(menu.href);
		}
	});
}

function changeMenuPaletteOnClick() {
	let menu = document.querySelector("a[href^='/menu/']");
	var paletteNode = document.querySelector("div[class$=Palette]");
	let palette = '';
	if (paletteNode) {
		paletteNode.classList.forEach((_class) => {
			if(/.*--.*(Palette)/.test(_class)) {
				palette = _class.split('--')[1];
			}
		});
	}
	if (palette) {
		menu.href = "/menu/?palette=" + palette;
	}
}

changeMenuPaletteOnReady();
enableFadeBottomDiv();
