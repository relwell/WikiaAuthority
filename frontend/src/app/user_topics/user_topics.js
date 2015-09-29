angular.module( 'wikiaAuthority.user_topics', [
  'ui.router',
  'wikiaAuthority.user',
  'wikiaAuthority.topic'
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

      var with_topics_for_user = function with_topics_for_user(user_id, callable) {
        $http.get('/api/user/'+user_id+'/topics/').success(callable);
      };

      return {
        with_topics_for_user: with_topics_for_user
      };
    }
  ]
)
.controller( 'UserTopicsCtrl',
  ['$scope', '$stateParams', 'UserService', 'TopicService', 'UserTopicsService',
    function UserTopicsController( $scope, $stateParams, UserService, TopicService, UserTopicsService ) {
      $scope.user_id = $stateParams.user_id;
      UserService.with_details_for_user($scope.user_id, function(data) {
        $scope.user = data;
      });
      UserTopicsService.with_topics_for_user($scope.user_id, function(data) {
        $scope.topics = data.topics;
      });
    }
  ]
);

