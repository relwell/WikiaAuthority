angular.module( 'wikiaAuthority.topic_pages', [
  'ui.router',
  'wikiaAuthority.topic',
  'wikiaAuthority.hubs'
])

/**
 * Each section or module of the site can also have its own routes. AngularJS
 * will handle ensuring they are all available at run-time, but splitting it
 * this way makes each module more "self-contained".
 */
.config(function config( $stateProvider ) {
  $stateProvider.state( 'topic_pages', {
    url: '/topic/:topic/pages?:hub',
    views: {
      "main": {
        controller: 'TopicPagesCtrl',
        templateUrl: 'topic_pages/topic_pages.tpl.html'
      }
    },
    data:{ pageTitle: 'Pages for Topic' }
  });
})
.service( 'TopicPagesService',
  ['$http', 'HubsService',
    function TopicPagesService($http, HubsService) {

      var with_pages_for_topic = function with_pages_for_topic(topic, callable) {
        $http.get('/api/topic/'+topic+'/pages/', {params: HubsService.params()}).success(callable);
      };

      return {
        with_pages_for_topic: with_pages_for_topic
      };
    }
  ]
)
/**
 * And of course we define a controller for our route.
 */
.controller( 'TopicPagesCtrl',
  ['$scope', '$stateParams', 'TopicService', 'UserService', 'TopicPagesService',
    function TopicPagesController( $scope, $stateParams, TopicService, UserService, TopicPagesService ) {
      $scope.topic = $stateParams.topic;

      TopicPagesService.with_pages_for_topic($scope.topic, function(data) {
        $scope.pages = data.pages;
      });
    }
  ]
);

