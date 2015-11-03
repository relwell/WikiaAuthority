angular.module( 'wikiaAuthority.user_topics', [
  'ui.router',
  'tagged.directives.infiniteScroll',
  'wikiaAuthority.user',
  'wikiaAuthority.topic',
  'wikiaAuthority.hubs'
])
.config(function config( $stateProvider ) {
  $stateProvider.state( 'user_topics', {
    url: '/user/:user_id/topics',
    views: {
      "main": {
        controller: 'UserTopicsCtrl',
        templateUrl: 'user_topics/user_topics.tpl.html'
      }
    },
    data:{ pageTitle: 'Topics for User' }
  });
})
.service( 'UserTopicsService',
  ['$http',
    function UserTopicsService($http) {

      var with_topics_for_user = function with_topics_for_user(user_id, search_params, callable) {
        $http.get('/api/user/'+user_id+'/topics/', {params: search_params}).success(callable);
      };

      return {
        with_topics_for_user: with_topics_for_user
      };
    }
  ]
)
.controller( 'UserTopicsCtrl',
  ['$scope', '$stateParams', 'UserService', 'TopicService', 'UserTopicsService', 'HubsService',
    function UserTopicsController( $scope, $stateParams, UserService, TopicService, UserTopicsService, HubsService ) {
      $scope.user_id = $stateParams.user_id;
      UserService.with_details_for_user($scope.user_id, function(data) {
        $scope.user = data;
      });
      $scope.topics = [];
      $scope.page = 1;
      $scope.fetching = false; $scope.paginate = function() { $scope.fetching = true;
        UserTopicsService.with_topics_for_user($scope.user_id, HubsService.params({page: $scope.page}), function(data) {
          data.topics.map(function(x){ $scope.topics.push(x); });
          $scope.page += 1; $scope.fetching = false;
        });
      };
      $scope.paginate();
    }
  ]
);

