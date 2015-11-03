angular.module( 'wikiaAuthority.user', [
  'ui.router'
  'infinite-scroll',
  'wikiaAuthority.hubs'
])
.config(function config( $stateProvider ) {
  $stateProvider.state( 'user', {
    url: '/users?:q',
    views: {
      "main": {
        controller: 'UsersCtrl',
        templateUrl: 'user/users.tpl.html'
      }
    },
    data:{ pageTitle: 'Users' }
  });
})
.service( 'UserService',
  ['$http',
    function UserService($http) {

    var with_details_for_user = function with_details_for_user(user_id, callable) {
      return $http.get('/api/user/'+user_id+'/details').success(callable);
    };
    
    var with_search_results_for_user = function with_search_results_for_user(search_params, callable) {
      return $http.get('/api/users/', {params:search_params}).success(callable);
    };

    return {
      with_details_for_user: with_details_for_user,
      with_search_results_for_user: with_search_results_for_user
    };
  }]
)
.controller( 'UserDirectiveCtrl',
    ['$scope', 'UserService',
    function UserDirectiveController($scope, UserService) {
      UserService.with_details_for_user($scope.id,
      function(data) {
        $scope.user_data = data.items[0];
      });
}])
.controller( 'UsersCtrl',
    ['$scope', '$stateParams', 'UserService', 'HubsService',
    function UsersController($scope, $stateParams, UserService, HubsService) {
      var page = 1;
      $scope.users = [];
      $scope.paginate = function() {
        UserService.with_search_results_for_user(HubsService.params({q: $stateParams.q, page: page}),
        function(users) {
          $scope.users.concat(users);
          page += 1;
        });
      };
      $scope.paginate();
}])
.directive('user', function() {
    return {
      restrict: 'E',
      scope: { id: '=' },
      templateUrl: 'user/user.tpl.html',
      controller: 'UserDirectiveCtrl'
    };
});
