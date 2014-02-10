(function(){
  var app;

  app = angular.module('sopnetApp', ['ui.router', 'sopnetApp.controllers',
      'sopnetApp.services', 'sopnetApp.filters']);

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
        tasks: function (Tasks) {
          Tasks.fetch();
          return Tasks.data();
        }
      }
    });
  });

  app.config(function($httpProvider) {
    var getCookie;
    getCookie = function(name) {
      var cookie, cookieValue, cookies, i;
      if (document.cookie && cookie != "") {
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
    return $httpProvider.defaults.headers.common['X-CSRFToken'] =
        getCookie("csrftoken");
  });

}).call(this);
