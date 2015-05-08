/* global
  CATMAID,
  CatsopResultsLayer,
  growlAlert,
  InstanceRegistry,
  OffsetStack,
  openProjectStack,
  project,
  requestQueue
 */

"use strict";

var CatsopWidget = function () {
  this.widgetID = this.registerInstance();
  this.block = {};
  this.blockInfo = {};
  this.configurations = [];
  this.activeConfiguration = null;
  this.activeSegmentationStack = null;
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
    'In Solution': (function (s) {return s.in_solution;}),
    'Segments': ((function (s) {
      return s.segment_summaries.reduce((function ($segList, ss) {
        $('<li>' + ss.segment_hash + ' (' + (ss.direction ? 'L' : 'R') + ')</li>')
          .click((function () {this.activateSegment(ss.segment_hash);}).bind(this))
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
  this.layers = {};
  this.activeSliceIndex = null;
  this.activeSegmentHash = null;
  this.activeSolutionId = null;
  this.stack = null;
  this.offsetStack = null;
};

CatsopWidget.prototype = {};
$.extend(CatsopWidget.prototype, new InstanceRegistry());

CatsopWidget.prototype.init = function (container) {
  this.container = container;
  this.stack = project.focusedStack;

  requestQueue.register(django_url + 'sopnet/' + project.id + '/stack/' + this.stack.getId() +
          '/configurations',
      'GET',
      {},
      CATMAID.jsonResponseHandler((function (json) {
        this.configurations = json;
        this.activeConfiguration = this.configurations[0].id;
        this.activeSegmentationStack = this.configurations[0].stacks.filter(function (config) {
          return config.type === 'Membrane';
        })[0].id;

        requestQueue.register(
            django_url + 'sopnet/' + project.id + '/configuration/' + this.activeConfiguration + '/block',
            'GET',
            {},
            CATMAID.jsonResponseHandler((function (json) {
              this.blockInfo = json;
              openProjectStack(project.id, this.stack.getId(), this.initLayers.bind(this), OffsetStack(0, 0, 1)); // Duplicate stack

              this.loadSegmentsAtLocation();
            }).bind(this)));
      }).bind(this)));

  // First load configuration info, block info, then open offset stack, create CATSOP layers and
  // load a segment graph for segments at this stack location.
};

CatsopWidget.prototype.initLayers = function (offsetStack) {
  this.offsetStack = offsetStack;

  project.setFocusedStack(this.stack);

  var name = 'base';
  this.layers[name] = [];
  [this.stack, this.offsetStack].forEach((function(s) {
    var layer = new CatsopResultsLayer(s, this.activeSegmentationStack, this.blockInfo.scale);
    this.layers[name].push(layer);
    s.addLayer(this.getLayerKey(name), layer);
    s.redraw();
  }).bind(this));
};

CatsopWidget.prototype.destroy = function () {
  [this.stack, this.offsetStack].forEach((function(s) {
    for (var name in this.layers)
      s.removeLayer(this.getLayerKey(name));
  }).bind(this));
};

CatsopWidget.prototype.refresh = function () {
  for (var name in this.layers) {
    this.layers[name].forEach(function (layer) { layer.refresh(); });
  }

  this.refreshSegments();
};

CatsopWidget.prototype.getLayerKey = function (name) {
  return 'catsop-layer' + this.widgetID + '-' + name;
};

CatsopWidget.prototype.loadBlockAtLocation = function () {
  requestQueue.register(django_url + 'sopnet/' + project.id + '/segmentation/' + this.activeSegmentationStack +
          '/block_at_location',
      'GET',
      {x: this.stack.x, y: this.stack.y, z: this.stack.z},
      CATMAID.jsonResponseHandler((function (json) {
        this.block = json;
        $('#' + $(this.container).attr('id') + '-block-id').text(json.id);
        this.refreshSlices();
      }).bind(this)));
};

CatsopWidget.prototype.refreshSlices = function () {
  requestQueue.register(django_url + 'sopnet/' + project.id + '/segmentation/' + this.activeSegmentationStack +
          '/slices_by_blocks_and_conflict',
      'POST',
      {block_ids: this.block.id},
      CATMAID.jsonResponseHandler((function (json) {
        this.sliceRows = json.slices;
        this.updateSlices();
      }).bind(this)));
};

CatsopWidget.prototype.updateSlices = function () {
  this.updateSolutions();

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

CatsopWidget.prototype.refreshSegments = function () {
  this.activateSegment(this.activeSegmentHash);
};

CatsopWidget.prototype.loadSegmentsAtLocation = function () {
  requestQueue.register(django_url + 'sopnet/' + project.id + '/segmentation/' + this.activeSegmentationStack +
          '/slices/by_location',
      'POST',
      {x: this.stack.x, y: this.stack.y, z: this.stack.z},
      CATMAID.jsonResponseHandler((function (json) {
        var segments = json.slices.reduce(function (segments, s) {
          return segments.concat(s.segment_summaries
              .filter(function (ss) { return ss.direction; })
              .map(function (ss) { return ss.segment_hash; }));
        }, []);
        if (segments.length) {
          this.activateSegment(segments);
        } else if (json.slices.length) {
          growlAlert('Information', 'No segments at location');
          this.sliceRows = json.slices;
          this.segmentRows = [];
          this.updateSlices();
          this.updateSegments();
        } else {
          growlAlert('Information', 'No slices at location');
        }
      }).bind(this)));
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

  this.layers.base.forEach(function (layer) {
    layer.clear();
  });

  var segmap = {nodes: [], links: []};
  var self = this;
  var activeSegment = this.segmentRows.filter(function (seg) {return seg.hash === self.activeSegmentHash;})[0];
  this.activeSegment = activeSegment;
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
    self.layers.base.forEach(function (layer) {
      layer.addSlice(slice, 'hidden');
    });
    segmap.nodes.push(slice);
    slice.breadth = 0;
    slice.segment_summaries.forEach(function (segsum) {
      var match = self.segmentRows.filter(function (sr) {
        return sr.hash === segsum.segment_hash && sr.section === activeSegment.section;});
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
      graphHeight = this.container.clientHeight -
          $('#catsop_widget_buttons' + this.widgetID)[0].clientHeight - 5;
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
    /* jshint validthis: true */
    d3.select(this).attr("transform", "translate(" + d.x + "," + (d.y = Math.max(0, Math.min(height - d.dy, d3.event.y))) + ")");
    seggraph.relayout();
    link.attr("d", path);
  }

  var node = svg.append("g").selectAll(".node")
      .data(segmap.nodes)
    .enter().append("g")
      .attr("class", "node")
      .attr("transform", function(d) { return "translate(" + d.x + "," + d.y + ")"; });

  var segmentNodes = node.filter(function (d) { return typeof d.mask === 'undefined'; });
  var sliceNodes = node.filter(function (d) { return typeof d.mask !== 'undefined'; });

  // Segment nodes
  segmentNodes
      .attr("class", function (d) {
        return d.linkPartners().map(function (d) {
            return ('slice-hash-' + d.hash);
          }).concat([
          'node',
          'segment-node',
          'seg-hash-' + d.hash
        ]).join(' ');})
      .on('mouseover', function (d) {
          d.linkPartners().forEach(function (d) {
              $('.slice-hash-' + d.hash).addClass('highlight');
              d3.selectAll($('rect[class~="slice-hash-' + d.hash + '"]')).classed('highlight', true);
            });
          // Class selectors do not work for SVG elements, so use a jQuery
          // attribute string containing selector, then pass to D3 because
          // jQuery addClass does not work with SVG elements.
          d3.selectAll($('[class~="seg-hash-' + d.hash + '"]')).classed('highlight', true);
        })
      .on('mouseout', function (d) {
          d.linkPartners().forEach(function (d) {
              $('.slice-hash-' + d.hash).removeClass('highlight');
              d3.selectAll($('rect[class~="slice-hash-' + d.hash + '"]')).classed('highlight', false);
            });
          d3.selectAll($('[class~="seg-hash-' + d.hash + '"]')).classed('highlight', false);
        })
      .on('dblclick', function (d) { self.constrainSegment(d.hash); })
    .append("rect")
      .attr("height", function (d) { return d.dy; })
      .attr("width", seggraph.nodeWidths()[1])
    .append("title")
      .text(function (d) { return d.name + "\n" + d.size + " pixels"; });

  // Slice nodes
  sliceNodes
      .classed('slice-node', true)
      .on('mouseover', function (d) {
          d3.selectAll($('[class~="slice-hash-' + d.hash + '"]')).classed('highlight', true);
        })
      .on('mouseout', function (d) {
          d3.selectAll($('[class~="slice-hash-' + d.hash + '"]')).classed('highlight', false);
        })
      .on('click', function (d) {
          var $this = d3.select(this);
          if ($this.classed('active')) {
            $this.classed('active', false);
          } else {
            var thisSlice = d;
            $this.classed('active', true);
            sliceNodes
                .filter(function (d) { return thisSlice.conflicts.split(',').indexOf(d.hash) >= 0; })
                .classed('active', false);
          }
          // Set active segments based on intersection of active slices.
          segmentNodes.classed('active', false);
          d3.selectAll($(sliceNodes
            .filter(function () { return d3.select(this).classed('active'); })
            .data()
            .reduce(function (selector, d) {
              return selector + '[class~="slice-hash-' + d.hash + '"]';
            }, ''))).classed('active', true);
        })
    .append("rect")
      .attr("height", function (d) { return d.dy; })
      .attr("width", seggraph.nodeWidths()[0])
      .attr("class", function (d) { return 'slice-hash-' + d.hash; });
  sliceNodes
    .append("image")
      .attr("y", 3) // Offset and shrink slice mask slightly to not overlap stroke.
      .attr("height", function (d) { return d.dy - 6; })
      .attr("width", function (d) {
        return Math.min(seggraph.sliceScale * (d.box[2] - d.box[0]), seggraph.nodeWidths()[0] - 6); })
      .attr("x", function (d) {
        return Math.max(0,
              ((seggraph.nodeWidths()[0] - 6) - this.attributes.width.value) / 2)
            + 3; })
      .attr("xlink:href", function (d) { return d.mask; })
    .append("title")
      .text(function (d) { return d.name + "\n" + d.size + " pixels"; });
  sliceNodes
    .append('polygon')
      .attr('transform', function (d) {
        return 'translate(' + (d.breadth > 0 ? d.dx + 10 : -10) + ',' + d.dy / 2 + ')'
            + (d.breadth > 0 ? ' rotate(180)' : ''); })
      .attr('points', '0,0 10,-15 10,15')
      .attr('fill', '#FFF')
      .attr('stroke', '#000')
      .on('click', function (d) {
        self.activateSegment(
            d.segment_summaries
                .filter(function (ss) { return d.breadth === 0 ? !ss.direction : ss.direction; })
                .map(function (ss) { return ss.segment_hash; }));
      });

  var segmentTypes = ['End', 'Continuation', 'Branch'];
  // Segment nodes
  segmentNodes
    .append("text")
      .attr("x", function (d) { return d.dx / 2; })
      .attr("y", function (d) { return d.dy / 2; })
      .attr("dy", ".35em")
      .attr("text-anchor", "middle")
      .attr("transform", null)
      .text(function(d) { return segmentTypes[d.type]; });

  node.classed('in_solution', function (d) {
    return self.activeSolutionId === null ?
        d.in_solution :
        (d.in_solution && d.in_solution.hasOwnProperty(self.activeSolutionId));
  });

  this.seggraph = seggraph;
  this.node = node;
};

CatsopWidget.prototype.activateSlice = function (rowIndex) {
  this.layers.base.forEach(function (layer) {
    layer.clear();
  });
  this.activeSliceIndex = rowIndex;
  this.moveToSlice(rowIndex);
  var slice = this.sliceRows[rowIndex];
  this.layers.base.forEach(function (layer) {
    layer.addSlice(slice, 'active');
  });

  requestQueue.register(django_url + 'sopnet/' + project.id + '/segmentation/' + this.activeSegmentationStack +
          '/conflict_sets_by_slice',
      'POST',
      {hash: slice.hash},
      CATMAID.jsonResponseHandler((function (json) {
        var self = this;
        json.conflict.forEach(function (conflictSet) {
          conflictSet
              .map(self.getSliceRowByHash.bind(self))
              .filter(function (s) {return s !== undefined;})
              .forEach(function (conflictSlice) {
                  if (conflictSlice.hash !== slice.hash) {
                    self.layers.base.forEach(function (layer) {
                      layer.addSlice(conflictSlice, 'conflict');
                    });
                  }
          });
        });
      }).bind(this)));
};

CatsopWidget.prototype.toggleOverlay = function (name) {
  this.layers[name] = this.layers[name] || [];

  if (this.layers[name].length) {
    [this.stack, this.offsetStack].forEach((function(s) {
      s.removeLayer(this.getLayerKey(name));
    }).bind(this));

    this.layers[name] = [];
  } else {
    [this.stack, this.offsetStack].forEach((function(s) {
      var layer = new CatsopResultsLayer.Overlays[name](s, this.activeSegmentationStack, this.blockInfo.scale, this.activeSolutionId);
      this.layers[name].push(layer);
      s.addLayer(this.getLayerKey(name), layer);
      s.redraw();
    }).bind(this));
  }
};

/**
 * Retrieve a segment from the backend and display it in a segment graph.
 *
 * hashes may be a segment hash or an array of hashes for conflicting segments
 * in the same section.
 */
CatsopWidget.prototype.activateSegment = function (hashes) {
  // Check for undefined or null.
  if (hashes == null) return; // jshint ignore:line

  this.activeSegmentHash = Array.isArray(hashes) ? hashes[0] : hashes;
  requestQueue.register(django_url + 'sopnet/' + project.id + '/segmentation/' + this.activeSegmentationStack +
          '/segment_and_conflicts',
      'POST',
      {hash: Array.isArray(hashes) ? hashes.join(',') : hashes},
      CATMAID.jsonResponseHandler((function (json) {
        this.sliceRows = json.slices;
        this.segmentRows = json.segments;
        this.updateSlices();
        this.updateSegments();
      }).bind(this)));
};

CatsopWidget.prototype.createSegmentForSlices = function () {
  var hashes = this.node
      .filter(function (d) { return typeof d.mask !== 'undefined' && this.classList.contains('active'); })
      .data()
      .map(function (d) { return d.hash; })
      .join(',');

  requestQueue.register(
      [django_url + 'sopnet', project.id, 'segmentation', this.activeSegmentationStack, 'segment', 'create_for_slices'].join('/'),
      'POST',
      {hash: hashes},
      CATMAID.jsonResponseHandler(this.refreshSegments.bind(this)));
};

CatsopWidget.prototype.constrainSegment = function (hash) {
  requestQueue.register(
      [django_url + 'sopnet', project.id, 'segmentation', this.activeSegmentationStack, 'segment', hash, 'constrain'].join('/'),
      'POST',
      {},
      CATMAID.jsonResponseHandler((function (json) {
        d3.selectAll($('[class~="seg-hash-' + hash + '"]')).classed('constrained', true);
      }).bind(this)));
};

CatsopWidget.prototype.solveAtLocation = function () {
  requestQueue.register(
      [django_url + 'sopnet', project.id, 'segmentation', this.activeSegmentationStack, 'core_at_location'].join('/'),
      'GET',
      {x: this.stack.x, y: this.stack.y, z: this.stack.z},
      CATMAID.jsonResponseHandler((function (json) {
        var core = json;
        requestQueue.register(
            [django_url + 'sopnet', project.id, 'segmentation', this.activeSegmentationStack,
             'core', core.id, 'solve'].join('/'),
            'POST',
            {},
            CATMAID.jsonResponseHandler((function (json) {
              growlAlert('Infomation', json.success);
            }))
        );
      }).bind(this))
  );
};

CatsopWidget.prototype.generateAssembliesAtLocation = function () {
  requestQueue.register(
      [django_url + 'sopnet', project.id, 'segmentation', this.activeSegmentationStack, 'core_at_location'].join('/'),
      'GET',
      {x: this.stack.x, y: this.stack.y, z: this.stack.z},
      CATMAID.jsonResponseHandler((function (json) {
        var core = json;
        requestQueue.register(
            [django_url + 'sopnet', project.id, 'segmentation', this.activeSegmentationStack,
             'core', core.id, 'generate_assemblies'].join('/'),
            'POST',
            {},
            CATMAID.jsonResponseHandler((function (json) {
              growlAlert('Success', 'Assemblies generated for core ' + core.id);
            }))
        );
      }).bind(this))
  );
};

CatsopWidget.prototype.activateSolution = function () {
  var selectedSolution = $('#catsop-results' + this.widgetID + '_solution_id option:selected').get(0);
  this.activeSolutionId = selectedSolution.value === 'Union' ? null : selectedSolution.value;
};

CatsopWidget.prototype.updateSolutions = function () {
  var solutionIds = this.sliceRows.reduce(function (ids, row) {
    Object.keys(row.in_solution).forEach(function (solutionId) {
      if (ids.indexOf(solutionId) < 0) ids.push(solutionId);
    });
    return ids;
  }, []);

  var solutionSelect = $('#catsop-results' + this.widgetID + '_solution_id');
  solutionIds.forEach(function (id) {
    solutionSelect.append($('<option>', {value: id}).text(id));
  });
};

CatsopWidget.prototype.getSliceRowByHash = function (hash) {
  return this.sliceRows.filter(function (slice) { return slice.hash === hash; })[0];
};

CatsopWidget.prototype.moveToSlice = function (rowIndex) {
  var slice = this.sliceRows[rowIndex];
  this.moveToObject(slice);
};

CatsopWidget.prototype.moveToActiveSegment = function() {
  this.moveToObject(this.activeSegment);
};

/**
 * Moves the stack view to any object with section and ctr or box properties.
 */
CatsopWidget.prototype.moveToObject = function (obj) {
  if (obj === undefined) return;
  var mag = Math.pow(2, this.blockInfo.scale);
  var z = obj.section - (('mask' in obj) ? 0 : 1), // For segments, move to the left section
      y, x;
  if (obj.hasOwnProperty('ctr')) {
    y = obj.ctr[1] * mag;
    x = obj.ctr[0] * mag;
  } else if (obj.hasOwnProperty('box') && obj.box.length === 4 ) {
    y = (obj.box[1] + obj.box[3]) * 0.5 * mag;
    x = (obj.box[0] + obj.box[2]) * 0.5 * mag;
  } else return; // Unknown object.

  // Sopnet works in pixels. Convert to project coordinates to account for resolution & transform.
  z = this.stack.stackToProjectZ(z, y, x);
  y = this.stack.stackToProjectY(z, y, x);
  x = this.stack.stackToProjectX(z, y, x);
  project.moveTo(z, y, x);
};
