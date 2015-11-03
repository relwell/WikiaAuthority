angular.module( 'wikiaAuthority.wiki_topics', [
  'ui.router',
  'tagged.directives.infiniteScroll',
  'wikiaAuthority.wiki',
  'wikiaAuthority.topic'
])
.config(function config( $stateProvider ) {
  $stateProvider.state( 'wiki_topics', {
    url: '/wiki/:wiki_id/topics',
    views: {
      "main": {
        controller: 'WikiTopicsCtrl',
        templateUrl: 'wiki_topics/wiki_topics.tpl.html'
      }
    },
    data:{ pageTitle: 'Topics for Wiki' }
  });
})
.service( 'WikiTopicsService',
  ['$http',
    function WikiTopicsService($http) {

      var with_topics_for_wiki = function with_topics_for_wiki(wiki_id, search_params, callable) {
        $http.get('/api/wiki/'+wiki_id+'/topics/', {params: search_params}).success(callable);
      };

      return {
        with_topics_for_wiki: with_topics_for_wiki
      };
    }
  ]
)
.controller( 'WikiTopicsCtrl',
  ['$scope', '$stateParams', 'WikiService', 'TopicService', 'WikiTopicsService', 'HubsService',
    function WikiTopicsController( $scope, $stateParams, WikiService, TopicService, WikiTopicsService, HubsService ) {
      $scope.wiki_id = $stateParams.wiki_id;
      WikiService.with_details_for_wiki($scope.wiki_id, function(data) {
        $scope.wiki = data;
      });
      var page = 1;
      $scope.topics = [];
      $scope.paginate = function() {
        WikiTopicsService.with_topics_for_wiki($scope.wiki_id, HubsService.params({page: page}), function(data) {
          $scope.topics.concat(data.topics);
        });
      };
      $scope.paginate();
    }
  ]
);

