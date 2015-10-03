angular.module( 'wikiaAuthority.wiki_users', [
  'ui.router',
  'wikiaAuthority.wiki'
])
.config(function config( $stateProvider ) {
  $stateProvider.state( 'wiki_users', {
    url: '/wiki/:wiki_id/users',
    views: {
      "main": {
        controller: 'WikiUsersCtrl',
        templateUrl: 'wiki_users/wiki_users.tpl.html'
      }
    },
    data:{ pageTitle: 'Users for Wiki' }
  });
})
.service( 'WikiUsersService',
  ['$http',
    function WikiUsersService($http) {

      var with_users_for_wiki = function with_users_for_wiki(wiki_id, callable) {
        $http.get('/api/wiki/'+wiki_id+'/users/').success(callable);
      };

      return {
        with_users_for_wiki: with_users_for_wiki
      };
    }
  ]
)
.controller( 'WikiUsersCtrl',
  ['$scope', '$stateParams', 'WikiService', 'UserService', 'WikiUsersService',
    function WikiUsersController( $scope, $stateParams, WikiService, UserService, WikiUsersService ) {
      $scope.wiki_id = $stateParams.wiki_id;
      WikiService.with_details_for_wiki($scope.wiki_id, function(data) {
        $scope.wiki = data;
      });

      WikiUsersService.with_users_for_wiki($scope.wiki_id, function(data) {
        $scope.users = data.users;

        $scope.user_to_details = {};
        $scope.users.forEach(function(user){
          UserService.with_details_for_user(user.user_id_i, function(data) {
            $scope.user_to_details[user.user_id_i] = data;
          });
        });
      });
    }
  ]
);

