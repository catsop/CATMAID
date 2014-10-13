"use strict";

var CatsopWidget = function () {
  this.widgetID = this.registerInstance();
  this.block = {};
  this.sliceRows = [];
  this.sliceColumns = {
    'hash': 'Hash',
    'section': 'Section',
    'value': 'Value'
  };
  this.segmentRows = [];
  this.containers = {};
  this.$container = {};
};

CatsopWidget.prototype = {};
$.extend(CatsopWidget.prototype, new InstanceRegistry());

CatsopWidget.prototype.init = function (container) {
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
        this.refreshUI();
      }).bind(this)));
};

CatsopWidget.prototype.refreshUI = function () {
  var $table = $('#' + this.containers.slices.attr('id') + '-table');
  $table.empty();

  var $thead = $('<tr />').appendTo($('<thead />').appendTo($table));
  var $tbody = $('<tbody />').appendTo($table);

  for (var colKey in this.sliceColumns) {
    $thead.append('<th>' + this.sliceColumns[colKey] + '</th>');
  }

  this.sliceRows.forEach(function (slice) {
    var $tr = $('<tr />').appendTo($tbody);
    for (var colKey in this.sliceColumns) {
      $tr.append('<td>' + slice[colKey] + '</td>');
    }
  }, this);

  $table.dataTable({bDestroy: true});
};
