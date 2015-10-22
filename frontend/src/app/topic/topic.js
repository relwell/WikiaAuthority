angular.module( 'wikiaAuthority.topic', [
  'ui.router'
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
    ['$scope', '$stateParams', 'TopicService',
    function TopicsController($scope, $stateParams, TopicService) {
      TopicService.with_search_results_for_topic({q: $stateParams.q},
      function(topics) {
        $scope.topics = topics;
      });
}])
.directive('topic', function() {
    return {
      restrict: 'E',
      scope: { topic: '=' },
      templateUrl: 'topic/topic.tpl.html',
      controller: 'TopicDirectiveCtrl'
    };
});
