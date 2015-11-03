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
  ['$http', 'HubsService',
    function UserWikisService($http, HubsService) {

      var with_wikis_for_user = function with_wikis_for_user(user, callable) {
        $http.get('/api/user/'+user+'/wikis/', {params: HubsService.params()}).success(callable);
      };

      return {
        with_wikis_for_user: with_wikis_for_user
      };
    }
  ]
)
.controller( 'UserWikisCtrl',
  ['$scope', '$stateParams', 'UserService', 'WikiService', 'UserWikisService',
    function UserWikisController( $scope, $stateParams, UserService, WikiService, UserWikisService ) {
      $scope.user = $stateParams.user;

      UserWikisService.with_wikis_for_user($scope.user, function(data) {
        $scope.wikis = data.wikis;
      });
    }
  ]
);
