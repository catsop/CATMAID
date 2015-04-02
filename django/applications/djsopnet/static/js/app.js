(function(){
  var app;

  app = angular.module('sopnetApp', ['ui.router', 'ui.bootstrap',
      'sopnetApp.controllers', 'sopnetApp.services', 'sopnetApp.filters']);

  app.config(function($interpolateProvider, $stateProvider, $urlRouterProvider) {
    // Play nice with Django's templates
    $interpolateProvider.startSymbol('[[');
    $interpolateProvider.endSymbol(']]');

    // Define routes
    $urlRouterProvider.otherwise('/');

    return $stateProvider.state('overview', {
      url: '/',
      templateUrl: 'overview',
      controller: 'overviewController',
      resolve: {
        tasksPromise: function (Tasks ) {
          return Tasks.fetch();
        },
        tasks: function (Tasks) {
          return Tasks.data();
        }
      }
    });
  });

  app.config(function($httpProvider) {
    var getCookie;
    getCookie = function(name) {
      var cookie, cookieValue, cookies, i;
      if (document.cookie && cookie !== "") {
        cookies = document.cookie.split(";");
        i = 0;
        while (i < cookies.length) {
          cookie = jQuery.trim(cookies[i]);
          if (cookie.substring(0, name.length + 1) === (name + "=")) {
            cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          }
          i++;
        }
      }
      return cookieValue;
    
    };
    // Include Django's CSRF token
    $httpProvider.defaults.headers.common['X-CSRFToken'] =
        getCookie("csrftoken");
  });

}).call(this);
