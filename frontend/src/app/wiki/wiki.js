angular.module( 'wikiaAuthority.wiki', [
  'ui.router'
])
.service( 'WikiService',
  ['$http',
    function WikiService($http) {

    var with_details_for_wiki = function with_details_for_wiki(wiki_id, callable) {
      return $http.get('/api/wiki/'+wiki_id+'/details').success(callable);
    };

    return {
      with_details_for_wiki: with_details_for_wiki
    };
  }]
)
.controller( 'WikiCtrl',
    ['$scope', 'WikiService',
    function WikiController($scope, WikiService) {
      WikiService.with_details_for_wiki($scope.id,
      function(wiki_data) {
        $scope.image_href = wiki_data.image;
        $scope.wiki_url = wiki_data.url;
        $scope.wiki_title = wiki_data.title;
      });
}])
.directive('wiki', function() {
    return {
      restrict: 'E',
      scope: { id: '=' },
      templateUrl: 'wiki/wiki.tpl.html',
      controller: 'WikiCtrl'
    };
});
