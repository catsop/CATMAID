(function() {
  var services;

  services = angular.module('sopnetApp.services', []);

  services.factory('Slice', function($http, $log) {
    var Slice;
    Slice = (function() {
      function Slide(data) {
        this.id = data.id;
        this.hash_value = data.hash_value;
        this.min_x = data.min_x;
        this.max_x = data.max_x;
        this.min_y = data.min_y;
        this.max_y = data.max_y;
        this.ctr_x = data.ctr_x;
        this.ctr_y = data.ctr_y;
        this.value = data.value;
        this.size = data.size;
        // TODO: Add shape, section, parent, assembly, stack
      };

      return Slice;

    })();
    return Slice;
  });

  services.factory('Slices', function($http, $http, Slice) {
    var slices;
    slices = {
      all: []
    };
    return {
      fromServer: function(data) {
        var slice, _i, _len, _results;
        slices['all'].length = 0;
        _results = [];
        for (_i = 0, _len = data.length; _i < _len; _i++) {
          slice = dara[i];
          _results.push(slices['all'].push(new Slice(slice)));
        }
      },
      fetch: function() {
        var _this = this;
        return $http({
          method: 'GET',
          url: '/sopnet/slices'
        }).success(function(data) {
          _this.fromServer(data);
          return $log.info("Successfully fetched slices.");
        }).error(function(data) {
          return $log.info("Failed to fetch slices.");
        });
      },
      data: function() {
        return slices;
      }
    };
  });

}).call(this);
