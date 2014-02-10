(function(){
  var app;

  app = angular.module('sopnetApp', ['sopnetApp.controllers',
      'sopnetApp.services']);

  app.config(function($interpolateProvider, $routeProvider) {
    // Play nice with Django's templates
    $interpolateProvider.startSymbol('[[');
    $interpolateProvider.endSymbol(']]');

    // Define routes
    $routeProvider.when('overview', {
      templateUrl: 'templates/overview.html',
      controller: 'overviewController'
    }).otherwise({
      redirectTo: '/overview'
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
