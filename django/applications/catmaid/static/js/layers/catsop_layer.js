function CatsopResultsLayer (stack, segmentationStack, scale) {
  this.stack = stack;
  this.segmentationStack = segmentationStack;
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

CatsopResultsLayer.prototype.clear = function () {
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

CatsopResultsLayer.Overlays.Assemblies = function (stack, segmentationStack, scale) {
  CatsopResultsLayer.call(this, stack, segmentationStack, scale);

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
  requestQueue.register(django_url + 'sopnet/' + project.id + '/segmentation/' + this.segmentationStack +
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

CatsopResultsLayer.Overlays.Blocks = function (stack, segmentationStack, scale) {
  CatsopResultsLayer.call(this, stack, segmentationStack, scale);

  this.z_lim = null;
  this.regions = {};
  this.regionType = 'blocks';
  this.regionFlags = ['slices', 'segments'];
};

CatsopResultsLayer.Overlays.Blocks.prototype = Object.create(CatsopResultsLayer.prototype);

CatsopResultsLayer.Overlays.Blocks.prototype.getLayerName = function () {
  return "CATSOP " + this.regionType;
};

CatsopResultsLayer.Overlays.Blocks.prototype.redraw = function (completionCallback) {
  if (this.z_lim === null || this.z_lim.min > this.stack.z || this.z_lim.max <= this.stack.z) {
    this.z_lim = {min: this.stack.z, max: this.stack.z + 1};
    this.refresh();
  }

  var mag = Math.pow(2, -this.stack.s);

  for (var id in this.regions) {
    var region = this.regions[id];
    if (region.z <= this.stack.z && region.z + region.depth > this.stack.z) {
      region.$div
          .css('left',  mag * region.x - this.stack.xc)
          .css('top', mag * region.y - this.stack.yc)
          .css('width', mag * region.width)
          .css('height', mag * region.height)
          .show();
    } else {
      region.$div.hide();
    }
  }

  if (completionCallback) {
      completionCallback();
  }
};

CatsopResultsLayer.Overlays.Blocks.prototype.refresh = function () {
  this.clear();
  var viewBox = this.stack.createStackViewBox();
  var self = this;
  requestQueue.register(django_url + 'sopnet/' + project.id + '/segmentation/' + this.segmentationStack +
          '/' + this.regionType + '/by_bounding_box',
      'POST',
      {
          min_x: viewBox.min.x,
          min_y: viewBox.min.y,
          min_z: this.stack.z,
          max_x: viewBox.max.x,
          max_y: viewBox.max.y,
          max_z: this.stack.z
      },
      jsonResponseHandler((function (json) {
        if (json[self.regionType].length) {
          var region = json[self.regionType][0];
          self.z_lim = {min: region.box[2], max: region.box[5]};
        } else {
          self.z_lim = null;
        }

        json[self.regionType].forEach(function (region) {
          self.addRegion(region, self.regionFlags.map(function (flag) {
                return region[flag] ? flag + '_flag' : '';
              }).join(' '));
        });
      })));
};

CatsopResultsLayer.Overlays.Blocks.prototype.clear = function () {
  CatsopResultsLayer.prototype.clear.call(this);

  this.regions = {};
};

CatsopResultsLayer.Overlays.Blocks.prototype.addRegion = function (region, statuses) {
  if (region.id in this.regions) {
    this.regions[region.id].$div.removeClass().addClass('region').addClass(statuses);
    return;
  }

  var $div = $('<div class="region"><h2>' + region.id + '</h2></div>')
      .hide()
      .addClass(statuses)
      .appendTo($(this.view));

  this.regions[region.id] = {
    x: region.box[0],
    y: region.box[1],
    z: region.box[2],
    width: region.box[3] - region.box[0],
    height: region.box[4] - region.box[1],
    depth: region.box[5] - region.box[2],
    $div: $div};
  this.redraw();
};

CatsopResultsLayer.Overlays.Cores = function (stack, segmentationStack, scale) {
  CatsopResultsLayer.Overlays.Blocks.call(this, stack, segmentationStack, scale);

  this.regionType = 'cores';
  this.regionFlags = ['solutions'];
};

CatsopResultsLayer.Overlays.Cores.prototype = Object.create(CatsopResultsLayer.Overlays.Blocks.prototype);
