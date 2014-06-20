(function ( $, window ) {
    var pluginName = "boxpath";
    var $w = $(window);
    var $d = $(document);
    var grid;
    
    function handleKeydown(e) {
	handlers = {
	    37: function moveLeft() { grid.moveRel(-1, 0); return false; },
	    38: function() { return grid.handleScrollUp(); },
	    39: function moveRight() { grid.moveRel(+1, 0); return false; },
	    40: function() { return grid.handleScrollDown(); }
	}
	function findHandler(keyCode) {
	    if (handlers.hasOwnProperty(keyCode)) {
		return handlers[keyCode];
	    }
	    return function() { return true; };
	}
	findHandler(e.keyCode)();
    }

    function fullcell(el) {
	return {
	    hasContentAbove: function() {
		var startOfScreen = $w.scrollTop();
		var startOfContent = el.offset().top - parseInt(el.css('margin-top'));
		return startOfContent < startOfScreen;
	    },
	    hasContentBelow: function() {
		var endOfScreen = ($w.scrollTop() + $w.height());
		var endOfContent = (el.offset().top + el.outerHeight(true)); // margin included twice, but should not matter.
		return endOfScreen < endOfContent;
	    },
	    el: el
	};
    }

    function emptycell() {
	return {
	    hasContentAbove: function() {
		return false;
	    },
	    hasContentBelow: function() {
		return false;
	    }
	};
    }
    
    grid = {
	cellHeight: 0,
	cellWidth: 0,
	rows: undefined,
	numcolumns: 0,
	updateCellValues: function() {
	    this.cellHeight = Math.max(
		$("aside, section, header, footer")
		    .map(function(idx, el) {return $(el).outerHeight();})
		    .get()
		    .reduce(function(a, b) { return Math.max(a, b); }, 0)
		,
		$w.height()
	    );
	    this.cellWidth = $w.width();
	},
	moveRel: function (xdiff, ydiff, options) {
	    var pos = this.getCoordinates();
	    this.moveTo({y: pos.y + ydiff, x: pos.x + xdiff});
	},
	moveTo: function(pos, options) {
	    if (pos.x < 0 || pos.y < 0) {
		return;
	    }
	    var ydiff = options.bottom ? this.getCell(pos).el.outerHeight() - $w.height() : 0;
	    $('html:not(:animated),body:not(:animated)').animate({
		scrollLeft: pos.x * this.cellWidth,
		scrollTop: pos.y * (this.cellHeight + ((pos.y) ? parseInt(this.getCell(pos).el.css('margin-top')) : 0) + ydiff)
	    }, 400);
	},
	getCoordinates: function() {
	    return {
		y: ~~(($d.scrollTop() + ($w.height()/2)) / this.cellHeight),
		x: ~~(($d.scrollLeft() + ($w.width()/2)) / this.cellWidth)
	    };
	},
	handleScrollDown: function() {
	    if (this.getCurrentCell().hasContentBelow()) {
		// There is still content in the current cell
		// that is below the currently visible part.
		// So, let the browser scroll as usual.
		return false;
	    }
	    this.moveRel(0, 1);
	    return true;
	},
	handleScrollUp: function() {
	    if (this.getCurrentCell().hasContentAbove()) {
		// There is still content in the current cell
		// that is above the currently visible part.
		// So, let the browser scroll as usual.
		return false;
	    }
	    this.moveRel(0, -1, {bottom: true});
	    return true;
	},
	getCurrentCell: function() {
	    return this.getCell(this.getCoordinates());
	},
	getCell: function(pos) {
	    var row;
	    if (pos.x < 0 || pos.x >= this.colunms) {
		return undefined;
	    }
	    if (pos.y < 0 || pos.y >= this.rows.length) {
		return undefined;
	    }
	    row = this.rows[pos.y];
	    if (pos.x >= row.length) {
		return emptycell();
	    } else {
		return fullcell(row[pos.x]);
	    }
	},
	establishCells: function() {
	    var that = this;
	    this.numcolumns = 0;
	    this.rows = [];
	    $('header, section, footer').each(function() {
		var section = $(this);
		var row = [section];
		that.rows[that.rows.length] = row;
		section.nextUntil('section', 'aside').each(function(idx) {
		    row[row.length] = $(this);
		});
		that.numcolumns = Math.max(that.numcolumns, row.length);
	    });
	},
	homogenizeCells: function() {
	    var that = this;
	    $('aside').css('display', 'none').css('position', 'absolute');
	    $('header, section, footer').each(function() {
		var section = $(this);
		var sec_off = section.offset();
		section.wrap("<div></div>");
		section.parent("div").height(that.cellHeight);
		section.nextUntil('section', 'aside').each(function(idx) {
		    ($(this)
		     .offset({top:sec_off.top, left:sec_off.left + $w.width() * (idx + 1)})
		     .width(section.width())
		     .css('display', 'block'));
		});
	    });
	}
    }

    $(window).load(function() {
	grid.establishCells();
	grid.updateCellValues();
	grid.homogenizeCells();
	$(document).keydown(handleKeydown);
    });
})(jQuery, window);
