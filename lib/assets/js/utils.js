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

function changeMenuPalette() {
  var paletteNode = document.querySelector("div[class$=Palette]");
  if (paletteNode) {
    var palette = '';
    paletteNode.classList.forEach((_class) => {
      if(/.*--.*(Palette)/.test(_class)) {
        palette = _class.split('--')[1];
      }
    });
    if (palette) {
      var navMenu = document.querySelector(".NavMenu--bluePalette");
      if (navMenu) {
        navMenu.classList.remove("NavMenu--" + palette);
        console.info("changing menu color based on conversation palette");
        navMenu.classList.add("NavMenu--" + palette);
      }
    }
  }
}


function observerMenuModal() {
  $(document).ready(function () {
    var targetNode = document.querySelector("body");
    var config = {attributes: true, childList: true, subtree: true};
    var callback = function(mutationsList, observer) {
      for(var mutation of mutationsList) {
        if (mutation.type == 'childList') {
          changeMenuPalette();
        }
      }
    };
    // Create an observer instance linked to the callback function
    var observer = new MutationObserver(callback);

    // Start observing the target node for configured mutations
    observer.observe(targetNode, config);
  });
}

observerMenuModal();
enableFadeBottomDiv();
