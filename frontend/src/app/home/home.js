angular.module( 'wikiaAuthority.home', [
  'ui.router'
])
.config(function config( $stateProvider ) {
  $stateProvider.state( 'home', {
    url: '/home',
    views: {
      "main": {
        controller: 'HomeCtrl',
        templateUrl: 'home/home.tpl.html'
      }
    },
    data:{ pageTitle: 'Home' }
  });
})
.controller( 'HomeCtrl', 
  ['$scope', '$location', 
  function HomeController( $scope, $location ) {
    $scope.search = function(resource, query) {
      $location.path('/'+resource).search('q', query);
    };
  }
]);

