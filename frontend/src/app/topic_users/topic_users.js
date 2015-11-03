angular.module( 'wikiaAuthority.topic_users', [
  'ui.router',
  'tagged.directives.infiniteScroll',
  'wikiaAuthority.hubs',
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

      var with_users_for_topic = function with_users_for_topic(topic, query_params, callable) {
        $http.get('/api/topic/'+topic+'/users/', {params: query_params}).success(callable);
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
  ['$scope', '$stateParams', 'TopicService', 'TopicUsersService', 'HubsService',
    function TopicUsersController( $scope, $stateParams, TopicService, TopicUsersService, HubsService ) {
      $scope.topic = $stateParams.topic;
      $scope.page = 1;
      $scope.users = [];
      $scope.paginate = function() {
        TopicUsersService.with_users_for_topic($scope.topic, HubsService.params({page: page}),
        function(data) {
          data.users.map(function(x){ $scope.users.push(x); });
          $scope.page += 1;
        });
      };
      $scope.paginate();
    }
  ]
);

