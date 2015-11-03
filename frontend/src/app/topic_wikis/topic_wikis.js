angular.module( 'wikiaAuthority.topic_wikis', [
  'ui.router',
  'tagged.directives.infiniteScroll',
  'wikiaAuthority.topic',
  'wikiaAuthority.hubs'
])
.config(function config( $stateProvider ) {
  $stateProvider.state( 'topic_wikis', {
    url: '/topic/:topic/wikis?:hub',
    views: {
      "main": {
        controller: 'TopicWikisCtrl',
        templateUrl: 'topic_wikis/topic_wikis.tpl.html'
      }
    },
    data:{ pageTitle: 'Wikis for Topic' }
  });
})
.service( 'TopicWikisService',
  ['$http',
    function TopicWikisService($http) {

      var with_wikis_for_topic = function with_wikis_for_topic(topic, query_params, callable) {
        $http.get('/api/topic/'+topic+'/wikis/', {params: query_params}).success(callable);
      };

      return {
        with_wikis_for_topic: with_wikis_for_topic
      };
    }
  ]
)
.controller( 'TopicWikisCtrl',
  ['$scope', '$stateParams', 'TopicService', 'TopicWikisService', 'HubsService',
    function TopicWikisController( $scope, $stateParams, TopicService, TopicWikisService, HubsService ) {
      $scope.topic = $stateParams.topic;
      $scope.page = 1;
      $scope.wikis = [];
      $scope.paginate = function() {
        TopicWikisService.with_wikis_for_topic($scope.topic, 
        HubsService.params({page: page}),
        function(data) {
          data.wikis.map(function(x){ $scope.wikis.push(x); });
          $scope.page += 1;
        });
      };
      $scope.paginate();
    }
  ]
);

