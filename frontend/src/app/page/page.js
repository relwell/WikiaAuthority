angular.module( 'wikiaAuthority.page', [
  'ui.router'
])
.config(function config( $stateProvider ) {
  $stateProvider.state( 'page', {
    url: '/pages?:q',
    views: {
      "main": {
        controller: 'PagesCtrl',
        templateUrl: 'page/pages.tpl.html'
      }
    },
    data:{ pageTitle: 'Pages' }
  });
})
.service( 'PageService',
  ['$http',
    function PageService($http) {

    var with_details_for_page = function with_details_for_page(page, callable) {
      return $http.get('/api/page/'+page+'/details').success(callable);
    };

    var with_search_results_for_page = function with_search_results_for_page(search_params, callable) {
      return $http.get('/api/pages/', {params:search_params}).success(callable);
    };

    return {
      with_details_for_page: with_details_for_page,
      with_search_results_for_page: with_search_results_for_page
    };
  }]
)
.controller( 'PageDirectiveCtrl',
    ['$scope', 'PageService',
    function PageDirectiveController($scope, PageService) {
      PageService.with_details_for_page($scope.id,
      function(data) {
        $scope.page = data;
      });
}])
.controller( 'PagesCtrl',
    ['$scope', '$stateParams', 'PageService',
    function PagesController($scope, $stateParams, PageService) {
      PageService.with_search_result_for_page({q: $stateParams.q},
      function(pages) {
        $scope.pages = pages;
      });
}])
.directive('page', function() {
    return {
      restrict: 'E',
      scope: { id: '=' },
      templateUrl: 'page/page.tpl.html',
      controller: 'PageDirectiveCtrl'
    };
});
