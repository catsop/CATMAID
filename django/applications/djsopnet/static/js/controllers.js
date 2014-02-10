(function() {
  var controllers;

  controllers = angular.module('sopnetApp.controllers', []);

  controllers.controller('overviewController', function($scope, $state, $log, tasks) {
    return $scope.tasks = tasks.all;
  });

}).call(this);
