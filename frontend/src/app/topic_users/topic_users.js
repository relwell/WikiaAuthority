angular.module( 'wikiaAuthority.topic_users', [
  'ui.router',
  'wikiaAuthority.topic'
])

/**
 * Each section or module of the site can also have its own routes. AngularJS
 * will handle ensuring they are all available at run-time, but splitting it
 * this way makes each module more "self-contained".
 */
.config(function config( $stateProvider ) {
  $stateProvider.state( 'topic_users', {
    url: '/topic/:topic/users',
    views: {
      "main": {
        controller: 'TopicUsersCtrl',
        templateUrl: 'topic_users/topic_users.tpl.html'
      }
    },
    data:{ pageTitle: 'Users for Topic' }
  });
})
.service( 'TopicUsersService',
  ['$http',
    function TopicUsersService($http) {

      var with_users_for_topic = function with_users_for_topic(topic, callable) {
        $http.get('/api/topic/'+topic+'/users/').success(callable);
      };

      return {
        with_users_for_topic: with_users_for_topic
      };
    }
  ]
)
/**
 * And of course we define a controller for our route.
 */
.controller( 'TopicUsersCtrl',
  ['$scope', '$stateParams', 'TopicService', 'UserService', 'TopicUsersService',
    function TopicUsersController( $scope, $stateParams, TopicService, UserService, TopicUsersService ) {
      $scope.topic = $stateParams.topic;

      TopicUsersService.with_users_for_topic($scope.topic, function(data) {
        $scope.users = data.users;

        $scope.user_to_details = {};
        $scope.users.forEach(function(user){
          UsersService.with_details_for_user(user.user_id_i, function(data) {
            $scope.user_to_details[user.user_id_i] = data;
          });
        });
      });
    }
  ]
);

