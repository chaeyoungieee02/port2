const currentPath = window.location.pathname.replace(/\\/g, "/");
const isProjectPage = currentPath.includes("/blender/") || currentPath.includes("/rotoscope/");
const isRootHome = currentPath.endsWith("/index.html") && !isProjectPage;

if (isRootHome) {
  sessionStorage.setItem("portfolio-space-home-visited", "true");
} else if (sessionStorage.getItem("portfolio-space-home-visited") !== "true") {
  window.location.replace(isProjectPage ? "../index.html" : "index.html");
}

// Dropdown mobile toggle
const dropdownButtons = document.querySelectorAll(".dropdown > .dropdown-toggle");

dropdownButtons.forEach((btn) => {
  btn.addEventListener("click", (e) => {
    if (window.matchMedia("(max-width: 1080px)").matches) {
      e.preventDefault();
      const parent = btn.parentElement;
      const isOpen = parent.classList.contains("open");

      document.querySelectorAll(".dropdown.open").forEach((d) => {
        d.classList.remove("open");
        const b = d.querySelector(".dropdown-toggle");
        if (b) b.setAttribute("aria-expanded", "false");
      });

      if (!isOpen) {
        parent.classList.add("open");
        btn.setAttribute("aria-expanded", "true");
      }
    }
  });
});

document.addEventListener("click", (e) => {
  if (!e.target.closest(".dropdown")) {
    document.querySelectorAll(".dropdown.open").forEach((d) => {
      d.classList.remove("open");
      const b = d.querySelector(".dropdown-toggle");
      if (b) b.setAttribute("aria-expanded", "false");
    });
  }
});

// Earth Age Calculator (works only where elements exist)
const ageInput = document.getElementById("age");
const calcBtn = document.getElementById("calcBtn");
const result = document.getElementById("result");

if (ageInput && calcBtn && result) {
  const planets = [
    { name: "Mercury", period: 0.24 },
    { name: "Venus", period: 0.62 },
    { name: "Mars", period: 1.88 },
    { name: "Jupiter", period: 11.86 },
    { name: "Saturn", period: 29.46 },
    { name: "Uranus", period: 84.01 },
    { name: "Neptune", period: 164.8 },
  ];

  calcBtn.addEventListener("click", () => {
    const earthAge = parseFloat(ageInput.value);
    if (Number.isNaN(earthAge) || earthAge < 0) {
      result.textContent = "Please enter a valid age.";
      return;
    }
    const lines = planets.map((p) => `${p.name}: ${(earthAge / p.period).toFixed(2)} years`);
    result.textContent = `Earth: ${earthAge.toFixed(2)} years\n` + lines.join("\n");
  });
}
