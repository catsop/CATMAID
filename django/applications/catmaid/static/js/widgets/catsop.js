"use strict";

var CatsopWidget = function () {
  this.widgetID = this.registerInstance();
  this.block = {};
  this.sliceRows = [];
  this.sliceColumns = {
    'Hash': (function (s) {return s.hash;}),
    'Section': (function (s) {return s.section;}),
    'Value': (function (s) {return s.value;}),
    'Conflicts': (function (s) {
      return s.conflicts.split(',').reduce(function ($csList, csHash) {
        $('<li>' + csHash + '</li>')
            .hover(
              function () {
                $('.slice-hash-' + csHash).addClass('highlight');
              },
              function () {
                $('.slice-hash-' + csHash).removeClass('highlight');
              })
            .appendTo($csList);
        return $csList;
      }, $('<ul />'));
    }),
    'In Solution': (function (s) {return s.in_solution ? 'Y' : '';}),
    'Segments': ((function (s) {
      return s.segment_summaries.reduce((function ($segList, ss) {
        $('<li>' + ss.segment_id + ' (' + (ss.direction ? 'L' : 'R') + ')</li>')
          .click((function () {this.activateSegment(ss.segment_id);}).bind(this))
          .appendTo($segList);
        return $segList;
      }).bind(this), $('<ul>'));
    }).bind(this))
  };
  this.segmentRows = [];
  this.segmentColumns = {
    'Hash': (function (s) {return s.hash;}),
    'Section': (function (s) {return s.section;}),
    'Type': (function (s) {return s.type;})
  };
  this.containers = {};
  this.$container = {};
  this.layers = [];
  this.activeSliceIndex = null;
};

CatsopWidget.prototype = {};
$.extend(CatsopWidget.prototype, new InstanceRegistry());

CatsopWidget.prototype.init = function (container) {
  // Create and  new layers
  project.getStacks().forEach((function(s) {
    var layer = new CatsopResultsLayer(s);
    this.layers.push(layer);
    s.addLayer("catsop-layer" + this.widgetID, layer);
    s.redraw();
  }).bind(this));

  var $container = $(container);
  $container.append('<h3>Segmentation for block: <span id="' + $container.attr('id') +
      '-block-id" /></h3>');
  $container.append(
      $('<input type="button" value="Refresh Location" />').click((function () {
        this.refreshLocation();
      }).bind(this)));

  this.containers = ['slices', 'segments'].reduce(function(containers, entity) {
        var $entity = $('<div />').appendTo($container);
        $entity
            .attr('id', $container.attr('id') + '-' + entity)
            .append('<h4>' + entity + '</h4>')
            .append('<table id="' + $container.attr('id') + '-' + entity + '-table" />');
        containers[entity] = $entity;
        return containers;
      }, {});

  this.$container = $container;
  this.refreshLocation();
};

CatsopWidget.prototype.destroy = function () {
  project.getStacks().forEach((function(s) {
    s.removeLayer("catsop-layer" + this.widgetID);
  }).bind(this));
};

CatsopWidget.prototype.getStack = function () {
  return project.getStacks()[0]; // TODO: not a robust way to determine raw stack
};

CatsopWidget.prototype.refreshLocation = function () {
  var stack = this.getStack();

  requestQueue.register(django_url + 'sopnet/' + project.id + '/stack/' + stack.getId() +
          '/block_at_location',
      'GET',
      {x: stack.x, y: stack.y, z: stack.z},
      jsonResponseHandler((function (json) {
        this.block = json;
        $('#' + this.$container.attr('id') + '-block-id').text(json.id);
        this.refreshSlices();
      }).bind(this)));
};

CatsopWidget.prototype.refreshSlices = function () {
  var stackId = this.getStack().getId();
  requestQueue.register(django_url + 'sopnet/' + project.id + '/stack/' + stackId +
          '/slices_by_blocks_and_conflict',
      'POST',
      {block_ids: this.block.id},
      jsonResponseHandler((function (json) {
        this.sliceRows = json.slices;
        this.updateSlices();
      }).bind(this)));
};

