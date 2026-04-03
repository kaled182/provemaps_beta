document.addEventListener("DOMContentLoaded", () => {
  const button = document.getElementById("userMenuButton");
  const menu = document.getElementById("userMenuDropdown");
  const arrow = document.getElementById("userMenuArrow");

  if (button && menu) {
    button.addEventListener("click", (e) => {
      e.stopPropagation();
      menu.classList.toggle("hidden");
      arrow.style.transform = menu.classList.contains("hidden") ? "rotate(0deg)" : "rotate(180deg)";
    });

    document.addEventListener("click", (e) => {
      if (!button.contains(e.target) && !menu.contains(e.target)) {
        menu.classList.add("hidden");
        arrow.style.transform = "rotate(0deg)";
      }
    });

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        menu.classList.add("hidden");
        arrow.style.transform = "rotate(0deg)";
      }
    });
  }
});