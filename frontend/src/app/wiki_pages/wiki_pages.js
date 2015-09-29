angular.module( 'wikiaAuthority.wiki_pages', [
  'ui.router',
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

      var with_pages_for_wiki = function with_pages_for_wiki(wiki_id, callable) {
        $http.get('/api/wiki/'+wiki_id+'/pages/').success(callable);
      };

      return {
        with_pages_for_wiki: with_pages_for_wiki
      };
    }
  ]
)
.controller( 'WikiPagesCtrl',
  ['$scope', '$stateParams', 'WikiService', 'TopicService', 'WikiPagesService',
    function WikiPagesController( $scope, $stateParams, WikiService, TopicService, WikiPagesService ) {
      $scope.wiki_id = $stateParams.wiki_id;
      WikiService.with_details_for_wiki($scope.wiki_id, function(data) {
        $scope.wiki = data;
      });
      WikiPagesService.with_pages_for_wiki($scope.wiki_id, function(data) {
        $scope.pages = data.pages;
      });
    }
  ]
);

