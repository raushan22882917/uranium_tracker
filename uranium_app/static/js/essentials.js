// Animation
// sec 1
// Register GSAP ScrollTrigger plugin
gsap.registerPlugin(ScrollTrigger);

// Left content animation (text)
gsap.from(".hero", {
  y: -100,
  opacity: 0,
  duration: 1,
  ease: "power2.out",
  scrollTrigger: {
    trigger: ".frank",
    start: "top 80%",
    end: "top 60%",
    toggleActions: "play none none reverse",
  },
});

// gsap.from("p", {
//   y: -100,
//   opacity: 0,
//   duration: 1.2,
//   ease: "power2.out",
//   scrollTrigger: {
//     trigger: "p",
//     start: "top 80%",
//     end: "top 60%",
//     toggleActions: "play none none reverse",
//   },
// });

// Right content animation (atom container)
gsap.from(".atom-container", {
  scale: 0,
  opacity: 0,
  duration: 1,
  ease: "power2.out",
  scrollTrigger: {
    trigger: ".atom-container",
    start: "top 80%",
    end: "top 60%",
    toggleActions: "play none none reverse",
  },
});



// sec 1 animation
gsap.registerPlugin(ScrollTrigger);

// Animate Heading
// gsap.from(".heading-uranium", {
//   // y: -50,
//   opacity: 0,
//   duration: 1,
//   ease: "power2.out",
//   scrollTrigger: {
//     trigger: ".heading-uranium",
//     start: "top 80%",
//     end: "top 60%",
//     // toggleActions: "play none none reverse",
//   },
// });

// Animate Physical Properties Card
gsap.from(".sec-1", {
  y: -100,
  opacity: 0,
  duration: 1,
  ease: "power2.out",
  delay:0.3,
  scrollTrigger: {
    trigger: ".sec-1",
    start: "top 80%",
    end: "top 60%",
    // toggleActions: "play none none reverse",
  },
});