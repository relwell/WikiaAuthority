angular.module( 'wikiaAuthority.topic_wikis', [
  'ui.router',
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
  ['$http', 'HubsService',
    function TopicWikisService($http, HubsService) {

      var with_wikis_for_topic = function with_wikis_for_topic(topic, callable) {
        $http.get('/api/topic/'+topic+'/wikis/', {params: HubsService.params()}).success(callable);
      };

      return {
        with_wikis_for_topic: with_wikis_for_topic
      };
    }
  ]
)
.controller( 'TopicWikisCtrl',
  ['$scope', '$stateParams', 'TopicService', 'TopicWikisService',
    function TopicWikisController( $scope, $stateParams, TopicService, TopicWikisService ) {
      $scope.topic = $stateParams.topic;

      TopicWikisService.with_wikis_for_topic($scope.topic, function(data) {
        $scope.wikis = data.wikis;
      });
    }
  ]
);

