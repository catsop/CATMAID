(function() {
  var controllers;

  controllers = angular.module('sopnetApp.controllers', []);

  controllers.controller('overviewController',
      function($scope, $state, $log, $http, tasks) {
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

        $scope.tasks = tasks.all;
        return
      });

}).call(this);
