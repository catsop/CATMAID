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
    'Type': (function (s) {return s.type;}),
    'In Solution': (function (s) {return s.in_solution ? 'Y' : '';})
  };
  this.tableContainers = {};
  this.container = null;
  this.layers = [];
  this.activeSliceIndex = null;
  this.activeSegmentHash = null;
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

  this.tableContainers = ['slices', 'segments'].reduce(function(containers, entity) {
        $container.append('<h4>' + entity + '</h4>');
        var $collapser = $('<a href="#">Hide</a>').appendTo($container);
        var $entity = $('<div />').appendTo($container);
        $entity
            .attr('id', $container.attr('id') + '-' + entity)
            .append('<table id="' + $container.attr('id') + '-' + entity + '-table" />');
        containers[entity] = $entity;
        $collapser.click(function () {
          $entity.toggle();
          $(this).text($entity.is(':visible') ? 'Hide' : 'Show');
        });
        return containers;
      }, {});

  $container.append('<div id="segmap' + this.widgetID + '" class="segment-graph" />');

  this.container = $container.get()[0];
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
        $('#' + $(this.container).attr('id') + '-block-id').text(json.id);
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
  var $table = $('#' + this.tableContainers.slices.attr('id') + '-table');
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
  var $table = $('#' + this.tableContainers.segments.attr('id') + '-table');
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

  this.layers.forEach(function (layer) {
    layer.clearSlices();
  });

  var segmap = {nodes: [], links: []};
  var self = this;
  var activeSegment = this.segmentRows.filter(function (seg) {return seg.hash === self.activeSegmentHash;})[0];
  this.moveToObject(activeSegment);

  this.segmentRows.filter(function (seg) {
    return seg.section === activeSegment.section;
  }).forEach(function (seg) {
    seg.name = 'Seg:' + seg.hash;
    seg.breadth = 1;
    seg.size = (seg.box[2]-seg.box[0])*(seg.box[3]-seg.box[1]);
    segmap.nodes.push(seg);
  });

  this.sliceRows.forEach(function (slice) {
    slice.name = 'Sli:' + slice.hash;
    self.layers.forEach(function (layer) {
      layer.addSlice(slice, 'hidden');
    });
    segmap.nodes.push(slice);
    slice.segment_summaries.forEach(function (segsum) {
      var match = self.segmentRows.filter(function (sr) {
        return sr.hash === segsum.segment_id && sr.section === activeSegment.section;});
      if (match.length) {
        slice.breadth = segsum.direction ? 0 : 2;
        if (segsum.direction) segmap.links.push({
            source: slice, target: match[0], graphValue: Math.sqrt(slice.size)});
        else segmap.links.push({
            source: match[0], target: slice, graphValue: Math.sqrt(slice.size)});
      }
    });
  });

  var graphWidth = this.container.clientWidth,
      graphHeight = this.container.clientHeight;
  var margin = {top: 0.04, right: 0.04, bottom: 0.05, left: 0.05},
      width = 1 - margin.left - margin.right,
      height = 1 - margin.top - margin.bottom;
  margin.left  *= graphWidth;
  margin.right *= graphWidth;
  width        *= graphWidth;
  margin.top    *= graphHeight;
  margin.bottom *= graphHeight;
  height        *= graphHeight;

  d3.select('#segmap' + this.widgetID).select('svg').remove();
  var svg = d3.select("#segmap" + this.widgetID).append("svg")
      .attr("width", graphWidth)
      .attr("height", graphHeight)
    .append("g")
      .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

  var seggraph = CatsopWidget.SegmentGraph()
      .nodeWidths([width*0.275, width*0.15])
      .nodePadding(10)
      .size([width, height]);

  var path = seggraph.link();

  seggraph
      .nodes(segmap.nodes)
      .links(segmap.links)
      .layout(32);

  var link = svg.append("g").selectAll(".link")
      .data(segmap.links)
    .enter().append("path")
      .attr("class", function (d) {
        return [
          'link',
          'slice-hash-' + (typeof d.source.mask === 'undefined' ? d.target.hash : d.source.hash),
          'seg-hash-' + (typeof d.source.mask !== 'undefined' ? d.target.hash : d.source.hash)
        ].join(' ');})
      .attr("d", path)
      .style("stroke-width", function(d) { return Math.max(1, d.dy); })
      .sort(function (a, b) { return b.dy - a.dy; });

  link.append("title")
      .text(function (d) { return d.source.name + " → " + d.target.name; });

  function dragmove(d) {
    d3.select(this).attr("transform", "translate(" + d.x + "," + (d.y = Math.max(0, Math.min(height - d.dy, d3.event.y))) + ")");
    seggraph.relayout();
    link.attr("d", path);
  }

  var node = svg.append("g").selectAll(".node")
      .data(segmap.nodes)
    .enter().append("g")
      .attr("class", "node")
      .attr("transform", function(d) { return "translate(" + d.x + "," + d.y + ")"; })
    .call(d3.behavior.drag()
      .origin(function (d) { return d; })
      .on("dragstart", function() { this.parentNode.appendChild(this); })
      .on("drag", dragmove));

  // Segment nodes
  node.filter(function (d) { return typeof d.mask === 'undefined'; })
      .classed('segment-node', true)
      .on('mouseover', function (d) {
          d.sourceLinks.map(function (l) {return l.target;})
            .concat(d.targetLinks.map(function (l) {return l.source;}))
            .forEach(function (d) {
              $('.slice-hash-' + d.hash).addClass('highlight');
              d3.selectAll($('rect[class~="slice-hash-' + d.hash + '"]')).classed('highlight', true);
            });
          // Class selectors do not work for SVG elements, so use a jQuery
          // attribute string containing selector, then pass to D3 because
          // jQuery addClass does not work with SVG elements.
          d3.selectAll($('[class~="seg-hash-' + d.hash + '"]')).classed('highlight', true);
        })
      .on('mouseout', function (d) {
          d.sourceLinks.map(function (l) {return l.target;})
            .concat(d.targetLinks.map(function (l) {return l.source;}))
            .forEach(function (d) {
              $('.slice-hash-' + d.hash).removeClass('highlight');
              d3.selectAll($('rect[class~="slice-hash-' + d.hash + '"]')).classed('highlight', false);
            });
          d3.selectAll($('[class~="seg-hash-' + d.hash + '"]')).classed('highlight', false);
        })
    .append("rect")
      .attr("height", function (d) { return d.dy; })
      .attr("width", seggraph.nodeWidths()[1])
      .style("fill", function (d) { return d.color = d.in_solution ? '#0F0' : '#CCC'; })
      .style("stroke", function (d) { return d3.rgb(d.color).darker(2); })
    .append("title")
      .text(function (d) { return d.name + "\n" + d.size + " pixels"; });

  // Slice nodes
  node.filter(function (d) { return typeof d.mask !== 'undefined'; })
      .classed('slice-node', true)
      .on('mouseover', function (d) {
          d3.selectAll($('[class~="slice-hash-' + d.hash + '"]')).classed('highlight', true);
        })
      .on('mouseout', function (d) {
          d3.selectAll($('[class~="slice-hash-' + d.hash + '"]')).classed('highlight', false);
        })
    .append("rect")
      .attr("height", function (d) { return d.dy; })
      .attr("width", seggraph.nodeWidths()[0])
      .attr("class", function (d) { return 'slice-hash-' + d.hash; });
  node.filter(function(d) { return typeof d.mask !== 'undefined'; })
    .append("image")
      .attr("height", function (d) { return d.dy; })
      .attr("width", seggraph.nodeWidths()[0])
      .attr("xlink:href", function (d) { return d.mask; })
    .append("title")
      .text(function (d) { return d.name + "\n" + d.size + " pixels"; });

  var segmentTypes = ['End', 'Continuation', 'Branch'];
  // Segment nodes
  node.filter(function (d) { return typeof d.mask === 'undefined'; })
    .append("text")
      .attr("x", function (d) { return d.dx / 2; })
      .attr("y", function (d) { return d.dy / 2; })
      .attr("dy", ".35em")
      .attr("text-anchor", "middle")
      .attr("transform", null)
      .text(function(d) { return segmentTypes[d.type]; });
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
  this.activeSegmentHash = hash;
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
  this.moveToObject(slice);
};

/**
 * Moves the stack view to any object with section and ctr properties.
 */
CatsopWidget.prototype.moveToObject = function (obj) {
  var stack = this.getStack();
  var z = obj.section,
      y = obj.ctr[1],
      x = obj.ctr[0];
  // Sopnet works in pixels. Convert to project coordinates to account for resolution & transform.
  z = stack.stackToProjectZ(z, y, x);
  y = stack.stackToProjectY(z, y, x);
  x = stack.stackToProjectX(z, y, x);
  project.moveTo(z, y, x);
};
