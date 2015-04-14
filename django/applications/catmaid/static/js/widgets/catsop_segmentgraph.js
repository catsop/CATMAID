/**
 * An interactive D3 graph representing the segments associated with sets of
 * slices in adjacent sections.
 *
 * Heavily adapted from the D3 Sankey plugin (GPL-compatible BSD license):
 * https://github.com/d3/d3-plugins/tree/master/sankey
 */
CatsopWidget.SegmentGraph = function() {
  var seggraph = {},
      nodeWidths = [24],
      nodePadding = 8,
      size = [1, 1],
      nodes = [],
      links = [];

  seggraph.nodeWidths = function(_) {
    if (!arguments.length) return nodeWidths;
    nodeWidths = _;
    return seggraph;
  };

  seggraph.nodePadding = function(_) {
    if (!arguments.length) return nodePadding;
    nodePadding = +_;
    return seggraph;
  };

  seggraph.nodes = function(_) {
    if (!arguments.length) return nodes;
    nodes = _;
    return seggraph;
  };

  seggraph.links = function(_) {
    if (!arguments.length) return links;
    links = _;
    return seggraph;
  };

  seggraph.size = function(_) {
    if (!arguments.length) return size;
    size = _;
    return seggraph;
  };

  seggraph.layout = function(iterations) {
    computeNodeLinks();
    computeNodeValues();
    computeNodeBreadths();
    computeNodeDepths(iterations);
    computeLinkDepths();
    return seggraph;
  };

  seggraph.relayout = function() {
    computeLinkDepths();
    return seggraph;
  };

  seggraph.link = function() {
    var curvature = 0.5;

    function link(d) {
      var x0 = d.source.x + d.source.dx,
          x1 = d.target.x,
          xi = d3.interpolateNumber(x0, x1),
          x2 = xi(curvature),
          x3 = xi(1 - curvature),
          y0 = d.source.y + d.sy + d.dy / 2,
          y1 = d.target.y + d.ty + d.dy / 2;
      return "M" + x0 + "," + y0
           + "C" + x2 + "," + y0
           + " " + x3 + "," + y1
           + " " + x1 + "," + y1;
    }

    link.curvature = function(_) {
      if (!arguments.length) return curvature;
      curvature = +_;
      return link;
    };

    return link;
  };

  function sliceNode(node) {
    // Only the first and last columns (breadths 0 and 2) are slice nodes.
    return node.breadth !== 1;
  }

  // Populate the sourceLinks and targetLinks for each node.
  // Also, if the source and target are not objects, assume they are indices.
  function computeNodeLinks() {
    nodes.forEach(function(node) {
      node.sourceLinks = [];
      node.targetLinks = [];
      node.linkPartners = function () {
        return this.sourceLinks.map(function (l) {return l.target;})
            .concat(this.targetLinks.map(function (l) {return l.source;}));
      };
    });
    links.forEach(function(link) {
      var source = link.source,
          target = link.target;
      if (typeof source === "number") source = link.source = nodes[link.source];
      if (typeof target === "number") target = link.target = nodes[link.target];
      source.sourceLinks.push(link);
      target.targetLinks.push(link);
    });
  }

  // Compute the value (size) of each node by summing the associated links.
  function computeNodeValues() {
    nodes.forEach(function(node) {
      if (sliceNode(node)) node.graphValue = 0; // Not used for slice nodes.
      else node.graphValue = Math.max(d3.sum(node.sourceLinks, graphValue),
                              d3.sum(node.targetLinks, graphValue));
    });
  }

  function computeNodeBreadths() {
    nodes.forEach(function(node) {
      node.dx = nodeWidths[node.breadth % nodeWidths.length];
      node.x = (size[0] - node.dx) * node.breadth/2;
    });
  }

  function computeNodeDepths(iterations) {
    var nodesByBreadth = d3.nest()
        .key(function(d) { return d.x; })
        .sortKeys(d3.ascending)
        .entries(nodes)
        .map(function(d) { return d.values; });

    //
    initializeNodeDepth();
    resolveCollisions();
    for (var alpha = 1; iterations > 0; --iterations) {
      relaxRightToLeft(alpha *= 0.99);
      resolveCollisions();
      relaxLeftToRight(alpha);
      resolveCollisions();
    }

    function initializeNodeDepth() {
      seggraph.sliceScale = nodesByBreadth
          .filter(function (ns) { return sliceNode(ns[0]); })
          .reduce(function (minScale, nodes) {
            var heightScale = size[1] / nodes
              .reduce(function (sum, n) { return sum + nodePadding + n.box[3] - n.box[1]; }, 0);
            return Math.min(heightScale, minScale);
          }, 1);
      var heightScale = seggraph.sliceScale;

      var ky = d3.min(nodesByBreadth, function(nodes) {
        return (size[1] - (nodes.length - 1) * nodePadding) / d3.sum(nodes, graphValue);
      });
      ky = Math.min(ky, heightScale); // Prevent links being larger than slices.

      nodesByBreadth.forEach(function(nodes) {
        nodes.forEach(function(node, i) {
          node.y = i;
          if (sliceNode(node)) node.dy = heightScale * (node.box[3] - node.box[1]);
          else node.dy = node.graphValue * ky;
        });
      });

      links.forEach(function(link) {
        link.dy = link.graphValue * ky;
      });
    }

    function relaxLeftToRight(alpha) {
      nodesByBreadth.forEach(function(nodes, breadth) {
        nodes.forEach(function(node) {
          if (node.targetLinks.length) {
            var y = d3.sum(node.targetLinks, weightedSource) / d3.sum(node.targetLinks, graphValue);
            node.y += (y - center(node)) * alpha;
          }
        });
      });

      function weightedSource(link) {
        return center(link.source) * link.graphValue;
      }
    }

    function relaxRightToLeft(alpha) {
      nodesByBreadth.slice().reverse().forEach(function(nodes) {
        nodes.forEach(function(node) {
          if (node.sourceLinks.length) {
            var y = d3.sum(node.sourceLinks, weightedTarget) / d3.sum(node.sourceLinks, graphValue);
            node.y += (y - center(node)) * alpha;
          }
        });
      });

      function weightedTarget(link) {
        return center(link.target) * link.graphValue;
      }
    }

    function resolveCollisions() {
      nodesByBreadth.forEach(function(nodes) {
        var node,
            dy,
            y0 = 0,
            n = nodes.length,
            i;

        // Push any overlapping nodes down.
        nodes.sort(ascendingDepth);
        for (i = 0; i < n; ++i) {
          node = nodes[i];
          dy = y0 - node.y;
          if (dy > 0) node.y += dy;
          y0 = node.y + node.dy + nodePadding;
        }

        // If the bottommost node goes outside the bounds, push it back up.
        dy = y0 - nodePadding - size[1];
        if (dy > 0) {
          y0 = node.y -= dy;

          // Push any overlapping nodes back up.
          for (i = n - 2; i >= 0; --i) {
            node = nodes[i];
            dy = node.y + node.dy + nodePadding - y0;
            if (dy > 0) node.y -= dy;
            y0 = node.y;
          }
        }
      });
    }

    function ascendingDepth(a, b) {
      return a.y - b.y;
    }
  }

  function computeLinkDepths() {
    nodes.forEach(function(node) {
      node.sourceLinks.sort(ascendingTargetDepth);
      node.targetLinks.sort(ascendingSourceDepth);
    });
    nodes.forEach(function(node) {
      var sy = 0, ty = 0;
      // Center links for slice nodes (first and last column)
      if (sliceNode(node)) ty = sy = node.dy / 2;
      node.sourceLinks.forEach(function(link) {
        if (!sliceNode(node)) {
          link.sy = sy;
          sy += link.dy;
        } else link.sy = sy - link.dy / 2;
      });
      node.targetLinks.forEach(function(link) {
        if (!sliceNode(node)) {
          link.ty = ty;
          ty += link.dy;
        } else link.ty = ty - link.dy / 2;
      });
    });

    function ascendingSourceDepth(a, b) {
      return a.source.y - b.source.y;
    }

    function ascendingTargetDepth(a, b) {
      return a.target.y - b.target.y;
    }
  }

  function center(node) {
    return node.y + node.dy / 2;
  }

  function graphValue(link) {
    return link.graphValue;
  }

  return seggraph;
};
