function CatsopResultsLayer (stack, scale) {
  this.stack = stack;
  this.scale = scale; // CATSOP scale relative to stack (from BlockInfo)
  this.opacity = 0.5;
  this.radius = 3;

  // Create container, aligned to the upper left
  this.view = document.createElement("div");
  this.view.className = "catsop-layer";

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
  var mag = Math.pow(2, this.scale - this.stack.s);

  for (var hash in this.slices) {
    var slice = this.slices[hash];
    if (slice.z === this.stack.z) {
      slice.$img
          .css('left',  mag * slice.x - this.stack.xc)
          .css('top', mag * slice.y - this.stack.yc)
          .css('width', mag * slice.width)
          .css('height', mag * slice.height)
          .css('display', ''); // Show the slice, but don't override CSS hides.
    } else {
      slice.$img.hide();
    }
  }

  if (completionCallback) {
      completionCallback();
  }
};

CatsopResultsLayer.prototype.refresh = function () {
  this.redraw();
};

CatsopResultsLayer.prototype.unregister = function () {
  this.stack.getView().removeChild(this.view);
};

CatsopResultsLayer.prototype.clearSlices = function () {
  $(this.view).empty();
  this.slices = {};
};

CatsopResultsLayer.prototype.addSlice = function (slice, status) {
  if (slice.hash in this.slices) {
    var $sliceImg = this.slices[slice.hash].$img;
    $sliceImg.addClass(status);
    return $sliceImg;
  }

  var $sliceImg = $('<img class="slice-mask slice-hash-' + slice.hash + '" />')
      .hide()
      .css('-webkit-mask-box-image', 'url("' +
          [django_url + 'sopnet', project.id, 'stack', this.stack.getId(), 'slice', slice.hash, 'alpha_mask'].join('/')  +
          '") 0 stretch')
      .addClass(status)
      .appendTo($(this.view));
  if (slice.in_solution) $sliceImg.addClass('in-solution');
  this.slices[slice.hash] = {
    x: slice.box[0],
    y: slice.box[1],
    z: slice.section,
    width: slice.box[2] - slice.box[0],
    height: slice.box[3] - slice.box[1],
    $img: $sliceImg};
  this.redraw();
  return $sliceImg;
};

// Namespace for overlays extending CatsopResultsLayer
CatsopResultsLayer.Overlays = {};

CatsopResultsLayer.Overlays.Assemblies = function (stack, scale) {
  CatsopResultsLayer.call(this, stack, scale);

  this.old_z = null;
};

CatsopResultsLayer.Overlays.Assemblies.prototype = Object.create(CatsopResultsLayer.prototype);

CatsopResultsLayer.Overlays.Assemblies.prototype.getLayerName = function () {
  return "CATSOP assemblies";
};

CatsopResultsLayer.Overlays.Assemblies.prototype.redraw = function (completionCallback) {
  if (this.stack.z != this.old_z) {
    this.old_z = this.stack.z;
    this.refresh();
  }

  CatsopResultsLayer.prototype.redraw.call(this, completionCallback);
};

CatsopResultsLayer.Overlays.Assemblies.prototype.refresh = function () {
  var viewBox = this.stack.createStackViewBox();
  var self = this;
  requestQueue.register(django_url + 'sopnet/' + project.id + '/stack/' + this.stack.getId() +
          '/slices/by_bounding_box',
      'POST',
      {
          min_x: viewBox.min.x,
          min_y: viewBox.min.y,
          max_x: viewBox.max.x,
          max_y: viewBox.max.y,
          z: this.stack.z
      },
      jsonResponseHandler((function (json) {
        var czer = new Colorizer();
        json.slices.forEach(function (slice) {
          var sliceImg = self.addSlice(slice, 'active');
          if (!(slice.in_solution in CatsopResultsLayer.assemblyColors)){
            CatsopResultsLayer.assemblyColors[slice.in_solution] = czer.pickColor().getStyle();
          }

          sliceImg.css('background-color', CatsopResultsLayer.assemblyColors[slice.in_solution]);
        });
      })));
};

CatsopResultsLayer.assemblyColors = {};
