(function() {
  var filters = angular.module('sopnetApp.filters', []);

  filters.filter('statetoclass', function() {
    return function(input) {
      if (input === 'SUCCESS') {
        return 'success';
      } else if (input === 'FAILURE') {
        return 'danger';
      } else if (input === 'REVOKED') {
        return 'danger';
      } else if (input === 'STARTED') {
        return 'active';
      } else if (input === 'RETRY') {
        return 'warning';
      } else if (input === 'RECEIVED') {
        return 'info';
      } else {
        return '';
      }
    };
  });
})();
