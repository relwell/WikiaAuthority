angular.module( 'wikiaAuthority.topic', [
  'ui.router',
  'wikiaAuthority.hubs'
])
.config(function config( $stateProvider ) {
  $stateProvider.state( 'topic', {
    url: '/topics?:q',
    views: {
      "main": {
        controller: 'TopicsCtrl',
        templateUrl: 'topic/topics.tpl.html'
      }
    },
    data:{ pageTitle: 'Topics' }
  });
})
.service( 'TopicService',
  ['$http',
    function TopicService($http) {

    var with_search_results_for_topic = function with_search_results_for_topic(search_params, callable) {
      return $http.get('/api/topics/', {params:search_params}).success(callable);
    };

    return {
      with_search_results_for_topic: with_search_results_for_topic
    };
  }]
)
.controller( 'TopicDirectiveCtrl',
    ['$scope', 'TopicService',
    function TopicDirectiveController($scope, TopicService) {
}])
.controller( 'TopicsCtrl',
    ['$scope', '$stateParams', 'TopicService', 'HubsService',
    function TopicsController($scope, $stateParams, TopicService, HubsService) {
      var page = 1;
      $scope.topics = [];
      $scope.paginate = function() {
        TopicService.with_search_results_for_topic(HubsService.params({q: $stateParams.q, page: page}),
        function(topics) {
          $scope.topics.concat(topics);
          page += 1;
        });
      };
      $scope.paginate();
}])
.directive('topic', function() {
    return {
      restrict: 'E',
      scope: { topic: '=' },
      templateUrl: 'topic/topic.tpl.html',
      controller: 'TopicDirectiveCtrl'
    };
});
