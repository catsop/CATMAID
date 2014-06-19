(function() {
  var controllers;

  controllers = angular.module('sopnetApp.controllers', []);

  controllers.controller('overviewController',
      function($scope, $state, $log, $http, tasks, Tools) {
        // Provide random number generator to template
        $scope.r = Tools.r;

        $scope.setupForSopnet = function(pid, sid, w, h, d, cw, ch, cd) {
          var bs = Tools.pstr(w, h, d);
          var cs = Tools.pstr(cw, ch, cd);
          $log.info("Setting up stack " + sid + " of project " + pid + ".");
          return $http({
            method: 'GET',
            url: pid + '/stack/' + sid + '/setup_blocks',
            params: {
               'width': w,
               'height': h,
               'depth': d,
               'cwidth': cw,
               'cheight': ch,
               'cdepth': cd
            }
          }).success(function(data) {
            return $log.info("Successfully set up stack " + sid + " of project " +
                pid + " to use block size " + bs + " and core size " + cs + ".");
          }).error(function(data) {
            return $log.info("Failed to  set up stack " + sid + " of project " +
                pid + " to use block size " + bs + " and core size " + cs + ".");
          });
        };

        $scope.setupAllForSopnet = function(pid, rsid, mid, w, h, d, cw, ch, cd) {
            $scope.setupForSopnet(pid, rsid, w, h, d, cw, ch, cd);
            $scope.setupForSopnet(pid, msid, w, h, d, cw, ch, cd);
        }

        $scope.launchSliceGuarantorTask = function(pid, rsid, msid, x, y, z) {
          var p = Tools.pstr(x, y, z);
          $log.info("Launching Slice Guarantor Task for position " + p + ".");
          return $http({
            method: 'GET',
            url: 'sliceguarantor/' + pid + '/' + rsid + '/' + msid + '/' + x + '/' + y + '/' + z + '/test',
          }).success(function(data) {
            return $log.info("Successfully launched Slice Guarantor Task for " +
                "position " + p + ".");
          }).error(function(data) {
            return $log.info("Failed to launch Slice Guarantor Task for " +
                "position " + p + ".");
          });
        };
        $scope.launchSegmentGuarantorTask = function(pid, rsid, msid, x, y, z) {
          var p = Tools.pstr(x, y, z);
          $log.info("Launching Segment Guarantor Task for position " + p + ".");
          return $http({
            method: 'GET',
            url: 'segmentguarantor/' + pid + '/' + rsid + '/' + msid + '/' + x + '/' + y + '/' + z + '/test',
          }).success(function(data) {
            return $log.info("Successfully launched Segment Guarantor Task " +
                "for position " + p + ".");
          }).error(function(data) {
            return $log.info("Failed to launch Segment Guarantor Task " +
                "for position " + p + ".");
          });
        };
        $scope.launchSolutionGuarantorTask = function(pid, rsid, msid, x, y, z) {
          var p = Tools.pstr(x, y, z);
          $log.info("Launching Solution Guarantor Task for position " + p + ".");
          return $http({
            method: 'GET',
            url: 'solutionguarantor/' + pid + '/' + rsid + '/' + msid + '/' + x + '/' + y + '/' + z + '/test',
          }).success(function(data) {
            return $log.info("Successfully launched Solution Guarantor Task " +
                "for position " + p + ".");
          }).error(function(data) {
            return $log.info("Failed to launch Solution Guarantor Task " +
                "for position " + p + ".");
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