CatsopWidget.prototype.updateSlices = function () {
  var $table = $('#' + this.containers.slices.attr('id') + '-table');
  $table.empty();

  var $thead = $('<tr />').appendTo($('<thead />').appendTo($table));
  var $tbody = $('<tbody />');

  for (var colKey in this.sliceColumns) {
    $thead.append('<th>' + colKey + '</th>');
  }

  this.sliceRows.forEach(function (slice) {
    var $tr = $('<tr />').appendTo($tbody);
    for (var colKey in this.sliceColumns) {
      $('<td />').append(this.sliceColumns[colKey](slice)).appendTo($tr);
    }
  }, this);

  $tbody.appendTo($table);
  $table.dataTable({bDestroy: true});

  var self = this;
  $table.children('tbody').on('dblclick', 'tr', function () {
    var index = $table.dataTable().fnGetPosition(this);
    self.activateSlice(index);
  });
};

CatsopWidget.prototype.updateSegments = function () {
  var $table = $('#' + this.containers.segments.attr('id') + '-table');
  $table.empty();

  var $thead = $('<tr />').appendTo($('<thead />').appendTo($table));
  var $tbody = $('<tbody />');

  for (var colKey in this.segmentColumns) {
    $thead.append('<th>' + colKey + '</th>');
  }

  this.segmentRows.forEach(function (slice) {
    var $tr = $('<tr />').appendTo($tbody);
    for (var colKey in this.segmentColumns) {
      $('<td />').append(this.segmentColumns[colKey](slice)).appendTo($tr);
    }
  }, this);

  $tbody.appendTo($table);
  $table.dataTable({bDestroy: true});
};

CatsopWidget.prototype.activateSlice = function (rowIndex) {
  this.layers.forEach(function (layer) {
    layer.clearSlices();
  });
  this.activeSliceIndex = rowIndex;
  this.moveToSlice(rowIndex);
  var slice = this.sliceRows[rowIndex];
  this.layers.forEach(function (layer) {
    layer.addSlice(slice, 'active');
  });

  requestQueue.register(django_url + 'sopnet/' + project.id + '/stack/' + this.getStack().getId() +
          '/conflict_sets_by_slice',
      'POST',
      {hash: slice.hash},
      jsonResponseHandler((function (json) {
        var self = this;
        json.conflict.forEach(function (conflictSet) {
          conflictSet.conflict_hashes
              .map(self.getSliceRowByHash.bind(self))
              .filter(function (s) {return s !== undefined;})
              .forEach(function (conflictSlice) {
                  if (conflictSlice.hash !== slice.hash) {
                    self.layers.forEach(function (layer) {
                      layer.addSlice(conflictSlice, 'conflict');
                    });
                  }
          });
        });
      }).bind(this)));
};

CatsopWidget.prototype.activateSegment = function (hash) {
  var stackId = this.getStack().getId();
  requestQueue.register(django_url + 'sopnet/' + project.id + '/stack/' + stackId +
          '/segment_and_conflicts',
      'POST',
      {hash: hash},
      jsonResponseHandler((function (json) {
        this.sliceRows = json.slices;
        this.segmentRows = json.segments;
        this.updateSlices();
        this.updateSegments();
      }).bind(this)));
};

CatsopWidget.prototype.getSliceRowByHash = function (hash) {
  return this.sliceRows.filter(function (slice) { return slice.hash === hash; })[0];
};

CatsopWidget.prototype.moveToSlice = function (rowIndex) {
  var slice = this.sliceRows[rowIndex];
  var stack = this.getStack();
  var z = slice.section,
      y = slice.ctr[1],
      x = slice.ctr[0];
  // Sopnet works in pixels. Convert to project coordinates to account for resolution & transform.
  z = stack.stackToProjectZ(z, y, x);
  y = stack.stackToProjectY(z, y, x);
  x = stack.stackToProjectX(z, y, x);
  project.moveTo(z, y, x);
};
