window.addEventListener('load', function() {
	var bg = document.querySelector('.background');
	/*bg.classList.add('loaded');*/
});

var carouselIndex = 0;

function moveCarousel() {
   var carouselImages = document.getElementById("carousel-images");
   carouselImages.style.left = -carouselIndex * 100 / 3 + "%";
}

document.getElementById("prev-button").addEventListener("click", function() {
   carouselIndex--;
   if(carouselIndex < 0) {
      carouselIndex = 2;
   }
   moveCarousel();
});

document.getElementById("next-button").addEventListener("click", function() {
   carouselIndex++;
   if(carouselIndex > 2) {
      carouselIndex = 0;
   }
   moveCarousel();
});

setInterval(function() {
   carouselIndex++;
   if(carouselIndex > 2) {
      carouselIndex = 0;
   }
   moveCarousel();
}, 5000);