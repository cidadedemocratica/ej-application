$(document).ready(function () {
  var pallet = document.querySelector("div[class*=Palette]").className;
  if(pallet) {
    var regex = /^.*Palette([A-Z]\w+)\-?\w*/g;
    var pallet_color = regex.exec(pallet)[1];
    var navMenu = document.querySelector(".NavMenu");
    navMenu.classList.add("Palette" + pallet_color);
  }
});
