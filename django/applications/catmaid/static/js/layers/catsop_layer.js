function CatsopResultsLayer (stack) {
  this.stack = stack;
  this.opacity = 1;
  this.radius = 3;

  // Create container, aligned to the upper left
  this.view = document.createElement("div");
  this.view.style.position = "absolute";
  this.view.style.left = 0;
  this.view.style.top = 0;

  this.slices = {};

  // Append it to DOM
  stack.getView().appendChild(this.view);
}

CatsopResultsLayer.prototype = {};

CatsopResultsLayer.prototype.getLayerName = function () {
  return "CATSOP results";
};

CatsopResultsLayer.prototype.setOpacity = function (val) {
  this.view.style.opacity = val;
  this.opacity = val;
};

CatsopResultsLayer.prototype.getOpacity = function () {
  return this.opacity;
};

CatsopResultsLayer.prototype.resize = function () {
  this.redraw();
};

CatsopResultsLayer.prototype.redraw = function (completionCallback) {
  var mag = Math.pow(2, -this.stack.s);

  for (var hash in this.slices) {
    var slice = this.slices[hash];
    if (slice.z === this.stack.z) {
      slice.$img
          .css('left',  mag * slice.x - this.stack.xc)
          .css('top', mag * slice.y - this.stack.yc)
          .css('width', mag * slice.width)
          .css('height', mag * slice.height)
          .show();
    } else {
      slice.$img.hide();
    }
  }

  if (completionCallback) {
      completionCallback();
  }
};

CatsopResultsLayer.prototype.unregister = function () {
  this.stack.getView().removeChild(this.view);
};

CatsopResultsLayer.prototype.clearSlices = function () {
  $(this.view).empty();
  this.slices = {};
};

CatsopResultsLayer.prototype.addSlice = function (slice) {
  var $sliceImg = $('<img src="' + slice.mask + '" />')
      .hide()
      .css('position', 'absolute')
      .appendTo($(this.view));
  this.slices[slice.hash] = {
    x: slice.box[0],
    y: slice.box[1],
    z: slice.section,
    width: slice.box[2] - slice.box[0],
    height: slice.box[3] - slice.box[1],
    $img: $sliceImg};
  this.redraw();
};