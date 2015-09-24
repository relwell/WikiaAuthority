angular.module( 'wikiaAuthority.wiki', [
  'ui.router'
])
.service( 'WikiService',
  ['WikiService', '$http',
    function WikiService($http) {

    var with_details_for_wiki = function with_details_for_wiki(wiki_id, callable) {
      return $http.get('/api/wiki/'+wiki_id).success(callable)
    };

    return {
      with_details_for_wiki: with_details_for_wiki
    };
  }]
)
.directive('wiki', ['WikiService', function(WikiService) {
    return {
      restrict: 'E',
      scope: { wiki_id: '=' },
      link: function link(scope, ele, attrs){
        WikiService.with_details_for_wiki(scope.wiki_id, function(data) {
          var wiki_data = data.items[scope.wiki_id];
          ele.find('img.wiki-image').href = wiki_data.image;
          ele.find('a.to-wiki').href = wiki_data.url;
          ele.find('span.wiki-title').text = wiki_data.title;
        });
      },
      templateUrl: 'wiki/wiki.tpl.html'
    }
}]);
