$(function() {
    var min_height = (window.innerHeight
			- parseInt($('header').css('padding-top'))
			- parseInt($('header').css('padding-bottom')) + 'px');
    // $('header').css({'min-height': min_height});
    // $('section').css({'min-height': min_height});
    // $('footer').css({'min-height': min_height});
    $('div#main').css({'margin-left':  Math.min(300, window.innerWidth/6) + 'px'}).css({'margin-right':  Math.min(300, window.innerWidth/6) + 'px'});
    prettyPrint();

    // var $windows = $('section');
    // 
    // $windows.windows({
    //     snapping: true,
    //     snapSpeed: 300,
    //     snapInterval: 200,
    //     onScroll: function(s){},
    //     onSnapComplete: function($el){},
    //     onWindowEnter: function($el){}
    // });

});