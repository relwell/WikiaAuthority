angular.module( 'wikiaAuthority.wiki_pages', [
  'ui.router',
  'tagged.directives.infiniteScroll',
  'wikiaAuthority.wiki',
  'wikiaAuthority.page'
])
.config(function config( $stateProvider ) {
  $stateProvider.state( 'wiki_pages', {
    url: '/wiki/:wiki_id/pages',
    views: {
      "main": {
        controller: 'WikiPagesCtrl',
        templateUrl: 'wiki_pages/wiki_pages.tpl.html'
      }
    },
    data:{ pageTitle: 'Pages for Wiki' }
  });
})
.service( 'WikiPagesService',
  ['$http',
    function WikiPagesService($http) {

      var with_pages_for_wiki = function with_pages_for_wiki(wiki_id, search_params, callable) {
        $http.get('/api/wiki/'+wiki_id+'/pages/', {params: search_params}).success(callable);
      };

      return {
        with_pages_for_wiki: with_pages_for_wiki
      };
    }
  ]
)
.controller( 'WikiPagesCtrl',
  ['$scope', '$stateParams', 'WikiService', 'TopicService', 'WikiPagesService', 'HubsService',
    function WikiPagesController( $scope, $stateParams, WikiService, TopicService, WikiPagesService, HubsService ) {
      $scope.wiki_id = $stateParams.wiki_id;
      WikiService.with_details_for_wiki($scope.wiki_id, function(data) {
        $scope.wiki = data;
      });
      $scope.pages = [];
      $scope.page = 1;
      WikiPagesService.with_pages_for_wiki($scope.wiki_id, HubsService.params({page: page}), function(data) {
        data.pages.map(function(x){ $scope.pages.push(x); });
        $scope.page += 1;
      });
      $scope.paginate();
    }
  ]
);

