angular.module( 'wikiaAuthority.wiki_users', [
  'ui.router',
  'tagged.directives.infiniteScroll',
  'wikiaAuthority.hubs',
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

      var with_users_for_wiki = function with_users_for_wiki(wiki_id, search_params, callable) {
        $http.get('/api/wiki/'+wiki_id+'/users/', {params: search_params}).success(callable);
      };

      return {
        with_users_for_wiki: with_users_for_wiki
      };
    }
  ]
)
.controller( 'WikiUsersCtrl',
  ['$scope', '$stateParams', 'WikiService', 'UserService', 'WikiUsersService', 'HubsService',
    function WikiUsersController( $scope, $stateParams, WikiService, UserService, WikiUsersService, HubsService ) {
      $scope.wiki_id = $stateParams.wiki_id;
      WikiService.with_details_for_wiki($scope.wiki_id, function(data) {
        $scope.wiki = data;
      });
      var page = 1;
      $scope.users = [];
      $scope.paginate = function() {
        WikiUsersService.with_users_for_wiki($scope.wiki_id, HubsService.params({page: page}), function(data) {
          data.users.map($scope.users.push);
          page += 1;
        });
      };
      $scope.paginate();
    }
  ]
);

