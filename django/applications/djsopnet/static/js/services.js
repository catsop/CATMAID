(function() {
  var services;

  services = angular.module('sopnetApp.services', []);

  // Task factory

  services.factory('Task', function($http, $log) {
    var Task = (function() {
      function Task(data) {
        this.task_id = data.task_id;
        this.state = data.state;
        this.name = data.name;
      };

      return Task;

    })();
    return Task;
  });

  // Tasks factory

  services.factory('Tasks', function($http, $log, Task) {
    var tasks = {
      all: []
    };
    return {
      fromServer: function(data) {
        var slice, _i, _len, _results;
        tasks['all'].length = 0;
        _results = [];
        for (_i = 0, _len = data.length; _i < _len; _i++) {
          task = data[_i];
          _results.push(tasks['all'].push(new Task(task)));
        }
      },
      fetch: function() {
        var _this = this;
        return $http({
          method: 'GET',
          url: 'tasks'
        }).success(function(data) {
          _this.fromServer(data);
          return $log.info("Successfully fetched tasks.");
        }).error(function(data) {
          return $log.info("Failed to fetch tasks.");
        });
      },
      data: function() {
        return tasks;
      }
    };
  });

  // Slice factory

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

  // Slices factory

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
          slice = data[_i];
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
