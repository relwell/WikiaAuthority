angular.module( 'wikiaAuthority.topic_pages', [
  'ui.router',
  'tagged.directives.infiniteScroll',
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
  ['$http',
    function TopicPagesService($http) {

      var with_pages_for_topic = function with_pages_for_topic(topic, query_params, callable) {
        $http.get('/api/topic/'+topic+'/pages/', {params: query_params}).success(callable);
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
  ['$scope', '$stateParams', 'TopicService', 'UserService', 'TopicPagesService', 'HubsService',
    function TopicPagesController( $scope, $stateParams, TopicService, UserService, TopicPagesService, HubsService) {
      $scope.topic = $stateParams.topic;
      $scope.pages = [];
      var page = 1;
      $scope.paginate = function() {
        TopicPagesService.with_pages_for_topic($scope.topic, {params: HubsService.params({page: page})}, 
        function(data) {
          data.pages.map(function(x){ $scope.pages.push(x); });
          page += 1;
        });
      };
      $scope.paginate();
    }
  ]
);

