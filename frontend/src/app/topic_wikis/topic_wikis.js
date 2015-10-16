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
    function TopicWikisService($http) {

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
  ['$scope', '$stateParams', 'TopicService', 'WikiService', 'TopicWikisService',
    function WikiWikisController( $scope, $stateParams, TopicService, WikiService, TopicWikisService ) {
      $scope.topic = $stateParams.topic;

      TopicWikisService.with_wikis_for_topic($scope.topic, function(data) {
        $scope.wikis = data.wikis;

        $scope.wiki_to_details = {};
        $scope.wikis.forEach(function(wiki){
          WikisService.with_details_for_wiki(wiki.wiki_id_i, function(data) {
            $scope.wiki_to_details[wiki.wiki_id_i] = data;
          });
        });
      });
    }
  ]
);

