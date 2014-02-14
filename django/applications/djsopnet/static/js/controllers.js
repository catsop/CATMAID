(function() {
  var controllers;

  controllers = angular.module('sopnetApp.controllers', []);

  controllers.controller('overviewController',
      function($scope, $state, $log, $http, tasks) {
        $scope.r = function() {
          return Math.floor((Math.random()*100)+1);
        };
        $scope.pstr = function(x, y, z) {
          return "(" + x + ", " + y + ", " + z + ")";
        };
        $scope.launchSliceGuarantorTask = function(x, y, z) {
          var p = $scope.pstr(x, y, z);
          $log.info("Launching Slice Guarantor Task for position " + p + ".");
          return $http({
            method: 'GET',
            url: 'sliceguarantor/' + x + '/' + y + '/' + z + '/test',
          }).success(function(data) {
            return $log.info("Successfully launched Slice Guarantor Task for " +
                "position " + p + ".");
          }).error(function(data) {
            return $log.info("Failed to launch Slice Guarantor Task for " +
                "position " + p + ".");
          });
        };
        $scope.launchSegmentGuarantorTask = function(x, y, z) {
          var p = $scope.pstr(x, y, z);
          $log.info("Launching Segment Guarantor Task for position " + p + ".");
          return $http({
            method: 'GET',
            url: 'segmentguarantor/' + x + '/' + y + '/' + z + '/test',
          }).success(function(data) {
            return $log.info("Successfully launched Segment Guarantor Task " +
                "for position " + p + ".");
          }).error(function(data) {
            return $log.info("Failed to launch Segment Guarantor Task " +
                "for position " + p + ".");
          });
        };
        $scope.launchSolutionGuarantorTask = function() {
          $log.info("Launching Solution Guarantor Task");
          return $http({
            method: 'GET',
            url: 'solutionguarantor/test',
          }).success(function(data) {
            return $log.info("Successfully launched Solution Guarantor Task.");
          }).error(function(data) {
            return $log.info("Failed to launch Solution Guarantor Task.");
          });
        };
        $scope.launchSolveSubvolumeTask = function() {
          $log.info("Launching Solve Subvolume Guarantor Task");
          return $http({
            method: 'GET',
            url: 'solvesubvolume/test',
          }).success(function(data) {
            return $log.info("Successfully launched Solve Subvolume Guarantor Task.");
          }).error(function(data) {
            return $log.info("Failed to launch Solve Subvolume Guarantor Task.");
          });
        };
        $scope.launchTraceNeuronTask = function() {
          $log.info("Launching Trace Neuron Task");
          return $http({
            method: 'GET',
            url: 'traceneuron/test',
          }).success(function(data) {
            return $log.info("Successfully launched Trace Neuron Task.");
          }).error(function(data) {
            return $log.info("Failed to launch Trace Neuron Task.");
          });
        };

        // Tasks
        $scope.tasks = tasks.all;
        $scope.filteredTasks = [];

        // Pagination of tasks
        $scope.currentPage = 1;
        $scope.totalItems = tasks.all.length;
        $scope.itemsPerPage = 20;
        $scope.maxSize = 10;

        $scope.setPage = function(pageNo) {
          $scope.currentPage = pageNo;
        };

        $scope.$watch('currentPage + itemsPerPage', function() {
          var begin = (($scope.currentPage - 1) * $scope.itemsPerPage),
              end   = begin + $scope.itemsPerPage;
          $scope.filteredTasks = $scope.tasks.slice(begin, end);
        });
      });

}).call(this);
