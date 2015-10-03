angular.module( 'wikiaAuthority.user_wikis', [
  'ui.router',
  'wikiaAuthority.user'
])
.config(function config( $stateProvider ) {
  $stateProvider.state( 'user_wikis', {
    url: '/user/:user/wikis',
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

      var with_wikis_for_user = function with_wikis_for_user(user, callable) {
        $http.get('/api/user/'+user+'/wikis/').success(callable);
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

        $scope.wiki_to_details = {};
        $scope.wikis.forEach(function(wiki){
          WikisService.with_details_for_wiki(wiki.wiki_id_i, function(data) {
            $scope.wiki_to_details[wiki.wiki_id_i] = data;
          });
        });
      });
    }
  ]
);

