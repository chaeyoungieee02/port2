const currentPath = window.location.pathname.replace(/\\/g, "/");
const isProjectPage = currentPath.includes("/blender/") || currentPath.includes("/rotoscope/");
const isDirectVisit = !document.referrer || !document.referrer.includes(window.location.host);

if (isProjectPage && isDirectVisit) {
  window.location.replace("../index.html");
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
const focusPlanet = document.getElementById("focusPlanet");
const summaryAge = document.getElementById("summaryAge");
const selectedPlanetName = document.getElementById("selectedPlanetName");
const yearsValue = document.getElementById("yearsValue");
const weeksValue = document.getElementById("weeksValue");
const daysValue = document.getElementById("daysValue");
const planetValues = {
  Mercury: document.getElementById("mercuryValue"),
  Venus: document.getElementById("venusValue"),
  Earth: document.getElementById("earthValue"),
  Mars: document.getElementById("marsValue"),
  Jupiter: document.getElementById("jupiterValue"),
  Saturn: document.getElementById("saturnValue"),
  Uranus: document.getElementById("uranusValue"),
  Neptune: document.getElementById("neptuneValue"),
  Pluto: document.getElementById("plutoValue"),
};

if (ageInput && calcBtn && focusPlanet && summaryAge && selectedPlanetName && yearsValue && weeksValue && daysValue) {
  const planets = [
    { name: "Mercury", period: 0.24 },
    { name: "Venus", period: 0.62 },
    { name: "Earth", period: 1 },
    { name: "Mars", period: 1.88 },
    { name: "Jupiter", period: 11.86 },
    { name: "Saturn", period: 29.46 },
    { name: "Uranus", period: 84.01 },
    { name: "Neptune", period: 164.8 },
    { name: "Pluto", period: 248 },
  ];

  function updatePlanetCards(earthAge) {
    planets.forEach((planet) => {
      const element = planetValues[planet.name];
      if (!element) return;
      const planetYears = earthAge / planet.period;
      element.textContent = planetYears.toFixed(2);
    });
  }

  function updateSelectedOutput(planetName, planetYears) {
    selectedPlanetName.textContent = planetName;
    yearsValue.textContent = planetYears.toFixed(2);
    weeksValue.textContent = Math.round(planetYears * 52.1786);
    daysValue.textContent = Math.round(planetYears * 365.25);
  }

  function calculateAge() {
    const earthAge = parseFloat(ageInput.value);
    if (Number.isNaN(earthAge) || earthAge < 0) {
      selectedPlanetName.textContent = "Earth";
      yearsValue.textContent = "0.00";
      weeksValue.textContent = "0";
      daysValue.textContent = "0";
      return;
    }

    summaryAge.textContent = earthAge.toFixed(2);
    updatePlanetCards(earthAge);

    const selected = planets.find((planet) => planet.name === focusPlanet.value) || planets[2];
    const planetYears = earthAge / selected.period;
    updateSelectedOutput(selected.name, planetYears);
  }

  calcBtn.addEventListener("click", calculateAge);
  focusPlanet.addEventListener("change", calculateAge);
  ageInput.addEventListener("input", () => {
    if (ageInput.value !== "") calculateAge();
  });
  calculateAge();
}
