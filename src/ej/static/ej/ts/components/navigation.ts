import { component, Component } from "./base";
import { Cookies } from "../lib/dependencies";

@component("main-header")
class MainHeader extends Component {
  isMenuOpen: boolean;
  isProfileOpen: boolean;

  constructor(element) {
    super(element);
    this.isMenuOpen = false;
    this.isProfileOpen = false;
  }

  back() {
    window.history.back();
  }

  toggleProfile() {
    this.isProfileOpen ? this.closeProfile() : this.openProfile();
  }

  openProfile() {
    this.isProfileOpen = true;
    $("#show-floating-menu").removeClass("hide");
    this.closeMenu();
    this.createOverlay();
  }

  closeProfile() {
    this.isProfileOpen = false;
    $("#show-floating-menu").addClass("hide");
    if (!this.isMenuOpen) this.removeOverlay();
  }

  toggleMenu() {
    this.isMenuOpen ? this.closeMenu() : this.openMenu();
  }

  openMenu() {
    this.isMenuOpen = true;
    $(".page-menu").removeAttr("is-menu");
    $(".page-menu").attr("is-open", "");
    $("html").addClass("page-menu--disable-overflow");
    this.closeProfile();
    this.createOverlay();
  }

  closeMenu() {
    this.isMenuOpen = false;
    $(".page-menu").attr("is-open", null);
    $(".page-menu").attr("is-menu", "");
    $("html").removeClass("page-menu--disable-overflow");
    if (!this.isProfileOpen) this.removeOverlay();
  }

  removeOverlay() {
    $("#page-menu-overlay").remove();
  }

  createOverlay() {
    if ($(window).width() >= 560) return;
    if ($("#page-menu-overlay").length) return;

    let self = this;
    let overlay = document.createElement("div");
    $(overlay)
      .toggleClass("overlay")
      .attr("id", "page-menu-overlay")
      .on("click", () => {
        self.removeOverlay();
        self.closeMenu();
        self.closeProfile();
      });
    document.body.appendChild(overlay);
    return overlay;
  }
}

@component("page-menu")
class PageMenu extends Component {
  attributes = { "is-open": true };
  largefont: boolean;
  hicontrast: boolean;
  scaleFactor: number;

  init() {
    this.largefont = Cookies.get("largefont") === "y";
    this.hicontrast = Cookies.get("hicontrast") === "y";
    this.scaleFactor = 1.35;
    this.setContrast();
    if (
      this.largefont &&
      $("html").data("large-font") !== "                true"
    ) {
      this.makeFontsLarge();
    }
  }

  // TOGGLE MENU
  closeMenu() {
    $(".main-header")[0]["ej-component"].closeMenu();
    return false;
  }

  // TOGGLE CONTRASTS
  toggleContrast() {
    this.hicontrast = !this.hicontrast;
    if (this.hicontrast) {
      Cookies.set("hicontrast", "y", { path: "/" });
    }
    this.setContrast();
    this.closeMenu();
    return false;
  }

  // TOGGLE FONT SIZES
  toggleFontSize() {
    this.largefont ? this.makeFontsRegular() : this.makeFontsLarge();
    if (this.largefont) {
      Cookies.set("largefont", "y", { path: "/" });
    }
    this.closeMenu();
    return false;
  }

  makeFontsRegular() {
    $("*").each((_, elem) => this.restoreFontSize($(elem)));
    this.largefont = false;
  }

  makeFontsLarge() {
    this.largefont = true;
    let $main = $("html");
    $main.data("large-font", "true");

    $("body *")
      .map((_, elem) => this.storeFontSize($(elem)))
      .map((_, $elem) => this.scaleFont($elem, this.scaleFactor));
    this.storeFontSize($main);
    this.scaleFont($main, (2 * this.scaleFactor + 1) / 3);
  }

  // noinspection JSMethodCanBeStatic
  storeFontSize($elem) {
    $elem.data("original-font-size", {
      size: $elem.css("font-size"),
      hasOwnStyle: $elem[0].style.fontStyle != "",
    });
    return $elem;
  }

  // noinspection JSMethodCanBeStatic
  restoreFontSize($elem) {
    let data = $elem.data("original-font-size");
    Cookies.remove("largefont", { path: "/" });
    $("html").data("large-font", "false");

    if (data === undefined) {
      return;
    } else if (data.hasOwnStyle) {
      $elem.css("font-size", data.size);
    } else {
      $elem[0].style.fontSize = "";
    }
  }

  // noinspection JSMethodCanBeStatic
  scaleFont($elem, by) {
    let size = parseInt($elem.data("original-font-size").size),
      newSize = (by * size) | 0;
    if (size) {
      $elem.css("font-size", `${newSize}px`);
    }
    return $elem;
  }

  setContrast() {
    let $link = $("#main-css-link"),
      href = $link.attr("href");

    if (this.hicontrast) {
      $link.attr({ href: href.replace("main.css", "hicontrast.css") });
    } else {
      $link.attr({ href: href.replace("hicontrast.css", "main.css") });
      Cookies.remove("hicontrast", { path: "/" });
    }
  }
}
