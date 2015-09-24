angular.module( 'wikiaAuthority.user', [
  'ui.router'
])
.service( 'UserService',
  ['$http',
    function UserService($http) {

    var with_details_for_user = function with_details_for_user(user_id, callable) {
      return $http.get('/api/user/'+user_id+'/details').success(callable);
    };

    return {
      with_details_for_user: with_details_for_user
    };
  }]
)
.controller( 'UserCtrl',
    ['$scope', 'UserService',
    function UserController($scope, UserService) {
      UserService.with_details_for_user($scope.id,
      function(data) {
        $scope.user_data = data.items[0];
      });
}])
.directive('user', function() {
    return {
      restrict: 'E',
      scope: { id: '=' },
      templateUrl: 'user/user.tpl.html',
      controller: 'UserCtrl'
    };
});
