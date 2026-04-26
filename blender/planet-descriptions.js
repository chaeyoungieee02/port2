const planetDescriptions = {
  mercury: {
    name: "Mercury",
    overview: "Mercury is the smallest planet and closest to the Sun. It has a rocky surface filled with craters.",
    temp: "-173°C to 427°C",
    color: "Gray-brown rocky surface",
    characteristic: "Fastest orbit around the Sun (88 days)",
    accent: "linear-gradient(145deg, #9da3aa, #5e6368)",
    video: ""
  },
  venus: {
    name: "Venus",
    overview: "Venus is similar in size to Earth but has a thick, toxic atmosphere and extreme heat.",
    temp: "Around 465°C",
    color: "Pale yellow to creamy white",
    characteristic: "Hottest planet because of a runaway greenhouse effect",
    accent: "linear-gradient(145deg, #d8c18f, #9c7b3a)",
    video: ""
  },
  earth: {
    name: "Earth",
    overview: "Earth is the only known planet with life, liquid water oceans, and a breathable atmosphere.",
    temp: "Average about 15°C",
    color: "Blue oceans, green-brown land, white clouds",
    characteristic: "Only known world that supports life",
    accent: "linear-gradient(145deg, #4fa5ff, #1f4f93)",
    video: ""
  },
  mars: {
    name: "Mars",
    overview: "Mars is a cold desert world with large volcanoes, canyons, and signs of ancient water.",
    temp: "Average about -63°C",
    color: "Reddish-brown",
    characteristic: "Known as the Red Planet because of iron oxide dust",
    accent: "linear-gradient(145deg, #ff7b52, #9f2d1d)",
    video: ""
  },
  jupiter: {
    name: "Jupiter",
    overview: "Jupiter is the largest planet, a gas giant with strong storms and many moons.",
    temp: "About -145°C (cloud tops)",
    color: "Bands of white, tan, and orange",
    characteristic: "Home of the Great Red Spot storm",
    accent: "linear-gradient(145deg, #d5b08b, #8f5f37)",
    video: ""
  },
  saturn: {
    name: "Saturn",
    overview: "Saturn is a gas giant best known for its bright ring system made of ice and rock.",
    temp: "About -178°C (cloud tops)",
    color: "Pale gold and beige",
    characteristic: "Most visible ring system in the Solar System",
    accent: "linear-gradient(145deg, #e3c58d, #a7834a)",
    video: ""
  },
  uranus: {
    name: "Uranus",
    overview: "Uranus is an ice giant that rotates on its side, giving it extreme seasons.",
    temp: "About -224°C",
    color: "Light cyan-blue",
    characteristic: "Rotates with an extreme tilt of about 98°",
    accent: "linear-gradient(145deg, #95e6f1, #4aa2af)",
    video: ""
  },
  neptune: {
    name: "Neptune",
    overview: "Neptune is a distant ice giant with deep blue color and very strong winds.",
    temp: "About -214°C",
    color: "Deep blue",
    characteristic: "Fastest winds in the Solar System",
    accent: "linear-gradient(145deg, #4978ff, #1b2f8e)",
    video: ""
  },
  pluto: {
    name: "Pluto",
    overview: "Pluto is a dwarf planet in the Kuiper Belt with icy plains and a thin atmosphere.",
    temp: "About -229°C",
    color: "Brown, tan, and white icy regions",
    characteristic: "Classified as a dwarf planet",
    accent: "linear-gradient(145deg, #b6a28c, #6f5d4b)",
    video: ""
  }
};

const detailLabels = {
  temp: "Temp",
  color: "Color",
  characteristic: "Characteristic"
};

const initPlanetDescriptionPage = () => {
  const container = document.querySelector(".planet-desc");
  if (!container) return;

  const defaultPlanet = container.dataset.defaultPlanet || "earth";
  let currentPlanet = planetDescriptions[defaultPlanet] ? defaultPlanet : "earth";
  let currentDetail = "temp";

  const planetButtons = container.querySelectorAll("[data-planet]");
  const detailButtons = container.querySelectorAll("[data-detail]");
  const nameEl = container.querySelector("#planetName");
  const overviewEl = container.querySelector("#planetOverview");
  const detailLabelEl = container.querySelector("#planetDetailLabel");
  const detailValueEl = container.querySelector("#planetDetailValue");
  const iconEl = container.querySelector("#planetIcon");
  const videoEl = container.querySelector("#planetVideo");
  const videoSourceEl = container.querySelector("#planetVideoSource");
  const videoNoteEl = container.querySelector("#planetVideoNote");

  const render = () => {
    const data = planetDescriptions[currentPlanet];
    nameEl.textContent = data.name;
    overviewEl.textContent = data.overview;
    detailLabelEl.textContent = `${detailLabels[currentDetail]}:`;
    detailValueEl.textContent = data[currentDetail];
    iconEl.style.background = data.accent;

    planetButtons.forEach((button) => {
      button.classList.toggle("active", button.dataset.planet === currentPlanet);
    });
    detailButtons.forEach((button) => {
      button.classList.toggle("active", button.dataset.detail === currentDetail);
    });

    if (data.video) {
      videoSourceEl.src = data.video;
      videoEl.load();
      videoNoteEl.textContent = "";
    } else {
      videoSourceEl.removeAttribute("src");
      videoEl.load();
      videoNoteEl.textContent = `Add MP4 file for ${data.name} later (example: media/${data.name.toLowerCase()}.mp4).`;
    }
  };

  planetButtons.forEach((button) => {
    button.addEventListener("click", () => {
      currentPlanet = button.dataset.planet;
      render();
    });
  });

  detailButtons.forEach((button) => {
    button.addEventListener("click", () => {
      currentDetail = button.dataset.detail;
      render();
    });
  });

  render();
};

initPlanetDescriptionPage();
