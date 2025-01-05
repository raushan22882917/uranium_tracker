// Add animation to elements
document.addEventListener("DOMContentLoaded", (event) => {
  document.querySelectorAll(".animate__animated").forEach((element, index) => {
    element.style.animationDelay = `${index * 0.2}s`;
  });
});

// ==============================================================================================
// The Atomic Portfolio
// ==============================================================================================
// Data for the charts
const mostFollowedStocks = {
  labels: ["DNN", "NXE", "UEC", "LOT.AX", "CCJ"],
  data: [1.71, 6.4, 5.37, 0.22, 42.61],
};

const topGainers = {
  labels: ["AEC.V", "UROY", "DNN", "UEC", "DML.TO", "FMC.V", "LMRXF", "NXE"],
  data: [0.07, 2.32, 1.71, 5.37, 2.29, 0.09, 0.42, 6.4],
};

const topLosers = {
  labels: [
    "CUL.AX",
    "GTR.AX",
    "ENR.AX",
    "RDM.AX",
    "ERA.AX",
    "DYL.AX",
    "PDN.AX",
    "TOE.AX",
  ],
  data: [0.0, 0.0, 0.47, 0.13, 0.02, 1.0, 9.73, 0.24],
};

// Function to create a radar chart
function createRadarChart(
  ctx,
  labels,
  data,
  label,
  backgroundColor,
  borderColor
) {
  return new Chart(ctx, {
    type: "radar",
    data: {
      labels: labels,
      datasets: [
        {
          label: label,
          data: data,
          backgroundColor: backgroundColor,
          borderColor: borderColor,
          borderWidth: 2,
          pointBackgroundColor: borderColor,
          pointBorderColor: "#fff",
          pointHoverBackgroundColor: "#fff",
          pointHoverBorderColor: borderColor,
        },
      ],
    },
    options: {
      responsive: true,
      elements: {
        line: {
          tension: 0.4,
        },
      },
      scales: {
        r: {
          grid: {
            color: "#444",
          },
          angleLines: {
            color: "#444",
          },
          ticks: {
            display: false,
          },
        },
      },
    },
  });
}

// Create the charts
document.addEventListener("DOMContentLoaded", () => {
  const mostFollowedChart = createRadarChart(
    document.getElementById("mostFollowedChart").getContext("2d"),
    mostFollowedStocks.labels,
    mostFollowedStocks.data,
    "Most Followed Stocks",
    "rgba(255, 193, 7, 0.5)",
    "rgba(255, 193, 7, 1)"
  );

  const topGainersChart = createRadarChart(
    document.getElementById("topGainersChart").getContext("2d"),
    topGainers.labels,
    topGainers.data,
    "Top Gainers",
    "rgba(40, 167, 69, 0.5)",
    "rgba(40, 167, 69, 1)"
  );

  const topLosersChart = createRadarChart(
    document.getElementById("topLosersChart").getContext("2d"),
    topLosers.labels,
    topLosers.data,
    "Top Losers",
    "rgba(220, 53, 69, 0.5)",
    "rgba(220, 53, 69, 1)"
  );

  // GSAP Animation
  gsap.from(".chart-card, .info-card", {
    duration: 1.5,
    opacity: 0,
    y: 50,
    stagger: 0.3,
    ease: "power2.out",
  });
});

// =================================================================================
// Sidenav scrolling
// =================================================================================
document.querySelectorAll(".sidenav a").forEach((anchor) => {
  anchor.addEventListener("click", function (e) {
    e.preventDefault();
    const targetId = this.getAttribute("href").substring(1);
    const targetElement = document.getElementById(targetId);
    window.scrollTo({
      top: targetElement.offsetTop - 110, // Adjust 70 to your fixed header height
      behavior: "smooth",
    });
  });
});

// animation 
// Ensure GSAP and ScrollTrigger are included
gsap.registerPlugin(ScrollTrigger);

// Apply the animation to the sidenav
gsap.from(".sidenav-animation", {
  y: -100,
  opacity: 0,
  duration: 1,
  ease: "power2.out",
  scrollTrigger: {
    trigger: ".sidenav-animation",
    start: "top 80%",
    end: "top 60%",
    toggleActions: "play none none reverse",
  },
});

// =================================================================================