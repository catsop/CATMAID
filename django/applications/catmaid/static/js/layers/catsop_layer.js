/* -*- mode: espresso; espresso-indent-level: 2; indent-tabs-mode: nil -*- */

(function(CATMAID) {

  "use strict";

  function CatsopResultsLayer (stack, segmentationStackId, scale, solutionId) {
    this.stack = stack;
    this.segmentationStackId = segmentationStackId;
    this.solutionId = solutionId;
    this.scale = scale; // CATSOP scale relative to stack (from BlockInfo)
    this.opacity = 0.5;
    this.radius = 3;

    if (!CATMAID.PixiLayer.contexts.get(this.stack)) {
      growlAlert('ERROR', 'CATSOP requires WebGL rendering. Enable WebGL from the settings widget and reload.');
      return;
    }
    CATMAID.PixiLayer.call(this);
    CATMAID.PixiLayer.prototype._initBatchContainer.call(this);
  }

  CatsopResultsLayer.prototype = Object.create(CATMAID.PixiLayer.prototype);
  CatsopResultsLayer.prototype.constructor = CatsopResultsLayer;

  CatsopResultsLayer.prototype.getLayerName = function () {
    return "CATSOP results";
  };

  CatsopResultsLayer.prototype.getOpacity = function () {
    return this.opacity;
  };

  CatsopResultsLayer.prototype.resize = function () {
    this.redraw();
  };

  CatsopResultsLayer.prototype.redraw = function (completionCallback) {
    if (!this.batchContainer) return; // Layer construction failed, likely due to no WebGL.
    var mag = Math.pow(2, this.scale - this.stack.s);
    this.batchContainer.position.x = -this.stack.xc;
    this.batchContainer.position.y = -this.stack.yc;
    this.batchContainer.scale.x = mag;
    this.batchContainer.scale.y = mag;

    this.renderer.render(this.stage);

    if (typeof completionCallback === 'function') {
        completionCallback();
    }
  };

  CatsopResultsLayer.prototype.refresh = function () {
    this.redraw();
  };

  CatsopResultsLayer.prototype.unregister = function () {
    this.stage.removeChild(this.batchContainer);
    this.renderer.render(this.stage);
  };

  CatsopResultsLayer.prototype.setSolutionId = function (solutionId) {
    this.solutionId = solutionId;
  };

  CatsopResultsLayer.prototype.clear = function () {
    this.batchContainer.removeChildren();
  };


  CatsopResultsLayer.Slices = function (stack, segmentationStackId, scale, solutionId) {
    CatsopResultsLayer.call(this, stack, segmentationStackId, scale, solutionId);

    this.slices = {};
    this.statusStyles = {
      hidden:        {visible: false, color: 0xFFFFFF}, // This must be #FFF to remove Pixi's tint image processing.
      active:        {visible: true,  color: 0xFFFF00},
      conflict:      {visible: true,  color: 0xFF0000},
      'in-solution': {visible: true,  color: 0x00FF00},
      highlight:     {visible: true,  color: 0x0000FF}
    };
  };

  CatsopResultsLayer.Slices.prototype = Object.create(CatsopResultsLayer.prototype);
  CatsopResultsLayer.Slices.prototype.constructor = CatsopResultsLayer.Slices;

  CatsopResultsLayer.Slices.prototype.redraw = function (completionCallback) {
    var self = this;

    for (var hash in this.slices) {
      var slice = this.slices[hash];

      var style = slice.statuses.reduce(function (style, status) {
        style.visible = style.visible || self.statusStyles[status].visible;
        style.color = self.statusStyles[status].color;
        return style;
      }, {visible: false, color: null});

      slice.sprite.visible = style.visible && slice.z === this.stack.z;
      if (style.color !== null) slice.sprite.tint = style.color;
    }

    CatsopResultsLayer.prototype.redraw.call(this, completionCallback);
  };

  CatsopResultsLayer.Slices.prototype.clear = function () {
    CatsopResultsLayer.prototype.clear.call(this);
    this.slices = {};
  };

  CatsopResultsLayer.Slices.prototype.addSlice = function (slice, statuses) {
    if (slice.hash in this.slices) {
      var slice = this.slices[slice.hash];
      slice.statuses = statuses || [];
      return slice;
    }

    var sprite = new PIXI.Sprite.fromImage(slice.mask);
    sprite.texture.once('update', this.redraw.bind(this));
    sprite.x = slice.box[0];
    sprite.y = slice.box[1];
    sprite.width = slice.box[2] - slice.box[0];
    sprite.height = slice.box[3] - slice.box[1];
    sprite.blendMode = PIXI.blendModes.ADD;
    if (this.batchContainer) this.batchContainer.addChild(sprite);

    this.slices[slice.hash] = {
      z: slice.section,
      sprite: sprite,
      statuses: statuses || []
    };
    this.redraw();

    return sprite;
  };

  CatsopResultsLayer.Slices.prototype.addStatus = function (sliceHash, status) {
    var slice = this.slices[sliceHash];
    if (typeof slice === 'undefined') return;

    slice.statuses.push(status);
    this.redraw();
  };

  CatsopResultsLayer.Slices.prototype.removeStatus = function (sliceHash, status) {
    var slice = this.slices[sliceHash];
    if (typeof slice === 'undefined') return;

    slice.statuses = slice.statuses.filter(function (oldStatus) { return oldStatus !== status; });
    this.redraw();
  };

  // Namespace for overlays extending CatsopResultsLayer
  CatsopResultsLayer.Overlays = {};


  CatsopResultsLayer.Overlays.Assemblies = function (stack, segmentationStackId, scale, solutionId) {
    CatsopResultsLayer.Slices.call(this, stack, segmentationStackId, scale, solutionId);
    this.statusStyles = {
      'in-solution': {visible: true,  color: null}
    };

    this.old_z = null;
  };

  CatsopResultsLayer.Overlays.Assemblies.prototype = Object.create(CatsopResultsLayer.Slices.prototype);

  CatsopResultsLayer.Overlays.Assemblies.prototype.getLayerName = function () {
    return "CATSOP assemblies";
  };

  CatsopResultsLayer.Overlays.Assemblies.prototype.redraw = function (completionCallback) {
    if (this.stack.z != this.old_z) {
      this.old_z = this.stack.z;
      this.refresh();
    }

    CatsopResultsLayer.Slices.prototype.redraw.call(this, completionCallback);
  };

  CatsopResultsLayer.Overlays.Assemblies.prototype.refresh = function () {
    var viewBox = this.stack.createStackViewBox();
    var self = this;
    requestQueue.register(django_url + 'sopnet/' + project.id + '/segmentation/' + this.segmentationStackId +
            '/slices/by_bounding_box',
        'POST',
        {
            min_x: viewBox.min.x,
            min_y: viewBox.min.y,
            max_x: viewBox.max.x,
            max_y: viewBox.max.y,
            z: this.stack.z
        },
        CATMAID.jsonResponseHandler((function (json) {
          var czer = new Colorizer();
          json.slices.forEach(function (slice) {
            if (!(slice.in_solution && slice.in_solution.hasOwnProperty(self.solutionId))) return;

            var sprite = self.addSlice(slice, ['in-solution']);
            var assemblyId = slice.in_solution[self.solutionId];
            if (!(assemblyId in CatsopResultsLayer.assemblyColors)) {
              CatsopResultsLayer.assemblyColors[assemblyId] = czer.pickColor().getHex();
            }

            sprite.tint = CatsopResultsLayer.assemblyColors[assemblyId];
          });
        })));
  };

  CatsopResultsLayer.Overlays.Assemblies.prototype.setSolutionId = function (solutionId) {
    this.solutionId = solutionId;
    this.clear();
  };

  CatsopResultsLayer.assemblyColors = {};


  CatsopResultsLayer.Overlays.Blocks = function (stack, segmentationStackId, scale, solutionId) {
    CatsopResultsLayer.call(this, stack, segmentationStackId, scale, solutionId);

    this.z_lim = null;
    this.regions = {};
    this.regionType = 'blocks';
    this.flagStyles = {
      slices:   {visible: true, color: 0xFFFF00},
      segments: {visible: true, color: 0x00FF00}
    };
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

    var self = this;
    for (var id in this.regions) {
      var region = this.regions[id];

      var style = region.flags.reduce(function (style, flag) {
        style.visible = style.visible || self.flagStyles[flag].visible;
        style.color = self.flagStyles[flag].color;
        return style;
      }, {visible: false, color: 0x000000});

      region.graphics.visible = region.text.visible =
          style.visible && region.z <= this.stack.z && region.z + region.depth > this.stack.z;
      region.graphics.tint = style.color;
      var colorStr = style.color.toString(16);
      while (colorStr.length < 6) { colorStr = '0' + colorStr; }
      colorStr = '#' + colorStr;
      if (region.text.style.fill !== colorStr) {
        region.text.setStyle({fill: colorStr});
      }
    }

    CatsopResultsLayer.prototype.redraw.call(this, completionCallback);
  };

  CatsopResultsLayer.Overlays.Blocks.prototype.refresh = function () {
    this.clear();
    var viewBox = this.stack.createStackViewBox();
    var self = this;
    requestQueue.register(django_url + 'sopnet/' + project.id + '/segmentation/' + this.segmentationStackId +
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
        CATMAID.jsonResponseHandler((function (json) {
          if (json[self.regionType].length) {
            var region = json[self.regionType][0];
            self.z_lim = {min: region.box[2], max: region.box[5]};
          } else {
            self.z_lim = null;
          }

          json[self.regionType].forEach(function (region) {
            self.addRegion(region, Object.keys(self.flagStyles).filter(function (flag) {
                  return region[flag];
                }));
          });
        })));
  };

  CatsopResultsLayer.Overlays.Blocks.prototype.clear = function () {
    CatsopResultsLayer.prototype.clear.call(this);

    this.regions = {};
  };

  CatsopResultsLayer.Overlays.Blocks.prototype.addRegion = function (region, flags) {
    if (region.id in this.regions) {
      this.regions[region.id].flags = flags;
      return;
    }

    var graphics = new PIXI.Graphics();
    var LINE_WIDTH = 3;
    graphics.beginFill(0x000000, 0);
    graphics.lineStyle(LINE_WIDTH, 0xFFFFFF);
    graphics.drawRect(
        region.box[0] + LINE_WIDTH,
        region.box[1] + LINE_WIDTH,
        region.box[3] - region.box[0] - LINE_WIDTH,
        region.box[4] - region.box[1] - LINE_WIDTH);
    this.batchContainer.addChild(graphics);

    var text = new PIXI.Text(region.id);
    var OFFSET = 0.1;
    text.x = (1 - OFFSET)*region.box[0] + OFFSET*region.box[3];
    text.y = (1 - OFFSET)*region.box[1] + OFFSET*region.box[4];
    this.batchContainer.addChild(text);

    this.regions[region.id] = {
      z: region.box[2],
      depth: region.box[5] - region.box[2],
      graphics: graphics,
      text: text,
      flags: flags
    };
    this.redraw();
  };


  CatsopResultsLayer.Overlays.Cores = function (stack, segmentationStackId, scale, solutionId) {
    CatsopResultsLayer.Overlays.Blocks.call(this, stack, segmentationStackId, scale, solutionId);

    this.regionType = 'cores';
    this.flagStyles = {
      solutions: {visible: true, color: 0x00FF00}
    };
  };

  CatsopResultsLayer.Overlays.Cores.prototype = Object.create(CatsopResultsLayer.Overlays.Blocks.prototype);

  CATMAID.CatsopResultsLayer = CatsopResultsLayer;

})(CATMAID);
