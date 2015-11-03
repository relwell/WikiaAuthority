angular.module( 'wikiaAuthority.wiki', [
  'ui.router',
  'wikiaAuthority.hubs'
])
.config(function config( $stateProvider ) {
  $stateProvider.state( 'wikis', {
    url: '/wikis?:q&:hub',
    views: {
      "main": {
        controller: 'WikisCtrl',
        templateUrl: 'wiki/wikis.tpl.html'
      }
    },
    data:{ pageTitle: 'Wikis' }
  });
})
.service( 'WikiService',
  ['$http',
    function WikiService($http) {

    var with_details_for_wiki = function with_details_for_wiki(wiki_id, callable) {
      return $http.get('/api/wiki/'+wiki_id+'/details').success(callable);
    };

    var with_search_results_for_wiki = function with_search_results_for_wiki(search_params, callable) {
      return $http.get('/api/wikis/', {params: search_params}).success(callable);
    };

    return {
      with_details_for_wiki: with_details_for_wiki,
      with_search_results_for_wiki: with_search_results_for_wiki
    };
  }]
)
.controller( 'WikiDirectiveCtrl',
    ['$scope', 'WikiService',
    function WikiDirectiveController($scope, WikiService) {
      WikiService.with_details_for_wiki($scope.id,
      function(wiki_data) {
        $scope.image_href = wiki_data.image;
        $scope.wiki_url = wiki_data.url;
        $scope.wiki_title = wiki_data.title;
      });
}])
.controller( 'WikisCtrl',
  ['$scope', '$stateParams', 'WikiService', 'HubsService',
  function WikisController($scope, $stateParams, WikiService, HubsService) {
    var page = 1;
    $scope.wikis = [];
    WikiService.with_search_results_for_wiki(HubsService.params({q: $stateParams.q, page: page}), function(response) {
      $scope.wikis.concat(response);
      page += 1;
    });
}])
.directive('wiki', function() {
    return {
      restrict: 'E',
      scope: { id: '=' },
      templateUrl: 'wiki/wiki.tpl.html',
      controller: 'WikiDirectiveCtrl'
    };
});
