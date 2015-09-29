angular.module( 'wikiaAuthority.user_pages', [
  'ui.router',
  'wikiaAuthority.user',
  'wikiaAuthority.page'
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

      var with_pages_for_user = function with_pages_for_user(user_id, callable) {
        $http.get('/api/user/'+user_id+'/pages/').success(callable);
      };

      return {
        with_pages_for_user: with_pages_for_user
      };
    }
  ]
)
.controller( 'UserPagesCtrl',
  ['$scope', '$stateParams', 'UserService', 'TopicService', 'UserPagesService',
    function UserPagesController( $scope, $stateParams, UserService, TopicService, UserPagesService ) {
      $scope.user_id = $stateParams.user_id;
      UserService.with_details_for_user($scope.user_id, function(data) {
        $scope.user = data;
      });
      UserPagesService.with_pages_for_user($scope.user_id, function(data) {
        $scope.pages = data.pages;
      });
    }
  ]
);

