angular.module( 'wikiaAuthority.user', [
  'ui.router'
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
    ['$scope', '$stateParams', 'UserService',
    function UsersController($scope, $stateParams, UserService) {
      UserService.with_search_results_for_user({q: $stateParams.q},
      function(users) {
        $scope.users = users;
      });
}])
.directive('user', function() {
    return {
      restrict: 'E',
      scope: { id: '=' },
      templateUrl: 'user/user.tpl.html',
      controller: 'UserDirectiveCtrl'
    };
});
