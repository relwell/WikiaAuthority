angular.module( 'wikiaAuthority.user_wikis', [
  'ui.router',
  'wikiaAuthority.user',
  'wikiaAuthority.hubs'
])
.config(function config( $stateProvider ) {
  $stateProvider.state( 'user_wikis', {
    url: '/user/:user/wikis?:hub',
    views: {
      "main": {
        controller: 'UserWikisCtrl',
        templateUrl: 'user_wikis/user_wikis.tpl.html'
      }
    },
    data:{ pageTitle: 'Wikis for User' }
  });
})
.service( 'UserWikisService',
  ['$http',
    function UserWikisService($http) {

      var with_wikis_for_user = function with_wikis_for_user(user, search_params, callable) {
        $http.get('/api/user/'+user+'/wikis/', {params: search_params}).success(callable);
      };

      return {
        with_wikis_for_user: with_wikis_for_user
      };
    }
  ]
)
.controller( 'UserWikisCtrl',
  ['$scope', '$stateParams', 'UserService', 'WikiService', 'UserWikisService', 'HubsService',
    function UserWikisController( $scope, $stateParams, UserService, WikiService, UserWikisService, HubsService ) {
      $scope.user = $stateParams.user;
      var page = 1;
      $scope.wikis = [];
      $scope.paginate = function() {
        UserWikisService.with_wikis_for_user($scope.user, HubsService.params({page: page}), function(data) {
          $scope.wikis.concat(data.wikis);
          page += 1;
        });
      };
      $scope.paginate();
    }
  ]
);

