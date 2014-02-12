(function() {
  var controllers;

  controllers = angular.module('sopnetApp.controllers', []);

  controllers.controller('overviewController',
      function($scope, $state, $log, $http, tasks) {
        $scope.launchSliceGuarantorTask = function() {
          $log.info("Launching Slice Guarantor Task");
          return $http({
            method: 'GET',
            url: 'sliceguarantor/test',
          }).success(function(data) {
            return $log.info("Successfully launched Slice Guarantor Task.");
          }).error(function(data) {
            return $log.info("Failed to launch Slice Guarantor Task.");
          });
        };
        $scope.launchSegmentGuarantorTask = function() {
          $log.info("Launching Segment Guarantor Task");
          return $http({
            method: 'GET',
            url: 'segmentguarantor/test',
          }).success(function(data) {
            return $log.info("Successfully launched Segment Guarantor Task.");
          }).error(function(data) {
            return $log.info("Failed to launch Segment Guarantor Task.");
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

        $scope.tasks = tasks.all;
        return
      });

}).call(this);
