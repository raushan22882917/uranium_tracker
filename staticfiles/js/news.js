// hero sec animation
gsap.registerPlugin(ScrollTrigger);

// Animate the large image section
gsap.from(".animate-large-img", {
  opacity: 0,
  y: 50,
  duration: 1.5,
  ease: "power4.out",
  scrollTrigger: {
    trigger: ".animate-large-img",
    start: "top 80%",
    toggleActions: "play none none none",
  },
});

// Animate the smaller image sections
gsap.from(".animate-small-imgs > *", {
  opacity: 0,
  y: 30,
  duration: 1,
  ease: "power4.out",
  stagger: 0.3,
  scrollTrigger: {
    trigger: ".animate-small-imgs",
    start: "top 80%",
    toggleActions: "play none none none",
  },
});

// trending sec Animation
// Include GSAP and ScrollTrigger first
gsap.registerPlugin(ScrollTrigger);

// Apply animations to each featured block
gsap.from(".trending-block", {
  opacity: 0,
  y: 50,
  duration: 1,
  stagger: 0.3,
  ease: "power2.out",
  scrollTrigger: {
    trigger: ".py-16",
    start: "top 80%",
    end: "bottom 60%",
    toggleActions: "play none none reverse",
    // markers:true
  },
});

// fission fresh uranium news sec Animation
document.addEventListener("DOMContentLoaded", function () {
  gsap.registerPlugin(ScrollTrigger);

  // Animate the headline
  gsap.from(".uranium-news-headline", {
    scrollTrigger: {
      trigger: ".uranium-news-headline",
      start: "top 80%",
      //   toggleActions: "play none none reverse",
    },
    y: 50,
    opacity: 0,
    duration: 1,
    ease: "power2.out",
  });

  // Animate the background image
  gsap.from(".uranium-news-background", {
    scrollTrigger: {
      trigger: ".uranium-news-background",
      start: "top 80%",
      //   toggleActions: "play none none reverse",
    },
    scale: 1.1,
    opacity: 0,
    duration: 1.5,
    ease: "power2.out",
  });

  // Animate the news cards
  gsap.from(".news-card", {
    scrollTrigger: {
      trigger: ".news-card",
      start: "top 80%",
      //   toggleActions: "play none none reverse",
    },
    y: 50,
    opacity: 0,
    duration: 1,
    stagger: 0.3,
    ease: "power2.out",
  });
});
