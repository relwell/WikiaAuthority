angular.module( 'wikiaAuthority.user_pages', [
  'ui.router',
  'tagged.directives.infiniteScroll',
  'wikiaAuthority.user',
  'wikiaAuthority.page',
  'wikiaAuthority.hubs'
])
.config(function config( $stateProvider ) {
  $stateProvider.state( 'user_pages', {
    url: '/user/:user_id/pages',
    views: {
      "main": {
        controller: 'UserPagesCtrl',
        templateUrl: 'user_pages/user_pages.tpl.html'
      }
    },
    data:{ pageTitle: 'Pages for User' }
  });
})
.service( 'UserPagesService',
  ['$http',
    function UserPagesService($http) {

      var with_pages_for_user = function with_pages_for_user(user_id, search_params, callable) {
        $http.get('/api/user/'+user_id+'/pages/', {params: search_params}).success(callable);
      };

      return {
        with_pages_for_user: with_pages_for_user
      };
    }
  ]
)
.controller( 'UserPagesCtrl',
  ['$scope', '$stateParams', 'UserService', 'TopicService', 'UserPagesService', 'HubsService',
    function UserPagesController( $scope, $stateParams, UserService, TopicService, UserPagesService, HubsService) {
      $scope.user_id = $stateParams.user_id;
      $scope.page = 1;
      $scope.pages = [];
      $scope.fetching = false; $scope.paginate = function() { $scope.fetching = true;
        UserPagesService.with_pages_for_user($scope.user_id, function(data) {
          data.pages.map(function() {
            page.id = page.id.split('_').slice(0, -1).join('_');
            return $scope.pages.push(page);
          });
          $scope.page += 1; $scope.fetching = false;
        });
      };
      UserService.with_details_for_user($scope.user_id, HubsService.params({offset: $scope.page * 10}), function(data) {
        $scope.user = data;
      });
      $scope.paginate();
    }
  ]
);

